import json

from fastapi.testclient import TestClient

from debug_agent.api import routes
from debug_agent.jobs.service import DebugJobService
from debug_agent.main import app
from debug_agent.models.fake import FakeModelAdapter
from debug_agent.spreadsheets.lark import LarkCliError
from debug_agent.spreadsheets.sync import SpreadsheetSourceRow


class StaticSpreadsheetClient:
    def __init__(self, rows: list[SpreadsheetSourceRow]) -> None:
        self.rows = rows
        self.requested_spreadsheet_id = ""
        self.requested_sheet_id = ""

    def list_rows(self, spreadsheet_id: str, sheet_id: str) -> list[SpreadsheetSourceRow]:
        self.requested_spreadsheet_id = spreadsheet_id
        self.requested_sheet_id = sheet_id
        return self.rows


class RecordingSpreadsheetClient(StaticSpreadsheetClient):
    def __init__(self, rows: list[SpreadsheetSourceRow]) -> None:
        super().__init__(rows)
        self.updated_rows: list[tuple[str, str, str, dict[str, str]]] = []

    def update_row(
        self, spreadsheet_id: str, sheet_id: str, row_id: str, fields: dict[str, str]
    ) -> None:
        self.updated_rows.append((spreadsheet_id, sheet_id, row_id, fields))


class FailingSpreadsheetClient:
    def list_rows(self, spreadsheet_id: str, sheet_id: str) -> list[SpreadsheetSourceRow]:
        raise LarkCliError("missing lark spreadsheet permission")


class MissingCliSpreadsheetClient:
    def list_rows(self, spreadsheet_id: str, sheet_id: str) -> list[SpreadsheetSourceRow]:
        raise FileNotFoundError("lark-cli")


class RequestConfiguredSpreadsheetClient(StaticSpreadsheetClient):
    def __init__(self, transport) -> None:
        del transport
        super().__init__(
            [
                SpreadsheetSourceRow(
                    row_id="row-from-request",
                    values={
                        "case_id": "synced-from-request",
                        "image_uri": "file://synced-from-request.png",
                        "prompt": "Read the answer",
                        "golden_answer_json": {"answers": [{"box_id": 1, "student_answer": "42"}]},
                        "scoring_standard": "exact match",
                        "predictions_json": [
                            {"trial": 1, "raw_output": '{"answers":[]}', "score": 0}
                        ],
                        "avg_score": 0.0,
                    },
                )
            ]
        )


