# ruff: noqa: F403,F405
from tests.api.lark_bot.common import *


def test_xiaod_turn_handle_cleans_post_at_markdown_spreadsheet_link_text(monkeypatch) -> None:
    client = TestClient(app)
    unique = uuid4().hex
    clean_url = "https://example.larkoffice.com/sheets/abc?sheet=testSheet123"
    sync_client = StaticSpreadsheetClient(
        [
            SpreadsheetSourceRow(
                row_id="2",
                values=_valid_spreadsheet_row_values("post-at-case-1"),
            ),
            SpreadsheetSourceRow(
                row_id="3",
                values=_valid_spreadsheet_row_values("post-at-case-2"),
            ),
        ]
    )
    monkeypatch.setattr(routes, "spreadsheet_sync_client", sync_client, raising=False)

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": f"@小D 处理这个表前2行：[{clean_url}]({clean_url})",
            "message_id": f"om_sheet_batch_post_at_markdown_{unique}",
            "open_id": f"ou_sheet_batch_post_at_markdown_{unique}",
            "chat_id": f"oc_sheet_batch_post_at_markdown_{unique}",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["kind"] == "backend_command"
    assert body["decision"]["backend_command"] == (
        f"/debug spreadsheet rerun {clean_url} testSheet123 2,3"
    )
    assert body["reply"]["action_kind"] == "spreadsheet_rerun"
    assert "](" not in body["reply"]["markdown"]
    commands = client.get("/api/lark/bot/commands/pending").json()["commands"]
    command = next(
        item
        for item in commands
        if item["message_id"] == f"om_sheet_batch_post_at_markdown_{unique}"
    )
    assert command["action"]["parameters"]["source"] == clean_url
    assert command["action"]["parameters"]["sheet_id"] == "testSheet123"
    assert command["action"]["parameters"]["row_ids"] == ["2", "3"]
    assert sync_client.requested_spreadsheet_id == "abc"
    assert sync_client.requested_sheet_id == "testSheet123"


def test_xiaod_turn_handle_returns_current_progress_for_latest_submitted_job() -> None:
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

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "小D，现在跑到哪了？",
            "actor": f"ou_{unique}",
            "open_id": f"ou_{unique}",
            "chat_id": f"oc_{unique}",
            "message_id": f"om_progress_{unique}",
            "identity": "bot",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["kind"] == "query_current_progress"
    assert body["handled"] is True
    reply = body["reply"]
    assert reply["action_kind"] == "query_current_progress"
    assert reply["message_type"] == "interactive"
    assert "--msg-type" in reply["delivery_args"]
    assert f"任务编号：`{job_id}`" in reply["markdown"]
    assert "正在执行基础复测" in reply["markdown"]
    assert "进度：20%" in reply["markdown"]
    assert "阶段耗时：" in reply["markdown"]
    assert "已完成 Agent：" in reply["markdown"]
    assert "预计下一步：" in reply["markdown"]
    assert reply["content"]["header"]["title"]["content"] == "当前任务进度"
    assert "阶段耗时" in reply["content"]["elements"][0]["content"]
    assert "已完成 Agent" in reply["content"]["elements"][0]["content"]
    assert "预计下一步" in reply["content"]["elements"][0]["content"]
    progress_labels = [
        action["text"]["content"] for action in reply["content"]["elements"][1]["actions"]
    ]
    assert progress_labels == ["打开任务", "查看运行阶段", "打开报告"]


def test_xiaod_turn_handle_clarifies_ambiguous_request_without_context() -> None:
    client = TestClient(app)
    unique = uuid4().hex

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "报告呢？",
            "actor": f"ou_{unique}",
            "open_id": f"ou_{unique}",
            "chat_id": f"oc_{unique}",
            "message_id": f"om_clarify_{unique}",
            "identity": "bot",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["kind"] == "clarify_intent"
    assert body["decision"]["reason"] == "missing_context_for_report"
    assert body["reply"]["action_kind"] == "clarify_intent"
    assert "我没有定位到当前 Debug 任务" in body["reply"]["markdown"]
    assert "最近任务" in body["reply"]["markdown"]


