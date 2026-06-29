import base64
import hashlib
import json
from types import SimpleNamespace

from Crypto.Cipher import AES

from debug_agent.lark.bot import (
    LarkBotCommandRequest,
    LarkBotReplyPayload,
    build_lark_bot_command_response,
    build_lark_bot_pending_command_reply,
    calculate_lark_bot_event_signature,
    decrypt_lark_bot_event_payload,
    lark_bot_reply_cli_args,
    parse_lark_bot_command,
    parse_lark_bot_event_payload,
    validate_lark_bot_event_signature,
)
from debug_agent.lark.connector import LarkConnectorStatus


def test_lark_bot_command_parses_readiness_and_pilot_gate() -> None:
    readiness = parse_lark_bot_command("/debug status")
    pilot_gate = parse_lark_bot_command("/debug pilot-gate")
    worker = parse_lark_bot_command("/debug worker")
    models = parse_lark_bot_command("/debug models")
    report = parse_lark_bot_command("/debug report job-1")
    evidence = parse_lark_bot_command("/debug evidence job-1")

    assert readiness.kind == "readiness"
    assert readiness.method == "GET"
    assert readiness.path == "/api/operations/readiness"
    assert readiness.side_effect is False
    assert pilot_gate.kind == "pilot_gate"
    assert pilot_gate.path == "/api/operations/pilot-gate"
    assert worker.kind == "worker_status"
    assert worker.path == "/worker/status"
    assert models.kind == "model_catalog"
    assert models.path == "/agent-models"
    assert report.kind == "job_report"
    assert report.path == "/jobs/job-1/report"
    assert evidence.kind == "job_evidence"
    assert evidence.path == "/jobs/job-1/evidence-ledger"


def test_lark_bot_command_parses_product_write_actions_as_confirmed() -> None:
    batch_pause = parse_lark_bot_command("/debug batch pause batch-1")
    worker_start = parse_lark_bot_command("/debug worker start")

    assert batch_pause.kind == "batch_pause"
    assert batch_pause.path == "/debug-batches/batch-1/pause"
    assert batch_pause.confirmation_required is True
    assert batch_pause.risk_level == "write"
    assert worker_start.kind == "worker_start"
    assert worker_start.path == "/worker/start"
    assert worker_start.confirmation_required is True


def test_lark_bot_command_marks_submit_case_as_confirmed_write_action() -> None:
    action = parse_lark_bot_command("/debug run case handwrite233")

    assert action.kind == "submit_case"
    assert action.method == "POST"
    assert action.path == "/api/cases/handwrite233/debug-jobs"
    assert action.side_effect is True
    assert action.confirmation_required is True
    assert action.risk_level == "write"
    assert action.parameters["case_id"] == "handwrite233"


def test_lark_bot_command_parses_controlled_probe_opt_in_flags() -> None:
    closure = parse_lark_bot_command("/debug auto-closure job-1 --controlled-probes")
    closure_report = parse_lark_bot_command(
        "/debug auto-closure-report job-1 --writeback --controlled-probes https://debug.example/report"
    )
    rerun = parse_lark_bot_command(
        "/debug spreadsheet rerun https://example.larkoffice.com/sheets/token?sheet=tab tab 2 --controlled-probes"
    )

    assert closure.kind == "auto_closure"
    assert closure.parameters["submit_controlled_probes"] is True
    assert closure_report.kind == "auto_closure_report"
    assert closure_report.parameters["submit_controlled_probes"] is True
    assert closure_report.parameters["writeback"] is True
    assert rerun.kind == "spreadsheet_rerun"
    assert rerun.parameters["submit_controlled_probes"] is True
    assert rerun.parameters["auto_closure"] is True


def test_lark_bot_command_builds_card_and_audit_context() -> None:
    response = build_lark_bot_command_response(
        LarkBotCommandRequest(
            text="/debug batch run case-a,case-b",
            actor="ops-reviewer",
            open_id="ou_1",
            chat_id="oc_1",
            identity="bot",
        ),
        actor="ops-reviewer",
        connector_status=LarkConnectorStatus(mode="cli", identity="bot", profile="debug-bot"),
        default_profile="debug-bot",
    )

    assert response.action.kind == "submit_batch"
    assert response.action.confirmation_required is True
    assert response.card.status == "warning"
    assert response.card.buttons[0].confirmation_required is True
    assert response.audit.actor == "ops-reviewer"
    assert response.audit.open_id == "ou_1"
    assert response.audit.profile == "debug-bot"
    assert response.warnings == ["该命令映射到写操作；真实执行前必须完成操作者确认和审计记录。"]


def test_lark_bot_command_unknown_returns_help_warning() -> None:
    response = build_lark_bot_command_response(
        LarkBotCommandRequest(text="/debug something-else", actor="ops-reviewer"),
        actor="ops-reviewer",
        connector_status=LarkConnectorStatus(),
    )

    assert response.action.kind == "unknown"
    assert response.action.method == "NONE"
    assert response.card.status == "warning"
    assert response.warnings == ["命令未识别，不会执行任何 Debug Agent 操作。"]


def test_lark_bot_event_payload_handles_url_verification() -> None:
    result = parse_lark_bot_event_payload({"type": "url_verification", "challenge": "verify-token"})

    assert result.event_type == "url_verification"
    assert result.challenge == "verify-token"
    assert result.command_request is None


