# Job List Status Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow `GET /jobs` to filter jobs by status so operators can load focused created/running/failed/completed queues.

**Architecture:** Extend the repository `list_jobs()` method with an optional `status` filter and pass the query parameter through the FastAPI route. Keep the existing unfiltered behavior unchanged.

**Tech Stack:** FastAPI, SQLAlchemy 2, pytest.

---

### Task 1: Backend Status Filter

**Files:**
- Modify: `backend/tests/api/test_job_listing.py`
- Modify: `backend/src/debug_agent/storage/repository.py`
- Modify: `backend/src/debug_agent/api/routes.py`

- [x] **Step 1: Add failing API test**

Add a test that creates one failed job and one created job, calls `GET /jobs?status=failed`, and asserts only the failed job is returned.

- [x] **Step 2: Run backend focused test**

Run: `python -m pytest backend/tests/api/test_job_listing.py -q`
Expected: FAIL because `GET /jobs` ignores the status query parameter.

- [x] **Step 3: Implement repository filter**

Update `list_jobs(status: str | None = None)` to add `where(DebugJobRow.status == status)` when provided.

- [x] **Step 4: Implement API query parameter**

Update `list_jobs(status: str | None = None)` route to pass the filter to the repository.

- [x] **Step 5: Run backend focused test**

Run: `python -m pytest backend/tests/api/test_job_listing.py -q`
Expected: PASS.

### Task 2: Verification and Checkpoint

**Files:**
- Modify: `docs/superpowers/plans/2026-06-11-job-list-status-filter.md`

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and secret scan**

Run diagnostics and scan for Ark key patterns.

- [x] **Step 3: Commit**

Run:

```bash
git add backend/src/debug_agent/storage/repository.py backend/src/debug_agent/api/routes.py backend/tests/api/test_job_listing.py docs/superpowers/plans/2026-06-11-job-list-status-filter.md
git commit -m "feat(jobs): filter job list by status"
```
