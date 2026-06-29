# ruff: noqa: F403,F405
from tests.api.lark_bot.common import *


def test_lark_bot_preflight_reports_gate_status_and_required_scopes() -> None:
    client = TestClient(app)
    original_settings = routes.settings
    original_lark_settings = routes.lark_spreadsheet_settings
    try:
        routes.settings = original_settings.model_copy(
            update={
                "environment": "pilot",
                "lark_event_mode": "webhook",
                "report_base_url": "https://debug-agent.example",
                "require_trusted_actor": True,
                "lark_bot_verification_token": SecretStr("real-bot-token"),
                "lark_bot_encrypt_key": SecretStr("real-encrypt-secret"),
            }
        )
        routes.lark_spreadsheet_settings = original_lark_settings.model_copy(
            update={"lark_cli_identity": "bot", "lark_cli_profile": "debug-bot"}
        )

        response = client.get("/api/lark/bot/preflight")

        assert response.status_code == 200
        body = response.json()
        assert body["event_mode"] == "webhook"
        assert body["event_endpoint_url"] == "https://debug-agent.example/api/lark/bot/events"
        assert body["setup_package_url"] == "/api/lark/bot/setup-package.zip"
        assert body["connector"]["identity"] == "bot"
        assert "im:message:send_as_bot" in body["required_bot_scopes"]
        assert body["pending_command_count"] >= 0
        assert body["failed_command_count"] >= 0
        setup_items = {item["key"]: item for item in body["operator_required_items"]}
        assert setup_items["deploy_callback_url"]["status"] == "done"
        assert setup_items["copy_verification_token"]["status"] == "done"
        assert setup_items["copy_encrypt_key"]["status"] == "done"
        assert setup_items["configure_bot_identity"]["status"] == "done"
        assert setup_items["subscribe_message_event"]["status"] == "manual_check"
        assert setup_items["grant_im_bot_scope"]["owner"] == "lark_app_admin"
        check_keys = {check["key"] for check in body["checks"]}
        assert {
            "event_endpoint",
            "verification_token",
            "encrypt_key",
            "trusted_actor",
            "connector_identity",
            "im_scope_catalog",
            "pending_commands",
            "failed_commands",
        } <= check_keys
    finally:
        routes.settings = original_settings
        routes.lark_spreadsheet_settings = original_lark_settings


def test_lark_bot_long_connection_preflight_uses_xiaod_mode_without_webhook_secrets() -> None:
    client = TestClient(app)
    original_settings = routes.settings
    original_lark_settings = routes.lark_spreadsheet_settings
    try:
        routes.settings = original_settings.model_copy(
            update={
                "environment": "pilot",
                "lark_event_mode": "long_connection",
                "report_base_url": "http://localhost:8000",
                "require_trusted_actor": True,
                "lark_bot_verification_token": None,
                "lark_bot_encrypt_key": None,
            }
        )
        routes.lark_spreadsheet_settings = original_lark_settings.model_copy(
            update={"lark_cli_identity": "bot", "lark_cli_profile": "xiaoD"}
        )

        response = client.get("/api/lark/bot/preflight")

        assert response.status_code == 200
        body = response.json()
        assert body["event_mode"] == "long_connection"
        assert "im:message.p2p_msg:readonly" in body["required_bot_scopes"]
        assert "im:message.group_at_msg:readonly" in body["required_bot_scopes"]
        assert "im:message:send_as_bot" in body["required_bot_scopes"]
        assert "im:message.group_at_msg.include_bot:readonly" not in body["required_bot_scopes"]
        setup_items = {item["key"]: item for item in body["operator_required_items"]}
        assert setup_items["deploy_callback_url"]["required"] is False
        assert setup_items["deploy_callback_url"]["status"] == "done"
        assert setup_items["copy_verification_token"]["required"] is False
        assert setup_items["copy_encrypt_key"]["required"] is False
        assert setup_items["run_webhook_probe"]["required"] is False
        assert setup_items["configure_card_callback"]["required"] is False
        assert setup_items["configure_card_callback"]["status"] == "done"
        assert setup_items["configure_bot_identity"]["status"] == "done"
        checks = {check["key"]: check for check in body["checks"]}
        assert checks["event_receiver_mode"]["status"] == "passed"
        assert checks["event_schema"]["status"] == "passed"
        assert checks["card_action_event_schema"]["status"] == "passed"
        assert "transport=sdk" in checks["card_action_event_schema"]["detail"]
        assert checks["connector_identity"]["status"] == "passed"
        assert "event_endpoint" not in checks
        assert "verification_token" not in checks
        assert "encrypt_key" not in checks
    finally:
        routes.settings = original_settings
        routes.lark_spreadsheet_settings = original_lark_settings


