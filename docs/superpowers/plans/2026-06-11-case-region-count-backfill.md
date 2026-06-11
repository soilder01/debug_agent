# Case Region Count Backfill Implementation Plan

> **For agentic workers:** Use TDD. Legacy case rows with `box_regions` in JSON must be searchable after migration.

**Goal:** Preserve region-ready filtering for existing databases created before `debug_cases.box_region_count`.

**Architecture:** Enhance `ensure_database_schema()` so when it adds or finds `box_region_count`, it backfills rows by parsing stored `case_json` and counting `box_regions`. Keep malformed JSON safe by assigning 0.

**Tech Stack:** SQLAlchemy, SQLite, pytest.

---

### Task 1: Migration Backfill

**Files:**
- Modify: `backend/src/debug_agent/storage/database.py`
- Test: `backend/tests/storage/test_repository.py`

- [x] **Step 1: Add failing migration backfill test**

Create a legacy `debug_cases` table without `box_region_count`, insert JSON containing two `box_regions`, run `ensure_database_schema()`, and assert the count is 2.

- [x] **Step 2: Run focused storage test**

Run: `python -m pytest backend/tests/storage/test_repository.py -q`
Expected: FAIL because migration currently defaults every legacy row to 0.

- [x] **Step 3: Implement backfill**

Parse legacy `case_json` rows and update `box_region_count`; malformed JSON remains 0.

- [x] **Step 4: Run focused storage test**

Run: `python -m pytest backend/tests/storage/test_repository.py -q`
Expected: PASS.

### Task 2: Verification and Checkpoint

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 3: Commit**

Commit with message: `fix(cases): backfill case region counts`.
