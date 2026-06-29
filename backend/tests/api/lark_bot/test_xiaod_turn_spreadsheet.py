# ruff: noqa: F403,F405
from tests.api.lark_bot.common import *


@pytest.mark.parametrize(
    ("text", "backend_command"),
    [
        (
            "处理这个表前3行：https://example.larkoffice.com/sheets/abc?sheet=def",
            "/debug spreadsheet rerun https://example.larkoffice.com/sheets/abc?sheet=def def 2,3,4",
        ),
        (
            "处理这个表前2行：https://example.larkoffice.com/sheets/abc?sheet=testSheet123",
            "/debug spreadsheet rerun https://example.larkoffice.com/sheets/abc?sheet=testSheet123 testSheet123 2,3",
        ),
        (
            "处理这个表第2行和第5行：https://example.larkoffice.com/sheets/abc?sheet=def",
            "/debug spreadsheet rerun https://example.larkoffice.com/sheets/abc?sheet=def def 2,5",
        ),
        (
            "重跑表格第2、5、8行：https://example.larkoffice.com/sheets/abc?sheet=def",
            "/debug spreadsheet rerun https://example.larkoffice.com/sheets/abc?sheet=def def 2,5,8",
        ),
        (
            "处理 JSZN-131 和 JSZN-096：https://example.larkoffice.com/sheets/abc?sheet=def",
            "/debug spreadsheet rerun https://example.larkoffice.com/sheets/abc?sheet=def def case:JSZN-131,JSZN-096",
        ),
    ],
)
def test_xiaod_turn_preview_maps_natural_spreadsheet_row_batch(
    text: str,
    backend_command: str,
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


def test_xiaod_turn_handle_creates_pending_spreadsheet_rerun_for_natural_row_batch() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "处理这个表前2行：https://example.larkoffice.com/sheets/abc?sheet=def",
            "message_id": "om_sheet_batch",
            "open_id": "ou_sheet_batch",
            "chat_id": "oc_sheet_batch",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["kind"] == "backend_command"
    assert body["reply"]["action_kind"] == "spreadsheet_rerun"
    assert body["reply"]["message_type"] == "interactive"
    assert body["reply"]["content"]["header"]["title"]["content"] == "表格批处理任务待确认"
    assert body["reply"]["markdown"].splitlines()[0] == (
        "已识别为表格批处理待确认：第 2、3 行。确认前不会创建或启动 Debug 任务。"
    )
    assert (
        "表格：https://example.larkoffice.com/sheets/abc?sheet=def" in body["reply"]["markdown"]
    )
    assert "工作表：`def`" in body["reply"]["markdown"]
    assert "待确认编号" in body["reply"]["markdown"]
    card_text = body["reply"]["content"]["elements"][0]["content"]
    assert "**识别结果**：第 2、3 行" in card_text
    actions = body["reply"]["content"]["elements"][1]["actions"]
    assert actions[0]["text"]["content"] == "确认创建任务"
    assert actions[0]["value"]["action"] == "confirm_pending_command"
    assert actions[1]["text"]["content"] == "取消"
    assert actions[1]["value"]["action"] == "cancel_pending_command"
    commands = client.get("/api/lark/bot/commands/pending").json()["commands"]
    command = next(item for item in commands if item["message_id"] == "om_sheet_batch")
    assert actions[0]["value"]["command_id"] == command["command_id"]
    assert actions[1]["value"]["command_id"] == command["command_id"]
    assert command["action_kind"] == "spreadsheet_rerun"
    assert command["action"]["parameters"]["source"] == (
        "https://example.larkoffice.com/sheets/abc?sheet=def"
    )
    assert command["action"]["parameters"]["sheet_id"] == "def"
    assert command["action"]["parameters"]["row_ids"] == ["2", "3"]


def test_xiaod_turn_handle_spreadsheet_rerun_card_includes_row_preflight(
    monkeypatch,
) -> None:
    client = TestClient(app)
    sync_client = StaticSpreadsheetClient(
        [
            SpreadsheetSourceRow(
                row_id="2",
                values={
                    "case_id": "preflight-case-1",
                    "image_uri": "file://preflight-case-1.png",
                    "prompt": "Read the answer",
                    "golden_answer_json": {"answers": [{"box_id": 1, "student_answer": "42"}]},
                    "scoring_standard": "exact match",
                    "predictions_json": [{"trial": 1, "raw_output": '{"answers":[]}', "score": 0}],
                    "avg_score": 0.0,
                },
            ),
            SpreadsheetSourceRow(
                row_id="3",
                values={
                    "case_id": "",
                    "prompt": "",
                },
            ),
        ]
    )
    monkeypatch.setattr(routes, "spreadsheet_sync_client", sync_client, raising=False)

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "处理这个表前3行：https://example.larkoffice.com/sheets/abc?sheet=def",
            "message_id": "om_sheet_batch_preflight",
            "open_id": "ou_sheet_batch_preflight",
            "chat_id": "oc_sheet_batch_preflight",
        },
    )

    assert response.status_code == 200
    body = response.json()
    card_text = body["reply"]["content"]["elements"][0]["content"]
    assert "请求 3 行，读到 2 行，可创建 1 个任务；无效 1 行，缺失 1 行" in card_text
    assert "**将创建任务的行**：`2`" in card_text
    assert "**表格中未读到的行**：`4`" in card_text
    assert "3: Missing required spreadsheet row value:" in card_text
    commands = client.get("/api/lark/bot/commands/pending").json()["commands"]
    command = next(item for item in commands if item["message_id"] == "om_sheet_batch_preflight")
    preflight = command["action"]["parameters"]["preflight"]
    assert preflight["requested_row_ids"] == ["2", "3", "4"]
    assert preflight["present_row_ids"] == ["2", "3"]
    assert preflight["valid_row_ids"] == ["2"]
    assert preflight["missing_row_ids"] == ["4"]
    assert preflight["valid_job_count"] == 1


