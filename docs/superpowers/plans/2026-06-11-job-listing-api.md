# Job Listing API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a job listing API that returns current and historical jobs with the same retry metadata as job detail.

**Architecture:** Add a repository method to list `DebugJobRow` records, then expose `GET /jobs` as a list of `DebugJobStatus` objects. Reuse the existing job-status builder logic so list and detail stay consistent.

**Tech Stack:** FastAPI, SQLAlchemy 2, Pydantic v2, pytest.

---

### Task 1: Backend Job Listing

**Files:**
- Create: `backend/tests/api/test_job_listing.py`
- Modify: `backend/src/debug_agent/storage/repository.py`
- Modify: `backend/src/debug_agent/api/routes.py`

- [x] **Step 1: Add failing API test**

Create two jobs through the public API, call `GET /jobs`, and assert both returned job ids include retry metadata.

- [x] **Step 2: Run backend focused test**

Run: `python -m pytest backend/tests/api/test_job_listing.py -q`
Expected: FAIL because `GET /jobs` is missing.

- [x] **Step 3: Implement repository listing**

Add `list_jobs()` to `DebugJobRepository`, ordered by `job_id`.

- [x] **Step 4: Implement API route**

Add `DebugJobListResponse` and `GET /jobs`, reusing a helper that builds `DebugJobStatus`.

- [x] **Step 5: Run backend focused test**

Run: `python -m pytest backend/tests/api/test_job_listing.py -q`
Expected: PASS.

### Task 2: Verification and Checkpoint

**Files:**
- Modify: `docs/superpowers/plans/2026-06-11-job-listing-api.md`

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and secret scan**

Run diagnostics and scan for Ark key patterns.

- [x] **Step 3: Commit**

Run:

```bash
git add backend/src/debug_agent/storage/repository.py backend/src/debug_agent/api/routes.py backend/tests/api/test_job_listing.py docs/superpowers/plans/2026-06-11-job-listing-api.md
git commit -m "feat(jobs): list debug jobs"
```
