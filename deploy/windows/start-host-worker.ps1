$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$PythonCandidates = @(
  (Join-Path $Root ".venv\Scripts\python.exe"),
  "python",
  "py"
)

$Python = $null
foreach ($Candidate in $PythonCandidates) {
  try {
    & $Candidate --version *> $null
    $Python = $Candidate
    break
  } catch {
    $null = $_
  }
}

if (-not $Python) {
  throw "No Python interpreter was found. Install Python 3.11+ or create .venv first."
}

$env:HOST_WORKER_BIND = if ($env:HOST_WORKER_BIND) { $env:HOST_WORKER_BIND } else { "0.0.0.0" }
$env:HOST_WORKER_PORT = if ($env:HOST_WORKER_PORT) { $env:HOST_WORKER_PORT } else { "8090" }

$ExistingListener = Get-NetTCPConnection -LocalPort ([int]$env:HOST_WORKER_PORT) -State Listen -ErrorAction SilentlyContinue
if ($ExistingListener) {
  Write-Host "Host worker already appears to be listening on port $($env:HOST_WORKER_PORT)."
  return
}

$LogDir = Join-Path $Root "runtime\logs"
New-Item -ItemType Directory -Force $LogDir | Out-Null
$Script = Join-Path $Root "worker\host_worker.py"
$OutLog = Join-Path $LogDir "host-worker.out.log"
$ErrLog = Join-Path $LogDir "host-worker.err.log"

Start-Process -FilePath $Python -ArgumentList @("`"$Script`"") -WorkingDirectory $Root -WindowStyle Hidden -RedirectStandardOutput $OutLog -RedirectStandardError $ErrLog
Write-Host "Started host worker on http://0.0.0.0:$($env:HOST_WORKER_PORT)"
Write-Host "Health: http://127.0.0.1:$($env:HOST_WORKER_PORT)/healthz"
