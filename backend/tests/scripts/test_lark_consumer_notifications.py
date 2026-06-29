# ruff: noqa: F403,F405
from tests.scripts.common import *


def test_lark_bot_consumer_delivers_completion_notifications(monkeypatch) -> None:
    module = load_lark_bot_consumer_module()
    sent_args: list[list[str]] = []
    marked_payloads: list[tuple[str, dict[str, object]]] = []

    def fake_get_json(url: str) -> dict[str, object]:
        assert (
            url
            == "http://debug-agent.local/api/lark/bot/badcase-drafts/completion-notifications?limit=20"
        )
        return {
            "notifications": [
                {
                    "draft": {"draft_id": "draft-1"},
                    "payload": {
                        "delivery_args": [
                            "im",
                            "+messages-reply",
                            "--message-id",
                            "om_1",
                            "--markdown",
                            "done",
                            "--as",
                            "bot",
                        ]
                    },
                }
            ]
        }

    def fake_run_lark_delivery_args(**kwargs) -> bool:
        sent_args.append(kwargs["args"])
        return True

    def fake_post_json(url: str, payload: dict[str, object]) -> dict[str, object]:
        marked_payloads.append((url, payload))
        return {"status": "completed"}

    monkeypatch.setattr(module, "get_json", fake_get_json)
    monkeypatch.setattr(module, "run_lark_delivery_args", fake_run_lark_delivery_args)
    monkeypatch.setattr(module, "post_json", fake_post_json)

    delivered = module.deliver_completion_notifications(
        base_url="http://debug-agent.local",
        profile="xiaoD",
        identity="bot",
        lark_cli="lark-cli",
    )

    assert delivered == 1
    assert sent_args == [
        ["im", "+messages-reply", "--message-id", "om_1", "--markdown", "done", "--as", "bot"]
    ]
    assert marked_payloads == [
        (
            "http://debug-agent.local/api/lark/bot/badcase-drafts/draft-1/completion-notified",
            {"actor": "lark-bot-consumer", "note": "Completion notification sent."},
        )
    ]


def test_lark_bot_consumer_delivers_progress_notifications_once(monkeypatch) -> None:
    module = load_lark_bot_consumer_module()
    module._SENT_PROGRESS_KEYS.clear()
    sent_args: list[list[str]] = []
    marked_payloads: list[tuple[str, dict[str, object]]] = []

    def fake_get_json(url: str) -> dict[str, object]:
        assert (
            url
            == "http://debug-agent.local/api/lark/bot/badcase-drafts/progress-notifications?limit=20"
        )
        return {
            "notifications": [
                {
                    "draft": {"draft_id": "draft-1"},
                    "progress_key": "draft-1:baseline-running",
                    "payload": {
                        "delivery_args": [
                            "im",
                            "+messages-reply",
                            "--message-id",
                            "om_1",
                            "--msg-type",
                            "interactive",
                            "--content",
                            "{}",
                            "--as",
                            "bot",
                        ]
                    },
                }
            ]
        }

    monkeypatch.setattr(module, "get_json", fake_get_json)
    monkeypatch.setattr(
        module,
        "post_json",
        lambda url, payload: marked_payloads.append((url, payload)) or {},
    )
    monkeypatch.setattr(
        module,
        "run_lark_delivery_args",
        lambda **kwargs: sent_args.append(kwargs["args"]) or True,
    )

    first = module.deliver_progress_notifications(
        base_url="http://debug-agent.local",
        profile="xiaoD",
        identity="bot",
        lark_cli="lark-cli",
    )
    second = module.deliver_progress_notifications(
        base_url="http://debug-agent.local",
        profile="xiaoD",
        identity="bot",
        lark_cli="lark-cli",
    )

    assert first == 1
    assert second == 0
    assert len(sent_args) == 1
    assert marked_payloads == [
        (
            "http://debug-agent.local/api/lark/bot/badcase-drafts/draft-1/progress-notified",
            {
                "actor": "lark-bot-consumer",
                "progress_key": "draft-1:baseline-running",
                "note": "Progress notification sent.",
            },
        )
    ]


