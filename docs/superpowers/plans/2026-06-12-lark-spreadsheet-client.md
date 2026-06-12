# Lark Spreadsheet Client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use TDD. Implement task-by-task, keep each checkbox updated, and commit after verification.

**Goal:** Add a Lark spreadsheet client adapter that converts sheet values into sync rows and forwards report writeback fields through an injectable transport.

**Architecture:** Extend `debug_agent.spreadsheets.lark` with a small `LarkSheetsTransport` protocol and `LarkSpreadsheetClient`. The client is network-free in tests: it reads a header/value matrix from transport, emits `SpreadsheetSourceRow` values with row-number row ids, and forwards updates to transport.

**Tech Stack:** Python, Pydantic, pytest, protocol-based dependency injection.

---

### Task 1: Lark Spreadsheet Client Contract

**Files:**
- Modify: `backend/src/debug_agent/spreadsheets/lark.py`
- Test: `backend/tests/spreadsheets/test_lark_client.py`

- [x] **Step 1: Add failing client tests**

Add tests proving the client converts header/value rows into `SpreadsheetSourceRow` objects, skips empty rows, and forwards writeback fields.

- [x] **Step 2: Run client tests for RED**

Run: `python -m pytest backend/tests/spreadsheets/test_lark_client.py -q`
Expected: FAIL because `LarkSpreadsheetClient` does not exist.

- [x] **Step 3: Implement minimal client**

Create `LarkSheetsTransport` and `LarkSpreadsheetClient` in `spreadsheets/lark.py`.

- [x] **Step 4: Run client tests for GREEN**

Run: `python -m pytest backend/tests/spreadsheets/test_lark_client.py -q`
Expected: PASS.

### Task 2: Verification and Checkpoint

- [x] **Step 1: Run focused tests**

Run: `python -m pytest backend/tests/spreadsheets/test_lark.py backend/tests/spreadsheets/test_lark_client.py backend/tests/spreadsheets/test_sync.py backend/tests/spreadsheets/test_writeback.py -q`
Expected: PASS.

- [x] **Step 2: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 3: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 4: Commit**

Commit with message: `feat(spreadsheets): add lark client adapter`.
