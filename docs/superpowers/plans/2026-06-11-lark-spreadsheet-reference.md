# Lark Spreadsheet Reference Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use TDD. Implement task-by-task, keep each checkbox updated, and commit after verification.

**Goal:** Parse and configure Lark spreadsheet references so real sheet URLs can be routed into the existing spreadsheet sync adapter boundary.

**Architecture:** Add a small network-free Lark module that parses `/sheets/{token}?sheet={sheet_id}` URLs and direct token/sheet inputs into a typed reference. Add settings support for optional environment defaults without storing credentials.

**Tech Stack:** Python, Pydantic, pytest, environment variables.

---

### Task 1: Lark Spreadsheet Reference Parser

**Files:**
- Create: `backend/src/debug_agent/spreadsheets/lark.py`
- Test: `backend/tests/spreadsheets/test_lark.py`

- [x] **Step 1: Add failing parser tests**

Add tests for parsing a Lark spreadsheet URL, parsing a direct token with explicit sheet id, and rejecting URLs without a sheet id.

- [x] **Step 2: Run parser tests for RED**

Run: `python -m pytest backend/tests/spreadsheets/test_lark.py -q`
Expected: FAIL because `debug_agent.spreadsheets.lark` does not exist.

- [x] **Step 3: Implement minimal parser**

Create `LarkSpreadsheetReference` and `parse_lark_spreadsheet_reference()`.

- [x] **Step 4: Run parser tests for GREEN**

Run: `python -m pytest backend/tests/spreadsheets/test_lark.py -q`
Expected: PASS.

### Task 2: Lark Spreadsheet Settings

**Files:**
- Modify: `backend/src/debug_agent/settings.py`
- Test: `backend/tests/test_settings.py`
- Modify: `.env.example`

- [x] **Step 1: Add failing settings tests**

Add tests proving optional `LARK_SPREADSHEET_URL` and `LARK_SHEET_ID` are read without requiring credentials.

- [x] **Step 2: Run settings tests for RED**

Run: `python -m pytest backend/tests/test_settings.py -q`
Expected: FAIL because `LarkSpreadsheetSettings` does not exist.

- [x] **Step 3: Implement settings**

Create `LarkSpreadsheetSettings.from_env()` and document optional env vars in `.env.example`.

- [x] **Step 4: Run settings tests for GREEN**

Run: `python -m pytest backend/tests/test_settings.py -q`
Expected: PASS.

### Task 3: Verification and Checkpoint

- [x] **Step 1: Run focused tests**

Run: `python -m pytest backend/tests/spreadsheets/test_lark.py backend/tests/test_settings.py -q`
Expected: PASS.

- [x] **Step 2: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 3: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 4: Commit**

Commit with message: `feat(spreadsheets): parse lark sheet references`.
