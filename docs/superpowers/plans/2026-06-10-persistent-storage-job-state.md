# Persistent Storage Job State Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add SQLite-compatible persistent storage for debug jobs and replay evidence, while keeping tests deterministic and local.

**Architecture:** Introduce a focused SQLAlchemy storage module with table definitions, engine/session helpers, and a repository layer. The API creates a debug job, transitions it through running/completed states, persists evidence records, and exposes job status through a new endpoint. The existing in-memory artifact store remains as a short-term cache for detail lookup, while the persistent repository becomes the durable source for job state and evidence metadata.

**Tech Stack:** Python 3.11, SQLAlchemy 2, SQLite, Pydantic v2, FastAPI, pytest.

---

## Files

```text
backend/src/debug_agent/storage/__init__.py
backend/src/debug_agent/storage/database.py
backend/src/debug_agent/storage/models.py
backend/src/debug_agent/storage/repository.py
backend/src/debug_agent/api/routes.py
backend/tests/storage/__init__.py
backend/tests/storage/test_repository.py
backend/tests/api/test_job_status.py
```

## Task 1: SQLAlchemy Storage Foundation

**Files:**
- Create: `backend/src/debug_agent/storage/__init__.py`
- Create: `backend/src/debug_agent/storage/database.py`
- Create: `backend/src/debug_agent/storage/models.py`
- Create: `backend/tests/storage/__init__.py`
- Create: `backend/tests/storage/test_repository.py`

- [ ] **Step 1: Write database schema test**

Create `backend/tests/storage/test_repository.py`:

```python
from debug_agent.storage.database import create_sqlite_memory_session_factory
from debug_agent.storage.models import Base, DebugJobRow, EvidenceRow


def test_storage_tables_can_be_created() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()

    Base.metadata.create_all(engine)

    with session_factory() as session:
        session.add(DebugJobRow(job_id="job-1", case_id="case-1", status="created"))
        session.add(
            EvidenceRow(
                evidence_id="evidence-1",
                job_id="job-1",
                case_id="case-1",
                step_name="baseline",
                trial=0,
                score=0,
                reasons_json="[\"box 1 mismatch\"]",
                raw_output="{\"answers\":[]}",
            )
        )
        session.commit()

    with session_factory() as session:
        assert session.get(DebugJobRow, "job-1").status == "created"
        assert session.get(EvidenceRow, "evidence-1").step_name == "baseline"
```

- [ ] **Step 2: Run failing test**

Run: `cd backend && python -m pytest tests/storage/test_repository.py -q`
Expected: fails because storage modules do not exist.

- [ ] **Step 3: Implement database helpers**

Create `backend/src/debug_agent/storage/database.py`:

```python
from collections.abc import Callable

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


def create_sqlite_memory_session_factory() -> tuple[Callable[[], Session], Engine]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return sessionmaker(bind=engine, expire_on_commit=False), engine
```

- [ ] **Step 4: Implement models**

Create `backend/src/debug_agent/storage/models.py`:

```python
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class DebugJobRow(Base):
    __tablename__ = "debug_jobs"

    job_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(120), index=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class EvidenceRow(Base):
    __tablename__ = "evidence"

    evidence_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(80), index=True)
    case_id: Mapped[str] = mapped_column(String(120), index=True)
    step_name: Mapped[str] = mapped_column(String(120), index=True)
    trial: Mapped[int] = mapped_column(Integer)
    score: Mapped[int] = mapped_column(Integer)
    reasons_json: Mapped[str] = mapped_column(Text)
    raw_output: Mapped[str] = mapped_column(Text)
```

- [ ] **Step 5: Verify and commit**

Run:
```bash
cd backend && python -m pytest tests/storage/test_repository.py -q
cd backend && python -m ruff check src tests && python -m mypy src
git add backend/src/debug_agent/storage backend/tests/storage
git commit -m "feat: add SQLAlchemy storage foundation"
```

## Task 2: Job Repository

**Files:**
- Create: `backend/src/debug_agent/storage/repository.py`
- Modify: `backend/tests/storage/test_repository.py`

- [ ] **Step 1: Add repository tests**

Append:

```python
from debug_agent.experiments.runner import ExperimentEvidence
from debug_agent.judging.runner import JudgeResult
from debug_agent.storage.repository import DebugJobRepository


def test_repository_tracks_job_state_and_evidence() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    evidence = ExperimentEvidence(
        evidence_id="case-1:baseline:0",
        step_name="baseline",
        trial=0,
        raw_output="{\"answers\":[]}",
        judge=JudgeResult(score=0, reasons=["box 1 mismatch"]),
    )

    repository.create_job(job_id="job-1", case_id="case-1")
    repository.mark_running("job-1")
    repository.save_evidence(job_id="job-1", case_id="case-1", evidence=[evidence])
    repository.mark_completed("job-1")

    job = repository.get_job("job-1")
    assert job is not None
    assert job.status == "completed"
    assert repository.list_evidence_ids("job-1") == ["case-1:baseline:0"]
```

- [ ] **Step 2: Run failing test**

