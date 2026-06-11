# Job Sort Validation Implementation Plan

> **For agentic workers:** Use TDD. API query parameters should fail loudly when clients send unsupported values.

**Goal:** Prevent invalid `/jobs?sort=...` values from being silently treated as default ascending order.

**Architecture:** Restrict the FastAPI `sort` query parameter to known values and keep repository behavior compatible for internal callers.

**Tech Stack:** FastAPI, pytest, Python typing.

---

### Task 1: API Sort Validation

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Test: `backend/tests/api/test_job_listing.py`

- [x] **Step 1: Add failing invalid-sort test**

Assert `GET /jobs?sort=unknown` returns HTTP 422.

- [x] **Step 2: Run focused backend test**

Run: `python -m pytest backend/tests/api/test_job_listing.py -q`
Expected: FAIL because unknown sort is currently accepted.

- [x] **Step 3: Implement sort whitelist**

Use typed query validation for `created_at_asc` and `created_at_desc`.

- [x] **Step 4: Run focused backend test**

Run: `python -m pytest backend/tests/api/test_job_listing.py -q`
Expected: PASS.

### Task 2: Verification and Checkpoint

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 3: Commit**

Commit with message: `fix(jobs): validate job sort parameter`.
