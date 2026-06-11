# Batch List Evidence Shortcut Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow operators to open job-scoped evidence directly from the loaded batch/history job list.

**Architecture:** Render evidence shortcuts under each batch job when `evidence_ids` are available. Add a dedicated `selectBatchJobEvidence(jobId, evidenceId)` function that calls the existing job-scoped evidence API without requiring the job to be opened first.

**Tech Stack:** React, TypeScript, Vitest, Testing Library.

---

### Task 1: Batch Evidence Shortcut

**Files:**
- Modify: `frontend/src/app/App.tsx`
- Test: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Add failing frontend assertion**

Update the persisted jobs test with an `evidence_ids` value, click `Open evidence <evidence_id> for job <job_id>`, assert `/api/jobs/<job_id>/evidence/<encoded_evidence_id>` is called, and assert evidence detail renders.

- [x] **Step 2: Run frontend focused test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: FAIL because the batch list has no direct evidence shortcut.

- [x] **Step 3: Implement direct evidence selection**

Add `selectBatchJobEvidence(jobId, evidenceId)` and render evidence shortcut buttons for each listed job.

- [x] **Step 4: Run frontend focused test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: PASS.

### Task 2: Verification and Checkpoint

**Files:**
- Modify: `docs/superpowers/plans/2026-06-11-batch-list-evidence-shortcut.md`

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and secret scan**

Run diagnostics and scan for Ark key patterns.

- [x] **Step 3: Commit**

Run:

```bash
git add frontend/src/app/App.tsx frontend/src/app/App.test.tsx docs/superpowers/plans/2026-06-11-batch-list-evidence-shortcut.md
git commit -m "feat(jobs): open evidence from batch list"
```
