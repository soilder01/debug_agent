from fastapi.testclient import TestClient

from debug_agent.api import routes
from debug_agent.main import app


def test_recommended_action_status_api_updates_and_lists_status() -> None:
    client = TestClient(app)
    submit_response = client.post("/cases/handwrite233/debug-jobs?auto_run=true&baseline_trials=1")
    assert submit_response.status_code == 202
    job_id = submit_response.json()["job_id"]

    response = client.patch(
        f"/jobs/{job_id}/recommended-actions/0/status",
        json={"status": "accepted", "actor": "qa-reviewer", "note": "prompt fix approved"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == job_id
    assert body["action_index"] == 0
    assert body["status"] == "accepted"
    assert body["actor"] == "qa-reviewer"
    assert body["note"] == "prompt fix approved"
    assert body["updated_at"]
    assert routes.job_repository.list_recommended_action_statuses(job_id)[0].status == "accepted"

    list_response = client.get(f"/jobs/{job_id}/recommended-actions/statuses")
    assert list_response.status_code == 200
    assert list_response.json()["statuses"] == [body]


def test_recommended_action_status_api_returns_404_for_missing_job() -> None:
    client = TestClient(app)

    response = client.patch(
        "/jobs/missing-job/recommended-actions/0/status",
        json={"status": "accepted", "actor": "qa-reviewer", "note": ""},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Debug job not found: missing-job"
