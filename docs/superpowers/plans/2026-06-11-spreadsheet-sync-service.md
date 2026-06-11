# Spreadsheet Sync Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use TDD. Implement task-by-task, keep each checkbox updated, and commit after verification.

**Goal:** Add a testable spreadsheet sync service that can import rows from an abstract spreadsheet client and create five-replay debug jobs.

**Architecture:** Define a small `SpreadsheetClient` protocol and `SpreadsheetSourceRow` model. Implement `sync_spreadsheet_rows()` as a pure orchestration layer over `parse_spreadsheet_rows()`, `DebugJobRepository.save_case()`, and `DebugJobService.submit_case_debug()`.

**Tech Stack:** Python, Pydantic, pytest, SQLAlchemy SQLite test repository.

---

### Task 1: Spreadsheet Sync Service

**Files:**
- Create: `backend/src/debug_agent/spreadsheets/__init__.py`
- Create: `backend/src/debug_agent/spreadsheets/sync.py`
- Test: `backend/tests/spreadsheets/__init__.py`
- Test: `backend/tests/spreadsheets/test_sync.py`

- [x] **Step 1: Add failing sync service tests**

Add tests proving an injected client can provide rows, valid rows are persisted, jobs are created with `baseline_trials=5`, and rejected rows do not create jobs.

- [x] **Step 2: Run sync tests for RED**

Run: `python -m pytest backend/tests/spreadsheets/test_sync.py -q`
Expected: FAIL because `debug_agent.spreadsheets.sync` does not exist.

- [x] **Step 3: Implement minimal sync service**

Create `SpreadsheetSourceRow`, `SpreadsheetSyncResult`, `SpreadsheetClient`, and `sync_spreadsheet_rows()`.

- [x] **Step 4: Run sync tests for GREEN**

Run: `python -m pytest backend/tests/spreadsheets/test_sync.py -q`
Expected: PASS.

### Task 2: Verification and Checkpoint

- [x] **Step 1: Run focused tests**

Run: `python -m pytest backend/tests/spreadsheets/test_sync.py backend/tests/imports/test_spreadsheet_rows.py backend/tests/api/test_spreadsheet_row_import.py -q`
Expected: PASS.

- [x] **Step 2: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 3: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 4: Commit**

Commit with message: `feat(spreadsheets): add sync service`.
