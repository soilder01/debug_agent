# ruff: noqa: F403,F405
from tests.api.lark_bot.common import *


def test_lark_bot_event_endpoint_returns_challenge_for_url_verification() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/lark/bot/events",
        json={"type": "url_verification", "challenge": "verify-token"},
    )

    assert response.status_code == 200
    assert response.json() == {"challenge": "verify-token"}


def test_lark_bot_event_endpoint_requires_configured_verification_token() -> None:
    client = TestClient(app)
    original_settings = routes.settings
    try:
        routes.settings = original_settings.model_copy(
            update={
                "lark_event_mode": "webhook",
                "lark_bot_verification_token": SecretStr("expected-token"),
            }
        )

        rejected = client.post(
            "/api/lark/bot/events",
            json={"type": "url_verification", "challenge": "verify-token", "token": "wrong-token"},
        )
        accepted = client.post(
            "/api/lark/bot/events",
            json={
                "type": "url_verification",
                "challenge": "verify-token",
                "token": "expected-token",
            },
        )

        assert rejected.status_code == 403
        assert "Invalid Lark bot verification token" in rejected.json()["detail"]
        assert accepted.status_code == 200
        assert accepted.json() == {"challenge": "verify-token"}
        latest_audit = routes.job_repository.list_lark_operation_audits(limit=1)[0]
        assert latest_audit.service == "bot"
        assert latest_audit.operation == "event_rejected"
        assert latest_audit.error_type == "invalid_verification_token"
    finally:
        routes.settings = original_settings


def test_lark_bot_event_endpoint_requires_signature_when_encrypt_key_configured() -> None:
    client = TestClient(app)
    original_settings = routes.settings
    try:
        routes.settings = original_settings.model_copy(
            update={
                "lark_event_mode": "webhook",
                "lark_bot_encrypt_key": SecretStr("encrypt-key"),
            }
        )
        body = json.dumps({"type": "url_verification", "challenge": "verify-token"}).encode("utf-8")
        signature = calculate_lark_bot_event_signature(
            timestamp="1700000000",
            nonce="nonce-1",
            encrypt_key="encrypt-key",
            body=body,
        )

        rejected = client.post(
            "/api/lark/bot/events",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Lark-Request-Timestamp": "1700000000",
                "X-Lark-Request-Nonce": "nonce-1",
                "X-Lark-Signature": "bad-signature",
            },
        )
        accepted = client.post(
            "/api/lark/bot/events",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Lark-Request-Timestamp": "1700000000",
                "X-Lark-Request-Nonce": "nonce-1",
                "X-Lark-Signature": signature,
            },
        )

        assert rejected.status_code == 403
        assert "Invalid Lark bot event signature" in rejected.json()["detail"]
        assert accepted.status_code == 200
        assert accepted.json() == {"challenge": "verify-token"}
        latest_audit = routes.job_repository.list_lark_operation_audits(limit=1)[0]
        assert latest_audit.operation == "event_rejected"
        assert latest_audit.error_type == "invalid_signature"
    finally:
        routes.settings = original_settings


def test_lark_bot_event_endpoint_skips_webhook_security_in_long_connection_mode() -> None:
    client = TestClient(app)
    original_settings = routes.settings
    try:
        routes.settings = original_settings.model_copy(
            update={
                "lark_event_mode": "long_connection",
                "lark_bot_encrypt_key": SecretStr("encrypt-key"),
                "lark_bot_verification_token": SecretStr("bot-token"),
            }
        )

        response = client.post(
            "/api/lark/bot/events",
            json={
                "schema": "2.0",
                "header": {
                    "event_type": "im.message.receive_v1",
                    "tenant_key": "tenant-1",
                    "token": "different-token",
                },
                "event": {
                    "sender": {"sender_id": {"open_id": "ou_1"}},
                    "message": {
                        "message_id": "om_1",
                        "chat_id": "oc_1",
                        "message_type": "text",
                        "content": '{"text":"/debug status"}',
                    },
                },
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["handled"] is True
        assert body["command"]["action"]["kind"] == "readiness"
    finally:
        routes.settings = original_settings


def test_lark_bot_event_endpoint_decrypts_url_verification_in_long_connection_mode() -> None:
    client = TestClient(app)
    original_settings = routes.settings
    try:
        routes.settings = original_settings.model_copy(
            update={
                "lark_event_mode": "long_connection",
                "lark_bot_encrypt_key": SecretStr("encrypt-key"),
                "lark_bot_verification_token": None,
            }
        )
        encrypted_payload = {
            "encrypt": _encrypt_lark_event_payload(
                {
                    "type": "url_verification",
                    "token": "bot-token",
                    "challenge": "verify-token",
                },
                "encrypt-key",
            )
        }

        response = client.post("/api/lark/bot/events", json=encrypted_payload)

        assert response.status_code == 200
        assert response.json() == {"challenge": "verify-token"}
    finally:
        routes.settings = original_settings


def test_lark_bot_event_endpoint_decrypts_encrypted_message_payload() -> None:
    client = TestClient(app)
    original_settings = routes.settings
    try:
        routes.settings = original_settings.model_copy(
            update={
                "lark_event_mode": "webhook",
                "lark_bot_encrypt_key": SecretStr("encrypt-key"),
                "lark_bot_verification_token": SecretStr("bot-token"),
            }
        )
        encrypted_payload = {
            "encrypt": _encrypt_lark_event_payload(
                {
                    "token": "bot-token",
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
                },
                "encrypt-key",
            )
        }
        body = json.dumps(encrypted_payload, separators=(",", ":")).encode("utf-8")
        signature = calculate_lark_bot_event_signature(
            timestamp="1700000000",
            nonce="nonce-1",
            encrypt_key="encrypt-key",
            body=body,
        )

        response = client.post(
            "/api/lark/bot/events",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Lark-Request-Timestamp": "1700000000",
                "X-Lark-Request-Nonce": "nonce-1",
                "X-Lark-Signature": signature,
            },
        )

        assert response.status_code == 200
        body_json = response.json()
        assert body_json["handled"] is True
        assert body_json["command"]["action"]["kind"] == "readiness"
        assert body_json["command"]["audit"]["actor"] == "ou_1"
    finally:
        routes.settings = original_settings


def test_lark_bot_event_endpoint_maps_message_to_preview_and_audit() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/lark/bot/events",
        json={
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
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["event_type"] == "im.message.receive_v1"
    assert body["handled"] is True
    assert body["command"]["action"]["kind"] == "readiness"
    assert body["command"]["audit"]["actor"] == "ou_1"
    assert body["command"]["audit"]["chat_id"] == "oc_1"
    assert body["command"]["audit"]["message_id"] == "om_1"
    assert body["command"]["audit"]["tenant_key"] == "tenant-1"
    audit = routes.job_repository.list_lark_operation_audits(limit=1)[0]
    assert audit.actor == "ou_1"
    assert audit.service == "bot"
    assert audit.operation == "readiness"
    assert audit.context == "/debug status"


def test_lark_bot_event_endpoint_ignores_non_message_events() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/lark/bot/events",
        json={"header": {"event_type": "im.message.reaction.created_v1"}},
    )

    assert response.status_code == 200
    assert response.json() == {
        "event_type": "im.message.reaction.created_v1",
        "handled": False,
        "challenge": "",
        "ignored_reason": "unsupported_event_type",
        "command": None,
    }
