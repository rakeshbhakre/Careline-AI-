# Development log

## Milestone 1 — repository foundation
Created directory boundaries, environment templates and Git ignore rules. Added architecture decision and requirements. No dependencies installed and no runtime tests performed yet. Next milestone: validate provider credentials and compatible Pipecat WebRTC stack.

## Milestone 2 — scheduling backend
Implemented FastAPI lifespan, typed settings, SQLite schema, idempotent future demo slots, transactional repository and async service. Replaced planned aiosqlite with stdlib sqlite3 and asyncio.to_thread to keep dependencies small and avoid blocking the event loop. Dashboard APIs expose masked phone numbers. Eight automated tests passed, including concurrent booking, cancellation ownership, and REST integration. Voice providers and frontend remain unimplemented; no remote push performed.

## Milestone 3 — voice engine

- Added per-call confirmation state and a conservative parser for numeric and individually spoken digits. Confirmation requires a matching assistant readback and a separate affirmative turn; unsupported phrases require clarification.
- Added provider-independent tool adapter; three registered operations use the existing scheduling service. No model-supplied phone or confirmation flag is trusted. Results omit full numbers and availability times are formatted in IST.
- Added Pipecat pipeline composition, Silero VAD, ElevenLabs realtime STT/TTS, configurable Gemini, and FastAPI SmallWebRTC signaling. Session state is not shared between callers. Appointment mutations remain transactional in the scheduling domain.
- Added RTVI client-ready handshake for future frontend integration. Dashboard refresh and rendering are still pending.
- Offline verification: 12 pytest tests passed, including booking/cancellation through tool adapter and rejection without confirmation. Python compile check passed. Actual Pipecat dependency installation and browser/provider integration are unverified because package index access and API credentials are unavailable here.
- Live acceptance: connect a compatible client, check both audio directions, confirm the readback gate with a fictional number, book a slot, inspect the REST schedule, cancel, disconnect, reconnect and verify session isolation. Test interrupted readbacks and provider failures. The prompt requests explicit appointment selection agreement; it is not a separately enforced state machine.

References: https://docs.pipecat.ai/api-reference/server/services/stt/elevenlabs ; https://docs.pipecat.ai/api-reference/server/services/tts/elevenlabs ; https://docs.pipecat.ai/pipecat/learn/function-calling ; https://docs.pipecat.ai/api-reference/server/services/transport/small-webrtc ; https://ai.google.dev/gemini-api/docs/pricing

## Milestone 4 — dashboard
- Added React/Vite split-screen dashboard with custom responsive CSS, schedule and voice feature modules.
- Uses official Pipecat JS client and SmallWebRTC for call connection, audio track, transcript, mute and disconnect callbacks.
- Schedule refreshes every 2.5 seconds with cancellation of stale requests. No additional event infrastructure.
- Two Node tests for IST date grouping passed; all 12 backend tests passed again. npm registry DNS was unreachable, so dependency installation, build and live browser behavior remain unverified.
- The frontend uses custom CSS rather than Tailwind to reduce setup dependencies. No lockfile could be generated without installation.
- No GitHub remote push or live demo recording has occurred.

## Setup handoff
Added Windows installation and launch scripts. Re-ran 12 backend tests and 2 frontend utility tests successfully. Live provider testing remains blocked by missing dependencies and credentials; Windows scripts are unverified in this Linux environment.
