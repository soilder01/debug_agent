# Job Timestamps Implementation Plan

> **For agentic workers:** Use TDD. Job history should be ordered by creation time and expose timestamps for operators.

**Goal:** Make debug-job history more auditable and easier to browse by persisting and showing creation/update times.

**Architecture:** Add `created_at` and `updated_at` to `DebugJobRow`, populate on creation, update on status transitions/retry release, migrate legacy tables, order job listing by `created_at` then `job_id`, expose timestamps in API responses, and render them in the frontend job list/status data.

**Tech Stack:** SQLAlchemy, SQLite, FastAPI, React, TypeScript, pytest, Vitest.

---

### Task 1: Storage Timestamps

**Files:**
- Modify: `backend/src/debug_agent/storage/models.py`
- Modify: `backend/src/debug_agent/storage/repository.py`
- Modify: `backend/src/debug_agent/storage/database.py`
- Test: `backend/tests/storage/test_repository.py`

- [x] **Step 1: Add failing storage timestamp tests**

Assert new jobs get timestamps, status updates move `updated_at`, legacy schema gets timestamp columns, and job listing orders by `created_at`.

- [x] **Step 2: Run focused storage test**

Run: `python -m pytest backend/tests/storage/test_repository.py -q`
Expected: FAIL because timestamp columns do not exist.

- [x] **Step 3: Implement storage timestamps**

Persist and update ISO timestamps, migrate legacy tables, and order lists by `created_at`.

- [x] **Step 4: Run focused storage test**

Run: `python -m pytest backend/tests/storage/test_repository.py -q`
Expected: PASS.

### Task 2: API Contract

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Test: `backend/tests/api/test_job_listing.py`

- [x] **Step 1: Add failing API timestamp assertions**

Assert `/jobs` response includes `created_at` and `updated_at`.

- [x] **Step 2: Run focused API test**

Run: `python -m pytest backend/tests/api/test_job_listing.py -q`
Expected: FAIL until API schema maps timestamp fields.

- [x] **Step 3: Implement API timestamp fields**

Add timestamp fields to `DebugJobStatus`.

- [x] **Step 4: Run focused API test**

Run: `python -m pytest backend/tests/api/test_job_listing.py -q`
Expected: PASS.

### Task 3: Frontend Display

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/app/App.tsx`
- Test: `frontend/src/app/App.test.tsx`

- [x] **Step 1: Add failing frontend timestamp assertion**

Assert loaded job history renders created/updated time for each job.

- [x] **Step 2: Run focused frontend test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: FAIL until timestamps are rendered.

- [x] **Step 3: Implement frontend timestamp display**

Add timestamp fields to frontend types and render them in job list items.

- [x] **Step 4: Run focused frontend test**

Run: `npx --yes pnpm@9.15.4 --dir frontend test -- --run src/app/App.test.tsx`
Expected: PASS.

### Task 4: Verification and Checkpoint

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 3: Commit**

Commit with message: `feat(jobs): expose job timestamps`.
