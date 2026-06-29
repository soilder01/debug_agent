# ruff: noqa: F403,F405
from tests.api.lark_bot.common import *


def test_xiaod_turn_handle_spreadsheet_rerun_card_includes_report_writeback_targets() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": (
                "处理这个表前2行，跑完返回报告并写回对应列："
                "https://example.larkoffice.com/sheets/abc?sheet=def"
            ),
            "message_id": "om_sheet_batch_report_writeback",
            "open_id": "ou_sheet_batch_report_writeback",
            "chat_id": "oc_sheet_batch_report_writeback",
        },
    )

    assert response.status_code == 200
    body = response.json()
    card_text = body["reply"]["content"]["elements"][0]["content"]
    assert (
        "**执行目标**：创建 Debug 任务、生成自动闭环报告、完成后询问是否同步到飞书表格" in card_text
    )
    commands = client.get("/api/lark/bot/commands/pending").json()["commands"]
    command = next(
        item for item in commands if item["message_id"] == "om_sheet_batch_report_writeback"
    )
    parameters = command["action"]["parameters"]
    assert parameters["auto_closure"] is True
    assert parameters["report"] is True
    assert parameters["writeback"] is True


def test_xiaod_turn_handle_explicit_sheet_rows_preempt_contextual_report_writeback(
    monkeypatch,
) -> None:
    client = TestClient(app)
    unique = uuid4().hex
    open_id = f"ou_sheet_context_report_{unique}"
    chat_id = f"oc_sheet_context_report_{unique}"
    sync_client = StaticSpreadsheetClient(
        [
            SpreadsheetSourceRow(
                row_id=str(row_id),
                values=_valid_spreadsheet_row_values(f"context-report-case-{row_id}"),
            )
            for row_id in range(2, 12)
        ]
    )
    monkeypatch.setattr(routes, "spreadsheet_sync_client", sync_client, raising=False)
    draft = client.post(
        "/api/lark/bot/badcase-drafts",
        json={
            "actor": open_id,
            "open_id": open_id,
            "chat_id": chat_id,
            "message_id": f"om_context_seed_{unique}",
            "text": "\n".join(
                [
                    "原始输入：https://example.com/context.png",
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
    context_job_id = confirmed["submitted_job"]["job_id"]
    routes.job_repository.mark_completed(context_job_id)

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": (
                "把这个表前10行debug任务跑完，返回报告，"
                "并在完成后询问是否写回/同步到飞书表格对应位置；"
                "https://example.larkoffice.com/sheets/abc?sheet=def"
            ),
            "message_id": f"om_sheet_context_report_{unique}",
            "open_id": open_id,
            "chat_id": chat_id,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["kind"] == "backend_command"
    assert body["decision"]["backend_command"] == (
        "/debug spreadsheet rerun "
        "https://example.larkoffice.com/sheets/abc?sheet=def "
        "def 2,3,4,5,6,7,8,9,10,11 --report --controlled-probes --writeback"
    )
    assert body["decision"]["backend_command"] != f"/debug report {context_job_id}"
    assert body["reply"]["action_kind"] == "spreadsheet_rerun"
    assert body["reply"]["message_type"] == "interactive"
    commands = client.get("/api/lark/bot/commands/pending").json()["commands"]
    command = next(
        item for item in commands if item["message_id"] == f"om_sheet_context_report_{unique}"
    )
    assert command["action_kind"] == "spreadsheet_rerun"
    parameters = command["action"]["parameters"]
    assert parameters["row_ids"] == ["2", "3", "4", "5", "6", "7", "8", "9", "10", "11"]
    assert parameters["report"] is True
    assert parameters["submit_controlled_probes"] is True
    assert parameters["writeback"] is True
    assert parameters["preflight"]["valid_row_ids"] == [
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
        "11",
    ]


def test_xiaod_timeout_sweeper_defaults_writeback_decision_to_no_sync(
    monkeypatch,
) -> None:
    writeback_client = RecordingWritebackClient()
    monkeypatch.setattr(routes, "spreadsheet_writeback_client", writeback_client, raising=False)
    command_id, run_id, job_id, actor, chat_id = (
        _create_spreadsheet_rerun_writeback_decision_fixture()
    )
    decision = routes.job_repository.get_pending_xiaod_decision(
        tenant_key="tenant-sync",
        chat_id=chat_id,
        open_id=actor,
        decision_kind="spreadsheet_rerun_writeback_sync",
    )
    assert decision is not None
    with routes.session_factory() as session:
        row = session.get(XiaoDPendingDecisionRow, decision.decision_id)
        assert row is not None
        row.expires_at = "2000-01-01T00:00:00+00:00"
        session.commit()

    result = routes.sweep_expired_xiaod_pending_decisions()

    assert result["default_no_sync"] == 1
    assert writeback_client.update_count == 0
    assert (
        routes.job_repository.get_pending_xiaod_decision(
            tenant_key="tenant-sync",
            chat_id=chat_id,
            open_id=actor,
            decision_kind="spreadsheet_rerun_writeback_sync",
        )
        is None
    )
    audit = routes.job_repository.get_spreadsheet_writeback_audit(job_id)
    assert audit is not None
    assert audit.status == "skipped"
    assert audit.error_message == "writeback decision timed out"
    run = next(
        item
        for item in routes.job_repository.list_xiaod_execution_runs(limit=20)
        if item.run_id == run_id
    )
    assert run.status == "completed"
    assert run.summary["writeback_decision_status"] == "default_skipped"
    audits = routes.job_repository.list_xiaod_command_audits(command_id=command_id)
    assert "xiaod_run_completed" in {audit.event_kind for audit in audits}


@pytest.mark.parametrize("text", ["不同步", "marker xxx 不同步"])
def test_xiaod_turn_handle_can_skip_spreadsheet_rerun_writeback_by_text(
    monkeypatch,
    text: str,
) -> None:
    client = TestClient(app)
    writeback_client = RecordingWritebackClient()
    monkeypatch.setattr(routes, "spreadsheet_writeback_client", writeback_client, raising=False)
    command_id, run_id, job_id, actor, chat_id = (
        _create_spreadsheet_rerun_writeback_decision_fixture()
    )

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": text,
            "message_id": "om_skip_sync_by_text",
            "open_id": actor,
            "actor": actor,
            "chat_id": chat_id,
            "tenant_key": "tenant-sync",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["kind"] == "skip_writeback_decision"
    assert body["decision"]["reason"] == "contextual_skip_writeback_decision"
    assert body["reply"]["status"] == "skipped"
    assert "运行完成沉淀" in body["reply"]["markdown"]
    assert writeback_client.update_count == 0
    assert (
        routes.job_repository.get_pending_xiaod_decision(
            tenant_key="tenant-sync",
            chat_id=chat_id,
            open_id=actor,
            decision_kind="spreadsheet_rerun_writeback_sync",
        )
        is None
    )
    run = next(
        item
        for item in routes.job_repository.list_xiaod_execution_runs(limit=20)
        if item.run_id == run_id
    )
    assert run.status == "completed"
    assert run.summary["writeback_decision_status"] == "skipped"
    assert run.summary["completed_summary"]["reason"] == "user_skipped_sync"
    assert run.summary["completed_summary"]["sync_requested"] is False
    assert run.summary["completed_summary"]["default_skip"] is False
    audit = routes.job_repository.get_spreadsheet_writeback_audit(job_id)
    assert audit is not None
    assert audit.status == "skipped"
    assert audit.error_message == "user_skipped_sync"
    audits = routes.job_repository.list_xiaod_command_audits(command_id=command_id)
    assert "xiaod_run_completed" in {item.event_kind for item in audits}


def test_xiaod_turn_handle_recovers_missing_writeback_decision_from_active_run(
    monkeypatch,
) -> None:
    client = TestClient(app)
    writeback_client = RecordingWritebackClient()
    monkeypatch.setattr(routes, "spreadsheet_writeback_client", writeback_client, raising=False)
    command_id, run_id, job_id, actor, chat_id = (
        _create_spreadsheet_rerun_writeback_decision_fixture()
    )
    decision = routes.job_repository.get_pending_xiaod_decision(
        tenant_key="tenant-sync",
        chat_id=chat_id,
        open_id=actor,
        decision_kind="spreadsheet_rerun_writeback_sync",
    )
    assert decision is not None
    routes.job_repository.resolve_xiaod_pending_decision(
        decision.decision_id,
        status="lost_for_recovery_test",
        actor="test",
        note="simulate missing pending decision",
    )

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "skip sync",
            "message_id": "om_skip_sync_recovered",
            "open_id": actor,
            "actor": actor,
            "chat_id": chat_id,
            "tenant_key": "tenant-sync",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["kind"] == "skip_writeback_decision"
    assert body["reply"]["status"] == "skipped"
    assert writeback_client.update_count == 0
    audit = routes.job_repository.get_spreadsheet_writeback_audit(job_id)
    assert audit is not None
    assert audit.status == "skipped"
    run = next(
        item
        for item in routes.job_repository.list_xiaod_execution_runs(limit=20)
        if item.run_id == run_id
    )
    assert run.status == "completed"
    assert run.summary["writeback_decision_status"] == "skipped"
    audits = routes.job_repository.list_xiaod_command_audits(command_id=command_id)
    assert "spreadsheet_rerun_writeback_decision_recovered" in {item.event_kind for item in audits}


def test_xiaod_turn_handle_does_not_recover_stale_writeback_decision(
    monkeypatch,
) -> None:
    writeback_client = RecordingWritebackClient()
    monkeypatch.setattr(routes, "spreadsheet_writeback_client", writeback_client, raising=False)
    _, run_id, _, actor, chat_id = _create_spreadsheet_rerun_writeback_decision_fixture()
    decision = routes.job_repository.get_pending_xiaod_decision(
        tenant_key="tenant-sync",
        chat_id=chat_id,
        open_id=actor,
        decision_kind="spreadsheet_rerun_writeback_sync",
    )
    assert decision is not None
    routes.job_repository.resolve_xiaod_pending_decision(
        decision.decision_id,
        status="lost_for_stale_recovery_test",
        actor="test",
        note="simulate missing pending decision",
    )
    with routes.session_factory() as session:
        run_row = session.get(XiaoDExecutionRunRow, run_id)
        assert run_row is not None
        run_row.updated_at = "2000-01-01T00:00:00+00:00"
        session.commit()

    recovered = routes.xiaod_pending_interaction_controller.pending_spreadsheet_rerun_writeback_decision(
        XiaoDTurnHandleRequest(
            text="skip sync",
            message_id="om_skip_sync_stale_recovery",
            open_id=actor,
            actor=actor,
            chat_id=chat_id,
            tenant_key="tenant-sync",
        )
    )

    assert recovered is None
    assert writeback_client.update_count == 0