def test_xiaod_turn_handle_spreadsheet_rerun_card_includes_report_sync_decision_targets() -> None:
    client = TestClient(app)
    unique = uuid4().hex

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": (
                "处理这个表前2行，返回报告并询问是否同步到飞书表格："
                "https://example.larkoffice.com/sheets/abc?sheet=def"
            ),
            "message_id": f"om_sheet_batch_report_sync_{unique}",
            "open_id": f"ou_sheet_batch_report_sync_{unique}",
            "chat_id": f"oc_sheet_batch_report_sync_{unique}",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["backend_command"] == (
        "/debug spreadsheet rerun "
        "https://example.larkoffice.com/sheets/abc?sheet=def "
        "def 2,3 --report --controlled-probes --writeback"
    )
    card_text = body["reply"]["content"]["elements"][0]["content"]
    assert (
        "**执行目标**：创建 Debug 任务、生成自动闭环报告、完成后询问是否同步到飞书表格" in card_text
    )
    commands = client.get("/api/lark/bot/commands/pending").json()["commands"]
    command = next(
        item for item in commands if item["message_id"] == f"om_sheet_batch_report_sync_{unique}"
    )
    parameters = command["action"]["parameters"]
    assert parameters["auto_closure"] is True
    assert parameters["report"] is True
    assert parameters["submit_controlled_probes"] is True
    assert parameters["writeback"] is True


def test_xiaod_turn_handle_creates_pending_spreadsheet_rerun_for_natural_case_ids() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "处理 JSZN-131 和 JSZN-096：https://example.larkoffice.com/sheets/abc?sheet=def",
            "message_id": "om_sheet_case_batch",
            "open_id": "ou_sheet_case_batch",
            "chat_id": "oc_sheet_case_batch",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["kind"] == "backend_command"
    assert body["reply"]["action_kind"] == "spreadsheet_rerun"
    assert body["reply"]["message_type"] == "interactive"
    assert body["reply"]["content"]["header"]["title"]["content"] == "表格批处理任务待确认"
    assert body["reply"]["markdown"].splitlines()[0] == (
        "已识别为表格批处理待确认：Case ID JSZN-131、JSZN-096。确认前不会创建或启动 Debug 任务。"
    )
    assert "Case ID：`JSZN-131, JSZN-096`" in body["reply"]["markdown"]
    card_text = body["reply"]["content"]["elements"][0]["content"]
    assert "**Case ID**：`JSZN-131, JSZN-096`" in card_text
    commands = client.get("/api/lark/bot/commands/pending").json()["commands"]
    command = next(item for item in commands if item["message_id"] == "om_sheet_case_batch")
    assert command["action"]["parameters"]["row_ids"] == []
    assert command["action"]["parameters"]["case_ids"] == ["JSZN-131", "JSZN-096"]


