from pathlib import Path


def test_verify_script_runs_backend_tests_with_safe_model_defaults() -> None:
    script = Path(__file__).parents[2] / "scripts" / "verify.ps1"
    content = script.read_text(encoding="utf-8")

    assert '$env:DEBUG_AGENT_MODEL_PROVIDER="fake"' in content
    assert '$env:DEBUG_AGENT_ENABLE_LIVE_MODEL_TESTS="0"' in content


def test_verify_script_reports_slow_backend_tests() -> None:
    script = Path(__file__).parents[2] / "scripts" / "verify.ps1"
    content = script.read_text(encoding="utf-8")

    assert "python -m pytest -ra --durations=20" in content


def test_verify_script_avoids_powershell_host_serialization_noise() -> None:
    script = Path(__file__).parents[2] / "scripts" / "verify.ps1"
    content = script.read_text(encoding="utf-8")

    assert "Write-Host" not in content
    assert '[Console]::WriteLine("==> $Name")' in content
