$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
}

Get-Content ".env" | ForEach-Object {
  $Line = $_.Trim()
  if ($Line -and -not $Line.StartsWith("#") -and $Line.Contains("=")) {
    $Name, $Value = $Line.Split("=", 2)
    [Environment]::SetEnvironmentVariable($Name.Trim(), $Value.Trim(), "Process")
  }
}

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
  throw "Virtual environment missing. Run deploy\windows\setup-native.ps1 first."
}

$Port = if ($env:PORT) { [int]$env:PORT } else { 8068 }
$ExistingListener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($ExistingListener) {
  Write-Host "Local LLM UI already appears to be listening on port $Port."
  return
}

$LogDir = Join-Path $Root "runtime\ui-data\logs"
New-Item -ItemType Directory -Force $LogDir | Out-Null
$OutLog = Join-Path $LogDir "ui.out.log"
$ErrLog = Join-Path $LogDir "ui.err.log"

Start-Process -FilePath $Python -ArgumentList @("-m", "app.app") -WorkingDirectory $Root -WindowStyle Hidden -RedirectStandardOutput $OutLog -RedirectStandardError $ErrLog
Write-Host "Started Local LLM UI on http://127.0.0.1:$Port"
Write-Host "Health: http://127.0.0.1:$Port/healthz"
