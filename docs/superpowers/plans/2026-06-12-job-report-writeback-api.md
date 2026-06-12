# Job Report Writeback API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use TDD. Implement task-by-task, keep each checkbox updated, and commit after verification.

**Goal:** Expose a backend API that writes a persisted job report back to the mapped spreadsheet row through an injectable writeback client.

**Architecture:** Add a thin `POST /jobs/{job_id}/spreadsheet-writeback` route that rebuilds the report from durable job evidence, resolves the persisted spreadsheet row mapping, and calls the existing `write_report_for_job()` boundary. Keep the real Lark transport out of this slice by using a configurable `spreadsheet_writeback_client`; return 503 when it is not configured and 404 for missing reports or mappings.

**Tech Stack:** FastAPI, Pydantic, pytest, TestClient.

---

### Task 1: Job Report Writeback Route

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Test: `backend/tests/api/test_job_report_writeback.py`

- [x] **Step 1: Add failing API tests**

Add tests proving `POST /jobs/{job_id}/spreadsheet-writeback` writes through an injected client, returns 404 when the job has no spreadsheet mapping, and returns 503 when no writeback client is configured.

- [x] **Step 2: Run API tests for RED**

Run: `python -m pytest backend/tests/api/test_job_report_writeback.py -q`
Expected: FAIL with 404 for the missing route.

- [x] **Step 3: Implement API route**

Add request model:

```python
class JobReportWritebackRequest(BaseModel):
    report_url: str
```

Add configurable client:

```python
spreadsheet_writeback_client: SpreadsheetWritebackClient | None = None
```

Add route:

```python
@router.post("/jobs/{job_id}/spreadsheet-writeback")
def write_job_report_to_spreadsheet(job_id: str, request: JobReportWritebackRequest) -> SpreadsheetWritebackResult:
    if spreadsheet_writeback_client is None:
        raise HTTPException(status_code=503, detail="Spreadsheet writeback client is not configured")
    report = build_report_for_job(job_repository, job_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Debug report not found for job: {job_id}")
    result = write_report_for_job(
        repository=job_repository,
        client=spreadsheet_writeback_client,
        job_id=job_id,
        report=report,
        report_url=request.report_url,
    )
    if result is None:
        raise HTTPException(status_code=404, detail=f"Spreadsheet row mapping not found for job: {job_id}")
    return result
```

- [x] **Step 4: Run API tests for GREEN**

Run: `python -m pytest backend/tests/api/test_job_report_writeback.py -q`
Expected: PASS.

### Task 2: Verification and Checkpoint

- [x] **Step 1: Run focused tests**

Run: `python -m pytest backend/tests/api/test_job_report.py backend/tests/api/test_job_report_writeback.py backend/tests/spreadsheets/test_writeback.py -q`
Expected: PASS.

- [x] **Step 2: Run full verification**

Run: `.\scripts\verify.ps1`
Expected: all tests, lint, and type checks pass.

- [x] **Step 3: Run diagnostics and safety checks**

Run diagnostics, `git diff --check`, and Ark key regex scan.

- [x] **Step 4: Commit**

Commit with message: `feat(api): write job reports to spreadsheets`.
