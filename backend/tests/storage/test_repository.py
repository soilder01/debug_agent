from pathlib import Path

from debug_agent.experiments.runner import ExperimentEvidence
from debug_agent.judging.runner import JudgeResult
from debug_agent.storage.database import create_sqlite_memory_session_factory, create_sqlite_session_factory
from debug_agent.storage.models import Base, DebugJobRow, EvidenceRow
from debug_agent.storage.repository import DebugJobRepository


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


def test_sqlite_file_session_factory_persists_rows_between_sessions() -> None:
    database_path = Path(".pytest-cache") / "debug-agent-storage-test.db"
    database_path.parent.mkdir(exist_ok=True)
    database_path.unlink(missing_ok=True)
    database_url = f"sqlite+pysqlite:///{database_path.resolve().as_posix()}"
    engine = None
    try:
        session_factory, engine = create_sqlite_session_factory(database_url)
        Base.metadata.create_all(engine)

        with session_factory() as session:
            session.add(DebugJobRow(job_id="job-1", case_id="case-1", status="created"))
            session.commit()

        with session_factory() as session:
            assert session.get(DebugJobRow, "job-1").case_id == "case-1"
    finally:
        if engine is not None:
            engine.dispose()
        database_path.unlink(missing_ok=True)


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


def test_repository_created_job_starts_with_zero_attempts() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)

    repository.create_job(job_id="job-1", case_id="case-1")

    job = repository.get_job("job-1")
    assert job is not None
    assert job.attempt_count == 0


def test_repository_marks_job_failed_with_error_message() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)

    repository.create_job(job_id="job-1", case_id="case-1")
    repository.mark_failed("job-1", "model adapter timeout")

    job = repository.get_job("job-1")
    assert job is not None
    assert job.status == "failed"
    assert job.error_message == "model adapter timeout"


def test_repository_returns_oldest_created_job() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)

    repository.create_job(job_id="job-2", case_id="case-2")
    repository.create_job(job_id="job-1", case_id="case-1")
    repository.mark_running("job-2")

    job = repository.get_next_created_job()

    assert job is not None
    assert job.job_id == "job-1"


def test_repository_claims_created_job_once() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    repository.create_job(job_id="job-1", case_id="case-1")

    claimed = repository.claim_next_created_job()
    second_claim = repository.claim_next_created_job()

    assert claimed is not None
    assert claimed.job_id == "job-1"
    assert claimed.status == "running"
    assert claimed.attempt_count == 1
    assert second_claim is None


def test_repository_releases_running_job_for_retry() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    repository.create_job(job_id="job-1", case_id="case-1")
    claimed = repository.claim_next_created_job()
    assert claimed is not None

    repository.release_for_retry("job-1", "transient model error")

    job = repository.get_job("job-1")
    assert job is not None
    assert job.status == "created"
    assert job.attempt_count == 1
    assert job.error_message == "transient model error"
