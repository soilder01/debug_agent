import time
from collections.abc import Callable

from fastapi.testclient import TestClient

from debug_agent.main import app


def wait_until(predicate: Callable[[], bool], timeout_seconds: float = 1.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("condition was not met before timeout")


def test_worker_status_endpoint_reports_lifecycle_state() -> None:
    client = TestClient(app)

    response = client.get("/worker/status")

    assert response.status_code == 200
    assert response.json() == {
        "running": False,
        "processed_count": 0,
        "error_count": 0,
        "last_error": None,
    }


def test_worker_start_is_idempotent_and_stop_updates_status() -> None:
    client = TestClient(app)

    first_start = client.post("/worker/start")
    second_start = client.post("/worker/start")
    stop_response = client.post("/worker/stop")
    status_response = client.get("/worker/status")

    assert first_start.status_code == 202
    assert first_start.json()["running"] is True
    assert second_start.status_code == 202
    assert second_start.json()["running"] is True
    assert stop_response.status_code == 200
    assert stop_response.json()["running"] is False
    assert status_response.json()["running"] is False


def test_worker_start_consumes_submitted_debug_job() -> None:
    client = TestClient(app)
    submit_response = client.post("/cases/handwrite233/debug-jobs")
    job_id = submit_response.json()["job_id"]

    start_response = client.post("/worker/start")
    wait_until(
        lambda: (status := client.get(f"/jobs/{job_id}").json())["status"] == "completed"
        and len(status["evidence_ids"]) == 6
    )
    stop_response = client.post("/worker/stop")

    status_response = client.get(f"/jobs/{job_id}")
    worker_status = client.get("/worker/status").json()
    assert start_response.status_code == 202
    assert stop_response.status_code == 200
    assert status_response.json()["status"] == "completed"
    assert status_response.json()["attempt_count"] == 1
    assert len(status_response.json()["evidence_ids"]) == 6
    assert worker_status["processed_count"] >= 1