def test_lark_bot_consumer_marks_progress_panel_message_id(monkeypatch) -> None:
    module = load_lark_bot_consumer_module()
    module._SENT_PROGRESS_KEYS.clear()
    sent_args: list[list[str]] = []
    marked_payloads: list[tuple[str, dict[str, object]]] = []

    monkeypatch.setattr(
        module,
        "get_json",
        lambda url: {
            "notifications": [
                {
                    "draft": {"draft_id": "draft-1"},
                    "progress_key": "draft-1:baseline-running",
                    "task_panel_key": "xiaod-task-panel:job-1",
                    "payload": {
                        "delivery_mode": "send",
                        "delivery_args": [
                            "im",
                            "+messages-reply",
                            "--message-id",
                            "om_1",
                            "--msg-type",
                            "interactive",
                            "--content",
                            "{}",
                            "--as",
                            "bot",
                        ],
                    },
                }
            ]
        },
    )

    def fake_run_lark_delivery_args(**kwargs):
        sent_args.append(kwargs["args"])
        return {"message_id": "om_panel_1", "chat_id": "oc_1"}

    monkeypatch.setattr(module, "run_lark_delivery_args", fake_run_lark_delivery_args)
    monkeypatch.setattr(
        module,
        "post_json",
        lambda url, payload: marked_payloads.append((url, payload)) or {},
    )

    delivered = module.deliver_progress_notifications(
        base_url="http://debug-agent.local",
        profile="xiaoD",
        identity="bot",
        lark_cli="lark-cli",
    )

    assert delivered == 1
    assert sent_args == [
        [
            "im",
            "+messages-reply",
            "--message-id",
            "om_1",
            "--msg-type",
            "interactive",
            "--content",
            "{}",
            "--as",
            "bot",
        ]
    ]
    assert marked_payloads == [
        (
            "http://debug-agent.local/api/lark/bot/badcase-drafts/draft-1/progress-notified",
            {
                "actor": "lark-bot-consumer",
                "progress_key": "draft-1:baseline-running",
                "note": "Progress notification sent.",
                "panel_message_id": "om_panel_1",
            },
        )
    ]


def test_lark_bot_consumer_falls_back_when_progress_panel_update_fails(monkeypatch) -> None:
    module = load_lark_bot_consumer_module()
    module._SENT_PROGRESS_KEYS.clear()
    sent_args: list[list[str]] = []
    marked_payloads: list[tuple[str, dict[str, object]]] = []
    results: list[object] = [
        False,
        {"message_id": "om_panel_replacement", "chat_id": "oc_1"},
    ]

    monkeypatch.setattr(
        module,
        "get_json",
        lambda url: {
            "notifications": [
                {
                    "draft": {"draft_id": "draft-1"},
                    "progress_key": "draft-1:attribution-running",
                    "task_panel_key": "xiaod-task-panel:job-1",
                    "task_panel_message_id": "om_panel_old",
                    "payload": {
                        "delivery_mode": "update_message",
                        "delivery_args": [
                            "api",
                            "PATCH",
                            "/open-apis/im/v1/messages/om_panel_old",
                            "--data",
                            '{"content":"{}"}',
                            "--as",
                            "bot",
                        ],
                        "fallback_delivery_args": [
                            "im",
                            "+messages-reply",
                            "--message-id",
                            "om_1",
                            "--msg-type",
                            "interactive",
                            "--content",
                            "{}",
                            "--as",
                            "bot",
                        ],
                    },
                }
            ]
        },
    )

    def fake_run_lark_delivery_args(**kwargs):
        sent_args.append(kwargs["args"])
        return results.pop(0)

    monkeypatch.setattr(module, "run_lark_delivery_args", fake_run_lark_delivery_args)
    monkeypatch.setattr(
        module,
        "post_json",
        lambda url, payload: marked_payloads.append((url, payload)) or {},
    )

    delivered = module.deliver_progress_notifications(
        base_url="http://debug-agent.local",
        profile="xiaoD",
        identity="bot",
        lark_cli="lark-cli",
    )

    assert delivered == 1
    assert sent_args == [
        [
            "api",
            "PATCH",
            "/open-apis/im/v1/messages/om_panel_old",
            "--data",
            '{"content":"{}"}',
            "--as",
            "bot",
        ],
        [
            "im",
            "+messages-reply",
            "--message-id",
            "om_1",
            "--msg-type",
            "interactive",
            "--content",
            "{}",
            "--as",
            "bot",
        ],
    ]
    assert marked_payloads == [
        (
            "http://debug-agent.local/api/lark/bot/badcase-drafts/draft-1/progress-notified",
            {
                "actor": "lark-bot-consumer",
                "progress_key": "draft-1:attribution-running",
                "note": "Progress notification sent.",
                "panel_message_id": "om_panel_replacement",
            },
        )
    ]


