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
        spreadsheet_url="https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123",
        sheet_id="",
        reference=LarkSpreadsheetReference(
            spreadsheet_id="testSpreadsheetToken123",
            sheet_id="testSheet123",
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


class MissingCliStatusClient:
    def list_rows(self, spreadsheet_id: str, sheet_id: str) -> list[SpreadsheetSourceRow]:
        raise FileNotFoundError("lark-cli")


class PermissionStatusClient:
    def list_rows(self, spreadsheet_id: str, sheet_id: str) -> list[SpreadsheetSourceRow]:
        raise LarkCliError(
            "permission denied",
            error_type="permission_denied",
            permission_scopes=["sheets:spreadsheet:readonly"],
            console_url="https://open.feishu.cn/app",
        )


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
        "connector_mode": "cli",
        "connector_identity": "unknown",
        "connector_profile": "",
        "connector_auth_status": "unknown",
        "connector_token_status": "unknown",
        "connectivity_status": "not_checked",
        "error_message": "",
        "error_type": "",
        "permission_scopes": [],
        "console_url": "",
        "risk_action": "",
    }


def test_lark_spreadsheet_status_can_use_request_url_without_env_configuration(monkeypatch) -> None:
    client = TestClient(app)
    status_client = RecordingStatusClient()
    monkeypatch.setattr(routes, "spreadsheet_sync_client", None, raising=False)
    monkeypatch.setattr(routes, "spreadsheet_writeback_client", None, raising=False)
    monkeypatch.setattr(routes, "LarkSpreadsheetClient", lambda transport: status_client)
    routes.configure_spreadsheet_clients(LarkSpreadsheetSettings())

    response = client.get(
        "/spreadsheets/lark/status"
        "?check_connectivity=true"
        "&spreadsheet_url=https://example.larkoffice.com/sheets/spreadsheet-query?sheet=sheet-query"
        "&spreadsheet_id=spreadsheet-query"
        "&sheet_id=sheet-query"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is True
    assert body["spreadsheet_id"] == "spreadsheet-query"
    assert body["sheet_id"] == "sheet-query"
    assert body["connectivity_status"] == "ok"
    assert status_client.requested_spreadsheet_id == "spreadsheet-query"
    assert status_client.requested_sheet_id == "sheet-query"


def test_lark_spreadsheet_status_reports_configured_reference(monkeypatch) -> None:
    client = TestClient(app)
    routes.configure_spreadsheet_clients(
        LarkSpreadsheetSettings(
            spreadsheet_url="https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123",
            sheet_id="",
            lark_cli_timeout_seconds=9,
            reference=LarkSpreadsheetReference(
                spreadsheet_id="testSpreadsheetToken123",
                sheet_id="testSheet123",
            ),
        )
    )

    response = client.get("/spreadsheets/lark/status")

    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is True
    assert body["spreadsheet_id"] == "testSpreadsheetToken123"
    assert body["sheet_id"] == "testSheet123"
    assert body["lark_cli_timeout_seconds"] == 9
    assert body["connector_mode"] == "cli"
    assert body["connector_identity"] == "unknown"
    assert body["connectivity_status"] == "not_checked"
    assert body["error_message"] == ""


def test_lark_spreadsheet_status_can_check_connectivity(monkeypatch) -> None:
    client = TestClient(app)
    status_client = RecordingStatusClient()
    routes.configure_spreadsheet_clients(
        LarkSpreadsheetSettings(
            spreadsheet_url="https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123",
            sheet_id="",
            reference=LarkSpreadsheetReference(
                spreadsheet_id="testSpreadsheetToken123",
                sheet_id="testSheet123",
            ),
        )
    )
    monkeypatch.setattr(routes, "spreadsheet_sync_client", status_client, raising=False)

    response = client.get("/spreadsheets/lark/status?check_connectivity=true")

    assert response.status_code == 200
    body = response.json()
    assert body["connectivity_status"] == "ok"
    assert body["error_message"] == ""
    assert status_client.requested_spreadsheet_id == "testSpreadsheetToken123"
    assert status_client.requested_sheet_id == "testSheet123"


def test_lark_spreadsheet_status_reports_connectivity_failure(monkeypatch) -> None:
    client = TestClient(app)
    routes.configure_spreadsheet_clients(
        LarkSpreadsheetSettings(
            spreadsheet_url="https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123",
            sheet_id="",
            reference=LarkSpreadsheetReference(
                spreadsheet_id="testSpreadsheetToken123",
                sheet_id="testSheet123",
            ),
        )
    )
    monkeypatch.setattr(routes, "spreadsheet_sync_client", FailingStatusClient(), raising=False)

    response = client.get("/spreadsheets/lark/status?check_connectivity=true")

    assert response.status_code == 200
    body = response.json()
    assert body["connectivity_status"] == "failed"
    assert body["error_message"] == "permission denied"
    assert body["error_type"] == "cli_error"


def test_lark_spreadsheet_status_reports_structured_permission_failure(monkeypatch) -> None:
    client = TestClient(app)
    routes.configure_spreadsheet_clients(
        LarkSpreadsheetSettings(
            spreadsheet_url="https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123",
            sheet_id="",
            reference=LarkSpreadsheetReference(
                spreadsheet_id="testSpreadsheetToken123",
                sheet_id="testSheet123",
            ),
        )
    )
    monkeypatch.setattr(routes, "spreadsheet_sync_client", PermissionStatusClient(), raising=False)

    response = client.get("/spreadsheets/lark/status?check_connectivity=true")

    assert response.status_code == 200
    body = response.json()
    assert body["connectivity_status"] == "failed"
    assert body["error_type"] == "permission_denied"
    assert body["permission_scopes"] == ["sheets:spreadsheet:readonly"]
    assert body["console_url"] == "https://open.feishu.cn/app"


def test_lark_spreadsheet_status_reports_missing_cli_as_connectivity_failure(monkeypatch) -> None:
    client = TestClient(app)
    routes.configure_spreadsheet_clients(
        LarkSpreadsheetSettings(
            spreadsheet_url="https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123",
            sheet_id="",
            reference=LarkSpreadsheetReference(
                spreadsheet_id="testSpreadsheetToken123",
                sheet_id="testSheet123",
            ),
        )
    )
    monkeypatch.setattr(routes, "spreadsheet_sync_client", MissingCliStatusClient(), raising=False)

    response = client.get("/spreadsheets/lark/status?check_connectivity=true")

    assert response.status_code == 200
    body = response.json()
    assert body["connectivity_status"] == "failed"
    assert "lark-cli" in body["error_message"]
