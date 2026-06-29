# ruff: noqa: F403,F405
from tests.api.lark_bot.common import *


@pytest.mark.parametrize(
    ("text", "action_kind"),
    [
        (
            "/debug spreadsheet sync https://example.larkoffice.com/sheets/abc?sheet=def",
            "spreadsheet_sync",
        ),
        (
            "/debug spreadsheet rerun https://example.larkoffice.com/sheets/abc?sheet=def def row-1,row-2",
            "spreadsheet_rerun",
        ),
        ("/debug writeback job-123", "spreadsheet_writeback_confirmation"),
        ("/debug base-writeback job-123", "base_writeback_confirmation"),
        (
            "/debug recommended-actions status job-123 0 accepted",
            "recommended_action_status_update",
        ),
        ("/debug recommended-actions verify job-123 0", "recommended_action_verification"),
        (
            "/debug human-handoffs status job-123 multimodal:conflict:1 resolved",
            "human_handoff_status_update",
        ),
        ("/debug strategy-followups run job-123 stability", "strategy_followup_job"),
        ("/debug targeted-probes run job-123 multimodal:conflict:1", "targeted_probe_job"),
        ("/debug auto-closure job-123", "auto_closure"),
        ("/debug auto-closure-report job-123 --writeback", "auto_closure_report"),
    ],
)


def test_xiaod_turn_handle_creates_pending_command_for_write_capabilities(
    text: str, action_kind: str
) -> None:
    client = TestClient(app)

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={"text": text, "message_id": "om_1", "open_id": "ou_1", "chat_id": "oc_1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["handled"] is True
    assert body["decision"]["kind"] == "backend_command"
    assert body["reply"]["action_kind"] == action_kind
    assert "待确认编号" in body["reply"]["markdown"]
    commands = client.get("/api/lark/bot/commands/pending").json()["commands"]
    assert any(command["action_kind"] == action_kind for command in commands)


def test_xiaod_turn_handle_creates_pending_command_for_product_write_command() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "启动 worker",
            "actor": "ou_operator",
            "open_id": "ou_operator",
            "chat_id": "oc_1",
            "message_id": "om_1",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["handled"] is True
    assert body["decision"]["kind"] == "backend_command"
    assert "待确认编号" in body["reply"]["markdown"]
    assert "确认前不会启动任务" in body["reply"]["markdown"]
    commands = client.get("/api/lark/bot/commands/pending").json()["commands"]
    assert len(commands) == 1
    assert commands[0]["action_kind"] == "worker_start"
    assert commands[0]["status"] == "pending"


def test_xiaod_turn_handle_default_deletes_expired_pending_before_new_write_command() -> None:
    client = TestClient(app)
    unique = uuid4().hex
    open_id = f"ou_expired_{unique}"
    chat_id = f"oc_expired_{unique}"

    first = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "启动 worker",
            "actor": open_id,
            "open_id": open_id,
            "chat_id": chat_id,
            "message_id": f"om_old_{unique}",
        },
    )
    assert first.status_code == 200
    old_pending = routes.job_repository.get_active_lark_bot_pending_command_for_user(
        tenant_key="",
        chat_id=chat_id,
        open_id=open_id,
    )
    assert old_pending is not None
    with routes.session_factory() as session:
        row = session.get(LarkBotPendingCommandRow, old_pending.command_id)
        assert row is not None
        row.expires_at = "2000-01-01T00:00:00+00:00"
        session.commit()

    second = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": (
                "处理这个表前10行："
                "https://example.larkoffice.com/sheets/abc?sheet=def"
            ),
            "actor": open_id,
            "open_id": open_id,
            "chat_id": chat_id,
            "message_id": f"om_new_{unique}",
        },
    )

    assert second.status_code == 200
    body = second.json()
    assert body["decision"]["kind"] == "backend_command"
    assert body["reply"]["action_kind"] == "spreadsheet_rerun"
    assert body["reply"]["message_type"] == "interactive"
    old_after = routes.job_repository.get_lark_bot_pending_command(old_pending.command_id)
    assert old_after is not None
    assert old_after.status == "default_deleted"
    audits = routes.job_repository.list_xiaod_command_audits(command_id=old_pending.command_id)
    assert [audit.event_kind for audit in audits] == ["command_default_deleted"]
    commands = client.get("/api/lark/bot/commands/pending").json()["commands"]
    user_pending = [
        command
        for command in commands
        if command["open_id"] == open_id and command["chat_id"] == chat_id and command["status"] == "pending"
    ]
    assert len(user_pending) == 1
    assert user_pending[0]["message_id"] == f"om_new_{unique}"
    assert user_pending[0]["action_kind"] == "spreadsheet_rerun"


def test_xiaod_timeout_sweeper_default_deletes_expired_cleanup_decision() -> None:
    client = TestClient(app)
    unique = uuid4().hex
    open_id = f"ou_cleanup_sweep_{unique}"
    chat_id = f"oc_cleanup_sweep_{unique}"

    first = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "启动 worker",
            "actor": open_id,
            "open_id": open_id,
            "chat_id": chat_id,
            "message_id": f"om_cleanup_sweep_{unique}",
        },
    )
    assert first.status_code == 200
    pending = routes.job_repository.get_active_lark_bot_pending_command_for_user(
        tenant_key="",
        chat_id=chat_id,
        open_id=open_id,
    )
    assert pending is not None
    decision = routes.job_repository.create_xiaod_pending_decision(
        decision_id=f"decision-cleanup-{unique}",
        tenant_key="",
        chat_id=chat_id,
        open_id=open_id,
        decision_kind="retain_or_delete_unexecuted_command",
        command_id=pending.command_id,
        payload={"action_kind": pending.action_kind},
        note="User declined continuation; waiting for retain/delete.",
        expires_at="2000-01-01T00:00:00+00:00",
    )

    result = routes.sweep_expired_xiaod_pending_decisions()

    assert result["default_deleted"] == 1
    cleaned = routes.job_repository.get_lark_bot_pending_command(pending.command_id)
    assert cleaned is not None
    assert cleaned.status == "default_deleted"
    assert (
        routes.job_repository.get_pending_xiaod_decision(
            tenant_key="",
            chat_id=chat_id,
            open_id=open_id,
            decision_kind="retain_or_delete_unexecuted_command",
        )
        is None
    )
    with routes.session_factory() as session:
        row = session.get(XiaoDPendingDecisionRow, decision.decision_id)
        assert row is not None
        assert row.status == "default_deleted"


