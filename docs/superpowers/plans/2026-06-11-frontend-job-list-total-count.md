# Frontend Job List Total Count Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Display loaded job count, total count, and unloaded count in the frontend queue panel after bounded job-list loading.

**Architecture:** Extend `DebugJobListResponse` with `total_count`. Store a nullable `jobListTotalCount` in `App`; batch/import flows use local list length, while persisted queue loading uses API `total_count`. Render `总任务` and `未加载` next to the current loaded count.

**Tech Stack:** React, TypeScript, Vitest, Testing Library.

---

### Task 1: Frontend Total Count Display

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`
- Test: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Add failing frontend assertions**

Update persisted and failed job loading tests to include `total_count` in mocked responses and assert `总任务` plus `未加载`.

- [x] **Step 2: Run frontend focused test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: FAIL because the UI does not render total/unloaded counts.

- [x] **Step 3: Type API total count**

Add `total_count: number` to `DebugJobListResponse`.

- [x] **Step 4: Render total and unloaded counts**

Add `jobListTotalCount` state, set it after batch/import/list loads, and render `总任务`/`未加载`.

- [x] **Step 5: Run frontend focused test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: PASS.

### Task 2: Verification and Checkpoint

**Files:**
- Modify: `docs/superpowers/plans/2026-06-11-frontend-job-list-total-count.md`

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and secret scan**

Run diagnostics and scan for Ark key patterns.

- [x] **Step 3: Commit**

Run:

```bash
git add frontend/src/api/client.ts frontend/src/app/App.tsx frontend/src/app/App.test.tsx docs/superpowers/plans/2026-06-11-frontend-job-list-total-count.md
git commit -m "feat(jobs): show job list total count"
```
