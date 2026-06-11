# Server Filter Cases With Regions Implementation Plan

> **For agentic workers:** Use TDD. Filter only by explicit `box_regions`; do not infer coordinate readiness from prompts or answers.

**Goal:** Move region-ready case filtering to the `/cases` API so large imported datasets can be narrowed before frontend rendering.

**Architecture:** Add optional `has_regions` query parameter to `/cases`. When `true`, return only cases with at least one `box_regions` entry. Update frontend `fetchCases()` to pass this parameter and wire the existing region filter button to reload from the server.

**Tech Stack:** FastAPI, Pydantic, React, TypeScript, pytest, Vitest.

---

### Task 1: Backend API Filter

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Test: `backend/tests/api/test_case_listing.py`

- [x] **Step 1: Add failing backend API test**

Assert `GET /cases?has_regions=true` returns only imported cases with `box_region_count > 0`.

- [x] **Step 2: Run focused backend test**

Run: `python -m pytest backend/tests/api/test_case_listing.py -q`
Expected: FAIL because `/cases` ignores `has_regions`.

- [x] **Step 3: Implement backend query filter**

Add optional `has_regions` query parameter and filter summaries by `len(case.box_regions) > 0`.

- [x] **Step 4: Run focused backend test**

Run: `python -m pytest backend/tests/api/test_case_listing.py -q`
Expected: PASS.

### Task 2: Frontend Server Filter

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`
- Test: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Add failing frontend API assertion**

Assert clicking `Only cases with regions` calls `/api/cases?has_regions=true` and renders the filtered response.

- [x] **Step 2: Run focused frontend test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: FAIL because the frontend currently filters in memory.

- [x] **Step 3: Implement frontend server-side filter call**

Extend `fetchCases(hasRegions?: boolean)` and call it from the filter buttons.

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

Commit with message: `feat(cases): filter region-ready cases in api`.
