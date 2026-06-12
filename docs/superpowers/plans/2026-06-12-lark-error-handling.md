# Lark Error Handling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use TDD. Implement task-by-task, keep each checkbox updated, and commit after verification.

**Goal:** Convert Lark spreadsheet transport failures into actionable API errors instead of leaking generic 500 responses during real spreadsheet sync/writeback.

**Architecture:** Catch `LarkCliError` at spreadsheet API boundaries and return HTTP 502 with a concise diagnostic message. Keep existing 503 not-configured and 404 missing-resource behavior unchanged.

**Tech Stack:** FastAPI, Python 3.11, pytest.

---

### Task 1: API Error Mapping

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Test: `backend/tests/api/test_spreadsheet_sync.py`
- Test: `backend/tests/api/test_job_report_writeback.py`

- [x] **Step 1: Add failing API tests**

Add tests proving sync and writeback return 502 when the spreadsheet client raises `LarkCliError`.

- [x] **Step 2: Run focused tests for RED**

Run: `python -m pytest tests/api/test_spreadsheet_sync.py tests/api/test_job_report_writeback.py`
Expected: FAIL because `LarkCliError` is not mapped to HTTP 502.

- [x] **Step 3: Implement API error mapping**

Catch `LarkCliError` around sync/writeback client calls and raise `HTTPException(status_code=502, detail=...)`.

- [x] **Step 4: Run focused tests for GREEN**

Run: `python -m pytest tests/api/test_spreadsheet_sync.py tests/api/test_job_report_writeback.py`
Expected: PASS.

### Task 2: Verification and Checkpoint

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 3: Commit**

Commit with message: `fix(api): map lark spreadsheet failures`.
