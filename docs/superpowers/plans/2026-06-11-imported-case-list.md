# Imported Case List Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add a backend API that lists persisted imported cases as lightweight summaries.

**Architecture:** Extend `DebugJobRepository` with a `list_cases()` read method that deserializes stored `DebugCase` rows and returns them ordered by `case_id`. Add a focused FastAPI response model for summaries so the API does not return large prompt/prediction payloads.

**Tech Stack:** Python 3.11, SQLAlchemy 2, Pydantic v2, FastAPI, pytest.

---

## File Structure

- Modify `backend/src/debug_agent/storage/repository.py`: add `list_cases()` to read persisted cases.
- Modify `backend/tests/storage/test_case_repository.py`: cover deterministic case listing.
- Modify `backend/src/debug_agent/api/routes.py`: add `DebugCaseSummary` and `GET /cases`.
- Create `backend/tests/api/test_case_listing.py`: verify imported JSONL and CSV cases appear in the list API.
- Create `docs/superpowers/plans/2026-06-11-imported-case-list.md`: this plan.

## API Contract

`GET /cases` returns:

```json
{
  "cases": [
    {
      "case_id": "imported-case-1",
      "image_uri": "file://image.png",
      "avg_score": 1.0,
      "debug_status": "pending",
      "root_cause": "visual_recognition_failure"
    }
  ]
}
```

Only persisted imported cases are listed. Fixture-only cases are still available through existing fixture-backed job submission paths but are not included until imported.

## Task 1: Repository Case Listing

**Files:**
- Modify: `backend/tests/storage/test_case_repository.py`
- Modify: `backend/src/debug_agent/storage/repository.py`

- [x] **Step 1: Write failing repository test**

Append this test to `backend/tests/storage/test_case_repository.py`:

```python
def test_repository_lists_imported_cases_ordered_by_case_id() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    first_case = load_fixture_case("handwrite233").model_copy(update={"case_id": "imported-b"})
    second_case = load_fixture_case("handwrite233").model_copy(update={"case_id": "imported-a"})

    repository.save_case(first_case)
    repository.save_case(second_case)

    listed_cases = repository.list_cases()

    assert [case.case_id for case in listed_cases] == ["imported-a", "imported-b"]
    assert listed_cases[0] == second_case
    assert listed_cases[1] == first_case
```

- [x] **Step 2: Run repository test to verify failure**

Run:

```powershell
python -m pytest tests/storage/test_case_repository.py -q
```

Expected: FAIL because `DebugJobRepository.list_cases` does not exist.

- [x] **Step 3: Implement `list_cases`**

Add this method to `DebugJobRepository` after `get_case`:

```python
    def list_cases(self) -> list[DebugCase]:
        with self._lock:
            with self._session_factory() as session:
                rows = session.scalars(select(DebugCaseRow).order_by(DebugCaseRow.case_id))
                return [DebugCase.model_validate_json(row.case_json) for row in rows]
```

- [x] **Step 4: Run repository test**

Run:

```powershell
python -m pytest tests/storage/test_case_repository.py -q
```

Expected: PASS.

## Task 2: Case List API

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Create: `backend/tests/api/test_case_listing.py`

- [x] **Step 1: Write failing API test**

Create `backend/tests/api/test_case_listing.py`:

