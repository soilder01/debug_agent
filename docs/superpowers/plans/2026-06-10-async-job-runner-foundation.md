# Async Job Runner Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split case debug submission from job execution so long-running OCR debug work becomes observable, retryable, and compatible with future queues.

**Architecture:** Introduce a small in-process job service above the existing repository and experiment runner. The API will support submitting a job without immediately running all experiments, running one pending job deterministically in tests, and querying durable job status through the existing `/jobs/{job_id}` endpoint.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2, pytest, React 18, TypeScript, Vitest.

---

## File Structure

- `backend/src/debug_agent/jobs/service.py`: job orchestration service that submits jobs and runs one pending job.
- `backend/src/debug_agent/storage/repository.py`: repository query helpers for pending jobs.
- `backend/src/debug_agent/api/routes.py`: API routes for submit/query/run-next job behavior.
- `backend/tests/jobs/test_service.py`: service-level TDD coverage for pending-to-completed lifecycle.
- `backend/tests/api/test_job_submission.py`: API contract coverage for accepted async submission and manual worker tick.
- `frontend/src/api/client.ts`: frontend client types for async job submission/status.
- `frontend/src/app/App.tsx`: switch UI action to submit job and display pending/completed job state.
- `frontend/src/app/App.test.tsx`: frontend regression for submitted job display.

## Task 1: Repository Pending Job Query

**Files:**
- Modify: `backend/src/debug_agent/storage/repository.py`
- Test: `backend/tests/storage/test_repository.py`

- [ ] **Step 1: Write the failing test**

Add this test to `backend/tests/storage/test_repository.py`:

```python
def test_repository_returns_oldest_created_job() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)

    repository.create_job(job_id="job-2", case_id="case-2")
    repository.create_job(job_id="job-1", case_id="case-1")
    repository.mark_running("job-2")

    job = repository.get_next_created_job()

    assert job is not None
    assert job.job_id == "job-1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/storage/test_repository.py::test_repository_returns_oldest_created_job -q`

Expected: FAIL with `AttributeError: 'DebugJobRepository' object has no attribute 'get_next_created_job'`.

- [ ] **Step 3: Write minimal implementation**

Add `get_next_created_job()` to `DebugJobRepository`:

```python
def get_next_created_job(self) -> DebugJobRow | None:
    with self._session_factory() as session:
        return session.scalars(
            select(DebugJobRow)
            .where(DebugJobRow.status == "created")
            .order_by(DebugJobRow.job_id)
            .limit(1)
        ).first()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/storage/test_repository.py -q`

Expected: PASS.

## Task 2: Job Service Submit And Run-Next

**Files:**
- Create: `backend/src/debug_agent/jobs/__init__.py`
- Create: `backend/src/debug_agent/jobs/service.py`
- Test: `backend/tests/jobs/test_service.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/jobs/test_service.py`:

```python
from debug_agent.jobs.service import DebugJobService
from debug_agent.storage.database import create_sqlite_memory_session_factory
from debug_agent.storage.models import Base
from debug_agent.storage.repository import DebugJobRepository


def test_job_service_submits_pending_job_and_runs_next_to_completion() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    service = DebugJobService(repository)

    submitted = service.submit_case_debug("handwrite233")

    assert submitted.status == "created"

    result = service.run_next_job()

    assert result is not None
    assert result.job_id == submitted.job_id
    job = repository.get_job(submitted.job_id)
    assert job is not None
    assert job.status == "completed"
    assert len(repository.list_evidence_ids(submitted.job_id)) == 6
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/jobs/test_service.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'debug_agent.jobs'`.

- [ ] **Step 3: Write minimal implementation**

Create `backend/src/debug_agent/jobs/__init__.py` as an empty package marker.

Create `backend/src/debug_agent/jobs/service.py` with:

