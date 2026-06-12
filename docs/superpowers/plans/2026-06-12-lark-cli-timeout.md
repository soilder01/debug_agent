# Lark CLI Timeout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use TDD. Implement task-by-task, keep each checkbox updated, and commit after verification.

**Goal:** Prevent Lark CLI calls from blocking API workers indefinitely when auth, network, or CLI execution hangs.

**Architecture:** Add a default timeout to `_run_lark_cli`, pass it to `subprocess.run`, and convert `subprocess.TimeoutExpired` into `LarkCliError` so API error mapping returns a diagnostic 502.

**Tech Stack:** Python 3.11, pytest, mypy strict, ruff.

---

### Task 1: Subprocess Timeout

**Files:**
- Modify: `backend/src/debug_agent/spreadsheets/lark.py`
- Test: `backend/tests/spreadsheets/test_lark_cli_transport.py`

- [x] **Step 1: Add failing timeout tests**

Add tests proving real subprocess execution receives a timeout and timeout expiration is converted into `LarkCliError`.

- [x] **Step 2: Run focused tests for RED**

Run: `python -m pytest tests/spreadsheets/test_lark_cli_transport.py`
Expected: FAIL because `subprocess.run` is not called with timeout and timeout errors are not converted.

- [x] **Step 3: Implement timeout handling**

Add a default timeout constant, pass it to `subprocess.run`, and catch `subprocess.TimeoutExpired`.

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

Commit with message: `fix(lark): timeout cli spreadsheet calls`.
