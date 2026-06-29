# ruff: noqa: F403,F405
from tests.scripts.common import *


def test_pilot_validation_record_writes_evidence_and_markdown(tmp_path, monkeypatch) -> None:
    module = load_pilot_record_module()

    def fake_fetch_bytes(base_url, path, timeout_seconds):
        payloads = {
            "/api/operations/readiness": {"level": "healthy"},
            "/api/operations/pilot-gate": {
                "status": "passed",
                "thresholds": {"min_completed_jobs": 20, "min_success_rate": 0.8},
                "batch_evidence": {
                    "completed_jobs": 24,
                    "best_batch_id": "batch-a",
                    "best_success_rate": 0.92,
                    "best_p95_duration_ms": 9000,
                    "best_estimated_cost_units": 12.5,
                },
            },
            "/api/operations/artifact-retention": {"eligible_file_count": 0},
            "/api/debug-batches/comparison?batch_ids=batch-a%2Cbatch-b": {
                "best_batch_id": "batch-a",
                "batch_ids": ["batch-a", "batch-b"],
                "items": [
                    {
                        "batch_id": "batch-a",
                        "model_profile": "公平复测=seedpro",
                        "model_runner_locked": True,
                    }
                ],
            },
        }
        if path == "/api/debug-batches/comparison.csv?batch_ids=batch-a%2Cbatch-b":
            content = b"batch_id,success_rate\nbatch-a,0.92\n"
        else:
            content = json_bytes(payloads[path])
        return {
            "ok": True,
            "status_code": 200,
            "url": f"{base_url}{path}",
            "content": content,
            "error": "",
        }

    monkeypatch.setattr(module, "fetch_bytes", fake_fetch_bytes)

    record = module.collect_validation_record(
        base_url="http://debug-agent.local",
        output_dir=tmp_path,
        batch_ids=["batch-a", "batch-b"],
        operator="ops-reviewer",
        environment="pilot",
        timeout_seconds=1,
        include_support_bundle=False,
        include_database_backup=False,
    )

    assert record["summary"]["status"] == "passed"
    assert record["summary"]["best_batch_id"] == "batch-a"
    assert (tmp_path / "readiness.json").exists()
    assert (tmp_path / "pilot_gate.json").exists()
    assert (tmp_path / "batch_comparison.csv").read_text(encoding="utf-8").startswith("batch_id")
    markdown = (tmp_path / "pilot-validation-record.md").read_text(encoding="utf-8")
    assert "Operator: ops-reviewer" in markdown
    assert "Model configuration summary: 公平复测=seedpro" in markdown


def test_pilot_validation_record_returns_failed_exit_code(monkeypatch, tmp_path) -> None:
    module = load_pilot_record_module()

    monkeypatch.setattr(
        module,
        "collect_validation_record",
        lambda **kwargs: {
            "summary": {"status": "failed"},
            "record_path": str(tmp_path / "pilot-validation-record.md"),
        },
    )

    assert (
        module.main(["--base-url", "http://debug-agent.local", "--output-dir", str(tmp_path)]) == 1
    )


def test_pilot_validation_record_allows_warning_when_requested(monkeypatch, tmp_path) -> None:
    module = load_pilot_record_module()

    monkeypatch.setattr(
        module,
        "collect_validation_record",
        lambda **kwargs: {
            "summary": {"status": "warning"},
            "record_path": str(tmp_path / "pilot-validation-record.md"),
        },
    )

    assert (
        module.main(["--base-url", "http://debug-agent.local", "--output-dir", str(tmp_path)]) == 1
    )
    assert (
        module.main(
            [
                "--base-url",
                "http://debug-agent.local",
                "--output-dir",
                str(tmp_path),
                "--allow-warning",
            ]
        )
        == 0
    )


def test_pilot_validation_record_serializes_failed_download_result() -> None:
    module = load_pilot_record_module()

    result = module._serializable_result(
        {
            "ok": False,
            "status_code": 0,
            "url": "http://debug-agent.local/api/operations/readiness",
            "content": b"raw bytes",
            "error": "connection refused",
        }
    )

    assert result == {
        "ok": False,
        "status_code": 0,
        "url": "http://debug-agent.local/api/operations/readiness",
        "content_length": 9,
        "error": "connection refused",
    }
