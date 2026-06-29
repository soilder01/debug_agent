# ruff: noqa: F403,F405
from tests.api.lark_bot.common import *


def test_xiaod_turn_handle_returns_latest_draft_status_reply() -> None:
    client = TestClient(app)
    unique = uuid4().hex
    open_id = f"ou_{unique}"
    chat_id = f"oc_{unique}"
    client.post(
        "/api/lark/bot/badcase-drafts",
        json={
            "actor": open_id,
            "open_id": open_id,
            "chat_id": chat_id,
            "message_id": f"om_draft_{unique}",
            "text": "原始输入：https://example.com/input.png\n模型输出：3",
        },
    )

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "然后呢？",
            "open_id": open_id,
            "chat_id": chat_id,
            "message_id": f"om_follow_{unique}",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["handled"] is True
    assert body["decision"]["kind"] == "badcase_draft_followup"
    assert "当前 badcase 草稿进度" in body["reply"]["markdown"]
    assert "期望结果/正确答案" in body["reply"]["markdown"]
    assert body["reply"]["message_id"] == f"om_follow_{unique}"


def test_xiaod_turn_handle_saves_incomplete_badcase_draft() -> None:
    client = TestClient(app)
    unique = uuid4().hex
    open_id = f"ou_{unique}"
    chat_id = f"oc_{unique}"

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "原始输入：https://example.com/input.png\n模型输出：3",
            "open_id": open_id,
            "chat_id": chat_id,
            "message_id": f"om_{unique}",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["handled"] is True
    assert body["decision"]["kind"] == "save_badcase_draft"
    assert "我已把这条信息记录为 badcase 草稿" in body["reply"]["markdown"]
    assert "期望结果/正确答案" in body["reply"]["markdown"]
    drafts = client.get("/api/lark/bot/badcase-drafts").json()["drafts"]
    draft = next(item for item in drafts if item["chat_id"] == chat_id)
    assert draft["status"] == "needs_more_info"
    assert draft["message_id"] == f"om_{unique}"


def test_xiaod_turn_handle_returns_confirmation_card_for_ready_badcase_draft() -> None:
    client = TestClient(app)
    unique = uuid4().hex

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "\n".join(
                [
                    "原始输入：https://example.com/input.png",
                    "模型输出：3",
                    "正确答案：8",
                    "错误现象：把 8 识别成 3",
                ]
            ),
            "open_id": f"ou_{unique}",
            "chat_id": f"oc_{unique}",
            "message_id": f"om_{unique}",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["handled"] is True
    assert body["decision"]["kind"] == "save_badcase_draft"
    assert body["reply"]["message_type"] == "interactive"
    assert body["reply"]["status"] == "ready_for_confirmation"
    assert "--msg-type" in body["reply"]["delivery_args"]
    assert "确认提交" in json.dumps(body["reply"]["content"], ensure_ascii=False)


def test_xiaod_turn_handle_starts_new_draft_when_ready_draft_exists() -> None:
    client = TestClient(app)
    unique = uuid4().hex
    open_id = f"ou_{unique}"
    chat_id = f"oc_{unique}"
    old_message_id = f"om_old_{unique}"
    new_message_id = f"om_new_{unique}"

    first = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "\n".join(
                [
                    "原始输入：https://example.com/old.png",
                    "模型输出：3",
                    "正确答案：8",
                    "错误现象：把 8 识别成 3",
                ]
            ),
            "open_id": open_id,
            "chat_id": chat_id,
            "message_id": old_message_id,
        },
    )
    assert first.status_code == 200
    old_draft = next(
        item
        for item in client.get("/api/lark/bot/badcase-drafts").json()["drafts"]
        if item["message_id"] == old_message_id
    )

    second = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": (
                "badcase:source:https://example.com/new-a-1.png; "
                "model_output: 5; expected: 8; issue: mistook 8 for 5"
            ),
            "open_id": open_id,
            "chat_id": chat_id,
            "message_id": new_message_id,
        },
    )

    assert second.status_code == 200
    body = second.json()
    assert body["handled"] is True
    assert body["decision"]["kind"] == "save_badcase_draft"
    drafts = client.get("/api/lark/bot/badcase-drafts").json()["drafts"]
    old_after = next(item for item in drafts if item["draft_id"] == old_draft["draft_id"])
    new_draft = next(item for item in drafts if item["message_id"] == new_message_id)
    assert old_after["message_id"] == old_message_id
    assert new_draft["draft_id"] != old_draft["draft_id"]
    assert new_draft["status"] == "ready_for_confirmation"
    assert new_draft["input_source"] == "https://example.com/new-a-1.png"
    assert new_draft["model_output"] == "5"
    assert new_draft["expected_output"] == "8"
    assert new_draft["issue_summary"] == "mistook 8 for 5"


