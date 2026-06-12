import time
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from debug_agent.api import routes
from debug_agent.jobs.service import DebugJobService
from debug_agent.main import app
from debug_agent.storage.database import create_sqlite_memory_session_factory
from debug_agent.storage.models import Base
from debug_agent.storage.repository import DebugJobRepository


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
        "completion_hook_enabled": False,
        "report_base_url": "http://localhost:8000",
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


class RecordingWritebackClient:
    def __init__(self) -> None:
        self.row_id = ""
        self.fields: dict[str, str] = {}

    def update_row(self, spreadsheet_id: str, sheet_id: str, row_id: str, fields: dict[str, str]) -> None:
        self.row_id = row_id
        self.fields = fields


@pytest.mark.asyncio
async def test_runtime_worker_writes_report_back_after_completed_mapped_job() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    service = DebugJobService(repository)
    submitted = service.submit_case_debug("handwrite233", baseline_trials=1)
    repository.save_spreadsheet_row_mapping(
        spreadsheet_id="spreadsheet-1",
        sheet_id="sheet-1",
        row_id="7",
        case_id=submitted.case_id,
        job_id=submitted.job_id,
    )
    writeback_client = RecordingWritebackClient()
    worker = routes.build_job_worker(
        service=service,
        repository=repository,
        writeback_client=writeback_client,
        report_base_url="https://debug-agent.local",
    )

    assert worker.status().completion_hook_enabled is True

    await worker.tick()

    assert writeback_client.row_id == "7"
    assert writeback_client.fields["分析报告链接"] == f"https://debug-agent.local/jobs/{submitted.job_id}/report"
    assert writeback_client.fields["错误原因"]
    assert worker.status().error_count == 0
