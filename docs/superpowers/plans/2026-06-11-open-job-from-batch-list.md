# Open Job From Batch List Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow operators to open a loaded batch/history job in the Job Status detail panel and then inspect job-scoped evidence.

**Architecture:** Reuse the existing `submittedJob`/`jobStatus` detail panel state. Add an `Open job <id>` button to each batch list item; selecting a full `DebugJobStatus` sets `jobStatus` and clears the current evidence selection.

**Tech Stack:** React, TypeScript, Vitest, Testing Library.

---

### Task 1: Open Batch Job Detail

**Files:**
- Modify: `frontend/src/app/App.tsx`
- Test: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Add failing frontend assertion**

Extend the persisted jobs test to click `Open job job-history-1` and assert the Job Status panel renders `Job ID：job-history-1` plus the recommendation action.

- [x] **Step 2: Run frontend focused test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: FAIL because the open button does not exist.

- [x] **Step 3: Implement open action**

Add `openBatchJob(job)` to set `submittedJob`, set `jobStatus` for full statuses, clear report and evidence, and render `Open job <id>` buttons in the batch list.

- [x] **Step 4: Run frontend focused test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: PASS.

### Task 2: Verification and Checkpoint

**Files:**
- Modify: `docs/superpowers/plans/2026-06-11-open-job-from-batch-list.md`

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and secret scan**

Run diagnostics and scan for Ark key patterns.

- [x] **Step 3: Commit**

Run:

```bash
git add frontend/src/app/App.tsx frontend/src/app/App.test.tsx docs/superpowers/plans/2026-06-11-open-job-from-batch-list.md
git commit -m "feat(jobs): open batch job details"
```
