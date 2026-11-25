# Start here (Windows + VS Code)

Install Python 3.12, Node.js 22 and Git if missing. Extract the ZIP and open the hospital-appointment-agent folder in VS Code. Open a PowerShell terminal at the project root.

1. Run `powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1`. This installs dependencies, runs offline tests and builds the dashboard. If a command fails, stop and read its error.
2. Configure `backend/.env` only if this folder is excluded from OneDrive sync. Keep the file local and never paste keys into chat or commit it. If OneDrive sync is on, keep `.env` blank and enter credentials in the backend terminal (input is hidden):

   ```powershell
   $env:ELEVENLABS_API_KEY = [System.Net.NetworkCredential]::new('', (Read-Host 'ElevenLabs API key' -AsSecureString)).Password
   $env:GROQ_API_KEY = [System.Net.NetworkCredential]::new('', (Read-Host 'Groq API key' -AsSecureString)).Password
   $env:ELEVENLABS_VOICE_ID = Read-Host 'ElevenLabs voice ID'
   ```

   Check that GROQ_MODEL in `.env` (default `openai/gpt-oss-20b`) is available to your account. These environment variables last only for this terminal session and are inherited by the backend process.
3. In that same backend terminal run `powershell -NoProfile -ExecutionPolicy Bypass -File .\start-backend.ps1`. In another terminal at the project root run `powershell -NoProfile -ExecutionPolicy Bypass -File .\start-frontend.ps1`.
4. Visit http://localhost:5173 and allow microphone access. Check http://localhost:8000/api/health if the dashboard cannot connect.
5. Follow the live acceptance checklist in README.md before recording the demo. The ZIP includes Git history. Create an empty repository in your own GitHub account and inspect `git remote -v` before adding or changing origin and pushing main.

Status: reconstructed snapshot with SDK audio and assistant transcript handling updated. See CODEX-HANDOFF.md for remaining live acceptance work. A configured health response does not prove provider connectivity. Use fictional phone numbers.
