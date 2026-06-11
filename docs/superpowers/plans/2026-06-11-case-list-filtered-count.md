# Case List Filtered Count Implementation Plan

> **For agentic workers:** Use TDD. Preserve `total_count` for all imported cases and add `filtered_count` for the active query.

**Goal:** Make region-filtered Imported Cases counts and load-more behavior accurate.

**Architecture:** Add `filtered_count` to `/cases` responses after applying `has_regions` but before `offset`/`limit`. Update frontend types and use `filtered_count` as the effective visible denominator, while still displaying `total_count` as all imported cases.

**Tech Stack:** FastAPI, React, TypeScript, pytest, Vitest.

---

### Task 1: Backend Filtered Count

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Test: `backend/tests/api/test_case_listing.py`

- [x] **Step 1: Add failing backend filtered-count test**

Assert `/cases?has_regions=true&limit=1` returns `filtered_count` equal to the filtered set size and `total_count` remains all imported cases.

- [x] **Step 2: Run focused backend test**

Run: `python -m pytest backend/tests/api/test_case_listing.py -q`
Expected: FAIL because `filtered_count` is missing.

- [x] **Step 3: Implement backend filtered count**

Compute `filtered_count` after `has_regions` filtering and before paging.

- [x] **Step 4: Run focused backend test**

Run: `python -m pytest backend/tests/api/test_case_listing.py -q`
Expected: PASS.

### Task 2: Frontend Filtered Count

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`
- Test: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Add failing frontend filtered-count assertions**

Assert region-filtered views show the filtered denominator and no false unloaded count when `filtered_count` equals loaded cases.

- [x] **Step 2: Run focused frontend test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: FAIL because frontend still uses `total_count`.

- [x] **Step 3: Implement frontend filtered count**

Store `filtered_count` and use it for displayed/loaded calculations.

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

Commit with message: `feat(cases): report filtered case count`.
