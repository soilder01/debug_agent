# Worker Claim And Retry Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make worker execution safer by adding explicit job claim semantics and basic retry accounting before introducing long-running background workers.

**Architecture:** Extend the SQLAlchemy job row with an attempt counter, add repository methods that atomically-ish claim a `created` job by transitioning it to `running`, and have `DebugJobService.run_next_job()` execute only claimed jobs. This keeps the current in-process worker testable while preparing for background loops and multi-worker protection.

**Tech Stack:** Python 3.11, SQLAlchemy 2, FastAPI, Pydantic v2, pytest, Ruff, mypy.

---

## File Structure

- `backend/src/debug_agent/storage/models.py`: add `attempt_count` to `DebugJobRow`.
- `backend/src/debug_agent/storage/repository.py`: add claim and retry helpers.
- `backend/src/debug_agent/jobs/service.py`: use claim semantics in `run_next_job()`.
- `backend/tests/storage/test_repository.py`: verify claim transitions and attempt accounting.
- `backend/tests/jobs/test_service.py`: verify service consumes a claimed job and ignores already running jobs.

## Task 1: Job Attempt Column

**Files:**
- Modify: `backend/src/debug_agent/storage/models.py`
- Modify: `backend/tests/storage/test_repository.py`

- [ ] **Step 1: Write failing test**

Add a storage test that creates a job and asserts `attempt_count == 0`.

- [ ] **Step 2: Run focused test**

Run: `python -m pytest tests/storage/test_repository.py::test_repository_created_job_starts_with_zero_attempts -q`

Expected: FAIL because `DebugJobRow` has no `attempt_count`.

- [ ] **Step 3: Implement column**

Add `attempt_count: Mapped[int] = mapped_column(Integer, default=0)` to `DebugJobRow`.

- [ ] **Step 4: Verify**

Run: `python -m pytest tests/storage/test_repository.py -q`

Expected: PASS.

## Task 2: Claim Next Created Job

**Files:**
- Modify: `backend/src/debug_agent/storage/repository.py`
- Modify: `backend/tests/storage/test_repository.py`

- [ ] **Step 1: Write failing test**

Add a test that calls `claim_next_created_job()`, expects the claimed job status to become `running`, attempt count to become `1`, and a second claim to return `None`.

- [ ] **Step 2: Run focused test**

Run: `python -m pytest tests/storage/test_repository.py::test_repository_claims_created_job_once -q`

Expected: FAIL with missing method.

- [ ] **Step 3: Implement method**

Add `claim_next_created_job()` to repository. It should select the first `created` row, set `status="running"`, increment `attempt_count`, commit, and return the claimed row.

- [ ] **Step 4: Verify**

Run: `python -m pytest tests/storage/test_repository.py -q`

Expected: PASS.

## Task 3: Service Uses Claim

**Files:**
- Modify: `backend/src/debug_agent/jobs/service.py`
- Modify: `backend/tests/jobs/test_service.py`

- [ ] **Step 1: Write failing service test**

Add a test that creates a job, marks it `running`, calls `run_next_job()`, and expects `None`.

- [ ] **Step 2: Run focused test**

Run: `python -m pytest tests/jobs/test_service.py::test_job_service_does_not_run_already_running_job -q`

Expected: PASS or FAIL depending on repository behavior; if it passes, keep it as regression coverage.

- [ ] **Step 3: Update service**

Change `run_next_job()` to call `claim_next_created_job()` and pass the claimed row into execution without a second claim.

- [ ] **Step 4: Verify**

Run: `python -m pytest tests/jobs/test_service.py tests/api -q`

Expected: PASS.

## Task 4: Full Verification

**Files:**
- Modify only files required by failing checks.

- [ ] **Step 1: Run complete verification**

Run: `powershell -ExecutionPolicy Bypass -File scripts/verify.ps1 -Target all`

Expected: all tests, lint, and type checks pass.

- [ ] **Step 2: Inspect git status**

Run: `git status --short`

Expected: only intended Phase 5, Phase 6, and worker-claim files are modified or added.