def test_lark_bot_consumer_delivers_generic_notifications(monkeypatch) -> None:
    module = load_lark_bot_consumer_module()
    module._SENT_PROGRESS_KEYS.clear()
    sent_args: list[list[str]] = []
    marked_payloads: list[tuple[str, dict[str, object]]] = []

    def fake_get_json(url: str) -> dict[str, object]:
        assert url == "http://debug-agent.local/api/lark/bot/notifications?limit=20"
        return {
            "notifications": [
                {
                    "kind": "badcase_progress",
                    "draft_id": "draft-1",
                    "progress_key": "draft-1:baseline-running",
                    "payload": {
                        "delivery_args": [
                            "im",
                            "+messages-reply",
                            "--message-id",
                            "om_1",
                            "--msg-type",
                            "interactive",
                            "--content",
                            "{}",
                            "--as",
                            "bot",
                        ]
                    },
                },
                {
                    "kind": "badcase_completion",
                    "draft_id": "draft-1",
                    "payload": {
                        "delivery_args": [
                            "im",
                            "+messages-reply",
                            "--message-id",
                            "om_1",
                            "--markdown",
                            "done",
                            "--as",
                            "bot",
                        ]
                    },
                },
                {
                    "notification_id": "xiaod-run-progress:run-1:writeback-decision-pending-1",
                    "kind": "xiaod_run_progress",
                    "payload": {
                        "delivery_args": [
                            "im",
                            "+messages-reply",
                            "--message-id",
                            "om_2",
                            "--msg-type",
                            "interactive",
                            "--content",
                            "{}",
                            "--as",
                            "bot",
                        ]
                    },
                },
            ]
        }

    monkeypatch.setattr(module, "get_json", fake_get_json)
    monkeypatch.setattr(
        module,
        "post_json",
        lambda url, payload: marked_payloads.append((url, payload)) or {},
    )
    monkeypatch.setattr(
        module,
        "run_lark_delivery_args",
        lambda **kwargs: sent_args.append(kwargs["args"]) or True,
    )

    delivered = module.deliver_notifications(
        base_url="http://debug-agent.local",
        profile="xiaoD",
        identity="bot",
        lark_cli="lark-cli",
    )

    assert delivered == 3
    assert len(sent_args) == 3
    assert marked_payloads == [
        (
            "http://debug-agent.local/api/lark/bot/badcase-drafts/draft-1/progress-notified",
            {
                "actor": "lark-bot-consumer",
                "progress_key": "draft-1:baseline-running",
                "note": "Progress notification sent.",
            },
        ),
        (
            "http://debug-agent.local/api/lark/bot/badcase-drafts/draft-1/completion-notified",
            {"actor": "lark-bot-consumer", "note": "Completion notification sent."},
        ),
        (
            "http://debug-agent.local/api/lark/bot/notification-outbox/xiaod-run-progress:run-1:writeback-decision-pending-1/sent",
            {"actor": "lark-bot-consumer", "note": "Notification outbox item sent."},
        ),
    ]


def test_lark_bot_consumer_marks_completion_delivery_failed(monkeypatch) -> None:
    module = load_lark_bot_consumer_module()
    marked_payloads: list[tuple[str, dict[str, object]]] = []

    def fake_get_json(url: str) -> dict[str, object]:
        assert (
            url
            == "http://debug-agent.local/api/lark/bot/badcase-drafts/completion-notifications?limit=20"
        )
        return {
            "notifications": [
                {
                    "draft": {"draft_id": "draft-1"},
                    "payload": {
                        "delivery_args": [
                            "im",
                            "+messages-reply",
                            "--message-id",
                            "om_invalid",
                            "--markdown",
                            "done",
                        ]
                    },
                }
            ]
        }

    def fake_post_json(url: str, payload: dict[str, object]) -> dict[str, object]:
        marked_payloads.append((url, payload))
        return {"status": "submitted"}

    monkeypatch.setattr(module, "get_json", fake_get_json)
    monkeypatch.setattr(module, "run_lark_delivery_args", lambda **kwargs: False)
    monkeypatch.setattr(module, "post_json", fake_post_json)

    delivered = module.deliver_completion_notifications(
        base_url="http://debug-agent.local",
        profile="xiaoD",
        identity="bot",
        lark_cli="lark-cli",
    )

    assert delivered == 0
    assert module.delivery_target_label(["--message-id", "om_invalid"]) == "--message-id om_invalid"
    assert marked_payloads == [
        (
            "http://debug-agent.local/api/lark/bot/badcase-drafts/draft-1/completion-delivery-failed",
            {
                "actor": "lark-bot-consumer",
                "note": "Completion notification delivery failed for --message-id om_invalid.",
                "error_message": "lark-cli delivery failed; see consumer stderr for details.",
                "max_attempts": 3,
            },
        )
    ]


def test_lark_bot_consumer_marks_outbox_delivery_failed(monkeypatch) -> None:
    module = load_lark_bot_consumer_module()
    marked_payloads: list[tuple[str, dict[str, object]]] = []

    def fake_post_json(url: str, payload: dict[str, object]) -> dict[str, object]:
        marked_payloads.append((url, payload))
        return {"status": "pending"}

    monkeypatch.setattr(module, "run_lark_delivery_args", lambda **kwargs: False)
    monkeypatch.setattr(module, "post_json", fake_post_json)

    delivered = module.deliver_outbox_notification(
        notification={
            "notification_id": "xiaod-run-progress:run-1:starting",
            "payload": {
                "delivery_args": [
                    "im",
                    "+messages-reply",
                    "--message-id",
                    "om_invalid",
                    "--markdown",
                    "starting",
                ]
            },
        },
        base_url="http://debug-agent.local",
        profile="xiaoD",
        identity="bot",
        lark_cli="lark-cli",
    )

    assert delivered is False
    assert marked_payloads == [
        (
            "http://debug-agent.local/api/lark/bot/notification-outbox/"
            "xiaod-run-progress:run-1:starting/failed",
            {
                "actor": "lark-bot-consumer",
                "note": "Notification outbox delivery failed for --message-id om_invalid.",
                "error_message": "lark-cli delivery failed; see consumer stderr for details.",
                "max_attempts": 3,
            },
        )
    ]
