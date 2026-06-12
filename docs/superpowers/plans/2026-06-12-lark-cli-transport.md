# Lark CLI Transport Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use TDD. Implement task-by-task, keep each checkbox updated, and commit after verification.

**Goal:** Provide a real runtime transport for Lark spreadsheets through `lark-cli`, so the existing sync/writeback services can read the provided spreadsheet and write report fields without committing credentials.

**Architecture:** Add a `LarkCliSheetsTransport` behind the existing `LarkSheetsTransport` protocol. The transport shells out to `lark-cli sheets +csv-get --rows-json` for reads, parses the JSON envelope into a value matrix, and writes report fields by resolving header columns then calling `lark-cli sheets +cells-set --cells -` for each target cell. Command execution is injected for deterministic tests.

**Tech Stack:** Python 3.11, subprocess, pytest, mypy strict, ruff.

---

### Task 1: CLI Transport Read

**Files:**
- Modify: `backend/src/debug_agent/spreadsheets/lark.py`
- Test: `backend/tests/spreadsheets/test_lark_cli_transport.py`

- [x] **Step 1: Add failing read test**

Add a test proving `LarkCliSheetsTransport.read_values()` invokes `lark-cli sheets +csv-get` with token, sheet, range, and `--rows-json`, then converts `{row_number, values}` rows into a matrix.

- [x] **Step 2: Run backend test for RED**

Run: `python -m pytest backend/tests/spreadsheets/test_lark_cli_transport.py`
Expected: FAIL because `LarkCliSheetsTransport` does not exist.

- [x] **Step 3: Implement read transport**

Add command runner injection, JSON envelope parsing, column ordering, and clear error handling for CLI failures.

- [x] **Step 4: Run backend test for GREEN**

Run: `python -m pytest backend/tests/spreadsheets/test_lark_cli_transport.py`
Expected: PASS.

### Task 2: CLI Transport Writeback

- [x] **Step 1: Add failing write test**

Add a test proving `update_row()` resolves field names from the header row and writes target cells through `+cells-set --cells -`.

- [x] **Step 2: Run backend test for RED**

Run: `python -m pytest backend/tests/spreadsheets/test_lark_cli_transport.py`
Expected: FAIL because writeback is not implemented.

- [x] **Step 3: Implement writeback transport**

Build single-cell A1 ranges from resolved headers, serialize `cells` JSON to stdin, and reject unknown field headers.

- [x] **Step 4: Run backend test for GREEN**

Run: `python -m pytest backend/tests/spreadsheets/test_lark_cli_transport.py`
Expected: PASS.

### Task 3: Verification and Checkpoint

- [x] **Step 1: Run focused spreadsheet tests**

Run: `python -m pytest backend/tests/spreadsheets`
Expected: PASS.

- [x] **Step 2: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 3: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 4: Commit**

Commit with message: `feat(backend): add lark cli spreadsheet transport`.
