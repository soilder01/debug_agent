# Job List Total Count Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Return `total_count` from `GET /jobs` so limited frontend loads can show whether more jobs exist.

**Architecture:** Add a repository count method that respects the same optional status filter but ignores limit. Extend `DebugJobListResponse` with `total_count`.

**Tech Stack:** FastAPI, SQLAlchemy 2, Pydantic v2, pytest.

---

### Task 1: Backend Total Count

**Files:**
- Modify: `backend/tests/api/test_job_listing.py`
- Modify: `backend/src/debug_agent/storage/repository.py`
- Modify: `backend/src/debug_agent/api/routes.py`

- [x] **Step 1: Add failing API assertion**

In the `limit=2` listing test, assert `total_count` is at least the number of created jobs and greater than the returned list length.

- [x] **Step 2: Run backend focused test**

Run: `python -m pytest backend/tests/api/test_job_listing.py -q`
Expected: FAIL because `total_count` is missing.

- [x] **Step 3: Implement repository count**

Add `count_jobs(status: str | None = None)` using SQLAlchemy `func.count()`.

- [x] **Step 4: Return total_count from API**

Add `total_count` to `DebugJobListResponse` and populate it in `GET /jobs`.

- [x] **Step 5: Run backend focused test**

Run: `python -m pytest backend/tests/api/test_job_listing.py -q`
Expected: PASS.

### Task 2: Verification and Checkpoint

**Files:**
- Modify: `docs/superpowers/plans/2026-06-11-job-list-total-count.md`

- [x] **Step 1: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 2: Run diagnostics and secret scan**

Run diagnostics and scan for Ark key patterns.

- [x] **Step 3: Commit**

Run:

```bash
git add backend/src/debug_agent/storage/repository.py backend/src/debug_agent/api/routes.py backend/tests/api/test_job_listing.py docs/superpowers/plans/2026-06-11-job-list-total-count.md
git commit -m "feat(jobs): include job list total count"
```