def test_xiaod_turn_handle_confirms_latest_ready_draft_and_submits_job() -> None:
    client = TestClient(app)
    unique = uuid4().hex
    open_id = f"ou_{unique}"
    chat_id = f"oc_{unique}"
    client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "\n".join(
                [
                    "原始输入：https://example.com/input.png",
                    "模型输出：3",
                    "正确答案：8",
                    "错误现象：把 8 识别成 3",
                ]
            ),
            "open_id": open_id,
            "chat_id": chat_id,
            "message_id": f"om_draft_{unique}",
        },
    )

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "确认提交",
            "open_id": open_id,
            "chat_id": chat_id,
            "message_id": f"om_confirm_{unique}",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["handled"] is True
    assert body["decision"]["kind"] == "confirm_badcase_draft"
    assert "Debug 任务已经创建" in body["reply"]["markdown"]
    assert "任务编号" in body["reply"]["markdown"]
    drafts = client.get("/api/lark/bot/badcase-drafts").json()["drafts"]
    draft = next(item for item in drafts if item["chat_id"] == chat_id)
    assert draft["status"] == "submitted"
    assert draft["submitted_job_id"]
    assert client.get(f"/jobs/{draft['submitted_job_id']}").status_code == 200


def test_xiaod_turn_handle_cancels_latest_open_draft() -> None:
    client = TestClient(app)
    unique = uuid4().hex
    open_id = f"ou_{unique}"
    chat_id = f"oc_{unique}"
    client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "原始输入：https://example.com/input.png\n模型输出：3",
            "open_id": open_id,
            "chat_id": chat_id,
            "message_id": f"om_draft_{unique}",
        },
    )

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "取消草稿",
            "open_id": open_id,
            "chat_id": chat_id,
            "message_id": f"om_cancel_{unique}",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["handled"] is True
    assert body["decision"]["kind"] == "cancel_badcase_draft"
    assert "已取消这条 badcase 草稿" in body["reply"]["markdown"]
    drafts = client.get("/api/lark/bot/badcase-drafts").json()["drafts"]
    draft = next(item for item in drafts if item["chat_id"] == chat_id)
    assert draft["status"] == "cancelled"


def test_xiaod_turn_handle_cancels_ready_draft_even_when_submitted_job_exists() -> None:
    client = TestClient(app)
    unique = uuid4().hex
    open_id = f"ou_{unique}"
    chat_id = f"oc_{unique}"
    submitted = client.post(
        "/api/lark/bot/badcase-drafts",
        json={
            "actor": open_id,
            "open_id": open_id,
            "chat_id": chat_id,
            "message_id": f"om_submitted_{unique}",
            "text": "\n".join(
                [
                    "原始输入：https://example.com/old.png",
                    "模型输出：3",
                    "正确答案：8",
                    "错误现象：旧任务识别错",
                ]
            ),
        },
    ).json()
    confirmed = client.post(
        f"/api/lark/bot/badcase-drafts/{submitted['draft_id']}/confirm",
        json={"actor": open_id, "create_job": True},
    ).json()
    routes.job_repository.mark_running(confirmed["submitted_job"]["job_id"])
    ready = client.post(
        "/api/lark/bot/badcase-drafts",
        json={
            "actor": open_id,
            "open_id": open_id,
            "chat_id": chat_id,
            "message_id": f"om_ready_{unique}",
            "text": "\n".join(
                [
                    "原始输入：https://example.com/new.png",
                    "模型输出：cat",
                    "正确答案：dog",
                    "错误现象：新任务标签错",
                ]
            ),
        },
    ).json()

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "算了，取消这个草稿，刚才那个先别跑。",
            "open_id": open_id,
            "chat_id": chat_id,
            "message_id": f"om_cancel_ready_{unique}",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["kind"] == "cancel_badcase_draft"
    assert "已取消这条 badcase 草稿" in body["reply"]["markdown"]
    cancelled = client.get(f"/api/lark/bot/badcase-drafts/{ready['draft_id']}").json()
    original = client.get(f"/api/lark/bot/badcase-drafts/{submitted['draft_id']}").json()
    assert cancelled["status"] == "cancelled"
    assert original["status"] == "submitted"


