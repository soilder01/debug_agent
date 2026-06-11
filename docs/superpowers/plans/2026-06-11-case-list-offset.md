# Case List Offset Implementation Plan

> **For agentic workers:** Use TDD. `offset` must page imported cases without changing `total_count`.

**Goal:** Let operators continue browsing imported cases after the first bounded page.

**Architecture:** Add optional `offset` to `/cases`, applied after optional `has_regions` filtering and before `limit` slicing. Extend frontend `fetchCases()` with `offset`, track the active region filter, and append additional pages through a "Load more imported cases" action.

**Tech Stack:** FastAPI, React, TypeScript, pytest, Vitest.

---

### Task 1: Backend Offset

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Test: `backend/tests/api/test_case_listing.py`

- [x] **Step 1: Add failing backend offset test**

Assert `GET /cases?offset=1&limit=1` returns the second item from the same ordered list while preserving `total_count`.

- [x] **Step 2: Run focused backend test**

Run: `python -m pytest backend/tests/api/test_case_listing.py -q`
Expected: FAIL because `/cases` ignores `offset`.

- [x] **Step 3: Implement backend offset**

Apply `offset` before `limit` slicing.

- [x] **Step 4: Run focused backend test**

Run: `python -m pytest backend/tests/api/test_case_listing.py -q`
Expected: PASS.

### Task 2: Frontend Load More

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`
- Test: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Add failing frontend load-more test**

Assert the second request calls `/api/cases?limit=50&offset=2` in the test fixture and appends the returned cases.

- [x] **Step 2: Run focused frontend test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: FAIL because no load-more action exists.

- [x] **Step 3: Implement frontend load more**

Add `offset` support in `fetchCases()` and append subsequent pages while preserving the active region filter.

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

Commit with message: `feat(cases): page imported cases`.
