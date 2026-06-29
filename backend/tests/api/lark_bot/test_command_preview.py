# ruff: noqa: F403,F405
from tests.api.lark_bot.common import *


def test_lark_bot_command_preview_maps_pilot_gate_and_records_audit() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/lark/bot/commands/preview",
        json={
            "text": "/debug pilot-gate",
            "actor": "ops-reviewer",
            "open_id": "ou_1",
            "chat_id": "oc_1",
            "identity": "bot",
            "profile": "debug-bot",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["action"]["kind"] == "pilot_gate"
    assert body["action"]["path"] == "/api/operations/pilot-gate"
    assert body["card"]["title"] == "试点准入评估"
    assert body["audit"]["actor"] == "ops-reviewer"
    assert body["audit"]["safe_command"] == "/debug pilot-gate"
    audit = routes.job_repository.list_lark_operation_audits(limit=1)[0]
    assert audit.actor == "ops-reviewer"
    assert audit.service == "bot"
    assert audit.operation == "pilot_gate"
    assert audit.identity == "bot"
    assert audit.profile == "debug-bot"
    assert audit.context == "/debug pilot-gate"


def test_lark_bot_command_preview_maps_spreadsheet_sync_decision_option_to_writeback() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/lark/bot/commands/preview",
        json={
            "text": (
                "/debug spreadsheet rerun "
                "https://example.larkoffice.com/sheets/abc?sheet=def def 2,3 同步到飞书"
            ),
            "actor": "ops-reviewer",
            "open_id": "ou_1",
            "chat_id": "oc_1",
            "identity": "bot",
            "profile": "debug-bot",
        },
    )

    assert response.status_code == 200
    body = response.json()
    parameters = body["action"]["parameters"]
    assert body["action"]["kind"] == "spreadsheet_rerun"
    assert parameters["report"] is True
    assert parameters["writeback"] is True


def test_lark_bot_command_preview_requires_actor_when_trusted_actor_enabled() -> None:
    client = TestClient(app)
    original_settings = routes.settings
    try:
        routes.settings = original_settings.model_copy(update={"require_trusted_actor": True})

        response = client.post(
            "/api/lark/bot/commands/preview",
            json={"text": "/debug status", "actor": "", "open_id": ""},
        )

        assert response.status_code == 400
        assert "Actor is required" in response.json()["detail"]
    finally:
        routes.settings = original_settings


def test_lark_bot_command_preview_accepts_open_id_as_actor_boundary() -> None:
    client = TestClient(app)
    original_settings = routes.settings
    try:
        routes.settings = original_settings.model_copy(update={"require_trusted_actor": True})

        response = client.post(
            "/api/lark/bot/commands/preview",
            json={"text": "/debug run case handwrite233", "actor": "", "open_id": "ou_operator"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["audit"]["actor"] == "ou_operator"
        assert body["action"]["kind"] == "submit_case"
        assert body["action"]["confirmation_required"] is True
        assert body["card"]["buttons"][0]["confirmation_required"] is True
    finally:
        routes.settings = original_settings
