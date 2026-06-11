# Repository Case Pagination Implementation Plan

> **For agentic workers:** Use TDD. Paging and filtering should avoid parsing non-returned case JSON.

**Goal:** Make imported-case listing scale better for large datasets by pushing pagination into repository queries.

**Architecture:** Extend `DebugJobRepository.list_cases()` with `has_regions`, `limit`, and `offset`. Add count helpers for all cases and filtered cases. Persist `box_region_count` on `DebugCaseRow` so region filtering can happen in SQL instead of deserializing every case JSON.

**Tech Stack:** SQLAlchemy, SQLite, FastAPI, pytest.

---

### Task 1: Repository Paging Contract

**Files:**
- Modify: `backend/src/debug_agent/storage/models.py`
- Modify: `backend/src/debug_agent/storage/repository.py`
- Test: `backend/tests/storage/test_repository.py`

- [x] **Step 1: Add failing repository paging test**

Assert `list_cases(limit=1, offset=1)` returns the second case and does not parse a deliberately invalid first-page row.

- [x] **Step 2: Run focused repository test**

Run: `python -m pytest backend/tests/storage/test_repository.py -q`
Expected: FAIL because `list_cases()` has no paging parameters.

- [x] **Step 3: Implement repository paging**

Add `limit` and `offset` to the SQL query before parsing rows.

- [x] **Step 4: Run focused repository test**

Run: `python -m pytest backend/tests/storage/test_repository.py -q`
Expected: PASS.

### Task 2: Repository Region Counts

**Files:**
- Modify: `backend/src/debug_agent/storage/models.py`
- Modify: `backend/src/debug_agent/storage/repository.py`
- Test: `backend/tests/storage/test_repository.py`

- [x] **Step 1: Add failing repository region-filter/count test**

Assert `list_cases(has_regions=True)` and `count_cases(has_regions=True)` use stored region counts.

- [x] **Step 2: Run focused repository test**

Run: `python -m pytest backend/tests/storage/test_repository.py -q`
Expected: FAIL until region count is persisted and queried.

- [x] **Step 3: Implement region count storage**

Persist `box_region_count` and query/count by that field.

- [x] **Step 4: Run focused repository test**

Run: `python -m pytest backend/tests/storage/test_repository.py -q`
Expected: PASS.

### Task 3: API Wiring

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Test: `backend/tests/api/test_case_listing.py`

- [x] **Step 1: Wire API to repository paging/counts**

Use repository `count_cases()` and paged `list_cases()` in `/cases`.

- [x] **Step 2: Run focused API test**

Run: `python -m pytest backend/tests/api/test_case_listing.py -q`
Expected: PASS.

### Task 4: Verification and Checkpoint

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 3: Commit**

Commit with message: `feat(cases): page cases in repository`.
