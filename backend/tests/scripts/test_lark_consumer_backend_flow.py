# ruff: noqa: F403,F405
from tests.scripts.common import *


def test_lark_bot_consumer_converts_sdk_message_event_to_flat_event() -> None:
    module = load_lark_bot_consumer_module()
    data = SimpleNamespace(
        header=SimpleNamespace(
            event_type="im.message.receive_v1",
            event_id="evt-1",
            tenant_key="tenant-1",
            create_time="1700000000000",
        ),
        event=SimpleNamespace(
            message=SimpleNamespace(
                message_id="om_1",
                chat_id="oc_1",
                chat_type="p2p",
                message_type="text",
                content=json.dumps({"text": "确认提交"}, ensure_ascii=False),
                create_time="1700000000001",
                mentions=[],
            ),
            sender=SimpleNamespace(
                sender_id=SimpleNamespace(open_id="ou_1", user_id="", union_id="")
            ),
        ),
    )

    event = module.sdk_message_event_to_flat_event(data)

    assert event["type"] == "im.message.receive_v1"
    assert event["message_id"] == "om_1"
    assert event["chat_id"] == "oc_1"
    assert event["sender_id"] == "ou_1"
    assert module.event_text(event) == "确认提交"


def test_lark_bot_consumer_handles_sdk_message_event_in_background(monkeypatch) -> None:
    module = load_lark_bot_consumer_module()
    started = module.threading.Event()
    release = module.threading.Event()
    calls: list[dict[str, object]] = []

    def fake_handle_event_line(**kwargs: object) -> None:
        started.set()
        release.wait(timeout=2)
        calls.append(dict(kwargs))

    monkeypatch.setattr(module, "handle_event_line", fake_handle_event_line)
    data = SimpleNamespace(
        header=SimpleNamespace(
            event_type="im.message.receive_v1",
            event_id="evt-1",
            tenant_key="tenant-1",
            create_time="1700000000000",
        ),
        event=SimpleNamespace(
            message=SimpleNamespace(
                message_id="om_1",
                chat_id="oc_1",
                chat_type="group",
                message_type="post",
                content=json.dumps(
                    {
                        "content": [
                            [
                                {"tag": "at", "user_name": "小D"},
                                {"tag": "text", "text": " 查看状态"},
                            ]
                        ]
                    },
                    ensure_ascii=False,
                ),
                create_time="1700000000001",
                mentions=[{"id": "cli_xiaod", "name": "小D"}],
            ),
            sender=SimpleNamespace(
                sender_id=SimpleNamespace(open_id="ou_1", user_id="", union_id="")
            ),
        ),
    )

    thread = module.handle_sdk_message_event(
        data=data,
        base_url="http://debug-agent.local",
        profile="xiaoD",
        identity="bot",
        lark_cli="lark-cli",
    )

    assert started.wait(timeout=1)
    assert thread.is_alive()
    release.set()
    thread.join(timeout=1)
    assert calls
    assert calls[0]["base_url"] == "http://debug-agent.local"
    assert calls[0]["profile"] == "xiaoD"
    assert '"message_id": "om_1"' in calls[0]["line"]


def test_lark_bot_consumer_converts_sdk_card_action_event_to_backend_payload() -> None:
    module = load_lark_bot_consumer_module()
    data = SimpleNamespace(
        header=SimpleNamespace(event_type="card.action.trigger", event_id="evt-2"),
        event=SimpleNamespace(
            action=SimpleNamespace(
                value={"action": "confirm_badcase_draft", "draft_id": "draft-1"},
                tag="button",
            ),
            operator=SimpleNamespace(open_id="ou_1"),
        ),
    )

    payload = module.sdk_card_action_event_to_payload(data)

    assert payload["schema"] == "2.0"
    assert payload["header"]["event_type"] == "card.action.trigger"
    assert payload["event"]["action"]["value"] == {
        "action": "confirm_badcase_draft",
        "draft_id": "draft-1",
    }


