import asyncio
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest

from debug_agent.jobs.service import DebugJobService
from debug_agent.jobs.worker import AsyncJobWorker
from debug_agent.models.fake import FakeModelAdapter
from debug_agent.storage.database import create_sqlite_memory_session_factory
from debug_agent.storage.models import Base, DebugJobRow
from debug_agent.storage.repository import DebugJobRepository


async def wait_until(predicate: Callable[[], bool], timeout_seconds: float = 5.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while asyncio.get_running_loop().time() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("condition was not met before timeout")


def create_service(max_attempts: int = 2) -> tuple[DebugJobRepository, DebugJobService]:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    return repository, DebugJobService(
        repository,
        max_attempts=max_attempts,
        model_provider=lambda case: FakeModelAdapter([prediction.raw_output for prediction in case.predictions]),
        enable_fixture_fallback=True,
    )


@pytest.mark.asyncio
async def test_async_worker_processes_created_job_until_completion() -> None:
    repository, service = create_service()
    submitted = service.submit_case_debug("handwrite233")
    worker = AsyncJobWorker(service, idle_sleep_seconds=0.01)

    started = worker.start()
    try:
        await wait_until(lambda: repository.get_job(submitted.job_id).status == "completed")
    finally:
        await worker.stop()

    job = repository.get_job(submitted.job_id)
    assert started is True
    assert job is not None
    assert job.status == "completed"
    assert job.attempt_count == 1
    assert len(repository.list_evidence_ids(submitted.job_id)) == 6
    assert worker.status().running is False
    assert worker.status().processed_count == 1


@pytest.mark.asyncio
async def test_async_worker_start_is_idempotent_while_running() -> None:
    _, service = create_service()
    worker = AsyncJobWorker(service, idle_sleep_seconds=0.01)

    first_start = worker.start()
    second_start = worker.start()
    await worker.stop()

    assert first_start is True
    assert second_start is False
    assert worker.status().running is False


@pytest.mark.asyncio
async def test_async_worker_survives_failed_job_attempt_and_keeps_polling() -> None:
    repository, service = create_service(max_attempts=1)
    repository.create_job(job_id="000-missing", case_id="missing-case")
    submitted = service.submit_case_debug("handwrite233")
    worker = AsyncJobWorker(service, idle_sleep_seconds=0.01)

    worker.start()
    try:
        await wait_until(lambda: repository.get_job(submitted.job_id).status == "completed")
    finally:
        await worker.stop()

    failed_attempt = repository.get_job("000-missing")
    completed_job = repository.get_job(submitted.job_id)
    assert failed_attempt is not None
    assert failed_attempt.status == "failed"
    assert failed_attempt.attempt_count == 1
    assert completed_job is not None
    assert completed_job.status == "completed"
    assert worker.status().error_count == 1
    assert worker.status().last_error is not None
    assert "missing-case" in worker.status().last_error


@pytest.mark.asyncio
async def test_async_worker_invokes_completion_hook_after_completed_job() -> None:
    repository, service = create_service()
    submitted = service.submit_case_debug("handwrite233")
    completed_job_ids: list[str] = []
    worker = AsyncJobWorker(
        service,
        idle_sleep_seconds=0.01,
        on_job_completed=lambda job: completed_job_ids.append(job.job_id),
    )

    await worker.tick()

    job = repository.get_job(submitted.job_id)
    assert job is not None
    assert job.status == "completed"
    assert completed_job_ids == [submitted.job_id]
    assert worker.status().processed_count == 1
    assert worker.status().error_count == 0


@pytest.mark.asyncio
async def test_async_worker_recovers_stale_running_job_before_tick() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    service = DebugJobService(
        repository,
        model_provider=lambda case: FakeModelAdapter([prediction.raw_output for prediction in case.predictions]),
        enable_fixture_fallback=True,
    )
    submitted = service.submit_case_debug("handwrite233")
    repository.mark_running(submitted.job_id)
    stale_updated_at = (datetime.now(UTC) - timedelta(minutes=30)).isoformat()
    with session_factory() as session:
        row = session.get(DebugJobRow, submitted.job_id)
        assert row is not None
        row.updated_at = stale_updated_at
        session.commit()
    worker = AsyncJobWorker(service, idle_sleep_seconds=0.01, stale_running_job_seconds=60)

    await worker.tick()

    job = repository.get_job(submitted.job_id)
    assert job is not None
    assert job.status == "completed"
    assert job.attempt_count == 2
    assert worker.status().recovered_stale_job_count == 1
    stages = repository.list_debug_run_stages(submitted.job_id)
    assert any(stage.stage == "queue_runtime" and stage.status == "recovered" for stage in stages)
