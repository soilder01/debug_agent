# Frontend Five Replay Submit Implementation Plan

> **For agentic workers:** Use TDD. The UI should use the persisted backend replay-count contract instead of relying on hidden defaults.

**Goal:** Make single-case debug submissions from the frontend run the standard five baseline replays used by the handwriting OCR workflow.

**Architecture:** Extend `submitDebugJob()` with a default `baselineTrials=5`, encode it into the debug-job URL, and keep existing auto-run behavior.

**Tech Stack:** React, TypeScript, Vitest, Testing Library.

---

### Task 1: Frontend Submit Contract

**Files:**
- Modify: `frontend/src/api/client.ts`
- Test: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Add failing frontend submit tests**

Assert single-case submit and selected-case submit call `/debug-jobs?auto_run=true&baseline_trials=5`.

- [x] **Step 2: Run focused frontend tests**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: FAIL because the frontend does not send `baseline_trials=5`.

- [x] **Step 3: Implement frontend default replay count**

Add `baselineTrials=5` to `submitDebugJob()` and generate the query string with `URLSearchParams`.

- [x] **Step 4: Run focused frontend tests**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: PASS.

### Task 2: Verification and Checkpoint

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 3: Commit**

Commit with message: `feat(frontend): submit five replay jobs`.
