"""WebRTC signaling lives in FastAPI; the media connection stays in Pipecat."""
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from .pipeline import run_call

router = APIRouter(prefix='/api/voice', tags=['voice'])


def handler_for(request):
    settings = request.app.state.settings
    if not settings.voice_configured:
        raise HTTPException(503, 'Configure ElevenLabs credentials and the selected LLM provider API key.')
    try:
        from pipecat.transports.smallwebrtc.request_handler import SmallWebRTCRequestHandler
    except ImportError as exc:
        raise HTTPException(503, 'Install requirements-voice.txt before starting calls.') from exc
    if request.app.state.voice_handler is None:
        request.app.state.voice_handler = SmallWebRTCRequestHandler()
    return request.app.state.voice_handler


@router.post('/offer')
async def offer(request: Request, background_tasks: BackgroundTasks):
    handler = handler_for(request)
    from pipecat.transports.smallwebrtc.request_handler import SmallWebRTCRequest
    data = await request.json()
    try:
        offer_request = SmallWebRTCRequest(**data)
    except (TypeError, ValueError) as exc:
        raise HTTPException(422, 'Invalid WebRTC offer') from exc

    async def start(connection):
        background_tasks.add_task(run_call, connection, request.app.state.settings, request.app.state.appointments)

    return await handler.handle_web_request(request=offer_request, webrtc_connection_callback=start)


@router.patch('/offer')
async def patch(request: Request):
    handler = handler_for(request)
    from pipecat.transports.smallwebrtc.request_handler import SmallWebRTCPatchRequest, IceCandidate
    data = await request.json()
    try:
        payload = SmallWebRTCPatchRequest(pc_id=data['pc_id'], candidates=[IceCandidate(**c) for c in data.get('candidates', [])])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(422, 'Invalid ICE candidates') from exc
    await handler.handle_patch_request(payload)
    return {'status': 'success'}
