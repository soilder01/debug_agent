# Frontend Job List Limit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Use the backend job-list `limit` parameter from the frontend so loading historical queues is bounded by default.

**Architecture:** Extend `fetchDebugJobs()` with an optional `limit` argument and have the Batch Jobs load actions request at most 50 jobs. Preserve status filtering and existing batch list rendering.

**Tech Stack:** React, TypeScript, Vitest, Testing Library.

---

### Task 1: Frontend Default Limit

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`
- Test: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Add failing frontend assertions**

Update the job loading tests to expect `/api/jobs?limit=50` and `/api/jobs?status=failed&limit=50`.

- [x] **Step 2: Run frontend focused test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: FAIL because frontend does not pass `limit`.

- [x] **Step 3: Implement client query builder**

Change `fetchDebugJobs(status?: string, limit?: number)` to build query params for both status and limit.

- [x] **Step 4: Pass default limit from UI**

Set a local `jobListLimit = 50` constant and call `fetchDebugJobs(status, jobListLimit)`.

- [x] **Step 5: Run frontend focused test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: PASS.

### Task 2: Verification and Checkpoint

**Files:**
- Modify: `docs/superpowers/plans/2026-06-11-frontend-job-list-limit.md`

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and secret scan**

Run diagnostics and scan for Ark key patterns.

- [x] **Step 3: Commit**

Run:

```bash
git add frontend/src/api/client.ts frontend/src/app/App.tsx frontend/src/app/App.test.tsx docs/superpowers/plans/2026-06-11-frontend-job-list-limit.md
git commit -m "feat(jobs): limit frontend job loading"
```
