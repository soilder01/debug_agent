# Frontend Case Box Regions Implementation Plan

> **For agentic workers:** Use TDD. Display only region metadata returned by the API; do not infer missing coordinates.

**Goal:** Let users inspect imported case answer-box regions in the frontend case detail panel, so CSV/JSONL region data is visible before launching debug jobs.

**Architecture:** Extend the frontend `DebugCaseDetail` type with optional `box_regions`, and render a region list in the selected case detail section.

**Tech Stack:** React, TypeScript, Vitest, Testing Library.

---

### Task 1: Case Detail Region Display

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`
- Test: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Add failing frontend assertion**

Update imported case detail test to include `box_regions` in the mocked response and assert the region is displayed.

- [x] **Step 2: Run focused frontend test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: FAIL because the detail panel does not render regions.

- [x] **Step 3: Implement type and rendering**

Add `box_regions` to `DebugCaseDetail` and render region rows under the selected case detail.

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

Commit with message: `feat(frontend): show case box regions`.
