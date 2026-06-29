# ruff: noqa: F403,F405
import asyncio

from tests.api.lark_bot.common import *


def test_spreadsheet_rerun_downloads_lark_sheet_video_attachment(monkeypatch, tmp_path) -> None:
    client = TestClient(app)
    rows_json = {
        "rows": [
            {
                "row_number": 1,
                "values": {
                    "A": "id",
                    "E": "predict",
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
                    "H": "Segment the video and return video_action_segments JSON.",
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

    class FakeReadConnector:
        def __init__(self) -> None:
            self.calls: list[list[str]] = []

        def run_json(self, args: list[str], stdin: str | None = None) -> dict[str, object]:
            self.calls.append(args)
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
                output_path.write_bytes(b"downloaded-video")
                return {"path": str(output_path)}
            raise AssertionError(args)

    connector = FakeReadConnector()
    original_client = routes.spreadsheet_sync_client
    original_settings = routes.settings
    try:
        routes.spreadsheet_sync_client = LarkSpreadsheetClient(
            RowsJsonSpreadsheetTransport(rows_json)
        )
        routes.settings = original_settings.model_copy(update={"image_artifact_dir": tmp_path})
        monkeypatch.setattr(routes, "_lark_bot_read_connector", lambda actor: connector)

        response = client.post(
            "/spreadsheets/rerun",
            json={
                "spreadsheet_id": "spreadsheet-1",
                "sheet_id": "sheet-1",
                "row_ids": ["2"],
                "baseline_trials": 1,
                "auto_run": False,
            },
        )
    finally:
        routes.spreadsheet_sync_client = original_client
        routes.settings = original_settings

    assert response.status_code == 202
    assert any(call[:2] == ["sheets", "+cells-get"] for call in connector.calls)
    assert any(call[:2] == ["api", "GET"] for call in connector.calls)
    saved_case = routes.job_repository.get_case("JSZN-131")
    assert saved_case is not None
    assert saved_case.image_uri.startswith("file:///")
    assert saved_case.image_uri.endswith("JSZN-131.mp4")
    assert (tmp_path / "lark-bot-media" / "file-token-1-JSZN-131.mp4").exists()


def test_lark_bot_spreadsheet_rerun_card_confirmation_creates_real_jobs(monkeypatch) -> None:
    client = TestClient(app)
    sync_client = StaticSpreadsheetClient(
        [
            SpreadsheetSourceRow(
                row_id="2",
                values={
                    "case_id": "card-rerun-case-1",
                    "image_uri": "file://card-rerun-case-1.png",
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
                    "case_id": "card-rerun-case-2",
                    "image_uri": "file://card-rerun-case-2.png",
                    "prompt": "Read the answer",
                    "golden_answer_json": {"answers": [{"box_id": 1, "student_answer": "43"}]},
                    "scoring_standard": "exact match",
                    "predictions_json": [{"trial": 1, "raw_output": '{"answers":[]}', "score": 0}],
                    "avg_score": 0.0,
                },
            ),
        ]
    )
    monkeypatch.setattr(routes, "spreadsheet_sync_client", sync_client, raising=False)
    monkeypatch.setattr(
        routes,
        "job_service",
        DebugJobService(
            routes.job_repository,
            model_provider=lambda case: FakeModelAdapter(outputs=[case.predictions[0].raw_output]),
        ),
        raising=False,
    )

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "处理这个表前2行：https://example.larkoffice.com/sheets/abc?sheet=def",
            "message_id": "om_sheet_real_run_card",
            "open_id": "ou_sheet_real_run_card",
            "chat_id": "oc_sheet_real_run_card",
        },
    )

    assert response.status_code == 200
    reply = response.json()["reply"]
    assert reply["message_type"] == "interactive"
    command_id = reply["content"]["elements"][1]["actions"][0]["value"]["command_id"]

    confirm_response = client.post(
        "/api/lark/bot/events",
        json={
            "header": {"event_type": "card.action.trigger"},
            "event": {
                "operator": {"open_id": "ou_card_reviewer"},
                "action": {
                    "value": {
                        "action": "confirm_pending_command",
                        "command_id": command_id,
                    }
                },
            },
        },
    )

    assert confirm_response.status_code == 200
    body = confirm_response.json()
    assert body["handled"] is True
    assert body["pending_command"]["status"] == "confirmed"
    reply = body["reply"]
    assert reply["message_type"] == "interactive"
    assert reply["content"]["header"]["title"]["content"] == "表格批处理已确认，后台执行中"

    completed = _wait_pending_command_status(command_id, "executed")
    result = completed.execution_result["spreadsheet_rerun"]
    assert sync_client.requested_spreadsheet_id == "abc"
    assert sync_client.requested_sheet_id == "def"
    assert result["imported_case_ids"] == ["card-rerun-case-1", "card-rerun-case-2"]
    assert [job["case_id"] for job in result["jobs"]] == [
        "card-rerun-case-1",
        "card-rerun-case-2",
    ]
    assert all(routes.job_repository.get_job(job["job_id"]) is not None for job in result["jobs"])
    run_panel_text = "\n".join(
        item.get("content", "") for item in reply["content"]["elements"] if isinstance(item, dict)
    )
    assert "有效行：`2, 3`" in run_panel_text
    run = routes.job_repository.get_active_xiaod_execution_run(
        tenant_key="",
        chat_id="oc_sheet_real_run_card",
        open_id="ou_sheet_real_run_card",
    )
    assert run is not None
    assert run.summary["job_ids"]


def test_lark_bot_spreadsheet_rerun_confirmation_queues_without_running_model(
    monkeypatch,
) -> None:
    client = TestClient(app)
    sync_client = StaticSpreadsheetClient(
        [
            SpreadsheetSourceRow(
                row_id="2",
                values=_valid_spreadsheet_row_values("card-rerun-queued-only"),
            )
        ]
    )
    monkeypatch.setattr(routes, "spreadsheet_sync_client", sync_client, raising=False)

    def forbidden_model_provider(case):
        del case
        raise AssertionError("XiaoD spreadsheet rerun confirmation must only queue jobs")

    routes.job_service._model_provider = forbidden_model_provider

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": (
                "处理这个表前1行，跑完返回报告："
                "https://example.larkoffice.com/sheets/abc?sheet=def"
            ),
            "message_id": "om_sheet_queue_only",
            "open_id": "ou_sheet_queue_only",
            "chat_id": "oc_sheet_queue_only",
        },
    )

    assert response.status_code == 200
    command_id = response.json()["reply"]["content"]["elements"][1]["actions"][0]["value"][
        "command_id"
    ]

    confirm_response = client.post(
        "/api/lark/bot/events",
        json={
            "header": {"event_type": "card.action.trigger"},
            "event": {
                "operator": {"open_id": "ou_card_reviewer"},
                "action": {
                    "value": {
                        "action": "confirm_pending_command",
                        "command_id": command_id,
                    }
                },
            },
        },
    )

    assert confirm_response.status_code == 200
    completed = _wait_pending_command_status(command_id, "executed")
    result = completed.execution_result["spreadsheet_rerun"]
    assert result["auto_closure_reports"] == []
    assert len(result["jobs"]) == 1
    job_id = result["jobs"][0]["job_id"]
    job = routes.job_repository.get_job(job_id)
    assert job is not None
    assert job.status == "created"
    batch = routes.job_repository.get_batch(job.artifact_group_id)
    assert batch is not None
    assert batch.retry_policy["auto_run"] is False
    assert batch.retry_policy["auto_closure"] is True
    assert batch.retry_policy["submit_controlled_probes"] is True
    assert batch.retry_policy["queue_priority"] == "interactive"