def test_xiaod_turn_handle_answers_assistant_chat(monkeypatch) -> None:
    client = TestClient(app)
    calls: list[tuple[str, str]] = []

    class FakeProjectAssistant:
        async def answer(self, question: str, *, model_id: str = ""):
            calls.append((question, model_id))
            return routes.AssistantChatResponse(
                answer=f"回答：{question}",
                citations=[],
                model_provider="fake",
                model_id=model_id or "fake-default",
            )

    original_assistant = routes.project_assistant
    try:
        monkeypatch.setattr(routes, "project_assistant", FakeProjectAssistant())
        response = client.post(
            "/api/lark/bot/xiaod/turns/handle",
            json={"text": "model_id=ep-user 解释一下报告", "message_id": "om_1"},
        )
    finally:
        routes.project_assistant = original_assistant

    assert response.status_code == 200
    body = response.json()
    assert body["handled"] is True
    assert body["decision"]["kind"] == "assistant_chat"
    assert body["reply"]["markdown"] == "回答：解释一下报告"
    assert calls == [("解释一下报告", "ep-user")]


def test_xiaod_turn_handle_uses_semantic_brain_for_debug_intake(monkeypatch) -> None:
    client = TestClient(app)
    unique = uuid4().hex

    class FakeSemanticBrain:
        async def decide(self, request, *, context=None):
            del context
            return routes.XiaoDTurnDecision(
                kind="save_badcase_draft",
                clean_text=request.text,
                reason="semantic_brain:test_debug_intake",
                extracted_fields={
                    "input_source": "https://example.com/semantic.png",
                    "model_output": "3",
                    "expected_output": "8",
                    "issue_summary": "模型把 8 识别成 3",
                },
            )

    original_brain = routes.xiaod_semantic_brain
    try:
        monkeypatch.setattr(routes, "xiaod_semantic_brain", FakeSemanticBrain())
        response = client.post(
            "/api/lark/bot/xiaod/turns/handle",
            json={
                "text": "这个样本不太对，帮我看一下",
                "open_id": f"ou_{unique}",
                "chat_id": f"oc_{unique}",
                "message_id": f"om_{unique}",
            },
        )
    finally:
        routes.xiaod_semantic_brain = original_brain

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["kind"] == "save_badcase_draft"
    assert body["decision"]["reason"] == "semantic_brain:test_debug_intake"
    assert body["decision"]["extracted_fields"]["model_output"] == "3"
    draft = next(
        item
        for item in client.get("/api/lark/bot/badcase-drafts").json()["drafts"]
        if item["message_id"] == f"om_{unique}"
    )
    assert draft["status"] == "ready_for_confirmation"
    assert draft["input_source"] == "https://example.com/semantic.png"
    assert draft["model_output"] == "3"
    assert draft["expected_output"] == "8"
    assert draft["issue_summary"] == "模型把 8 识别成 3"


