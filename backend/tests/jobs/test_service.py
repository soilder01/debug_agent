import pytest

from debug_agent.cases.fixtures import load_fixture_case
from debug_agent.cases.models import DebugCase
from debug_agent.jobs.service import DebugJobService
from debug_agent.models.fake import FakeModelAdapter
from debug_agent.storage.database import create_sqlite_memory_session_factory
from debug_agent.storage.models import Base
from debug_agent.storage.repository import DebugJobRepository


@pytest.mark.asyncio
async def test_job_service_submits_pending_job_and_runs_next_to_completion() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    service = DebugJobService(repository)

    submitted = service.submit_case_debug("handwrite233")

    assert submitted.status == "created"

    result = await service.run_next_job()

    assert result is not None
    assert result.job_id == submitted.job_id
    job = repository.get_job(submitted.job_id)
    assert job is not None
    assert job.status == "completed"
    assert job.attempt_count == 1
    assert len(repository.list_evidence_ids(submitted.job_id)) == 6


@pytest.mark.asyncio
async def test_job_service_does_not_run_already_running_job() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    service = DebugJobService(repository)
    repository.create_job(job_id="job-1", case_id="handwrite233")
    repository.mark_running("job-1")

    result = await service.run_next_job()

    assert result is None
    assert repository.list_evidence_ids("job-1") == []


@pytest.mark.asyncio
async def test_job_service_requeues_failed_job_before_max_attempts() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    service = DebugJobService(repository, max_attempts=2)
    repository.create_job(job_id="job-1", case_id="missing-case")

    with pytest.raises(FileNotFoundError):
        await service.run_next_job()

    job = repository.get_job("job-1")
    assert job is not None
    assert job.status == "created"
    assert job.attempt_count == 1
    assert job.error_message is not None
    assert "missing-case" in job.error_message


@pytest.mark.asyncio
async def test_job_service_marks_job_failed_when_attempts_exhausted() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    service = DebugJobService(repository, max_attempts=1)
    repository.create_job(job_id="job-1", case_id="missing-case")

    with pytest.raises(FileNotFoundError):
        await service.run_next_job()

    job = repository.get_job("job-1")
    assert job is not None
    assert job.status == "failed"
    assert job.attempt_count == 1
    assert job.error_message is not None
    assert "missing-case" in job.error_message


def test_job_service_submits_imported_case_from_repository() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    service = DebugJobService(repository)
    case = load_fixture_case("handwrite233").model_copy(update={"case_id": "imported-1"})
    repository.save_case(case)

    submitted = service.submit_case_debug("imported-1")

    assert submitted.case_id == "imported-1"
    assert submitted.status == "created"


@pytest.mark.asyncio
async def test_job_service_uses_injected_model_provider() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    selected_case_ids: list[str] = []

    def model_provider(case: DebugCase) -> FakeModelAdapter:
        selected_case_ids.append(case.case_id)
        return FakeModelAdapter(outputs=[case.predictions[0].raw_output], model_name="injected")

    service = DebugJobService(repository, model_provider=model_provider)
    submitted = service.submit_case_debug("handwrite233")

    await service.run_next_job()

    assert selected_case_ids == ["handwrite233"]
    evidence_ids = repository.list_evidence_ids(submitted.job_id)
    assert len(evidence_ids) == 6
