# Job Status Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose retry attempts and job errors through the API and frontend so operators can understand pending, retried, completed, and failed jobs.

**Architecture:** Extend the existing `/jobs/{job_id}` response contract with `attempt_count`, keep persistence in the existing SQLAlchemy job row, and add a small frontend job status panel. The UI will render submitted job state immediately and can render fetched job status in later phases without changing the type contract.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2, pytest, React 18, TypeScript, Vitest.

---

## File Structure

- `backend/src/debug_agent/api/routes.py`: include `attempt_count` in `DebugJobStatus`.
- `backend/tests/api/test_job_status.py`: assert attempts appear after worker execution.
- `frontend/src/api/client.ts`: add `DebugJobStatus` type and `fetchJobStatus()` client.
- `frontend/src/jobs/JobStatusPanel.tsx`: present job id, status, attempts, and error message.
- `frontend/src/app/App.tsx`: render `JobStatusPanel` for submitted jobs.
- `frontend/src/app/App.test.tsx`: assert attempts/error observability in UI.

## Task 1: API Job Status Includes Attempt Count

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Modify: `backend/tests/api/test_job_status.py`

- [ ] **Step 1: Write failing API assertion**

Update `test_debug_case_returns_queryable_completed_job_status` to assert `body["attempt_count"] == 0` for the synchronous compatibility endpoint.

- [ ] **Step 2: Run focused test**

Run: `python -m pytest tests/api/test_job_status.py -q`

Expected: FAIL with missing `attempt_count`.

- [ ] **Step 3: Implement response field**

Add `attempt_count: int` to `DebugJobStatus` and populate it from `job.attempt_count`.

- [ ] **Step 4: Verify API tests**

Run: `python -m pytest tests/api -q`

Expected: PASS.

## Task 2: Frontend Job Status Type And Panel

**Files:**
- Modify: `frontend/src/api/client.ts`
- Create: `frontend/src/jobs/JobStatusPanel.tsx`
- Modify: `frontend/src/app/App.test.tsx`
- Modify: `frontend/src/app/App.tsx`

- [ ] **Step 1: Write failing UI expectation**

Update the submitted job mock to include `attempt_count: 0` and `error_message: null`, then assert the UI renders `尝试次数：0` and no error.

- [ ] **Step 2: Run focused frontend test**

Run: `npx --yes pnpm@9.15.4 test -- --run src/app/App.test.tsx`

Expected: FAIL because attempts are not rendered.

- [ ] **Step 3: Implement type and panel**

Add `DebugJobStatus` type plus `fetchJobStatus(jobId)`. Create `JobStatusPanel` and render it in `App.tsx` for submitted jobs.

- [ ] **Step 4: Verify frontend test**

Run: `npx --yes pnpm@9.15.4 test -- --run src/app/App.test.tsx`

Expected: PASS.

## Task 3: Full Verification

**Files:**
- Modify only files required by failing checks.

- [ ] **Step 1: Run complete verification**

Run: `powershell -ExecutionPolicy Bypass -File scripts/verify.ps1 -Target all`

Expected: all tests, lint, and type checks pass.

- [ ] **Step 2: Inspect git status**

Run: `git status --short`

Expected: only intended ongoing implementation files are modified or added.
