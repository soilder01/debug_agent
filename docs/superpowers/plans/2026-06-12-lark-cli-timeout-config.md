# Lark CLI Timeout Config Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use TDD. Implement task-by-task, keep each checkbox updated, and commit after verification.

**Goal:** Make Lark CLI spreadsheet timeout configurable for enterprise deployments while keeping the safe default of 60 seconds.

**Architecture:** Add `lark_cli_timeout_seconds` to `LarkSpreadsheetSettings`, read it from `LARK_CLI_TIMEOUT_SECONDS`, pass it from API wiring into `LarkCliSheetsTransport`, and have the transport use the instance timeout for subprocess calls.

**Tech Stack:** Python 3.11, pytest, mypy strict, ruff.

---

### Task 1: Timeout Configuration

**Files:**
- Modify: `backend/src/debug_agent/settings.py`
- Modify: `backend/src/debug_agent/api/routes.py`
- Modify: `backend/src/debug_agent/spreadsheets/lark.py`
- Test: `backend/tests/test_settings.py`
- Test: `backend/tests/spreadsheets/test_lark_cli_transport.py`

- [x] **Step 1: Add failing tests**

Add tests proving `LARK_CLI_TIMEOUT_SECONDS` is loaded from env and `LarkCliSheetsTransport(timeout_seconds=...)` passes the configured value to subprocess.

- [x] **Step 2: Run focused tests for RED**

Run: `python -m pytest tests/test_settings.py tests/spreadsheets/test_lark_cli_transport.py`
Expected: FAIL because timeout is fixed at 60 seconds and settings do not expose the env value.

- [x] **Step 3: Implement timeout configuration**

Add setting field/env parsing, transport constructor support, and API wiring.

- [x] **Step 4: Run focused tests for GREEN**

Run: `python -m pytest tests/test_settings.py tests/spreadsheets/test_lark_cli_transport.py`
Expected: PASS.

### Task 2: Verification and Checkpoint

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 3: Commit**

Commit with message: `feat(lark): configure cli timeout`.
