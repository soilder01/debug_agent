# Job Report API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use TDD. Implement task-by-task, keep each checkbox updated, and commit after verification.

**Goal:** Expose generated job reports through a backend API without rerunning experiments.

**Architecture:** Add a thin `GET /jobs/{job_id}/report` route that calls `build_report_for_job()` and returns `DebugReport`, with 404 for missing jobs or missing persisted case data.

**Tech Stack:** FastAPI, pytest, TestClient.

---

### Task 1: Job Report Route

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Test: `backend/tests/api/test_job_report.py`

- [x] **Step 1: Add failing API tests**

Add tests proving `GET /jobs/{job_id}/report` returns a persisted report and 404 for missing jobs.

- [x] **Step 2: Run API tests for RED**

Run: `python -m pytest backend/tests/api/test_job_report.py -q`
Expected: FAIL with 404 for the missing route.

- [x] **Step 3: Implement API route**

Add route that calls `build_report_for_job(job_repository, job_id)`.

- [x] **Step 4: Run API tests for GREEN**

Run: `python -m pytest backend/tests/api/test_job_report.py -q`
Expected: PASS.

### Task 2: Verification and Checkpoint

- [x] **Step 1: Run focused tests**

Run: `python -m pytest backend/tests/api/test_job_report.py backend/tests/reports/test_job_report.py -q`
Expected: PASS.

- [x] **Step 2: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 3: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 4: Commit**

Commit with message: `feat(api): expose job reports`.
