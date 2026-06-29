$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$dockerCliDir = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages\Docker.DockerCLI_Microsoft.Winget.Source_8wekyb3d8bbwe\docker"
if (Test-Path $dockerCliDir) {
    $env:PATH = "$dockerCliDir;$env:PATH"
}

docker compose --project-directory $repoRoot config --no-env-resolution --quiet
