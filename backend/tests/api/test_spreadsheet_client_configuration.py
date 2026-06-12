from fastapi.testclient import TestClient

from debug_agent.api import routes
from debug_agent.main import app
from debug_agent.settings import LarkSpreadsheetSettings
from debug_agent.spreadsheets.lark import LarkCliError, LarkSpreadsheetClient, LarkSpreadsheetReference
from debug_agent.spreadsheets.sync import SpreadsheetSourceRow


def test_configure_spreadsheet_clients_wires_lark_client_when_reference_exists(monkeypatch) -> None:
    monkeypatch.setattr(routes, "spreadsheet_sync_client", None, raising=False)
    monkeypatch.setattr(routes, "spreadsheet_writeback_client", None, raising=False)
    lark_settings = LarkSpreadsheetSettings(
        spreadsheet_url="https://bytedance.larkoffice.com/sheets/NLews6C2ShValptV7IdcJ62tnWc?sheet=qJAomX",
        sheet_id="",
        reference=LarkSpreadsheetReference(
            spreadsheet_id="NLews6C2ShValptV7IdcJ62tnWc",
            sheet_id="qJAomX",
        ),
    )

    routes.configure_spreadsheet_clients(lark_settings)

    assert isinstance(routes.spreadsheet_sync_client, LarkSpreadsheetClient)
    assert routes.spreadsheet_writeback_client is routes.spreadsheet_sync_client


def test_configure_spreadsheet_clients_leaves_clients_unset_without_reference(monkeypatch) -> None:
    monkeypatch.setattr(routes, "spreadsheet_sync_client", None, raising=False)
    monkeypatch.setattr(routes, "spreadsheet_writeback_client", None, raising=False)

    routes.configure_spreadsheet_clients(LarkSpreadsheetSettings())

    assert routes.spreadsheet_sync_client is None
    assert routes.spreadsheet_writeback_client is None


class RecordingStatusClient:
    def __init__(self) -> None:
        self.requested_spreadsheet_id = ""
        self.requested_sheet_id = ""

    def list_rows(self, spreadsheet_id: str, sheet_id: str) -> list[SpreadsheetSourceRow]:
        self.requested_spreadsheet_id = spreadsheet_id
        self.requested_sheet_id = sheet_id
        return []


class FailingStatusClient:
    def list_rows(self, spreadsheet_id: str, sheet_id: str) -> list[SpreadsheetSourceRow]:
        raise LarkCliError("permission denied")


def test_lark_spreadsheet_status_reports_unconfigured(monkeypatch) -> None:
    client = TestClient(app)
    monkeypatch.setattr(routes, "spreadsheet_sync_client", None, raising=False)
    monkeypatch.setattr(routes, "spreadsheet_writeback_client", None, raising=False)
    routes.configure_spreadsheet_clients(LarkSpreadsheetSettings())

    response = client.get("/spreadsheets/lark/status")

    assert response.status_code == 200
    assert response.json() == {
        "configured": False,
        "spreadsheet_id": "",
        "sheet_id": "",
        "lark_cli_timeout_seconds": 60,
        "connectivity_status": "not_checked",
        "error_message": "",
    }


def test_lark_spreadsheet_status_reports_configured_reference(monkeypatch) -> None:
    client = TestClient(app)
    routes.configure_spreadsheet_clients(
        LarkSpreadsheetSettings(
            spreadsheet_url="https://bytedance.larkoffice.com/sheets/NLews6C2ShValptV7IdcJ62tnWc?sheet=qJAomX",
            sheet_id="",
            lark_cli_timeout_seconds=9,
            reference=LarkSpreadsheetReference(
                spreadsheet_id="NLews6C2ShValptV7IdcJ62tnWc",
                sheet_id="qJAomX",
            ),
        )
    )

    response = client.get("/spreadsheets/lark/status")

    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is True
    assert body["spreadsheet_id"] == "NLews6C2ShValptV7IdcJ62tnWc"
    assert body["sheet_id"] == "qJAomX"
    assert body["lark_cli_timeout_seconds"] == 9
    assert body["connectivity_status"] == "not_checked"
    assert body["error_message"] == ""


def test_lark_spreadsheet_status_can_check_connectivity(monkeypatch) -> None:
    client = TestClient(app)
    status_client = RecordingStatusClient()
    routes.configure_spreadsheet_clients(
        LarkSpreadsheetSettings(
            spreadsheet_url="https://bytedance.larkoffice.com/sheets/NLews6C2ShValptV7IdcJ62tnWc?sheet=qJAomX",
            sheet_id="",
            reference=LarkSpreadsheetReference(
                spreadsheet_id="NLews6C2ShValptV7IdcJ62tnWc",
                sheet_id="qJAomX",
            ),
        )
    )
    monkeypatch.setattr(routes, "spreadsheet_sync_client", status_client, raising=False)

    response = client.get("/spreadsheets/lark/status?check_connectivity=true")

    assert response.status_code == 200
    body = response.json()
    assert body["connectivity_status"] == "ok"
    assert body["error_message"] == ""
    assert status_client.requested_spreadsheet_id == "NLews6C2ShValptV7IdcJ62tnWc"
    assert status_client.requested_sheet_id == "qJAomX"


def test_lark_spreadsheet_status_reports_connectivity_failure(monkeypatch) -> None:
    client = TestClient(app)
    routes.configure_spreadsheet_clients(
        LarkSpreadsheetSettings(
            spreadsheet_url="https://bytedance.larkoffice.com/sheets/NLews6C2ShValptV7IdcJ62tnWc?sheet=qJAomX",
            sheet_id="",
            reference=LarkSpreadsheetReference(
                spreadsheet_id="NLews6C2ShValptV7IdcJ62tnWc",
                sheet_id="qJAomX",
            ),
        )
    )
    monkeypatch.setattr(routes, "spreadsheet_sync_client", FailingStatusClient(), raising=False)

    response = client.get("/spreadsheets/lark/status?check_connectivity=true")

    assert response.status_code == 200
    body = response.json()
    assert body["connectivity_status"] == "failed"
    assert body["error_message"] == "permission denied"