def test_spreadsheet_rerun_execution_marks_active_run_batch_before_backend_call(
    monkeypatch,
) -> None:
    unique = uuid4().hex
    command_id = f"cmd-rerun-batch-started-{unique}"
    command = routes.job_repository.create_lark_bot_pending_command(
        command_id=command_id,
        actor=f"ou_batch_started_{unique}",
        open_id=f"ou_batch_started_{unique}",
        chat_id=f"oc_batch_started_{unique}",
        message_id=f"om_batch_started_{unique}",
        tenant_key="tenant-batch-started",
        identity="bot",
        profile="xiaoD",
        command_text="/debug spreadsheet rerun https://example.larkoffice.com/sheets/abc?sheet=def def 2",
        action_kind="spreadsheet_rerun",
        action={
            "kind": "spreadsheet_rerun",
            "parameters": {
                "source": "https://example.larkoffice.com/sheets/abc?sheet=def",
                "sheet_id": "def",
                "row_ids": ["2"],
                "preflight": {
                    "status": "ok",
                    "valid_row_ids": ["2"],
                    "valid_case_ids": ["case-2"],
                },
            },
        },
        card={},
        note="test",
        expires_at="2099-01-01T00:00:00+00:00",
    )
    routes._ensure_xiaod_spreadsheet_rerun_active_run(command)

    class EmptyRerunResult:
        jobs: list[object] = []

        def model_copy(self, *, update: dict[str, object]) -> "EmptyRerunResult":
            self.auto_closure_reports = update.get("auto_closure_reports", [])
            return self

        def model_dump(self, mode: str = "json") -> dict[str, object]:
            del mode
            return {
                "imported_case_ids": [],
                "imported_rows": [],
                "rejected_rows": [],
                "skipped_row_ids": [],
                "jobs": [],
                "auto_closure_reports": getattr(self, "auto_closure_reports", []),
            }

    async def fake_rerun_spreadsheet(request: routes.SpreadsheetRerunRequest) -> EmptyRerunResult:
        assert request.artifact_group_id.startswith("sheet-rerun-")
        run = routes.job_repository.get_active_xiaod_execution_run(
            tenant_key="tenant-batch-started",
            chat_id=f"oc_batch_started_{unique}",
            open_id=f"ou_batch_started_{unique}",
        )
        assert run is not None
        assert run.summary["batch_id"] == request.artifact_group_id
        assert run.summary["stage"] == "batch_started"
        return EmptyRerunResult()

    monkeypatch.setattr(routes, "rerun_spreadsheet", fake_rerun_spreadsheet)

    routes._execute_lark_bot_pending_command(command)

    notification = _xiaod_run_progress_notification(
        routes.job_repository.get_active_xiaod_execution_run(
            tenant_key="tenant-batch-started",
            chat_id=f"oc_batch_started_{unique}",
            open_id=f"ou_batch_started_{unique}",
        ).run_id
    )
    assert notification.stage == "starting"
    assert notification.payload.content["header"]["title"]["content"] == (
        "表格批处理已确认，正在后台启动"
    )


