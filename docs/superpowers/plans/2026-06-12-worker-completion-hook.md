# Worker Completion Hook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use TDD. Implement task-by-task, keep each checkbox updated, and commit after verification.

**Goal:** Provide a worker-level completion hook so enterprise workflows can attach automatic report writeback, audit, or notification after a debug job completes.

**Architecture:** Add an optional `on_job_completed` callback to `AsyncJobWorker`. `tick()` invokes it only when `run_next_job()` returns a completed job. Hook failures are tracked in worker error counters without undoing the completed job.

**Tech Stack:** Python 3.11, pytest-asyncio, mypy strict, ruff.

---

### Task 1: Worker Completion Hook

**Files:**
- Modify: `backend/src/debug_agent/jobs/worker.py`
- Test: `backend/tests/jobs/test_worker.py`

- [x] **Step 1: Add failing hook test**

Add a test proving the worker calls `on_job_completed` with the completed job after processing.

- [x] **Step 2: Run focused tests for RED**

Run: `python -m pytest tests/jobs/test_worker.py`
Expected: FAIL because `AsyncJobWorker` does not accept or invoke a completion hook.

- [x] **Step 3: Implement completion hook**

Add callback support and error accounting around hook execution.

- [x] **Step 4: Run focused tests for GREEN**

Run: `python -m pytest tests/jobs/test_worker.py`
Expected: PASS.

### Task 2: Verification and Checkpoint

- [x] **Step 1: Run focused backend tests**

Run: `python -m pytest tests/jobs/test_worker.py tests/api/test_worker_control.py`
Expected: PASS.

- [x] **Step 2: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 3: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 4: Commit**

Commit with message: `feat(worker): add job completion hook`.
