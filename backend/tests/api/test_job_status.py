from fastapi.testclient import TestClient

from debug_agent.main import app


def test_debug_case_returns_queryable_completed_job_status() -> None:
    client = TestClient(app)

    debug_response = client.post("/cases/handwrite233/debug")

    assert debug_response.status_code == 200
    job_id = debug_response.json()["job_id"]
    response = client.get(f"/jobs/{job_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == job_id
    assert body["case_id"] == "handwrite233"
    assert body["status"] == "completed"
    assert body["attempt_count"] == 0
    assert body["error_message"] is None
    assert len(body["evidence_ids"]) == 6
    assert body["evidence_error_counts"] == {
        "total_evidence": 6,
        "failed_judgements": 6,
        "response_parse_errors": 0,
        "model_call_errors": 0,
    }