def test_lark_bot_spreadsheet_rerun_report_writeback_waits_for_sync_decision(
    monkeypatch,
) -> None:
    client = TestClient(app)
    sync_client = StaticSpreadsheetClient(
        [
            SpreadsheetSourceRow(
                row_id="2",
                values=_valid_spreadsheet_row_values("card-rerun-report-writeback"),
            )
        ]
    )
    writeback_client = RecordingWritebackClient()
    monkeypatch.setattr(routes, "spreadsheet_sync_client", sync_client, raising=False)
    monkeypatch.setattr(routes, "spreadsheet_writeback_client", writeback_client, raising=False)
    monkeypatch.setattr(
        routes,
        "job_service",
        DebugJobService(
            routes.job_repository,
            model_provider=lambda case: FakeModelAdapter(outputs=[case.predictions[0].raw_output]),
        ),
        raising=False,
    )

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": (
                "处理这个表前1行，跑完返回报告并写回对应列："
                "https://example.larkoffice.com/sheets/abc?sheet=def"
            ),
            "message_id": "om_sheet_report_writeback_confirm",
            "open_id": "ou_sheet_report_writeback_confirm",
            "chat_id": "oc_sheet_report_writeback_confirm",
        },
    )

    assert response.status_code == 200
    command_id = response.json()["reply"]["content"]["elements"][1]["actions"][0]["value"][
        "command_id"
    ]
    confirm_response = client.post(
        "/api/lark/bot/events",
        json={
            "header": {"event_type": "card.action.trigger"},
            "event": {
                "operator": {"open_id": "ou_card_reviewer"},
                "action": {
                    "value": {
                        "action": "confirm_pending_command",
                        "command_id": command_id,
                    }
                },
            },
        },
    )

    assert confirm_response.status_code == 200
    body = confirm_response.json()
    assert body["pending_command"]["status"] == "confirmed"
    assert body["reply"]["content"]["header"]["title"]["content"] == "表格批处理已确认，后台执行中"
    completed = _wait_pending_command_status(command_id, "executed")
    execution_result = completed.execution_result
    result = execution_result["spreadsheet_rerun"]
    job_id = result["jobs"][0]["job_id"]
    assert execution_result["writeback_requested"] is True
    assert execution_result["writeback_decision_status"] == "not_ready"
    assert result["auto_closure_reports"] == []
    assert writeback_client.update_count == 0
    assert routes.job_repository.get_spreadsheet_writeback_audit(job_id) is None

    worker = routes.build_job_worker(
        service=routes.job_service,
        repository=routes.job_repository,
        writeback_client=None,
        report_base_url="https://debug-agent.local",
        auto_writeback_enabled=False,
        auto_closure_enabled=True,
    )
    asyncio.run(worker.tick())

    decision = routes.job_repository.get_pending_xiaod_decision(
        tenant_key="",
        chat_id="oc_sheet_report_writeback_confirm",
        open_id="ou_sheet_report_writeback_confirm",
        decision_kind="spreadsheet_rerun_writeback_sync",
    )
    assert decision is not None
    assert decision.command_id == command_id
    assert decision.payload["default"] == "no_sync"
    run = routes.job_repository.get_active_xiaod_execution_run(
        tenant_key="",
        chat_id="oc_sheet_report_writeback_confirm",
        open_id="ou_sheet_report_writeback_confirm",
    )
    assert run is not None
    assert run.status == "writeback_decision_pending"
    assert run.summary["writeback_decision_status"] == "pending"
    assert run.summary["auto_closure_reports"][0]["writeback_status"] == "sync_decision_pending"

    notification = routes.xiaod_run_progress_notification_controller.notification_for_run(run)
    assert notification is not None
    assert notification.payload.content["header"]["title"]["content"] == "Debug 报告已生成"
    report_actions = notification.payload.content["elements"][3]["actions"]
    assert [action["text"]["content"] for action in report_actions] == [
        "打开最终报告",
        "查看运行批次",
    ]
    assert report_actions[1]["url"].endswith(
        f"/xiaod/views/debug-batches/{run.summary['batch_id']}"
    )
    decision_actions = notification.payload.content["elements"][6]["actions"]
    assert [action["text"]["content"] for action in decision_actions] == [
        "同步到飞书表格",
        "不同步",
    ]