```python
from uuid import uuid4

from pydantic import BaseModel

from debug_agent.artifacts.store import artifact_store
from debug_agent.cases.fixtures import load_fixture_case
from debug_agent.experiments.planner import plan_experiments
from debug_agent.experiments.runner import run_experiments
from debug_agent.models.fake import FakeModelAdapter
from debug_agent.storage.repository import DebugJobRepository


class SubmittedDebugJob(BaseModel):
    job_id: str
    case_id: str
    status: str


class DebugJobService:
    def __init__(self, repository: DebugJobRepository) -> None:
        self._repository = repository

    def submit_case_debug(self, case_id: str) -> SubmittedDebugJob:
        case = load_fixture_case(case_id)
        job_id = str(uuid4())
        self._repository.create_job(job_id=job_id, case_id=case.case_id)
        return SubmittedDebugJob(job_id=job_id, case_id=case.case_id, status="created")

    async def run_job(self, job_id: str) -> SubmittedDebugJob:
        job = self._repository.get_job(job_id)
        if job is None:
            raise KeyError(f"Debug job not found: {job_id}")
        self._repository.mark_running(job_id)
        case = load_fixture_case(job.case_id)
        plan = plan_experiments(case)
        adapter = FakeModelAdapter(outputs=[prediction.raw_output for prediction in case.predictions])
        try:
            run_result = await run_experiments(case=case, plan=plan, adapter=adapter)
            artifact_store.save_case_evidence(case.case_id, run_result.evidence)
            self._repository.save_evidence(job_id=job_id, case_id=case.case_id, evidence=run_result.evidence)
            self._repository.mark_completed(job_id)
        except Exception as exc:
            self._repository.mark_failed(job_id, str(exc))
            raise
        return SubmittedDebugJob(job_id=job_id, case_id=case.case_id, status="completed")

    async def run_next_job(self) -> SubmittedDebugJob | None:
        job = self._repository.get_next_created_job()
        if job is None:
            return None
        return await self.run_job(job.job_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/jobs/test_service.py -q`

Expected: PASS.

## Task 3: API Async Submission And Worker Tick

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Test: `backend/tests/api/test_job_submission.py`

- [ ] **Step 1: Write the failing API test**

Create `backend/tests/api/test_job_submission.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/api/test_job_submission.py -q`

Expected: FAIL with HTTP `404` for `/cases/handwrite233/debug-jobs`.

- [ ] **Step 3: Update API routes**

In `backend/src/debug_agent/api/routes.py`:

- instantiate `DebugJobService(job_repository)`.
- add `POST /cases/{case_id}/debug-jobs` with `status_code=202`.
- add `POST /jobs/run-next`.
- keep existing `POST /cases/{case_id}/debug` as synchronous compatibility by calling `submit_case_debug()` then `run_job()`.

- [ ] **Step 4: Run API tests**

Run: `python -m pytest tests/api -q`

Expected: PASS.

## Task 4: Frontend Job Submission Contract

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/app/App.test.tsx`

- [ ] **Step 1: Write failing frontend expectation**

Update `frontend/src/app/App.test.tsx` fetch mock so the button receives a submitted job payload from `/api/cases/handwrite233/debug-jobs`, then assert:

```typescript
expect(await screen.findByText("Job ID：job-123")).toBeInTheDocument();
expect(screen.getByText("状态：created")).toBeInTheDocument();
```

- [ ] **Step 2: Run frontend test to verify it fails**

Run: `npx --yes pnpm@9.15.4 test -- --run src/app/App.test.tsx`

Expected: FAIL because the frontend still calls `/api/cases/handwrite233/debug`.

- [ ] **Step 3: Update frontend client and UI**

Add a `SubmittedDebugJob` type and `submitDebugJob(caseId)` client function. Update `App.tsx` to call `submitDebugJob("handwrite233")` for the first button and render the submitted job state through `CaseDetail`.

- [ ] **Step 4: Run frontend test**

Run: `npx --yes pnpm@9.15.4 test -- --run src/app/App.test.tsx`

Expected: PASS.

## Task 5: Full Verification

**Files:**
- Modify only files required by failing checks.

- [ ] **Step 1: Run complete verification**

Run: `powershell -ExecutionPolicy Bypass -File scripts/verify.ps1 -Target all`

Expected: backend tests, frontend tests, backend lint, frontend lint, backend typecheck, and frontend typecheck all pass.

- [ ] **Step 2: Inspect git status**

Run: `git status --short`

Expected: only intended Phase 5 and Phase 6 files are modified or added.
