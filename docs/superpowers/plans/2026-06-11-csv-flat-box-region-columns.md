# CSV Flat Box Region Columns Implementation Plan

> **For agentic workers:** Use TDD. Parse only explicit coordinate columns; do not infer or synthesize missing regions.

**Goal:** Let common spreadsheet exports import one answer-box region from flat columns such as `box_id`, `x`, `y`, `width`, and `height`, without requiring authors to hand-write `box_regions_json`.

**Architecture:** Extend CSV aliases for flat region columns, parse a single `BoxRegion` when all required flat coordinate fields are present, and keep `box_regions_json` as the higher-fidelity multi-region path.

**Tech Stack:** Python, csv, Pydantic, pytest.

---

### Task 1: Flat Region Parsing

**Files:**
- Modify: `backend/src/debug_agent/imports/csv_cases.py`
- Test: `backend/tests/imports/test_csv_cases.py`

- [x] **Step 1: Add failing flat-column parser test**

Assert CSV columns `box_region_box_id,x,y,width,height,label` import one `DebugCase.box_regions` item.

- [x] **Step 2: Run focused CSV parser test**

Run: `python -m pytest backend/tests/imports/test_csv_cases.py -q`
Expected: FAIL because flat coordinate columns are ignored.

- [x] **Step 3: Implement flat region parsing**

Add aliases and parse one optional region from explicit flat columns when all required values are present.

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

Commit with message: `feat(imports): parse flat csv box regions`.