def test_lark_bot_long_connection_setup_package_exports_diagnostics() -> None:
    client = TestClient(app)
    original_settings = routes.settings
    original_lark_settings = routes.lark_spreadsheet_settings
    try:
        routes.settings = original_settings.model_copy(
            update={
                "environment": "pilot",
                "lark_event_mode": "long_connection",
                "report_base_url": "http://localhost:8000",
                "require_trusted_actor": True,
                "lark_bot_verification_token": None,
                "lark_bot_encrypt_key": None,
            }
        )
        routes.lark_spreadsheet_settings = original_lark_settings.model_copy(
            update={"lark_cli_identity": "bot", "lark_cli_profile": "xiaoD"}
        )

        response = client.get("/api/lark/bot/setup-package.zip")

        assert response.status_code == 200
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            names = set(archive.namelist())
            assert "long-connection-diagnostics.ps1" in names
            diagnostics = archive.read("long-connection-diagnostics.ps1").decode("utf-8")
            legacy_probe = archive.read("webhook-probe-commands.ps1").decode("utf-8")
            assert "lark-cli event consume im.message.receive_v1" in diagnostics
            assert "lark_bot_long_connection_consumer.py --transport sdk" in diagnostics
            assert "不需要 webhook probe" in legacy_probe
    finally:
        routes.settings = original_settings
        routes.lark_spreadsheet_settings = original_lark_settings


def test_lark_bot_setup_acknowledgement_updates_preflight_manual_item() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/lark/bot/setup-acknowledgements/subscribe_message_event",
        json={
            "actor": "lark-admin",
            "evidence": "审批单 FEISHU-123 已订阅 im.message.receive_v1",
            "note": "管理员确认",
        },
    )

    assert response.status_code == 200
    acknowledgement = response.json()
    assert acknowledgement["item_key"] == "subscribe_message_event"
    assert acknowledgement["actor"] == "lark-admin"

    preflight = client.get("/api/lark/bot/preflight").json()
    setup_items = {item["key"]: item for item in preflight["operator_required_items"]}
    item = setup_items["subscribe_message_event"]
    assert item["status"] == "done"
    assert item["acknowledgement"]["actor"] == "lark-admin"
    assert "FEISHU-123" in item["evidence"]

    list_response = client.get(
        "/api/lark/bot/setup-acknowledgements?item_key=subscribe_message_event"
    )
    assert list_response.status_code == 200
    assert list_response.json()["acknowledgements"][0]["evidence"].startswith("审批单 FEISHU-123")
    latest_audit = routes.job_repository.list_lark_operation_audits(limit=1)[0]
    assert latest_audit.service == "bot"
    assert latest_audit.operation == "setup_acknowledge"
    assert latest_audit.context == "subscribe_message_event"


def test_lark_bot_setup_acknowledgement_rejects_unknown_item_and_empty_evidence() -> None:
    client = TestClient(app)

    unknown = client.post(
        "/api/lark/bot/setup-acknowledgements/not-a-real-item",
        json={"actor": "ops", "evidence": "审批单"},
    )
    missing_evidence = client.post(
        "/api/lark/bot/setup-acknowledgements/run_webhook_probe",
        json={"actor": "ops", "evidence": "   "},
    )

    assert unknown.status_code == 404
    assert missing_evidence.status_code == 400


def test_lark_bot_go_live_gate_blocks_until_setup_is_complete() -> None:
    client = TestClient(app)

    response = client.get("/api/lark/bot/go-live-gate")

    assert response.status_code == 200
    body = response.json()
    assert body["allowed"] is False
    assert body["decision"] == "暂不允许进入真实飞书机器人 dogfood。"
    check_keys = {check["key"] for check in body["checks"]}
    assert {
        "production_readiness",
        "bot_preflight",
        "setup_items",
        "manual_acknowledgements",
        "missing_scopes",
        "pending_commands",
        "failed_commands",
    } <= check_keys
    assert body["export_urls"]["setup_package"] == "/api/lark/bot/setup-package.zip"


def test_lark_bot_long_connection_go_live_gate_does_not_require_webhook_probe_acknowledgement() -> (
    None
):
    client = TestClient(app)
    original_settings = routes.settings
    original_lark_settings = routes.lark_spreadsheet_settings
    try:
        routes.settings = original_settings.model_copy(
            update={
                "lark_event_mode": "long_connection",
                "lark_bot_verification_token": None,
                "lark_bot_encrypt_key": None,
            }
        )
        routes.lark_spreadsheet_settings = original_lark_settings.model_copy(
            update={"lark_cli_identity": "bot", "lark_cli_profile": "xiaoD"}
        )

        response = client.get("/api/lark/bot/go-live-gate")

        assert response.status_code == 200
        body = response.json()
        assert body["preflight"]["event_mode"] == "long_connection"
        manual_acknowledgements = {check["key"]: check for check in body["checks"]}[
            "manual_acknowledgements"
        ]
        assert "运行 webhook 探针" not in manual_acknowledgements["detail"]
        assert "配置消息卡片交互回调" not in manual_acknowledgements["detail"]
    finally:
        routes.settings = original_settings
        routes.lark_spreadsheet_settings = original_lark_settings


