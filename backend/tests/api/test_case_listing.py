import csv
import io
import json

from fastapi.testclient import TestClient

from debug_agent.cases.fixtures import load_fixture_case
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
            "case_id": "case-list-csv-1",
            "image_uri": "file://case-list.png",
            "prompt": "Read the answer",
            "golden_answer_json": json.dumps(golden_answer),
            "scoring_standard": "exact match",
            "predictions_json": json.dumps(predictions),
            "avg_score": "1.0",
            "debug_status": "pending",
            "root_cause": "visual_recognition_failure",
        }
    )
    return output.getvalue()


def test_case_listing_returns_imported_case_summaries() -> None:
    client = TestClient(app)
    case_payload = load_fixture_case("handwrite233").model_dump()
    case_payload["case_id"] = "case-list-jsonl-1"
    case_payload["box_regions"] = [
        {
            "box_id": 1,
            "x": 12,
            "y": 34,
            "width": 56,
            "height": 78,
            "unit": "pixel",
            "label": "box-1",
        }
    ]
    case_json = json.dumps(case_payload)

    jsonl_response = client.post("/imports/jsonl", json={"jsonl": case_json, "create_jobs": False})
    csv_response = client.post("/imports/csv", json={"csv_text": csv_text(), "create_jobs": False})
    response = client.get("/cases")

    assert jsonl_response.status_code == 202
    assert csv_response.status_code == 202
    assert response.status_code == 200
    cases = response.json()["cases"]
    by_case_id = {case["case_id"]: case for case in cases}
    assert by_case_id["case-list-jsonl-1"]["avg_score"] == 0.0
    assert by_case_id["case-list-jsonl-1"]["box_region_count"] == 1
    assert by_case_id["case-list-csv-1"] == {
        "case_id": "case-list-csv-1",
        "image_uri": "file://case-list.png",
        "avg_score": 1.0,
        "debug_status": "pending",
        "root_cause": "visual_recognition_failure",
        "box_region_count": 0,
    }


def test_case_listing_can_filter_cases_with_regions() -> None:
    client = TestClient(app)
    case_payload = load_fixture_case("handwrite233").model_dump()
    case_payload["case_id"] = "case-list-region-filter-jsonl"
    case_payload["box_regions"] = [
        {
            "box_id": 1,
            "x": 12,
            "y": 34,
            "width": 56,
            "height": 78,
            "unit": "pixel",
            "label": "box-1",
        }
    ]
    region_response = client.post("/imports/jsonl", json={"jsonl": json.dumps(case_payload), "create_jobs": False})
    csv_response = client.post("/imports/csv", json={"csv_text": csv_text(), "create_jobs": False})

    response = client.get("/cases?has_regions=true")

    assert region_response.status_code == 202
    assert csv_response.status_code == 202
    assert response.status_code == 200
    body = response.json()
    case_ids = {case["case_id"] for case in body["cases"]}
    assert "case-list-region-filter-jsonl" in case_ids
    assert "case-list-csv-1" not in case_ids
    assert body["total_count"] > len(body["cases"])
