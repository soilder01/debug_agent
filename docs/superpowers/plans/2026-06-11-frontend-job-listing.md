# Frontend Job Listing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let operators load persisted debug jobs from `GET /jobs` into the frontend batch/job triage list.

**Architecture:** Add a typed frontend client for `GET /jobs`, add a “Load debug jobs” action in the Batch Jobs section, and reuse the existing batch job status rendering so loaded jobs show status, retry guidance, and errors.

**Tech Stack:** React, TypeScript, Vitest, Testing Library.

---

### Task 1: Frontend Job Listing

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`
- Test: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Add failing frontend assertion**

Add a test that clicks `Load debug jobs`, expects `fetch("/api/jobs")`, and verifies a returned job appears in the batch list with retry guidance.

- [x] **Step 2: Run frontend focused test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: FAIL because no UI action calls `GET /jobs`.

- [x] **Step 3: Implement API client**

Add `DebugJobListResponse` and `fetchDebugJobs()` in `frontend/src/api/client.ts`.

- [x] **Step 4: Implement UI action**

Import `fetchDebugJobs()`, add `loadDebugJobs()`, render `Load debug jobs`, and populate `batchResult` plus `batchJobStatuses`.

- [x] **Step 5: Run frontend focused test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: PASS.

### Task 2: Verification and Checkpoint

**Files:**
- Modify: `docs/superpowers/plans/2026-06-11-frontend-job-listing.md`

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and secret scan**

Run diagnostics and scan for Ark key patterns.

- [x] **Step 3: Commit**

Run:

```bash
git add frontend/src/api/client.ts frontend/src/app/App.tsx frontend/src/app/App.test.tsx docs/superpowers/plans/2026-06-11-frontend-job-listing.md
git commit -m "feat(jobs): load persisted jobs in frontend"
```
