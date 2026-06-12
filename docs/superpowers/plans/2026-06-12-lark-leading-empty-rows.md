# Lark Leading Empty Rows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use TDD. Implement task-by-task, keep each checkbox updated, and commit after verification.

**Goal:** Make Lark spreadsheet sync/writeback robust when a worksheet has blank rows before the header row.

**Architecture:** Keep the transport value matrix unchanged, but teach `LarkSpreadsheetClient` to choose the first non-empty matrix row as headers and preserve sheet row ids from that offset. Teach `LarkCliSheetsTransport` writeback header lookup to use the first non-empty rows-json row, not physical row 1.

**Tech Stack:** Python 3.11, pytest, mypy strict, ruff.

---

### Task 1: Skip Leading Empty Header Rows

**Files:**
- Modify: `backend/src/debug_agent/spreadsheets/lark.py`
- Test: `backend/tests/spreadsheets/test_lark_client.py`
- Test: `backend/tests/spreadsheets/test_lark_cli_transport.py`

- [x] **Step 1: Add failing tests**

Add tests proving sync row conversion and writeback header lookup skip leading empty rows.

- [x] **Step 2: Run focused tests for RED**

Run: `python -m pytest tests/spreadsheets/test_lark_client.py tests/spreadsheets/test_lark_cli_transport.py`
Expected: FAIL because the first physical row is still treated as the header.

- [x] **Step 3: Implement leading-empty-row handling**

Find the first non-empty row for headers, preserve data row ids, and raise a clear error if no header row exists.

- [x] **Step 4: Run focused tests for GREEN**

Run: `python -m pytest tests/spreadsheets/test_lark_client.py tests/spreadsheets/test_lark_cli_transport.py`
Expected: PASS.

### Task 2: Verification and Checkpoint

- [x] **Step 1: Run spreadsheet tests**

Run: `python -m pytest tests/spreadsheets`
Expected: PASS.

- [x] **Step 2: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 3: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 4: Commit**

Commit with message: `fix(lark): skip leading empty sheet rows`.
