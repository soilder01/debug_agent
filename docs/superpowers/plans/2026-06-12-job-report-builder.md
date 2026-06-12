# Job Report Builder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use TDD. Implement task-by-task, keep each checkbox updated, and commit after verification.

**Goal:** Rebuild a `DebugReport` from persisted job, case, and evidence rows without rerunning model experiments.

**Architecture:** Add repository support to list persisted evidence objects for a job, then add `build_report_for_job()` that loads the job, case, plan, and evidence into `generate_initial_report()`.

**Tech Stack:** Python, Pydantic, pytest, SQLAlchemy SQLite repository.

---

### Task 1: Evidence Listing

**Files:**
- Modify: `backend/src/debug_agent/storage/repository.py`
- Test: `backend/tests/storage/test_repository.py`

- [x] **Step 1: Add failing evidence listing test**

Add a test proving `list_evidence(job_id)` returns persisted `ExperimentEvidence` objects ordered by evidence id.

- [x] **Step 2: Run repository test for RED**

Run: `python -m pytest backend/tests/storage/test_repository.py -q`
Expected: FAIL because `list_evidence()` does not exist.

- [x] **Step 3: Implement evidence listing**

Add `list_evidence(job_id)` by reusing `list_evidence_ids()` and `get_evidence()`.

- [x] **Step 4: Run repository test for GREEN**

Run: `python -m pytest backend/tests/storage/test_repository.py -q`
Expected: PASS.

### Task 2: Build Report From Job

**Files:**
- Create: `backend/src/debug_agent/reports/job_report.py`
- Test: `backend/tests/reports/test_job_report.py`

- [x] **Step 1: Add failing job report tests**

Add tests proving `build_report_for_job(repository, job_id)` reconstructs experiment summary from persisted evidence and returns `None` for missing jobs.

- [x] **Step 2: Run job report tests for RED**

Run: `python -m pytest backend/tests/reports/test_job_report.py -q`
Expected: FAIL because `debug_agent.reports.job_report` does not exist.

- [x] **Step 3: Implement job report builder**

Create `build_report_for_job()` using repository job/case/evidence, `plan_experiments()`, `ExperimentRunResult`, and `generate_initial_report()`.

- [x] **Step 4: Run job report tests for GREEN**

Run: `python -m pytest backend/tests/reports/test_job_report.py -q`
Expected: PASS.

### Task 3: Verification and Checkpoint

- [x] **Step 1: Run focused tests**

Run: `python -m pytest backend/tests/storage/test_repository.py backend/tests/reports/test_job_report.py backend/tests/spreadsheets/test_writeback.py -q`
Expected: PASS.

- [x] **Step 2: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 3: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 4: Commit**

Commit with message: `feat(reports): build reports from jobs`.
