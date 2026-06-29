# ruff: noqa: F403,F405
from tests.api.lark_bot.common import *


def test_lark_bot_pending_lifecycle_card_rejects_different_user() -> None:
    client = TestClient(app)
    unique = uuid4().hex
    owner = f"ou_owner_{unique}"
    chat_id = f"oc_owner_{unique}"

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "启动 worker",
            "actor": owner,
            "open_id": owner,
            "chat_id": chat_id,
            "message_id": f"om_owner_{unique}",
        },
    )
    assert response.status_code == 200
    pending = routes.job_repository.get_active_lark_bot_pending_command_for_user(
        tenant_key="",
        chat_id=chat_id,
        open_id=owner,
    )
    assert pending is not None

    rejected = client.post(
        "/api/lark/bot/events",
        json={
            "header": {"event_type": "card.action.trigger"},
            "event": {
                "operator": {"open_id": f"ou_intruder_{unique}"},
                "action": {
                    "value": {
                        "action": "continue_pending_command",
                        "command_id": pending.command_id,
                    }
                },
            },
        },
    )

    assert rejected.status_code == 403
    assert "Only the user who created this XiaoD pending command" in rejected.json()["detail"]


def test_lark_bot_pending_command_confirms_and_executes_single_case_debug() -> None:
    client = TestClient(app)

    create_response = client.post(
        "/api/lark/bot/commands/pending",
        json={
            "text": "/debug run case handwrite233",
            "actor": "ops-reviewer",
            "open_id": "ou_1",
            "chat_id": "oc_1",
            "message_id": "om_1",
            "identity": "bot",
        },
    )

    assert create_response.status_code == 200
    pending = create_response.json()
    assert pending["status"] == "pending"
    assert pending["action_kind"] == "submit_case"
    assert pending["action"]["parameters"]["case_id"] == "handwrite233"
    assert pending["message_id"] == "om_1"

    confirm_response = client.post(
        f"/api/lark/bot/commands/pending/{pending['command_id']}/confirm",
        json={"actor": "ops-reviewer", "note": "confirmed in bot card"},
    )

    assert confirm_response.status_code == 200
    executed = confirm_response.json()
    assert executed["status"] == "executed"
    assert executed["confirmed_by"] == "ops-reviewer"
    submitted_job = executed["execution_result"]["submitted_job"]
    assert submitted_job["case_id"] == "handwrite233"
    assert submitted_job["artifact_group_id"] == "lark-bot"
    assert routes.job_repository.get_job(submitted_job["job_id"]) is not None
    latest_audit = routes.job_repository.list_lark_operation_audits(limit=1)[0]
    assert latest_audit.service == "bot"
    assert latest_audit.operation == "pending_command_executed"
    assert latest_audit.risk_action == "submit_case"

    preview_response = client.get(
        f"/api/lark/bot/commands/pending/{pending['command_id']}/reply-preview"
    )
    assert preview_response.status_code == 200
    reply_preview = preview_response.json()
    assert reply_preview["target_type"] == "message"
    assert reply_preview["message_id"] == "om_1"
    assert "Debug Agent 已提交调试任务" in reply_preview["markdown"]
    assert reply_preview["delivery_args"][:4] == ["im", "+messages-reply", "--message-id", "om_1"]

    dry_run_response = client.post(
        f"/api/lark/bot/commands/pending/{pending['command_id']}/send-reply",
        json={"actor": "ops-reviewer", "dry_run": True},
    )
    assert dry_run_response.status_code == 200
    dry_run = dry_run_response.json()
    assert dry_run["sent"] is False
    assert dry_run["dry_run"] is True
    assert "--dry-run" in dry_run["payload"]["delivery_args"]


