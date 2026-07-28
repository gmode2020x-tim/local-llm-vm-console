$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Created .env from .env.example"
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
  $PythonLauncher = $null
  foreach ($Candidate in @("py", "python")) {
    try {
      & $Candidate --version *> $null
      $PythonLauncher = $Candidate
      break
    } catch {
      $null = $_
    }
  }
  if (-not $PythonLauncher) {
    throw "Python 3.11+ was not found on PATH."
  }
  if ($PythonLauncher -eq "py") {
    py -3 -m venv .venv
  } else {
    python -m venv .venv
  }
}

.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

New-Item -ItemType Directory -Force "runtime\ui-data\logs" | Out-Null

Write-Host ""
Write-Host "Native setup complete."
Write-Host "Start UI:      .\deploy\windows\start-ui.ps1"
Write-Host "Start worker:  .\deploy\windows\start-host-worker.ps1"
Write-Host "Open:          http://127.0.0.1:8068"
