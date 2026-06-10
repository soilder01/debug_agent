# JSONL Case Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Import locally prepared JSONL debug cases into persistent storage and create debug jobs from them.

**Architecture:** Add a `debug_cases` SQLite table storing validated `DebugCase` JSON by `case_id`. Extend `DebugJobRepository` with case save/load methods, update `DebugJobService` to prefer persisted imported cases before fixture files, and expose `POST /imports/jsonl` for newline-delimited `DebugCase` payloads.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy 2, SQLite, pytest.

---

## File Structure

- Modify `backend/src/debug_agent/storage/models.py`: add `DebugCaseRow`.
- Modify `backend/src/debug_agent/storage/repository.py`: add `save_case()` and `get_case()`.
- Modify `backend/src/debug_agent/jobs/service.py`: load persisted cases before fixture cases.
- Modify `backend/src/debug_agent/api/routes.py`: add JSONL import request/response models and `POST /imports/jsonl`.
- Create `backend/tests/api/test_jsonl_import.py`: verify JSONL import creates persistent cases and jobs.
- Create `backend/tests/storage/test_case_repository.py`: verify case persistence roundtrip.
- Create `docs/superpowers/plans/2026-06-10-jsonl-case-import.md`: this plan.

## Task 1: Case Persistence

**Files:**
- Modify: `backend/src/debug_agent/storage/models.py`
- Modify: `backend/src/debug_agent/storage/repository.py`
- Create: `backend/tests/storage/test_case_repository.py`

- [ ] **Step 1: Write failing case repository test**

Create `backend/tests/storage/test_case_repository.py` with:

```python
import json

from debug_agent.cases.fixtures import load_fixture_case
from debug_agent.cases.models import DebugCase
from debug_agent.storage.database import create_sqlite_memory_session_factory
from debug_agent.storage.models import Base
from debug_agent.storage.repository import DebugJobRepository


def test_repository_persists_imported_debug_case() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    case = load_fixture_case("handwrite233").model_copy(update={"case_id": "imported-1"})

    repository.save_case(case)

    loaded = repository.get_case("imported-1")
    assert loaded == case
    assert isinstance(loaded, DebugCase)
    assert json.loads(case.model_dump_json())["case_id"] == "imported-1"
```

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
python -m pytest tests/storage/test_case_repository.py -q
```

Expected: FAIL because `DebugJobRepository.save_case()` does not exist.

- [ ] **Step 3: Add `DebugCaseRow` and repository methods**

In `backend/src/debug_agent/storage/models.py`, add:

```python
class DebugCaseRow(Base):
    __tablename__ = "debug_cases"

    case_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    case_json: Mapped[str] = mapped_column(Text)
```

In `backend/src/debug_agent/storage/repository.py`, import `DebugCase` and `DebugCaseRow`, then add:

```python
    def save_case(self, case: DebugCase) -> None:
        with self._lock:
            with self._session_factory() as session:
                session.merge(DebugCaseRow(case_id=case.case_id, case_json=case.model_dump_json()))
                session.commit()

    def get_case(self, case_id: str) -> DebugCase | None:
        with self._lock:
            with self._session_factory() as session:
                row = session.get(DebugCaseRow, case_id)
                if row is None:
                    return None
                return DebugCase.model_validate_json(row.case_json)
```

- [ ] **Step 4: Run storage test**

Run:

```powershell
python -m pytest tests/storage/test_case_repository.py -q
```

Expected: PASS.

## Task 2: Job Service Loads Imported Cases

**Files:**
- Modify: `backend/src/debug_agent/jobs/service.py`
- Create or modify: `backend/tests/jobs/test_service.py`

- [ ] **Step 1: Add failing service test**

Append this test to `backend/tests/jobs/test_service.py`:

```python
def test_job_service_submits_imported_case_from_repository() -> None:
    repository, service = create_service()
    case = load_fixture_case("handwrite233").model_copy(update={"case_id": "imported-1"})
    repository.save_case(case)

    submitted = service.submit_case_debug("imported-1")

    assert submitted.case_id == "imported-1"
    assert submitted.status == "created"
```

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
python -m pytest tests/jobs/test_service.py::test_job_service_submits_imported_case_from_repository -q
```

Expected: FAIL because `submit_case_debug()` still only calls `load_fixture_case()`.

- [ ] **Step 3: Update job service case loading**

In `backend/src/debug_agent/jobs/service.py`, add:

```python
from debug_agent.cases.models import DebugCase
```

Add private helper:

```python
    def _load_case(self, case_id: str) -> DebugCase:
        imported_case = self._repository.get_case(case_id)
        if imported_case is not None:
            return imported_case
        return load_fixture_case(case_id)
```

Replace both `load_fixture_case(...)` calls with `self._load_case(...)`.

- [ ] **Step 4: Run service tests**

Run:

```powershell
python -m pytest tests/jobs/test_service.py -q
```

Expected: PASS.

## Task 3: JSONL Import API

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Create: `backend/tests/api/test_jsonl_import.py`

- [ ] **Step 1: Write failing API test**

Create `backend/tests/api/test_jsonl_import.py` with:

