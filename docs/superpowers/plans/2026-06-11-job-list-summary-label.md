# Job List Summary Label Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Batch Jobs summary label accurately distinguish newly created batch jobs from loaded historical queue jobs.

**Architecture:** Add a small UI state that stores the current job list summary label. Batch/import flows keep `批量创建`; persisted job loading uses `队列任务`; failed-job loading uses `失败任务`.

**Tech Stack:** React, TypeScript, Vitest, Testing Library.

---

### Task 1: Accurate Job List Label

**Files:**
- Modify: `frontend/src/app/App.tsx`
- Test: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Add failing frontend assertions**

Update persisted job loading tests to expect `队列任务：1` and failed job loading tests to expect `失败任务：1`.

- [x] **Step 2: Run frontend focused test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: FAIL because the UI still renders `批量创建`.

- [x] **Step 3: Implement summary label state**

Add `jobListSummaryLabel`, set it in submit/import/load flows, and render `{jobListSummaryLabel}：{batchResult.jobs.length}`.

- [x] **Step 4: Run frontend focused test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: PASS.

### Task 2: Verification and Checkpoint

**Files:**
- Modify: `docs/superpowers/plans/2026-06-11-job-list-summary-label.md`

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and secret scan**

Run diagnostics and scan for Ark key patterns.

- [x] **Step 3: Commit**

Run:

```bash
git add frontend/src/app/App.tsx frontend/src/app/App.test.tsx docs/superpowers/plans/2026-06-11-job-list-summary-label.md
git commit -m "fix(jobs): label loaded job queues"
```
