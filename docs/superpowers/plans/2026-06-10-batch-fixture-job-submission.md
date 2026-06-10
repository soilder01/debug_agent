# Batch Fixture Job Submission Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a minimal batch submission API that creates one debug job per fixture case id, preparing the system for sheet-driven batch ingestion.

**Architecture:** Keep batch submission at the API/service layer and reuse `DebugJobService.submit_case_debug()` for each case id. The initial response returns a batch summary with created jobs and rejected case ids; no new database batch table is introduced yet.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, pytest.

---

## File Structure

- `backend/src/debug_agent/api/routes.py`: add request/response models and `/debug-jobs/batch` route.
- `backend/tests/api/test_batch_job_submission.py`: verify multiple fixture ids produce multiple jobs and invalid ids are reported.

## Task 1: Batch Job Submission API

**Files:**
- Create: `backend/tests/api/test_batch_job_submission.py`
- Modify: `backend/src/debug_agent/api/routes.py`

- [ ] **Step 1: Write failing API test**

Create a test that posts `{"case_ids": ["handwrite233", "missing-case"]}` to `/debug-jobs/batch`, expects `202`, one created job for `handwrite233`, one rejected id for `missing-case`, and verifies the created job is queryable through `/jobs/{job_id}`.

- [ ] **Step 2: Run focused API test**

Run: `python -m pytest tests/api/test_batch_job_submission.py -q`

Expected: FAIL with HTTP 404 because the route does not exist.

- [ ] **Step 3: Implement route**

Add Pydantic models `BatchDebugJobRequest` and `BatchDebugJobResponse` in `routes.py`. Implement `POST /debug-jobs/batch` with `status_code=202`; for each case id, call `job_service.submit_case_debug()`, collect successes, and collect `FileNotFoundError` ids into `rejected_case_ids`.

- [ ] **Step 4: Verify API tests**

Run: `python -m pytest tests/api -q`

Expected: PASS.

## Task 2: Full Verification And Commit

**Files:**
- Modify only files required by failing checks.

- [ ] **Step 1: Run complete verification**

Run: `powershell -ExecutionPolicy Bypass -File scripts/verify.ps1 -Target all`

Expected: all tests, lint, and type checks pass.

- [ ] **Step 2: Inspect and commit**

Run: `git status --short`, then commit the intended files with a conventional commit.
