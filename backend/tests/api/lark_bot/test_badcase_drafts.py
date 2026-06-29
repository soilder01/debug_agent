# ruff: noqa: F403,F405
from tests.api.lark_bot.common import *


def test_lark_bot_badcase_draft_collects_fields_and_confirms_job() -> None:
    client = TestClient(app)
    unique = uuid4().hex
    chat_id = f"oc_{unique}"
    open_id = f"ou_{unique}"

    incomplete = client.post(
        "/api/lark/bot/badcase-drafts",
        json={
            "actor": open_id,
            "open_id": open_id,
            "chat_id": chat_id,
            "message_id": f"om_{unique}_1",
            "text": "帮我调试这个识别错误，图片：https://example.com/input.png",
        },
    )

    assert incomplete.status_code == 200
    draft = incomplete.json()
    assert draft["status"] == "needs_more_info"
    assert draft["input_source"] == "https://example.com/input.png"
    assert set(draft["missing_fields"]) >= {"model_output", "expected_output", "issue_summary"}

    complete = client.post(
        "/api/lark/bot/badcase-drafts",
        json={
            "actor": open_id,
            "open_id": open_id,
            "chat_id": chat_id,
            "message_id": f"om_{unique}_2",
            "text": "\n".join(
                [
                    '模型输出：{"answer":"3"}',
                    '正确答案：{"answer":"8"}',
                    "错误现象：把 8 识别成 3",
                ]
            ),
        },
    )

    assert complete.status_code == 200
    ready = complete.json()
    assert ready["draft_id"] == draft["draft_id"]
    assert ready["status"] == "ready_for_confirmation"
    assert ready["missing_fields"] == []

    confirmed = client.post(
        f"/api/lark/bot/badcase-drafts/{ready['draft_id']}/confirm",
        json={"actor": open_id, "create_job": True},
    )

    assert confirmed.status_code == 200
    body = confirmed.json()
    assert body["draft"]["status"] == "submitted"
    assert body["draft"]["submitted_case_id"].startswith("lark-draft-")
    assert body["submitted_job"]["status"] == "created"
    assert body["submitted_job"]["artifact_group_id"] == "lark-bot"
    saved_case = routes.job_repository.get_case(body["draft"]["submitted_case_id"])
    assert saved_case is not None
    assert saved_case.task_type == "generic_json"
    assert saved_case.image_uri == "https://example.com/input.png"