def test_xiaod_turn_handle_does_not_accept_semantic_missing_input_source_placeholder(
    monkeypatch,
) -> None:
    client = TestClient(app)
    unique = uuid4().hex

    class FakeSemanticBrain:
        async def decide(self, request, *, context=None):
            del context
            return routes.XiaoDTurnDecision(
                kind="save_badcase_draft",
                clean_text=request.text,
                reason="semantic_brain:incomplete_debug_intake",
                extracted_fields={
                    "input_source": "brain-dialog-03 对应图片（暂未提供链接/附件）",
                    "model_output": "3",
                    "expected_output": "8",
                    "issue_summary": "模型说 3，其实应该是 8",
                },
            )

    original_brain = routes.xiaod_semantic_brain
    try:
        monkeypatch.setattr(routes, "xiaod_semantic_brain", FakeSemanticBrain())
        response = client.post(
            "/api/lark/bot/xiaod/turns/handle",
            json={
                "text": "brain-dialog-03 有个图不对，模型说 3，其实应该是 8，但我现在没链接，先帮我记一下？",
                "open_id": f"ou_{unique}",
                "chat_id": f"oc_{unique}",
                "message_id": f"om_{unique}",
            },
        )
    finally:
        routes.xiaod_semantic_brain = original_brain

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["kind"] == "save_badcase_draft"
    draft = next(
        item
        for item in client.get("/api/lark/bot/badcase-drafts").json()["drafts"]
        if item["message_id"] == f"om_{unique}"
    )
    assert draft["status"] == "needs_more_info"
    assert draft["input_source"] == ""
    assert "input_source" in draft["missing_fields"]
    assert draft["model_output"] == "3"
    assert draft["expected_output"] == "8"


def test_xiaod_turn_handle_reports_ready_draft_is_not_submitted_yet() -> None:
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
            "message_id": f"om_ready_report_{unique}",
            "text": "\n".join(
                [
                    "原始输入：https://example.com/report-ready.png",
                    "模型输出：3",
                    "正确答案：8",
                    "错误现象：把 8 识别成 3",
                ]
            ),
        },
    ).json()

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "报告呢？刚才这个有结论没？",
            "actor": open_id,
            "open_id": open_id,
            "chat_id": chat_id,
            "message_id": f"om_ready_report_query_{unique}",
            "identity": "bot",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["kind"] == "query_current_progress"
    assert body["reply"]["action_kind"] == "query_current_progress"
    assert "还没有提交成 Debug 任务" in body["reply"]["markdown"]
    assert f"草稿编号：`{draft['draft_id']}`" in body["reply"]["markdown"]
    assert "确认提交" in body["reply"]["markdown"]


def test_xiaod_turn_handle_starts_new_draft_for_semantic_new_badcase_during_running_job(
    monkeypatch,
) -> None:
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
        json={"actor": open_id, "create_job": True},
    ).json()
    job_id = confirmed["submitted_job"]["job_id"]
    routes.job_repository.mark_running(job_id)
    original_draft = client.get(f"/api/lark/bot/badcase-drafts/{draft['draft_id']}").json()

    class FakeSemanticBrain:
        async def decide(self, request, *, context=None):
            del context
            return routes.XiaoDTurnDecision(
                kind="save_badcase_draft",
                clean_text=request.text,
                reason="semantic_brain:new_badcase_while_job_running",
                extracted_fields={
                    "input_source": "https://example.com/new-case.png",
                    "model_output": "3",
                    "expected_output": "8",
                    "issue_summary": "模型把 8 识别成 3",
                },
            )

    original_brain = routes.xiaod_semantic_brain
    try:
        monkeypatch.setattr(routes, "xiaod_semantic_brain", FakeSemanticBrain())
        response = client.post(
            "/api/lark/bot/xiaod/turns/handle",
            json={
                "text": "脑子验收：我这有个新的图识别问题，帮我建草稿。",
                "actor": open_id,
                "open_id": open_id,
                "chat_id": chat_id,
                "message_id": f"om_new_case_{unique}",
                "identity": "bot",
            },
        )
    finally:
        routes.xiaod_semantic_brain = original_brain

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["kind"] == "save_badcase_draft"
    assert body["decision"]["reason"] == "semantic_brain:new_badcase_while_job_running"
    assert body["reply"]["action_kind"] == "badcase_confirmation"
    submitted_draft = client.get(f"/api/lark/bot/badcase-drafts/{draft['draft_id']}").json()
    assert submitted_draft["source_text"] == original_draft["source_text"]
    drafts = client.get("/api/lark/bot/badcase-drafts").json()["drafts"]
    new_draft = next(item for item in drafts if item["message_id"] == f"om_new_case_{unique}")
    assert new_draft["draft_id"] != draft["draft_id"]
    assert new_draft["status"] == "ready_for_confirmation"
    assert new_draft["submitted_job_id"] == ""
    assert new_draft["input_source"] == "https://example.com/new-case.png"
    assert new_draft["model_output"] == "3"
    assert new_draft["expected_output"] == "8"
    assert new_draft["issue_summary"] == "模型把 8 识别成 3"
    stages = routes.job_repository.list_debug_run_stages(job_id)
    assert all(stage.stage != "supplemental_context" for stage in stages)


