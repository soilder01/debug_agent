param(
  [string]$HostAddress = "127.0.0.1",
  [int]$Port = 8000,
  [string]$Environment = "production-candidate",
  [string]$ArtifactDir = "",
  [string]$DatabaseUrl = "",
  [string]$ReportBaseUrl = "",
  [switch]$NoReload
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$BackendRoot = Join-Path $ProjectRoot "backend"
$BackendSrc = Join-Path $BackendRoot "src"

if (-not $env:DEBUG_AGENT_ENVIRONMENT) {
  $env:DEBUG_AGENT_ENVIRONMENT = $Environment
}

if ($ArtifactDir) {
  $env:DEBUG_AGENT_IMAGE_ARTIFACT_DIR = $ArtifactDir
}
elseif (-not $env:DEBUG_AGENT_IMAGE_ARTIFACT_DIR) {
  $env:DEBUG_AGENT_IMAGE_ARTIFACT_DIR = Join-Path $ProjectRoot "backend\artifacts"
}

if ($DatabaseUrl) {
  $env:DEBUG_AGENT_DATABASE_URL = $DatabaseUrl
}
elseif (-not $env:DEBUG_AGENT_DATABASE_URL) {
  $DatabasePath = Join-Path $env:DEBUG_AGENT_IMAGE_ARTIFACT_DIR "debug-agent.db"
  $env:DEBUG_AGENT_DATABASE_URL = "sqlite+pysqlite:///$($DatabasePath.Replace('\', '/'))"
}

if ($ReportBaseUrl) {
  $env:DEBUG_AGENT_REPORT_BASE_URL = $ReportBaseUrl
}
elseif (-not $env:DEBUG_AGENT_REPORT_BASE_URL) {
  $env:DEBUG_AGENT_REPORT_BASE_URL = "http://$HostAddress`:$Port"
}

if (-not $env:DEBUG_AGENT_REQUIRE_TRUSTED_ACTOR) {
  $env:DEBUG_AGENT_REQUIRE_TRUSTED_ACTOR = "1"
}

if (-not $env:DEBUG_AGENT_ARTIFACT_RETENTION_DAYS) {
  $env:DEBUG_AGENT_ARTIFACT_RETENTION_DAYS = "30"
}

if (-not $env:PYTHONPATH) {
  $env:PYTHONPATH = $BackendSrc
}
elseif ($env:PYTHONPATH -notlike "*$BackendSrc*") {
  $env:PYTHONPATH = "$BackendSrc;$env:PYTHONPATH"
}

New-Item -ItemType Directory -Force -Path $env:DEBUG_AGENT_IMAGE_ARTIFACT_DIR | Out-Null

[Console]::WriteLine("==> Debug Agent production-candidate backend")
[Console]::WriteLine("    environment: $env:DEBUG_AGENT_ENVIRONMENT")
[Console]::WriteLine("    database: $env:DEBUG_AGENT_DATABASE_URL")
[Console]::WriteLine("    artifacts: $env:DEBUG_AGENT_IMAGE_ARTIFACT_DIR")
[Console]::WriteLine("    report base url: $env:DEBUG_AGENT_REPORT_BASE_URL")

Push-Location $BackendRoot
try {
  $ReloadFlag = if ($NoReload) { "" } else { " --reload" }
  Invoke-Expression "python -m uvicorn debug_agent.main:app --host $HostAddress --port $Port$ReloadFlag"
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
  Pop-Location
}
