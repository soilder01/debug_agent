# ruff: noqa: F403,F405
from tests.scripts.common import *


def test_lark_bot_consumer_deduplicates_replayed_message_events(monkeypatch) -> None:
    module = load_lark_bot_consumer_module()
    module._SEEN_EVENT_KEYS.clear()
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_post_json(url: str, payload: dict[str, object]) -> dict[str, object]:
        calls.append((url, payload))
        return {"handled": True, "reply": {"markdown": "我是小D"}}

    monkeypatch.setattr(module, "post_json", fake_post_json)
    monkeypatch.setattr(module, "reply_markdown_to_event", lambda **kwargs: None)
    event = {
        "type": "im.message.receive_v1",
        "event_id": "evt-replay-1",
        "chat_type": "p2p",
        "message_id": "om_replay_1",
        "content": json.dumps({"text": "你是？"}, ensure_ascii=False),
    }

    for _ in range(2):
        module.handle_event_line(
            line=json.dumps(event),
            base_url="http://debug-agent.local",
            profile="xiaoD",
            identity="bot",
            send_replies=True,
            lark_cli="lark-cli",
        )

    assert len(calls) == 1


def test_lark_bot_consumer_persists_seen_message_ids_across_restarts(
    monkeypatch,
    tmp_path,
) -> None:
    module = load_lark_bot_consumer_module()
    module._SEEN_EVENT_KEYS.clear()
    module.configure_persistent_event_dedup(str(tmp_path / "seen-events.jsonl"))
    calls: list[tuple[str, dict[str, object]]] = []
    delivered_args: list[list[str]] = []

    def fake_post_json(url: str, payload: dict[str, object]) -> dict[str, object]:
        calls.append((url, payload))
        return {
            "handled": True,
            "reply": {
                "delivery_args": [
                    "im",
                    "+messages-reply",
                    "--message-id",
                    "om_replayed_after_restart",
                    "--markdown",
                    "我是小D",
                    "--as",
                    "bot",
                ],
                "markdown": "我是小D",
            },
        }

    monkeypatch.setattr(module, "post_json", fake_post_json)
    monkeypatch.setattr(
        module,
        "run_lark_delivery_args",
        lambda **kwargs: delivered_args.append(kwargs["args"]) or True,
    )
    event = {
        "type": "im.message.receive_v1",
        "event_id": "evt-before-restart",
        "chat_type": "p2p",
        "message_id": "om_replayed_after_restart",
        "content": json.dumps({"text": "你是？"}, ensure_ascii=False),
    }

    module.handle_event_line(
        line=json.dumps(event),
        base_url="http://debug-agent.local",
        profile="xiaoD",
        identity="bot",
        send_replies=True,
        lark_cli="lark-cli",
    )
    module._SEEN_EVENT_KEYS.clear()
    module._PERSISTENT_EVENT_KEYS = None
    replayed = {**event, "event_id": "evt-after-restart"}
    module.handle_event_line(
        line=json.dumps(replayed),
        base_url="http://debug-agent.local",
        profile="xiaoD",
        identity="bot",
        send_replies=True,
        lark_cli="lark-cli",
    )

    assert len(calls) == 1
    assert len(delivered_args) == 1


def test_lark_bot_consumer_deduplicates_replayed_card_actions(monkeypatch) -> None:
    module = load_lark_bot_consumer_module()
    module._SEEN_EVENT_KEYS.clear()
    posted: list[tuple[str, dict[str, object]]] = []

    def fake_post_json(url: str, payload: dict[str, object]) -> dict[str, object]:
        posted.append((url, payload))
        return {"handled": True, "action": "confirm_badcase_draft"}

    monkeypatch.setattr(module, "post_json", fake_post_json)
    event = {
        "schema": "2.0",
        "header": {"event_type": "card.action.trigger", "event_id": "evt-card-1"},
        "event": {
            "operator": {"open_id": "ou_1"},
            "action": {
                "value": {
                    "action": "confirm_badcase_draft",
                    "draft_id": "draft-1",
                }
            },
        },
    }

    for _ in range(2):
        module.handle_event_line(
            line=json.dumps(event),
            base_url="http://debug-agent.local",
            profile="xiaoD",
            identity="bot",
            send_replies=True,
            lark_cli="lark-cli",
        )

    assert len(posted) == 1


def test_lark_bot_consumer_card_dedup_includes_pending_command_id() -> None:
    module = load_lark_bot_consumer_module()
    first = {
        "schema": "2.0",
        "header": {"event_type": "card.action.trigger"},
        "event": {
            "operator": {"open_id": "ou_1"},
            "action": {
                "value": {
                    "action": "confirm_pending_command",
                    "command_id": "command-1",
                }
            },
        },
    }
    second = {
        "schema": "2.0",
        "header": {"event_type": "card.action.trigger"},
        "event": {
            "operator": {"open_id": "ou_1"},
            "action": {
                "value": {
                    "action": "confirm_pending_command",
                    "command_id": "command-2",
                }
            },
        },
    }

    assert module.event_dedup_key(first) != module.event_dedup_key(second)
