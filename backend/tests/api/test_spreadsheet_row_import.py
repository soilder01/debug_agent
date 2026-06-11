import json

from fastapi.testclient import TestClient

from debug_agent.main import app


def test_spreadsheet_row_import_persists_rows_reports_rejections_and_creates_jobs() -> None:
    client = TestClient(app)
    golden_answer = {"answers": [{"box_id": 1, "student_answer": "42"}]}
    predictions = [{"trial": 1, "raw_output": json.dumps(golden_answer), "score": 1}]

    response = client.post(
        "/imports/spreadsheet-rows",
        json={
            "rows": [
                {
                    "sheet_row_id": "sheet-row-good",
                    "case_id": "spreadsheet-import-1",
                    "image_uri": "file://spreadsheet.png",
                    "prompt": "Read the answer",
                    "golden_answer_json": golden_answer,
                    "scoring_standard": "exact match",
                    "predictions_json": predictions,
                    "avg_score": 1.0,
                    "debug_status": "pending",
                    "root_cause": "",
                },
                {
                    "sheet_row_id": "sheet-row-bad",
                    "case_id": "spreadsheet-import-bad",
                    "image_uri": "file://bad.png",
                    "prompt": "Read the answer",
                    "golden_answer_json": "not-json",
                    "scoring_standard": "exact match",
                    "predictions_json": [],
                    "avg_score": 0.0,
                },
            ],
            "create_jobs": True,
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["imported_case_ids"] == ["spreadsheet-import-1"]
    assert body["imported_rows"] == [{"sheet_row_id": "sheet-row-good", "case_id": "spreadsheet-import-1"}]
    assert len(body["rejected_rows"]) == 1
    assert body["rejected_rows"][0]["sheet_row_id"] == "sheet-row-bad"
    assert len(body["jobs"]) == 1
    assert body["jobs"][0]["case_id"] == "spreadsheet-import-1"

    case_response = client.get("/cases/spreadsheet-import-1")
    assert case_response.status_code == 200
    assert case_response.json()["human_notes"]["debug_status"] == "pending"

    job_id = body["jobs"][0]["job_id"]
    worker_response = client.post("/jobs/run-next")
    assert worker_response.status_code == 200
    assert worker_response.json()["job_id"] == job_id
    status = client.get(f"/jobs/{job_id}").json()
    assert status["status"] == "completed"
    assert len([evidence_id for evidence_id in status["evidence_ids"] if ":baseline_replay:" in evidence_id]) == 5
    assert len(status["evidence_ids"]) == 10


def test_spreadsheet_row_import_can_skip_job_creation() -> None:
    client = TestClient(app)
    golden_answer = {"answers": [{"box_id": 2, "student_answer": "84"}]}

    response = client.post(
        "/imports/spreadsheet-rows",
        json={
            "rows": [
                {
                    "sheet_row_id": "sheet-row-no-job",
                    "case_id": "spreadsheet-import-no-job",
                    "image_uri": "file://spreadsheet-no-job.png",
                    "prompt": "Read the answer",
                    "golden_answer_json": golden_answer,
                    "scoring_standard": "exact match",
                    "predictions_json": [{"trial": 1, "raw_output": json.dumps(golden_answer), "score": 1}],
                    "avg_score": 1.0,
                }
            ],
            "create_jobs": False,
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["imported_case_ids"] == ["spreadsheet-import-no-job"]
    assert body["jobs"] == []
