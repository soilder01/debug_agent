# Async Worker Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a minimal asynchronous background worker loop that continuously consumes created debug jobs using the existing `DebugJobService`.

**Architecture:** Introduce a focused `AsyncJobWorker` class in `debug_agent.jobs.worker`. The worker owns loop lifecycle state, executes one safe `tick()` at a time via `DebugJobService.run_next_job()`, catches job execution errors so the loop does not die, and exposes a serializable status object for future API/UI observability.

**Tech Stack:** Python 3.11, asyncio, Pydantic v2, pytest-asyncio, existing SQLAlchemy repository and job service.

---

## File Structure

- Create `backend/src/debug_agent/jobs/worker.py`: owns background worker lifecycle, single-tick execution, error capture, and status reporting.
- Create `backend/tests/jobs/test_worker.py`: proves the worker can process created jobs without manual `/jobs/run-next`, can stop cleanly, does not start twice, and survives a failing job attempt.
- No API route changes in this phase: the worker loop foundation is backend-internal first. Start/stop API endpoints can be added in the next phase once lifecycle semantics are verified in isolation.

## Task 1: Worker Processes Jobs In Background

**Files:**
- Create: `backend/tests/jobs/test_worker.py`
- Create: `backend/src/debug_agent/jobs/worker.py`

- [ ] **Step 1: Write the failing worker completion test**

Create `backend/tests/jobs/test_worker.py` with:

```python
import asyncio
from collections.abc import Callable

import pytest

from debug_agent.jobs.service import DebugJobService
from debug_agent.jobs.worker import AsyncJobWorker
from debug_agent.storage.database import create_sqlite_memory_session_factory
from debug_agent.storage.models import Base, DebugJobRow
from debug_agent.storage.repository import DebugJobRepository


async def wait_until(predicate: Callable[[], bool], timeout_seconds: float = 1.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while asyncio.get_running_loop().time() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("condition was not met before timeout")


def create_service() -> tuple[DebugJobRepository, DebugJobService]:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    return repository, DebugJobService(repository)


@pytest.mark.asyncio
async def test_async_worker_processes_created_job_until_completion() -> None:
    repository, service = create_service()
    submitted = service.submit_case_debug("handwrite233")
    worker = AsyncJobWorker(service, idle_sleep_seconds=0.01)

    started = worker.start()
    await wait_until(lambda: repository.get_job(submitted.job_id).status == "completed")
    await worker.stop()

    job = repository.get_job(submitted.job_id)
    assert started is True
    assert job is not None
    assert job.status == "completed"
    assert job.attempt_count == 1
    assert len(repository.list_evidence_ids(submitted.job_id)) == 6
    assert worker.status().running is False
    assert worker.status().processed_count == 1
```

- [ ] **Step 2: Run the worker test to verify it fails**

Run:

```powershell
python -m pytest tests/jobs/test_worker.py::test_async_worker_processes_created_job_until_completion -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'debug_agent.jobs.worker'`.

- [ ] **Step 3: Implement minimal worker loop**

Create `backend/src/debug_agent/jobs/worker.py` with:

```python
import asyncio

from pydantic import BaseModel

from debug_agent.jobs.service import DebugJobService


class AsyncJobWorkerStatus(BaseModel):
    running: bool
    processed_count: int
    error_count: int
    last_error: str | None


class AsyncJobWorker:
    def __init__(self, service: DebugJobService, idle_sleep_seconds: float = 0.1) -> None:
        self._service = service
        self._idle_sleep_seconds = idle_sleep_seconds
        self._task: asyncio.Task[None] | None = None
        self._stop_requested = False
        self._processed_count = 0
        self._error_count = 0
        self._last_error: str | None = None

    def start(self) -> bool:
        if self._task is not None and not self._task.done():
            return False
        self._stop_requested = False
        self._task = asyncio.create_task(self._run())
        return True

    async def stop(self) -> None:
        self._stop_requested = True
        if self._task is None:
            return
        await self._task

    async def tick(self) -> None:
        try:
            result = await self._service.run_next_job()
        except Exception as exc:
            self._error_count += 1
            self._last_error = str(exc)
            return
        if result is not None:
            self._processed_count += 1

    def status(self) -> AsyncJobWorkerStatus:
        return AsyncJobWorkerStatus(
            running=self._task is not None and not self._task.done(),
            processed_count=self._processed_count,
            error_count=self._error_count,
            last_error=self._last_error,
        )

    async def _run(self) -> None:
        while not self._stop_requested:
            await self.tick()
            await asyncio.sleep(self._idle_sleep_seconds)
```

