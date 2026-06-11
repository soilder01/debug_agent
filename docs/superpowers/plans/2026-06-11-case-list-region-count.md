# Case List Region Count Implementation Plan

> **For agentic workers:** Use TDD. Count only explicit `box_regions` returned from stored cases.

**Goal:** Show whether imported cases include answer-box regions directly in the case list, so users can triage which samples are ready for localized visual debugging.

**Architecture:** Add `box_region_count` to backend `DebugCaseSummary`, populate it from `len(case.box_regions)`, mirror it in the frontend `DebugCaseSummary`, and render it in the imported case list.

**Tech Stack:** FastAPI, Pydantic, React, TypeScript, pytest, Vitest.

---

### Task 1: Backend Case Summary Count

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Test: `backend/tests/api/test_case_listing.py`

- [x] **Step 1: Add failing backend assertion**

Assert `/cases` summaries include `box_region_count`.

- [x] **Step 2: Run focused backend test**

Run: `python -m pytest backend/tests/api/test_case_listing.py -q`
Expected: FAIL because summaries do not include the field.

- [x] **Step 3: Implement backend summary field**

Add `box_region_count` and populate it from each case.

- [x] **Step 4: Run focused backend test**

Run: `python -m pytest backend/tests/api/test_case_listing.py -q`
Expected: PASS.

### Task 2: Frontend Case List Display

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`
- Test: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Add failing frontend assertion**

Assert imported case summaries render the region count.

- [x] **Step 2: Run focused frontend test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: FAIL because the list does not render region counts.

- [x] **Step 3: Implement frontend type and rendering**

Add `box_region_count` and display it next to each case summary.

- [x] **Step 4: Run focused frontend test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: PASS.

### Task 3: Verification and Checkpoint

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 3: Commit**

Commit with message: `feat(cases): show box region counts`.
