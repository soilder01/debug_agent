from debug_agent.api import routes
from debug_agent.settings import LarkSpreadsheetSettings
from debug_agent.spreadsheets.lark import LarkSpreadsheetClient, LarkSpreadsheetReference


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
