# ruff: noqa: F403,F405
from tests.api.lark_bot.common import *


def test_lark_bot_badcase_progress_notifications_report_running_stage() -> None:
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
    routes.job_repository.mark_running(job_id)

    response = client.get("/api/lark/bot/badcase-drafts/progress-notifications")

    assert response.status_code == 200
    body = response.json()
    notification = next(
        item for item in body["notifications"] if item["draft"]["draft_id"] == draft["draft_id"]
    )
    assert notification["stage"] == "baseline"
    assert notification["progress_key"].endswith(":baseline-running")
    assert notification["payload"]["message_type"] == "interactive"
    assert notification["payload"]["action_kind"] == "badcase_progress"
    assert "--msg-type" in notification["payload"]["delivery_args"]
    card = notification["payload"]["content"]
    assert card["header"]["title"]["content"] == "正在执行基础复测"
    assert "进度" in card["elements"][0]["content"]
    assert "阶段耗时" in card["elements"][0]["content"]
    assert "已完成 Agent" in card["elements"][0]["content"]
    assert "预计下一步" in card["elements"][0]["content"]
    labels = [action["text"]["content"] for action in card["elements"][1]["actions"]]
    assert labels == ["打开任务", "查看运行阶段", "打开报告"]
    generic_response = client.get("/api/lark/bot/notifications")
    assert generic_response.status_code == 200
    generic_notification = next(
        item
        for item in generic_response.json()["notifications"]
        if item["draft_id"] == draft["draft_id"]
    )
    assert generic_notification["kind"] == "badcase_progress"
    assert (
        generic_notification["notification_id"]
        == f"badcase-progress:{notification['progress_key']}"
    )
    assert generic_notification["dedupe_key"] == notification["progress_key"]
    assert generic_notification["progress_key"] == notification["progress_key"]
    assert (
        generic_notification["payload"]["idempotency_key"]
        == notification["payload"]["idempotency_key"]
    )
    outbox_rows = routes.job_repository.list_lark_notification_outbox(status="pending")
    persisted = next(
        item
        for item in outbox_rows
        if item.notification_id == f"badcase-progress:{notification['progress_key']}"
    )
    assert persisted.kind == "badcase_progress"
    assert persisted.dedupe_key == notification["progress_key"]
    assert persisted.progress_key == notification["progress_key"]
    assert (
        persisted.envelope["payload"]["idempotency_key"]
        == notification["payload"]["idempotency_key"]
    )


def test_lark_bot_badcase_progress_notification_mark_sent_persists_stage() -> None:
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
    routes.job_repository.mark_running(job_id)
    notification = next(
        item
        for item in client.get("/api/lark/bot/badcase-drafts/progress-notifications").json()[
            "notifications"
        ]
        if item["draft"]["draft_id"] == draft["draft_id"]
    )

    marked = client.post(
        f"/api/lark/bot/badcase-drafts/{draft['draft_id']}/progress-notified",
        json={
            "actor": "lark-bot-consumer",
            "progress_key": notification["progress_key"],
            "note": "Progress notification sent.",
        },
    )
    follow_up = client.get("/api/lark/bot/badcase-drafts/progress-notifications").json()

    assert marked.status_code == 200
    assert notification["progress_key"] in marked.json()["progress_notified_keys"]
    assert all(
        item["progress_key"] != notification["progress_key"] for item in follow_up["notifications"]
    )


def test_lark_bot_progress_notifications_update_existing_task_panel() -> None:
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
    routes.job_repository.mark_running(job_id)
    first_notification = next(
        item
        for item in client.get("/api/lark/bot/badcase-drafts/progress-notifications").json()[
            "notifications"
        ]
        if item["draft"]["draft_id"] == draft["draft_id"]
    )

    marked = client.post(
        f"/api/lark/bot/badcase-drafts/{draft['draft_id']}/progress-notified",
        json={
            "actor": "lark-bot-consumer",
            "progress_key": first_notification["progress_key"],
            "panel_message_id": f"om_panel_{unique}",
            "note": "Progress task panel sent.",
        },
    )
    routes.job_repository.save_debug_run_stage(
        job_id=job_id,
        stage="baseline",
        status="completed",
        input={"case_id": confirmed["submitted_job"]["case_id"]},
        output={"job_status": "running"},
        failure_reason="",
        retryable=True,
    )

    response = client.get("/api/lark/bot/badcase-drafts/progress-notifications")

    assert marked.status_code == 200
    assert marked.json()["progress_panel_message_id"] == f"om_panel_{unique}"
    assert response.status_code == 200
    next_notification = next(
        item
        for item in response.json()["notifications"]
        if item["draft"]["draft_id"] == draft["draft_id"]
    )
    assert next_notification["stage"] == "attribution"
    assert next_notification["payload"]["delivery_mode"] == "update_message"
    assert next_notification["payload"]["message_id"] == f"om_panel_{unique}"
    assert next_notification["payload"]["task_panel_key"] == f"xiaod-task-panel:{job_id}"
    assert next_notification["task_panel_key"] == f"xiaod-task-panel:{job_id}"
    assert next_notification["task_panel_message_id"] == f"om_panel_{unique}"
    assert next_notification["payload"]["delivery_args"][:4] == [
        "api",
        "PATCH",
        f"/open-apis/im/v1/messages/om_panel_{unique}",
        "--data",
    ]
    assert "正在归因和规划后续验证" in next_notification["payload"]["delivery_args"][4]
    assert next_notification["payload"]["fallback_delivery_args"][:4] == [
        "im",
        "+messages-reply",
        "--message-id",
        f"om_{unique}",
    ]