Run: `cd backend && python -m pytest tests/storage/test_repository.py -q`
Expected: fails because repository does not exist.

- [ ] **Step 3: Implement repository**

Create `backend/src/debug_agent/storage/repository.py`:

```python
import json
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from debug_agent.experiments.runner import ExperimentEvidence
from debug_agent.storage.models import DebugJobRow, EvidenceRow


class DebugJobRepository:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def create_job(self, job_id: str, case_id: str) -> None:
        with self._session_factory() as session:
            session.add(DebugJobRow(job_id=job_id, case_id=case_id, status="created"))
            session.commit()

    def mark_running(self, job_id: str) -> None:
        self._set_status(job_id, "running")

    def mark_completed(self, job_id: str) -> None:
        self._set_status(job_id, "completed")

    def mark_failed(self, job_id: str, error_message: str) -> None:
        with self._session_factory() as session:
            job = session.get(DebugJobRow, job_id)
            if job is None:
                return
            job.status = "failed"
            job.error_message = error_message
            session.commit()

    def get_job(self, job_id: str) -> DebugJobRow | None:
        with self._session_factory() as session:
            return session.get(DebugJobRow, job_id)

    def save_evidence(
        self, job_id: str, case_id: str, evidence: list[ExperimentEvidence]
    ) -> None:
        with self._session_factory() as session:
            for item in evidence:
                session.merge(
                    EvidenceRow(
                        evidence_id=item.evidence_id,
                        job_id=job_id,
                        case_id=case_id,
                        step_name=item.step_name,
                        trial=item.trial,
                        score=item.judge.score,
                        reasons_json=json.dumps(item.judge.reasons, ensure_ascii=False),
                        raw_output=item.raw_output,
                    )
                )
            session.commit()

    def list_evidence_ids(self, job_id: str) -> list[str]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(EvidenceRow.evidence_id).where(EvidenceRow.job_id == job_id)
            ).all()
            return sorted(rows)

    def _set_status(self, job_id: str, status: str) -> None:
        with self._session_factory() as session:
            job = session.get(DebugJobRow, job_id)
            if job is None:
                return
            job.status = status
            session.commit()
```

- [ ] **Step 4: Verify and commit**

Run:
```bash
cd backend && python -m pytest tests/storage/test_repository.py -q
cd backend && python -m ruff check src tests && python -m mypy src
git add backend/src/debug_agent/storage/repository.py backend/tests/storage/test_repository.py
git commit -m "feat: add debug job repository"
```

## Task 3: API Job State

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Create: `backend/tests/api/test_job_status.py`

- [ ] **Step 1: Write API test**

Create `backend/tests/api/test_job_status.py`:

```python
from fastapi.testclient import TestClient

from debug_agent.main import app


def test_debug_case_returns_job_and_status_endpoint() -> None:
    client = TestClient(app)

    debug_response = client.post("/cases/handwrite233/debug")
    body = debug_response.json()
    job_id = body["job_id"]

    status_response = client.get(f"/jobs/{job_id}")

    assert status_response.status_code == 200
    status_body = status_response.json()
    assert status_body["job_id"] == job_id
    assert status_body["case_id"] == "handwrite233"
    assert status_body["status"] == "completed"
    assert status_body["evidence_ids"] == body["experiment_summary"]["evidence_ids"]
```

- [ ] **Step 2: Run failing test**

Run: `cd backend && python -m pytest tests/api/test_job_status.py -q`
Expected: fails because report has no job id and jobs route does not exist.

- [ ] **Step 3: Add `job_id` to DebugReport**

Modify `backend/src/debug_agent/reports/generator.py` so `DebugReport` has `job_id: str | None = None` and `generate_initial_report(..., job_id: str | None = None)`.

- [ ] **Step 4: Add API repository singleton and job route**

In `routes.py`, create SQLite in-memory repository at module level, create/mark job in `debug_case`, save evidence in repository, and add `GET /jobs/{job_id}` returning a dict with `job_id`, `case_id`, `status`, `error_message`, and `evidence_ids`.

- [ ] **Step 5: Verify and commit**

Run:
```bash
cd backend && python -m pytest tests/api/test_job_status.py -q
cd backend && python -m pytest tests -q && python -m ruff check src tests && python -m mypy src
git add backend/src/debug_agent/api/routes.py backend/src/debug_agent/reports/generator.py backend/tests/api/test_job_status.py
git commit -m "feat: expose debug job status"
```

## Task 4: Full Verification

- [ ] **Step 1: Run full verification**

Run: `powershell -ExecutionPolicy Bypass -File scripts/verify.ps1 -Target all`
Expected: all checks pass.

- [ ] **Step 2: Check working tree**

Run: `git status --short --branch`
Expected: clean working tree.

---

## Self-Review

Spec coverage:
- Persistent schema exists for jobs and evidence.
- Repository tracks job state transitions.
- API exposes job status and evidence ids.
- Tests run without live model calls or external services.

Placeholder scan:
- No placeholder or open-ended implementation steps are present.

Type consistency:
- `DebugJobRow`, `EvidenceRow`, and `DebugJobRepository` are consistently used by storage tests and API.
