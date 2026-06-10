# CSV Case Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Import table-like CSV rows into persisted `DebugCase` records and optionally create debug jobs.

**Architecture:** Add a focused CSV mapper that converts each CSV row into a validated `DebugCase`. Reuse the existing imported case repository and job creation flow, and expose `POST /imports/csv` with the same response shape as JSONL import so the frontend can reuse import/batch UI later.

**Tech Stack:** Python 3.11, stdlib `csv` and `json`, Pydantic v2, FastAPI, pytest.

---

## File Structure

- Create `backend/src/debug_agent/imports/csv_cases.py`: parse CSV text into `DebugCase` instances and per-row rejections.
- Create `backend/src/debug_agent/imports/__init__.py`: package marker.
- Create `backend/tests/imports/test_csv_cases.py`: cover CSV row mapping and invalid row rejection.
- Modify `backend/src/debug_agent/api/routes.py`: add `CsvImportRequest` and `POST /imports/csv`.
- Create `backend/tests/api/test_csv_import.py`: verify CSV import persists cases, creates jobs, and worker can run them.
- Create `docs/superpowers/plans/2026-06-10-csv-case-import.md`: this plan.

## CSV Contract

Required columns:
- `case_id`
- `image_uri`
- `prompt`
- `golden_answer_json`
- `scoring_standard`
- `predictions_json`
- `avg_score`

Optional columns:
- `debug_status`
- `root_cause`

JSON column formats:

```json
{"answers":[{"box_id":1,"student_answer":"42"}]}
```

```json
[{"trial":1,"raw_output":"{\"answers\":[{\"box_id\":1,\"student_answer\":\"42\"}]}","score":1}]
```

## Task 1: CSV Mapper

**Files:**
- Create: `backend/src/debug_agent/imports/__init__.py`
- Create: `backend/src/debug_agent/imports/csv_cases.py`
- Create: `backend/tests/imports/test_csv_cases.py`

- [x] **Step 1: Write failing mapper tests**

Create `backend/tests/imports/test_csv_cases.py` with:

```python
import csv
import io
import json

from debug_agent.imports.csv_cases import parse_csv_cases


def csv_text(rows: list[dict[str, str]]) -> str:
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
    writer.writerows(rows)
    return output.getvalue()


def test_parse_csv_cases_maps_rows_to_debug_cases() -> None:
    golden_answer = {"answers": [{"box_id": 1, "student_answer": "42"}]}
    raw_output = json.dumps(golden_answer)
    predictions = [{"trial": 1, "raw_output": raw_output, "score": 1}]

    result = parse_csv_cases(
        csv_text(
            [
                {
                    "case_id": "csv-1",
                    "image_uri": "file://image.png",
                    "prompt": "Read the answer",
                    "golden_answer_json": json.dumps(golden_answer),
                    "scoring_standard": "exact match",
                    "predictions_json": json.dumps(predictions),
                    "avg_score": "1.0",
                    "debug_status": "pending",
                    "root_cause": "",
                }
            ]
        )
    )

    assert result.rejected_rows == []
    assert len(result.cases) == 1
    case = result.cases[0]
    assert case.case_id == "csv-1"
    assert case.golden_answer.answers[0].student_answer == "42"
    assert case.predictions[0].raw_output == raw_output
    assert case.avg_score == 1.0
    assert case.human_notes.debug_status == "pending"


def test_parse_csv_cases_reports_invalid_rows() -> None:
    result = parse_csv_cases(
        csv_text(
            [
                {
                    "case_id": "bad-csv",
                    "image_uri": "file://image.png",
                    "prompt": "Read the answer",
                    "golden_answer_json": "not-json",
                    "scoring_standard": "exact match",
                    "predictions_json": "[]",
                    "avg_score": "0.0",
                    "debug_status": "",
                    "root_cause": "",
                }
            ]
        )
    )

    assert result.cases == []
    assert len(result.rejected_rows) == 1
    assert result.rejected_rows[0].row_number == 2
    assert "not-json" in result.rejected_rows[0].error_message
```