def test_lark_bot_event_payload_extracts_text_message_command() -> None:
    result = parse_lark_bot_event_payload(
        {
            "schema": "2.0",
            "header": {"event_type": "im.message.receive_v1", "tenant_key": "tenant-1"},
            "event": {
                "sender": {"sender_id": {"open_id": "ou_1"}},
                "message": {
                    "message_id": "om_1",
                    "chat_id": "oc_1",
                    "message_type": "text",
                    "content": '{"text":"/debug status"}',
                },
            },
        }
    )

    assert result.event_type == "im.message.receive_v1"
    assert result.command_request is not None
    assert result.command_request.text == "/debug status"
    assert result.command_request.open_id == "ou_1"
    assert result.command_request.actor == "ou_1"
    assert result.command_request.chat_id == "oc_1"
    assert result.command_request.message_id == "om_1"
    assert result.command_request.tenant_key == "tenant-1"


def test_lark_bot_event_payload_ignores_unsupported_event_type() -> None:
    result = parse_lark_bot_event_payload(
        {"header": {"event_type": "im.message.reaction.created_v1"}}
    )

    assert result.event_type == "im.message.reaction.created_v1"
    assert result.ignored_reason == "unsupported_event_type"


def test_lark_bot_event_signature_uses_raw_body() -> None:
    body = b'{"token":"bot-token","challenge":"verify"}'
    signature = calculate_lark_bot_event_signature(
        timestamp="1700000000",
        nonce="nonce-1",
        encrypt_key="encrypt-key",
        body=body,
    )

    assert signature
    assert validate_lark_bot_event_signature(
        headers={
            "X-Lark-Request-Timestamp": "1700000000",
            "X-Lark-Request-Nonce": "nonce-1",
            "X-Lark-Signature": signature,
        },
        body=body,
        encrypt_key="encrypt-key",
    )
    assert not validate_lark_bot_event_signature(
        headers={
            "X-Lark-Request-Timestamp": "1700000000",
            "X-Lark-Request-Nonce": "nonce-1",
            "X-Lark-Signature": signature,
        },
        body=b'{"challenge":"changed"}',
        encrypt_key="encrypt-key",
    )


def test_lark_bot_event_payload_decrypts_encrypted_callback() -> None:
    plaintext = {"token": "bot-token", "challenge": "verify-token"}
    encrypted = _encrypt_lark_event_payload(plaintext, "encrypt-key")

    decrypted = decrypt_lark_bot_event_payload({"encrypt": encrypted}, "encrypt-key")

    assert decrypted == plaintext


def test_lark_bot_reply_payload_prefers_message_reply_target() -> None:
    payload = build_lark_bot_pending_command_reply(
        SimpleNamespace(
            command_id="cmd-1",
            action_kind="submit_case",
            status="executed",
            command_text="/debug run case handwrite233",
            message_id="om_1",
            chat_id="oc_1",
            open_id="ou_1",
            execution_result={
                "submitted_job": {
                    "job_id": "job-1",
                    "case_id": "handwrite233",
                }
            },
            error_message="",
        ),
        identity="bot",
        dry_run=True,
    )

    assert payload.target_type == "message"
    assert payload.message_id == "om_1"
    assert "Debug Agent 已提交调试任务" in payload.markdown
    assert "`job-1`" in payload.markdown
    assert payload.idempotency_key.startswith("da-")
    assert len(payload.idempotency_key) <= 40
    assert payload.delivery_args[:4] == ["im", "+messages-reply", "--message-id", "om_1"]
    assert "--dry-run" in payload.delivery_args


def test_lark_bot_reply_cli_args_can_send_to_chat_without_dry_run() -> None:
    payload = build_lark_bot_pending_command_reply(
        SimpleNamespace(
            command_id="cmd-2",
            action_kind="submit_batch",
            status="pending",
            command_text="/debug batch run case-a,case-b",
            message_id="",
            chat_id="oc_1",
            open_id="",
            execution_result={},
            error_message="",
            expires_at="2026-06-23T10:00:00+00:00",
        ),
        identity="bot",
        dry_run=False,
    )
    args = lark_bot_reply_cli_args(payload, identity="bot", dry_run=False)

    assert payload.target_type == "chat"
    assert args[:4] == ["im", "+messages-send", "--chat-id", "oc_1"]
    assert "--as" in args
    assert "bot" in args
    assert "--dry-run" not in args


def test_lark_bot_reply_cli_args_escapes_card_url_shell_metacharacters() -> None:
    payload = LarkBotReplyPayload(
        command_id="card-1",
        action_kind="badcase_confirmation",
        status="ready_for_confirmation",
        target_type="message",
        message_id="om_1",
        markdown="确认提交",
        message_type="interactive",
        content={
            "elements": [
                {
                    "tag": "button",
                    "url": "http://localhost:8000/api/lark/bot/badcase-drafts/draft-1/confirm-link?action=confirm_badcase_draft&token=secret",
                }
            ]
        },
        idempotency_key="da-card-123",
    )

    args = lark_bot_reply_cli_args(payload, identity="bot", dry_run=True)

    content = args[args.index("--content") + 1]
    assert "&token" not in content
    assert "\\u0026token" in content


def _encrypt_lark_event_payload(payload: dict[str, object], encrypt_key: str) -> str:
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    padding_size = AES.block_size - (len(raw) % AES.block_size)
    padded = raw + bytes([padding_size]) * padding_size
    key = hashlib.sha256(encrypt_key.encode("utf-8")).digest()
    iv = b"0123456789abcdef"
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return base64.b64encode(iv + cipher.encrypt(padded)).decode("ascii")