- [ ] **Step 4: Run the worker completion test to verify it passes**

Run:

```powershell
python -m pytest tests/jobs/test_worker.py::test_async_worker_processes_created_job_until_completion -q
```

Expected: PASS.

## Task 2: Worker Lifecycle Guardrails

**Files:**
- Modify: `backend/tests/jobs/test_worker.py`
- Modify: `backend/src/debug_agent/jobs/worker.py`

- [ ] **Step 1: Add lifecycle and failure-survival tests**

Append these tests to `backend/tests/jobs/test_worker.py`:

```python
@pytest.mark.asyncio
async def test_async_worker_start_is_idempotent_while_running() -> None:
    _, service = create_service()
    worker = AsyncJobWorker(service, idle_sleep_seconds=0.01)

    first_start = worker.start()
    second_start = worker.start()
    await worker.stop()

    assert first_start is True
    assert second_start is False
    assert worker.status().running is False


@pytest.mark.asyncio
async def test_async_worker_survives_failed_job_attempt_and_keeps_polling() -> None:
    repository, service = create_service()
    repository.create_job(job_id="job-1", case_id="missing-case")
    submitted = service.submit_case_debug("handwrite233")
    worker = AsyncJobWorker(service, idle_sleep_seconds=0.01)

    worker.start()
    await wait_until(lambda: repository.get_job(submitted.job_id).status == "completed")
    await worker.stop()

    failed_attempt = repository.get_job("job-1")
    completed_job = repository.get_job(submitted.job_id)
    assert failed_attempt is not None
    assert failed_attempt.status == "created"
    assert failed_attempt.attempt_count == 1
    assert completed_job is not None
    assert completed_job.status == "completed"
    assert worker.status().error_count == 1
    assert worker.status().last_error is not None
    assert "missing-case" in worker.status().last_error
```

- [ ] **Step 2: Run lifecycle tests**

Run:

```powershell
python -m pytest tests/jobs/test_worker.py -q
```

Expected: PASS with 3 worker tests.

- [ ] **Step 3: Refactor only if needed**

If `mypy` complains about `repository.get_job(...).status` in the test lambda, update the first test lambda to avoid optional access:

```python
    await wait_until(
        lambda: (job := repository.get_job(submitted.job_id)) is not None and job.status == "completed"
    )
```

If no typecheck complaint occurs, do not refactor.

## Task 3: Full Verification And Commit

**Files:**
- Create: `backend/src/debug_agent/jobs/worker.py`
- Create: `backend/tests/jobs/test_worker.py`
- Create: `docs/superpowers/plans/2026-06-10-async-worker-loop.md`

- [ ] **Step 1: Run full verification**

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

- [ ] **Step 2: Run diagnostics**

Run diagnostics for:
- `backend/src/debug_agent/jobs/worker.py`
- `backend/tests/jobs/test_worker.py`

Expected: no diagnostics.

- [ ] **Step 3: Secret scan**

Run:

```powershell
git diff -- backend/src/debug_agent/jobs/worker.py backend/tests/jobs/test_worker.py docs/superpowers/plans/2026-06-10-async-worker-loop.md | Select-String -Pattern 'ark-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|ARK_API_KEY'
```

Expected: no real secret values. The plan may contain the literal text `ARK_API_KEY` only as part of the scan command.

- [ ] **Step 4: Commit**

Run:

```powershell
git add backend/src/debug_agent/jobs/worker.py backend/tests/jobs/test_worker.py docs/superpowers/plans/2026-06-10-async-worker-loop.md
git commit -m "feat(jobs): add async worker loop"
```

Expected: one commit containing only Phase 15 worker loop changes and plan.

## Self-Review

- Spec coverage: The plan implements a backend worker loop foundation, lifecycle state, idempotent start behavior, safe stop behavior, and survival after a failed job attempt.
- Placeholder scan: No TBD, TODO, or unspecified implementation instructions remain.
- Type consistency: The plan uses existing `DebugJobService`, `DebugJobRepository`, `Base`, and `create_sqlite_memory_session_factory()` names exactly as currently defined.
