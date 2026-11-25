# Hospital Appointment Agent

A browser-based voice receptionist prototype for the NexovAI internship assignment.

## Status
The reconstructed project now has the voice client connection updated for the pinned Small WebRTC SDK, remote audio track replacement and playback handling, and assistant transcript handling for both the older RTVI 1.2 server and newer bot-output events. The greeting prompt also avoids restarting after tool results. Automated scheduling, booking, and cancellation checks are included. Live assistant audio and the full live booking/cancellation call still need verification with provider credentials and a browser microphone. See [handoff notes](CODEX-HANDOFF.md).

## Architecture
React + Vite frontend; a single Python FastAPI backend containing Pipecat and scheduling modules; SQLite persistence. ElevenLabs provides STT and TTS; Groq (GPT-OSS 20B) provides language understanding and function calling; Gemini is optional.

See [architecture](docs/architecture.md) for decisions and acceptance criteria.

## Run the scheduling backend

Use Python 3.12 (recommended) or 3.11. The setup script can detect an installed Python 3.10 runtime as a fallback, but use Python 3.11/3.12 for voice calls.

```bash
cd backend
python -m venv .venv
# Activate the virtual environment for your OS
python -m pip install -r requirements.txt
python -m pytest -q
python -m uvicorn src.main:app --port 8000
```

Open http://localhost:8000/docs to inspect the read-only scheduling endpoints. The SQLite database initializes automatically. API provider keys are not needed for these tests.

## Voice engine (integration pending live verification)

Use Python 3.11 or 3.12 in a virtual environment. The Windows setup script installs the pinned voice stack. From `backend/`:

```sh
python -m pip install -r requirements-voice.txt
cp .env.example .env
# Set ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, GROQ_API_KEY in .env.
# GROQ_MODEL is configurable; verify your account has access.
python -m uvicorn src.main:app --port 8000
```

On Windows PowerShell use `Copy-Item .env.example .env` instead of `cp` if needed. Keep real credentials out of synced folders; on OneDrive use the hidden environment variable prompts in `START-HERE.md` unless sync is disabled for this project.
The WebRTC offer endpoint is `/api/voice/offer` (POST/PATCH). The custom dashboard uses the official Pipecat JavaScript client. Run one Uvicorn worker for in-memory connection state. The health endpoint indicates configuration only, not provider connectivity.

`python -m pytest -q` runs the offline scheduling and tool tests. Pipecat is pinned to 0.0.108 to target the PipelineTask and RTVI v1 APIs. This workspace has the voice extras installed. Live outgoing audio, assistant transcript delivery and booking/cancellation still need a browser call with configured provider credentials. Use fictional phone numbers only. On Windows, follow `START-HERE.md` for hidden terminal prompts; keep provider keys out of the frontend and synced folders.

## Run the dashboard (second terminal)

Use Node 22 or newer. From the project root:

```sh
cd frontend
npm install
npm test
npm run dev
```

Open http://localhost:5173. The frontend uses the default API URL http://localhost:8000; copy `.env.example` to `.env` to override it. No provider keys belong in the frontend. The dashboard polls the schedule every 2.5 seconds. Voice readiness indicates configuration, not a successful provider connection.

## Windows quick start

Extract the project ZIP, open the extracted `hospital-appointment-agent` directory in VS Code, and open two PowerShell terminals. In the first terminal:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-voice.txt
```

Setup creates a blank `backend/.env`. Store credentials there only if the project folder is excluded from OneDrive sync; otherwise use the hidden PowerShell prompts in [START-HERE.md](START-HERE.md). Then run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn src.main:app --port 8000
```

In the second terminal, from the project root:

```powershell
cd frontend
npm install
npm run build
npm run dev
```

Open the dashboard at http://localhost:5173. Allow microphone access and use a fictional phone number. Do not expose this demo to the public internet with real patient data. The ZIP preserves local Git history; inspect `git log --oneline` before publishing to an empty repository you own.

## Live acceptance checklist

- [ ] Install voice and frontend dependencies and build frontend.
- [ ] Confirm provider keys, model access and ElevenLabs voice ID.
- [ ] Start a browser call; hear the greeting and see both sides of transcript.
- [ ] Speak a fictional phone number, verify matching readback, confirm.
- [ ] Request availability, select an offered slot, verify booking in dashboard.
- [ ] Cancel the appointment, verify slot restored and status updated.
- [ ] End call, reconnect and verify a fresh caller session.
- [ ] Check missing credentials, denied microphone permission, and network failure.

Full live acceptance is not complete; see CODEX-HANDOFF.md for observed partial results. Record a short demo only after these checks pass.

## Quick start scripts

See [START-HERE.md](START-HERE.md) for the Windows setup and launch commands.