def test_lark_bot_permission_checklist_blocks_recent_drive_download_scope() -> None:
    client = TestClient(app)
    routes.job_repository.save_lark_operation_audit(
        actor="local-dev-operator",
        connector_mode="cli",
        identity="bot",
        profile="xiaoD",
        service="drive",
        operation="+download",
        status="failed",
        context="drive +download --file-token sheet-attachment",
        error_type="permission_denied",
        hint="grant docs:document.media:download",
        permission_scopes=["docs:document.media:download"],
        console_url="https://open.larkoffice.com/app?lang=zh-CN",
        risk_action="lark_bot_sheet_attachment_download",
        duration_ms=15,
    )

    response = client.get("/api/lark/bot/permission-checklist")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["blocking_scopes"] == ["docs:document.media:download"]
    assert "im:message.group_at_msg:readonly" in body["required_scopes"]
    assert "sheets:spreadsheet:readonly" in body["required_scopes"]
    assert "docs:document.media:download" in body["required_scopes"]
    assert "im:message.group_at_msg.include_bot:readonly" in body["recommended_scopes"]
    assert "docx:document:readonly" in body["recommended_scopes"]
    drive_requirement = {requirement["scope"]: requirement for requirement in body["requirements"]}[
        "docs:document.media:download"
    ]
    assert drive_requirement["status"] == "needs_action"
    assert drive_requirement["blocking"] is True
    assert "docs:document.media:download" in body["admin_handoff_markdown"]

    preflight = client.get("/api/lark/bot/preflight").json()
    assert "docs:document.media:download" in preflight["required_bot_scopes"]
    assert preflight["recent_missing_scopes"] == ["docs:document.media:download"]
    gate = client.get("/api/lark/bot/go-live-gate").json()
    assert gate["export_urls"]["permission_checklist"] == "/api/lark/bot/permission-checklist"
    missing_scope_check = {check["key"]: check for check in gate["checks"]}["missing_scopes"]
    assert missing_scope_check["status"] == "failed"
    assert "docs:document.media:download" in missing_scope_check["detail"]


def test_lark_bot_setup_package_exports_admin_handoff_without_secrets() -> None:
    client = TestClient(app)
    original_settings = routes.settings
    original_lark_settings = routes.lark_spreadsheet_settings
    try:
        routes.settings = original_settings.model_copy(
            update={
                "environment": "pilot",
                "lark_event_mode": "webhook",
                "report_base_url": "https://debug-agent.example",
                "require_trusted_actor": True,
                "lark_bot_verification_token": SecretStr("real-bot-token"),
                "lark_bot_encrypt_key": SecretStr("real-encrypt-secret"),
            }
        )
        routes.lark_spreadsheet_settings = original_lark_settings.model_copy(
            update={"lark_cli_identity": "bot", "lark_cli_profile": "debug-bot"}
        )

        response = client.get("/api/lark/bot/setup-package.zip")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            names = set(archive.namelist())
            assert {
                "manifest.json",
                "README.txt",
                "preflight.json",
                "permission-checklist.json",
                "permission-checklist.md",
                "setup-checklist.json",
                "setup-acknowledgements.json",
                "setup-checklist.md",
                "feishu-admin-handoff.md",
                "required-scopes.json",
                "webhook-probe-commands.ps1",
            } <= names
            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
            preflight = json.loads(archive.read("preflight.json").decode("utf-8"))
            permission_checklist = json.loads(
                archive.read("permission-checklist.json").decode("utf-8")
            )
            checklist_md = archive.read("setup-checklist.md").decode("utf-8")
            permission_md = archive.read("permission-checklist.md").decode("utf-8")
            probe_commands = archive.read("webhook-probe-commands.ps1").decode("utf-8")
            full_text = "\n".join(
                archive.read(name).decode("utf-8", errors="ignore") for name in names
            )
            assert manifest["export_type"] == "lark_bot_setup_package"
            assert (
                manifest["event_endpoint_url"] == "https://debug-agent.example/api/lark/bot/events"
            )
            assert preflight["setup_package_url"] == "/api/lark/bot/setup-package.zip"
            assert "im:message.group_at_msg:readonly" in permission_checklist["required_scopes"]
            assert (
                "im:message.group_at_msg.include_bot:readonly"
                in permission_checklist["recommended_scopes"]
            )
            assert "docs:document.media:download" in permission_checklist["required_scopes"]
            assert "飞书机器人真实接入清单" in checklist_md
            assert "小D Bot 飞书权限申请清单" in permission_md
            assert "im:message:send_as_bot" in checklist_md
            assert "<verification-token>" in probe_commands
            assert "<encrypt-key>" in probe_commands
            assert "real-bot-token" not in full_text
            assert "real-encrypt-secret" not in full_text
    finally:
        routes.settings = original_settings
        routes.lark_spreadsheet_settings = original_lark_settings
