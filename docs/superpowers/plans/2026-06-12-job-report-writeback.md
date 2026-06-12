# Job Report Writeback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use TDD. Implement task-by-task, keep each checkbox updated, and commit after verification.

**Goal:** Write a generated debug report back to the spreadsheet row associated with a completed job.

**Architecture:** Add repository lookup by `job_id`, then add `write_report_for_job()` that resolves the row mapping and delegates to the existing spreadsheet writeback client. Keep this network-free and test it with a recording client.

**Tech Stack:** Python, Pydantic, pytest, SQLAlchemy SQLite repository.

---

### Task 1: Mapping Lookup by Job

**Files:**
- Modify: `backend/src/debug_agent/storage/repository.py`
- Test: `backend/tests/storage/test_spreadsheet_row_mapping.py`

- [x] **Step 1: Add failing job mapping lookup test**

Add a test proving `get_spreadsheet_row_mapping_by_job_id()` returns the row mapping saved for a job.

- [x] **Step 2: Run mapping tests for RED**

Run: `python -m pytest backend/tests/storage/test_spreadsheet_row_mapping.py -q`
Expected: FAIL because lookup by job id does not exist.

- [x] **Step 3: Implement repository lookup**

Add `get_spreadsheet_row_mapping_by_job_id(job_id)`.

- [x] **Step 4: Run mapping tests for GREEN**

Run: `python -m pytest backend/tests/storage/test_spreadsheet_row_mapping.py -q`
Expected: PASS.

### Task 2: Job Report Writeback Service

**Files:**
- Modify: `backend/src/debug_agent/spreadsheets/writeback.py`
- Test: `backend/tests/spreadsheets/test_writeback.py`

- [x] **Step 1: Add failing job writeback tests**

Add tests proving `write_report_for_job()` resolves mapping, writes fields to the mapped row, and returns `None` when no mapping exists.

- [x] **Step 2: Run writeback tests for RED**

Run: `python -m pytest backend/tests/spreadsheets/test_writeback.py -q`
Expected: FAIL because `write_report_for_job()` does not exist.

- [x] **Step 3: Implement job writeback**

Add `write_report_for_job()` using repository mapping lookup and `write_report_to_spreadsheet_row()`.

- [x] **Step 4: Run writeback tests for GREEN**

Run: `python -m pytest backend/tests/spreadsheets/test_writeback.py -q`
Expected: PASS.

### Task 3: Verification and Checkpoint

- [x] **Step 1: Run focused tests**

Run: `python -m pytest backend/tests/storage/test_spreadsheet_row_mapping.py backend/tests/spreadsheets/test_writeback.py -q`
Expected: PASS.

- [x] **Step 2: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 3: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 4: Commit**

Commit with message: `feat(spreadsheets): write reports by job mapping`.
