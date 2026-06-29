# ruff: noqa: F403,F405
from tests.scripts.common import *


def test_production_preflight_builds_passed_report() -> None:
    module = load_preflight_module()

    report = module.build_preflight_report(
        base_url="http://debug-agent.local/",
        endpoints={
            "health": {
                "ok": True,
                "status_code": 200,
                "payload": {"status": "ok", "service": "debug-agent-backend"},
            },
            "readiness": {"ok": True, "status_code": 200, "payload": {"level": "healthy"}},
            "artifact_retention": {
                "ok": True,
                "status_code": 200,
                "payload": {"eligible_file_count": 0, "eligible_size_bytes": 0},
            },
            "pilot_gate": {
                "ok": True,
                "status_code": 200,
                "payload": {
                    "status": "passed",
                    "batch_evidence": {"completed_jobs": 20, "best_batch_id": "batch-a"},
                },
            },
        },
    )

    assert report["base_url"] == "http://debug-agent.local"
    assert report["status"] == "passed"
    assert report["next_actions"] == []


def test_production_preflight_fails_on_critical_readiness() -> None:
    module = load_preflight_module()

    report = module.build_preflight_report(
        base_url="http://debug-agent.local",
        endpoints={
            "health": {"ok": True, "status_code": 200, "payload": {"status": "ok"}},
            "readiness": {"ok": True, "status_code": 200, "payload": {"level": "critical"}},
            "artifact_retention": {
                "ok": True,
                "status_code": 200,
                "payload": {"eligible_file_count": 0},
            },
            "pilot_gate": {"ok": True, "status_code": 200, "payload": {"status": "passed"}},
        },
    )

    assert report["status"] == "failed"
    assert any(
        check["key"] == "readiness" and check["status"] == "failed" for check in report["checks"]
    )


def test_production_preflight_returns_warning_exit_code_unless_allowed(monkeypatch) -> None:
    module = load_preflight_module()

    monkeypatch.setattr(
        module,
        "run_preflight",
        lambda base_url, timeout_seconds: {
            "status": "warning",
            "next_actions": ["Review artifact retention."],
        },
    )

    assert module.main(["--base-url", "http://debug-agent.local"]) == 1
    assert module.main(["--base-url", "http://debug-agent.local", "--allow-warning"]) == 0


def test_start_production_script_sets_safe_runtime_defaults() -> None:
    script = (SCRIPT_ROOT / "start-production.ps1").read_text(encoding="utf-8")

    assert "DEBUG_AGENT_ENVIRONMENT" in script
    assert "production-candidate" in script
    assert "DEBUG_AGENT_REQUIRE_TRUSTED_ACTOR" in script
    assert "DEBUG_AGENT_ARTIFACT_RETENTION_DAYS" in script
    assert "PYTHONPATH" in script
    assert "python -m uvicorn debug_agent.main:app" in script
    assert "Write-Host" not in script


def test_docker_compose_runs_backend_worker_and_lark_consumer() -> None:
    compose = (SCRIPT_ROOT.parents[0] / "docker-compose.yml").read_text(encoding="utf-8")

    assert "healthcheck:" in compose
    assert "worker:" in compose
    assert "python /app/scripts/run_debug_agent_worker.py" in compose
    assert "lark_bot_long_connection_consumer.py" in compose
    assert "condition: service_healthy" in compose
    assert "backend_artifacts:/app/backend/artifacts" in compose
    assert "restart: unless-stopped" in compose
    assert "LARK_BOT_ACTION_TOKEN_SECRET" in compose


def test_compose_config_check_avoids_env_secret_expansion() -> None:
    script = (SCRIPT_ROOT / "compose_config_check.ps1").read_text(encoding="utf-8")

    assert "docker compose" in script
    assert "--no-env-resolution" in script
    assert "--quiet" in script
    assert "--environment" not in script


def test_worker_runner_script_starts_and_stops_worker() -> None:
    script = (SCRIPT_ROOT / "run_debug_agent_worker.py").read_text(encoding="utf-8")

    assert "from debug_agent.api.routes import job_worker" in script
    assert "job_worker.start()" in script
    assert "await job_worker.stop()" in script
    assert "SIGTERM" in script
