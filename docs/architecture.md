# Architecture decision: modular monolith

Status: accepted for implementation; not yet integration-tested.

## Context
The assignment requires Python Pipecat, ElevenLabs STT/TTS, three registered appointment tools, spoken phone-number confirmation, browser calls, live transcript and a schedule dashboard. SQLite and mock doctors are allowed.

## Decision
Use React/Vite/custom CSS for the single-page dashboard, FastAPI for REST and WebRTC signaling, Pipecat with SmallWebRTC for audio, Groq for tool calling (Gemini optional), and SQLite with sqlite3 and explicit thread offloading for persistence. Select and pin compatible SDK versions after validating the voice example.

## Boundaries
- Appointment module: schemas, repository, service and read-only dashboard router. No Pipecat dependency.
- Voice module: signaling, pipeline, prompt, per-call session and tool adapters. Calls appointment service directly.
- Database module: schema, connection lifecycle and idempotent fictional seed data.
- Frontend: voice-call and schedule-board features, shared API client.

## Data flow
Browser microphone -> WebRTC -> Pipecat -> ElevenLabs STT -> Groq -> ElevenLabs TTS -> WebRTC -> browser speaker. LLM function calls invoke scheduling logic through tool adapters. Return committed results to the model. Transcript events reach the browser; successful mutations trigger dashboard refetch, with polling fallback.

## Correctness
Use a partial unique index on active bookings per slot. Cancel rather than delete; check ownership by confirmed normalized phone number. Keep confirmation per session and reset on changed number. Disambiguate multiple bookings before cancellation. Treat phone confirmation as demo identification, not secure authentication. Use fictional data and never expose provider secrets to the browser. Keep one backend worker for initial in-memory call state.

## Acceptance criteria
Real browser audio, both ElevenLabs speech services, all three registered tools, spoken number read-back and confirmation, persistent booking and cancellation, live transcript and schedule refresh. Test concurrent booking and session isolation. README and a recording of a full booking flow (at most three minutes) required for submission.

## Trade-offs
A monolith avoids an internal network boundary and additional database service. SQLite and in-memory WebRTC sessions constrain horizontal scaling; appropriate for a local demo, not a production healthcare system.
