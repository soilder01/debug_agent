# Case List Total Count Implementation Plan

> **For agentic workers:** Use TDD. `total_count` must represent all imported cases before optional filters.

**Goal:** Preserve total imported-case visibility when `/cases?has_regions=true` returns a filtered subset, so the frontend can display `shown/total`.

**Architecture:** Add `total_count` to `DebugCaseListResponse`. Compute it from all loaded cases before applying `has_regions`. Store the total in frontend state and render `已显示样本：returned/total`.

**Tech Stack:** FastAPI, Pydantic, React, TypeScript, pytest, Vitest.

---

### Task 1: Backend Total Count

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Test: `backend/tests/api/test_case_listing.py`

- [x] **Step 1: Add failing backend assertion**

Assert `/cases?has_regions=true` includes `total_count` and that it remains larger than the filtered result when zero-region cases exist.

- [x] **Step 2: Run focused backend test**

Run: `python -m pytest backend/tests/api/test_case_listing.py -q`
Expected: FAIL because the response has no `total_count`.

- [x] **Step 3: Implement backend total count**

Add `total_count` to the response and compute it before filtering.

- [x] **Step 4: Run focused backend test**

Run: `python -m pytest backend/tests/api/test_case_listing.py -q`
Expected: PASS.

### Task 2: Frontend Display

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`
- Test: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Add failing frontend assertion**

Assert filtered case loading displays `已显示样本：1/2` using the API `total_count`.

- [x] **Step 2: Run focused frontend test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: FAIL because the frontend displays `1/1`.

- [x] **Step 3: Implement frontend total count state**

Add `total_count` to the response type, persist it in state, and render shown/total.

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

Commit with message: `feat(cases): include case list total count`.
