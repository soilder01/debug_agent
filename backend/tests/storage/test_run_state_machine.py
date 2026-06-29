from debug_agent.storage.database import create_sqlite_memory_session_factory, ensure_database_schema
from debug_agent.storage.repository import DebugJobRepository


def test_repository_records_baseline_stage_transitions() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    ensure_database_schema(engine)
    repository = DebugJobRepository(session_factory)

    repository.create_job(job_id="job-1", case_id="case-1", baseline_trials=3)
    assert repository.list_debug_run_stages("job-1")[0].model_dump(include={"stage", "status", "retryable"}) == {
        "stage": "baseline",
        "status": "pending",
        "retryable": True,
    }

    repository.mark_running("job-1")
    running_stage = repository.list_debug_run_stages("job-1")[0]
    assert running_stage.status == "running"
    assert running_stage.input["baseline_trials"] == 3

    repository.release_for_retry("job-1", "transient model timeout")
    retry_stage = repository.list_debug_run_stages("job-1")[0]
    assert retry_stage.status == "failed"
    assert retry_stage.failure_reason == "transient model timeout"
    assert retry_stage.retryable is True

    repository.mark_failed("job-1", "retry budget exhausted")
    failed_stage = repository.list_debug_run_stages("job-1")[0]
    assert failed_stage.status == "failed"
    assert failed_stage.failure_reason == "retry budget exhausted"
    assert failed_stage.retryable is False


def test_repository_records_ordered_debug_run_stages() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    ensure_database_schema(engine)
    repository = DebugJobRepository(session_factory)
    repository.create_job(job_id="job-1", case_id="case-1", baseline_trials=1)

    repository.save_debug_run_stage(
        job_id="job-1",
        stage="targeted",
        status="completed",
        input={"targets": ["video:segment:1"]},
        output={"created_jobs": ["job-probe-1"]},
        failure_reason="",
        retryable=True,
    )
    repository.save_debug_run_stage(
        job_id="job-1",
        stage="writeback",
        status="completed",
        input={"report_url": "/api/artifacts/files/report.md"},
        output={"writeback_status": "succeeded"},
        failure_reason="",
        retryable=True,
    )

    assert [stage.stage for stage in repository.list_debug_run_stages("job-1")] == [
        "baseline",
        "targeted",
        "writeback",
    ]
    writeback_stage = repository.list_debug_run_stages("job-1")[-1]
    assert writeback_stage.output["writeback_status"] == "succeeded"
