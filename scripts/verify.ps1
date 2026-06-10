param(
  [ValidateSet("test", "lint", "typecheck", "all")]
  [string]$Target = "all"
)

$ErrorActionPreference = "Stop"

function Run-Step($Name, $Command, $WorkingDirectory) {
  Write-Host "==> $Name"
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
  Run-Step "backend tests" "python -m pytest -q" "backend"
}

if ($Target -eq "lint" -or $Target -eq "all") {
  Run-Step "backend lint" "python -m ruff check src tests" "backend"
}

if ($Target -eq "typecheck" -or $Target -eq "all") {
  Run-Step "backend typecheck" "python -m mypy src" "backend"
  Run-Step "frontend typecheck" "npx --yes pnpm@9.15.4 typecheck" "frontend"
}