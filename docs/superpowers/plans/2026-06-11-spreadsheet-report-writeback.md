# Spreadsheet Report Writeback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use TDD. Implement task-by-task, keep each checkbox updated, and commit after verification.

**Goal:** Build the writeback payload for spreadsheet rows so agent conclusions can populate `错误原因`, `评估问题反馈`, and `分析报告链接`.

**Architecture:** Add a pure writeback module that converts `DebugReport` into spreadsheet fields and a small client protocol for future Lark update calls. Keep it network-free and fully testable with a recording fake client.

**Tech Stack:** Python, Pydantic, pytest.

---

### Task 1: Report Writeback Payload

**Files:**
- Create: `backend/src/debug_agent/spreadsheets/writeback.py`
- Test: `backend/tests/spreadsheets/test_writeback.py`

- [x] **Step 1: Add failing writeback tests**

Add tests proving `DebugReport` becomes spreadsheet fields with root cause, evaluation feedback, report link, stability metrics, and preserved suggested fields.

- [x] **Step 2: Run writeback tests for RED**

Run: `python -m pytest backend/tests/spreadsheets/test_writeback.py -q`
Expected: FAIL because `debug_agent.spreadsheets.writeback` does not exist.

- [x] **Step 3: Implement minimal writeback module**

Create `build_report_writeback_fields()` and `write_report_to_spreadsheet_row()`.

- [x] **Step 4: Run writeback tests for GREEN**

Run: `python -m pytest backend/tests/spreadsheets/test_writeback.py -q`
Expected: PASS.

### Task 2: Verification and Checkpoint

- [x] **Step 1: Run focused tests**

Run: `python -m pytest backend/tests/spreadsheets/test_writeback.py backend/tests/spreadsheets/test_sync.py backend/tests/reports/test_generator.py -q`
Expected: PASS.

- [x] **Step 2: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 3: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 4: Commit**

Commit with message: `feat(spreadsheets): build report writeback fields`.
