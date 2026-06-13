from fastapi.testclient import TestClient

from debug_agent.main import app


def test_job_report_api_returns_report_from_persisted_job_evidence() -> None:
    client = TestClient(app)
    submit_response = client.post("/cases/handwrite233/debug-jobs?auto_run=true&baseline_trials=5")
    assert submit_response.status_code == 202
    job_id = submit_response.json()["job_id"]

    response = client.get(f"/jobs/{job_id}/report")

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == job_id
    assert body["case_id"] == "handwrite233"
    assert body["experiment_summary"]["total_trials"] == 10
    assert len(body["experiment_summary"]["evidence_ids"]) == 10
    assert body["root_cause"]["label"] == "answer_mismatch"
    assert body["root_cause"]["confidence"] == "high"
    assert body["observed_failure"]["type"] == "answer_mismatch"
    assert body["observed_failure"]["affected_box_ids"]


def test_job_report_api_returns_404_for_missing_job() -> None:
    client = TestClient(app)

    response = client.get("/jobs/missing-job/report")

    assert response.status_code == 404
