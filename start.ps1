#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
$demoPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$demoEntry = Join-Path $PSScriptRoot 'backend\app.py'
$demoLogs = Join-Path $PSScriptRoot 'startup-logs'
$demoRun = [Guid]::NewGuid().ToString('N')
$demoStdout = Join-Path $demoLogs "$demoRun.stdout.log"
$demoStderr = Join-Path $demoLogs "$demoRun.stderr.log"
$demoProcess = $null
$demoExitCode = 0

function Show-Setup {
    Write-Host 'Run these setup commands, then launch this script again:'
    $quotedRoot = $PSScriptRoot.Replace("'", "''")
    Write-Host "Set-Location -LiteralPath '$quotedRoot'"
    Write-Host 'python -m venv .venv'
    Write-Host '.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt'
}

try {
    if (-not (Test-Path -LiteralPath $demoPython -PathType Leaf)) {
        Show-Setup
        throw 'The project Python environment is missing.'
    }
    try {
        & $demoPython -c 'import flask' 2>&1 | Out-Null
    } catch {
        Show-Setup
        throw 'Flask is unavailable in the project Python environment.'
    }
    if ($LASTEXITCODE -ne 0) {
        Show-Setup
        throw 'Flask is unavailable in the project Python environment.'
    }
    $listeners = [System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners()
    if ($listeners | Where-Object { $_.Port -eq 5000 }) {
        throw 'Port 5000 is occupied. Stop the existing server or free the port, then retry. No process was stopped.'
    }
    New-Item -ItemType Directory -Path $demoLogs -Force | Out-Null
    $demoProcess = Start-Process -FilePath $demoPython -ArgumentList @('-u', ('"' + $demoEntry + '"')) -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput $demoStdout -RedirectStandardError $demoStderr -PassThru
    $deadline = [DateTime]::UtcNow.AddSeconds(15)
    $ready = $false
    while ([DateTime]::UtcNow -lt $deadline) {
        if ($demoProcess.HasExited) {
            throw "Backend exited during startup (exit code $($demoProcess.ExitCode))."
        }
        try {
            $health = Invoke-RestMethod -Uri 'http://127.0.0.1:5000/api/health' -TimeoutSec 1
            $ready = ($health.status -eq 'ok' -and $health.dataset_loaded -eq $true)
        } catch {
            $ready = $false
        }
        if ($ready) { break }
        Start-Sleep -Milliseconds 200
    }
    if (-not $ready) { throw 'Backend did not become ready within 15 seconds.' }
    if ($demoProcess.HasExited) { throw 'Backend exited before the browser could open.' }
    Write-Host 'Ready: http://127.0.0.1:5000/  -- Press Ctrl+C to stop.'
    try {
        Start-Process 'http://127.0.0.1:5000/'
    } catch {
        Write-Warning 'Could not open the browser. Open http://127.0.0.1:5000/ manually.'
    }
    while (-not $demoProcess.HasExited) { Start-Sleep -Milliseconds 250 }
    if ($demoProcess.ExitCode -ne 0) { throw "Backend exited with code $($demoProcess.ExitCode)." }
} catch {
    $demoExitCode = 1
    Write-Host "Startup error: $($_.Exception.Message)" -ForegroundColor Red
    if (Test-Path -LiteralPath $demoStderr) {
        Get-Content -LiteralPath $demoStderr -Tail 15 | ForEach-Object { Write-Host $_ }
    }
} finally {
    if ($null -ne $demoProcess) {
        if (-not $demoProcess.HasExited) { $demoProcess.Kill(); $demoProcess.WaitForExit() }
        $demoProcess.Dispose()
        Write-Host "Backend logs: $demoStdout"
        Write-Host "              $demoStderr"
    }
}
exit $demoExitCode
