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
