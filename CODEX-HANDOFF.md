# Codex handoff — Careline AI

This is a reconstruction from the last archived repository plus the known local edits described in chat. It is not a copy of the user's current Windows working tree. The original Git history is preserved; the reconstructed changes are intentionally uncommitted for review. No real credentials or local appointment records are included. Prefer continuing the existing Windows repository if it contains newer work.

## Known state from local testing
- Python 3.12.10, Pipecat 0.0.108, Groq SDK 1.7.0; frontend React/Vite with client-js 1.13.1 and small-webrtc-transport 1.10.8.
- User observed 12 backend tests passing after provider migration; earlier 2 frontend tests and Vite build passed. Health endpoint configured. Windows tzdata and React scroll useEffect fixes applied.
- Gemini returned 503 in standalone and live calls; Groq GPT-OSS 20B worked standalone (1.98s) and in Pipecat (one measured TTFB 0.404s). Caller transcript and availability tool result observed. ElevenLabs TTS invoked; earlier TTS TTFB 0.086s, not proof of delivered audio.
- **Blocking issue: no audible assistant voice and no assistant transcript.** A silent test did not help. No live booking/cancellation verified. One model response after tool result appeared to repeat greeting.
- Browser warned bot protocol 1.2.0 older than client 2.1.0; deprecated `webrtcUrl`; remote audio track replacement logged. Console Ninja extension logged WebSocket failures on localhost:60388; treat as separate unless proven otherwise.

## Codex instructions
Inspect `git status`, `git diff`, `frontend/src/features/voice-call/useVoiceCall.js`, `PhoneScreen.jsx`, installed SDK types/sources, and backend `pipeline.py`. Do not rebuild from scratch. Fix outgoing audio and both-sided transcript first. Confirm actual TTS audio frames, remote track attachment/replacement, playback promises and event compatibility; use version-specific SDK APIs and pin compatible versions only if needed. Inspect unused botBuffer and transcript event behavior. Check greeting and tool-result continuation. Preserve mandatory Pipecat, ElevenLabs STT/TTS, phone confirmation guard and transactional appointment tools. Do not replace Groq without evidence.

Run backend syntax/tests/pip check and frontend tests/build/audit. Avoid npm audit fix --force. Verify live call using mock data: greeting, availability, phone readback and confirmation, booking, dashboard update, cancellation and reconnect. User must confirm audible speech; don't claim completion without it. Update docs, env example and Git hygiene. Never print or commit keys. Do not push or submit without user approval. No destructive operations. Prioritize core functionality over visual polish. Explain verified results and remaining blockers.

## Launch
Open this folder in VS Code. On a fresh extraction run setup.ps1 per START-HERE.md, then fill backend/.env with existing ElevenLabs and Groq credentials. Start backend and frontend scripts in separate PowerShell terminals. If using original local repo, do not overwrite its .env, database, virtual environment, or uncommitted changes with this archive.

## Current workspace update (2026-11-25)
- Updated the frontend to configure the installed Small WebRTC transport with `webrtcRequestParams` and `connect()`, replacing deprecated URL options.
- Remote audio now uses a persistent MediaStream, handles track replacement/removal, and reports playback rejection with actionable audio controls.
- Assistant transcript handling now collects older RTVI bot LLM text and flushes it at turn stop; newer server bot-output events are used when the server protocol supports them. Caller transcript remains handled by `onUserTranscript`.
- Updated the receptionist prompt to greet once and continue naturally after tool calls.
- Updated Vite from 6.3.6 to patched 6.4.6 after npm audit found a high-severity advisory; audit then reported zero vulnerabilities.
- Setup creates an ignored blank `backend/.env` if missing and prefers Python 3.12 while detecting supported local runtimes. Never copy keys into chat or Git. This workspace is under OneDrive; avoid storing real credentials in `.env` unless sync is disabled for the project. Environment variables in the backend terminal are an alternative.
- Frontend tests/build and offline backend tests pass in this workspace. A live provider call is still required to confirm actual audible assistant speech, assistant transcript delivery, and the complete booking/cancellation interaction.
