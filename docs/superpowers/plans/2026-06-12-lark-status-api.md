# Lark Spreadsheet Status API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use TDD. Implement task-by-task, keep each checkbox updated, and commit after verification.

**Goal:** Expose a read-only API that lets operators verify whether Lark spreadsheet sync/writeback is configured and optionally test connectivity before running imports.

**Architecture:** Store the active `LarkSpreadsheetSettings` during API client configuration. Add `GET /spreadsheets/lark/status` returning configured reference and timeout. When `check_connectivity=true`, call the configured spreadsheet sync client with the reference and report `ok` or `failed` without creating jobs or writing data.

**Tech Stack:** FastAPI, Python 3.11, pytest, mypy strict, ruff.

---

### Task 1: Lark Status Endpoint

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Test: `backend/tests/api/test_spreadsheet_client_configuration.py`

- [x] **Step 1: Add failing status tests**

Add tests for unconfigured status, configured status, successful connectivity check, and failed connectivity check.

- [x] **Step 2: Run focused tests for RED**

Run: `python -m pytest tests/api/test_spreadsheet_client_configuration.py`
Expected: FAIL because the status endpoint does not exist.

- [x] **Step 3: Implement status endpoint**

Persist active Lark settings, add response model, and implement optional connectivity check with safe error mapping.

- [x] **Step 4: Run focused tests for GREEN**

Run: `python -m pytest tests/api/test_spreadsheet_client_configuration.py`
Expected: PASS.

### Task 2: Verification and Checkpoint

- [x] **Step 1: Run focused API tests**

Run: `python -m pytest tests/api/test_spreadsheet_client_configuration.py tests/api/test_spreadsheet_sync.py`
Expected: PASS.

- [x] **Step 2: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 3: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 4: Commit**

Commit with message: `feat(api): expose lark spreadsheet status`.
