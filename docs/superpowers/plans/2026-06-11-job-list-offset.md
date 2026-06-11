# Job List Offset Implementation Plan

> **For agentic workers:** Use TDD. Job history lists must support loading pages beyond the initial limit.

**Goal:** Let operators continue browsing debug-job history after the first 50 rows.

**Architecture:** Add optional `offset` to repository/API job listing. Extend frontend `fetchDebugJobs()` with `offset`, preserve the active status filter, and append subsequent pages via "Load more debug jobs".

**Tech Stack:** FastAPI, SQLAlchemy, React, TypeScript, pytest, Vitest.

---

### Task 1: Backend Job Offset

**Files:**
- Modify: `backend/src/debug_agent/storage/repository.py`
- Modify: `backend/src/debug_agent/api/routes.py`
- Test: `backend/tests/api/test_job_listing.py`

- [x] **Step 1: Add failing backend offset test**

Assert `GET /jobs?offset=1&limit=1` returns the second item from the same ordered job list and preserves `total_count`.

- [x] **Step 2: Run focused backend test**

Run: `python -m pytest backend/tests/api/test_job_listing.py -q`
Expected: FAIL because `/jobs` ignores `offset`.

- [x] **Step 3: Implement backend offset**

Apply offset before limit in repository job listing and expose it through `/jobs`.

- [x] **Step 4: Run focused backend test**

Run: `python -m pytest backend/tests/api/test_job_listing.py -q`
Expected: PASS.

### Task 2: Frontend Load More Jobs

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`
- Test: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Add failing frontend load-more test**

Assert "Load more debug jobs" requests `/api/jobs?limit=50&offset=1` and appends returned jobs.

- [x] **Step 2: Run focused frontend test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: FAIL because the button/action does not exist.

- [x] **Step 3: Implement frontend load more**

Track active status filter, request offset by loaded job count, and append returned jobs.

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

Commit with message: `feat(jobs): page job history`.
