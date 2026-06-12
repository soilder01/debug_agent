from fastapi.testclient import TestClient

from debug_agent.api import routes
from debug_agent.main import app


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
