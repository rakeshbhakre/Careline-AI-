$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot 'frontend')
if (!(Test-Path 'node_modules')) { throw 'Run setup.ps1 first.' }
npm.cmd run dev -- --strictPort
