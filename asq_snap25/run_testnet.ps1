# Launch ASQ-snap25 on Binance testnet and tee console to a real log file.
# Usage (from repo root, with conda env already active):
#   .\asq_snap25\run_testnet.ps1

# Do NOT use ErrorAction Stop here: Nautilus writes [ERROR] lines to stderr
# (e.g. Binance -2011 cancel-already-gone). PowerShell would treat those as
# terminating errors and kill the Tee-Object pipeline.
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:ASQ_INSTRUMENTS = "ETHUSDT-PERP.BINANCE"
if (-not $env:BINANCE_TESTNET) { $env:BINANCE_TESTNET = "1" }

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logDir = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir "asq-snap25-testnet-$stamp.log"

Write-Host "cwd:  $Root"
Write-Host "log:  $log"
Write-Host "tip:  look for this .log file (not the 0-byte stubs without extension)"
Write-Host ""

# Merge stderr via cmd so PowerShell never promotes Nautilus ERROR logs to
# NativeCommandError / RemoteException (which previously stopped the bot).
cmd /c "python -m asq_snap25 2>&1" | Tee-Object -FilePath $log
