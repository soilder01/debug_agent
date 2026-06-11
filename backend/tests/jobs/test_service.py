from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import unquote, urlparse

import pytest
from PIL import Image

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
async def test_job_service_uses_submitted_baseline_trials_when_running_job() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    service = DebugJobService(repository)

    submitted = service.submit_case_debug("handwrite233", baseline_trials=5)

    await service.run_next_job()

    job = repository.get_job(submitted.job_id)
    assert job is not None
    assert job.baseline_trials == 5
    evidence_ids = repository.list_evidence_ids(submitted.job_id)
    assert len([evidence_id for evidence_id in evidence_ids if ":baseline_replay:" in evidence_id]) == 5
    assert len(evidence_ids) == 10


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


@pytest.mark.asyncio
async def test_job_service_writes_localized_crop_artifacts_when_configured() -> None:
    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        temp_path = Path(temp_dir)
        source_image_path = temp_path / "case-service-crop.png"
        Image.new("RGB", (100, 100), color="white").save(source_image_path)
        session_factory, engine = create_sqlite_memory_session_factory()
        Base.metadata.create_all(engine)
        repository = DebugJobRepository(session_factory)
        case_data = load_fixture_case("handwrite233").model_dump()
        case_data["case_id"] = "service-crop-case"
        case_data["image_uri"] = source_image_path.as_uri()
        case_data["box_regions"] = [
            {
                "box_id": 1,
                "x": 10,
                "y": 12,
                "width": 24,
                "height": 16,
                "unit": "pixel",
                "label": "box-1",
            }
        ]
        case = DebugCase.model_validate(case_data)
        repository.save_case(case)
        service = DebugJobService(
            repository,
            model_provider=lambda debug_case: FakeModelAdapter(outputs=[debug_case.predictions[0].raw_output]),
            image_artifact_dir=temp_path / "artifacts",
        )
        submitted = service.submit_case_debug(case.case_id)

        await service.run_next_job()

        evidence_ids = repository.list_evidence_ids(submitted.job_id)
        localized_evidence = [
            repository.get_evidence(submitted.job_id, evidence_id)
            for evidence_id in evidence_ids
            if ":localized_observation_request:" in evidence_id
        ]
        crop_uris = [
            artifact.derived_image_uri
            for evidence in localized_evidence
            if evidence is not None
            for artifact in evidence.image_artifacts
            if artifact.derived_image_uri
        ]
        assert crop_uris
        crop_path = _path_from_file_uri(crop_uris[0])
        assert crop_path.exists()
        with Image.open(crop_path) as crop:
            assert crop.size == (24, 16)


def _path_from_file_uri(uri: str) -> Path:
    parsed = urlparse(uri)
    path_text = unquote(parsed.path)
    if len(path_text) >= 3 and path_text[0] == "/" and path_text[2] == ":":
        path_text = path_text[1:]
    return Path(path_text)
