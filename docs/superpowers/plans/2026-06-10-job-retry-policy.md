# Job Retry Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic retry policy for failed debug jobs so transient failures can be retried and exhausted failures become visible.

**Architecture:** Keep retry logic inside `DebugJobService` and state persistence inside `DebugJobRepository`. A failed claimed job is released back to `created` while `attempt_count < max_attempts`; once attempts are exhausted it transitions to `failed` with the latest error message.

**Tech Stack:** Python 3.11, SQLAlchemy 2, Pydantic v2, pytest, Ruff, mypy.

---

## File Structure

- `backend/src/debug_agent/storage/repository.py`: add `release_for_retry()`.
- `backend/src/debug_agent/jobs/service.py`: add `max_attempts` constructor option and retry decision.
- `backend/tests/storage/test_repository.py`: verify retry release state.
- `backend/tests/jobs/test_service.py`: verify retry and final failure behavior using invalid fixture case ids.

## Task 1: Repository Release For Retry

**Files:**
- Modify: `backend/src/debug_agent/storage/repository.py`
- Modify: `backend/tests/storage/test_repository.py`

- [ ] **Step 1: Write failing test**

Add a test that creates a job, claims it, releases it for retry with an error message, and asserts status returns to `created`, `attempt_count` remains `1`, and `error_message` is preserved.

- [ ] **Step 2: Run focused test**

Run: `python -m pytest tests/storage/test_repository.py::test_repository_releases_running_job_for_retry -q`

Expected: FAIL with missing `release_for_retry`.

- [ ] **Step 3: Implement repository method**

Add `release_for_retry(job_id, error_message)` that sets `status="created"` and stores `error_message`.

- [ ] **Step 4: Verify storage tests**

Run: `python -m pytest tests/storage/test_repository.py -q`

Expected: PASS.

## Task 2: Service Retries Until Max Attempts

**Files:**
- Modify: `backend/src/debug_agent/jobs/service.py`
- Modify: `backend/tests/jobs/test_service.py`

- [ ] **Step 1: Write failing service test**

Add an async test using a repository-created job with `case_id="missing-case"` and `DebugJobService(repository, max_attempts=2)`. The first `run_next_job()` should raise `FileNotFoundError`, leave the job `created`, and keep `attempt_count == 1`.

- [ ] **Step 2: Run focused test**

Run: `python -m pytest tests/jobs/test_service.py::test_job_service_requeues_failed_job_before_max_attempts -q`

Expected: FAIL because current service always marks failed.

- [ ] **Step 3: Implement retry decision**

Change exception handling in `_run_claimed_job()` so it reads current `attempt_count`; if below `max_attempts`, call `release_for_retry()`, otherwise `mark_failed()`.

- [ ] **Step 4: Verify focused test**

Run: `python -m pytest tests/jobs/test_service.py::test_job_service_requeues_failed_job_before_max_attempts -q`

Expected: PASS.

## Task 3: Service Marks Exhausted Job Failed

**Files:**
- Modify: `backend/tests/jobs/test_service.py`
- Modify only failing implementation if needed.

- [ ] **Step 1: Write exhausted retry test**

Add an async test using `case_id="missing-case"` and `max_attempts=1`. `run_next_job()` should raise `FileNotFoundError`, leave status `failed`, `attempt_count == 1`, and store an error message.

- [ ] **Step 2: Run focused test**

Run: `python -m pytest tests/jobs/test_service.py::test_job_service_marks_job_failed_when_attempts_exhausted -q`

Expected: PASS if Task 2 was implemented correctly; otherwise fix implementation minimally.

- [ ] **Step 3: Verify service and API tests**

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

Expected: only intended ongoing implementation files are modified or added.
