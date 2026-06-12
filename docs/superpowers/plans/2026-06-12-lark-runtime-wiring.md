# Lark Runtime Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use TDD. Implement task-by-task, keep each checkbox updated, and commit after verification.

**Goal:** Automatically wire the real Lark spreadsheet client into API runtime when Lark spreadsheet configuration is present, while preserving safe 503 behavior when not configured.

**Architecture:** Add a small API-layer configuration function that reads `LarkSpreadsheetSettings`, creates `LarkSpreadsheetClient(LarkCliSheetsTransport())`, and assigns the same client to sync and writeback globals. Keep credentials outside source control by relying on local `lark-cli` auth/config.

**Tech Stack:** FastAPI, Python 3.11, pytest, mypy strict, ruff.

---

### Task 1: Runtime Client Wiring

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Test: `backend/tests/api/test_spreadsheet_client_configuration.py`

- [x] **Step 1: Add failing configuration test**

Add tests proving configured Lark settings wire sync/writeback clients and missing settings leave them unset.

- [x] **Step 2: Run backend test for RED**

Run: `python -m pytest tests/api/test_spreadsheet_client_configuration.py`
Expected: FAIL because `configure_spreadsheet_clients` does not exist.

- [x] **Step 3: Implement runtime wiring**

Add `configure_spreadsheet_clients()` and call it during module import after client globals are initialized.

- [x] **Step 4: Run backend test for GREEN**

Run: `python -m pytest tests/api/test_spreadsheet_client_configuration.py`
Expected: PASS.

### Task 2: Verification and Checkpoint

- [x] **Step 1: Run focused API tests**

Run: `python -m pytest tests/api/test_spreadsheet_client_configuration.py tests/api/test_spreadsheet_sync.py tests/api/test_job_report_writeback.py`
Expected: PASS.

- [x] **Step 2: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 3: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 4: Commit**

Commit with message: `feat(api): wire lark spreadsheet client`.