def test_lark_bot_consumer_processes_group_messages_only_when_addressed() -> None:
    module = load_lark_bot_consumer_module()
    group_event = {"chat_type": "group"}

    assert not module.should_process_event(event=group_event, text="帮我调试这个识别错误")
    assert module.should_process_event(event=group_event, text="@小D 帮我调试这个识别错误")
    assert module.strip_bot_mention_prefix("@小D 帮我调试这个识别错误") == "帮我调试这个识别错误"

    mentioned_event = {"chat_type": "group", "mentions": [{"name": "小D"}]}
    assert module.should_process_event(event=mentioned_event, text="帮我调试这个识别错误")


def test_lark_bot_consumer_uses_backend_turn_handle_before_local_actions(monkeypatch) -> None:
    module = load_lark_bot_consumer_module()
    module.BACKEND_TURN_HANDLE_ENABLED = True
    calls: list[tuple[str, dict[str, object]]] = []
    delivered_args: list[list[str]] = []

    def fake_post_json(url: str, payload: dict[str, object]) -> dict[str, object]:
        calls.append((url, payload))
        return {
            "handled": True,
            "decision": {"kind": "help", "clean_text": "/", "reason": "help_request"},
            "reply": {
                "delivery_args": [
                    "im",
                    "+messages-reply",
                    "--message-id",
                    "om_1",
                    "--markdown",
                    "小D使用说明",
                    "--as",
                    "bot",
                ],
                "markdown": "小D使用说明",
            },
        }

    monkeypatch.setattr(module, "post_json", fake_post_json)
    monkeypatch.setattr(
        module,
        "run_lark_delivery_args",
        lambda **kwargs: delivered_args.append(kwargs["args"]) or True,
    )

    module.handle_event_line(
        line=json.dumps(
            {"chat_type": "p2p", "message_id": "om_1", "content": json.dumps({"text": "/"})}
        ),
        base_url="http://debug-agent.local",
        profile="xiaoD",
        identity="bot",
        send_replies=True,
        lark_cli="lark-cli",
    )

    assert calls == [
        (
            "http://debug-agent.local/api/lark/bot/xiaod/turns/handle",
            {
                "text": "/",
                "has_attachments": False,
                "actor": "",
                "open_id": "",
                "chat_id": "",
                "message_id": "om_1",
                "tenant_key": "",
                "identity": "bot",
                "profile": "xiaoD",
                "attachments": [],
                "resolve_link_content": True,
            },
        )
    ]
    assert delivered_args == [
        [
            "im",
            "+messages-reply",
            "--message-id",
            "om_1",
            "--markdown",
            "小D使用说明",
            "--as",
            "bot",
        ]
    ]


def test_lark_bot_consumer_delegates_badcase_draft_save_to_backend_handle(monkeypatch) -> None:
    module = load_lark_bot_consumer_module()
    module.BACKEND_TURN_HANDLE_ENABLED = True
    calls: list[tuple[str, dict[str, object]]] = []
    delivered_args: list[list[str]] = []

    def fake_post_json(url: str, payload: dict[str, object]) -> dict[str, object]:
        calls.append((url, payload))
        return {
            "handled": True,
            "decision": {"kind": "save_badcase_draft", "clean_text": str(payload["text"])},
            "reply": {
                "delivery_args": [
                    "im",
                    "+messages-reply",
                    "--message-id",
                    "om_1",
                    "--markdown",
                    "我已把这条信息记录为 badcase 草稿。",
                    "--as",
                    "bot",
                ],
                "markdown": "我已把这条信息记录为 badcase 草稿。",
            },
        }

    monkeypatch.setattr(module, "post_json", fake_post_json)
    monkeypatch.setattr(
        module,
        "run_lark_delivery_args",
        lambda **kwargs: delivered_args.append(kwargs["args"]) or True,
    )

    sheet_url = "https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123"
    module.handle_event_line(
        line=json.dumps(
            {"chat_type": "p2p", "message_id": "om_1", "content": json.dumps({"text": sheet_url})}
        ),
        base_url="http://debug-agent.local",
        profile="xiaoD",
        identity="bot",
        send_replies=True,
        lark_cli="lark-cli",
    )

    assert calls[0] == (
        "http://debug-agent.local/api/lark/bot/xiaod/turns/handle",
        {
            "text": sheet_url,
            "has_attachments": False,
            "actor": "",
            "open_id": "",
            "chat_id": "",
            "message_id": "om_1",
            "tenant_key": "",
            "identity": "bot",
            "profile": "xiaoD",
            "attachments": [],
            "resolve_link_content": True,
        },
    )
    assert delivered_args == [
        [
            "im",
            "+messages-reply",
            "--message-id",
            "om_1",
            "--markdown",
            "我已把这条信息记录为 badcase 草稿。",
            "--as",
            "bot",
        ]
    ]