def test_lark_bot_pending_command_can_be_confirmed_from_interactive_task_card() -> None:
    client = TestClient(app)

    create_response = client.post(
        "/api/lark/bot/commands/pending",
        json={
            "text": "/debug run case handwrite233",
            "actor": "ops-reviewer",
            "open_id": "ou_1",
            "chat_id": "oc_1",
            "message_id": "om_1",
            "identity": "bot",
        },
    )

    assert create_response.status_code == 200
    pending = create_response.json()

    response = client.post(
        "/api/lark/bot/events",
        json={
            "header": {"event_type": "card.action.trigger"},
            "event": {
                "operator": {"open_id": "ou_card_reviewer"},
                "action": {
                    "value": {
                        "action": "confirm_pending_command",
                        "command_id": pending["command_id"],
                    }
                },
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["handled"] is True
    assert body["action"] == "confirm_pending_command"
    assert body["pending_command"]["status"] == "executed"
    assert body["pending_command"]["confirmed_by"] == "ou_card_reviewer"
    assert body["pending_command"]["execution_result"]["submitted_job"]["case_id"] == "handwrite233"
    assert body["reply"]["message_type"] == "post"
    assert "Debug Agent 已提交调试任务" in body["reply"]["markdown"]


def test_lark_bot_pending_command_can_be_cancelled_and_cannot_execute() -> None:
    client = TestClient(app)

    create_response = client.post(
        "/api/lark/bot/commands/pending",
        json={
            "text": "/debug run case handwrite233",
            "actor": "ops-reviewer",
            "open_id": "ou_1",
            "chat_id": "oc_1",
            "message_id": "om_1",
            "identity": "bot",
        },
    )

    assert create_response.status_code == 200
    pending = create_response.json()

    cancel_response = client.post(
        f"/api/lark/bot/commands/pending/{pending['command_id']}/cancel",
        json={"actor": "ops-reviewer", "note": "cancelled in bot card"},
    )

    assert cancel_response.status_code == 200
    cancelled = cancel_response.json()
    assert cancelled["status"] == "cancelled"
    assert cancelled["confirmed_by"] == "ops-reviewer"
    assert all(job.case_id != "handwrite233" for job in routes.job_repository.list_jobs())

    confirm_response = client.post(
        f"/api/lark/bot/commands/pending/{pending['command_id']}/confirm",
        json={"actor": "ops-reviewer", "note": "should not execute"},
    )

    assert confirm_response.status_code == 409
    assert "cancelled" in confirm_response.json()["detail"]


def test_lark_bot_pending_command_can_be_cancelled_from_interactive_task_card() -> None:
    client = TestClient(app)

    create_response = client.post(
        "/api/lark/bot/commands/pending",
        json={
            "text": "/debug run case handwrite233",
            "actor": "ops-reviewer",
            "open_id": "ou_1",
            "chat_id": "oc_1",
            "message_id": "om_1",
            "identity": "bot",
        },
    )

    assert create_response.status_code == 200
    pending = create_response.json()

    response = client.post(
        "/api/lark/bot/events",
        json={
            "header": {"event_type": "card.action.trigger"},
            "event": {
                "operator": {"open_id": "ou_card_reviewer"},
                "action": {
                    "value": {
                        "action": "cancel_pending_command",
                        "command_id": pending["command_id"],
                    }
                },
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["handled"] is True
    assert body["action"] == "cancel_pending_command"
    assert body["pending_command"]["status"] == "cancelled"
    assert body["pending_command"]["confirmed_by"] == "ou_card_reviewer"
    assert body["reply"]["message_type"] == "post"
    assert "Debug Agent 已取消待确认操作" in body["reply"]["markdown"]
    assert all(job.case_id != "handwrite233" for job in routes.job_repository.list_jobs())


def test_lark_bot_pending_command_confirms_and_executes_batch_debug() -> None:
    client = TestClient(app)

    create_response = client.post(
        "/api/lark/bot/commands/pending",
        json={
            "text": "/debug batch run handwrite233,missing-case",
            "actor": "ops-reviewer",
            "open_id": "ou_1",
        },
    )

    assert create_response.status_code == 200
    pending = create_response.json()
    assert pending["action_kind"] == "submit_batch"

    confirm_response = client.post(
        f"/api/lark/bot/commands/pending/{pending['command_id']}/confirm",
        json={"actor": "ops-reviewer"},
    )

    assert confirm_response.status_code == 200
    executed = confirm_response.json()
    batch = executed["execution_result"]["batch"]
    assert executed["status"] == "executed"
    assert batch["rejected_case_ids"] == ["missing-case"]
    assert batch["jobs"][0]["case_id"] == "handwrite233"
    assert batch["batch"]["batch"]["batch_id"].startswith("batch-")


def test_lark_bot_pending_command_confirms_and_executes_batch_pause() -> None:
    client = TestClient(app)
    batch_id = f"batch-bot-pause-{uuid4().hex[:8]}"
    routes.job_repository.create_batch(batch_id=batch_id, total_jobs=0)

    create_response = client.post(
        "/api/lark/bot/commands/pending",
        json={
            "text": f"/debug batch pause {batch_id}",
            "actor": "ops-reviewer",
            "open_id": "ou_1",
        },
    )

    assert create_response.status_code == 200
    pending = create_response.json()
    assert pending["action_kind"] == "batch_pause"

    confirm_response = client.post(
        f"/api/lark/bot/commands/pending/{pending['command_id']}/confirm",
        json={"actor": "ops-reviewer"},
    )

    assert confirm_response.status_code == 200
    executed = confirm_response.json()
    assert executed["status"] == "executed"


def test_lark_bot_pending_command_confirm_creates_spreadsheet_writeback_confirmation(
    monkeypatch,
) -> None:
    client = TestClient(app)
    unique = uuid4().hex
    job_id = f"job-writeback-{unique}"
    case_id = f"case-writeback-{unique}"
    routes.job_repository.create_job(job_id=job_id, case_id=case_id, artifact_group_id="test")
    routes.job_repository.mark_completed(job_id)
    routes.job_repository.save_spreadsheet_row_mapping(
        job_id=job_id,
        case_id=case_id,
        spreadsheet_id="sheet-token",
        sheet_id="sheet-id",
        row_id="row-1",
    )
    monkeypatch.setattr(routes, "build_report_for_job", lambda _repository, _job_id: object())

    create_response = client.post(
        "/api/lark/bot/commands/pending",
        json={
            "text": f"/debug writeback {job_id}",
            "actor": "ops-reviewer",
            "open_id": "ou_1",
        },
    )
    assert create_response.status_code == 200
    pending = create_response.json()
    assert pending["action_kind"] == "spreadsheet_writeback_confirmation"

    confirm_response = client.post(
        f"/api/lark/bot/commands/pending/{pending['command_id']}/confirm",
        json={"actor": "ops-reviewer"},
    )

    assert confirm_response.status_code == 200
    executed = confirm_response.json()
    assert executed["status"] == "executed"
    confirmation = executed["execution_result"]["write_confirmation"]
    assert confirmation["service"] == "sheets"
    assert confirmation["operation"] == "+cells-set"
    assert confirmation["status"] == "pending"


def test_lark_bot_pending_command_confirms_remaining_write_capabilities(monkeypatch) -> None:
    client = TestClient(app)
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_update_recommended_action_status(job_id, action_index, request):
        calls.append(
            (
                "recommended_action_status_update",
                {
                    "job_id": job_id,
                    "action_index": action_index,
                    "status": request.status,
                    "actor": request.actor,
                    "note": request.note,
                },
            )
        )
        return DummyModelResult(job_id=job_id, action_index=action_index, status=request.status)

    def fake_create_recommended_action_verification_job(job_id, action_index, request):
        calls.append(
            (
                "recommended_action_verification",
                {
                    "job_id": job_id,
                    "action_index": action_index,
                    "actor": request.actor,
                    "note": request.note,
                },
            )
        )
        return DummyModelResult(
            job_id=job_id, action_index=action_index, verification_job_id="job-v"
        )

    def fake_update_human_handoff_status(job_id, target_id, request):
        calls.append(
            (
                "human_handoff_status_update",
                {
                    "job_id": job_id,
                    "target_id": target_id,
                    "status": request.status,
                    "actor": request.actor,
                    "note": request.note,
                },
            )
        )
        return DummyModelResult(job_id=job_id, target_id=target_id, status=request.status)

    def fake_create_strategy_follow_up_job(job_id, stage, request):
        calls.append(
            (
                "strategy_followup_job",
                {"job_id": job_id, "stage": stage, "actor": request.actor, "note": request.note},
            )
        )
        return DummyModelResult(source_job_id=job_id, stage=stage, follow_up_job_id="job-s")

    def fake_create_targeted_probe_job(job_id, target_id, request):
        calls.append(
            (
                "targeted_probe_job",
                {
                    "job_id": job_id,
                    "target_id": target_id,
                    "actor": request.actor,
                    "note": request.note,
                },
            )
        )
        return DummyModelResult(source_job_id=job_id, target_id=target_id, probe_job_id="job-p")

    async def fake_run_job_auto_debug_closure(job_id, request):
        calls.append(
            (
                "auto_closure",
                {
                    "job_id": job_id,
                    "actor": request.actor,
                    "writeback": request.writeback,
                    "report_url": request.report_url,
                    "submit_controlled_probes": request.submit_controlled_probes,
                },
            )
        )
        return DummyModelResult(source_job_id=job_id, writeback=request.writeback)

    async def fake_run_job_auto_debug_closure_report(job_id, request):
        calls.append(
            (
                "auto_closure_report",
                {
                    "job_id": job_id,
                    "actor": request.actor,
                    "writeback": request.writeback,
                    "report_url": request.report_url,
                    "submit_controlled_probes": request.submit_controlled_probes,
                },
            )
        )
        return DummyModelResult(source_job_id=job_id, report_artifact_url="file:///closure.md")

    monkeypatch.setattr(
        routes,
        "update_recommended_action_status",
        fake_update_recommended_action_status,
    )
    monkeypatch.setattr(
        routes,
        "create_recommended_action_verification_job",
        fake_create_recommended_action_verification_job,
    )
    monkeypatch.setattr(routes, "update_human_handoff_status", fake_update_human_handoff_status)
    monkeypatch.setattr(routes, "create_strategy_follow_up_job", fake_create_strategy_follow_up_job)
    monkeypatch.setattr(routes, "create_targeted_probe_job", fake_create_targeted_probe_job)
    monkeypatch.setattr(routes, "run_job_auto_debug_closure", fake_run_job_auto_debug_closure)
    monkeypatch.setattr(
        routes,
        "run_job_auto_debug_closure_report",
        fake_run_job_auto_debug_closure_report,
    )

    scenarios = [
        (
            "/debug recommended-actions status job-123 0 accepted accepted by owner",
            "recommended_action_status_update",
            "recommended_action_status",
        ),
        (
            "/debug recommended-actions verify job-123 0 rerun validation",
            "recommended_action_verification",
            "recommended_action_verification",
        ),
        (
            "/debug human-handoffs status job-123 multimodal:conflict:1 resolved fixed",
            "human_handoff_status_update",
            "human_handoff_status",
        ),
        (
            "/debug strategy-followups run job-123 stability rerun",
            "strategy_followup_job",
            "strategy_followup",
        ),
        (
            "/debug targeted-probes run job-123 multimodal:conflict:1 probe again",
            "targeted_probe_job",
            "targeted_probe",
        ),
        (
            "/debug auto-closure job-123 --controlled-probes",
            "auto_closure",
            "auto_closure",
        ),
        (
            "/debug auto-closure-report job-123 --writeback --controlled-probes https://debug.example/report",
            "auto_closure_report",
            "auto_closure_report",
        ),
    ]

    for text, action_kind, result_key in scenarios:
        create_response = client.post(
            "/api/lark/bot/commands/pending",
            json={"text": text, "actor": "ops-reviewer", "open_id": "ou_1"},
        )
        assert create_response.status_code == 200
        pending = create_response.json()
        assert pending["action_kind"] == action_kind

        confirm_response = client.post(
            f"/api/lark/bot/commands/pending/{pending['command_id']}/confirm",
            json={"actor": "ops-reviewer"},
        )

        assert confirm_response.status_code == 200
        executed = confirm_response.json()
        assert executed["status"] == "executed"
        assert result_key in executed["execution_result"]

    call_kinds = [kind for kind, _payload in calls]
    assert call_kinds == [scenario[1] for scenario in scenarios]
    assert calls[0][1]["status"] == "accepted"
    assert calls[2][1]["status"] == "resolved"
    assert calls[-1][1]["writeback"] is True
    assert calls[-2][1]["submit_controlled_probes"] is True
    assert calls[-1][1]["submit_controlled_probes"] is True
    assert calls[-1][1]["report_url"] == "https://debug.example/report"


def test_lark_bot_pending_commands_can_be_listed_and_filtered() -> None:
    client = TestClient(app)

    create_pending = client.post(
        "/api/lark/bot/commands/pending",
        json={"text": "/debug run case handwrite233", "actor": "ops-reviewer"},
    ).json()
    create_executed = client.post(
        "/api/lark/bot/commands/pending",
        json={"text": "/debug batch run handwrite233", "actor": "ops-reviewer"},
    ).json()
    confirm_response = client.post(
        f"/api/lark/bot/commands/pending/{create_executed['command_id']}/confirm",
        json={"actor": "ops-reviewer"},
    )
    assert confirm_response.status_code == 200

    all_response = client.get("/api/lark/bot/commands/pending?limit=10")
    pending_response = client.get("/api/lark/bot/commands/pending?status=pending&limit=10")

    assert all_response.status_code == 200
    assert pending_response.status_code == 200
    all_body = all_response.json()
    pending_body = pending_response.json()
    assert all_body["total_count"] >= 2
    assert {item["command_id"] for item in all_body["commands"]} >= {
        create_pending["command_id"],
        create_executed["command_id"],
    }
    assert create_pending["command_id"] in {item["command_id"] for item in pending_body["commands"]}
    assert all(item["status"] == "pending" for item in pending_body["commands"])


def test_lark_bot_pending_command_sends_reply_through_connector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = TestClient(app)
    calls: list[tuple[list[str], str | None]] = []

    class FakeBotConnector:
        def status(self) -> LarkConnectorStatus:
            return LarkConnectorStatus(mode="fake", identity="bot", profile="debug-bot")

        def run_json(self, args: list[str], stdin: str | None = None) -> dict[str, object]:
            calls.append((args, stdin))
            return {"message_id": "om_reply", "chat_id": "oc_1"}

    monkeypatch.setattr(
        routes,
        "_lark_bot_im_connector",
        lambda *, actor, identity, profile: FakeBotConnector(),
    )
    create_response = client.post(
        "/api/lark/bot/commands/pending",
        json={
            "text": "/debug run case handwrite233",
            "actor": "ops-reviewer",
            "open_id": "ou_1",
            "chat_id": "oc_1",
        },
    )
    pending = create_response.json()
    confirm_response = client.post(
        f"/api/lark/bot/commands/pending/{pending['command_id']}/confirm",
        json={"actor": "ops-reviewer"},
    )
    assert confirm_response.status_code == 200

    send_response = client.post(
        f"/api/lark/bot/commands/pending/{pending['command_id']}/send-reply",
        json={"actor": "ops-reviewer", "dry_run": False},
    )

    assert send_response.status_code == 200
    sent = send_response.json()
    assert sent["sent"] is True
    assert sent["dry_run"] is False
    assert sent["result"]["message_id"] == "om_reply"
    assert calls[0][0][:4] == ["im", "+messages-send", "--chat-id", "oc_1"]
    assert "--dry-run" not in calls[0][0]
    latest_audit = routes.job_repository.list_lark_operation_audits(limit=1)[0]
    assert latest_audit.service == "bot"
    assert latest_audit.operation == "reply_sent"


def test_lark_bot_pending_command_rejects_read_only_command() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/lark/bot/commands/pending",
        json={"text": "/debug status", "actor": "ops-reviewer"},
    )

    assert response.status_code == 400
    assert "Only write-risk" in response.json()["detail"]


def test_lark_bot_pending_command_expired_cannot_execute() -> None:
    client = TestClient(app)

    create_response = client.post(
        "/api/lark/bot/commands/pending",
        json={"text": "/debug run case handwrite233", "actor": "ops-reviewer", "ttl_minutes": 1},
    )
    pending = create_response.json()
    routes.job_repository.complete_lark_bot_pending_command(
        pending["command_id"],
        status="pending",
        execution_result={},
    )
    with routes.session_factory() as session:
        row = session.get(LarkBotPendingCommandRow, pending["command_id"])
        assert row is not None
        row.expires_at = "2000-01-01T00:00:00+00:00"
        row.executed_at = ""
        session.commit()

    response = client.post(
        f"/api/lark/bot/commands/pending/{pending['command_id']}/confirm",
        json={"actor": "ops-reviewer"},
    )

    assert response.status_code == 409
    assert "expired" in response.json()["detail"]
