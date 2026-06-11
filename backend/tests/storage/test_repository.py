from pathlib import Path

from debug_agent.experiments.runner import ExperimentEvidence
from debug_agent.judging.runner import JudgeResult
from debug_agent.storage.database import (
    create_sqlite_memory_session_factory,
    create_sqlite_session_factory,
    ensure_database_schema,
)
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
                model_name="fake",
                model_provider="fake",
                model_id="fake",
                score=0,
                reasons_json="[\"box 1 mismatch\"]",
                raw_output="{\"answers\":[]}",
            )
        )
        session.commit()

    with session_factory() as session:
        assert session.get(DebugJobRow, "job-1").status == "created"
        row = session.get(EvidenceRow, ("job-1", "evidence-1"))
        assert row is not None
        assert row.step_name == "baseline"
        assert row.model_name == "fake"
        assert row.model_provider == "fake"
        assert row.model_id == "fake"


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
        model_name="seed2-lite",
        model_provider="ark",
        model_id="ep-seed2-lite",
        request_summary={"prompt_length": 31, "has_image": True, "image_uri_scheme": "tos"},
        latency_ms=42,
        response_parse_error="Expecting value: line 1 column 1 (char 0)",
        model_call_error_type="TimeoutError",
        model_call_error_message="model request timed out",
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
    with session_factory() as session:
        row = session.get(EvidenceRow, ("job-1", "case-1:baseline:0"))
        assert row is not None
        assert row.model_name == "seed2-lite"
        assert row.model_provider == "ark"
        assert row.model_id == "ep-seed2-lite"
        assert row.request_summary_json == (
            "{\"prompt_length\": 31, \"has_image\": true, \"image_uri_scheme\": \"tos\"}"
        )
        assert row.latency_ms == 42
        assert row.response_parse_error == "Expecting value: line 1 column 1 (char 0)"
        assert row.model_call_error_type == "TimeoutError"
        assert row.model_call_error_message == "model request timed out"

    restored = repository.get_evidence("job-1", "case-1:baseline:0")
    assert restored is not None
    assert restored.evidence_id == "case-1:baseline:0"
    assert restored.step_name == "baseline"
    assert restored.trial == 0
    assert restored.model_name == "seed2-lite"
    assert restored.model_provider == "ark"
    assert restored.model_id == "ep-seed2-lite"
    assert restored.request_summary == {
        "prompt_length": 31,
        "has_image": True,
        "image_uri_scheme": "tos",
    }
    assert restored.latency_ms == 42
    assert restored.response_parse_error == "Expecting value: line 1 column 1 (char 0)"
    assert restored.model_call_error_type == "TimeoutError"
    assert restored.model_call_error_message == "model request timed out"
    assert restored.raw_output == "{\"answers\":[]}"
    assert restored.judge.score == 0
    assert restored.judge.reasons == ["box 1 mismatch"]


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


def test_repository_keeps_same_evidence_ids_for_different_jobs() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    evidence = ExperimentEvidence(
        evidence_id="case-1:baseline:0",
        step_name="baseline",
        trial=0,
        model_name="fake",
        model_provider="fake",
        model_id="fake",
        request_summary={"prompt_length": 1, "has_image": False, "image_uri_scheme": ""},
        latency_ms=1,
        raw_output="{\"answers\":[]}",
        judge=JudgeResult(score=0, reasons=["box 1 mismatch"]),
    )

    repository.create_job(job_id="job-1", case_id="case-1")
    repository.create_job(job_id="job-2", case_id="case-1")
    repository.save_evidence(job_id="job-1", case_id="case-1", evidence=[evidence])
    repository.save_evidence(job_id="job-2", case_id="case-1", evidence=[evidence])

    assert repository.list_evidence_ids("job-1") == ["case-1:baseline:0"]
    assert repository.list_evidence_ids("job-2") == ["case-1:baseline:0"]


