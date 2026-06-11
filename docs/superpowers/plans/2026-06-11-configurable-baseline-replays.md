# Configurable Baseline Replays Implementation Plan

> **For agentic workers:** Use TDD. Replay counts must be persisted on queued jobs so worker execution matches submission intent.

**Goal:** Support explicit five-run baseline replay jobs, matching the handwriting OCR workflow where each sample is run multiple times to measure stability.

**Architecture:** Add `baseline_trials` to experiment planning, persist it on `debug_jobs`, expose it through job submission query parameters, and use the stored value when the worker executes the job.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, SQLite migrations.

---

### Task 1: Backend Replay Count Contract

**Files:**
- Modify: `backend/src/debug_agent/experiments/planner.py`
- Modify: `backend/src/debug_agent/storage/models.py`
- Modify: `backend/src/debug_agent/storage/repository.py`
- Modify: `backend/src/debug_agent/storage/database.py`
- Modify: `backend/src/debug_agent/jobs/service.py`
- Modify: `backend/src/debug_agent/api/routes.py`
- Test: `backend/tests/experiments/test_planner.py`
- Test: `backend/tests/storage/test_repository.py`
- Test: `backend/tests/jobs/test_service.py`
- Test: `backend/tests/api/test_job_submission.py`

- [x] **Step 1: Add failing replay-count tests**

Assert `baseline_trials=5` changes the plan, is persisted on jobs, and auto-run job submissions produce the expanded evidence set.

- [x] **Step 2: Run focused backend tests**

Run: `python -m pytest backend/tests/experiments/test_planner.py backend/tests/storage/test_repository.py backend/tests/jobs/test_service.py backend/tests/api/test_job_submission.py -q`
Expected: FAIL because replay counts are not configurable or persisted.

- [x] **Step 3: Implement persisted replay count**

Add the column, migration, repository parameter, planner parameter, service parameter, and route query parameter.

- [x] **Step 4: Run focused backend tests**

Run: `python -m pytest backend/tests/experiments/test_planner.py backend/tests/storage/test_repository.py backend/tests/jobs/test_service.py backend/tests/api/test_job_submission.py -q`
Expected: PASS.

### Task 2: Verification and Checkpoint

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 3: Commit**

Commit with message: `feat(jobs): configure baseline replays`.
