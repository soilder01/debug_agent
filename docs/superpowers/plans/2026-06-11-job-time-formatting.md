# Job Time Formatting Implementation Plan

> **For agentic workers:** Use TDD. Display readable local timestamps while preserving raw ISO values for audit.

**Goal:** Make job history timestamps easier for operators to read without losing exact machine-readable audit data.

**Architecture:** Add a small frontend formatting helper for job timestamps. Render formatted local time in the batch triage list and preserve the original ISO timestamp in a `title` attribute.

**Tech Stack:** React, TypeScript, Vitest, Testing Library.

---

### Task 1: Frontend Time Formatting

**Files:**
- Modify: `frontend/src/app/App.tsx`
- Test: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Add failing frontend formatting assertion**

Assert a job list row shows formatted `YYYY-MM-DD HH:mm:ss` and keeps the raw ISO value in `title`.

- [x] **Step 2: Run focused frontend test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: FAIL because the UI currently renders raw ISO text directly.

- [x] **Step 3: Implement timestamp formatter**

Add a small formatter using local `Date` fields and fall back to the raw string for invalid timestamps.

- [x] **Step 4: Run focused frontend test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: PASS.

### Task 2: Verification and Checkpoint

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 3: Commit**

Commit with message: `feat(jobs): format job timestamps`.
