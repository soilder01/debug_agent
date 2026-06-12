# Spreadsheet Sync API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use TDD. Implement task-by-task, keep each checkbox updated, and commit after verification.

**Goal:** Expose a backend API that syncs spreadsheet rows into persisted cases and default five-replay debug jobs.

**Architecture:** Add `POST /spreadsheets/sync` as a thin route over the existing `sync_spreadsheet_rows()` service. Keep the spreadsheet provider injectable through `spreadsheet_sync_client`; return 503 when no client is configured, and persist row mappings so later report writeback can target the original row.

**Tech Stack:** FastAPI, Pydantic, pytest, TestClient.

---

### Task 1: Spreadsheet Sync Route

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Test: `backend/tests/api/test_spreadsheet_sync.py`

- [x] **Step 1: Add failing API tests**

Add tests proving `POST /spreadsheets/sync` imports spreadsheet rows, creates default five-replay jobs, persists job-to-row mapping, and returns 503 when no sync client is configured.

- [x] **Step 2: Run API tests for RED**

Run: `python -m pytest backend/tests/api/test_spreadsheet_sync.py -q`
Expected: FAIL with 404 for the missing route.

- [x] **Step 3: Implement API route**

Add request model:

```python
class SpreadsheetSyncRequest(BaseModel):
    spreadsheet_id: str
    sheet_id: str
    create_jobs: bool = True
    baseline_trials: int = Field(default=5, ge=0, le=5)
```

Add configurable client:

```python
spreadsheet_sync_client: SpreadsheetClient | None = None
```

Add route:

```python
@router.post("/spreadsheets/sync", status_code=202)
def sync_spreadsheet(request: SpreadsheetSyncRequest) -> SpreadsheetSyncResult:
    if spreadsheet_sync_client is None:
        raise HTTPException(status_code=503, detail="Spreadsheet sync client is not configured")
    return sync_spreadsheet_rows(
        client=spreadsheet_sync_client,
        spreadsheet_id=request.spreadsheet_id,
        sheet_id=request.sheet_id,
        repository=job_repository,
        job_service=job_service,
        create_jobs=request.create_jobs,
        baseline_trials=request.baseline_trials,
    )
```

- [x] **Step 4: Run API tests for GREEN**

Run: `python -m pytest backend/tests/api/test_spreadsheet_sync.py -q`
Expected: PASS.

### Task 2: Verification and Checkpoint

- [x] **Step 1: Run focused tests**

Run: `python -m pytest backend/tests/api/test_spreadsheet_sync.py backend/tests/spreadsheets/test_sync.py backend/tests/api/test_job_report_writeback.py -q`
Expected: PASS.

- [x] **Step 2: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 3: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 4: Commit**

Commit with message: `feat(api): sync spreadsheet rows`.
