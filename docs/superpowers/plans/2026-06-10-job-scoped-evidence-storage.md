# Job Scoped Evidence Storage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure repeated debug jobs for the same case retain independent evidence rows instead of overwriting each other.

**Architecture:** Change `EvidenceRow` from a globally unique `evidence_id` primary key to a composite primary key of `(job_id, evidence_id)`. Keep the external API and repository method `list_evidence_ids(job_id)` returning the original evidence ids, so frontend and job status contracts remain stable while persistence becomes job-scoped.

**Tech Stack:** Python 3.11, SQLAlchemy 2, SQLite, pytest.

---

## File Structure

- Modify `backend/src/debug_agent/storage/models.py`: make `job_id` and `evidence_id` composite primary key columns for `EvidenceRow`.
- Modify `backend/src/debug_agent/storage/database.py`: add a lightweight startup migration that converts legacy global `evidence_id` primary key tables into job-scoped composite primary key tables.
- Modify `backend/src/debug_agent/storage/repository.py`: keep `save_evidence()` and `list_evidence_ids()` behavior stable; `session.merge()` will become job-scoped once the model has a composite primary key. Serialize repository session access with a lock so the API polling thread and worker thread do not concurrently use the same in-memory SQLite connection.
- Modify `backend/src/debug_agent/api/routes.py`: call the schema helper instead of raw `Base.metadata.create_all(engine)`.
- Modify `backend/tests/storage/test_repository.py`: update direct `session.get()` usage for composite primary key and add a regression test proving duplicate evidence ids across different jobs are both retained.
- Modify `backend/tests/api/test_worker_control.py`: strengthen worker API evidence count assertion back to full evidence count once storage is job-scoped.

## Task 1: Repository Regression Test

**Files:**
- Modify: `backend/tests/storage/test_repository.py`

- [ ] **Step 1: Write failing duplicate-evidence regression test**

Append this test to `backend/tests/storage/test_repository.py`:

```python
def test_repository_keeps_same_evidence_ids_for_different_jobs() -> None:
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
    repository.create_job(job_id="job-2", case_id="case-1")
    repository.save_evidence(job_id="job-1", case_id="case-1", evidence=[evidence])
    repository.save_evidence(job_id="job-2", case_id="case-1", evidence=[evidence])

    assert repository.list_evidence_ids("job-1") == ["case-1:baseline:0"]
    assert repository.list_evidence_ids("job-2") == ["case-1:baseline:0"]
```

- [ ] **Step 2: Run the regression test to verify it fails**

Run:

```powershell
python -m pytest tests/storage/test_repository.py::test_repository_keeps_same_evidence_ids_for_different_jobs -q
```

Expected: FAIL because the second `save_evidence()` overwrites the first row by global `evidence_id`, leaving `job-1` with no evidence.

## Task 2: Composite Primary Key

**Files:**
- Modify: `backend/src/debug_agent/storage/models.py`
- Modify: `backend/tests/storage/test_repository.py`

- [ ] **Step 1: Update `EvidenceRow` primary key**

In `backend/src/debug_agent/storage/models.py`, change `EvidenceRow` columns to:

```python
class EvidenceRow(Base):
    __tablename__ = "evidence"

    job_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    evidence_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(120), index=True)
    step_name: Mapped[str] = mapped_column(String(120), index=True)
    trial: Mapped[int] = mapped_column(Integer)
    score: Mapped[int] = mapped_column(Integer)
    reasons_json: Mapped[str] = mapped_column(Text)
    raw_output: Mapped[str] = mapped_column(Text)
```

- [ ] **Step 2: Update direct `session.get()` test**

In `backend/tests/storage/test_repository.py`, update:

```python
        assert session.get(EvidenceRow, "evidence-1").step_name == "baseline"
```

to:

```python
        row = session.get(EvidenceRow, ("job-1", "evidence-1"))
        assert row is not None
        assert row.step_name == "baseline"
```

- [ ] **Step 3: Run storage tests**

Run:

```powershell
python -m pytest tests/storage/test_repository.py -q
```

Expected: PASS.

## Task 3: Worker API Evidence Count Regression

**Files:**
- Modify: `backend/tests/api/test_worker_control.py`
- Modify: `backend/src/debug_agent/storage/database.py`
- Modify: `backend/src/debug_agent/storage/repository.py`
- Modify: `backend/src/debug_agent/api/routes.py`

- [ ] **Step 1: Strengthen worker API assertion**

In `backend/tests/api/test_worker_control.py`, update:

```python
    assert len(status_response.json()["evidence_ids"]) > 0
```