def test_lark_bot_consumer_does_not_run_local_business_fallback_when_backend_handle_fails(
    monkeypatch,
) -> None:
    module = load_lark_bot_consumer_module()
    module.BACKEND_TURN_HANDLE_ENABLED = True
    replies: list[str] = []

    def fake_post_json(url: str, payload: dict[str, object]) -> dict[str, object]:
        assert url == "http://debug-agent.local/api/lark/bot/xiaod/turns/handle"
        raise RuntimeError("connection refused")

    monkeypatch.setattr(module, "post_json", fake_post_json)
    monkeypatch.setattr(
        module,
        "reply_markdown_to_event",
        lambda **kwargs: replies.append(kwargs["markdown"]),
    )

    sheet_url = "https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123"
    module.handle_event_line(
        line=json.dumps(
            {"chat_type": "p2p", "message_id": "om_1", "content": json.dumps({"text": sheet_url})}
        ),
        base_url="http://debug-agent.local",
        profile="xiaoD",
        identity="bot",
        send_replies=True,
        lark_cli="lark-cli",
    )

    assert len(replies) == 1
    assert "后端暂时不可用" in replies[0]
    assert "不会在长连接脚本里另跑一套业务逻辑" in replies[0]


def test_lark_bot_consumer_plain_reply_uses_text_message(monkeypatch) -> None:
    module = load_lark_bot_consumer_module()
    commands: list[list[str]] = []

    class Result:
        returncode = 0
        stderr = ""

    def fake_run(command: list[str], **kwargs) -> Result:
        commands.append(command)
        return Result()

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(module, "resolve_executable", lambda name: name)

    module.send_reply(
        lark_cli="lark-cli",
        profile="xiaoD",
        identity="bot",
        message_id="om_1",
        markdown="我是小D，能帮你处理 Debug Agent badcase。",
    )

    assert commands
    command = commands[0]
    assert command[:5] == ["lark-cli", "--profile", "xiaoD", "im", "+messages-reply"]
    assert "--message-id" in command
    assert command[command.index("--message-id") + 1] == "om_1"
    assert "--text" in command
    assert command[command.index("--text") + 1] == "我是小D，能帮你处理 Debug Agent badcase。"
    assert "--markdown" not in command
    assert "--idempotency-key" in command
    assert len(command[command.index("--idempotency-key") + 1]) <= 40
    assert command[-2:] == ["--as", "bot"]


def test_lark_bot_consumer_plain_reply_strips_lark_invalid_control_chars(monkeypatch) -> None:
    module = load_lark_bot_consumer_module()
    commands: list[list[str]] = []

    class Result:
        returncode = 0
        stderr = ""

    monkeypatch.setattr(
        module.subprocess, "run", lambda command, **kwargs: commands.append(command) or Result()
    )
    monkeypatch.setattr(module, "resolve_executable", lambda name: name)

    dirty_text = "我是小D\u0085，可以帮你处理 badcase。\u0000\n第二行"
    module.send_reply(
        lark_cli="lark-cli",
        profile="xiaoD",
        identity="bot",
        message_id="om_1",
        markdown=dirty_text,
    )

    sent_text = commands[0][commands[0].index("--text") + 1]
    assert sent_text == "我是小D，可以帮你处理 badcase。\n第二行"
    assert "\u0085" not in sent_text
    assert "\u0000" not in sent_text
