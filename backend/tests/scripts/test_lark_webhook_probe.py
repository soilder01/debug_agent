# ruff: noqa: F403,F405
from tests.scripts.common import *


def test_lark_bot_webhook_probe_builds_signed_encrypted_probe_request() -> None:
    module = load_lark_bot_probe_module()
    payload = module.build_url_verification_payload(challenge="verify", token="bot-token")

    body, headers = module.request_body_and_headers(
        payload,
        encrypt_key="encrypt-key",
        encrypt_payload=True,
        timestamp="1700000000",
        nonce="nonce-1",
    )

    assert b"encrypt" in body
    assert headers["X-Lark-Request-Timestamp"] == "1700000000"
    assert headers["X-Lark-Request-Nonce"] == "nonce-1"
    assert headers["X-Lark-Signature"]
    expected = module.calculate_lark_signature(
        timestamp="1700000000",
        nonce="nonce-1",
        encrypt_key="encrypt-key",
        body=body,
    )
    assert headers["X-Lark-Signature"] == expected


def test_lark_bot_webhook_probe_builds_passed_url_verification_report() -> None:
    module = load_lark_bot_probe_module()

    report = module.build_probe_report(
        mode="url-verification",
        base_url="http://debug-agent.local/",
        expected_challenge="verify",
        result={
            "ok": True,
            "status_code": 200,
            "url": "http://debug-agent.local/api/lark/bot/events",
            "request": {},
            "response": {"challenge": "verify"},
            "error": "",
        },
    )

    assert report["base_url"] == "http://debug-agent.local"
    assert report["status"] == "passed"
    assert all(check["status"] == "passed" for check in report["checks"])