to:

```python
    assert len(status_response.json()["evidence_ids"]) == 6
```

- [ ] **Step 2: Run API worker control tests**

Run:

```powershell
python -m pytest tests/api/test_worker_control.py -q
```

Expected: PASS with 3 tests.

## Task 3.5: Startup Migration And Thread-Safe Repository Access

**Files:**
- Modify: `backend/src/debug_agent/storage/database.py`
- Modify: `backend/src/debug_agent/storage/repository.py`
- Modify: `backend/src/debug_agent/api/routes.py`
- Modify: `backend/tests/storage/test_repository.py`

- [ ] **Step 1: Add legacy schema migration coverage**

Add a storage test that creates the old `evidence` table with `evidence_id` as the only primary key, calls `ensure_database_schema(engine)`, then inserts the same `evidence_id` for a second `job_id`.

Expected: both `("job-1", evidence_id)` and `("job-2", evidence_id)` can be read.

- [ ] **Step 2: Add startup schema helper**

Add `ensure_database_schema(engine)` in `backend/src/debug_agent/storage/database.py`.

Expected: it detects `evidence` tables whose primary key is `["evidence_id"]`, renames the old table, creates the new `EvidenceRow` table, copies rows, drops the legacy table, then calls `Base.metadata.create_all(engine)`.

- [ ] **Step 3: Use the schema helper in routes**

Replace `Base.metadata.create_all(engine)` in `backend/src/debug_agent/api/routes.py` with `ensure_database_schema(engine)`.

Expected: app startup can migrate old local SQLite files before serving worker APIs.

- [ ] **Step 4: Serialize repository sessions**

Add a `threading.RLock` to `DebugJobRepository` and wrap each method that opens a session with that lock.

Expected: worker thread writes and API polling reads are serialized for the same repository instance, which prevents in-memory SQLite connection races.

- [ ] **Step 5: Run focused worker and storage tests**

Run:

```powershell
python -m pytest tests/api/test_worker_control.py::test_worker_start_consumes_submitted_debug_job tests/storage/test_repository.py tests/jobs/test_worker.py -q
```

Expected: PASS.

## Task 4: Full Verification And Commit

**Files:**
- Modify: `backend/src/debug_agent/api/routes.py`
- Modify: `backend/src/debug_agent/storage/database.py`
- Modify: `backend/src/debug_agent/storage/models.py`
- Modify: `backend/src/debug_agent/storage/repository.py`
- Modify: `backend/tests/storage/test_repository.py`
- Modify: `backend/tests/api/test_worker_control.py`
- Create: `docs/superpowers/plans/2026-06-10-job-scoped-evidence-storage.md`

- [ ] **Step 1: Run full verification**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1 -Target all
```

Expected:
- Backend tests pass.
- Frontend tests pass.
- Backend lint passes.
- Frontend lint passes.
- Backend typecheck passes.
- Frontend typecheck passes.

- [ ] **Step 2: Run diagnostics**

Run diagnostics for:
- `backend/src/debug_agent/storage/models.py`
- `backend/tests/storage/test_repository.py`
- `backend/tests/api/test_worker_control.py`

Expected: no diagnostics.

- [ ] **Step 3: Secret scan**

Run:

```powershell
git diff -- backend/src/debug_agent/api/routes.py backend/src/debug_agent/storage/database.py backend/src/debug_agent/storage/models.py backend/src/debug_agent/storage/repository.py backend/tests/storage/test_repository.py backend/tests/api/test_worker_control.py docs/superpowers/plans/2026-06-10-job-scoped-evidence-storage.md | Select-String -Pattern 'ark-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|ARK_API_KEY'
```

Expected: no matches.

- [ ] **Step 4: Commit**

Run:

```powershell
git add backend/src/debug_agent/api/routes.py backend/src/debug_agent/storage/database.py backend/src/debug_agent/storage/models.py backend/src/debug_agent/storage/repository.py backend/tests/storage/test_repository.py backend/tests/api/test_worker_control.py docs/superpowers/plans/2026-06-10-job-scoped-evidence-storage.md
git commit -m "fix(storage): scope evidence rows by job"
```

Expected: one commit containing only Phase 17 evidence storage isolation changes and plan.

## Self-Review

- Spec coverage: This plan fixes evidence overwrite for repeated jobs of the same case and restores exact worker API evidence count assertions.
- Placeholder scan: No TBD, TODO, or vague implementation steps remain.
- Type consistency: The plan uses existing `EvidenceRow`, `DebugJobRepository`, `ExperimentEvidence`, and `JudgeResult` names exactly as currently defined.