def test_xiaod_turn_handle_returns_onboarding_help_card() -> None:
    client = TestClient(app)
    unique = uuid4().hex

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "小D怎么用？",
            "actor": f"ou_{unique}",
            "open_id": f"ou_{unique}",
            "chat_id": f"oc_{unique}",
            "message_id": f"om_help_{unique}",
            "identity": "bot",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["kind"] == "help"
    reply = body["reply"]
    assert reply["message_type"] == "interactive"
    assert reply["content"]["header"]["title"]["content"] == "小D Debug Agent 使用入口"
    actions = [
        action["text"]["content"]
        for element in reply["content"]["elements"]
        if element["tag"] == "action"
        for action in element["actions"]
    ]
    assert "完整使用手册" in actions
    assert "表格重跑说明" in actions
    assert "RAG知识库" in actions
    urls = [
        action["url"]
        for element in reply["content"]["elements"]
        if element["tag"] == "action"
        for action in element["actions"]
    ]
    assert any(url.endswith("/xiaod/views/manual") for url in urls)


def test_xiaod_turn_handle_pauses_current_job_from_natural_contextual_text() -> None:
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

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "先别跑了",
            "actor": open_id,
            "open_id": open_id,
            "chat_id": chat_id,
            "message_id": f"om_pause_natural_{unique}",
            "identity": "bot",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["kind"] == "pause_current_job"
    assert body["decision"]["reason"] == "contextual_debug_job_pause"
    assert "已暂停当前 Debug 任务" in body["reply"]["markdown"]
    assert routes.job_repository.get_job(job_id).status == "paused"


def test_xiaod_turn_handle_controls_latest_submitted_job() -> None:
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

    pause_response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "小D，暂停当前任务",
            "actor": f"ou_{unique}",
            "open_id": f"ou_{unique}",
            "chat_id": f"oc_{unique}",
            "message_id": f"om_pause_{unique}",
            "identity": "bot",
        },
    )

    assert pause_response.status_code == 200
    pause_body = pause_response.json()
    assert pause_body["decision"]["kind"] == "pause_current_job"
    assert pause_body["reply"]["action_kind"] == "pause_current_job"
    assert "已暂停当前 Debug 任务" in pause_body["reply"]["markdown"]
    assert routes.job_repository.get_job(job_id).status == "paused"

    resume_response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "小D，恢复当前任务",
            "actor": f"ou_{unique}",
            "open_id": f"ou_{unique}",
            "chat_id": f"oc_{unique}",
            "message_id": f"om_resume_{unique}",
            "identity": "bot",
        },
    )

    assert resume_response.status_code == 200
    resume_body = resume_response.json()
    assert resume_body["decision"]["kind"] == "resume_current_job"
    assert resume_body["reply"]["action_kind"] == "resume_current_job"
    assert "已恢复当前 Debug 任务" in resume_body["reply"]["markdown"]
    assert routes.job_repository.get_job(job_id).status == "created"

    cancel_response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "小D，取消当前任务",
            "actor": f"ou_{unique}",
            "open_id": f"ou_{unique}",
            "chat_id": f"oc_{unique}",
            "message_id": f"om_cancel_{unique}",
            "identity": "bot",
        },
    )

    assert cancel_response.status_code == 200
    cancel_body = cancel_response.json()
    assert cancel_body["decision"]["kind"] == "cancel_current_job"
    assert cancel_body["reply"]["action_kind"] == "cancel_current_job"
    assert "已取消当前 Debug 任务" in cancel_body["reply"]["markdown"]
    assert routes.job_repository.get_job(job_id).status == "cancelled"


