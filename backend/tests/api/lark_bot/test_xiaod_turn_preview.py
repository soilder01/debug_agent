# ruff: noqa: F403,F405
from tests.api.lark_bot.common import *


def test_xiaod_turn_preview_routes_followup_before_general_chat() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/lark/bot/xiaod/turns/preview",
        json={"text": "然后呢？"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "badcase_draft_followup"
    assert body["reason"] == "latest_badcase_draft_status"
    assert body["backend_command"] == ""


def test_xiaod_turn_preview_maps_existing_product_command() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/lark/bot/xiaod/turns/preview",
        json={"text": "查看 worker 状态"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "backend_command"
    assert body["backend_command"] == "/debug worker"
    assert body["reason"] == "mapped_to_debug_agent_api"


@pytest.mark.parametrize(
    ("text", "backend_command"),
    [
        ("查看观测总览", "/debug observability"),
        ("最近任务列表", "/debug jobs"),
        ("批次对比", "/debug batch-comparison"),
        ("待确认命令有哪些", "/debug pending"),
        ("产物保留状态", "/debug artifact-retention"),
        ("样本列表", "/debug cases"),
        ("飞书表格状态", "/debug sheet-status"),
        ("权限检查", "/debug scope-check"),
        ("运维支持包", "/debug support-bundle"),
        ("推荐动作状态 job-123", "/debug recommended-actions job-123"),
        ("人工交接 job-123", "/debug human-handoffs job-123"),
        ("策略跟进 job-123", "/debug strategy-followups job-123"),
        ("定向探针 job-123", "/debug targeted-probes job-123"),
        (
            "同步表格 https://example.larkoffice.com/sheets/abc?sheet=def",
            "/debug spreadsheet sync https://example.larkoffice.com/sheets/abc?sheet=def",
        ),
        (
            "重跑表格 https://example.larkoffice.com/sheets/abc?sheet=def",
            "/debug spreadsheet rerun https://example.larkoffice.com/sheets/abc?sheet=def",
        ),
        ("写回任务 job-123", "/debug writeback job-123"),
        ("base写回 job-123", "/debug base-writeback job-123"),
        ("接受推荐动作 job-123 0", "/debug recommended-actions status job-123 0 accepted"),
        ("验证推荐动作 job-123 0", "/debug recommended-actions verify job-123 0"),
        (
            "人工交接已解决 job-123 multimodal:conflict:1",
            "/debug human-handoffs status job-123 multimodal:conflict:1 resolved",
        ),
        ("创建策略跟进 job-123 stability", "/debug strategy-followups run job-123 stability"),
        (
            "创建定向探针 job-123 multimodal:conflict:1",
            "/debug targeted-probes run job-123 multimodal:conflict:1",
        ),
        ("自动闭环 job-123", "/debug auto-closure job-123"),
        ("自动闭环报告 job-123", "/debug auto-closure-report job-123"),
    ],
)


def test_xiaod_turn_preview_maps_read_only_product_capabilities(
    text: str, backend_command: str
) -> None:
    client = TestClient(app)

    response = client.post(
        "/api/lark/bot/xiaod/turns/preview",
        json={"text": text},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "backend_command"
    assert body["backend_command"] == backend_command


def test_xiaod_turn_preview_preserves_chat_model_override() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/lark/bot/xiaod/turns/preview",
        json={"text": "model_id=ep-user 解释一下报告"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "assistant_chat"
    assert body["assistant_question"] == "解释一下报告"
    assert body["assistant_model_id"] == "ep-user"


def test_xiaod_turn_handle_returns_help_reply_payload() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={"text": "/", "message_id": "om_1", "open_id": "ou_1", "chat_id": "oc_1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["handled"] is True
    assert body["decision"]["kind"] == "help"
    assert "小D使用说明" in body["reply"]["markdown"]
    assert body["reply"]["target_type"] == "message"
    assert body["reply"]["delivery_args"][:4] == ["im", "+messages-reply", "--message-id", "om_1"]
    assert "--dry-run" not in body["reply"]["delivery_args"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("/debug observability", "观测总览"),
        ("/debug artifact-retention", "产物保留"),
        ("/debug cases", "样本列表"),
        ("/debug sheet-status", "飞书表格连接"),
        ("/debug scope-check", "Lark Scope 检查"),
        ("/debug export", "DebugJob 导出包"),
        ("/debug support-bundle", "运维支持包"),
        ("/debug database-backup", "数据库备份包"),
        ("/debug jobs", "任务列表"),
        ("/debug batches", "批次列表"),
        ("/debug batch-comparison", "批次对比"),
        ("/debug pending", "待确认机器人命令"),
    ],
)


def test_xiaod_turn_handle_returns_read_only_product_summaries(text: str, expected: str) -> None:
    client = TestClient(app)

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={"text": text, "message_id": "om_1", "open_id": "ou_1", "chat_id": "oc_1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["handled"] is True
    assert expected in body["reply"]["markdown"]
    assert body["reply"]["target_type"] == "message"


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("recommended-actions", "推荐动作状态"),
        ("human-handoffs", "人工交接状态"),
        ("strategy-followups", "策略跟进任务"),
        ("targeted-probes", "定向探针任务"),
    ],
)


def test_xiaod_turn_handle_returns_job_deep_read_summaries(command: str, expected: str) -> None:
    client = TestClient(app)
    submit_response = client.post("/cases/handwrite233/debug-jobs")
    assert submit_response.status_code == 202
    job_id = submit_response.json()["job_id"]

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": f"/debug {command} {job_id}",
            "message_id": "om_1",
            "open_id": "ou_1",
            "chat_id": "oc_1",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["handled"] is True
    assert expected in body["reply"]["markdown"]
    assert body["reply"]["target_type"] == "message"


def test_xiaod_turn_handle_answers_product_read_command() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={"text": "查看 worker 状态", "message_id": "om_1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["handled"] is True
    assert body["decision"]["kind"] == "backend_command"
    assert "Worker 队列状态" in body["reply"]["markdown"]
    assert "Worker：" in body["reply"]["markdown"]
    assert body["reply"]["delivery_args"][:4] == ["im", "+messages-reply", "--message-id", "om_1"]
