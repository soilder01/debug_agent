# Worker Control API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose controlled backend API endpoints to start, stop, and inspect the async debug job worker.

**Architecture:** Instantiate one process-local `AsyncJobWorker` beside the existing global `DebugJobService` in `debug_agent.api.routes`. Add small FastAPI endpoints that delegate to `worker.start()`, `worker.stop()`, and `worker.status()`, returning the existing Pydantic status model so frontend and future operators can inspect queue consumption state.

**Tech Stack:** FastAPI, Pydantic v2, pytest, FastAPI TestClient, existing `AsyncJobWorker`.

---

## File Structure

- Modify `backend/src/debug_agent/api/routes.py`: import `AsyncJobWorker`, instantiate `job_worker`, and add `/worker/start`, `/worker/stop`, `/worker/status`.
- Create `backend/tests/api/test_worker_control.py`: verify status shape, idempotent start, stop, and actual consumption of a submitted job.
- Create `docs/superpowers/plans/2026-06-10-worker-control-api.md`: this plan.

## Task 1: Worker Status API

**Files:**
- Create: `backend/tests/api/test_worker_control.py`
- Modify: `backend/src/debug_agent/api/routes.py`

- [ ] **Step 1: Write failing status endpoint test**

Create `backend/tests/api/test_worker_control.py` with:

```python
from fastapi.testclient import TestClient

from debug_agent.main import app


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
```

- [ ] **Step 2: Run the status endpoint test to verify it fails**

Run:

```powershell
python -m pytest tests/api/test_worker_control.py::test_worker_status_endpoint_reports_lifecycle_state -q
```

Expected: FAIL with 404 because `/worker/status` does not exist yet.

- [ ] **Step 3: Add worker instance and status endpoint**

In `backend/src/debug_agent/api/routes.py`, add this import:

```python
from debug_agent.jobs.worker import AsyncJobWorker, AsyncJobWorkerStatus
```

After `job_service = DebugJobService(job_repository)`, add:

```python
job_worker = AsyncJobWorker(job_service)
```

After the `/jobs/run-next` endpoint, add:

```python
@router.get("/worker/status")
def get_worker_status() -> AsyncJobWorkerStatus:
    return job_worker.status()
```

- [ ] **Step 4: Run the status endpoint test to verify it passes**

Run:

```powershell
python -m pytest tests/api/test_worker_control.py::test_worker_status_endpoint_reports_lifecycle_state -q
```

Expected: PASS.

## Task 2: Worker Start And Stop API

**Files:**
- Modify: `backend/tests/api/test_worker_control.py`
- Modify: `backend/src/debug_agent/api/routes.py`

- [ ] **Step 1: Add failing start/stop API test**

Append this test to `backend/tests/api/test_worker_control.py`:

```python
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
```

- [ ] **Step 2: Run the worker control tests to verify failure**

Run:

```powershell
python -m pytest tests/api/test_worker_control.py -q
```

Expected: FAIL with 404 for `/worker/start` or `/worker/stop`.

- [ ] **Step 3: Add start and stop endpoints**

In `backend/src/debug_agent/api/routes.py`, add:

```python
@router.post("/worker/start", status_code=202)
def start_worker() -> AsyncJobWorkerStatus:
    job_worker.start()
    return job_worker.status()


@router.post("/worker/stop")
async def stop_worker() -> AsyncJobWorkerStatus:
    await job_worker.stop()
    return job_worker.status()
```

- [ ] **Step 4: Run worker control tests**

Run:

```powershell
python -m pytest tests/api/test_worker_control.py -q
```

Expected: PASS with 2 worker control API tests.

## Task 3: Worker API Consumes Submitted Jobs

**Files:**
- Modify: `backend/tests/api/test_worker_control.py`
- Modify: `backend/src/debug_agent/api/routes.py` only if needed

- [ ] **Step 1: Add failing consumption test**

Append this helper and test to `backend/tests/api/test_worker_control.py`:

```python
import time
from collections.abc import Callable


def wait_until(predicate: Callable[[], bool], timeout_seconds: float = 1.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("condition was not met before timeout")


def test_worker_start_consumes_submitted_debug_job() -> None:
    client = TestClient(app)
    submit_response = client.post("/cases/handwrite233/debug-jobs")
    job_id = submit_response.json()["job_id"]

    start_response = client.post("/worker/start")
    wait_until(lambda: client.get(f"/jobs/{job_id}").json()["status"] == "completed")
    stop_response = client.post("/worker/stop")

    status_response = client.get(f"/jobs/{job_id}")
    worker_status = client.get("/worker/status").json()
    assert start_response.status_code == 202
    assert stop_response.status_code == 200
    assert status_response.json()["status"] == "completed"
    assert status_response.json()["attempt_count"] == 1
    assert len(status_response.json()["evidence_ids"]) == 6
    assert worker_status["processed_count"] >= 1
```

- [ ] **Step 2: Run the consumption test**

Run:

```powershell
python -m pytest tests/api/test_worker_control.py::test_worker_start_consumes_submitted_debug_job -q
```

Expected: PASS if Task 2 implementation is sufficient. If it fails because a previous test leaves the worker running, call `/worker/stop` at the start of each test.

- [ ] **Step 3: Stabilize tests if needed**

If tests interfere through the global worker instance, add this helper to `backend/tests/api/test_worker_control.py` and call it at the start and end of each test:

```python
def stop_worker_if_running(client: TestClient) -> None:
    client.post("/worker/stop")
```

Use it like:

```python
    client = TestClient(app)
    stop_worker_if_running(client)
```

Expected: tests pass independently and in file order.

## Task 4: Full Verification And Commit

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Create: `backend/tests/api/test_worker_control.py`
- Create: `docs/superpowers/plans/2026-06-10-worker-control-api.md`

- [ ] **Step 1: Run API tests**

Run:

```powershell
python -m pytest tests/api -q
```

Expected: all API tests pass.

- [ ] **Step 2: Run full verification**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1 -Target all
```

Expected:
- Backend tests pass.
- Frontend tests pass.
- Backend lint passes.
- Frontend lint passes.
- Backend typecheck passes.
- Frontend typecheck passes.

- [ ] **Step 3: Run diagnostics**

Run diagnostics for:
- `backend/src/debug_agent/api/routes.py`
- `backend/tests/api/test_worker_control.py`

Expected: no diagnostics.

- [ ] **Step 4: Secret scan**

Run:

```powershell
git diff -- backend/src/debug_agent/api/routes.py backend/tests/api/test_worker_control.py docs/superpowers/plans/2026-06-10-worker-control-api.md | Select-String -Pattern 'ark-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
```

Expected: no matches.

- [ ] **Step 5: Commit**

Run:

```powershell
git add backend/src/debug_agent/api/routes.py backend/tests/api/test_worker_control.py docs/superpowers/plans/2026-06-10-worker-control-api.md
git commit -m "feat(api): add worker control endpoints"
```

Expected: one commit containing only Phase 16 worker control API changes and plan.

## Self-Review

- Spec coverage: The plan exposes status, start, stop, and an end-to-end proof that the worker consumes a submitted job.
- Placeholder scan: No TBD, TODO, or vague implementation steps remain.
- Type consistency: The plan uses `AsyncJobWorker`, `AsyncJobWorkerStatus`, `job_service`, and existing route patterns exactly as currently defined.