```python
from fastapi.testclient import TestClient

from debug_agent.cases.fixtures import load_fixture_case
from debug_agent.main import app


def test_jsonl_import_persists_cases_and_creates_jobs() -> None:
    client = TestClient(app)
    case_json = load_fixture_case("handwrite233").model_copy(update={"case_id": "imported-jsonl-1"}).model_dump_json()

    response = client.post("/imports/jsonl", json={"jsonl": case_json, "create_jobs": True})

    assert response.status_code == 202
    body = response.json()
    assert body["imported_case_ids"] == ["imported-jsonl-1"]
    assert body["rejected_lines"] == []
    assert len(body["jobs"]) == 1
    assert body["jobs"][0]["case_id"] == "imported-jsonl-1"

    job_id = body["jobs"][0]["job_id"]
    status_response = client.get(f"/jobs/{job_id}")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "created"

    worker_response = client.post("/jobs/run-next")
    assert worker_response.status_code == 200
    assert worker_response.json()["job_id"] == job_id
    assert client.get(f"/jobs/{job_id}").json()["status"] == "completed"
```

- [ ] **Step 2: Run API test to verify failure**

Run:

```powershell
python -m pytest tests/api/test_jsonl_import.py -q
```

Expected: FAIL because `/imports/jsonl` does not exist.

- [ ] **Step 3: Add import models and endpoint**

In `backend/src/debug_agent/api/routes.py`, import `json` and `ValidationError`, and add:

```python
class JsonlImportRequest(BaseModel):
    jsonl: str
    create_jobs: bool = True


class JsonlRejectedLine(BaseModel):
    line_number: int
    error_message: str


class JsonlImportResponse(BaseModel):
    imported_case_ids: list[str]
    jobs: list[SubmittedDebugJob]
    rejected_lines: list[JsonlRejectedLine]
```

Add endpoint:

```python
@router.post("/imports/jsonl", status_code=202)
def import_jsonl_cases(request: JsonlImportRequest) -> JsonlImportResponse:
    imported_case_ids: list[str] = []
    jobs: list[SubmittedDebugJob] = []
    rejected_lines: list[JsonlRejectedLine] = []
    for line_number, line in enumerate(request.jsonl.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            case = DebugCase.model_validate(json.loads(line))
            job_repository.save_case(case)
            imported_case_ids.append(case.case_id)
            if request.create_jobs:
                jobs.append(job_service.submit_case_debug(case.case_id))
        except (json.JSONDecodeError, ValidationError, FileNotFoundError) as exc:
            rejected_lines.append(JsonlRejectedLine(line_number=line_number, error_message=str(exc)))
    return JsonlImportResponse(imported_case_ids=imported_case_ids, jobs=jobs, rejected_lines=rejected_lines)
```

- [ ] **Step 4: Run API tests**

Run:

```powershell
python -m pytest tests/api/test_jsonl_import.py tests/api/test_batch_job_submission.py -q
```

Expected: PASS.

## Task 4: Full Verification And Commit

**Files:**
- Modify: `backend/src/debug_agent/storage/models.py`
- Modify: `backend/src/debug_agent/storage/repository.py`
- Modify: `backend/src/debug_agent/jobs/service.py`
- Modify: `backend/src/debug_agent/api/routes.py`
- Modify: `backend/tests/jobs/test_service.py`
- Create: `backend/tests/storage/test_case_repository.py`
- Create: `backend/tests/api/test_jsonl_import.py`
- Create: `docs/superpowers/plans/2026-06-10-jsonl-case-import.md`

- [ ] **Step 1: Run full verification**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1 -Target all
```

Expected: backend tests, frontend tests, lint, and typecheck all pass.

- [ ] **Step 2: Run diagnostics**

Run diagnostics for edited backend files and new tests.

Expected: no diagnostics.

- [ ] **Step 3: Secret scan**

Run:

```powershell
git diff -- backend/src/debug_agent/storage/models.py backend/src/debug_agent/storage/repository.py backend/src/debug_agent/jobs/service.py backend/src/debug_agent/api/routes.py backend/tests/jobs/test_service.py backend/tests/storage/test_case_repository.py backend/tests/api/test_jsonl_import.py docs/superpowers/plans/2026-06-10-jsonl-case-import.md | Select-String -Pattern 'ark-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|ARK_API_KEY'
```

Expected: no real secret values.

- [ ] **Step 4: Commit**

Run:

```powershell
git add backend/src/debug_agent/storage/models.py backend/src/debug_agent/storage/repository.py backend/src/debug_agent/jobs/service.py backend/src/debug_agent/api/routes.py backend/tests/jobs/test_service.py backend/tests/storage/test_case_repository.py backend/tests/api/test_jsonl_import.py docs/superpowers/plans/2026-06-10-jsonl-case-import.md
git commit -m "feat(imports): add jsonl case import"
```

Expected: one commit containing only Phase 20 JSONL import changes and plan.

## Self-Review

- Spec coverage: The plan adds persistent imported cases, job service support, and a JSONL import API that creates jobs.
- Placeholder scan: No TBD, TODO, or vague implementation steps remain.
- Type consistency: Uses existing `DebugCase`, `SubmittedDebugJob`, `DebugJobRepository`, and job lifecycle fields.
