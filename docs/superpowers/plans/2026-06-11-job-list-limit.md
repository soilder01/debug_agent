# Job List Limit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `limit` query parameter to `GET /jobs` so large historical queues can be loaded safely.

**Architecture:** Extend `DebugJobRepository.list_jobs()` with an optional SQL `LIMIT`, then pass FastAPI's `limit` query parameter through the route. Existing unbounded and status-filter behavior remains unchanged.

**Tech Stack:** FastAPI, SQLAlchemy 2, pytest.

---

### Task 1: Backend Limit Parameter

**Files:**
- Modify: `backend/tests/api/test_job_listing.py`
- Modify: `backend/src/debug_agent/storage/repository.py`
- Modify: `backend/src/debug_agent/api/routes.py`

- [x] **Step 1: Add failing API test**

Add a test that creates three jobs, calls `GET /jobs?limit=2`, and asserts exactly two jobs are returned.

- [x] **Step 2: Run backend focused test**

Run: `python -m pytest backend/tests/api/test_job_listing.py -q`
Expected: FAIL because `limit` is ignored.

- [x] **Step 3: Implement repository limit**

Update `list_jobs(status: str | None = None, limit: int | None = None)` and apply `query.limit(limit)` when provided.

- [x] **Step 4: Implement API query parameter**

Update `GET /jobs` route to accept and pass `limit`.

- [x] **Step 5: Run backend focused test**

Run: `python -m pytest backend/tests/api/test_job_listing.py -q`
Expected: PASS.

### Task 2: Verification and Checkpoint

**Files:**
- Modify: `docs/superpowers/plans/2026-06-11-job-list-limit.md`

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and secret scan**

Run diagnostics and scan for Ark key patterns.

- [x] **Step 3: Commit**

Run:

```bash
git add backend/src/debug_agent/storage/repository.py backend/src/debug_agent/api/routes.py backend/tests/api/test_job_listing.py docs/superpowers/plans/2026-06-11-job-list-limit.md
git commit -m "feat(jobs): limit job list results"
```
