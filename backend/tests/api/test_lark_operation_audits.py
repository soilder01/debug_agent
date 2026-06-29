from fastapi.testclient import TestClient

from debug_agent.api import routes
from debug_agent.main import app
from debug_agent.settings import LarkSpreadsheetSettings
from debug_agent.spreadsheets.lark import LarkSpreadsheetReference


def test_lark_operation_audit_api_filters_and_paginates() -> None:
    client = TestClient(app)
    routes.job_repository.save_lark_operation_audit(
        actor="local-dev-operator",
        connector_mode="cli",
        identity="bot",
        profile="debug-bot",
        service="sheets",
        operation="+csv-get",
        status="failed",
        context="+csv-get --spreadsheet-token sheet --sheet-id tab",
        error_type="permission_denied",
        hint="run lark-cli auth login",
        permission_scopes=["sheets:spreadsheet:readonly"],
        console_url="https://open.feishu.cn/app",
        duration_ms=11,
    )
    routes.job_repository.save_lark_operation_audit(
        actor="local-dev-operator",
        connector_mode="cli",
        identity="bot",
        profile="debug-bot",
        service="sheets",
        operation="+cells-set",
        status="succeeded",
        context="+cells-set --spreadsheet-token sheet --sheet-id tab",
        duration_ms=7,
    )

    response = client.get("/lark/operation-audits?status=failed&limit=1")

    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 1
    assert len(body["audits"]) == 1
    audit = body["audits"][0]
    assert audit["connector_mode"] == "cli"
    assert audit["identity"] == "bot"
    assert audit["profile"] == "debug-bot"
    assert audit["service"] == "sheets"
    assert audit["operation"] == "+csv-get"
    assert audit["status"] == "failed"
    assert audit["error_type"] == "permission_denied"
    assert audit["hint"] == "run lark-cli auth login"
    assert audit["permission_scopes"] == ["sheets:spreadsheet:readonly"]
    assert audit["console_url"] == "https://open.feishu.cn/app"
    assert audit["duration_ms"] == 11


def test_lark_scope_check_api_returns_requirements_and_recent_missing_scopes() -> None:
    client = TestClient(app)
    routes.job_repository.save_lark_operation_audit(
        actor="local-dev-operator",
        connector_mode="cli",
        identity="bot",
        profile="debug-bot",
        service="sheets",
        operation="+csv-get",
        status="failed",
        context="+csv-get --spreadsheet-token sheet --sheet-id tab",
        error_type="permission_denied",
        hint="run lark-cli auth login",
        permission_scopes=["sheets:spreadsheet:readonly"],
        console_url="https://open.feishu.cn/app",
        duration_ms=11,
    )

    response = client.get("/api/lark/scopes/check?service=sheets")

    assert response.status_code == 200
    body = response.json()
    assert body["connector_mode"] == "cli"
    assert body["auth_check_status"] == "not_verified"
    assert body["recent_missing_scopes"] == ["sheets:spreadsheet:readonly"]
    assert body["console_url"] == "https://open.larkoffice.com/app?lang=zh-CN"
    assert [requirement["operation"] for requirement in body["requirements"]] == ["+csv-get", "+cells-set"]
    read_requirement = body["requirements"][0]
    assert read_requirement["required_scopes"] == ["sheets:spreadsheet:readonly"]
    assert read_requirement["status"] == "missing_recently"
    assert read_requirement["recent_failure_count"] == 1
    write_requirement = body["requirements"][1]
    assert write_requirement["required_scopes"] == ["sheets:spreadsheet"]
    assert write_requirement["confirmation_required"] is True
    assert "not_verified" in body["repair_steps"][0]


def test_lark_auth_session_api_creates_fetches_and_completes_session() -> None:
    client = TestClient(app)

    create_response = client.post(
        "/api/lark/auth-sessions",
        json={
            "identity": "user",
            "profile": "debug-user",
            "scopes": ["sheets:spreadsheet:readonly"],
            "redirect_url": "https://debug-agent.local/lark/callback",
            "actor": "local-dev-operator",
            "note": "need user auth",
        },
    )

    assert create_response.status_code == 200
    created = create_response.json()
    assert created["identity"] == "user"
    assert created["profile"] == "debug-user"
    assert created["scopes"] == ["sheets:spreadsheet:readonly"]
    assert created["status"] == "pending"
    assert created["state"]
    assert "debug_agent_auth=1" in created["auth_url"]
    assert "state=" in created["auth_url"]
    assert "sheets%3Aspreadsheet%3Areadonly" in created["auth_url"]

    get_response = client.get(f"/api/lark/auth-sessions/{created['auth_session_id']}")

    assert get_response.status_code == 200
    assert get_response.json()["auth_session_id"] == created["auth_session_id"]

    complete_response = client.post(
        f"/api/lark/auth-sessions/{created['auth_session_id']}/complete",
        json={"actor": "local-dev-operator", "note": "authorization completed"},
    )

    assert complete_response.status_code == 200
    completed = complete_response.json()
    assert completed["status"] == "authorized"
    assert completed["completed_by"] == "local-dev-operator"
    assert completed["note"] == "authorization completed"
    assert completed["completed_at"]


def test_request_scoped_lark_client_wires_operation_audit_sink(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class CapturingTransport:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(routes, "LarkCliSheetsTransport", CapturingTransport)
    monkeypatch.setattr(routes, "LarkSpreadsheetClient", lambda transport: transport)

    client = routes._lark_client_for_settings(
        LarkSpreadsheetSettings(
            spreadsheet_url="https://example.larkoffice.com/sheets/spreadsheet-1?sheet=sheet-1",
            sheet_id="",
            lark_cli_profile="debug-bot",
            lark_cli_identity="bot",
            reference=LarkSpreadsheetReference(spreadsheet_id="spreadsheet-1", sheet_id="sheet-1"),
        )
    )

    assert client is not None
    assert captured["profile"] == "debug-bot"
    assert captured["identity"] == "bot"
    assert captured["audit_sink"] is routes._record_lark_connector_audit