- [x] **Step 2: Run mapper tests to verify failure**

Run:

```powershell
python -m pytest tests/imports/test_csv_cases.py -q
```

Expected: FAIL because `debug_agent.imports.csv_cases` does not exist.

- [x] **Step 3: Implement CSV mapper**

Create `backend/src/debug_agent/imports/__init__.py` as an empty file.

Create `backend/src/debug_agent/imports/csv_cases.py` with:

```python
import csv
import json
from io import StringIO

from pydantic import BaseModel, ValidationError

from debug_agent.cases.models import AnswerSet, DebugCase, HumanNotes, Prediction


class CsvRejectedRow(BaseModel):
    row_number: int
    error_message: str


class CsvCaseParseResult(BaseModel):
    cases: list[DebugCase]
    rejected_rows: list[CsvRejectedRow]


def parse_csv_cases(csv_text: str) -> CsvCaseParseResult:
    cases: list[DebugCase] = []
    rejected_rows: list[CsvRejectedRow] = []
    reader = csv.DictReader(StringIO(csv_text))
    for row_number, row in enumerate(reader, start=2):
        try:
            cases.append(_row_to_case(row))
        except (KeyError, ValueError, ValidationError, json.JSONDecodeError) as exc:
            rejected_rows.append(CsvRejectedRow(row_number=row_number, error_message=str(exc)))
    return CsvCaseParseResult(cases=cases, rejected_rows=rejected_rows)


def _row_to_case(row: dict[str, str | None]) -> DebugCase:
    golden_answer_text = _required(row, "golden_answer_json")
    predictions_text = _required(row, "predictions_json")
    return DebugCase(
        case_id=_required(row, "case_id"),
        image_uri=_required(row, "image_uri"),
        prompt=_required(row, "prompt"),
        golden_answer=AnswerSet.model_validate(json.loads(golden_answer_text)),
        scoring_standard=_required(row, "scoring_standard"),
        predictions=[Prediction.model_validate(item) for item in json.loads(predictions_text)],
        avg_score=float(_required(row, "avg_score")),
        human_notes=HumanNotes(
            debug_status=row.get("debug_status") or "",
            root_cause=row.get("root_cause") or "",
        ),
    )


def _required(row: dict[str, str | None], key: str) -> str:
    value = row.get(key)
    if value is None or value == "":
        raise ValueError(f"Missing required CSV column value: {key}")
    return value
```

- [x] **Step 4: Run mapper tests**

Run:

```powershell
python -m pytest tests/imports/test_csv_cases.py -q
```

Expected: PASS.

## Task 2: CSV Import API

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Create: `backend/tests/api/test_csv_import.py`

- [x] **Step 1: Write failing API test**

Create `backend/tests/api/test_csv_import.py` with:

```python
import csv
import io
import json

from fastapi.testclient import TestClient

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
            "case_id": "csv-import-1",
            "image_uri": "file://image.png",
            "prompt": "Read the answer",
            "golden_answer_json": json.dumps(golden_answer),
            "scoring_standard": "exact match",
            "predictions_json": json.dumps(predictions),
            "avg_score": "1.0",
            "debug_status": "pending",
            "root_cause": "",
        }
    )
    return output.getvalue()


def test_csv_import_persists_cases_and_creates_jobs() -> None:
    client = TestClient(app)

    response = client.post("/imports/csv", json={"csv_text": csv_text(), "create_jobs": True})

    assert response.status_code == 202
    body = response.json()
    assert body["imported_case_ids"] == ["csv-import-1"]
    assert body["rejected_rows"] == []
    assert len(body["jobs"]) == 1
    assert body["jobs"][0]["case_id"] == "csv-import-1"

    job_id = body["jobs"][0]["job_id"]
    worker_response = client.post("/jobs/run-next")
    assert worker_response.status_code == 200
    assert worker_response.json()["job_id"] == job_id
    status = client.get(f"/jobs/{job_id}").json()
    assert status["status"] == "completed"
    assert len(status["evidence_ids"]) == 6
```

