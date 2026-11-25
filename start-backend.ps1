$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot 'backend')
if (!(Test-Path '.venv\Scripts\python.exe')) { throw 'Run setup.ps1 first.' }
& .\.venv\Scripts\python.exe -m uvicorn src.main:app --host 127.0.0.1 --port 8000