def test_repository_counts_evidence_error_categories() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    repository.create_job(job_id="job-1", case_id="case-1")
    repository.save_evidence(
        job_id="job-1",
        case_id="case-1",
        evidence=[
            ExperimentEvidence(
                evidence_id="case-1:baseline:0",
                step_name="baseline",
                trial=0,
                raw_output="{\"answers\":[]}",
                judge=JudgeResult(score=0, reasons=["student_answer_mismatch"]),
            ),
            ExperimentEvidence(
                evidence_id="case-1:parse:0",
                step_name="parse",
                trial=0,
                response_parse_error="Expecting value",
                raw_output="not-json",
                judge=JudgeResult(score=0, reasons=["response_parse_error"]),
            ),
            ExperimentEvidence(
                evidence_id="case-1:model:0",
                step_name="model",
                trial=0,
                model_call_error_type="TimeoutError",
                model_call_error_message="model request timed out",
                raw_output="",
                judge=JudgeResult(score=0, reasons=["model_call_error"]),
            ),
        ],
    )

    assert repository.count_evidence_errors("job-1") == {
        "total_evidence": 3,
        "failed_judgements": 3,
        "response_parse_errors": 1,
        "model_call_errors": 1,
    }


def test_database_schema_migrates_legacy_global_evidence_primary_key() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE evidence (
                evidence_id VARCHAR(200) NOT NULL PRIMARY KEY,
                job_id VARCHAR(80) NOT NULL,
                case_id VARCHAR(120) NOT NULL,
                step_name VARCHAR(120) NOT NULL,
                trial INTEGER NOT NULL,
                score INTEGER NOT NULL,
                reasons_json TEXT NOT NULL,
                raw_output TEXT NOT NULL
            )
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO evidence (
                evidence_id,
                job_id,
                case_id,
                step_name,
                trial,
                score,
                reasons_json,
                raw_output
            )
            VALUES (
                'case-1:baseline:0',
                'job-1',
                'case-1',
                'baseline',
                0,
                0,
                '[]',
                '{"answers":[]}'
            )
            """
        )

    ensure_database_schema(engine)

    with session_factory() as session:
        legacy_row = session.get(EvidenceRow, ("job-1", "case-1:baseline:0"))
        session.add(
            EvidenceRow(
                job_id="job-2",
                evidence_id="case-1:baseline:0",
                case_id="case-1",
                step_name="baseline",
                trial=0,
                score=1,
                reasons_json="[]",
                raw_output="{\"answers\":[]}",
            )
        )
        session.commit()

    with session_factory() as session:
        assert legacy_row is not None
        assert session.get(EvidenceRow, ("job-1", "case-1:baseline:0")) is not None
        assert session.get(EvidenceRow, ("job-2", "case-1:baseline:0")) is not None


def test_database_schema_adds_missing_evidence_model_name_column() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE evidence (
                job_id VARCHAR(80) NOT NULL,
                evidence_id VARCHAR(200) NOT NULL,
                case_id VARCHAR(120) NOT NULL,
                step_name VARCHAR(120) NOT NULL,
                trial INTEGER NOT NULL,
                score INTEGER NOT NULL,
                reasons_json TEXT NOT NULL,
                raw_output TEXT NOT NULL,
                PRIMARY KEY (job_id, evidence_id)
            )
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO evidence (
                job_id,
                evidence_id,
                case_id,
                step_name,
                trial,
                score,
                reasons_json,
                raw_output
            )
            VALUES (
                'job-1',
                'case-1:baseline:0',
                'case-1',
                'baseline',
                0,
                0,
                '[]',
                '{"answers":[]}'
            )
            """
        )

    ensure_database_schema(engine)

    with session_factory() as session:
        row = session.get(EvidenceRow, ("job-1", "case-1:baseline:0"))
        assert row is not None
        assert row.model_name == ""