def test_lark_bot_badcase_progress_notifications_report_auto_closure_targeted_stage() -> None:
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
                    "原始输入：https://example.com/video.mp4",
                    '模型输出：{"segments":[]}',
                    '正确答案：{"segments":[{"start_s":1,"end_s":3}]}',
                    "错误现象：视频时间片段漏识别",
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
    source_job = routes.job_repository.get_job(job_id)
    assert source_job is not None
    routes.job_repository.mark_completed(job_id)
    routes.job_repository.save_debug_run_stage(
        job_id=job_id,
        stage="auto_closure",
        status="running",
        input={"source_job_id": job_id},
        output={"phase": "targeted_probe"},
        failure_reason="",
        retryable=True,
    )
    probe_job_id = f"probe-{unique}"
    routes.job_repository.create_job(job_id=probe_job_id, case_id=source_job.case_id)
    routes.job_repository.save_targeted_probe_job(
        source_job_id=job_id,
        target_id="video:segment:1",
        planned_steps="targeted_video_segment_probe",
        probe_job_id=probe_job_id,
        actor="auto-debug-agent",
        note="auto targeted probe",
    )

    response = client.get("/api/lark/bot/badcase-drafts/progress-notifications")

    assert response.status_code == 200
    notification = next(
        item
        for item in response.json()["notifications"]
        if item["draft"]["draft_id"] == draft["draft_id"]
    )
    assert notification["stage"] == "targeted_probe"
    assert notification["progress_key"].endswith(":targeted-1-0")
    card = notification["payload"]["content"]
    assert card["header"]["title"]["content"] == "正在做定向复测"
    assert "targeted probe" in card["elements"][0]["content"]


def test_lark_bot_badcase_progress_notifications_report_hypothesis_stage() -> None:
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
                    "原始输入：https://example.com/video.mp4",
                    '模型输出：{"segments":[]}',
                    '正确答案：{"segments":[{"start_s":1,"end_s":3}]}',
                    "错误现象：视频时间片段漏识别",
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
        output={"phase": "hypothesis"},
        failure_reason="",
        retryable=True,
    )
    routes.job_repository.save_debug_run_stage(
        job_id=job_id,
        stage="hypothesis",
        status="completed",
        input={"job_id": job_id},
        output={
            "hypothesis_closure": {
                "hypotheses": [{"hypothesis_id": "h-prompt", "status": "candidate"}],
                "probe_plans": [
                    {
                        "probe_id": "probe-h-prompt",
                        "model_runner_config_ref": "locked_source",
                    }
                ],
                "causal_comparisons": [
                    {
                        "probe_id": "probe-h-prompt",
                        "verdict": "inconclusive",
                    }
                ],
                "fairness_lock": {"model_runner_config_ref": "locked_source"},
            }
        },
        failure_reason="",
        retryable=False,
    )

    response = client.get("/api/lark/bot/badcase-drafts/progress-notifications")

    assert response.status_code == 200
    notification = next(
        item
        for item in response.json()["notifications"]
        if item["draft"]["draft_id"] == draft["draft_id"]
    )
    assert notification["stage"] == "hypothesis"
    assert notification["progress_key"].endswith(":hypothesis-1-1-1")
    card = notification["payload"]["content"]
    assert card["header"]["title"]["content"] == "正在生成候选根因假设"
    assert "候选假设 1 个" in card["elements"][0]["content"]
    assert "Probe 计划 1 个" in card["elements"][0]["content"]
    assert "locked_source" in card["elements"][0]["content"]


def test_lark_bot_badcase_progress_notifications_report_auto_closure_verification_stage() -> None:
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
                    "原始输入：https://example.com/video.mp4",
                    '模型输出：{"segments":[]}',
                    '正确答案：{"segments":[{"start_s":1,"end_s":3}]}',
                    "错误现象：视频时间片段漏识别",
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
    source_job = routes.job_repository.get_job(job_id)
    assert source_job is not None
    routes.job_repository.mark_completed(job_id)
    routes.job_repository.save_debug_run_stage(
        job_id=job_id,
        stage="auto_closure",
        status="running",
        input={"source_job_id": job_id},
        output={"phase": "verification"},
        failure_reason="",
        retryable=True,
    )
    probe_job_id = f"probe-{unique}"
    routes.job_repository.create_job(job_id=probe_job_id, case_id=source_job.case_id)
    routes.job_repository.mark_completed(probe_job_id)
    routes.job_repository.save_targeted_probe_job(
        source_job_id=job_id,
        target_id="video:segment:1",
        planned_steps="targeted_video_segment_probe",
        probe_job_id=probe_job_id,
        actor="auto-debug-agent",
        note="auto targeted probe",
    )
    verification_job_id = f"verify-{unique}"
    routes.job_repository.create_job(job_id=verification_job_id, case_id=source_job.case_id)
    routes.job_repository.save_recommended_action_verification(
        job_id=job_id,
        action_index=0,
        verification_job_id=verification_job_id,
        actor="auto-debug-agent",
        note="auto recommendation verification",
    )

    response = client.get("/api/lark/bot/badcase-drafts/progress-notifications")

    assert response.status_code == 200
    notification = next(
        item
        for item in response.json()["notifications"]
        if item["draft"]["draft_id"] == draft["draft_id"]
    )
    assert notification["stage"] == "verification"
    assert notification["progress_key"].endswith(":verification-1-0")
    card = notification["payload"]["content"]
    assert card["header"]["title"]["content"] == "正在验证推荐动作"
    assert "推荐动作验证任务" in card["elements"][0]["content"]