def test_xiaod_spreadsheet_rerun_progress_cards_cover_async_dogfood_lifecycle() -> None:
    batch_id = "batch-xiaod-async-progress"
    job_id = "job-xiaod-async-progress"
    command_id = "cmd-xiaod-async-progress"
    run_id = "run-xiaod-async-progress"
    routes.job_repository.create_batch(
        batch_id=batch_id,
        total_jobs=1,
        retry_policy={"source": "spreadsheet_rerun", "auto_closure": True},
    )
    routes.job_repository.create_job(
        job_id=job_id,
        case_id="handwrite233",
        artifact_group_id=batch_id,
    )
    routes.job_repository.create_xiaod_execution_run(
        run_id=run_id,
        tenant_key="tenant-progress",
        chat_id="oc_progress",
        open_id="ou_progress",
        command_id=command_id,
        batch_id=batch_id,
        action_kind="spreadsheet_rerun",
        status="active",
        summary={
            "command_id": command_id,
            "message_id": "om_progress",
            "chat_id": "oc_progress",
            "open_id": "ou_progress",
            "batch_id": batch_id,
            "job_ids": [job_id],
            "report_requested": True,
            "report_count": 0,
            "writeback_requested": False,
            "writeback_decision_status": "not_requested",
        },
    )

    created = _xiaod_run_progress_notification(run_id)
    assert created.stage == "created"
    assert created.payload.content["header"]["title"]["content"] == "表格批处理任务已创建"

    routes.job_repository.mark_running(job_id)
    running = _xiaod_run_progress_notification(run_id)
    assert running.stage == "running"
    assert running.payload.content["header"]["title"]["content"] == "表格批处理正在执行"

    routes.job_repository.mark_completed(job_id)
    report_pending = _xiaod_run_progress_notification(run_id)
    assert report_pending.stage == "report_pending"
    assert (
        report_pending.payload.content["header"]["title"]["content"]
        == "表格批处理已完成，等待报告生成"
    )
    assert "已生成 0/1 份自动闭环报告" in report_pending.payload.markdown

    row_results = [
        {
            "row_id": "2",
            "case_id": "handwrite233",
            "job_id": job_id,
            "job_status": "completed",
            "report_url": f"/api/artifacts/files/{job_id}_auto_closure_report.md",
            "writeback_status": "not_requested",
            "source_mapped": True,
            "spreadsheet_id": "spreadsheet-progress",
            "sheet_id": "sheet-progress",
        }
    ]
    report_payload = {
        "job_id": job_id,
        "case_id": "handwrite233",
        "report_artifact_url": f"/api/artifacts/files/{job_id}_auto_closure_report.md",
        "writeback_status": "not_requested",
    }
    routes.job_repository.complete_xiaod_execution_run(
        run_id,
        status="active",
        summary={
            "command_id": command_id,
            "message_id": "om_progress",
            "chat_id": "oc_progress",
            "open_id": "ou_progress",
            "batch_id": batch_id,
            "job_ids": [job_id],
            "row_results": row_results,
            "report_requested": True,
            "report_count": 1,
            "writeback_requested": False,
            "writeback_decision_status": "not_requested",
            "auto_closure_reports": [report_payload],
        },
    )
    report_generated = _xiaod_run_progress_notification(run_id)
    assert report_generated.stage == "report_generated"
    assert report_generated.payload.content["header"]["title"]["content"] == "Debug 报告已生成"

    row_results[0]["writeback_status"] = "sync_decision_pending"
    report_payload["writeback_status"] = "sync_decision_pending"
    routes.job_repository.complete_xiaod_execution_run(
        run_id,
        status="writeback_decision_pending",
        summary={
            "command_id": command_id,
            "message_id": "om_progress",
            "chat_id": "oc_progress",
            "open_id": "ou_progress",
            "batch_id": batch_id,
            "job_ids": [job_id],
            "row_results": row_results,
            "report_requested": True,
            "report_count": 1,
            "writeback_requested": True,
            "writeback_decision_status": "pending",
            "auto_closure_reports": [report_payload],
        },
    )
    writeback_decision = _xiaod_run_progress_notification(run_id)
    assert writeback_decision.stage == "writeback_decision_pending"
    assert writeback_decision.payload.content["header"]["title"]["content"] == "Debug 报告已生成"
    report_actions = writeback_decision.payload.content["elements"][3]["actions"]
    assert report_actions[0]["text"]["content"] == "打开最终报告"
    decision_actions = writeback_decision.payload.content["elements"][6]["actions"]
    assert [action["text"]["content"] for action in decision_actions] == [
        "同步到飞书表格",
        "不同步",
    ]