def test_database_schema_adds_missing_evidence_provider_and_model_id_columns() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE evidence (
                job_id VARCHAR(80) NOT NULL,
                evidence_id VARCHAR(200) NOT NULL,
                case_id VARCHAR(120) NOT NULL,
                step_name VARCHAR(120) NOT NULL,
                trial INTEGER NOT NULL,
                model_name VARCHAR(120) NOT NULL DEFAULT '',
                score INTEGER NOT NULL,
                reasons_json TEXT NOT NULL,
                raw_output TEXT NOT NULL,
                PRIMARY KEY (job_id, evidence_id)
            )
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO evidence (
                job_id,
                evidence_id,
                case_id,
                step_name,
                trial,
                model_name,
                score,
                reasons_json,
                raw_output
            )
            VALUES (
                'job-1',
                'case-1:baseline:0',
                'case-1',
                'baseline',
                0,
                'seed2-lite',
                0,
                '[]',
                '{"answers":[]}'
            )
            """
        )

    ensure_database_schema(engine)

    with session_factory() as session:
        row = session.get(EvidenceRow, ("job-1", "case-1:baseline:0"))
        assert row is not None
        assert row.model_provider == ""
        assert row.model_id == ""


def test_database_schema_adds_missing_evidence_request_summary_and_latency_columns() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE evidence (
                job_id VARCHAR(80) NOT NULL,
                evidence_id VARCHAR(200) NOT NULL,
                case_id VARCHAR(120) NOT NULL,
                step_name VARCHAR(120) NOT NULL,
                trial INTEGER NOT NULL,
                model_name VARCHAR(120) NOT NULL DEFAULT '',
                model_provider VARCHAR(80) NOT NULL DEFAULT '',
                model_id VARCHAR(160) NOT NULL DEFAULT '',
                score INTEGER NOT NULL,
                reasons_json TEXT NOT NULL,
                raw_output TEXT NOT NULL,
                PRIMARY KEY (job_id, evidence_id)
            )
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO evidence (
                job_id,
                evidence_id,
                case_id,
                step_name,
                trial,
                score,
                reasons_json,
                raw_output
            )
            VALUES (
                'job-1',
                'case-1:baseline:0',
                'case-1',
                'baseline',
                0,
                0,
                '[]',
                '{"answers":[]}'
            )
            """
        )

    ensure_database_schema(engine)

    with session_factory() as session:
        row = session.get(EvidenceRow, ("job-1", "case-1:baseline:0"))
        assert row is not None
        assert row.request_summary_json == "{}"
        assert row.latency_ms == 0


def test_database_schema_adds_missing_evidence_parse_error_column() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE evidence (
                job_id VARCHAR(80) NOT NULL,
                evidence_id VARCHAR(200) NOT NULL,
                case_id VARCHAR(120) NOT NULL,
                step_name VARCHAR(120) NOT NULL,
                trial INTEGER NOT NULL,
                model_name VARCHAR(120) NOT NULL DEFAULT '',
                model_provider VARCHAR(80) NOT NULL DEFAULT '',
                model_id VARCHAR(160) NOT NULL DEFAULT '',
                request_summary_json TEXT NOT NULL DEFAULT '{}',
                latency_ms INTEGER NOT NULL DEFAULT 0,
                score INTEGER NOT NULL,
                reasons_json TEXT NOT NULL,
                raw_output TEXT NOT NULL,
                PRIMARY KEY (job_id, evidence_id)
            )
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO evidence (
                job_id,
                evidence_id,
                case_id,
                step_name,
                trial,
                score,
                reasons_json,
                raw_output
            )
            VALUES (
                'job-1',
                'case-1:baseline:0',
                'case-1',
                'baseline',
                0,
                0,
                '[]',
                'not-json'
            )
            """
        )

    ensure_database_schema(engine)

    with session_factory() as session:
        row = session.get(EvidenceRow, ("job-1", "case-1:baseline:0"))
        assert row is not None
        assert row.response_parse_error == ""


def test_database_schema_adds_missing_evidence_model_call_error_columns() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE evidence (
                job_id VARCHAR(80) NOT NULL,
                evidence_id VARCHAR(200) NOT NULL,
                case_id VARCHAR(120) NOT NULL,
                step_name VARCHAR(120) NOT NULL,
                trial INTEGER NOT NULL,
                model_name VARCHAR(120) NOT NULL DEFAULT '',
                model_provider VARCHAR(80) NOT NULL DEFAULT '',
                model_id VARCHAR(160) NOT NULL DEFAULT '',
                request_summary_json TEXT NOT NULL DEFAULT '{}',
                latency_ms INTEGER NOT NULL DEFAULT 0,
                response_parse_error TEXT NOT NULL DEFAULT '',
                score INTEGER NOT NULL,
                reasons_json TEXT NOT NULL,
                raw_output TEXT NOT NULL,
                PRIMARY KEY (job_id, evidence_id)
            )
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO evidence (
                job_id,
                evidence_id,
                case_id,
                step_name,
                trial,
                score,
                reasons_json,
                raw_output
            )
            VALUES (
                'job-1',
                'case-1:baseline:0',
                'case-1',
                'baseline',
                0,
                0,
                '[]',
                ''
            )
            """
        )

    ensure_database_schema(engine)

    with session_factory() as session:
        row = session.get(EvidenceRow, ("job-1", "case-1:baseline:0"))
        assert row is not None
        assert row.model_call_error_type == ""
        assert row.model_call_error_message == ""
