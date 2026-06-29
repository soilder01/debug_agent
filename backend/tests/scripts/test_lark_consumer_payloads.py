# ruff: noqa: F403,F405
from tests.scripts.common import *


def test_lark_bot_consumer_request_json_wraps_timeout(monkeypatch) -> None:
    module = load_lark_bot_consumer_module()

    def raise_timeout(*args, **kwargs):
        raise TimeoutError("timed out")

    monkeypatch.setattr(module.urllib_request, "urlopen", raise_timeout)
    request = module.urllib_request.Request("http://127.0.0.1:8000/slow", method="GET")

    with pytest.raises(RuntimeError, match="request timed out"):
        module.request_json(request)


def test_lark_bot_consumer_extracts_complete_badcase_text_from_event_content() -> None:
    module = load_lark_bot_consumer_module()
    text = "\n".join(
        [
            "原始输入：https://example.com/a.png",
            '模型输出：{"answer":"3"}',
            '正确答案：{"answer":"8"}',
            "错误现象：把 8 识别成 3",
        ]
    )
    event = {
        "chat_type": "p2p",
        "content": json.dumps({"text": text}, ensure_ascii=False),
    }

    assert module.event_text(event) == text
    assert module.should_process_event(event=event, text=text)


def test_lark_bot_consumer_flattens_rich_text_badcase_content() -> None:
    module = load_lark_bot_consumer_module()
    event = {
        "chat_type": "p2p",
        "content": json.dumps(
            {
                "content": [
                    [
                        {"tag": "text", "text": "原始输入："},
                        {"tag": "a", "href": "https://example.com/a.png"},
                    ],
                    [{"tag": "text", "text": '模型输出：{"answer":"3"}'}],
                    [{"tag": "text", "text": '正确答案：{"answer":"8"}'}],
                    [{"tag": "text", "text": "错误现象：把 8 识别成 3"}],
                ]
            },
            ensure_ascii=False,
        ),
    }

    text = module.event_text(event)

    assert text == "\n".join(
        [
            "原始输入：https://example.com/a.png",
            '模型输出：{"answer":"3"}',
            '正确答案：{"answer":"8"}',
            "错误现象：把 8 识别成 3",
        ]
    )


def test_lark_bot_consumer_extracts_image_and_file_attachments() -> None:
    module = load_lark_bot_consumer_module()
    event = {
        "attachments": [{"type": "file", "file_key": "file_v2_1", "name": "sample.json"}],
        "content": json.dumps(
            {
                "content": [
                    [{"tag": "text", "text": "帮我调试这个"}],
                    [{"tag": "img", "image_key": "img_v2_1", "name": "input.png"}],
                    [{"tag": "a", "href": "https://example.com/not-an-attachment"}],
                ]
            },
            ensure_ascii=False,
        ),
    }

    attachments = module.event_attachments(event)

    assert attachments == [
        {"type": "file", "file_key": "file_v2_1", "name": "sample.json"},
        {"type": "img", "image_key": "img_v2_1", "name": "input.png"},
    ]


def test_lark_bot_consumer_forwards_card_action_events(monkeypatch) -> None:
    module = load_lark_bot_consumer_module()
    module._SEEN_EVENT_KEYS.clear()
    posted: list[tuple[str, dict[str, object]]] = []
    delivered_args: list[list[str]] = []

    event = {
        "header": {"event_type": "card.action.trigger"},
        "event": {
            "action": {
                "value": {
                    "action": "confirm_badcase_draft",
                    "draft_id": "draft-1",
                }
            }
        },
    }

    def fake_post_json(url: str, payload: dict[str, object]) -> dict[str, object]:
        posted.append((url, payload))
        return {
            "handled": True,
            "action": "confirm_badcase_draft",
            "reply": {
                "delivery_args": [
                    "im",
                    "+messages-reply",
                    "--message-id",
                    "om_1",
                    "--markdown",
                    "已收到确认，Debug 任务已提交。",
                ]
            },
        }

    monkeypatch.setattr(module, "post_json", fake_post_json)
    monkeypatch.setattr(
        module,
        "run_lark_delivery_args",
        lambda **kwargs: delivered_args.append(kwargs["args"]) or True,
    )

    module.handle_event_line(
        line=json.dumps(event),
        base_url="http://debug-agent.local",
        profile="xiaoD",
        identity="bot",
        send_replies=True,
        lark_cli="lark-cli",
    )

    assert module.is_card_action_event(event)
    assert posted == [("http://debug-agent.local/api/lark/bot/events", event)]
    assert delivered_args == [
        [
            "im",
            "+messages-reply",
            "--message-id",
            "om_1",
            "--markdown",
            "已收到确认，Debug 任务已提交。",
        ]
    ]


def test_lark_bot_consumer_flattens_at_mentions_from_rich_text() -> None:
    module = load_lark_bot_consumer_module()
    event = {
        "chat_type": "group",
        "content": json.dumps(
            {
                "content": [
                    [{"tag": "at", "user_name": "小D"}, {"tag": "text", "text": " 查看状态"}]
                ]
            },
            ensure_ascii=False,
        ),
    }

    text = module.event_text(event)

    assert text == "@小D查看状态"
    assert module.should_process_event(event=event, text=text)
