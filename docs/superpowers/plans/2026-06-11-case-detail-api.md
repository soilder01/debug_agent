# Case Detail API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add a backend API for retrieving a full imported or fixture-backed `DebugCase` by `case_id`.

**Architecture:** Reuse the existing `DebugJobService` case-loading precedence: imported cases first, fixture cases second. Expose a read-only `GET /cases/{case_id}` endpoint returning the validated `DebugCase` model, with `404` for missing cases.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, pytest.

---

## File Structure

- Modify `backend/src/debug_agent/jobs/service.py`: expose a public `load_case(case_id)` wrapper around the existing private loading behavior.
- Modify `backend/src/debug_agent/api/routes.py`: add `GET /cases/{case_id}`.
- Create `backend/tests/api/test_case_detail.py`: verify imported case detail, fixture fallback, and missing case 404.
- Create `docs/superpowers/plans/2026-06-11-case-detail-api.md`: this plan.

## Task 1: Service Case Loader

**Files:**
- Modify: `backend/src/debug_agent/jobs/service.py`
- Create: `backend/tests/api/test_case_detail.py`

- [x] **Step 1: Write failing API tests**

Create `backend/tests/api/test_case_detail.py`:

```python
from fastapi.testclient import TestClient

from debug_agent.cases.fixtures import load_fixture_case
from debug_agent.main import app


def test_case_detail_returns_imported_case() -> None:
    client = TestClient(app)
    imported_case = load_fixture_case("handwrite233").model_copy(update={"case_id": "case-detail-imported-1"})

    import_response = client.post(
        "/imports/jsonl",
        json={"jsonl": imported_case.model_dump_json(), "create_jobs": False},
    )
    response = client.get("/cases/case-detail-imported-1")

    assert import_response.status_code == 202
    assert response.status_code == 200
    body = response.json()
    assert body["case_id"] == "case-detail-imported-1"
    assert body["prompt"] == imported_case.prompt
    assert body["golden_answer"]["answers"][0]["student_answer"] == imported_case.golden_answer.answers[0].student_answer
    assert len(body["predictions"]) == len(imported_case.predictions)


def test_case_detail_falls_back_to_fixture_case() -> None:
    client = TestClient(app)

    response = client.get("/cases/handwrite233")

    assert response.status_code == 200
    assert response.json()["case_id"] == "handwrite233"


def test_case_detail_returns_404_for_missing_case() -> None:
    client = TestClient(app)

    response = client.get("/cases/missing-case-detail")

    assert response.status_code == 404
    assert "missing-case-detail" in response.json()["detail"]
```

- [x] **Step 2: Run tests to verify failure**

Run:

```powershell
python -m pytest tests/api/test_case_detail.py -q
```

Expected: FAIL because `GET /cases/{case_id}` does not exist.

- [x] **Step 3: Add public service loader**

In `backend/src/debug_agent/jobs/service.py`, add this method before `_load_case`:

```python
    def load_case(self, case_id: str) -> DebugCase:
        return self._load_case(case_id)
```

- [x] **Step 4: Add detail endpoint**

In `backend/src/debug_agent/api/routes.py`, add this endpoint after `list_cases` and before `submit_debug_job`:

```python
@router.get("/cases/{case_id}")
def get_case_detail(case_id: str) -> DebugCase:
    try:
        return job_service.load_case(case_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
```

Keep `debug_case` at `/cases/{case_id}/debug`; FastAPI should route the more specific path correctly because both endpoint definitions are distinct.

- [x] **Step 5: Run detail tests**

Run:

```powershell
python -m pytest tests/api/test_case_detail.py -q
```

Expected: PASS.

## Task 2: Full Verification And Commit

**Files:**
- Modify: `backend/src/debug_agent/jobs/service.py`
- Modify: `backend/src/debug_agent/api/routes.py`
- Create: `backend/tests/api/test_case_detail.py`
- Create: `docs/superpowers/plans/2026-06-11-case-detail-api.md`

- [x] **Step 1: Run full verification**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1 -Target all
```

Expected: backend tests, frontend tests, lint, and typecheck all pass.

- [x] **Step 2: Run diagnostics**

Run diagnostics for edited backend files.

Expected: no diagnostics.

- [x] **Step 3: Secret scan**

Run:

```powershell
Select-String -Path backend/src/debug_agent/jobs/service.py,backend/src/debug_agent/api/routes.py,backend/tests/api/test_case_detail.py,docs/superpowers/plans/2026-06-11-case-detail-api.md -Pattern 'ark-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
```

Expected: no output.

- [x] **Step 4: Commit**

Run:

```powershell
git add backend/src/debug_agent/jobs/service.py backend/src/debug_agent/api/routes.py backend/tests/api/test_case_detail.py docs/superpowers/plans/2026-06-11-case-detail-api.md
git commit -m "feat(cases): add case detail api"
```

Expected: one commit containing only Phase 27 case detail API changes and plan.

## Self-Review

- Spec coverage: The plan covers imported case detail, fixture fallback, missing case 404, full validation, and commit.
- Placeholder scan: No TBD, TODO, or vague implementation steps remain.
- Type consistency: Endpoint returns existing `DebugCase` model from `debug_agent.cases.models`.
