import json

import pytest

from debug_agent.lark.connector import (
    FakeLarkConnector,
    LarkCliConnector,
    LarkCliError,
    LarkConnectorAuditEvent,
    LarkOpenApiConnector,
    _lark_cli_error_from_raw,
    lark_required_scopes,
    lark_scope_requirements,
)


class RecordingCommandRunner:
    def __init__(self, output: dict[str, object]) -> None:
        self.output = output
        self.calls: list[tuple[list[str], str | None]] = []

    def __call__(self, args: list[str], stdin: str | None = None) -> str:
        self.calls.append((args, stdin))
        return json.dumps(self.output)


def test_lark_cli_connector_injects_profile_and_reports_status() -> None:
    runner = RecordingCommandRunner({"ok": True, "data": {"rows": []}})
    connector = LarkCliConnector(command_runner=runner, profile="debug-bot", identity="bot")

    assert connector.status().profile == "debug-bot"
    assert connector.status().identity == "bot"

    data = connector.run_json(["sheets", "+csv-get", "--spreadsheet-token", "sheet", "--sheet-id", "tab"])

    assert data == {"rows": []}
    assert runner.calls[0][0][:4] == ["lark-cli", "--profile", "debug-bot", "sheets"]


def test_lark_cli_connector_emits_success_audit_event() -> None:
    runner = RecordingCommandRunner({"ok": True, "data": {"rows": []}})
    events: list[LarkConnectorAuditEvent] = []
    connector = LarkCliConnector(command_runner=runner, profile="debug-bot", identity="bot", audit_sink=events.append)

    connector.run_json(["sheets", "+csv-get", "--spreadsheet-token", "sheet", "--sheet-id", "tab"])

    assert len(events) == 1
    event = events[0]
    assert event.connector_mode == "cli"
    assert event.identity == "bot"
    assert event.profile == "debug-bot"
    assert event.service == "sheets"
    assert event.operation == "+csv-get"
    assert event.status == "succeeded"
    assert "--spreadsheet-token sheet" in event.context


def test_lark_cli_connector_blocks_commands_outside_allowlist() -> None:
    connector = LarkCliConnector(command_runner=RecordingCommandRunner({"ok": True, "data": {}}))

    with pytest.raises(LarkCliError) as exc_info:
        connector.run_json(["drive", "+delete", "--file-token", "secret"])

    assert exc_info.value.error_type == "command_not_allowed"


def test_lark_cli_connector_normalizes_permission_error_envelope() -> None:
    runner = RecordingCommandRunner(
        {
            "ok": False,
            "error": {
                "type": "permission_denied",
                "message": "permission denied",
                "hint": "run lark-cli auth login --scope sheets:spreadsheet:readonly",
                "permission_violations": [{"scope": "sheets:spreadsheet:readonly"}],
                "console_url": "https://open.feishu.cn/app",
            },
        }
    )
    connector = LarkCliConnector(command_runner=runner)

    with pytest.raises(LarkCliError) as exc_info:
        connector.run_json(["sheets", "+csv-get", "--spreadsheet-token", "sheet", "--sheet-id", "tab"])

    error = exc_info.value
    assert error.error_type == "permission_denied"
    assert error.permission_scopes == ["sheets:spreadsheet:readonly"]
    assert error.console_url == "https://open.feishu.cn/app"
    assert "auth login" in error.hint


def test_lark_cli_connector_extracts_subject_permission_violations() -> None:
    runner = RecordingCommandRunner(
        {
            "ok": False,
            "error": {
                "type": "permission_denied",
                "message": "permission denied",
                "permission_violations": [{"subject": "drive:file:download"}],
            },
        }
    )
    connector = LarkCliConnector(
        command_runner=runner,
        allowed_commands={("drive", "+download")},
    )

    with pytest.raises(LarkCliError) as exc_info:
        connector.run_json(["drive", "+download", "--file-token", "file-token"])

    assert exc_info.value.error_type == "permission_denied"
    assert exc_info.value.permission_scopes == ["drive:file:download"]


def test_lark_cli_connector_extracts_missing_scopes_and_api_operation() -> None:
    runner = RecordingCommandRunner(
        {
            "ok": False,
            "error": {
                "type": "authorization",
                "message": "access denied",
                "missing_scopes": ["docs:document.media:download"],
                "console_url": "https://open.feishu.cn/app/cli_xxx/auth",
            },
        }
    )
    events: list[LarkConnectorAuditEvent] = []
    connector = LarkCliConnector(
        command_runner=runner,
        allowed_commands={("api", "GET")},
        audit_sink=events.append,
    )

    with pytest.raises(LarkCliError) as exc_info:
        connector.run_json(
            [
                "api",
                "GET",
                "/open-apis/drive/v1/medias/file-token/download",
                "--output",
                "media.mp4",
                "--as",
                "bot",
            ]
        )

    assert exc_info.value.error_type == "permission_denied"
    assert exc_info.value.permission_scopes == ["docs:document.media:download"]
    assert events[0].service == "api"
    assert events[0].operation == "GET"


def test_lark_cli_connector_extracts_embedded_permission_violations() -> None:
    runner = RecordingCommandRunner(
        {
            "ok": False,
            "error": {
                "type": "network",
                "message": (
                    'HTTP 400: {"error":{"permission_violations":'
                    '[{"subject":"drive:file:download"}]}}'
                ),
            },
        }
    )
    connector = LarkCliConnector(
        command_runner=runner,
        allowed_commands={("drive", "+download")},
    )

    with pytest.raises(LarkCliError) as exc_info:
        connector.run_json(["drive", "+download", "--file-token", "file-token"])

    assert exc_info.value.error_type == "permission_denied"
    assert exc_info.value.permission_scopes == ["drive:file:download"]


