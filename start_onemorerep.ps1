$ErrorActionPreference = 'Stop'
$project = $PSScriptRoot
$pgRoot = 'C:\Users\cooli\Downloads\postgresql-18.6-4-windows-x64-binaries\pgsql'
$pgCtl = Join-Path $pgRoot 'bin\pg_ctl.exe'
$dataDir = Join-Path $project 'data\postgres'
$logDir = Join-Path $project 'work'
$backendLog = Join-Path $logDir 'backend.log'
$frontendLog = Join-Path $logDir 'frontend.log'
$apiUrl = 'http://127.0.0.1:8000'
$webUrl = 'http://127.0.0.1:3000'

if (!(Test-Path -LiteralPath $pgCtl)) { throw "PostgreSQL executable not found: $pgCtl" }
if (!(Test-Path -LiteralPath $dataDir)) { throw "PostgreSQL data directory not found: $dataDir" }
if (!(Test-Path -LiteralPath (Join-Path $project 'config_local.py'))) {
    throw 'Local database credentials are missing. Restore config_local.py before launching.'
}
if (!(Test-Path -LiteralPath (Join-Path $project 'frontend\node_modules\next\dist\bin\next'))) {
    throw 'Frontend dependencies are missing. In frontend, run npm install first.'
}

New-Item -ItemType Directory -Path $logDir -Force | Out-Null
& $pgCtl -D $dataDir status *> $null
if ($LASTEXITCODE -ne 0) {
    & $pgCtl -D $dataDir -l (Join-Path $logDir 'postgresql.log') -o '-h 127.0.0.1 -p 5432' start
    if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL could not start. Check work\postgresql.log.' }
}

$apiRunning = $false
try { $null = Invoke-RestMethod "$apiUrl/health" -TimeoutSec 2; $apiRunning = $true } catch {}
if (!$apiRunning) {
    $apiCommand = "Set-Location -LiteralPath '$project'; python -m uvicorn onemorerep.webapp:app --host 127.0.0.1 --port 8000 *> '$backendLog'"
    Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @('-NoProfile', '-Command', $apiCommand)
}

$webRunning = $false
try { $null = Invoke-WebRequest $webUrl -TimeoutSec 2; $webRunning = $true } catch {}
if (!$webRunning) {
    $webCommand = "Set-Location -LiteralPath '$project\frontend'; npm run dev -- --hostname 127.0.0.1 *> '$frontendLog'"
    Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @('-NoProfile', '-Command', $webCommand)
}

$ready = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    try {
        $null = Invoke-WebRequest $webUrl -TimeoutSec 2
        $null = Invoke-RestMethod "$apiUrl/health" -TimeoutSec 2
        $ready = $true
        break
    } catch { Start-Sleep -Seconds 1 }
}
if (!$ready) { throw "OneMoreRep did not become ready. Check $backendLog and $frontendLog." }
Start-Process $webUrl
Write-Host "OneMoreRep is open at $webUrl"
