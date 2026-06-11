# Import Batch Five Replays Implementation Plan

> **For agentic workers:** Use TDD. Imported and batched jobs must preserve the five-run replay workflow through queued worker execution.

**Goal:** Make batch submissions and imported case jobs default to five baseline replays, matching the real spreadsheet triage workflow.

**Architecture:** Add `baseline_trials` to batch, JSONL import, and CSV import request contracts with default `5`, validate the range, and pass it into `submit_case_debug()`.

**Tech Stack:** FastAPI, Pydantic, pytest.

---

### Task 1: Backend Batch/Import Replay Counts

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Test: `backend/tests/api/test_batch_job_submission.py`
- Test: `backend/tests/api/test_csv_import.py`
- Test: `backend/tests/api/test_jsonl_import.py`

- [x] **Step 1: Add failing batch/import replay tests**

Assert batch, CSV import, and JSONL import jobs produce five `baseline_replay` evidence rows when processed.

- [x] **Step 2: Run focused backend tests**

Run: `python -m pytest backend/tests/api/test_batch_job_submission.py backend/tests/api/test_csv_import.py backend/tests/api/test_jsonl_import.py -q`
Expected: FAIL because these paths still create default one-baseline jobs.

- [x] **Step 3: Implement request-level replay counts**

Add validated `baseline_trials` fields with default `5` and pass them into job submission.

- [x] **Step 4: Run focused backend tests**

Run: `python -m pytest backend/tests/api/test_batch_job_submission.py backend/tests/api/test_csv_import.py backend/tests/api/test_jsonl_import.py -q`
Expected: PASS.

### Task 2: Verification and Checkpoint

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 3: Commit**

Commit with message: `feat(imports): create five replay jobs`.
