from fastapi.testclient import TestClient

from debug_agent.api import routes
from debug_agent.main import app
from debug_agent.spreadsheets.lark import LarkCliError


class RecordingWritebackClient:
    def __init__(self) -> None:
        self.spreadsheet_id = ""
        self.sheet_id = ""
        self.row_id = ""
        self.fields: dict[str, str] = {}

    def update_row(self, spreadsheet_id: str, sheet_id: str, row_id: str, fields: dict[str, str]) -> None:
        self.spreadsheet_id = spreadsheet_id
        self.sheet_id = sheet_id
        self.row_id = row_id
        self.fields = fields


class FailingWritebackClient:
    def update_row(self, spreadsheet_id: str, sheet_id: str, row_id: str, fields: dict[str, str]) -> None:
        raise LarkCliError("sheet header not found")


def test_job_report_writeback_api_updates_mapped_spreadsheet_row(monkeypatch) -> None:
    client = TestClient(app)
    writeback_client = RecordingWritebackClient()
    monkeypatch.setattr(routes, "spreadsheet_writeback_client", writeback_client, raising=False)
    submit_response = client.post("/cases/handwrite233/debug-jobs?auto_run=true&baseline_trials=5")
    assert submit_response.status_code == 202
    job_id = submit_response.json()["job_id"]
    routes.job_repository.save_spreadsheet_row_mapping(
        spreadsheet_id="spreadsheet-1",
        sheet_id="sheet-1",
        row_id="row-42",
        case_id="handwrite233",
        job_id=job_id,
    )

    response = client.post(
        f"/jobs/{job_id}/spreadsheet-writeback",
        json={"report_url": f"https://debug-agent.local/jobs/{job_id}/report"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["row_id"] == "row-42"
    assert body["fields"]["分析报告链接"] == f"https://debug-agent.local/jobs/{job_id}/report"
    assert body["fields"]["错误原因"].startswith("模型无法稳定识别涂改后的最终答案")
    assert writeback_client.spreadsheet_id == "spreadsheet-1"
    assert writeback_client.sheet_id == "sheet-1"
    assert writeback_client.row_id == "row-42"
    assert writeback_client.fields == body["fields"]
    audit = routes.job_repository.get_spreadsheet_writeback_audit(job_id)
    assert audit is not None
    assert audit.status == "succeeded"
    assert audit.row_id == "row-42"
    assert audit.report_url == f"https://debug-agent.local/jobs/{job_id}/report"
    assert audit.fields == body["fields"]


def test_job_report_writeback_api_returns_404_when_mapping_is_missing(monkeypatch) -> None:
    client = TestClient(app)
    monkeypatch.setattr(routes, "spreadsheet_writeback_client", RecordingWritebackClient(), raising=False)
    submit_response = client.post("/cases/handwrite233/debug-jobs?auto_run=true&baseline_trials=5")
    assert submit_response.status_code == 202
    job_id = submit_response.json()["job_id"]

    response = client.post(
        f"/jobs/{job_id}/spreadsheet-writeback",
        json={"report_url": f"https://debug-agent.local/jobs/{job_id}/report"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == f"Spreadsheet row mapping not found for job: {job_id}"


def test_job_report_writeback_api_returns_503_when_client_is_not_configured(monkeypatch) -> None:
    client = TestClient(app)
    monkeypatch.setattr(routes, "spreadsheet_writeback_client", None, raising=False)
    submit_response = client.post("/cases/handwrite233/debug-jobs?auto_run=true&baseline_trials=5")
    assert submit_response.status_code == 202
    job_id = submit_response.json()["job_id"]

    response = client.post(
        f"/jobs/{job_id}/spreadsheet-writeback",
        json={"report_url": f"https://debug-agent.local/jobs/{job_id}/report"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Spreadsheet writeback client is not configured"


def test_job_report_writeback_api_maps_lark_transport_failures(monkeypatch) -> None:
    client = TestClient(app)
    monkeypatch.setattr(routes, "spreadsheet_writeback_client", FailingWritebackClient(), raising=False)
    submit_response = client.post("/cases/handwrite233/debug-jobs?auto_run=true&baseline_trials=5")
    assert submit_response.status_code == 202
    job_id = submit_response.json()["job_id"]
    routes.job_repository.save_spreadsheet_row_mapping(
        spreadsheet_id="spreadsheet-1",
        sheet_id="sheet-1",
        row_id="7",
        case_id="handwrite233",
        job_id=job_id,
    )

    response = client.post(
        f"/jobs/{job_id}/spreadsheet-writeback",
        json={"report_url": f"https://debug-agent.local/jobs/{job_id}/report"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Lark spreadsheet operation failed: sheet header not found"
    audit = routes.job_repository.get_spreadsheet_writeback_audit(job_id)
    assert audit is not None
    assert audit.status == "failed"
    assert audit.row_id == "7"
    assert audit.report_url == f"https://debug-agent.local/jobs/{job_id}/report"
    assert audit.error_message == "sheet header not found"


def test_job_report_writeback_audit_api_returns_latest_audit() -> None:
    client = TestClient(app)
    routes.job_repository.save_spreadsheet_writeback_audit(
        job_id="job-audit-api",
        status="succeeded",
        row_id="7",
        report_url="https://debug-agent.local/jobs/job-audit-api/report",
        fields={"错误原因": "模型无法稳定识别涂改后的最终答案。"},
        error_message="",
    )

    response = client.get("/jobs/job-audit-api/spreadsheet-writeback/audit")

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == "job-audit-api"
    assert body["status"] == "succeeded"
    assert body["row_id"] == "7"
    assert body["report_url"] == "https://debug-agent.local/jobs/job-audit-api/report"
    assert body["fields"] == {"错误原因": "模型无法稳定识别涂改后的最终答案。"}
    assert body["error_message"] == ""
    assert body["updated_at"]


def test_job_report_writeback_audit_api_returns_404_when_missing() -> None:
    client = TestClient(app)

    response = client.get("/jobs/missing-audit/spreadsheet-writeback/audit")

    assert response.status_code == 404
    assert response.json()["detail"] == "Spreadsheet writeback audit not found for job: missing-audit"


def test_spreadsheet_writeback_audit_summary_api_counts_statuses() -> None:
    client = TestClient(app)
    routes.job_repository.save_spreadsheet_writeback_audit(
        job_id="summary-success",
        status="succeeded",
        row_id="7",
        report_url="https://debug-agent.local/jobs/summary-success/report",
        fields={},
        error_message="",
    )
    routes.job_repository.save_spreadsheet_writeback_audit(
        job_id="summary-failed",
        status="failed",
        row_id="8",
        report_url="https://debug-agent.local/jobs/summary-failed/report",
        fields={},
        error_message="permission denied",
    )

    response = client.get("/spreadsheets/writeback/audits/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["by_status"]["succeeded"] >= 1
    assert body["by_status"]["failed"] >= 1
    assert body["total_count"] >= 2


def test_spreadsheet_writeback_audit_list_api_filters_and_paginates() -> None:
    client = TestClient(app)
    for job_id, status in [
        ("list-success", "succeeded"),
        ("list-failed-1", "failed-list-test"),
        ("list-failed-2", "failed-list-test"),
    ]:
        routes.job_repository.save_spreadsheet_writeback_audit(
            job_id=job_id,
            status=status,
            row_id=job_id,
            report_url=f"https://debug-agent.local/jobs/{job_id}/report",
            fields={"job": job_id},
            error_message="permission denied" if status == "failed-list-test" else "",
        )

    response = client.get("/spreadsheets/writeback/audits?status=failed-list-test&limit=1&offset=1")

    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 2
    assert len(body["audits"]) == 1
    assert body["audits"][0]["status"] == "failed-list-test"
    assert body["audits"][0]["job_id"] == "list-failed-1"
    assert body["audits"][0]["fields"] == {"job": "list-failed-1"}
