# Job List Sort Implementation Plan

> **For agentic workers:** Use TDD. Job history should support newest-first browsing without changing existing default order.

**Goal:** Let operators quickly inspect the latest debug jobs in large queues.

**Architecture:** Add optional `sort=created_at_desc` to `/jobs`, forward it to repository ordering, extend frontend `fetchDebugJobs()` with sort, and add a "Load newest debug jobs" action that preserves pagination with the active sort.

**Tech Stack:** FastAPI, SQLAlchemy, React, TypeScript, pytest, Vitest.

---

### Task 1: Backend Sort

**Files:**
- Modify: `backend/src/debug_agent/storage/repository.py`
- Modify: `backend/src/debug_agent/api/routes.py`
- Test: `backend/tests/api/test_job_listing.py`

- [x] **Step 1: Add failing backend sort test**

Assert `GET /jobs?sort=created_at_desc&limit=2` returns jobs ordered by `created_at` descending.

- [x] **Step 2: Run focused backend test**

Run: `python -m pytest backend/tests/api/test_job_listing.py -q`
Expected: FAIL because `/jobs` ignores `sort`.

- [x] **Step 3: Implement backend sort**

Support default ascending order and `created_at_desc`.

- [x] **Step 4: Run focused backend test**

Run: `python -m pytest backend/tests/api/test_job_listing.py -q`
Expected: PASS.

### Task 2: Frontend Newest Action

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`
- Test: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Add failing frontend newest-first test**

Assert "Load newest debug jobs" requests `/api/jobs?limit=50&sort=created_at_desc`.

- [x] **Step 2: Run focused frontend test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: FAIL because the action does not exist.

- [x] **Step 3: Implement frontend newest action**

Extend API query builder, add active sort state, and add the newest-first button.

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

Commit with message: `feat(jobs): sort job history`.
