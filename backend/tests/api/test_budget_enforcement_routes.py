import csv
import io
import json
from uuid import uuid4

from fastapi.testclient import TestClient
from httpx import Response

from debug_agent.api import routes
from debug_agent.cases.fixtures import load_fixture_case
from debug_agent.experiments.runner import ExperimentEvidence
from debug_agent.judging.runner import JudgeResult
from debug_agent.main import app
from debug_agent.spreadsheets.sync import SpreadsheetSourceRow


class RecordingSpreadsheetClient:
    def __init__(self) -> None:
        self.list_rows_called = False

    def list_rows(self, spreadsheet_id: str, sheet_id: str) -> list[SpreadsheetSourceRow]:
        self.list_rows_called = True
        return []


def _force_usage_over_budget() -> None:
    job_id = f"budget-gate-routing-{uuid4()}"
    routes.job_repository.create_job(job_id=job_id, case_id="handwrite233")
    routes.job_repository.save_evidence(
        job_id=job_id,
        case_id="handwrite233",
        evidence=[
            ExperimentEvidence(
                evidence_id="budget-gate-routing-evidence-1",
                step_name="baseline_replay",
                trial=0,
                request_summary={"prompt_length": 1000},
                raw_output="{}",
                judge=JudgeResult(score=0, reasons=["budget fixture"]),
            )
        ],
    )
    routes.job_repository.mark_failed(job_id, "budget fixture cleanup")


def _assert_budget_gate(response: Response) -> None:
    assert response.status_code == 429
    assert response.json()["detail"] == "Usage budget exceeded; new debug jobs are disabled."


def _csv_text(case_id: str) -> str:
    golden_answer = {"answers": [{"box_id": 1, "student_answer": "42"}]}
    raw_output = json.dumps(golden_answer)
    predictions = [{"trial": 1, "raw_output": raw_output, "score": 1}]
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "case_id",
            "image_uri",
            "prompt",
            "golden_answer_json",
            "scoring_standard",
            "predictions_json",
            "avg_score",
        ],
    )
    writer.writeheader()
    writer.writerow(
        {
            "case_id": case_id,
            "image_uri": "file://image.png",
            "prompt": "Read the answer",
            "golden_answer_json": json.dumps(golden_answer),
            "scoring_standard": "exact match",
            "predictions_json": json.dumps(predictions),
            "avg_score": "1.0",
        }
    )
    return output.getvalue()


def _spreadsheet_row(case_id: str) -> dict[str, object]:
    golden_answer = {"answers": [{"box_id": 1, "student_answer": "42"}]}
    return {
        "sheet_row_id": f"row-{case_id}",
        "case_id": case_id,
        "image_uri": "file://spreadsheet.png",
        "prompt": "Read the answer",
        "golden_answer_json": golden_answer,
        "scoring_standard": "exact match",
        "predictions_json": [{"trial": 1, "raw_output": json.dumps(golden_answer), "score": 1}],
        "avg_score": 1.0,
    }


def test_budget_gate_rejects_batch_debug_job_submission() -> None:
    client = TestClient(app)
    original_settings = routes.settings
    try:
        routes.settings = original_settings.model_copy(update={"usage_budget_units": 1.0, "enforce_usage_budget": True})
        _force_usage_over_budget()

        response = client.post("/debug-jobs/batch", json={"case_ids": ["handwrite233"]})

        _assert_budget_gate(response)
    finally:
        routes.settings = original_settings


def test_budget_gate_rejects_jsonl_import_when_jobs_would_be_created() -> None:
    client = TestClient(app)
    original_settings = routes.settings
    case_json = load_fixture_case("handwrite233").model_copy(update={"case_id": "budget-jsonl-1"}).model_dump_json()
    try:
        routes.settings = original_settings.model_copy(update={"usage_budget_units": 1.0, "enforce_usage_budget": True})
        _force_usage_over_budget()

        response = client.post("/imports/jsonl", json={"jsonl": case_json, "create_jobs": True})

        _assert_budget_gate(response)
    finally:
        routes.settings = original_settings


def test_budget_gate_rejects_csv_import_when_jobs_would_be_created() -> None:
    client = TestClient(app)
    original_settings = routes.settings
    try:
        routes.settings = original_settings.model_copy(update={"usage_budget_units": 1.0, "enforce_usage_budget": True})
        _force_usage_over_budget()

        response = client.post("/imports/csv", json={"csv_text": _csv_text("budget-csv-1"), "create_jobs": True})

        _assert_budget_gate(response)
    finally:
        routes.settings = original_settings


def test_budget_gate_rejects_spreadsheet_row_import_when_jobs_would_be_created() -> None:
    client = TestClient(app)
    original_settings = routes.settings
    try:
        routes.settings = original_settings.model_copy(update={"usage_budget_units": 1.0, "enforce_usage_budget": True})
        _force_usage_over_budget()

        response = client.post(
            "/imports/spreadsheet-rows",
            json={"rows": [_spreadsheet_row("budget-spreadsheet-row-1")], "create_jobs": True},
        )

        _assert_budget_gate(response)
    finally:
        routes.settings = original_settings


def test_budget_gate_rejects_spreadsheet_sync_before_reading_rows(monkeypatch) -> None:
    client = TestClient(app)
    original_settings = routes.settings
    sync_client = RecordingSpreadsheetClient()
    monkeypatch.setattr(routes, "spreadsheet_sync_client", sync_client, raising=False)
    try:
        routes.settings = original_settings.model_copy(update={"usage_budget_units": 1.0, "enforce_usage_budget": True})
        _force_usage_over_budget()

        response = client.post(
            "/spreadsheets/sync",
            json={
                "spreadsheet_id": "spreadsheet-budget-1",
                "sheet_id": "sheet-budget-1",
                "create_jobs": True,
            },
        )

        _assert_budget_gate(response)
        assert sync_client.list_rows_called is False
    finally:
        routes.settings = original_settings
