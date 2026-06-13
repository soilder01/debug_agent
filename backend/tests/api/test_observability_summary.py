from fastapi.testclient import TestClient

from debug_agent.api.routes import job_repository
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
    assert body["worker"]["running"] is False
    assert body["worker"]["auto_writeback_enabled"] is False
    assert body["worker"]["completion_hook_enabled"] is False

    job_repository.mark_failed(created["job_id"], "test cleanup")