def test_lark_cli_raw_error_parser_ignores_progress_prefix() -> None:
    error = _lark_cli_error_from_raw(
        raw=(
            'Downloading: SfFr...lnfb\n{"ok":false,"error":{"type":"network",'
            '"message":"HTTP 400: {\\"error\\":{\\"permission_violations\\":'
            '[{\\"subject\\":\\"drive:file:download\\"}]}}"}}'
        ),
        fallback_message="fallback",
        fallback_type="cli_error",
    )

    assert error.error_type == "permission_denied"
    assert error.permission_scopes == ["drive:file:download"]


def test_lark_cli_connector_emits_permission_audit_event() -> None:
    runner = RecordingCommandRunner(
        {
            "ok": False,
            "error": {
                "type": "permission_denied",
                "message": "permission denied",
                "hint": "run lark-cli auth login --scope sheets:spreadsheet:readonly",
                "permission_violations": [{"scope": "sheets:spreadsheet:readonly"}],
                "console_url": "https://open.feishu.cn/app",
            },
        }
    )
    events: list[LarkConnectorAuditEvent] = []
    connector = LarkCliConnector(command_runner=runner, audit_sink=events.append)

    with pytest.raises(LarkCliError):
        connector.run_json(["sheets", "+csv-get", "--spreadsheet-token", "sheet", "--sheet-id", "tab"])

    assert len(events) == 1
    event = events[0]
    assert event.status == "failed"
    assert event.error_type == "permission_denied"
    assert event.hint == "run lark-cli auth login --scope sheets:spreadsheet:readonly"
    assert event.permission_scopes == ["sheets:spreadsheet:readonly"]
    assert event.console_url == "https://open.feishu.cn/app"


def test_lark_cli_connector_normalizes_confirmation_required_envelope() -> None:
    runner = RecordingCommandRunner(
        {
            "ok": False,
            "error": {
                "type": "confirmation_required",
                "message": "write requires confirmation",
                "risk": {"level": "high-risk-write", "action": "sheets +cells-set"},
            },
        }
    )
    connector = LarkCliConnector(command_runner=runner)

    with pytest.raises(LarkCliError) as exc_info:
        connector.run_json(["sheets", "+cells-set", "--spreadsheet-token", "sheet", "--sheet-id", "tab"])

    assert exc_info.value.error_type == "confirmation_required"
    assert exc_info.value.risk_action == "sheets +cells-set"


def test_lark_scope_requirements_list_known_sheet_permissions() -> None:
    requirements = lark_scope_requirements(service="sheets")

    assert [requirement.operation for requirement in requirements] == ["+csv-get", "+cells-set"]
    assert lark_required_scopes("sheets", "+csv-get") == ["sheets:spreadsheet:readonly"]
    assert lark_required_scopes("sheets", "cells-set") == ["sheets:spreadsheet"]
    assert requirements[1].confirmation_required is True


def test_lark_scope_requirements_include_im_bot_reply_permissions() -> None:
    requirements = lark_scope_requirements(service="im", operation="+messages-reply")

    assert {requirement.identity for requirement in requirements} == {"bot", "user"}
    assert "im:message:send_as_bot" in lark_required_scopes("im", "+messages-reply")
    assert "im:message.send_as_user" in lark_required_scopes("im", "+messages-reply")
    assert all(requirement.confirmation_required for requirement in requirements)


def test_lark_cli_connector_allows_im_message_send_and_redacts_content_from_context() -> None:
    runner = RecordingCommandRunner({"ok": True, "data": {"message_id": "om_1"}})
    events: list[LarkConnectorAuditEvent] = []
    connector = LarkCliConnector(command_runner=runner, identity="bot", audit_sink=events.append)

    data = connector.run_json(
        [
            "im",
            "+messages-send",
            "--chat-id",
            "oc_1",
            "--markdown",
            "## secret result",
            "--idempotency-key",
            "idem-1",
            "--as",
            "bot",
        ]
    )

    assert data == {"message_id": "om_1"}
    assert events[0].service == "im"
    assert events[0].operation == "+messages-send"
    assert "--chat-id oc_1" in events[0].context
    assert "--idempotency-key idem-1" in events[0].context
    assert "secret result" not in events[0].context


def test_lark_openapi_connector_reports_skeleton_status_and_audit() -> None:
    events: list[LarkConnectorAuditEvent] = []
    connector = LarkOpenApiConnector(identity="bot", profile="openapi-bot", audit_sink=events.append)

    assert connector.status().mode == "openapi"
    assert connector.status().auth_status == "not_configured"
    with pytest.raises(LarkCliError) as exc_info:
        connector.run_json(["sheets", "+csv-get", "--spreadsheet-token", "sheet"])

    assert exc_info.value.error_type == "connector_not_implemented"
    assert len(events) == 1
    assert events[0].connector_mode == "openapi"
    assert events[0].error_type == "connector_not_implemented"


def test_fake_lark_connector_returns_configured_response_and_audit() -> None:
    events: list[LarkConnectorAuditEvent] = []
    connector = FakeLarkConnector(
        responses={("sheets", "+csv-get"): {"rows": [["case_id"], ["case-1"]]}},
        audit_sink=events.append,
    )

    data = connector.run_json(["sheets", "+csv-get", "--spreadsheet-token", "sheet"])

    assert connector.status().mode == "fake"
    assert data == {"rows": [["case_id"], ["case-1"]]}
    assert events[0].connector_mode == "fake"
    assert events[0].status == "succeeded"
