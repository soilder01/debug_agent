# Batch Retry Guidance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show retry guidance directly in the batch job list so operators can triage many jobs without opening each job detail.

**Architecture:** Reuse `retry_recommendation_detail` already returned by job status polling. The batch list renders the human-readable label and severity when available, with graceful fallback for newly submitted jobs that have not been polled yet.

**Tech Stack:** React, TypeScript, Vitest, Testing Library.

---

### Task 1: Batch List Guidance

**Files:**
- Modify: `frontend/src/app/App.tsx`
- Test: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Add failing frontend assertion**

In the batch polling test, include `retry_recommendation_detail` in mocked job status responses and assert that the batch list shows:

```typescript
expect(screen.getByText("job-2 建议：重试预算已耗尽")).toBeInTheDocument();
expect(screen.getByText("job-2 级别：critical")).toBeInTheDocument();
```

- [x] **Step 2: Run frontend focused test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: FAIL because the batch list does not render retry guidance.

- [x] **Step 3: Implement batch list rendering**

Render `job.retry_recommendation_detail.label` and `job.retry_recommendation_detail.severity` when present.

- [x] **Step 4: Run frontend focused test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: PASS.

### Task 2: Verification and Checkpoint

**Files:**
- Modify: `docs/superpowers/plans/2026-06-11-batch-retry-guidance.md`

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and secret scan**

Run diagnostics and scan for Ark key patterns.

- [x] **Step 3: Commit**

Run:

```bash
git add frontend/src/app/App.tsx frontend/src/app/App.test.tsx docs/superpowers/plans/2026-06-11-batch-retry-guidance.md
git commit -m "feat(jobs): show batch retry guidance"
```
