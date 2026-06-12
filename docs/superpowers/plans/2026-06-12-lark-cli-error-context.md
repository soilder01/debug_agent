# Lark CLI Error Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use TDD. Implement task-by-task, keep each checkbox updated, and commit after verification.

**Goal:** Make Lark CLI failures easier to diagnose by including safe command context in errors without logging stdin payloads or secrets.

**Architecture:** Add a command summarizer that extracts the Lark shortcut and safe flags such as `--range`, `--sheet-id`, and `--spreadsheet-token`. Use it in non-zero exit and timeout errors. Do not include stdin content in error messages.

**Tech Stack:** Python 3.11, pytest, mypy strict, ruff.

---

### Task 1: Safe Error Context

**Files:**
- Modify: `backend/src/debug_agent/spreadsheets/lark.py`
- Test: `backend/tests/spreadsheets/test_lark_cli_transport.py`

- [x] **Step 1: Add failing error-context tests**

Add tests proving non-zero exits and timeouts include the Lark shortcut and range/sheet context, while excluding stdin payloads.

- [x] **Step 2: Run focused tests for RED**

Run: `python -m pytest tests/spreadsheets/test_lark_cli_transport.py`
Expected: FAIL because errors currently do not include command context.

- [x] **Step 3: Implement safe command context**

Add a command summarizer and use it in `_run_lark_cli` error messages.

- [x] **Step 4: Run focused tests for GREEN**

Run: `python -m pytest tests/spreadsheets/test_lark_cli_transport.py`
Expected: PASS.

### Task 2: Verification and Checkpoint

- [x] **Step 1: Run spreadsheet tests**

Run: `python -m pytest tests/spreadsheets`
Expected: PASS.

- [x] **Step 2: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 3: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 4: Commit**

Commit with message: `fix(lark): include safe cli error context`.
