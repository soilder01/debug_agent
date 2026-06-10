# Frontend Job Status Polling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After submitting a debug job, automatically poll `/jobs/{job_id}` until the job reaches a terminal state so reviewers see live status, attempts, errors, and evidence ids.

**Architecture:** Keep polling inside the React app for now using a small `useEffect` loop and the existing `fetchJobStatus()` client. Poll only while the latest job is non-terminal (`created` or `running`) and stop at `completed` or `failed`.

**Tech Stack:** React 18, TypeScript, Vitest, Testing Library, FastAPI-compatible frontend API contract.

---

## File Structure

- `frontend/src/app/App.tsx`: maintain job status state and poll after submit.
- `frontend/src/app/App.test.tsx`: verify submit followed by polling renders completed job status and evidence count.
- `frontend/src/jobs/JobStatusPanel.tsx`: render evidence count from status payload.

## Task 1: Poll Job Status After Submit

**Files:**
- Modify: `frontend/src/app/App.test.tsx`
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/jobs/JobStatusPanel.tsx`

- [ ] **Step 1: Write failing frontend test**

Update the app test to mock two fetch calls: first `POST /debug-jobs` returns `created`, then `GET /jobs/job-123` returns `completed` with `evidence_ids: ["e1"]`. Use fake timers to advance polling and assert `状态：completed` and `证据数：1`.

- [ ] **Step 2: Run focused frontend test**

Run: `npx --yes pnpm@9.15.4 test -- --run src/app/App.test.tsx`

Expected: FAIL because the app does not poll after submit.

- [ ] **Step 3: Implement polling**

Import `useEffect` and `fetchJobStatus()` in `App.tsx`. Store `jobStatus` separately from `submittedJob`. When a submitted job exists and status is not terminal, start a timeout that fetches `/jobs/{job_id}` and updates `jobStatus`.

- [ ] **Step 4: Render evidence count**

Update `JobStatusPanel` to render `证据数：{job.evidence_ids?.length ?? 0}`.

- [ ] **Step 5: Verify focused frontend test**

Run: `npx --yes pnpm@9.15.4 test -- --run src/app/App.test.tsx`

Expected: PASS.

## Task 2: Full Verification

**Files:**
- Modify only files required by failing checks.

- [ ] **Step 1: Run complete verification**

Run: `powershell -ExecutionPolicy Bypass -File scripts/verify.ps1 -Target all`

Expected: all tests, lint, and type checks pass.

- [ ] **Step 2: Inspect git status**

Run: `git status --short`

Expected: only frontend polling plan and implementation files are modified or added.
