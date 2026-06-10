# Frontend Batch Job Submission Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a minimal frontend entry point for submitting multiple fixture case ids as debug jobs through the batch API.

**Architecture:** Extend the existing frontend API client with `submitBatchDebugJobs()`, keep the UI state local to `App.tsx`, and render a concise batch summary. This phase does not add batch polling or persistence tables; it only creates jobs and displays immediate submission results.

**Tech Stack:** React 18, TypeScript, Vitest, Testing Library.

---

## File Structure

- `frontend/src/api/client.ts`: add batch request/response types and `submitBatchDebugJobs()`.
- `frontend/src/app/App.tsx`: add textarea, submit button, batch state, and summary rendering.
- `frontend/src/app/App.test.tsx`: verify batch submission request and summary.

## Task 1: Frontend Batch Submission Client And UI

**Files:**
- Modify: `frontend/src/app/App.test.tsx`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`

- [ ] **Step 1: Write failing frontend test**

Extend `App.test.tsx` with a second test that types `handwrite233\nmissing-case`, clicks `Submit batch jobs`, expects fetch to call `/api/debug-jobs/batch` with JSON body `{"case_ids":["handwrite233","missing-case"]}`, and renders `批量创建：1` plus `拒绝：missing-case`.

- [ ] **Step 2: Run focused frontend test**

Run: `npx --yes pnpm@9.15.4 test -- --run src/app/App.test.tsx`

Expected: FAIL because the UI has no batch controls.

- [ ] **Step 3: Implement client**

Add `BatchDebugJobResponse` and `submitBatchDebugJobs(caseIds: string[])` to `client.ts`.

- [ ] **Step 4: Implement UI**

Add textarea state, button handler, and summary rendering in `App.tsx`.

- [ ] **Step 5: Verify focused frontend test**

Run: `npx --yes pnpm@9.15.4 test -- --run src/app/App.test.tsx`

Expected: PASS.

## Task 2: Full Verification And Commit

**Files:**
- Modify only files required by failing checks.

- [ ] **Step 1: Run complete verification**

Run: `powershell -ExecutionPolicy Bypass -File scripts/verify.ps1 -Target all`

Expected: all tests, lint, and type checks pass.

- [ ] **Step 2: Inspect and commit**

Run: `git status --short`, scan for secrets, then commit the intended files with a conventional commit.