def test_lark_bot_badcase_draft_accepts_complete_labeled_message() -> None:
    client = TestClient(app)
    unique = uuid4().hex

    response = client.post(
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

    assert response.status_code == 200
    draft = response.json()
    assert draft["status"] == "ready_for_confirmation"
    assert draft["missing_fields"] == []
    assert draft["input_source"] == "https://example.com/a.png"
    assert draft["model_output"] == '{"answer":"3"}'
    assert draft["expected_output"] == '{"answer":"8"}'
    assert draft["issue_summary"] == "把 8 识别成 3"
    assert draft["links"] == ["https://example.com/a.png"]


def test_lark_bot_badcase_draft_accepts_semicolon_separated_labeled_message() -> None:
    client = TestClient(app)
    unique = uuid4().hex

    response = client.post(
        "/api/lark/bot/badcase-drafts",
        json={
            "actor": f"ou_{unique}",
            "open_id": f"ou_{unique}",
            "chat_id": f"oc_{unique}",
            "message_id": f"om_{unique}",
            "text": (
                "帮我调试这个 badcase："
                "原始输入：https://example.com/a.png；"
                "模型输出：3；"
                "正确答案：8；"
                "错误现象：把 8 识别成 3。"
            ),
        },
    )

    assert response.status_code == 200
    draft = response.json()
    assert draft["status"] == "ready_for_confirmation"
    assert draft["missing_fields"] == []
    assert draft["input_source"] == "https://example.com/a.png"
    assert draft["model_output"] == "3"
    assert draft["expected_output"] == "8"
    assert draft["issue_summary"] == "把 8 识别成 3"
    assert draft["links"] == ["https://example.com/a.png"]


def test_lark_bot_badcase_draft_accepts_ascii_labeled_message() -> None:
    client = TestClient(app)
    unique = uuid4().hex

    response = client.post(
        "/api/lark/bot/badcase-drafts",
        json={
            "actor": f"ou_{unique}",
            "open_id": f"ou_{unique}",
            "chat_id": f"oc_{unique}",
            "message_id": f"om_{unique}",
            "text": "\n".join(
                [
                    "input: https://example.com/a.png",
                    'model_output: {"answer":"3"}',
                    'expected: {"answer":"8"}',
                    "issue: mistook 8 for 3",
                ]
            ),
        },
    )

    assert response.status_code == 200
    draft = response.json()
    assert draft["status"] == "ready_for_confirmation"
    assert draft["missing_fields"] == []
    assert draft["input_source"] == "https://example.com/a.png"
    assert draft["model_output"] == '{"answer":"3"}'
    assert draft["expected_output"] == '{"answer":"8"}'
    assert draft["issue_summary"] == "mistook 8 for 3"


def test_lark_bot_badcase_draft_does_not_pass_missing_media_filename_to_model() -> None:
    client = TestClient(app)
    unique = uuid4().hex

    response = client.post(
        "/api/lark/bot/badcase-drafts",
        json={
            "actor": f"ou_{unique}",
            "open_id": f"ou_{unique}",
            "chat_id": f"oc_{unique}",
            "message_id": f"om_{unique}",
            "text": "\n".join(
                [
                    "video: JSZN-131.mp4",
                    'predict: {"video_action_segments":[]}',
                    'expected: {"video_action_segments":[{"start_s":0.1}]}',
                    "gpt_response: EvalOpCheckTimestamp 失败：end_s 超出范围",
                ]
            ),
        },
    )
    draft = response.json()

    assert draft["status"] == "needs_more_info"
    assert "input_source" in draft["missing_fields"]
    assert draft["input_source"] == ""

    confirmed = client.post(
        f"/api/lark/bot/badcase-drafts/{draft['draft_id']}/confirm",
        json={"actor": f"ou_{unique}", "create_job": True},
    )

    assert confirmed.status_code == 409


def test_lark_bot_badcase_draft_uses_plain_links_and_attachments_as_input_source() -> None:
    client = TestClient(app)
    unique = uuid4().hex

    link_response = client.post(
        "/api/lark/bot/badcase-drafts",
        json={
            "actor": f"ou_{unique}_link",
            "open_id": f"ou_{unique}_link",
            "chat_id": f"oc_{unique}_link",
            "message_id": f"om_{unique}_link",
            "text": "\n".join(
                [
                    "帮我调试这个：https://example.com/plain-input.png",
                    '模型输出：{"answer":"3"}',
                    '正确答案：{"answer":"8"}',
                    "错误现象：把 8 识别成 3",
                ]
            ),
        },
    )

    assert link_response.status_code == 200
    link_draft = link_response.json()
    assert link_draft["status"] == "ready_for_confirmation"
    assert link_draft["input_source"] == "https://example.com/plain-input.png"
    assert link_draft["missing_fields"] == []
    assert link_draft["attachments"] == [
        {
            "type": "link_context",
            "link_type": "external_url",
            "resource": "外部链接",
            "url": "https://example.com/plain-input.png",
            "status": "recognized",
            "next_action": "作为 badcase 原始输入保存；如需读取内容，需要补充具体连接器。",
        }
    ]

    attachment_response = client.post(
        "/api/lark/bot/badcase-drafts",
        json={
            "actor": f"ou_{unique}_attachment",
            "open_id": f"ou_{unique}_attachment",
            "chat_id": f"oc_{unique}_attachment",
            "message_id": f"om_{unique}_attachment",
            "text": "\n".join(
                [
                    '模型输出：{"answer":"3"}',
                    '正确答案：{"answer":"8"}',
                    "错误现象：把 8 识别成 3",
                ]
            ),
            "attachments": [{"type": "image", "image_key": "img_v2_1", "name": "input.png"}],
        },
    )

    assert attachment_response.status_code == 200
    attachment_draft = attachment_response.json()
    assert attachment_draft["status"] == "ready_for_confirmation"
    assert attachment_draft["input_source"] == "attachment:image:img_v2_1 (input.png)"
    assert attachment_draft["attachments"] == [
        {"type": "image", "image_key": "img_v2_1", "name": "input.png"}
    ]
    assert attachment_draft["missing_fields"] == []


def test_lark_bot_badcase_draft_classifies_lark_and_debug_agent_links() -> None:
    client = TestClient(app)
    unique = uuid4().hex

    response = client.post(
        "/api/lark/bot/badcase-drafts",
        json={
            "actor": f"ou_{unique}",
            "open_id": f"ou_{unique}",
            "chat_id": f"oc_{unique}",
            "message_id": f"om_{unique}",
            "text": "\n".join(
                [
                    "原始输入：https://example.larkoffice.com/sheets/shtcn123?sheet=tab-1",
                    "参考文档：https://bytedance.larkoffice.com/docx/doc-token",
                    "历史报告：http://localhost:8000/jobs/job-1/report",
                    '模型输出：{"answer":"3"}',
                    '正确答案：{"answer":"8"}',
                    "错误现象：把 8 识别成 3",
                ]
            ),
        },
    )

    assert response.status_code == 200
    draft = response.json()
    contexts = {
        item["url"]: item for item in draft["attachments"] if item.get("type") == "link_context"
    }
    sheet = contexts["https://example.larkoffice.com/sheets/shtcn123?sheet=tab-1"]
    assert sheet["link_type"] == "lark_sheet"
    assert sheet["resource"] == "飞书电子表格"
    assert sheet["token"] == "shtcn123"
    assert sheet["sheet_id"] == "tab-1"
    assert "选择样本行" in sheet["next_action"]
    doc = contexts["https://bytedance.larkoffice.com/docx/doc-token"]
    assert doc["link_type"] == "lark_doc"
    assert doc["resource"] == "飞书文档"
    report = contexts["http://localhost:8000/jobs/job-1/report"]
    assert report["link_type"] == "debug_agent_report"
    assert report["identifier"] == "job-1"


def test_lark_bot_badcase_draft_reads_lark_doc_content(monkeypatch) -> None:
    client = TestClient(app)
    unique = uuid4().hex
    captured_args: list[list[str]] = []

    class FakeReadConnector:
        def __init__(self, *, actor: str) -> None:
            self.actor = actor

        def run_json(self, args: list[str], stdin: str | None = None) -> dict[str, object]:
            captured_args.append(args)
            return {
                "markdown": "\n".join(
                    [
                        "原始输入：https://example.com/doc-input.png",
                        '模型输出：{"answer":"3"}',
                        '正确答案：{"answer":"8"}',
                        "错误现象：把 8 识别成 3",
                    ]
                )
            }

    monkeypatch.setattr(
        routes, "_lark_bot_read_connector", lambda actor: FakeReadConnector(actor=actor)
    )
    routes.lark_spreadsheet_settings = routes.lark_spreadsheet_settings.model_copy(
        update={"lark_cli_identity": "bot", "lark_cli_profile": "xiaoD"}
    )

    response = client.post(
        "/api/lark/bot/badcase-drafts",
        json={
            "actor": f"ou_{unique}",
            "open_id": f"ou_{unique}",
            "chat_id": f"oc_{unique}",
            "message_id": f"om_{unique}",
            "text": "帮我调试这个文档：https://bytedance.larkoffice.com/docx/doc-token",
            "resolve_link_content": True,
        },
    )

    assert response.status_code == 200
    draft = response.json()
    assert draft["status"] == "ready_for_confirmation"
    assert draft["input_source"] == "https://example.com/doc-input.png"
    assert draft["model_output"] == '{"answer":"3"}'
    assert draft["expected_output"] == '{"answer":"8"}'
    assert draft["issue_summary"] == "把 8 识别成 3"
    context = next(item for item in draft["attachments"] if item.get("link_type") == "lark_doc")
    assert context["status"] == "content_resolved"
    assert context["badcase_fields"]["issue_summary"] == "把 8 识别成 3"
    assert captured_args[0][:4] == ["docs", "+fetch", "--api-version", "v2"]
    assert "--as" in captured_args[0]


def test_lark_bot_badcase_draft_reads_lark_sheet_row(monkeypatch) -> None:
    client = TestClient(app)
    unique = uuid4().hex

    class FakeReadConnector:
        def run_json(self, args: list[str], stdin: str | None = None) -> dict[str, object]:
            assert args[:2] == ["sheets", "+csv-get"]
            assert "--rows-json" in args
            return {
                "rows": [
                    {
                        "row_number": 1,
                        "values": {
                            "A": "原始输入",
                            "B": "模型输出",
                            "C": "正确答案",
                            "D": "错误现象",
                        },
                    },
                    {
                        "row_number": 2,
                        "values": {
                            "A": "https://example.com/sheet-input.png",
                            "B": '{"answer":"3"}',
                            "C": '{"answer":"8"}',
                            "D": "把 8 识别成 3",
                        },
                    },
                ]
            }

    monkeypatch.setattr(routes, "_lark_bot_read_connector", lambda actor: FakeReadConnector())

    response = client.post(
        "/api/lark/bot/badcase-drafts",
        json={
            "actor": f"ou_{unique}",
            "open_id": f"ou_{unique}",
            "chat_id": f"oc_{unique}",
            "message_id": f"om_{unique}",
            "text": "帮我调试表格这一行：https://example.larkoffice.com/sheets/shtcn123?sheet=tab-1&row=2",
            "resolve_link_content": True,
        },
    )

    assert response.status_code == 200
    draft = response.json()
    assert draft["status"] == "needs_more_info"
    assert set(draft["missing_fields"]) >= {
        "case_id",
        "prompt",
        "scoring_standard",
    }
    context = next(item for item in draft["attachments"] if item.get("link_type") == "lark_sheet")
    assert context["status"] == "spreadsheet_row_rejected"
    assert context["selected_row"] == "2"
    assert context["row_count"] == 1


def test_lark_bot_badcase_draft_maps_real_debug_sheet_headers(monkeypatch) -> None:
    client = TestClient(app)
    unique = uuid4().hex

    class FakeReadConnector:
        def run_json(self, args: list[str], stdin: str | None = None) -> dict[str, object]:
            if args[:2] == ["sheets", "+csv-get"]:
                assert "A1:AZ50" in args
                return {
                    "rows": [
                        {
                            "row_number": 1,
                            "values": {
                                "A": "id",
                                "D": "cot_content",
                                "E": "predict",
                                "G": "gpt_response",
                                "H": "user prompt",
                                "I": "参考答案",
                                "J": "video",
                                "L": "评分标准（详细版）",
                                "M": "评分标准（宽松版）",
                                "R": "评估问题反馈\n（务必再三确认）",
                            },
                        },
                        {
                            "row_number": 2,
                            "values": {
                                "A": "JSZN-131",
                                "D": "model chain of thought",
                                "E": '{"video_action_segments":[]}',
                                "G": "EvalOpCheckTimestamp 失败：clip 0 end_s 不在范围内",
                                "H": "You need to accurately divide the movements.",
                                "I": (
                                    '{"video_action_segments":[{"subtask_label":"pick","start_s":0.1,'
                                    '"end_s":1.0}]}'
                                ),
                                "J": "JSZN-131.mp4",
                                "L": "详细标准：必须严格匹配 subtask_label、顺序和时间戳。",
                                "M": "宽松标准：subtask_label 的内容、先后顺序必须和参考答案一致。",
                                "R": "自动复测发现：baseline 0/3；targeted 1/1；verification 2/2。",
                            },
                        },
                    ]
                }
            if args[:2] == ["sheets", "+cells-get"]:
                assert "J2:J2" in args
                return {
                    "ranges": [
                        {
                            "cells": [
                                [
                                    {
                                        "value": "JSZN-131.mp4",
                                        "rich_text": [
                                            {
                                                "type": "attachment",
                                                "attachment_token": "file-token-1",
                                                "text": "JSZN-131.mp4",
                                                "mime_type": "video/mp4",
                                                "file_size": 123,
                                            }
                                        ],
                                    }
                                ]
                            ]
                        }
                    ]
                }
            if args[:2] == ["api", "GET"]:
                assert "/open-apis/drive/v1/medias/file-token-1/download" in args
                output_path = Path(args[args.index("--output") + 1])
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(b"fake-video")
                return {"path": str(output_path)}
            raise AssertionError(args)

    monkeypatch.setattr(routes, "_lark_bot_read_connector", lambda actor: FakeReadConnector())

    response = client.post(
        "/api/lark/bot/badcase-drafts",
        json={
            "actor": f"ou_{unique}",
            "open_id": f"ou_{unique}",
            "chat_id": f"oc_{unique}",
            "message_id": f"om_{unique}",
            "text": "小D，帮我调试这个表格：https://example.larkoffice.com/sheets/shtcn123?sheet=tab-1",
            "resolve_link_content": True,
        },
    )

    assert response.status_code == 200
    draft = response.json()
    assert draft["status"] == "ready_for_confirmation"
    assert draft["input_source"].startswith("file:///")
    assert draft["input_source"].endswith("JSZN-131.mp4")
    assert draft["model_output"] == '{"video_action_segments":[]}'
    assert "temporal_segments" in draft["expected_output"]
    assert draft["issue_summary"] == "EvalOpCheckTimestamp 失败：clip 0 end_s 不在范围内"
    assert draft["scoring_standard"] == "详细标准：必须严格匹配 subtask_label、顺序和时间戳。"
    context = next(item for item in draft["attachments"] if item.get("link_type") == "lark_sheet")
    assert context["selected_row"] == "2"
    assert context["schema_mappings"]["scoring_standard"]["source_header"] == "评分标准（详细版）"
    assert context["media_input"]["status"] == "downloaded"
    assert context["media_input"]["attachment_token"] == "file-token-1"

    confirmed = client.post(
        f"/api/lark/bot/badcase-drafts/{draft['draft_id']}/confirm",
        json={"actor": f"ou_{unique}", "create_job": True},
    )

    assert confirmed.status_code == 200
    submitted = confirmed.json()
    assert submitted["draft"]["submitted_case_id"] == "JSZN-131"
    saved_case = routes.job_repository.get_case("JSZN-131")
    assert saved_case is not None
    assert saved_case.prompt == "You need to accurately divide the movements."
    assert saved_case.scoring_standard == "详细标准：必须严格匹配 subtask_label、顺序和时间戳。"
    assert saved_case.image_uri.startswith("file:///")


def test_lark_bot_badcase_draft_uses_requested_sheet_label_to_select_row(monkeypatch) -> None:
    client = TestClient(app)
    unique = uuid4().hex

    class FakeReadConnector:
        def run_json(self, args: list[str], stdin: str | None = None) -> dict[str, object]:
            if args[:2] == ["sheets", "+csv-get"]:
                return {
                    "rows": [
                        {
                            "row_number": 1,
                            "values": {
                                "A": "id",
                                "E": "predict",
                                "G": "gpt_response",
                                "H": "user prompt",
                                "I": "参考答案",
                                "J": "video",
                                "K": "chains_alpha",
                            },
                        },
                        {
                            "row_number": 2,
                            "values": {
                                "A": "JSZN-096",
                                "E": '{"answer":"wrong-row"}',
                                "G": "不要选这一行",
                                "H": "wrong prompt",
                                "I": '{"answer":"wrong"}',
                                "J": "JSZN-096.mp4",
                                "K": "[]",
                            },
                        },
                        {
                            "row_number": 29,
                            "values": {
                                "A": "JSZN-131",
                                "E": '{"answer":"target-row"}',
                                "G": "定位到 JSZN-131 的错误现象",
                                "H": "target prompt",
                                "I": '{"answer":"target"}',
                                "J": "JSZN-131.mp4",
                                "K": "[]",
                            },
                        },
                    ]
                }
            if args[:2] == ["sheets", "+cells-get"]:
                assert "J29:J29" in args
                return {
                    "ranges": [
                        {
                            "cells": [
                                [
                                    {
                                        "value": "JSZN-131.mp4",
                                        "rich_text": [
                                            {
                                                "type": "attachment",
                                                "attachment_token": "file-token-131",
                                                "text": "JSZN-131.mp4",
                                                "mime_type": "video/mp4",
                                                "file_size": 123,
                                            }
                                        ],
                                    }
                                ]
                            ]
                        }
                    ]
                }
            if args[:2] == ["api", "GET"]:
                output_path = Path(args[args.index("--output") + 1])
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(b"fake-video")
                return {"path": str(output_path)}
            raise AssertionError(args)

    monkeypatch.setattr(routes, "_lark_bot_read_connector", lambda actor: FakeReadConnector())

    response = client.post(
        "/api/lark/bot/badcase-drafts",
        json={
            "actor": f"ou_{unique}",
            "open_id": f"ou_{unique}",
            "chat_id": f"oc_{unique}",
            "message_id": f"om_{unique}",
            "text": "小D，处理 JSZN-131：https://example.larkoffice.com/sheets/shtcn123?sheet=tab-1",
            "resolve_link_content": True,
        },
    )

    assert response.status_code == 200
    draft = response.json()
    assert draft["status"] == "ready_for_confirmation"
    assert draft["model_output"] == '{"answer":"target-row"}'
    assert draft["issue_summary"] == "定位到 JSZN-131 的错误现象"
    context = next(item for item in draft["attachments"] if item.get("link_type") == "lark_sheet")
    assert context["target_label"] == "JSZN-131"
    assert context["selected_label"] == "JSZN-131"
    assert context["selected_row"] == "29"


def test_lark_bot_badcase_draft_requires_media_when_sheet_attachment_download_fails(
    monkeypatch,
) -> None:
    client = TestClient(app)
    unique = uuid4().hex

    class FakeReadConnector:
        def run_json(self, args: list[str], stdin: str | None = None) -> dict[str, object]:
            if args[:2] == ["sheets", "+csv-get"]:
                return {
                    "rows": [
                        {
                            "row_number": 1,
                            "values": {
                                "A": "id",
                                "E": "predict",
                                "G": "gpt_response",
                                "H": "user prompt",
                                "I": "参考答案",
                                "J": "video",
                                "K": "chains_alpha",
                            },
                        },
                        {
                            "row_number": 2,
                            "values": {
                                "A": "JSZN-131",
                                "E": '{"video_action_segments":[]}',
                                "G": "EvalOpCheckTimestamp 失败",
                                "H": "target prompt",
                                "I": (
                                    '{"video_action_segments":[{"subtask_label":"pick","start_s":0.1,'
                                    '"end_s":1.0}]}'
                                ),
                                "J": "JSZN-131.mp4",
                                "K": "[]",
                            },
                        },
                    ]
                }
            if args[:2] == ["sheets", "+cells-get"]:
                return {
                    "ranges": [
                        {
                            "cells": [
                                [
                                    {
                                        "value": "JSZN-131.mp4",
                                        "rich_text": [
                                            {
                                                "type": "attachment",
                                                "attachment_token": "file-token-1",
                                                "text": "JSZN-131.mp4",
                                                "mime_type": "video/mp4",
                                            }
                                        ],
                                    }
                                ]
                            ]
                        }
                    ]
                }
            if args[:2] == ["api", "GET"]:
                raise routes.LarkCliError(
                    "missing document media download scope: docs:document.media:download",
                    error_type="permission_denied",
                    permission_scopes=["docs:document.media:download"],
                )
            raise AssertionError(args)

    monkeypatch.setattr(routes, "_lark_bot_read_connector", lambda actor: FakeReadConnector())

    response = client.post(
        "/api/lark/bot/badcase-drafts",
        json={
            "actor": f"ou_{unique}",
            "open_id": f"ou_{unique}",
            "chat_id": f"oc_{unique}",
            "message_id": f"om_{unique}",
            "text": "小D，帮我调试这个表格：https://example.larkoffice.com/sheets/shtcn123?sheet=tab-1",
            "resolve_link_content": True,
        },
    )

    assert response.status_code == 200
    draft = response.json()
    assert draft["status"] == "needs_more_info"
    assert "input_source" in draft["missing_fields"]
    assert draft["input_source"] == ""
    context = next(item for item in draft["attachments"] if item.get("link_type") == "lark_sheet")
    assert context["status"] == "download_failed"
    assert context["media_input"]["status"] == "download_failed"
    assert context["media_input"]["permission_scopes"] == ["docs:document.media:download"]


def test_lark_bot_badcase_draft_replaces_stale_link_context_after_retry(monkeypatch) -> None:
    client = TestClient(app)
    unique = uuid4().hex
    download_attempts = 0

    class FakeReadConnector:
        def run_json(self, args: list[str], stdin: str | None = None) -> dict[str, object]:
            nonlocal download_attempts
            if args[:2] == ["sheets", "+csv-get"]:
                return {
                    "rows": [
                        {
                            "row_number": 1,
                            "values": {
                                "A": "id",
                                "E": "predict",
                                "G": "gpt_response",
                                "H": "user prompt",
                                "I": "参考答案",
                                "J": "video",
                                "K": "chains_alpha",
                            },
                        },
                        {
                            "row_number": 2,
                            "values": {
                                "A": "JSZN-131",
                                "E": '{"video_action_segments":[]}',
                                "G": "EvalOpCheckTimestamp 失败",
                                "H": "target prompt",
                                "I": (
                                    '{"video_action_segments":[{"subtask_label":"pick","start_s":0.1,'
                                    '"end_s":1.0}]}'
                                ),
                                "J": "JSZN-131.mp4",
                                "K": "[]",
                            },
                        },
                    ]
                }
            if args[:2] == ["sheets", "+cells-get"]:
                return {
                    "ranges": [
                        {
                            "cells": [
                                [
                                    {
                                        "value": "JSZN-131.mp4",
                                        "rich_text": [
                                            {
                                                "type": "attachment",
                                                "attachment_token": "file-token-1",
                                                "text": "JSZN-131.mp4",
                                                "mime_type": "video/mp4",
                                            }
                                        ],
                                    }
                                ]
                            ]
                        }
                    ]
                }
            if args[:2] == ["api", "GET"]:
                download_attempts += 1
                if download_attempts == 1:
                    raise routes.LarkCliError(
                        "missing document media download scope",
                        error_type="permission_denied",
                        permission_scopes=["docs:document.media:download"],
                    )
                output_path = Path(args[args.index("--output") + 1])
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(b"fake-video")
                return {}
            raise AssertionError(args)

    monkeypatch.setattr(routes, "_lark_bot_read_connector", lambda actor: FakeReadConnector())
    payload = {
        "actor": f"ou_{unique}",
        "open_id": f"ou_{unique}",
        "chat_id": f"oc_{unique}",
        "message_id": f"om_{unique}",
        "text": "小D，帮我调试这个表格：https://example.larkoffice.com/sheets/shtcn123?sheet=tab-1",
        "resolve_link_content": True,
    }

    first = client.post("/api/lark/bot/badcase-drafts", json=payload).json()
    second = client.post(
        "/api/lark/bot/badcase-drafts",
        json={**payload, "message_id": f"om_retry_{unique}"},
    ).json()

    assert first["status"] == "needs_more_info"
    assert second["status"] == "ready_for_confirmation"
    sheet_contexts = [
        item for item in second["attachments"] if item.get("link_type") == "lark_sheet"
    ]
    assert len(sheet_contexts) == 1
    assert sheet_contexts[0]["media_input"]["status"] == "downloaded"


def test_lark_bot_badcase_draft_reads_lark_base_record(monkeypatch) -> None:
    client = TestClient(app)
    unique = uuid4().hex

    class FakeReadConnector:
        def run_json(self, args: list[str], stdin: str | None = None) -> dict[str, object]:
            assert args[:2] == ["base", "+record-list"]
            return {
                "items": [
                    {
                        "record_id": "rec_1",
                        "fields": {
                            "原始输入": "https://example.com/base-input.png",
                            "模型输出": '{"answer":"3"}',
                            "正确答案": '{"answer":"8"}',
                            "错误现象": "把 8 识别成 3",
                        },
                    }
                ]
            }

    monkeypatch.setattr(routes, "_lark_bot_read_connector", lambda actor: FakeReadConnector())

    response = client.post(
        "/api/lark/bot/badcase-drafts",
        json={
            "actor": f"ou_{unique}",
            "open_id": f"ou_{unique}",
            "chat_id": f"oc_{unique}",
            "message_id": f"om_{unique}",
            "text": "帮我调试 Base 记录：https://bytedance.larkoffice.com/base/bascn123?table=tbl_1&record=rec_1",
            "resolve_link_content": True,
        },
    )

    assert response.status_code == 200
    draft = response.json()
    assert draft["status"] == "ready_for_confirmation"
    assert draft["input_source"] == "https://example.com/base-input.png"
    context = next(item for item in draft["attachments"] if item.get("link_type") == "lark_base")
    assert context["status"] == "content_resolved"
    assert context["selected_record"] == "rec_1"


def test_lark_bot_badcase_draft_keeps_read_failures_non_blocking(monkeypatch) -> None:
    client = TestClient(app)
    unique = uuid4().hex

    class FakeReadConnector:
        def run_json(self, args: list[str], stdin: str | None = None) -> dict[str, object]:
            raise routes.LarkCliError(
                "missing scope",
                error_type="permission_denied",
                permission_scopes=["docx:document:readonly"],
            )

    monkeypatch.setattr(routes, "_lark_bot_read_connector", lambda actor: FakeReadConnector())

    response = client.post(
        "/api/lark/bot/badcase-drafts",
        json={
            "actor": f"ou_{unique}",
            "open_id": f"ou_{unique}",
            "chat_id": f"oc_{unique}",
            "message_id": f"om_{unique}",
            "text": "帮我调试这个文档：https://bytedance.larkoffice.com/docx/doc-token",
            "resolve_link_content": True,
        },
    )

    assert response.status_code == 200
    draft = response.json()
    assert draft["status"] == "needs_more_info"
    context = next(item for item in draft["attachments"] if item.get("link_type") == "lark_doc")
    assert context["status"] == "read_failed"
    assert context["error_type"] == "permission_denied"
    assert context["permission_scopes"] == ["docx:document:readonly"]


def test_lark_bot_badcase_confirmation_card_preview_and_action_confirm() -> None:
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

    preview = client.get(f"/api/lark/bot/badcase-drafts/{draft['draft_id']}/confirmation-card")

    assert preview.status_code == 200
    payload = preview.json()
    assert payload["message_type"] == "interactive"
    assert payload["content"]["header"]["title"]["content"] == "确认提交 Debug 任务"
    assert payload["delivery_args"][:4] == [
        "im",
        "+messages-reply",
        "--message-id",
        f"om_{unique}",
    ]
    assert "--msg-type" in payload["delivery_args"]
    assert "interactive" in payload["delivery_args"]
    actions = payload["content"]["elements"][1]["actions"]
    assert actions[0]["value"] == {
        "action": "confirm_badcase_draft",
        "draft_id": draft["draft_id"],
        "create_job": True,
    }
    assert actions[0]["behaviors"] == [
        {
            "type": "callback",
            "value": {
                "action": "confirm_badcase_draft",
                "draft_id": draft["draft_id"],
                "create_job": True,
            },
        }
    ]
    assert actions[1]["behaviors"] == [
        {
            "type": "callback",
            "value": {
                "action": "cancel_badcase_draft",
                "draft_id": draft["draft_id"],
            },
        }
    ]
    fallback_confirm = next(
        action for action in actions if action.get("text", {}).get("content") == "打开确认页"
    )
    parsed_url = urlparse(fallback_confirm["url"])
    assert parsed_url.path.endswith(
        f"/api/lark/bot/badcase-drafts/{draft['draft_id']}/confirm-link"
    )
    assert parse_qs(parsed_url.query)["action"] == ["confirm_badcase_draft"]
    assert parse_qs(parsed_url.query)["token"][0]

    action_response = client.post(
        "/api/lark/bot/events",
        json={
            "header": {"event_type": "card.action.trigger"},
            "event": {
                "operator": {"operator_id": {"open_id": f"ou_{unique}"}},
                "action": {
                    "value": {
                        "action": "confirm_badcase_draft",
                        "draft_id": draft["draft_id"],
                    }
                },
            },
        },
    )

    assert action_response.status_code == 200
    body = action_response.json()
    assert body["handled"] is True
    assert body["action"] == "confirm_badcase_draft"
    assert body["draft"]["status"] == "submitted"
    assert body["submitted_job"]["job_id"]
    assert body["reply"]["target_type"] == "message"
    assert body["reply"]["message_id"] == f"om_{unique}"
    assert "已收到确认，Debug 任务已提交" in body["reply"]["markdown"]
    assert body["submitted_job"]["job_id"] in body["reply"]["markdown"]
    assert "完成后我会发回根因摘要、证据、报告入口和后续闭环选项" in body["reply"]["markdown"]


def test_lark_bot_badcase_confirmation_link_requires_token_and_confirms_once() -> None:
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
    card = client.get(f"/api/lark/bot/badcase-drafts/{draft['draft_id']}/confirmation-card").json()
    actions = card["content"]["elements"][1]["actions"]
    confirm_url = next(
        action["url"] for action in actions if action.get("text", {}).get("content") == "打开确认页"
    )
    parsed = urlparse(confirm_url)

    rejected = client.post(
        parsed.path,
        params={"action": "confirm_badcase_draft", "token": "wrong-token"},
    )
    assert rejected.status_code == 403

    query = parse_qs(parsed.query)
    page = client.get(parsed.path, params={key: values[0] for key, values in query.items()})
    assert page.status_code == 200
    assert "确认提交 Debug 任务" in page.text

    confirmed = client.post(parsed.path, params={key: values[0] for key, values in query.items()})
    assert confirmed.status_code == 200
    assert "已提交 Debug 任务" in confirmed.text
    submitted = routes.job_repository.get_lark_bot_badcase_draft(draft["draft_id"])
    assert submitted is not None
    assert submitted.status == "submitted"
    first_job_id = submitted.submitted_job_id

    repeated = client.post(parsed.path, params={key: values[0] for key, values in query.items()})
    assert repeated.status_code == 200
    repeated_draft = routes.job_repository.get_lark_bot_badcase_draft(draft["draft_id"])
    assert repeated_draft is not None
    assert repeated_draft.submitted_job_id == first_job_id


def test_lark_bot_badcase_confirm_saves_source_sheet_row_mapping() -> None:
    client = TestClient(app)
    unique = uuid4().hex
    draft = client.post(
        "/api/lark/bot/badcase-drafts",
        json={
            "actor": f"ou_{unique}",
            "open_id": f"ou_{unique}",
            "chat_id": f"oc_{unique}",
            "message_id": f"om_{unique}",
            "text": "小D，帮我调试这个表格",
            "input_source": "file:///tmp/input.mp4",
            "model_output": '{"answer":"3"}',
            "expected_output": '{"answer":"8"}',
            "issue_summary": "把 8 识别成 3",
            "attachments": [
                {
                    "type": "link_context",
                    "link_type": "lark_sheet",
                    "token": "spreadsheet-token-1",
                    "sheet_id": "sheet-1",
                    "selected_row": "12",
                }
            ],
        },
    ).json()

    confirmed = client.post(
        f"/api/lark/bot/badcase-drafts/{draft['draft_id']}/confirm",
        json={"actor": f"ou_{unique}", "create_job": True},
    ).json()

    job_id = confirmed["submitted_job"]["job_id"]
    mapping = routes.job_repository.get_spreadsheet_row_mapping_by_job_id(job_id)
    assert mapping is not None
    assert mapping.spreadsheet_id == "spreadsheet-token-1"
    assert mapping.sheet_id == "sheet-1"
    assert mapping.row_id == "12"
    assert mapping.case_id == confirmed["draft"]["submitted_case_id"]
    assert mapping.job_id == job_id


def test_lark_bot_badcase_draft_can_be_cancelled_before_submission() -> None:
    client = TestClient(app)
    unique = uuid4().hex

    response = client.post(
        "/api/lark/bot/badcase-drafts",
        json={
            "actor": f"ou_{unique}",
            "open_id": f"ou_{unique}",
            "chat_id": f"oc_{unique}",
            "message_id": f"om_{unique}",
            "text": "帮我调试这个识别错误，图片：https://example.com/input.png",
        },
    )
    draft = response.json()

    cancelled = client.post(
        f"/api/lark/bot/badcase-drafts/{draft['draft_id']}/cancel",
        json={"actor": f"ou_{unique}", "note": "wrong sample"},
    )

    assert cancelled.status_code == 200
    body = cancelled.json()
    assert body["status"] == "cancelled"
    assert body["error_message"] == "wrong sample"

    rejected = client.post(
        f"/api/lark/bot/badcase-drafts/{draft['draft_id']}/confirm",
        json={"actor": f"ou_{unique}", "create_job": True},
    )

    assert rejected.status_code == 409


def test_lark_bot_permission_checklist_reads_missing_scope_from_badcase_draft() -> None:
    client = TestClient(app)
    routes.job_repository.save_lark_bot_badcase_draft(
        draft_id="draft-media-permission",
        actor="local-smoke",
        status="needs_more_info",
        source_text="小D，帮我调试这个表格",
        attachments=[
            {
                "type": "link_context",
                "link_type": "lark_sheet",
                "status": "download_failed",
                "media_input": {
                    "status": "download_failed",
                    "attachment_token": "file-token-1",
                    "permission_scopes": ["docs:document.media:download"],
                },
            }
        ],
        missing_fields=["input_source"],
    )

    response = client.get("/api/lark/bot/permission-checklist")

    assert response.status_code == 200
    body = response.json()
    assert body["blocking_scopes"] == ["docs:document.media:download"]
    drive_requirement = {requirement["scope"]: requirement for requirement in body["requirements"]}[
        "docs:document.media:download"
    ]
    assert drive_requirement["recent_missing"] is True