def test_xiaod_turn_handle_backend_command_preempts_semantic_badcase_for_row_batch(
    monkeypatch,
) -> None:
    client = TestClient(app)

    class FakeSemanticBrain:
        async def decide(self, request, *, context=None):
            del context
            return routes.XiaoDTurnDecision(
                kind="save_badcase_draft",
                clean_text=request.text,
                reason="semantic_brain:wrong_single_badcase",
                extracted_fields={
                    "input_source": request.text,
                    "issue_summary": "wrong semantic branch",
                },
            )

    original_brain = routes.xiaod_semantic_brain
    try:
        monkeypatch.setattr(routes, "xiaod_semantic_brain", FakeSemanticBrain())
        response = client.post(
            "/api/lark/bot/xiaod/turns/handle",
            json={
                "text": "处理这个表前2行：https://example.larkoffice.com/sheets/abc?sheet=def",
                "message_id": "om_sheet_batch_semantic",
                "open_id": "ou_sheet_batch_semantic",
                "chat_id": "oc_sheet_batch_semantic",
            },
        )
    finally:
        routes.xiaod_semantic_brain = original_brain

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["kind"] == "backend_command"
    assert body["decision"]["backend_command"] == (
        "/debug spreadsheet rerun https://example.larkoffice.com/sheets/abc?sheet=def def 2,3"
    )
    assert body["reply"]["action_kind"] == "spreadsheet_rerun"


def test_xiaod_turn_handle_live_card_validation_copy_stays_spreadsheet_rerun(
    monkeypatch,
) -> None:
    client = TestClient(app)

    class FakeSemanticBrain:
        async def decide(self, request, *, context=None):
            del context
            return routes.XiaoDTurnDecision(
                kind="save_badcase_draft",
                clean_text=request.text,
                reason="semantic_brain:wrong_live_card_validation_branch",
                extracted_fields={
                    "input_source": request.text,
                    "issue_summary": "wrong semantic branch",
                },
            )

    original_brain = routes.xiaod_semantic_brain
    try:
        monkeypatch.setattr(routes, "xiaod_semantic_brain", FakeSemanticBrain())
        response = client.post(
            "/api/lark/bot/xiaod/turns/handle",
            json={
                "text": (
                    "task-card-live-test 处理这个表第2行："
                    "https://example.larkoffice.com/sheets/abc?sheet=def\n"
                    "只做真实群卡片验收：需要看到确认创建任务和取消按钮，不要点击确认。"
                ),
                "message_id": "om_sheet_batch_live_card_validation",
                "open_id": "ou_sheet_batch_live_card_validation",
                "chat_id": "oc_sheet_batch_live_card_validation",
            },
        )
    finally:
        routes.xiaod_semantic_brain = original_brain

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["kind"] == "backend_command"
    assert body["decision"]["backend_command"] == (
        "/debug spreadsheet rerun https://example.larkoffice.com/sheets/abc?sheet=def def 2"
    )
    assert body["reply"]["message_type"] == "interactive"
    actions = body["reply"]["content"]["elements"][1]["actions"]
    assert actions[0]["value"]["action"] == "confirm_pending_command"
    assert actions[1]["value"]["action"] == "cancel_pending_command"


def test_xiaod_turn_handle_context_reference_does_not_hide_explicit_sheet_row_batch(
    monkeypatch,
) -> None:
    client = TestClient(app)

    class FakeSemanticBrain:
        async def decide(self, request, *, context=None):
            del context
            return routes.XiaoDTurnDecision(
                kind="save_badcase_draft",
                clean_text=request.text,
                reason="semantic_brain:wrong_contextual_sheet_batch",
                extracted_fields={
                    "input_source": request.text,
                    "issue_summary": "wrong semantic branch",
                },
            )

    original_brain = routes.xiaod_semantic_brain
    try:
        monkeypatch.setattr(routes, "xiaod_semantic_brain", FakeSemanticBrain())
        response = client.post(
            "/api/lark/bot/xiaod/turns/handle",
            json={
                "text": "这个表前10行有多个任务，帮我处理：https://example.larkoffice.com/sheets/abc?sheet=def",
                "message_id": "om_sheet_batch_context_reference",
                "open_id": "ou_sheet_batch_context_reference",
                "chat_id": "oc_sheet_batch_context_reference",
            },
        )
    finally:
        routes.xiaod_semantic_brain = original_brain

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["kind"] == "backend_command"
    assert body["decision"]["backend_command"] == (
        "/debug spreadsheet rerun "
        "https://example.larkoffice.com/sheets/abc?sheet=def def 2,3,4,5,6,7,8,9,10,11"
    )
    assert body["reply"]["action_kind"] == "spreadsheet_rerun"
