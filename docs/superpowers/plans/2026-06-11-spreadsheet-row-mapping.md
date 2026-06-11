# Spreadsheet Row Mapping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use TDD. Implement task-by-task, keep each checkbox updated, and commit after verification.

**Goal:** Persist spreadsheet row mappings so imported rows can be linked back to the exact row for later report writeback.

**Architecture:** Add a `spreadsheet_row_mappings` storage table keyed by `spreadsheet_id`, `sheet_id`, and `row_id`. Add repository methods, then have the spreadsheet sync service save case/job mappings during import.

**Tech Stack:** SQLAlchemy, SQLite, pytest, Pydantic.

---

### Task 1: Durable Row Mapping Storage

**Files:**
- Modify: `backend/src/debug_agent/storage/models.py`
- Modify: `backend/src/debug_agent/storage/repository.py`
- Test: `backend/tests/storage/test_spreadsheet_row_mapping.py`

- [x] **Step 1: Add failing repository mapping tests**

Add tests for saving, reading, and updating a spreadsheet row mapping.

- [x] **Step 2: Run repository mapping tests for RED**

Run: `python -m pytest backend/tests/storage/test_spreadsheet_row_mapping.py -q`
Expected: FAIL because mapping storage does not exist.

- [x] **Step 3: Implement mapping table and repository methods**

Create `SpreadsheetRowMappingRow`, a `SpreadsheetRowMapping` DTO, and repository save/get methods.

- [x] **Step 4: Run repository mapping tests for GREEN**

Run: `python -m pytest backend/tests/storage/test_spreadsheet_row_mapping.py -q`
Expected: PASS.

### Task 2: Sync Service Mapping

**Files:**
- Modify: `backend/src/debug_agent/spreadsheets/sync.py`
- Test: `backend/tests/spreadsheets/test_sync.py`

- [x] **Step 1: Add failing sync mapping assertion**

Assert `sync_spreadsheet_rows()` persists row-to-case/job mapping for imported rows.

- [x] **Step 2: Run sync tests for RED**

Run: `python -m pytest backend/tests/spreadsheets/test_sync.py -q`
Expected: FAIL because sync does not save mappings.

- [x] **Step 3: Save mappings during sync**

Call repository mapping save method for each imported row after optional job creation.

- [x] **Step 4: Run sync tests for GREEN**

Run: `python -m pytest backend/tests/spreadsheets/test_sync.py -q`
Expected: PASS.

### Task 3: Verification and Checkpoint

- [x] **Step 1: Run focused tests**

Run: `python -m pytest backend/tests/storage/test_spreadsheet_row_mapping.py backend/tests/spreadsheets/test_sync.py -q`
Expected: PASS.

- [x] **Step 2: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 3: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 4: Commit**

Commit with message: `feat(spreadsheets): persist row mappings`.