def test_xiaod_turn_handle_merges_supplement_into_current_job() -> None:
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
                    "原始输入：https://example.com/video.mp4",
                    '模型输出：{"segments":[]}',
                    '正确答案：{"segments":[{"start_s":1,"end_s":3}]}',
                    "错误现象：视频时间片段漏识别",
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

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "补充材料：视频第 2 秒右侧按钮闪了一下，模型漏掉了。",
            "actor": f"ou_{unique}",
            "open_id": f"ou_{unique}",
            "chat_id": f"oc_{unique}",
            "message_id": f"om_supplement_{unique}",
            "identity": "bot",
            "attachments": [{"type": "file", "file_key": "file_v2_extra", "name": "extra.mp4"}],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["kind"] == "save_badcase_draft"
    assert body["reply"]["action_kind"] == "supplement_current_job"
    assert "已补充到当前 Debug 任务" in body["reply"]["markdown"]
    updated_draft = client.get(f"/api/lark/bot/badcase-drafts/{draft['draft_id']}").json()
    assert updated_draft["status"] == "submitted"
    assert updated_draft["submitted_job_id"] == job_id
    assert "视频第 2 秒右侧按钮闪了一下" in updated_draft["source_text"]
    assert any(item.get("file_key") == "file_v2_extra" for item in updated_draft["attachments"])
    stages = routes.job_repository.list_debug_run_stages(job_id)
    supplement_stage = next(stage for stage in stages if stage.stage == "supplemental_context")
    assert supplement_stage.status == "completed"
    assert supplement_stage.output["message_id"] == f"om_supplement_{unique}"
    assert "视频第 2 秒右侧按钮闪了一下" in supplement_stage.input["supplement_text"]


def test_xiaod_turn_handle_returns_recent_tasks_card_for_current_chat() -> None:
    client = TestClient(app)
    unique = uuid4().hex
    job_ids: list[str] = []
    for index in range(3):
        draft = client.post(
            "/api/lark/bot/badcase-drafts",
            json={
                "actor": f"ou_{unique}",
                "open_id": f"ou_{unique}",
                "chat_id": f"oc_{unique}",
                "message_id": f"om_{unique}_{index}",
                "text": "\n".join(
                    [
                        f"原始输入：https://example.com/{index}.png",
                        f'模型输出：{{"answer":"{index}"}}',
                        '正确答案：{"answer":"8"}',
                        "错误现象：识别错",
                    ]
                ),
            },
        ).json()
        confirmed = client.post(
            f"/api/lark/bot/badcase-drafts/{draft['draft_id']}/confirm",
            json={"actor": f"ou_{unique}", "create_job": True},
        ).json()
        job_id = confirmed["submitted_job"]["job_id"]
        job_ids.append(job_id)
        if index == 0:
            routes.job_repository.mark_completed(job_id)
            _mark_auto_closure_completed(job_id)
        elif index == 1:
            routes.job_repository.mark_running(job_id)

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "小D，最近 3 个任务",
            "actor": f"ou_{unique}",
            "open_id": f"ou_{unique}",
            "chat_id": f"oc_{unique}",
            "message_id": f"om_recent_{unique}",
            "identity": "bot",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["kind"] == "query_recent_tasks"
    reply = body["reply"]
    assert reply["action_kind"] == "query_recent_tasks"
    assert reply["message_type"] == "interactive"
    assert "--msg-type" in reply["delivery_args"]
    assert "最近 Debug 任务" in reply["markdown"]
    for job_id in job_ids:
        assert job_id in reply["markdown"]
    assert reply["content"]["header"]["title"]["content"] == "最近 Debug 任务"
    labels = [action["text"]["content"] for action in reply["content"]["elements"][1]["actions"]]
    assert labels[:9] == [
        "打开任务 1",
        "查看进度 1",
        "打开报告 1",
        "打开任务 2",
        "查看进度 2",
        "打开报告 2",
        "打开任务 3",
        "查看进度 3",
        "打开报告 3",
    ]