```python
import csv
import io
import json

from fastapi.testclient import TestClient

from debug_agent.cases.fixtures import load_fixture_case
from debug_agent.main import app


def csv_text() -> str:
    golden_answer = {"answers": [{"box_id": 1, "student_answer": "42"}]}
    raw_output = json.dumps(golden_answer)
    predictions = [{"trial": 1, "raw_output": raw_output, "score": 1}]
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "case_id",
            "image_uri",
            "prompt",
            "golden_answer_json",
            "scoring_standard",
            "predictions_json",
            "avg_score",
            "debug_status",
            "root_cause",
        ],
    )
    writer.writeheader()
    writer.writerow(
        {
            "case_id": "case-list-csv-1",
            "image_uri": "file://case-list.png",
            "prompt": "Read the answer",
            "golden_answer_json": json.dumps(golden_answer),
            "scoring_standard": "exact match",
            "predictions_json": json.dumps(predictions),
            "avg_score": "1.0",
            "debug_status": "pending",
            "root_cause": "visual_recognition_failure",
        }
    )
    return output.getvalue()


def test_case_listing_returns_imported_case_summaries() -> None:
    client = TestClient(app)
    case_json = load_fixture_case("handwrite233").model_copy(update={"case_id": "case-list-jsonl-1"}).model_dump_json()

    jsonl_response = client.post("/imports/jsonl", json={"jsonl": case_json, "create_jobs": False})
    csv_response = client.post("/imports/csv", json={"csv_text": csv_text(), "create_jobs": False})
    response = client.get("/cases")

    assert jsonl_response.status_code == 202
    assert csv_response.status_code == 202
    assert response.status_code == 200
    cases = response.json()["cases"]
    by_case_id = {case["case_id"]: case for case in cases}
    assert by_case_id["case-list-jsonl-1"]["avg_score"] == 0.0
    assert by_case_id["case-list-csv-1"] == {
        "case_id": "case-list-csv-1",
        "image_uri": "file://case-list.png",
        "avg_score": 1.0,
        "debug_status": "pending",
        "root_cause": "visual_recognition_failure",
    }
```

- [x] **Step 2: Run API test to verify failure**

Run:

```powershell
python -m pytest tests/api/test_case_listing.py -q
```

Expected: FAIL because `GET /cases` does not exist.

- [x] **Step 3: Add response models and route**

In `backend/src/debug_agent/api/routes.py`, add these models after `CsvImportResponse`:

```python
class DebugCaseSummary(BaseModel):
    case_id: str
    image_uri: str
    avg_score: float
    debug_status: str
    root_cause: str


class DebugCaseListResponse(BaseModel):
    cases: list[DebugCaseSummary]
```

Add this endpoint after `health`:

```python
@router.get("/cases")
def list_cases() -> DebugCaseListResponse:
    return DebugCaseListResponse(
        cases=[
            DebugCaseSummary(
                case_id=case.case_id,
                image_uri=case.image_uri,
                avg_score=case.avg_score,
                debug_status=case.human_notes.debug_status,
                root_cause=case.human_notes.root_cause,
            )
            for case in job_repository.list_cases()
        ]
    )
```

- [x] **Step 4: Run API and repository tests**

Run:

```powershell
python -m pytest tests/storage/test_case_repository.py tests/api/test_case_listing.py -q
```

Expected: PASS.

## Task 3: Full Verification And Commit

**Files:**
- Modify: `backend/src/debug_agent/storage/repository.py`
- Modify: `backend/tests/storage/test_case_repository.py`
- Modify: `backend/src/debug_agent/api/routes.py`
- Create: `backend/tests/api/test_case_listing.py`
- Create: `docs/superpowers/plans/2026-06-11-imported-case-list.md`

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
Select-String -Path backend/src/debug_agent/storage/repository.py,backend/tests/storage/test_case_repository.py,backend/src/debug_agent/api/routes.py,backend/tests/api/test_case_listing.py,docs/superpowers/plans/2026-06-11-imported-case-list.md -Pattern 'ark-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
```

Expected: no output.

- [x] **Step 4: Commit**

Run:

```powershell
git add backend/src/debug_agent/storage/repository.py backend/tests/storage/test_case_repository.py backend/src/debug_agent/api/routes.py backend/tests/api/test_case_listing.py docs/superpowers/plans/2026-06-11-imported-case-list.md
git commit -m "feat(cases): list imported case summaries"
```

Expected: one commit containing only Phase 25 imported case listing changes and plan.

## Self-Review

- Spec coverage: The plan adds repository listing, API summaries, tests for JSONL/CSV imports, and full verification.
- Placeholder scan: No TBD, TODO, or vague implementation steps remain.
- Type consistency: `DebugCaseSummary` fields match `DebugCase` and `HumanNotes` field names.
