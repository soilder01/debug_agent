# Case List Limit Implementation Plan

> **For agentic workers:** Use TDD. `limit` must bound returned rows without changing `total_count`.

**Goal:** Prevent large imported-case datasets from being loaded into the frontend all at once.

**Architecture:** Add optional `limit` to `/cases`, applied after `has_regions` filtering while `total_count` remains the pre-filter total. Extend frontend `fetchCases()` with `limit` and default Imported Cases loading to 50 rows.

**Tech Stack:** FastAPI, React, TypeScript, pytest, Vitest.

---

### Task 1: Backend Limit

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Test: `backend/tests/api/test_case_listing.py`

- [x] **Step 1: Add failing backend limit test**

Assert `GET /cases?limit=1` returns one case and preserves a larger `total_count`.

- [x] **Step 2: Run focused backend test**

Run: `python -m pytest backend/tests/api/test_case_listing.py -q`
Expected: FAIL because `/cases` ignores `limit`.

- [x] **Step 3: Implement backend limit**

Apply `limit` after optional region filtering.

- [x] **Step 4: Run focused backend test**

Run: `python -m pytest backend/tests/api/test_case_listing.py -q`
Expected: PASS.

### Task 2: Frontend Default Limit

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`
- Test: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Add failing frontend request assertions**

Assert case loading calls `/api/cases?limit=50` and region filtering calls `/api/cases?has_regions=true&limit=50`.

- [x] **Step 2: Run focused frontend test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: FAIL because frontend does not pass `limit`.

- [x] **Step 3: Implement frontend limit**

Add a `caseListLimit` constant and include it in `fetchCases`.

- [x] **Step 4: Run focused frontend test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: PASS.

- [x] **Step 5: Show unloaded case count**

Render the unloaded imported-case count when `total_count` is larger than the returned case list.

### Task 3: Verification and Checkpoint

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 3: Commit**

Commit with message: `feat(cases): limit case list results`.
