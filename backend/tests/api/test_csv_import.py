import csv
import io
import json

from fastapi.testclient import TestClient

from debug_agent.main import app


def csv_text() -> str:
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
            "debug_status",
            "root_cause",
        ],
    )
    writer.writeheader()
    writer.writerow(
        {
            "case_id": "csv-import-1",
            "image_uri": "file://image.png",
            "prompt": "Read the answer",
            "golden_answer_json": json.dumps(golden_answer),
            "scoring_standard": "exact match",
            "predictions_json": json.dumps(predictions),
            "avg_score": "1.0",
            "debug_status": "pending",
            "root_cause": "",
        }
    )
    return output.getvalue()


def test_csv_import_persists_cases_and_creates_jobs() -> None:
    client = TestClient(app)

    response = client.post("/imports/csv", json={"csv_text": csv_text(), "create_jobs": True})

    assert response.status_code == 202
    body = response.json()
    assert body["imported_case_ids"] == ["csv-import-1"]
    assert body["rejected_rows"] == []
    assert len(body["jobs"]) == 1
    assert body["jobs"][0]["case_id"] == "csv-import-1"

    job_id = body["jobs"][0]["job_id"]
    worker_response = client.post("/jobs/run-next")
    assert worker_response.status_code == 200
    assert worker_response.json()["job_id"] == job_id
    status = client.get(f"/jobs/{job_id}").json()
    assert status["status"] == "completed"
    assert len(status["evidence_ids"]) == 6