def test_xiaod_run_progress_counts_reports_only_for_source_mapped_rows() -> None:
    unique = uuid4().hex
    run_id = f"run-source-report-count-{unique}"
    command_id = f"cmd-source-report-count-{unique}"
    batch_id = f"batch-source-report-count-{unique}"
    source_job_id = f"job-source-report-count-{unique}"
    probe_job_id = f"job-probe-report-count-{unique}"
    routes.job_repository.create_batch(
        batch_id=batch_id,
        total_jobs=2,
        retry_policy={"queue_priority": "interactive"},
    )
    routes.job_repository.create_job(
        job_id=source_job_id,
        case_id="handwrite233",
        artifact_group_id=batch_id,
    )
    routes.job_repository.create_job(
        job_id=probe_job_id,
        case_id="handwrite233__hypothesis_probe__probe_h1",
        artifact_group_id=batch_id,
    )
    routes.job_repository.mark_completed(source_job_id)
    routes.job_repository.mark_completed(probe_job_id)
    routes.job_repository.save_lark_report_document(
        job_id=source_job_id,
        status="published",
        document_url="https://bytedance.larkoffice.com/docx/source-report-doc",
        document_token="source-report-doc",
        internal_report_url=f"http://localhost:8000/jobs/{source_job_id}/report",
    )
    routes.job_repository.create_xiaod_execution_run(
        run_id=run_id,
        tenant_key="tenant-progress",
        chat_id="oc_progress",
        open_id=f"ou_source_report_count_{unique}",
        command_id=command_id,
        batch_id=batch_id,
        action_kind="spreadsheet_rerun",
        status="writeback_decision_pending",
        summary={
            "command_id": command_id,
            "message_id": "om_progress",
            "chat_id": "oc_progress",
            "open_id": f"ou_source_report_count_{unique}",
            "batch_id": batch_id,
            "job_ids": [source_job_id, probe_job_id],
            "row_results": [
                {
                    "row_id": "2",
                    "case_id": "handwrite233",
                    "job_id": source_job_id,
                    "job_status": "completed",
                    "report_url": f"/api/artifacts/files/{source_job_id}_report.md",
                    "writeback_status": "sync_decision_pending",
                    "source_mapped": True,
                    "spreadsheet_id": "spreadsheet-progress",
                    "sheet_id": "sheet-progress",
                },
                {
                    "row_id": "",
                    "case_id": "handwrite233__hypothesis_probe__probe_h1",
                    "job_id": probe_job_id,
                    "job_status": "completed",
                    "report_url": "",
                    "writeback_status": "not_ready",
                    "source_mapped": False,
                    "spreadsheet_id": "",
                    "sheet_id": "",
                },
            ],
            "report_requested": True,
            "report_count": 1,
            "writeback_requested": True,
            "writeback_decision_status": "pending",
            "auto_closure_reports": [
                {
                    "job_id": source_job_id,
                    "case_id": "handwrite233",
                    "report_artifact_url": f"/api/artifacts/files/{source_job_id}_report.md",
                    "writeback_status": "sync_decision_pending",
                }
            ],
        },
    )

    notification = _xiaod_run_progress_notification(run_id)

    assert notification.stage == "writeback_decision_pending"
    assert "已生成 1 份报告；同步前不会写回飞书表格。" in notification.payload.markdown
    assert "1/1 行有 source mapping" in notification.payload.markdown
    assert "https://bytedance.larkoffice.com/docx/source-report-doc" in (
        notification.payload.markdown
    )
    assert probe_job_id not in notification.payload.markdown
    report_actions = notification.payload.content["elements"][3]["actions"]
    assert report_actions[0]["text"]["content"] == "打开最终报告"
    assert report_actions[0]["url"] == "https://bytedance.larkoffice.com/docx/source-report-doc"
    decision_actions = notification.payload.content["elements"][6]["actions"]
    assert [action["text"]["content"] for action in decision_actions] == [
        "同步到飞书表格",
        "不同步",
    ]


