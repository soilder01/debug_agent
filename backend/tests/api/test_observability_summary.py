from fastapi.testclient import TestClient

from debug_agent.api.routes import job_repository
from debug_agent.experiments.runner import ExperimentEvidence
from debug_agent.judging.runner import JudgeResult
from debug_agent.main import app


def test_observability_summary_reports_runtime_and_operational_counts() -> None:
    client = TestClient(app)
    created = client.post("/cases/handwrite233/debug-jobs").json()
    failed = client.post("/cases/handwrite233/debug-jobs").json()
    job_repository.mark_failed(failed["job_id"], "forced failure for observability test")
    job_repository.save_spreadsheet_writeback_audit(
        job_id=failed["job_id"],
        status="failed",
        row_id="7",
        report_url=f"https://debug-agent.local/jobs/{failed['job_id']}/report",
        fields={},
        error_message="permission denied",
    )
    job_repository.save_evidence(
        job_id=failed["job_id"],
        case_id=failed["case_id"],
        evidence=[
            ExperimentEvidence(
                evidence_id="observability-evidence-1",
                step_name="baseline_replay",
                trial=0,
                latency_ms=120,
                response_parse_error="",
                model_call_error_type="",
                raw_output="{}",
                judge=JudgeResult(score=0, reasons=["wrong answer"]),
            ),
            ExperimentEvidence(
                evidence_id="observability-evidence-2",
                step_name="localized_observation",
                trial=1,
                latency_ms=80,
                response_parse_error="invalid json",
                model_call_error_type="TimeoutError",
                model_call_error_message="request timed out",
                raw_output="not-json",
                judge=JudgeResult(score=0, reasons=["model_call_error"]),
            ),
        ],
    )

    response = client.get("/observability/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["jobs"]["total_count"] >= 2
    assert body["jobs"]["by_status"]["created"] >= 1
    assert body["jobs"]["by_status"]["failed"] >= 1
    assert body["jobs"]["pending_count"] == body["jobs"]["by_status"]["created"]
    assert body["jobs"]["failed_count"] == body["jobs"]["by_status"]["failed"]
    assert body["writeback_audits"]["total_count"] >= 1
    assert body["writeback_audits"]["by_status"]["failed"] >= 1
    assert body["evidence"]["total_evidence"] >= 2
    assert body["evidence"]["failed_judgements"] >= 2
    assert body["evidence"]["response_parse_errors"] >= 1
    assert body["evidence"]["model_call_errors"] >= 1
    assert body["evidence"]["average_latency_ms"] >= 0
    assert body["worker"]["running"] is False
    assert body["worker"]["auto_writeback_enabled"] is False
    assert body["worker"]["completion_hook_enabled"] is False
    assert body["health"]["level"] == "critical"
    assert "failed jobs present" in body["health"]["reasons"]
    assert "failed spreadsheet writebacks present" in body["health"]["reasons"]
    assert "model call errors present" in body["health"]["reasons"]
    assert "Inspect failed jobs and open their evidence chain." in body["health"]["actions"]
    assert "Retry failed spreadsheet writebacks after checking Lark permissions and sheet headers." in body["health"][
        "actions"
    ]
    assert "Check model endpoint health, timeout settings, and retry affected jobs." in body["health"]["actions"]

    job_repository.mark_failed(created["job_id"], "test cleanup")
