$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
function Check-Exit { if ($LASTEXITCODE -ne 0) { throw "Command failed (exit $LASTEXITCODE). See the error above." } }

# Prefer the documented runtimes, but permit the installed Python launcher/runtime
# on fresh Windows images where the py launcher entry can point at a missing Store app.
$pythonExe = $null
foreach ($candidate in @(@('py', '-3.12'), @('py', '-3.11'), @('py', '-3.10'), @('python'))) {
    $command = $candidate[0]
    $candidateArgs = @($candidate | Select-Object -Skip 1)
    try {
        $candidateExe = & $command @candidateArgs -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $candidateExe = ($candidateExe | Select-Object -Last 1).Trim()
            & $candidateExe --version *> $null
            if ($LASTEXITCODE -eq 0) {
                $pythonExe = $candidateExe
                break
            }
        }
    } catch { }
}
if (!$pythonExe) { throw 'Python 3.10 or newer was not found. Install Python 3.12 (recommended) and rerun setup.' }
$pythonVersion = & $pythonExe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($LASTEXITCODE -ne 0 -or [version]$pythonVersion -lt [version]'3.10' -or [version]$pythonVersion -ge [version]'3.14') {
    throw "Unsupported Python version '$pythonVersion'. Install Python 3.12 and rerun setup."
}
Write-Host "Using Python $pythonVersion. Python 3.11 or 3.12 is recommended for voice calls."
node --version
Check-Exit
Push-Location backend
try {
    $venvPython = '.venv\Scripts\python.exe'
    if (Test-Path $venvPython) {
        try { & $venvPython --version *> $null } catch { $LASTEXITCODE = 1 }
        if ($LASTEXITCODE -ne 0) { throw 'The existing backend/.venv interpreter cannot start. Preserve it and repair or rename it manually, then rerun setup.' }
    }
    if (!(Test-Path $venvPython)) { & $pythonExe -m venv .venv; Check-Exit }
    & .\.venv\Scripts\python.exe -m pip install -r requirements-voice.txt
    Check-Exit
    & .\.venv\Scripts\python.exe -m pip check
    Check-Exit
    if (!(Test-Path .env)) { Copy-Item .env.example .env }
    & .\.venv\Scripts\python.exe -m pytest -q
    Check-Exit
} finally { Pop-Location }
Push-Location frontend
try {
    npm.cmd install
    Check-Exit
    npm.cmd test
    Check-Exit
    npm.cmd run build
    Check-Exit
} finally { Pop-Location }
Write-Host 'Setup complete. Edit backend/.env with your provider credentials before starting a call.'
