# CSV Box Regions Import Implementation Plan

> **For agentic workers:** Use TDD. Only parse explicit region metadata from CSV; do not infer coordinates.

**Goal:** Let CSV-imported handwriting OCR cases carry `box_regions` so table exports can preserve answer-box coordinates for localized evidence and later crop generation.

**Architecture:** Extend CSV column aliases with `box_regions_json`, parse it as an optional JSON list, and pass it into `DebugCase.box_regions`. Empty or absent values default to an empty list.

**Tech Stack:** Python, csv, Pydantic, pytest.

---

### Task 1: CSV Region Parsing

**Files:**
- Modify: `backend/src/debug_agent/imports/csv_cases.py`
- Test: `backend/tests/imports/test_csv_cases.py`

- [x] **Step 1: Add failing CSV parser test**

Assert `box_regions_json` imports coordinates into `DebugCase.box_regions`.

- [x] **Step 2: Run focused CSV parser test**

Run: `python -m pytest backend/tests/imports/test_csv_cases.py -q`
Expected: FAIL because CSV parser ignores `box_regions_json`.

- [x] **Step 3: Implement optional region parsing**

Add aliases and parse optional JSON list into `box_regions`.

- [x] **Step 4: Run focused CSV parser test**

Run: `python -m pytest backend/tests/imports/test_csv_cases.py -q`
Expected: PASS.

### Task 2: Verification and Checkpoint

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 3: Commit**

Commit with message: `feat(imports): parse csv box regions`.