def test_xiaod_turn_handle_returns_continuation_for_fresh_pending_before_new_write_command() -> None:
    client = TestClient(app)
    unique = uuid4().hex
    open_id = f"ou_fresh_{unique}"
    chat_id = f"oc_fresh_{unique}"

    first = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "启动 worker",
            "actor": open_id,
            "open_id": open_id,
            "chat_id": chat_id,
            "message_id": f"om_old_{unique}",
        },
    )
    assert first.status_code == 200
    old_pending = routes.job_repository.get_active_lark_bot_pending_command_for_user(
        tenant_key="",
        chat_id=chat_id,
        open_id=open_id,
    )
    assert old_pending is not None

    second = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": (
                "处理这个表前10行："
                "https://example.larkoffice.com/sheets/abc?sheet=def"
            ),
            "actor": open_id,
            "open_id": open_id,
            "chat_id": chat_id,
            "message_id": f"om_new_{unique}",
        },
    )

    assert second.status_code == 200
    body = second.json()
    assert body["decision"]["kind"] == "backend_command"
    assert body["reply"]["action_kind"] == "continue_pending_command"
    assert "我先不创建新的重复任务" in body["reply"]["markdown"]
    assert old_pending.command_id in body["reply"]["markdown"]
    commands = client.get("/api/lark/bot/commands/pending").json()["commands"]
    user_pending = [
        command
        for command in commands
        if command["open_id"] == open_id and command["chat_id"] == chat_id and command["status"] == "pending"
    ]
    assert [command["command_id"] for command in user_pending] == [old_pending.command_id]


@pytest.mark.parametrize("text", ["task5-marker 继续执行", "dogfood-123继续执行"])
def test_xiaod_turn_handle_prefixed_continue_confirms_active_pending(text: str) -> None:
    client = TestClient(app)
    unique = uuid4().hex
    open_id = f"ou_continue_{unique}"
    chat_id = f"oc_continue_{unique}"

    first = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "启动 worker",
            "actor": open_id,
            "open_id": open_id,
            "chat_id": chat_id,
            "message_id": f"om_old_{unique}",
        },
    )
    assert first.status_code == 200
    pending = routes.job_repository.get_active_lark_bot_pending_command_for_user(
        tenant_key="",
        chat_id=chat_id,
        open_id=open_id,
    )
    assert pending is not None

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": text,
            "actor": open_id,
            "open_id": open_id,
            "chat_id": chat_id,
            "message_id": f"om_continue_{unique}",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["kind"] == "continue_pending_command"
    assert body["reply"]["action_kind"] == "worker_start"
    assert body["reply"]["status"] == "executed"
    updated = routes.job_repository.get_lark_bot_pending_command(pending.command_id)
    assert updated is not None
    assert updated.status == "executed"
    assert updated.confirmed_by == open_id


def test_xiaod_turn_handle_uses_context_for_ambiguous_continue_and_report() -> None:
    client = TestClient(app)
    unique = uuid4().hex
    open_id = f"ou_{unique}"
    chat_id = f"oc_{unique}"
    draft = client.post(
        "/api/lark/bot/badcase-drafts",
        json={
            "actor": open_id,
            "open_id": open_id,
            "chat_id": chat_id,
            "message_id": f"om_{unique}",
            "text": "\n".join(
                [
                    "原始输入：https://example.com/a.png",
                    '模型输出：{"answer":"3"}',
                    '正确答案：{"answer":"8"}',
                    "错误现象：把 8 识别成 3",
                ]
            ),
        },
    ).json()
    confirmed = client.post(
        f"/api/lark/bot/badcase-drafts/{draft['draft_id']}/confirm",
        json={"actor": open_id, "create_job": True},
    ).json()
    job_id = confirmed["submitted_job"]["job_id"]
    routes.job_repository.mark_running(job_id)

    continue_response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "继续",
            "actor": open_id,
            "open_id": open_id,
            "chat_id": chat_id,
            "message_id": f"om_continue_{unique}",
            "identity": "bot",
        },
    )

    assert continue_response.status_code == 200
    continue_body = continue_response.json()
    assert continue_body["decision"]["kind"] == "query_current_progress"
    assert continue_body["decision"]["reason"] == "contextual_continue_current_job"
    assert f"任务编号：`{job_id}`" in continue_body["reply"]["markdown"]

    routes.job_repository.mark_completed(job_id)
    _mark_auto_closure_completed(job_id)
    report_response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "报告呢？",
            "actor": open_id,
            "open_id": open_id,
            "chat_id": chat_id,
            "message_id": f"om_report_{unique}",
            "identity": "bot",
        },
    )

    assert report_response.status_code == 200
    report_body = report_response.json()
    assert report_body["decision"]["kind"] == "backend_command"
    assert report_body["decision"]["backend_command"] == f"/debug report {job_id}"
    assert report_body["decision"]["reason"] == "contextual_latest_job_report"
    assert "报告" in report_body["reply"]["markdown"]
