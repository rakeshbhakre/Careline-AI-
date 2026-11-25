"""Compose one Pipecat pipeline per WebRTC connection."""
from .prompt import system_prompt
from .session import CallSession
from .tools import TOOL_SPECS, VoiceTools


async def run_call(connection, settings, appointments):
    # Keep provider imports local so the scheduling API can run without voice extras.
    from pipecat.adapters.schemas.function_schema import FunctionSchema
    from pipecat.adapters.schemas.tools_schema import ToolsSchema
    from pipecat.audio.vad.silero import SileroVADAnalyzer
    from pipecat.frames.frames import LLMContextFrame, LLMRunFrame, InterruptionFrame
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.runner import PipelineRunner
    from pipecat.pipeline.task import PipelineParams, PipelineTask
    from pipecat.processors.aggregators.llm_context import LLMContext
    from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair, LLMUserAggregatorParams
    from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
    from pipecat.services.elevenlabs.stt import ElevenLabsRealtimeSTTService
    from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
    from pipecat.services.google.llm import GoogleLLMService
    from pipecat.services.groq.llm import GroqLLMService
    from pipecat.transports.base_transport import TransportParams
    from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport

    session = CallSession()
    tools = VoiceTools(appointments, session)
    transport = SmallWebRTCTransport(webrtc_connection=connection, params=TransportParams(audio_in_enabled=True, audio_out_enabled=True))
    stt = ElevenLabsRealtimeSTTService(api_key=settings.elevenlabs_api_key)
    tts = ElevenLabsTTSService(api_key=settings.elevenlabs_api_key, settings=ElevenLabsTTSService.Settings(voice=settings.elevenlabs_voice_id))
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
    user, assistant = LLMContextAggregatorPair(context, user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()))

    class ConfirmationGuard(FrameProcessor):
        """Observe each new user context message before inference, not LLM arguments."""
        def __init__(self):
            super().__init__()
            self.last_user = None
            self.interrupted = False

        async def process_frame(self, frame, direction):
            await super().process_frame(frame, direction)
            if isinstance(frame, InterruptionFrame):
                self.interrupted = True
            if isinstance(frame, LLMContextFrame) and direction == FrameDirection.DOWNSTREAM:
                messages = frame.context.get_messages()
                latest = next((m for m in reversed(messages) if isinstance(m, dict) and m.get('role') == 'user' and isinstance(m.get('content'), str)), None)
                if latest is not None and latest is not self.last_user:
                    self.last_user = latest
                    session.observe_user(latest['content'])
                    self.interrupted = False
            await self.push_frame(frame, direction)

    guard = ConfirmationGuard()

    @assistant.event_handler('on_assistant_turn_stopped')
    async def assistant_turn(_aggregator, message):
        session.observe_assistant(message.content, getattr(message, 'interrupted', False) or guard.interrupted)

    async def handle(params):
        result = await tools.execute(params.function_name, params.arguments)
        await params.result_callback(result)

    for name, *_ in TOOL_SPECS:
        llm.register_function(name, handle, cancel_on_interruption=False)

    pipeline = Pipeline([transport.input(), stt, user, guard, llm, tts, transport.output(), assistant])
    task = PipelineTask(pipeline, params=PipelineParams(enable_metrics=True, enable_usage_metrics=True))

    @task.rtvi.event_handler('on_client_ready')
    async def connected(rtvi):
        await rtvi.set_bot_ready()
        context.add_message({'role': 'developer', 'content': 'Greet the caller now.'})
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler('on_client_disconnected')
    async def disconnected(_transport, _client):
        await task.cancel()

    await PipelineRunner(handle_sigint=False).run(task)