def test_lark_bot_spreadsheet_rerun_writeback_decision_can_skip_without_writing(
    monkeypatch,
) -> None:
    client = TestClient(app)
    writeback_client = RecordingWritebackClient()
    monkeypatch.setattr(routes, "spreadsheet_writeback_client", writeback_client, raising=False)
    command_id, run_id, job_id, actor, chat_id = (
        _create_spreadsheet_rerun_writeback_decision_fixture()
    )

    response = client.post(
        "/api/lark/bot/events",
        json=_spreadsheet_rerun_writeback_action_payload(
            action="skip_spreadsheet_rerun_writeback",
            command_id=command_id,
            actor=actor,
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["handled"] is True
    assert body["writeback_decision"]["status"] == "skipped"
    assert body["writeback_decision"]["row_results"][0]["writeback_status"] == "skipped"
    assert body["writeback_decision"]["row_results"][0]["error_message"] == "user_skipped_sync"
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
    assert audit.error_message == "user_skipped_sync"
    run = next(
        item
        for item in routes.job_repository.list_xiaod_execution_runs(limit=20)
        if item.run_id == run_id
    )
    assert run.status == "completed"
    assert run.completed_at
    assert run.summary["writeback_decision_status"] == "skipped"
    completed_summary = run.summary["completed_summary"]
    assert completed_summary["status"] == "completed"
    assert completed_summary["writeback_decision_status"] == "skipped"
    assert completed_summary["writeback_status_counts"] == {"skipped": 1}
    audits = routes.job_repository.list_xiaod_command_audits(command_id=command_id)
    assert "xiaod_run_completed" in {audit.event_kind for audit in audits}


def test_lark_bot_spreadsheet_rerun_writeback_decision_can_sync_mapped_rows(
    monkeypatch,
) -> None:
    client = TestClient(app)
    writeback_client = RecordingWritebackClient()
    monkeypatch.setattr(routes, "spreadsheet_writeback_client", writeback_client, raising=False)
    command_id, run_id, job_id, actor, _chat_id = (
        _create_spreadsheet_rerun_writeback_decision_fixture()
    )

    response = client.post(
        "/api/lark/bot/events",
        json=_spreadsheet_rerun_writeback_action_payload(
            action="sync_spreadsheet_rerun_writeback",
            command_id=command_id,
            actor=actor,
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["handled"] is True
    assert body["writeback_decision"]["status"] == "synced"
    assert body["writeback_decision"]["row_results"][0]["writeback_status"] == "succeeded"
    assert writeback_client.update_count == 1
    assert writeback_client.spreadsheet_id == "spreadsheet-sync"
    assert writeback_client.sheet_id == "sheet-sync"
    assert writeback_client.row_id == "row-1"
    audit = routes.job_repository.get_spreadsheet_writeback_audit(job_id)
    assert audit is not None
    assert audit.status == "succeeded"
    run = next(
        item
        for item in routes.job_repository.list_xiaod_execution_runs(limit=20)
        if item.run_id == run_id
    )
    assert run.status == "completed"
    assert run.summary["writeback_decision_status"] == "synced"


def test_lark_bot_spreadsheet_rerun_writeback_decision_defaults_to_no_sync(
    monkeypatch,
) -> None:
    client = TestClient(app)
    writeback_client = RecordingWritebackClient()
    monkeypatch.setattr(routes, "spreadsheet_writeback_client", writeback_client, raising=False)
    command_id, run_id, job_id, actor, chat_id = (
        _create_spreadsheet_rerun_writeback_decision_fixture()
    )

    response = client.post(
        "/api/lark/bot/events",
        json=_spreadsheet_rerun_writeback_action_payload(
            action="default_skip_spreadsheet_rerun_writeback",
            command_id=command_id,
            actor=actor,
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["handled"] is True
    assert body["writeback_decision"]["status"] == "default_skipped"
    assert body["writeback_decision"]["row_results"][0]["writeback_status"] == "skipped"
    assert (
        body["writeback_decision"]["row_results"][0]["error_message"]
        == "writeback decision timed out"
    )
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
    assert run.completed_at
    assert run.summary["writeback_decision_status"] == "default_skipped"
    completed_summary = run.summary["completed_summary"]
    assert completed_summary["status"] == "completed"
    assert completed_summary["writeback_decision_status"] == "default_skipped"
    assert completed_summary["default_skip"] is True
    audits = routes.job_repository.list_xiaod_command_audits(command_id=command_id)
    completed_audit = next(audit for audit in audits if audit.event_kind == "xiaod_run_completed")
    assert completed_audit.payload["writeback_decision_status"] == "default_skipped"


def test_lark_bot_spreadsheet_rerun_confirm_uses_preflight_valid_rows(monkeypatch) -> None:
    client = TestClient(app)
    sync_client = StaticSpreadsheetClient(
        [
            SpreadsheetSourceRow(
                row_id="2",
                values=_valid_spreadsheet_row_values("card-rerun-valid-only"),
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
    monkeypatch.setattr(
        routes,
        "job_service",
        DebugJobService(
            routes.job_repository,
            model_provider=lambda case: FakeModelAdapter(outputs=[case.predictions[0].raw_output]),
        ),
        raising=False,
    )

    response = client.post(
        "/api/lark/bot/xiaod/turns/handle",
        json={
            "text": "处理这个表前3行：https://example.larkoffice.com/sheets/abc?sheet=def",
            "message_id": "om_sheet_valid_rows_only",
            "open_id": "ou_sheet_valid_rows_only",
            "chat_id": "oc_sheet_valid_rows_only",
        },
    )

    assert response.status_code == 200
    command_id = response.json()["reply"]["content"]["elements"][1]["actions"][0]["value"][
        "command_id"
    ]

    confirm_response = client.post(
        "/api/lark/bot/events",
        json={
            "header": {"event_type": "card.action.trigger"},
            "event": {
                "operator": {"open_id": "ou_card_reviewer"},
                "action": {
                    "value": {
                        "action": "confirm_pending_command",
                        "command_id": command_id,
                    }
                },
            },
        },
    )

    assert confirm_response.status_code == 200
    body = confirm_response.json()
    assert body["pending_command"]["status"] == "confirmed"
    completed = _wait_pending_command_status(command_id, "executed")
    result = completed.execution_result["spreadsheet_rerun"]
    preflight = completed.execution_result["preflight"]
    assert preflight["requested_row_ids"] == ["2", "3", "4"]
    assert preflight["valid_row_ids"] == ["2"]
    assert preflight["missing_row_ids"] == ["4"]
    assert result["imported_case_ids"] == ["card-rerun-valid-only"]
    assert result["rejected_rows"] == []
    assert [job["case_id"] for job in result["jobs"]] == ["card-rerun-valid-only"]
    assert body["reply"]["message_type"] == "interactive"
    run_panel_text = body["reply"]["content"]["elements"][0]["content"]
    assert "表格批处理已确认，后台执行中" in run_panel_text
    assert "有效行：`2`" in run_panel_text
    assert "缺失行：`4`" in run_panel_text


def test_lark_bot_spreadsheet_rerun_confirm_fails_when_preflight_has_no_valid_rows(
    monkeypatch,
) -> None:
    client = TestClient(app)
    sync_client = StaticSpreadsheetClient(
        [
            SpreadsheetSourceRow(
                row_id="2",
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
            "text": "处理这个表前1行：https://example.larkoffice.com/sheets/abc?sheet=def",
            "message_id": "om_sheet_no_valid_rows",
            "open_id": "ou_sheet_no_valid_rows",
            "chat_id": "oc_sheet_no_valid_rows",
        },
    )

    assert response.status_code == 200
    command_id = response.json()["reply"]["content"]["elements"][1]["actions"][0]["value"][
        "command_id"
    ]

    confirm_response = client.post(
        f"/api/lark/bot/commands/pending/{command_id}/confirm",
        json={"actor": "ou_card_reviewer"},
    )

    assert confirm_response.status_code == 200
    assert confirm_response.json()["status"] == "confirmed"
    command = _wait_pending_command_status(command_id, "failed")
    commands = client.get("/api/lark/bot/commands/pending").json()["commands"]
    command_payload = next(item for item in commands if item["command_id"] == command_id)
    assert command_payload["status"] == "failed"
    assert command.error_message == "No valid spreadsheet rows after preflight."
    assert routes.job_repository.list_jobs() == []


def _xiaod_run_progress_notification(run_id: str):
    notifications = routes.list_xiaod_run_progress_notifications(limit=20)
    return next(
        item for item in notifications if item.payload.command_id == f"xiaod-run-progress-{run_id}"
    )
