from fastapi.testclient import TestClient

from debug_agent.main import app


def test_submit_debug_job_returns_accepted_then_worker_completes_it() -> None:
    client = TestClient(app)

    submit_response = client.post("/cases/handwrite233/debug-jobs")

    assert submit_response.status_code == 202
    submitted = submit_response.json()
    assert submitted["case_id"] == "handwrite233"
    assert submitted["status"] == "created"

    status_response = client.get(f"/jobs/{submitted['job_id']}")
    assert status_response.json()["status"] == "created"

    worker_response = client.post("/jobs/run-next")

    assert worker_response.status_code == 200
    assert worker_response.json()["job_id"] == submitted["job_id"]
    assert client.get(f"/jobs/{submitted['job_id']}").json()["status"] == "completed"


def test_submit_debug_job_with_auto_run_completes_without_worker_tick() -> None:
    client = TestClient(app)

    submit_response = client.post("/cases/handwrite233/debug-jobs?auto_run=true")

    assert submit_response.status_code == 202
    submitted = submit_response.json()
    assert submitted["case_id"] == "handwrite233"
    assert submitted["status"] == "created"
    status_response = client.get(f"/jobs/{submitted['job_id']}")
    assert status_response.json()["status"] == "completed"
    assert len(status_response.json()["evidence_ids"]) == 6


def test_submit_debug_job_accepts_baseline_trial_count_for_five_run_replay() -> None:
    client = TestClient(app)

    submit_response = client.post("/cases/handwrite233/debug-jobs?auto_run=true&baseline_trials=5")

    assert submit_response.status_code == 202
    submitted = submit_response.json()
    status_response = client.get(f"/jobs/{submitted['job_id']}")
    body = status_response.json()
    assert body["status"] == "completed"
    assert len([evidence_id for evidence_id in body["evidence_ids"] if ":baseline_replay:" in evidence_id]) == 5
    assert len(body["evidence_ids"]) == 10


def test_submit_debug_job_rejects_invalid_baseline_trial_count() -> None:
    client = TestClient(app)

    response = client.post("/cases/handwrite233/debug-jobs?baseline_trials=6")

    assert response.status_code == 422
