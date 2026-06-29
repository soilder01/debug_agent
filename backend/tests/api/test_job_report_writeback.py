from fastapi.testclient import TestClient

from debug_agent.api import routes
from debug_agent.main import app
from debug_agent.settings import LarkSpreadsheetSettings
from debug_agent.spreadsheets.lark import LarkCliError, LarkSpreadsheetReference


class RecordingWritebackClient:
    def __init__(self) -> None:
        self.spreadsheet_id = ""
        self.sheet_id = ""
        self.row_id = ""
        self.fields: dict[str, str] = {}
        self.update_count = 0

    def update_row(self, spreadsheet_id: str, sheet_id: str, row_id: str, fields: dict[str, str]) -> None:
        self.update_count += 1
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
    assert body["fields"]["错误原因"].startswith("结构化评分显示")
    assert "student_answer_mismatch" in body["fields"]["错误原因"]
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
    assert writeback_client.update_count == 1


def test_job_report_writeback_api_is_idempotent_after_success(monkeypatch) -> None:
    client = TestClient(app)
    writeback_client = RecordingWritebackClient()
    monkeypatch.setattr(routes, "spreadsheet_writeback_client", writeback_client, raising=False)
    submit_response = client.post("/cases/handwrite233/debug-jobs?auto_run=true&baseline_trials=5")
    assert submit_response.status_code == 202
    job_id = submit_response.json()["job_id"]
    report_url = f"https://debug-agent.local/jobs/{job_id}/report"
    routes.job_repository.save_spreadsheet_row_mapping(
        spreadsheet_id="spreadsheet-1",
        sheet_id="sheet-1",
        row_id="row-42",
        case_id="handwrite233",
        job_id=job_id,
    )

    first_response = client.post(f"/jobs/{job_id}/spreadsheet-writeback", json={"report_url": report_url})
    second_response = client.post(f"/jobs/{job_id}/spreadsheet-writeback", json={"report_url": report_url})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json() == first_response.json()
    assert writeback_client.update_count == 1
    audit = routes.job_repository.get_spreadsheet_writeback_audit(job_id)
    assert audit is not None
    assert audit.status == "succeeded"
    assert audit.report_url == report_url