- [x] **Step 2: Run API test to verify failure**

Run:

```powershell
python -m pytest tests/api/test_csv_import.py -q
```

Expected: FAIL because `/imports/csv` does not exist.

- [x] **Step 3: Add CSV import endpoint**

In `backend/src/debug_agent/api/routes.py`, import:

```python
from debug_agent.imports.csv_cases import CsvRejectedRow, parse_csv_cases
```

Add models:

```python
class CsvImportRequest(BaseModel):
    csv_text: str
    create_jobs: bool = True


class CsvImportResponse(BaseModel):
    imported_case_ids: list[str]
    jobs: list[SubmittedDebugJob]
    rejected_rows: list[CsvRejectedRow]
```

Add endpoint:

```python
@router.post("/imports/csv", status_code=202)
def import_csv_cases(request: CsvImportRequest) -> CsvImportResponse:
    parse_result = parse_csv_cases(request.csv_text)
    imported_case_ids: list[str] = []
    jobs: list[SubmittedDebugJob] = []
    for case in parse_result.cases:
        job_repository.save_case(case)
        imported_case_ids.append(case.case_id)
        if request.create_jobs:
            jobs.append(job_service.submit_case_debug(case.case_id))
    return CsvImportResponse(
        imported_case_ids=imported_case_ids,
        jobs=jobs,
        rejected_rows=parse_result.rejected_rows,
    )
```

- [x] **Step 4: Run API import tests**

Run:

```powershell
python -m pytest tests/api/test_csv_import.py tests/api/test_jsonl_import.py -q
```

Expected: PASS.

## Task 3: Full Verification And Commit

**Files:**
- Create: `backend/src/debug_agent/imports/__init__.py`
- Create: `backend/src/debug_agent/imports/csv_cases.py`
- Modify: `backend/src/debug_agent/api/routes.py`
- Create: `backend/tests/imports/test_csv_cases.py`
- Create: `backend/tests/api/test_csv_import.py`
- Create: `docs/superpowers/plans/2026-06-10-csv-case-import.md`

- [x] **Step 1: Run full verification**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1 -Target all
```

Expected: backend tests, frontend tests, lint, and typecheck all pass.

- [x] **Step 2: Run diagnostics**

Run diagnostics for edited backend files and new tests.

Expected: no diagnostics.

- [x] **Step 3: Secret scan**

Run:

```powershell
git diff -- backend/src/debug_agent/imports/__init__.py backend/src/debug_agent/imports/csv_cases.py backend/src/debug_agent/api/routes.py backend/tests/imports/test_csv_cases.py backend/tests/api/test_csv_import.py docs/superpowers/plans/2026-06-10-csv-case-import.md | Select-String -Pattern 'ark-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|ARK_API_KEY'
```

Expected: no real secret values.

- [x] **Step 4: Commit**

Run:

```powershell
git add backend/src/debug_agent/imports/__init__.py backend/src/debug_agent/imports/csv_cases.py backend/src/debug_agent/api/routes.py backend/tests/imports/test_csv_cases.py backend/tests/api/test_csv_import.py docs/superpowers/plans/2026-06-10-csv-case-import.md
git commit -m "feat(imports): add csv case import"
```

Expected: one commit containing only Phase 22 CSV import changes and plan.

## Self-Review

- Spec coverage: The plan adds a CSV mapper and API that convert tabular rows into persisted `DebugCase` records and jobs.
- Placeholder scan: No TBD, TODO, or vague implementation steps remain.
- Type consistency: Uses existing `DebugCase`, `SubmittedDebugJob`, imported case persistence, and job execution flow.
