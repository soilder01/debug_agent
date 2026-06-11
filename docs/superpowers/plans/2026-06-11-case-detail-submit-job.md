# Case Detail Submit Job Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Let users create a debug job directly from the selected case detail panel.

**Architecture:** Reuse the existing `submitDebugJob(caseId)` frontend client. Add a selected-case action in `App.tsx` that submits the currently opened case, updates the existing single-job status panel state, and clears stale report/evidence state.

**Tech Stack:** React 18, TypeScript, Vite, Vitest, Testing Library.

---

## File Structure

- Modify `frontend/src/app/App.tsx`: add a detail-level job submit handler and button.
- Modify `frontend/src/app/App.test.tsx`: add a focused test covering detail-to-job handoff.
- Create `docs/superpowers/plans/2026-06-11-case-detail-submit-job.md`: this plan.

## Task 1: Detail-To-Job Handoff

**Files:**
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Write failing test**

Add a test that loads imported cases, opens one case detail, clicks `Create debug job for case-list-1`, and verifies `POST /api/cases/case-list-1/debug-jobs?auto_run=true` plus rendered job status.

- [x] **Step 2: Run failing test**

Run:

```powershell
npx --yes pnpm@9.15.4 test -- --run src/app/App.test.tsx
```

Expected: FAIL because the detail-level submit button does not exist.

- [x] **Step 3: Implement handler and button**

Add `submitSelectedCaseJob(caseId)` in `App.tsx` and render a button in the selected case detail panel.

- [x] **Step 4: Run focused tests and typecheck**

Run:

```powershell
npx --yes pnpm@9.15.4 test -- --run src/app/App.test.tsx
npx --yes pnpm@9.15.4 typecheck
```

Expected: PASS.

## Task 2: Full Verification And Commit

**Files:**
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/app/App.test.tsx`
- Create: `docs/superpowers/plans/2026-06-11-case-detail-submit-job.md`

- [x] **Step 1: Run full verification**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1 -Target all
```

Expected: backend tests, frontend tests, lint, and typecheck all pass.

- [x] **Step 2: Run diagnostics and secret scan**

Run diagnostics and scan edited files for Ark key patterns.

- [x] **Step 3: Commit**

Run:

```powershell
git add frontend/src/app/App.tsx frontend/src/app/App.test.tsx docs/superpowers/plans/2026-06-11-case-detail-submit-job.md
git commit -m "feat(frontend): submit job from case detail"
```

Expected: one commit containing only Phase 29 changes.

## Self-Review

- Spec coverage: The plan connects selected case detail to existing job execution and status rendering.
- Placeholder scan: No TBD or TODO remains.
- Type consistency: The implementation uses existing `submitDebugJob` and `SubmittedDebugJob`.
