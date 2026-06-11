# Filter Cases With Regions Implementation Plan

> **For agentic workers:** Use TDD. Filter only by explicit `box_region_count`; do not infer region readiness from other fields.

**Goal:** Let users quickly narrow imported cases to samples that have answer-box coordinates, then use that visible subset for batch debug jobs.

**Architecture:** Add frontend state for a region-only case filter. Derive visible imported cases from `importedCases` and `box_region_count`. Render toggle buttons and make "Use imported cases for batch" copy the visible list.

**Tech Stack:** React, TypeScript, Vitest, Testing Library.

---

### Task 1: Region-Ready Case Filter

**Files:**
- Modify: `frontend/src/app/App.tsx`
- Test: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Add failing frontend assertion**

Assert clicking "Only cases with regions" hides zero-region cases and batch copy uses only visible cases.

- [x] **Step 2: Run focused frontend test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: FAIL because the filter button does not exist.

- [x] **Step 3: Implement region-only filter**

Add filter state, visible case derivation, toggle buttons, and batch copy from visible cases.

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

Commit with message: `feat(frontend): filter region-ready cases`.
