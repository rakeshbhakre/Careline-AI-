"""Compose one observable, isolated Pipecat pipeline per WebRTC connection."""
import logging
import uuid

from .prompt import system_prompt
from .session import CallSession, UserTurnTracker
from .tools import TOOL_SPECS, VoiceTools

logger = logging.getLogger(__name__)


async def run_call(connection, settings, appointments):
    # Keep provider imports local so the scheduling API can run without voice extras.
    from pipecat.adapters.schemas.function_schema import FunctionSchema
    from pipecat.adapters.schemas.tools_schema import ToolsSchema
    from pipecat.audio.vad.silero import SileroVADAnalyzer
    from pipecat.frames.frames import (
        FunctionCallInProgressFrame,
        FunctionCallResultFrame,
        InputAudioRawFrame,
        InterruptionFrame,
        InterimTranscriptionFrame,
        LLMContextFrame,
        LLMFullResponseEndFrame,
        LLMFullResponseStartFrame,
        LLMRunFrame,
        LLMTextFrame,
        TTSAudioRawFrame,
        TranscriptionFrame,
        VADUserStartedSpeakingFrame,
        VADUserStoppedSpeakingFrame,
    )
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.runner import PipelineRunner
    from pipecat.pipeline.task import PipelineParams, PipelineTask
    from pipecat.processors.aggregators.llm_context import LLMContext
    from pipecat.processors.aggregators.llm_response_universal import (
        LLMContextAggregatorPair,
        LLMUserAggregatorParams,
    )
    from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
    from pipecat.services.elevenlabs.stt import ElevenLabsRealtimeSTTService
    from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
    from pipecat.services.google.llm import GoogleLLMService
    from pipecat.services.groq.llm import GroqLLMService
    from pipecat.transports.base_transport import TransportParams
    from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport

    call_id = uuid.uuid4().hex[:8]
    session = CallSession()
    tools = VoiceTools(appointments, session)
    transport = SmallWebRTCTransport(
        webrtc_connection=connection,
        params=TransportParams(audio_in_enabled=True, audio_out_enabled=True),
    )
    stt = ElevenLabsRealtimeSTTService(api_key=settings.elevenlabs_api_key)
    tts = ElevenLabsTTSService(
        api_key=settings.elevenlabs_api_key,
        settings=ElevenLabsTTSService.Settings(voice=settings.elevenlabs_voice_id),
    )
    if settings.llm_provider == 'groq':
        llm = GroqLLMService(
            api_key=settings.groq_api_key,
            settings=GroqLLMService.Settings(model=settings.groq_model, system_instruction=system_prompt()),
        )
    else:
        llm = GoogleLLMService(
            api_key=settings.google_api_key,
            settings=GoogleLLMService.Settings(model=settings.google_model, system_instruction=system_prompt()),
        )

    schemas = [FunctionSchema(name=n, description=d, properties=p, required=r) for n, d, p, r in TOOL_SPECS]
    context = LLMContext(messages=[], tools=ToolsSchema(standard_tools=schemas))
    user, assistant = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()),
    )

    class VoiceFlowTrace(FrameProcessor):
        """Log pipeline progress without recording transcript contents or credentials."""

        WATCHED = (
            InputAudioRawFrame,
            InterimTranscriptionFrame,
            TranscriptionFrame,
            VADUserStartedSpeakingFrame,
            VADUserStoppedSpeakingFrame,
            InterruptionFrame,
            LLMContextFrame,
            LLMFullResponseStartFrame,
            LLMTextFrame,
            FunctionCallInProgressFrame,
            FunctionCallResultFrame,
            LLMFullResponseEndFrame,
            TTSAudioRawFrame,
        )

        def __init__(self, stage):
            super().__init__()
            self.stage = stage
            self.counts = {}

        async def process_frame(self, frame, direction):
            await super().process_frame(frame, direction)
            if isinstance(frame, self.WATCHED):
                name = type(frame).__name__
                self.counts[name] = self.counts.get(name, 0) + 1
                count = self.counts[name]
                if count == 1 or count % 50 == 0 or isinstance(frame, (TranscriptionFrame, LLMTextFrame, FunctionCallInProgressFrame, FunctionCallResultFrame, InterruptionFrame)):
                    size = len(getattr(frame, 'audio', b'')) if hasattr(frame, 'audio') else len(getattr(frame, 'text', '')) if hasattr(frame, 'text') else None
                    logger.info('voice[%s] stage=%s frame=%s count=%s size=%s', call_id, self.stage, name, count, size)
            await self.push_frame(frame, direction)

    microphone_trace = VoiceFlowTrace('microphone_to_stt')
    stt_trace = VoiceFlowTrace('elevenlabs_stt_to_turn_aggregator')
    llm_trace = VoiceFlowTrace('groq_llm_to_elevenlabs_tts')
    tts_trace = VoiceFlowTrace('elevenlabs_tts_to_webrtc_output')
    webrtc_trace = VoiceFlowTrace('after_webrtc_output')

    class ConfirmationGuard(FrameProcessor):
        """Observe each caller turn exactly once before it reaches the LLM."""

        def __init__(self):
            super().__init__()
            self.turn_tracker = UserTurnTracker()
            self.interrupted = False

        async def process_frame(self, frame, direction):
            await super().process_frame(frame, direction)
            if isinstance(frame, InterruptionFrame):
                self.interrupted = True
            if isinstance(frame, LLMContextFrame) and direction == FrameDirection.DOWNSTREAM:
                latest = self.turn_tracker.next_user_text(frame.context.get_messages())
                if latest is not None:
                    session.observe_user(latest)
                    self.interrupted = False
                    await publish_patient_state()
            await self.push_frame(frame, direction)

    confirmation_guard = ConfirmationGuard()
    task = PipelineTask(
        Pipeline([
            transport.input(),
            microphone_trace,
            stt,
            stt_trace,
            user,
            confirmation_guard,
            llm,
            llm_trace,
            tts,
            tts_trace,
            transport.output(),
            webrtc_trace,
            assistant,
        ]),
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
    )

    greeting_instruction = {'role': 'developer', 'content': 'Greet the caller once now, then ask how you can help.'}
    greeting_pending = True

    async def publish_patient_state():
        await task.rtvi.send_server_message({
            'type': 'careline.patient',
            'patient_name': session.patient_name,
            'phone_number': session.phone,
            'phone_confirmed': session.confirmed,
        })

    @assistant.event_handler('on_assistant_turn_stopped')
    async def assistant_turn(_aggregator, message):
        nonlocal greeting_pending
        interrupted = getattr(message, 'interrupted', False)
        session.observe_assistant(message.content, interrupted)
        if greeting_pending:
            context.set_messages([item for item in context.get_messages() if item is not greeting_instruction])
            greeting_pending = False
        await publish_patient_state()

    async def handle(params):
        result = await tools.execute(params.function_name, params.arguments)
        status = result.get('status') if isinstance(result, dict) else 'error'
        logger.info('voice[%s] tool=%s status=%s', call_id, params.function_name, status)
        if params.function_name == 'prepare_appointment' and status == 'ready_for_confirmation':
            await publish_patient_state()
        elif params.function_name == 'book_appointment' and status == 'booked':
            await task.rtvi.send_server_message({
                'type': 'careline.appointment_booked',
                'appointment': result,
                'phone_number': session.phone,
            })
        elif params.function_name == 'cancel_appointment' and status == 'cancelled':
            await task.rtvi.send_server_message({'type': 'careline.appointment_cancelled', 'appointment_id': result.get('id')})
        await params.result_callback(result)

    for name, *_ in TOOL_SPECS:
        llm.register_function(name, handle, cancel_on_interruption=False)

    @task.rtvi.event_handler('on_client_ready')
    async def connected(rtvi):
        logger.info('voice[%s] WebRTC client ready; queueing one-time greeting', call_id)
        await rtvi.set_bot_ready()
        context.add_message(greeting_instruction)
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler('on_client_disconnected')
    async def disconnected(_transport, _client):
        logger.info('voice[%s] WebRTC client disconnected', call_id)
        await task.cancel()

    logger.info('voice[%s] pipeline starting; audio in/out enabled, VAD and interruptions enabled', call_id)
    try:
        await PipelineRunner(handle_sigint=False).run(task)
    except Exception:
        logger.exception('voice[%s] pipeline failed', call_id)
        raise
    finally:
        for trace in (microphone_trace, stt_trace, llm_trace, tts_trace, webrtc_trace):
            logger.info('voice[%s] stage=%s totals=%s', call_id, trace.stage, trace.counts)
        logger.info('voice[%s] pipeline stopped', call_id)
