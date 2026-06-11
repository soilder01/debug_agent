# Spreadsheet Row Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use TDD. Implement task-by-task, keep each checkbox updated, and commit after verification.

**Goal:** Add a local spreadsheet-row import/sync contract that mirrors Feishu sheet rows without requiring live Feishu credentials.

**Architecture:** Add a pure import module that converts normalized spreadsheet rows into `DebugCase` objects and rejected-row diagnostics. Add a thin API route that persists valid rows and optionally creates five-replay debug jobs, reusing existing repository and job service behavior.

**Tech Stack:** FastAPI, Pydantic, pytest, SQLite repository.

---

### Task 1: Spreadsheet Row Parser

**Files:**
- Create: `backend/src/debug_agent/imports/spreadsheet_rows.py`
- Test: `backend/tests/imports/test_spreadsheet_rows.py`

- [x] **Step 1: Add failing parser tests**

Create tests proving row dictionaries can be parsed into `DebugCase`, preserve `sheet_row_id`, reject malformed rows, and parse `box_regions_json`.

- [x] **Step 2: Run parser tests for RED**

Run: `python -m pytest backend/tests/imports/test_spreadsheet_rows.py -q`
Expected: FAIL because `debug_agent.imports.spreadsheet_rows` does not exist.

- [x] **Step 3: Implement minimal parser**

Create `parse_spreadsheet_rows(rows)` returning `SpreadsheetRowImportResult(imported_cases, rejected_rows)`. Reuse `DebugCase`, `AnswerSet`, `Prediction`, `HumanNotes`, and `BoxRegion`.

- [x] **Step 4: Run parser tests for GREEN**

Run: `python -m pytest backend/tests/imports/test_spreadsheet_rows.py -q`
Expected: PASS.

### Task 2: Spreadsheet Row API

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Test: `backend/tests/api/test_spreadsheet_row_import.py`

- [x] **Step 1: Add failing API tests**

Create tests for `POST /imports/spreadsheet-rows` that persist valid rows, report rejected rows, and create five-baseline jobs when `create_jobs=true`.

- [x] **Step 2: Run API tests for RED**

Run: `python -m pytest backend/tests/api/test_spreadsheet_row_import.py -q`
Expected: FAIL with 404 for the missing route.

- [x] **Step 3: Implement API route**

Add request/response models and route that calls `parse_spreadsheet_rows()`, saves cases, and submits jobs with `baseline_trials=5` by default.

- [x] **Step 4: Run API tests for GREEN**

Run: `python -m pytest backend/tests/api/test_spreadsheet_row_import.py -q`
Expected: PASS.

### Task 3: Verification and Checkpoint

- [x] **Step 1: Run focused tests**

Run: `python -m pytest backend/tests/imports/test_spreadsheet_rows.py backend/tests/api/test_spreadsheet_row_import.py -q`
Expected: PASS.

- [x] **Step 2: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 3: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 4: Commit**

Commit with message: `feat(imports): sync spreadsheet rows`.