def test_job_report_writeback_requires_confirmation_when_requested(monkeypatch) -> None:
    client = TestClient(app)
    writeback_client = RecordingWritebackClient()
    monkeypatch.setattr(routes, "spreadsheet_writeback_client", writeback_client, raising=False)
    submit_response = client.post("/cases/handwrite233/debug-jobs?auto_run=true&baseline_trials=5")
    assert submit_response.status_code == 202
    job_id = submit_response.json()["job_id"]
    report_url = f"https://debug-agent.local/jobs/{job_id}/report"
    routes.job_repository.save_spreadsheet_row_mapping(
        spreadsheet_id="spreadsheet-1",
        sheet_id="sheet-1",
        row_id="row-42",
        case_id="handwrite233",
        job_id=job_id,
    )

    response = client.post(
        f"/jobs/{job_id}/spreadsheet-writeback",
        json={"report_url": report_url, "require_confirmation": True},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["type"] == "lark_write_confirmation_required"
    assert response.json()["detail"]["risk_action"] == "sheets +cells-set"
    assert writeback_client.update_count == 0


def test_job_report_writeback_succeeds_with_confirmed_lark_write_confirmation(monkeypatch) -> None:
    client = TestClient(app)
    writeback_client = RecordingWritebackClient()
    monkeypatch.setattr(routes, "spreadsheet_writeback_client", writeback_client, raising=False)
    submit_response = client.post("/cases/handwrite233/debug-jobs?auto_run=true&baseline_trials=5")
    assert submit_response.status_code == 202
    job_id = submit_response.json()["job_id"]
    report_url = f"https://debug-agent.local/jobs/{job_id}/report"
    routes.job_repository.save_spreadsheet_row_mapping(
        spreadsheet_id="spreadsheet-1",
        sheet_id="sheet-1",
        row_id="row-42",
        case_id="handwrite233",
        job_id=job_id,
    )

    confirmation_response = client.post(
        f"/jobs/{job_id}/spreadsheet-writeback/confirmation",
        json={"report_url": report_url, "actor": "qa-operator", "note": "reviewed target row"},
    )
    assert confirmation_response.status_code == 200
    confirmation = confirmation_response.json()
    assert confirmation["status"] == "pending"
    assert confirmation["actor"] == "qa-operator"
    assert confirmation["service"] == "sheets"
    assert confirmation["operation"] == "+cells-set"
    assert confirmation["required_scopes"] == ["sheets:spreadsheet"]
    assert "spreadsheet-1/sheet-1" in confirmation["resource_summary"]

    blocked_response = client.post(
        f"/jobs/{job_id}/spreadsheet-writeback",
        json={
            "report_url": report_url,
            "require_confirmation": True,
            "confirmation_id": confirmation["confirmation_id"],
        },
    )
    assert blocked_response.status_code == 409
    assert blocked_response.json()["detail"]["type"] == "lark_write_confirmation_not_confirmed"

    confirm_response = client.post(
        f"/lark/write-confirmations/{confirmation['confirmation_id']}/confirm",
        json={"actor": "qa-operator", "note": "confirmed write risk"},
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["status"] == "confirmed"
    assert confirm_response.json()["confirmed_by"] == "qa-operator"

    write_response = client.post(
        f"/jobs/{job_id}/spreadsheet-writeback",
        json={
            "report_url": report_url,
            "require_confirmation": True,
            "confirmation_id": confirmation["confirmation_id"],
        },
    )

    assert write_response.status_code == 200
    assert write_response.json()["row_id"] == "row-42"
    assert writeback_client.update_count == 1


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


def test_job_report_writeback_api_recovers_failed_audit_mapping_from_current_lark_reference(monkeypatch) -> None:
    client = TestClient(app)
    writeback_client = RecordingWritebackClient()
    monkeypatch.setattr(routes, "spreadsheet_writeback_client", writeback_client, raising=False)
    monkeypatch.setattr(
        routes,
        "lark_spreadsheet_settings",
        LarkSpreadsheetSettings(
            spreadsheet_url="https://example.larkoffice.com/sheets/spreadsheet-retry?sheet=sheet-retry",
            sheet_id="sheet-retry",
            reference=LarkSpreadsheetReference(spreadsheet_id="spreadsheet-retry", sheet_id="sheet-retry"),
        ),
        raising=False,
    )
    submit_response = client.post("/cases/handwrite233/debug-jobs?auto_run=true&baseline_trials=5")
    assert submit_response.status_code == 202
    job_id = submit_response.json()["job_id"]
    report_url = f"https://debug-agent.local/jobs/{job_id}/report"
    routes.job_repository.save_spreadsheet_writeback_audit(
        job_id=job_id,
        status="failed",
        row_id="row-7",
        report_url=report_url,
        fields={},
        error_message="Spreadsheet header not found: 影响目标",
    )

    response = client.post(f"/jobs/{job_id}/spreadsheet-writeback", json={"report_url": report_url})

    assert response.status_code == 200
    body = response.json()
    assert body["row_id"] == "row-7"
    assert writeback_client.spreadsheet_id == "spreadsheet-retry"
    assert writeback_client.sheet_id == "sheet-retry"
    assert writeback_client.row_id == "row-7"
    mapping = routes.job_repository.get_spreadsheet_row_mapping_by_job_id(job_id)
    assert mapping is not None
    assert mapping.spreadsheet_id == "spreadsheet-retry"
    audit = routes.job_repository.get_spreadsheet_writeback_audit(job_id)
    assert audit is not None
    assert audit.status == "succeeded"
    assert audit.fields == body["fields"]


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


def test_spreadsheet_writeback_audit_list_api_filters_and_paginates(monkeypatch) -> None:
    client = TestClient(app)
    timestamps = iter(
        [
            "2026-06-12T00:00:00.000001+00:00",
            "2026-06-12T00:00:00.000002+00:00",
            "2026-06-12T00:00:00.000003+00:00",
        ]
    )
    monkeypatch.setattr("debug_agent.storage.repository._utc_now_iso", lambda: next(timestamps))
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
