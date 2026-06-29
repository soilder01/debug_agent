# ruff: noqa: F403,F405
from tests.api.lark_bot.common import *


def test_lark_bot_badcase_completion_notifications_mark_sent(monkeypatch) -> None:
    client = TestClient(app)
    unique = uuid4().hex

    draft_response = client.post(
        "/api/lark/bot/badcase-drafts",
        json={
            "actor": f"ou_{unique}",
            "open_id": f"ou_{unique}",
            "chat_id": f"oc_{unique}",
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
    )
    draft = draft_response.json()
    confirmed = client.post(
        f"/api/lark/bot/badcase-drafts/{draft['draft_id']}/confirm",
        json={"actor": f"ou_{unique}", "create_job": True},
    ).json()
    job_id = confirmed["submitted_job"]["job_id"]
    routes.job_repository.mark_completed(job_id)
    _mark_auto_closure_completed(job_id)
    monkeypatch.setattr(
        routes,
        "build_report_for_job",
        lambda repository, requested_job_id: (
            SimpleNamespace(
                root_cause=SimpleNamespace(
                    label="model_call_error",
                    confidence="high",
                    evidence_summary="模型调用失败，未能完成稳定复测。",
                ),
                recommended_actions=[
                    {"priority": "P0", "summary": "先修复模型调用链路后重跑该 badcase。"}
                ],
                agent_traces=[
                    SimpleNamespace(
                        agent_role="model_runner",
                        input_excerpt="Classify.",
                        output_excerpt='{"answer":"3"}',
                        reasoning_summary="规则判分失败。",
                    )
                ],
            )
            if requested_job_id == job_id
            else None
        ),
    )

    notification_response = client.get("/api/lark/bot/badcase-drafts/completion-notifications")

    assert notification_response.status_code == 200
    notifications = notification_response.json()["notifications"]
    notification = next(
        item for item in notifications if item["draft"]["draft_id"] == draft["draft_id"]
    )
    assert notification["job_id"] == job_id
    assert notification["job_status"] == "completed"
    assert notification["payload"]["target_type"] == "message"
    assert notification["payload"]["message_id"] == f"om_{unique}"
    assert notification["payload"]["delivery_args"][:3] == ["im", "+messages-reply", "--message-id"]
    assert notification["payload"]["message_type"] == "interactive"
    assert "--msg-type" in notification["payload"]["delivery_args"]
    assert "--markdown" not in notification["payload"]["delivery_args"]
    assert notification["payload"]["content"]["header"]["title"]["content"].startswith(
        "Debug Agent 调试"
    )
    card_actions = notification["payload"]["content"]["elements"][1]["actions"]
    card_labels = [action["text"]["content"] for action in card_actions]
    card_urls = {
        action["text"]["content"]: action["url"] for action in card_actions if "url" in action
    }
    assert "打开报告" in card_labels
    assert "打开任务" in card_labels
    assert "打开证据" in card_labels
    assert "验证推荐动作" in card_labels
    assert any("写回" in label for label in card_labels)
    assert "人工复核" in card_labels
    assert card_urls["打开任务"].endswith(f"/xiaod/views/jobs/{job_id}")
    assert card_urls["打开证据"].endswith(f"/xiaod/views/jobs/{job_id}/evidence-ledger")
    assert card_urls["验证推荐动作"].endswith(
        f"/xiaod/views/jobs/{job_id}/recommended-actions"
    )
    assert card_urls["人工复核"].endswith(f"/xiaod/views/jobs/{job_id}/human-handoffs")
    assert "--dry-run" not in notification["payload"]["delivery_args"]
    assert "Debug Agent 调试未通过，需要处理" in notification["payload"]["markdown"]
    assert "根因判断：model_call_error / high" in notification["payload"]["markdown"]
    assert (
        "推荐动作：P0 / 先修复模型调用链路后重跑该 badcase。" in notification["payload"]["markdown"]
    )
    assert "多 Agent 协同：未发现 meta-agent 产物" in notification["payload"]["markdown"]
    assert "Agent 输入与推理摘要：已写入完整报告" in notification["payload"]["markdown"]
    assert (
        "完整报告包含：run stages、evidence ledger、Agent 输入与推理摘要"
        in notification["payload"]["markdown"]
    )
    assert "Auto-closure：已发现闭环执行阶段" in notification["payload"]["markdown"]
    assert (
        "前端可继续查看证据、报告、推荐动作、写回审计和闭环任务"
        in notification["payload"]["markdown"]
    )
    assert notification["report_url"].endswith(f"/xiaod/views/jobs/{job_id}/report")
    repeated_notifications = client.get(
        "/api/lark/bot/badcase-drafts/completion-notifications"
    ).json()["notifications"]
    repeated_notification = next(
        item for item in repeated_notifications if item["draft"]["draft_id"] == draft["draft_id"]
    )
    assert (
        repeated_notification["payload"]["idempotency_key"]
        == notification["payload"]["idempotency_key"]
    )
    generic_response = client.get("/api/lark/bot/notifications")
    assert generic_response.status_code == 200
    generic_notification = next(
        item
        for item in generic_response.json()["notifications"]
        if item["draft_id"] == draft["draft_id"]
    )
    assert generic_notification["kind"] == "badcase_completion"
    assert (
        generic_notification["notification_id"]
        == f"badcase-completion:{draft['draft_id']}:{job_id}"
    )
    assert generic_notification["dedupe_key"] == f"{draft['draft_id']}:{job_id}"
    assert (
        generic_notification["payload"]["idempotency_key"]
        == notification["payload"]["idempotency_key"]
    )
    outbox_rows = routes.job_repository.list_lark_notification_outbox(status="pending")
    persisted = next(
        item
        for item in outbox_rows
        if item.notification_id == f"badcase-completion:{draft['draft_id']}:{job_id}"
    )
    assert persisted.kind == "badcase_completion"
    assert persisted.dedupe_key == f"{draft['draft_id']}:{job_id}"
    assert persisted.attempts == 0
    assert (
        persisted.envelope["payload"]["idempotency_key"]
        == notification["payload"]["idempotency_key"]
    )
    outbox_response = client.get("/api/lark/bot/notification-outbox?status=pending")
    assert outbox_response.status_code == 200
    outbox_body = outbox_response.json()
    outbox_item = next(
        item
        for item in outbox_body["notifications"]
        if item["notification_id"] == f"badcase-completion:{draft['draft_id']}:{job_id}"
    )
    assert outbox_item["kind"] == "badcase_completion"
    assert outbox_item["status"] == "pending"
    assert outbox_item["attempts"] == 0
    assert outbox_item["last_error"] == ""

    notified = client.post(
        f"/api/lark/bot/badcase-drafts/{draft['draft_id']}/completion-notified",
        json={"actor": f"ou_{unique}", "note": "sent"},
    )

    assert notified.status_code == 200
    assert notified.json()["status"] == "completed"
    sent_outbox = routes.job_repository.get_lark_notification_outbox(
        f"badcase-completion:{draft['draft_id']}:{job_id}"
    )
    assert sent_outbox is not None
    assert sent_outbox.status == "sent"
    assert sent_outbox.sent_at
    follow_up = client.get("/api/lark/bot/badcase-drafts/completion-notifications").json()
    assert all(
        item["draft"]["draft_id"] != draft["draft_id"] for item in follow_up["notifications"]
    )


def test_lark_bot_completion_notification_waits_for_auto_closure_stage() -> None:
    client = TestClient(app)
    unique = uuid4().hex
    draft_response = client.post(
        "/api/lark/bot/badcase-drafts",
        json={
            "actor": f"ou_{unique}",
            "open_id": f"ou_{unique}",
            "chat_id": f"oc_{unique}",
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
    )
    draft = draft_response.json()
    confirmed = client.post(
        f"/api/lark/bot/badcase-drafts/{draft['draft_id']}/confirm",
        json={"actor": f"ou_{unique}", "create_job": True},
    ).json()
    job_id = confirmed["submitted_job"]["job_id"]
    routes.job_repository.mark_completed(job_id)
    routes.job_repository.save_debug_run_stage(
        job_id=job_id,
        stage="auto_closure",
        status="running",
        input={"source_job_id": job_id},
        output={},
        failure_reason="",
        retryable=True,
    )

    pending = client.get("/api/lark/bot/badcase-drafts/completion-notifications").json()

    assert all(item["draft"]["draft_id"] != draft["draft_id"] for item in pending["notifications"])

    routes.job_repository.save_debug_run_stage(
        job_id=job_id,
        stage="auto_closure",
        status="completed",
        input={"source_job_id": job_id},
        output={"created_targeted_probe_jobs": []},
        failure_reason="",
        retryable=True,
    )

    ready = client.get("/api/lark/bot/badcase-drafts/completion-notifications").json()

    assert any(item["draft"]["draft_id"] == draft["draft_id"] for item in ready["notifications"])


def test_lark_bot_completion_notification_prefers_lark_doc_report(monkeypatch) -> None:
    client = TestClient(app)
    original_settings = routes.settings
    docs_connector = RecordingDocsConnector()
    unique = uuid4().hex
    job_id = f"job-doc-report-{unique}"
    draft = routes.job_repository.save_lark_bot_badcase_draft(
        draft_id=str(uuid4()),
        actor=f"ou_{unique}",
        open_id=f"ou_{unique}",
        chat_id=f"oc_{unique}",
        message_id=f"om_{unique}",
        status="submitted",
        source_text="小D，帮我调试这个 badcase",
        input_source="https://example.com/a.png",
        model_output='{"answer":"3"}',
        expected_output='{"answer":"8"}',
        issue_summary="把 8 识别成 3",
        submitted_case_id="handwrite233",
        submitted_job_id=job_id,
    )
    routes.job_repository.create_job(job_id=job_id, case_id="handwrite233")
    routes.job_repository.mark_completed(job_id)
    _mark_auto_closure_completed(job_id)
    monkeypatch.setattr(
        routes,
        "_lark_report_document_connector",
        lambda *, actor: docs_connector,
    )
    monkeypatch.setattr(
        routes,
        "build_report_for_job",
        lambda repository, requested_job_id: (
            _completed_debug_report(job_id=requested_job_id) if requested_job_id == job_id else None
        ),
    )
    routes.settings = original_settings.model_copy(update={"lark_report_docs_enabled": True})
    try:
        notification_response = client.get("/api/lark/bot/badcase-drafts/completion-notifications")
        notification_response_again = client.get(
            "/api/lark/bot/badcase-drafts/completion-notifications"
        )
    finally:
        routes.settings = original_settings

    assert notification_response.status_code == 200
    notifications = notification_response.json()["notifications"]
    notification = next(
        item for item in notifications if item["draft"]["draft_id"] == draft.draft_id
    )
    assert notification["report_url"] == "https://bytedance.larkoffice.com/docx/doccn-debug-report"
    assert (
        "查看云文档报告：https://bytedance.larkoffice.com/docx/doccn-debug-report"
        in notification["payload"]["markdown"]
    )
    assert (
        f"报告详情页：{original_settings.report_base_url.rstrip()}/xiaod/views/jobs/{job_id}/report"
        in notification["payload"]["markdown"]
    )
    assert len(docs_connector.calls) == 1
    args, stdin = docs_connector.calls[0]
    assert args[:6] == ["docs", "+create", "--api-version", "v2", "--doc-format", "xml"]
    assert "--content" in args
    assert args[args.index("--as") + 1] == "user"
    assert stdin is not None
    assert "<title>handwrite233 最终 Debug 报告</title>" in stdin
    assert "<p><b>先看这三件事</b></p>" in stdin
    assert "<p><b>证据链阅读顺序</b></p>" in stdin
    assert (
        "<p><b>本区读法：</b>按“证据地图 → 关键证据卡片 → 证据解读 → "
        "原始输出索引”的顺序看。正文只保留关键原始输出摘要。</p>"
    ) in stdin
    assert "<h2>原始 Badcase 证据</h2>" in stdin
    assert "<h2>输入与 Prompt 改动审计</h2>" in stdin
    assert "<h2>阶段方法解释</h2>" in stdin
    assert "<h3>先看这三件事</h3>" not in stdin
    assert "report_presentation_agent" not in stdin
    assert "版式计划审计" not in stdin
    assert "完整报告正文" not in stdin
    saved = routes.job_repository.get_lark_report_document(job_id)
    assert saved is not None
    assert saved.status == "published"
    assert saved.document_url == "https://bytedance.larkoffice.com/docx/doccn-debug-report"
    assert notification_response_again.status_code == 200
    assert len(docs_connector.calls) == 1


def test_lark_report_document_profile_defaults_to_user_profile() -> None:
    original_settings = routes.settings
    original_lark_settings = routes.lark_spreadsheet_settings
    routes.settings = original_settings.model_copy(
        update={"lark_report_doc_identity": "user", "lark_report_doc_profile": ""}
    )
    routes.lark_spreadsheet_settings = original_lark_settings.model_copy(
        update={"lark_cli_profile": "xiaoD"}
    )
    try:
        assert routes._lark_report_doc_profile() == ""
    finally:
        routes.settings = original_settings
        routes.lark_spreadsheet_settings = original_lark_settings


def test_lark_report_document_bot_profile_falls_back_to_lark_profile() -> None:
    original_settings = routes.settings
    original_lark_settings = routes.lark_spreadsheet_settings
    routes.settings = original_settings.model_copy(
        update={"lark_report_doc_identity": "bot", "lark_report_doc_profile": ""}
    )
    routes.lark_spreadsheet_settings = original_lark_settings.model_copy(
        update={"lark_cli_profile": "xiaoD"}
    )
    try:
        assert routes._lark_report_doc_profile() == "xiaoD"
    finally:
        routes.settings = original_settings
        routes.lark_spreadsheet_settings = original_lark_settings


def test_lark_report_document_explicit_profile_wins() -> None:
    original_settings = routes.settings
    routes.settings = original_settings.model_copy(
        update={"lark_report_doc_identity": "user", "lark_report_doc_profile": "report-user"}
    )
    try:
        assert routes._lark_report_doc_profile() == "report-user"
    finally:
        routes.settings = original_settings


def test_lark_bot_badcase_completion_delivery_failure_caps_retries(monkeypatch) -> None:
    client = TestClient(app)
    unique = uuid4().hex
    draft = client.post(
        "/api/lark/bot/badcase-drafts",
        json={
            "actor": f"ou_{unique}",
            "open_id": f"ou_{unique}",
            "chat_id": f"oc_{unique}",
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
        json={"actor": f"ou_{unique}", "create_job": True},
    ).json()
    job_id = confirmed["submitted_job"]["job_id"]
    routes.job_repository.mark_completed(job_id)
    _mark_auto_closure_completed(job_id)
    monkeypatch.setattr(
        routes,
        "build_report_for_job",
        lambda repository, requested_job_id: (
            SimpleNamespace(
                root_cause=SimpleNamespace(
                    label="model_call_error",
                    confidence="high",
                    evidence_summary="模型调用失败。",
                ),
                recommended_actions=[],
            )
            if requested_job_id == job_id
            else None
        ),
    )
    assert client.get("/api/lark/bot/badcase-drafts/completion-notifications").json()[
        "notifications"
    ]
    assert client.get("/api/lark/bot/notifications").status_code == 200
    notification_id = f"badcase-completion:{draft['draft_id']}:{job_id}"

    first = client.post(
        f"/api/lark/bot/badcase-drafts/{draft['draft_id']}/completion-delivery-failed",
        json={
            "actor": "lark-bot-consumer",
            "note": "first failure",
            "error_message": "invalid open_message_id",
            "max_attempts": 2,
        },
    )

    assert first.status_code == 200
    assert first.json()["status"] == "submitted"
    first_error = json.loads(first.json()["error_message"])
    assert first_error["completion_delivery_failure"]["attempts"] == 1
    first_outbox = routes.job_repository.get_lark_notification_outbox(notification_id)
    assert first_outbox is not None
    assert first_outbox.status == "pending"
    assert first_outbox.attempts == 1
    assert first_outbox.last_error == "invalid open_message_id"
    assert client.get("/api/lark/bot/badcase-drafts/completion-notifications").json()[
        "notifications"
    ]

    second = client.post(
        f"/api/lark/bot/badcase-drafts/{draft['draft_id']}/completion-delivery-failed",
        json={
            "actor": "lark-bot-consumer",
            "note": "second failure",
            "error_message": "invalid open_message_id",
            "max_attempts": 2,
        },
    )

    assert second.status_code == 200
    assert second.json()["status"] == "completion_delivery_failed"
    second_error = json.loads(second.json()["error_message"])
    assert second_error["completion_delivery_failure"]["attempts"] == 2
    second_outbox = routes.job_repository.get_lark_notification_outbox(notification_id)
    assert second_outbox is not None
    assert second_outbox.status == "failed"
    assert second_outbox.attempts == 2
    assert second_outbox.last_error == "invalid open_message_id"
    follow_up = client.get("/api/lark/bot/badcase-drafts/completion-notifications").json()
    assert all(
        item["draft"]["draft_id"] != draft["draft_id"] for item in follow_up["notifications"]
    )