def test_xiaod_turn_handle_starts_new_incomplete_draft_instead_of_polluting_submitted_job(
    monkeypatch,
) -> None:
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
        json={"actor": open_id, "create_job": True},
    ).json()
    job_id = confirmed["submitted_job"]["job_id"]
    routes.job_repository.mark_running(job_id)
    original_draft = client.get(f"/api/lark/bot/badcase-drafts/{draft['draft_id']}").json()

    class FakeSemanticBrain:
        async def decide(self, request, *, context=None):
            del context
            return routes.XiaoDTurnDecision(
                kind="save_badcase_draft",
                clean_text=request.text,
                reason="semantic_brain:incomplete_new_badcase",
                extracted_fields={
                    "model_output": "3",
                    "expected_output": "8",
                    "issue_summary": "模型说 3，其实应该是 8",
                },
            )

    original_brain = routes.xiaod_semantic_brain
    try:
        monkeypatch.setattr(routes, "xiaod_semantic_brain", FakeSemanticBrain())
        response = client.post(
            "/api/lark/bot/xiaod/turns/handle",
            json={
                "text": "有个图不对，模型说 3，其实应该是 8，但我现在没链接，先帮我记一下？",
                "actor": open_id,
                "open_id": open_id,
                "chat_id": chat_id,
                "message_id": f"om_incomplete_new_case_{unique}",
                "identity": "bot",
            },
        )
    finally:
        routes.xiaod_semantic_brain = original_brain

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["kind"] == "save_badcase_draft"
    assert body["reply"]["action_kind"] == "save_badcase_draft"
    submitted_draft = client.get(f"/api/lark/bot/badcase-drafts/{draft['draft_id']}").json()
    assert submitted_draft["source_text"] == original_draft["source_text"]
    assert submitted_draft["input_source"] == original_draft["input_source"]
    drafts = client.get("/api/lark/bot/badcase-drafts").json()["drafts"]
    new_draft = next(
        item for item in drafts if item["message_id"] == f"om_incomplete_new_case_{unique}"
    )
    assert new_draft["draft_id"] != draft["draft_id"]
    assert new_draft["status"] == "needs_more_info"
    assert new_draft["input_source"] == ""
    assert "input_source" in new_draft["missing_fields"]
    stages = routes.job_repository.list_debug_run_stages(job_id)
    assert all(stage.stage != "supplemental_context" for stage in stages)


def test_xiaod_turn_handle_starts_new_draft_for_supplement_after_completed_job() -> None:
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
        json={"actor": open_id, "create_job": True},
    ).json()
    job_id = confirmed["submitted_job"]["job_id"]
    routes.job_repository.mark_completed(job_id)
    original_draft = client.get(f"/api/lark/bot/badcase-drafts/{draft['draft_id']}").json()

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "补充材料：其实视频第 2 秒右侧有一个闪烁按钮。",
            "actor": open_id,
            "open_id": open_id,
            "chat_id": chat_id,
            "message_id": f"om_supplement_done_{unique}",
            "identity": "bot",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["kind"] == "save_badcase_draft"
    assert body["reply"]["action_kind"] == "save_badcase_draft"
    assert "我已把这条信息记录为 badcase 草稿" in body["reply"]["markdown"]
    submitted_draft = client.get(f"/api/lark/bot/badcase-drafts/{draft['draft_id']}").json()
    assert submitted_draft["source_text"] == original_draft["source_text"]
    drafts = client.get("/api/lark/bot/badcase-drafts").json()["drafts"]
    new_draft = next(
        item for item in drafts if item["message_id"] == f"om_supplement_done_{unique}"
    )
    assert new_draft["draft_id"] != draft["draft_id"]
    assert new_draft["status"] == "needs_more_info"
    assert new_draft["submitted_job_id"] == ""
