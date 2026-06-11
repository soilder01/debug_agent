# Frontend Job Status Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let operators load failed jobs directly from the frontend using the backend `GET /jobs?status=failed` filter.

**Architecture:** Extend `fetchDebugJobs()` with an optional status parameter and add a `Load failed jobs` button in the Batch Jobs section. Reuse the existing batch triage list rendering.

**Tech Stack:** React, TypeScript, Vitest, Testing Library.

---

### Task 1: Failed Job Loading

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`
- Test: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Add failing frontend assertion**

Add a test that clicks `Load failed jobs`, expects `fetch("/api/jobs?status=failed")`, and verifies the failed job appears.

- [x] **Step 2: Run frontend focused test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: FAIL because the failed-job button does not exist yet.

- [x] **Step 3: Implement client status parameter**

Change `fetchDebugJobs(status?: string)` to call `/api/jobs?status=<status>` when provided.

- [x] **Step 4: Implement UI button**

Add `Load failed jobs` and call the existing job loading path with `failed`.

- [x] **Step 5: Run frontend focused test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: PASS.

### Task 2: Verification and Checkpoint

**Files:**
- Modify: `docs/superpowers/plans/2026-06-11-frontend-job-status-filter.md`

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and secret scan**

Run diagnostics and scan for Ark key patterns.

- [x] **Step 3: Commit**

Run:

```bash
git add frontend/src/api/client.ts frontend/src/app/App.tsx frontend/src/app/App.test.tsx docs/superpowers/plans/2026-06-11-frontend-job-status-filter.md
git commit -m "feat(jobs): load failed jobs in frontend"
```
