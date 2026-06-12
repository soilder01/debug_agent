import json

from fastapi.testclient import TestClient

from debug_agent.api import routes
from debug_agent.main import app
from debug_agent.spreadsheets.lark import LarkCliError
from debug_agent.spreadsheets.sync import SpreadsheetSourceRow


class StaticSpreadsheetClient:
    def __init__(self, rows: list[SpreadsheetSourceRow]) -> None:
        self.rows = rows
        self.requested_spreadsheet_id = ""
        self.requested_sheet_id = ""

    def list_rows(self, spreadsheet_id: str, sheet_id: str) -> list[SpreadsheetSourceRow]:
        self.requested_spreadsheet_id = spreadsheet_id
        self.requested_sheet_id = sheet_id
        return self.rows


class FailingSpreadsheetClient:
    def list_rows(self, spreadsheet_id: str, sheet_id: str) -> list[SpreadsheetSourceRow]:
        raise LarkCliError("missing lark spreadsheet permission")


def test_spreadsheet_sync_api_imports_rows_creates_jobs_and_saves_mapping(monkeypatch) -> None:
    client = TestClient(app)
    golden_answer = {"answers": [{"box_id": 1, "student_answer": "42"}]}
    sync_client = StaticSpreadsheetClient(
        [
            SpreadsheetSourceRow(
                row_id="row-api-1",
                values={
                    "case_id": "synced-api-case-1",
                    "image_uri": "file://synced-api-case-1.png",
                    "prompt": "Read the answer",
                    "golden_answer_json": golden_answer,
                    "scoring_standard": "exact match",
                    "predictions_json": [
                        {"trial": 1, "raw_output": json.dumps(golden_answer), "score": 1},
                    ],
                    "avg_score": 1.0,
                },
            )
        ]
    )
    monkeypatch.setattr(routes, "spreadsheet_sync_client", sync_client, raising=False)

    response = client.post(
        "/spreadsheets/sync",
        json={
            "spreadsheet_id": "spreadsheet-api-1",
            "sheet_id": "sheet-api-1",
            "create_jobs": True,
            "baseline_trials": 5,
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert sync_client.requested_spreadsheet_id == "spreadsheet-api-1"
    assert sync_client.requested_sheet_id == "sheet-api-1"
    assert body["imported_case_ids"] == ["synced-api-case-1"]
    assert body["imported_rows"][0]["sheet_row_id"] == "row-api-1"
    assert body["rejected_rows"] == []
    assert len(body["jobs"]) == 1
    job_id = body["jobs"][0]["job_id"]
    mapping = routes.job_repository.get_spreadsheet_row_mapping_by_job_id(job_id)
    assert mapping is not None
    assert mapping.spreadsheet_id == "spreadsheet-api-1"
    assert mapping.sheet_id == "sheet-api-1"
    assert mapping.row_id == "row-api-1"
    assert mapping.case_id == "synced-api-case-1"


def test_spreadsheet_sync_api_returns_503_when_client_is_not_configured(monkeypatch) -> None:
    client = TestClient(app)
    monkeypatch.setattr(routes, "spreadsheet_sync_client", None, raising=False)

    response = client.post(
        "/spreadsheets/sync",
        json={
            "spreadsheet_id": "spreadsheet-api-1",
            "sheet_id": "sheet-api-1",
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Spreadsheet sync client is not configured"


def test_spreadsheet_sync_api_maps_lark_transport_failures(monkeypatch) -> None:
    client = TestClient(app)
    monkeypatch.setattr(routes, "spreadsheet_sync_client", FailingSpreadsheetClient(), raising=False)

    response = client.post(
        "/spreadsheets/sync",
        json={
            "spreadsheet_id": "spreadsheet-api-1",
            "sheet_id": "sheet-api-1",
        },
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Lark spreadsheet operation failed: missing lark spreadsheet permission"
