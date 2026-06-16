param(
  [ValidateSet("test", "lint", "typecheck", "all")]
  [string]$Target = "all"
)

$ErrorActionPreference = "Stop"

function Run-Step($Name, $Command, $WorkingDirectory) {
  [Console]::WriteLine("==> $Name")
  Push-Location $WorkingDirectory
  try {
    Invoke-Expression $Command
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  }
  finally {
    Pop-Location
  }
}

if ($Target -eq "test" -or $Target -eq "all") {
  Run-Step "backend tests" '$env:DEBUG_AGENT_MODEL_PROVIDER="fake"; $env:DEBUG_AGENT_ENABLE_LIVE_MODEL_TESTS="0"; python -m pytest -ra --durations=20' "backend"
  Run-Step "frontend tests" "npx --yes pnpm@9.15.4 test -- --run" "frontend"
}

if ($Target -eq "lint" -or $Target -eq "all") {
  Run-Step "backend lint" "python -m ruff check src tests" "backend"
  Run-Step "frontend lint" "npx --yes pnpm@9.15.4 lint" "frontend"
}

if ($Target -eq "typecheck" -or $Target -eq "all") {
  Run-Step "backend typecheck" "python -m mypy src" "backend"
  Run-Step "frontend typecheck" "npx --yes pnpm@9.15.4 typecheck" "frontend"
}
