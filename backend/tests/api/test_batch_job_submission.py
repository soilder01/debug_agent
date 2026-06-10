from fastapi.testclient import TestClient

from debug_agent.main import app


def test_batch_debug_job_submission_creates_jobs_and_reports_rejections() -> None:
    client = TestClient(app)

    response = client.post(
        "/debug-jobs/batch",
        json={"case_ids": ["handwrite233", "missing-case"]},
    )

    assert response.status_code == 202
    body = response.json()
    assert len(body["jobs"]) == 1
    assert body["jobs"][0]["case_id"] == "handwrite233"
    assert body["rejected_case_ids"] == ["missing-case"]

    job_id = body["jobs"][0]["job_id"]
    status_response = client.get(f"/jobs/{job_id}")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "created"