def test_spreadsheet_sync_api_imports_rows_creates_jobs_and_saves_mapping(monkeypatch) -> None:
    client = TestClient(app)
    golden_answer = {"answers": [{"box_id": 1, "student_answer": "42"}]}
    sync_client = StaticSpreadsheetClient(
        [
            SpreadsheetSourceRow(
                row_id="row-api-1",
                values={
                    "case_id": "synced-api-case-1",
                    "image_uri": "file://synced-api-case-1.png",
                    "prompt": "Read the answer",
                    "golden_answer_json": golden_answer,
                    "scoring_standard": "exact match",
                    "predictions_json": [
                        {"trial": 1, "raw_output": json.dumps(golden_answer), "score": 1},
                    ],
                    "avg_score": 1.0,
                },
            )
        ]
    )
    monkeypatch.setattr(routes, "spreadsheet_sync_client", sync_client, raising=False)

    response = client.post(
        "/spreadsheets/sync",
        json={
            "spreadsheet_id": "spreadsheet-api-1",
            "sheet_id": "sheet-api-1",
            "create_jobs": True,
            "baseline_trials": 5,
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert sync_client.requested_spreadsheet_id == "spreadsheet-api-1"
    assert sync_client.requested_sheet_id == "sheet-api-1"
    assert body["imported_case_ids"] == ["synced-api-case-1"]
    assert body["imported_rows"][0]["sheet_row_id"] == "row-api-1"
    assert body["rejected_rows"] == []
    assert len(body["jobs"]) == 1
    job_id = body["jobs"][0]["job_id"]
    mapping = routes.job_repository.get_spreadsheet_row_mapping_by_job_id(job_id)
    assert mapping is not None
    assert mapping.spreadsheet_id == "spreadsheet-api-1"
    assert mapping.sheet_id == "sheet-api-1"
    assert mapping.row_id == "row-api-1"
    assert mapping.case_id == "synced-api-case-1"


def test_spreadsheet_rerun_api_filters_rows_and_runs_jobs(monkeypatch) -> None:
    client = TestClient(app)
    sync_client = StaticSpreadsheetClient(
        [
            SpreadsheetSourceRow(
                row_id="2",
                values={
                    "case_id": "rerun-api-case-1",
                    "image_uri": "file://rerun-api-case-1.png",
                    "prompt": "Read the answer",
                    "reference_answer_json": {
                        "video_action_segments": [
                            {
                                "subtask_label": "The right arm picks up the crab clamp and adjusts its position",
                                "start_s": 0.1,
                                "end_s": 23.1,
                            }
                        ]
                    },
                    "scoring_ops_json": [
                        {
                            "op_name": "check_timestamp",
                            "format": "float",
                            "in_key": "video_action_segments",
                            "grids": [
                                {
                                    "start_s": {"type": "range", "min": 0.0, "max": 1.0},
                                    "end_s": {"type": "range", "min": 22.0, "max": 24.0},
                                }
                            ],
                        }
                    ],
                    "predictions_json": [
                        {
                            "trial": 1,
                            "raw_output": (
                                '{"video_action_segments":[{"subtask_label":"The right arm picks up the crab clamp and adjusts its position",'
                                '"start_s":0.0,"end_s":34.0}]}'
                            ),
                            "score": 0,
                        }
                    ],
                    "avg_score": 0.0,
                },
            ),
            SpreadsheetSourceRow(
                row_id="3",
                values={
                    "case_id": "rerun-api-case-2",
                    "image_uri": "file://rerun-api-case-2.png",
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
        "/spreadsheets/rerun",
        json={
            "spreadsheet_id": "spreadsheet-api-rerun",
            "sheet_id": "sheet-api-rerun",
            "row_ids": ["2"],
            "baseline_trials": 1,
            "auto_run": True,
            "auto_closure": True,
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["imported_case_ids"] == ["rerun-api-case-1"]
    assert body["imported_rows"] == [{"sheet_row_id": "2", "case_id": "rerun-api-case-1"}]
    assert body["skipped_row_ids"] == ["3"]
    assert body["jobs"][0]["status"] == "completed"
    assert body["auto_closure_reports"][0]["job_id"] == body["jobs"][0]["job_id"]
    assert body["auto_closure_reports"][0]["report_artifact_url"].endswith(
        "_auto_closure_report.md"
    )
    assert body["auto_closure_reports"][0]["writeback_status"] == "not_requested"


def test_spreadsheet_rerun_auto_closure_writeback_waits_for_sync_decision(
    monkeypatch,
) -> None:
    client = TestClient(app)
    spreadsheet_client = RecordingSpreadsheetClient(
        [
            SpreadsheetSourceRow(
                row_id="2",
                values=_video_rerun_row("rerun-api-writeback-case-1"),
            )
        ]
    )
    monkeypatch.setattr(routes, "spreadsheet_sync_client", spreadsheet_client, raising=False)
    monkeypatch.setattr(routes, "spreadsheet_writeback_client", spreadsheet_client, raising=False)
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
        "/spreadsheets/rerun",
        json={
            "spreadsheet_id": "spreadsheet-api-rerun-writeback",
            "sheet_id": "sheet-api-rerun-writeback",
            "row_ids": ["2"],
            "baseline_trials": 1,
            "auto_run": True,
            "auto_closure": True,
            "writeback": True,
        },
    )

    assert response.status_code == 202
    body = response.json()
    job_id = body["jobs"][0]["job_id"]
    report_url = body["auto_closure_reports"][0]["report_artifact_url"]
    assert body["auto_closure_reports"][0]["writeback_status"] == "sync_decision_pending"
    assert spreadsheet_client.updated_rows == []
    assert routes.job_repository.get_spreadsheet_writeback_audit(job_id) is None

    stages_response = client.get(f"/jobs/{job_id}/run-stages")
    assert stages_response.status_code == 200
    stages = stages_response.json()["stages"]
    assert [stage["stage"] for stage in stages] == [
        "baseline",
        "hypothesis",
        "targeted",
        "verification",
        "attribution",
        "writeback",
        "auto_closure",
        "debug_loop",
    ]
    assert stages[0]["status"] == "completed"
    stage_by_name = {stage["stage"]: stage for stage in stages}
    assert stage_by_name["writeback"]["status"] == "pending"
    assert stage_by_name["writeback"]["output"]["report_url"] == report_url
    assert stage_by_name["writeback"]["output"]["writeback_status"] == "sync_decision_pending"
    assert stage_by_name["auto_closure"]["status"] == "completed"
    assert stage_by_name["debug_loop"]["status"] in {"waiting", "completed"}

    ledger_response = client.get(f"/jobs/{job_id}/evidence-ledger")
    assert ledger_response.status_code == 200
    ledger_records = ledger_response.json()["records"]
    assert ledger_records[0]["raw_output"].startswith('{"video_action_segments"')
    assert ledger_records[0]["judge_version"] == "debug-agent-judge-v1"
    assert isinstance(ledger_records[0]["score_delta"]["score"], int)
    assert "prompt_length" in ledger_records[0]["prompt"]

    report_response = client.get(report_url)
    assert report_response.status_code == 200
    assert "当前自动写回状态为 `sync_decision_pending`" in report_response.text
    assert "当前自动写回状态为 `succeeded`" not in report_response.text
    assert "skipped_no_client" not in report_response.text


def test_spreadsheet_rerun_auto_closure_can_opt_in_controlled_probe_submission(
    monkeypatch,
) -> None:
    client = TestClient(app)
    spreadsheet_client = RecordingSpreadsheetClient(
        [
            SpreadsheetSourceRow(
                row_id="2",
                values=_video_rerun_row("rerun-api-controlled-probe-case-1"),
            )
        ]
    )
    monkeypatch.setattr(routes, "spreadsheet_sync_client", spreadsheet_client, raising=False)
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
        "/spreadsheets/rerun",
        json={
            "spreadsheet_id": "spreadsheet-api-rerun-controlled-probe",
            "sheet_id": "sheet-api-rerun-controlled-probe",
            "row_ids": ["2"],
            "baseline_trials": 1,
            "auto_run": True,
            "auto_closure": True,
            "submit_controlled_probes": True,
        },
    )

    assert response.status_code == 202
    report = response.json()["auto_closure_reports"][0]
    submitted_probe_results = [
        item for item in report["closure"]["probe_results"] if item["probe_job_id"]
    ]
    assert submitted_probe_results
    probe_job = routes.job_repository.get_job(submitted_probe_results[0]["probe_job_id"])
    assert probe_job is not None
    assert probe_job.status == "created"
    assert routes.job_repository.list_evidence(probe_job.job_id) == []
    assert report["writeback_status"] == "not_requested"


def test_spreadsheet_rerun_async_path_records_controlled_probe_opt_in(
    monkeypatch,
) -> None:
    client = TestClient(app)
    spreadsheet_client = RecordingSpreadsheetClient(
        [
            SpreadsheetSourceRow(
                row_id="2",
                values=_video_rerun_row("rerun-api-async-controlled-probe-case-1"),
            )
        ]
    )
    monkeypatch.setattr(routes, "spreadsheet_sync_client", spreadsheet_client, raising=False)

    response = client.post(
        "/spreadsheets/rerun",
        json={
            "spreadsheet_id": "spreadsheet-api-rerun-async-controlled-probe",
            "sheet_id": "sheet-api-rerun-async-controlled-probe",
            "row_ids": ["2"],
            "baseline_trials": 1,
            "auto_run": False,
            "auto_closure": True,
            "submit_controlled_probes": True,
            "writeback": False,
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["jobs"][0]["status"] == "created"
    assert body["auto_closure_reports"] == []
    batch_id = body["batch"]["batch"]["batch_id"]
    batch = routes.job_repository.get_batch(batch_id)
    assert batch is not None
    assert batch.retry_policy["auto_run"] is False
    assert batch.retry_policy["auto_closure"] is True
    assert batch.retry_policy["submit_controlled_probes"] is True
    assert batch.retry_policy["writeback"] is False


def test_spreadsheet_sync_api_returns_503_when_client_is_not_configured(monkeypatch) -> None:
    client = TestClient(app)
    monkeypatch.setattr(routes, "spreadsheet_sync_client", None, raising=False)

    response = client.post(
        "/spreadsheets/sync",
        json={
            "spreadsheet_id": "spreadsheet-api-1",
            "sheet_id": "sheet-api-1",
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Spreadsheet sync client is not configured"


def test_spreadsheet_sync_api_configures_lark_client_from_request_url(monkeypatch) -> None:
    client = TestClient(app)
    monkeypatch.setattr(routes, "spreadsheet_sync_client", None, raising=False)
    monkeypatch.setattr(routes, "spreadsheet_writeback_client", None, raising=False)
    monkeypatch.setattr(routes, "LarkSpreadsheetClient", RequestConfiguredSpreadsheetClient)

    response = client.post(
        "/spreadsheets/sync",
        json={
            "spreadsheet_url": "https://example.larkoffice.com/sheets/spreadsheet-from-url?sheet=sheet-from-url",
            "spreadsheet_id": "spreadsheet-from-url",
            "sheet_id": "sheet-from-url",
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["imported_case_ids"] == ["synced-from-request"]
    assert routes.lark_spreadsheet_settings.reference is not None
    assert routes.lark_spreadsheet_settings.reference.spreadsheet_id == "spreadsheet-from-url"
    assert routes.lark_spreadsheet_settings.reference.sheet_id == "sheet-from-url"


def test_spreadsheet_sync_api_maps_lark_transport_failures(monkeypatch) -> None:
    client = TestClient(app)
    monkeypatch.setattr(
        routes, "spreadsheet_sync_client", FailingSpreadsheetClient(), raising=False
    )

    response = client.post(
        "/spreadsheets/sync",
        json={
            "spreadsheet_id": "spreadsheet-api-1",
            "sheet_id": "sheet-api-1",
        },
    )

    assert response.status_code == 502
    assert (
        response.json()["detail"]
        == "Lark spreadsheet operation failed: missing lark spreadsheet permission"
    )


def test_spreadsheet_sync_api_maps_missing_lark_cli_failures(monkeypatch) -> None:
    client = TestClient(app)
    monkeypatch.setattr(
        routes, "spreadsheet_sync_client", MissingCliSpreadsheetClient(), raising=False
    )

    response = client.post(
        "/spreadsheets/sync",
        json={
            "spreadsheet_id": "spreadsheet-api-1",
            "sheet_id": "sheet-api-1",
        },
    )

    assert response.status_code == 502
    assert "lark-cli" in response.json()["detail"]


def _video_rerun_row(case_id: str) -> dict[str, object]:
    return {
        "case_id": case_id,
        "image_uri": f"https://media.example/{case_id}.mp4",
        "prompt": "Read the answer",
        "reference_answer_json": {
            "video_action_segments": [
                {
                    "subtask_label": "The right arm picks up the crab clamp and adjusts its position",
                    "start_s": 0.1,
                    "end_s": 23.1,
                }
            ]
        },
        "scoring_ops_json": [
            {
                "op_name": "check_timestamp",
                "format": "float",
                "in_key": "video_action_segments",
                "grids": [
                    {
                        "start_s": {"type": "range", "min": 0.0, "max": 1.0},
                        "end_s": {"type": "range", "min": 22.0, "max": 24.0},
                    }
                ],
            }
        ],
        "predictions_json": [
            {
                "trial": 1,
                "raw_output": (
                    '{"video_action_segments":[{"subtask_label":"The right arm picks up the crab clamp and adjusts its position",'
                    '"start_s":0.0,"end_s":34.0}]}'
                ),
                "score": 0,
            }
        ],
        "avg_score": 0.0,
    }
