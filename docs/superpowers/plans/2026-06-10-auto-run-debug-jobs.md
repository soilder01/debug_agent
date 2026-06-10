# Auto Run Debug Jobs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a submitted debug job execute automatically in the request lifecycle for the local harness so the frontend polling flow can observe completion without manually calling `/jobs/run-next`.

**Architecture:** Add an explicit `auto_run` query option to `POST /cases/{case_id}/debug-jobs`. When enabled, the API submits the job, runs that exact job once through the existing `DebugJobService`, and still returns `202` with the created job payload so clients keep the async contract. This is a controlled stepping stone before a true background worker loop.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, pytest, existing React polling client.

---

## File Structure

- `backend/src/debug_agent/api/routes.py`: add `auto_run` query parameter to debug job submission.
- `backend/tests/api/test_job_submission.py`: verify auto-run completes the submitted job without `/jobs/run-next`.
- `frontend/src/api/client.ts`: request `auto_run=true` when submitting local debug jobs.
- `frontend/src/app/App.test.tsx`: assert submit call uses `auto_run=true`.

## Task 1: API Auto Run Option

**Files:**
- Modify: `backend/tests/api/test_job_submission.py`
- Modify: `backend/src/debug_agent/api/routes.py`

- [ ] **Step 1: Write failing API test**

Add a test that calls `POST /cases/handwrite233/debug-jobs?auto_run=true`, asserts `202`, and then checks `GET /jobs/{job_id}` returns `completed` without calling `/jobs/run-next`.

- [ ] **Step 2: Run focused API test**

Run: `python -m pytest tests/api/test_job_submission.py::test_submit_debug_job_with_auto_run_completes_without_worker_tick -q`

Expected: FAIL because `auto_run` is ignored.

- [ ] **Step 3: Implement API option**

Update `submit_debug_job(case_id: str, auto_run: bool = False)` so it submits the job and, when `auto_run` is true, calls `await job_service.run_job(submitted.job_id)` before returning the original submitted payload.

- [ ] **Step 4: Verify API tests**

Run: `python -m pytest tests/api -q`

Expected: PASS.

## Task 2: Frontend Uses Auto Run For Local Harness

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.test.tsx`

- [ ] **Step 1: Write failing frontend assertion**

Update the app test to expect `fetch` was called with `/api/cases/handwrite233/debug-jobs?auto_run=true`.

- [ ] **Step 2: Run focused frontend test**

Run: `npx --yes pnpm@9.15.4 test -- --run src/app/App.test.tsx`

Expected: FAIL because the client posts to `/debug-jobs`.

- [ ] **Step 3: Implement client URL**

Update `submitDebugJob()` to post to `/api/cases/${caseId}/debug-jobs?auto_run=true`.

- [ ] **Step 4: Verify frontend test**

Run: `npx --yes pnpm@9.15.4 test -- --run src/app/App.test.tsx`

Expected: PASS.

## Task 3: Full Verification And Commit

**Files:**
- Modify only files required by failing checks.

- [ ] **Step 1: Run complete verification**

Run: `powershell -ExecutionPolicy Bypass -File scripts/verify.ps1 -Target all`

Expected: all tests, lint, and type checks pass.

- [ ] **Step 2: Inspect and commit**

Run: `git status --short`, then commit the intended files with a conventional commit.
