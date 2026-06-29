from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import unquote, urlparse

import pytest
from PIL import Image

from debug_agent.cases.fixtures import load_fixture_case
from debug_agent.cases.models import DebugCase
from debug_agent.jobs import service as service_module
from debug_agent.jobs.service import DebugJobService, classify_failure, classify_failure_stage
from debug_agent.models.config import AgentModelConfig
from debug_agent.models.adapters import ModelResponse
from debug_agent.models.fake import FakeModelAdapter
from debug_agent.reports.job_report import build_report_for_job
from debug_agent.storage.database import create_sqlite_memory_session_factory
from debug_agent.storage.models import Base
from debug_agent.storage.repository import DebugJobRepository


@pytest.mark.asyncio
async def test_job_service_submits_pending_job_and_runs_next_to_completion() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    service = DebugJobService(
        repository,
        model_provider=_fake_case_model_provider,
        enable_fixture_fallback=True,
    )

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
    service = DebugJobService(
        repository,
        model_provider=_fake_case_model_provider,
        enable_fixture_fallback=True,
    )

    submitted = service.submit_case_debug("handwrite233", baseline_trials=5)

    await service.run_next_job()

    job = repository.get_job(submitted.job_id)
    assert job is not None
    assert job.baseline_trials == 5
    evidence_ids = repository.list_evidence_ids(submitted.job_id)
    assert (
        len([evidence_id for evidence_id in evidence_ids if ":baseline_replay:" in evidence_id])
        == 5
    )
    assert len(evidence_ids) == 10


@pytest.mark.asyncio
async def test_job_service_writes_artifacts_under_group_and_job_directory() -> None:
    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        artifact_root = Path(temp_dir) / "artifacts"
        session_factory, engine = create_sqlite_memory_session_factory()
        Base.metadata.create_all(engine)
        repository = DebugJobRepository(session_factory)
        service = DebugJobService(
            repository,
            model_provider=_fake_case_model_provider,
            image_artifact_dir=artifact_root,
            enable_fixture_fallback=True,
        )

        submitted = service.submit_case_debug("handwrite233", artifact_group_id="batch-jszn")
        await service.run_job(submitted.job_id)

        job_dir = artifact_root / "runs" / "batch-jszn" / submitted.job_id
        assert (job_dir / "model_outputs").is_dir()
        assert any((job_dir / "model_outputs").glob("*_structured-output.txt"))
        job = repository.get_job(submitted.job_id)
        assert job is not None
        assert job.artifact_group_id == "batch-jszn"


@pytest.mark.asyncio
async def test_job_service_does_not_run_already_running_job() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    service = DebugJobService(
        repository,
        model_provider=_fake_case_model_provider,
        enable_fixture_fallback=True,
    )
    repository.create_job(job_id="job-1", case_id="handwrite233")
    repository.mark_running("job-1")

    result = await service.run_next_job()

    assert result is None
    assert repository.list_evidence_ids("job-1") == []


@pytest.mark.asyncio
async def test_job_service_run_job_is_idempotent_for_completed_job() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    service = DebugJobService(
        repository,
        model_provider=_fake_case_model_provider,
        enable_fixture_fallback=True,
    )
    submitted = service.submit_case_debug("handwrite233")
    await service.run_job(submitted.job_id)
    completed = repository.get_job(submitted.job_id)
    assert completed is not None
    evidence_ids = repository.list_evidence_ids(submitted.job_id)

    second_result = await service.run_job(submitted.job_id)

    after_second_run = repository.get_job(submitted.job_id)
    assert after_second_run is not None
    assert second_result.status == "completed"
    assert after_second_run.attempt_count == completed.attempt_count
    assert repository.list_evidence_ids(submitted.job_id) == evidence_ids


@pytest.mark.asyncio
async def test_job_service_run_job_is_idempotent_for_running_job() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    service = DebugJobService(repository, enable_fixture_fallback=True)
    repository.create_job(job_id="job-running", case_id="handwrite233")
    repository.mark_running("job-running")
    running = repository.get_job("job-running")
    assert running is not None

    result = await service.run_job("job-running")

    after_run = repository.get_job("job-running")
    assert after_run is not None
    assert result.status == "running"
    assert after_run.status == "running"
    assert after_run.attempt_count == running.attempt_count
    assert repository.list_evidence_ids("job-running") == []


@pytest.mark.asyncio
async def test_job_service_does_not_complete_job_cancelled_during_model_run() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    submitted_job_id = ""

    class CancellingModelAdapter:
        async def generate(self, prompt: str, image_uri: str) -> ModelResponse:
            del prompt, image_uri
            repository.update_job_status(
                submitted_job_id,
                "cancelled",
                error_message="Cancelled by XiaoD while model_runner was active.",
            )
            return ModelResponse(model_name="canceller", trial=0, raw_output='{"answer":"8"}')

    service = DebugJobService(
        repository,
        model_provider=lambda case: CancellingModelAdapter(),
        enable_fixture_fallback=True,
    )
    submitted = service.submit_case_debug("handwrite233")
    submitted_job_id = submitted.job_id

    result = await service.run_next_job()

    job = repository.get_job(submitted.job_id)
    assert result is not None
    assert result.status == "cancelled"
    assert job is not None
    assert job.status == "cancelled"
    assert "Cancelled by XiaoD" in job.error_message
    assert repository.list_evidence_ids(submitted.job_id) == []
    attempts = repository.list_job_attempts(submitted.job_id)
    assert attempts[0].status == "cancelled"
    assert attempts[0].retry_decision == "cancelled_by_user"


@pytest.mark.asyncio
async def test_job_service_stops_model_runner_trials_after_cancellation() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    submitted_job_id = ""
    generate_count = 0

    class CancellingModelAdapter:
        async def generate(self, prompt: str, image_uri: str) -> ModelResponse:
            nonlocal generate_count
            del prompt, image_uri
            generate_count += 1
            repository.update_job_status(
                submitted_job_id,
                "cancelled",
                error_message="Cancelled after first model_runner trial.",
            )
            return ModelResponse(model_name="canceller", trial=0, raw_output='{"answer":"8"}')

    service = DebugJobService(
        repository,
        model_provider=lambda case: CancellingModelAdapter(),
        enable_fixture_fallback=True,
    )
    submitted = service.submit_case_debug("handwrite233", baseline_trials=5)
    submitted_job_id = submitted.job_id

    result = await service.run_next_job()

    assert result is not None
    assert result.status == "cancelled"
    assert generate_count == 1


@pytest.mark.asyncio
async def test_job_service_stops_invalid_input_without_retry() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    service = DebugJobService(repository, max_attempts=2)
    repository.create_job(job_id="job-1", case_id="missing-case")

    with pytest.raises(FileNotFoundError):
        await service.run_next_job()

    job = repository.get_job("job-1")
    assert job is not None
    assert job.status == "failed"
    assert job.attempt_count == 1
    assert job.error_message is not None
    assert "missing-case" in job.error_message
    attempts = repository.list_job_attempts("job-1")
    assert attempts[0].failure_type == "invalid_input"
    assert attempts[0].retry_decision == "retry_stopped"


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


def test_job_service_rejects_fixture_fallback_by_default() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    service = DebugJobService(repository)

    with pytest.raises(FileNotFoundError):
        service.submit_case_debug("handwrite233")


def test_failure_classification_keeps_timeouts_and_lark_stage_actionable() -> None:
    assert classify_failure(TimeoutError("model request timed out")) == "model_timeout"
    assert (
        classify_failure(RuntimeError("lark-cli read timed out after 60 seconds"))
        == "model_timeout"
    )
    assert classify_failure_stage(RuntimeError("lark-cli spreadsheet write failed")) == "writeback"
    assert (
        classify_failure_stage(RuntimeError("lark-cli read timed out after 60 seconds"))
        == "writeback"
    )


@pytest.mark.asyncio
async def test_job_service_uses_injected_model_provider() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    selected_case_ids: list[str] = []

    def model_provider(case: DebugCase) -> FakeModelAdapter:
        selected_case_ids.append(case.case_id)
        return FakeModelAdapter(outputs=[case.predictions[0].raw_output], model_name="injected")

    service = DebugJobService(
        repository, model_provider=model_provider, enable_fixture_fallback=True
    )
    submitted = service.submit_case_debug("handwrite233")

    await service.run_next_job()

    assert selected_case_ids == ["handwrite233"]
    evidence_ids = repository.list_evidence_ids(submitted.job_id)
    assert len(evidence_ids) == 6


@pytest.mark.asyncio
async def test_job_service_runs_meta_agents_from_batch_model_config(monkeypatch) -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    case = DebugCase.model_validate(
        {
            "case_id": "meta-agent-case",
            "task_type": "classification",
            "image_uri": "",
            "prompt": "Classify.",
            "golden_answer": {"answers": [{"box_id": 1, "student_answer": "ok"}]},
            "expected_output": {"label": "ok"},
            "scoring_standard": "label must match.",
            "predictions": [
                {
                    "trial": 0,
                    "raw_output": (
                        '{"root_cause_summary":"LLM confirms schema drift.",'
                        '"recommended_actions":[{"summary":"Update schema guard."}],'
                        '"confidence_reasons":[{"source":"llm","summary":"Evidence is consistent."}],'
                        '"judge_comparison_notes":[{"evidence_id":"meta-agent-case:baseline_replay:0",'
                        '"target_id":"label","deterministic_reason":"label_mismatch",'
                        '"llm_note":"Label mismatch is consistent with schema drift.","risk":"medium"}],'
                        '"strategy_updates":[{"stage":"llm_probe","objective":"Probe schema drift",'
                        '"planned_probe":"schema_probe","stop_condition":"probe passes",'
                        '"escalation":"human review"}]}'
                    ),
                    "score": 0,
                }
            ],
            "avg_score": 0,
        }
    )
    repository.save_case(case)
    repository.create_batch(
        batch_id="batch-meta",
        total_jobs=1,
        retry_policy={
            "agent_model_config": {
                "roles": {
                    "model_runner": {
                        "provider": "fake",
                        "model_id": "fake",
                        "thinking": "disabled",
                        "locked": True,
                    },
                    "report_root_cause": {
                        "provider": "fake",
                        "model_id": "fake",
                        "thinking": "enabled",
                    },
                    "experiment_planner": {
                        "provider": "fake",
                        "model_id": "fake",
                        "thinking": "enabled",
                    },
                    "judge_comparator": {
                        "provider": "fake",
                        "model_id": "fake",
                        "thinking": "enabled",
                    },
                }
            }
        },
    )
    monkeypatch.setattr(service_module, "build_model_adapter", _fake_case_model_provider)
    service = DebugJobService(repository)
    submitted = service.submit_case_debug(
        case.case_id, baseline_trials=1, artifact_group_id="batch-meta"
    )

    await service.run_next_job()

    stages = repository.list_debug_run_stages(submitted.job_id)
    attribution_stage = next(stage for stage in stages if stage.stage == "attribution")
    enrichment = attribution_stage.output["meta_agent_enrichment"]
    assert enrichment["status"] == "completed"
    assert enrichment["root_cause_summary"] == "LLM confirms schema drift."
    assert enrichment["telemetry"][0]["agent_role"] == "report_root_cause"
    assert enrichment["telemetry"][0]["model_id"] == "fake"
    assert enrichment["telemetry"][0]["thinking"] == "enabled"
    assert enrichment["telemetry"][2]["agent_role"] == "judge_comparator"
    assert enrichment["telemetry"][2]["model_id"] == "fake"
    assert enrichment["telemetry"][2]["thinking"] == "enabled"
    assert (
        enrichment["judge_comparison_notes"][0]["llm_note"]
        == "Label mismatch is consistent with schema drift."
    )
    traces = enrichment["agent_traces"]
    trace_roles = {trace["agent_role"] for trace in traces}
    assert {"report_root_cause", "experiment_planner", "judge_comparator"} <= trace_roles
    root_trace = next(trace for trace in traces if trace["agent_role"] == "report_root_cause")
    assert "Report Root Cause Agent" in root_trace["input_excerpt"]
    assert root_trace["input_summary"]["case_id"] == "meta-agent-case"
    assert root_trace["reasoning_summary"] == "LLM confirms schema drift."
    assert root_trace["raw_cot_policy"] == "visible_output_summary_only"

    report = build_report_for_job(repository, submitted.job_id)
    assert report is not None
    assert report.meta_agent_enrichment["status"] == "completed"
    assert any(action["summary"] == "Update schema guard." for action in report.recommended_actions)
    assert any(strategy["stage"] == "llm_probe" for strategy in report.debug_strategy)
    assert report.judge_comparison_notes[0]["risk"] == "medium"
    report_trace_roles = {trace.agent_role for trace in report.agent_traces}
    assert {
        "model_runner",
        "report_root_cause",
        "experiment_planner",
        "judge_comparator",
    } <= report_trace_roles
    model_runner_trace = next(
        trace for trace in report.agent_traces if trace.agent_role == "model_runner"
    )
    assert model_runner_trace.input_summary["case_id"] == "meta-agent-case"
    assert "Classify." in model_runner_trace.input_excerpt
    assert model_runner_trace.output_excerpt


def test_job_service_uses_default_agent_model_config_for_single_live_jobs(monkeypatch) -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    default_config = AgentModelConfig(
        roles={"model_runner": {"provider": "fake", "model_id": "fake", "thinking": "disabled"}}
    )
    monkeypatch.setattr(service_module, "default_agent_model_config", lambda: default_config)
    service = DebugJobService(repository)

    assert service._agent_model_config_for_job("single").model_dump() == default_config.model_dump()


@pytest.mark.asyncio
async def test_job_service_downgrades_meta_agents_when_budget_is_exceeded(monkeypatch) -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    case = load_fixture_case("handwrite233").model_copy(update={"case_id": "budget-downgrade-case"})
    repository.save_case(case)
    repository.create_batch(
        batch_id="batch-budget",
        total_jobs=2,
        retry_policy={
            "agent_model_config": {
                "roles": {
                    "model_runner": {
                        "provider": "fake",
                        "model_id": "source",
                        "thinking": "disabled",
                        "locked": True,
                    },
                    "report_root_cause": {
                        "provider": "fake",
                        "model_id": "strong",
                        "thinking": "enabled",
                    },
                    "experiment_planner": {
                        "provider": "fake",
                        "model_id": "strong",
                        "thinking": "enabled",
                    },
                    "judge_comparator": {
                        "provider": "fake",
                        "model_id": "strong",
                        "thinking": "enabled",
                    },
                    "writeback_operator": {
                        "provider": "fake",
                        "model_id": "lite",
                        "thinking": "disabled",
                    },
                }
            }
        },
    )
    repository.create_job(
        job_id="previous-job", case_id=case.case_id, artifact_group_id="batch-budget"
    )
    repository.save_debug_run_stage(
        job_id="previous-job",
        stage="baseline",
        status="completed",
        input={},
        output={"usage": {"estimated_cost_units": 2.0}},
        failure_reason="",
        retryable=False,
    )
    monkeypatch.setattr(service_module, "build_model_adapter", _fake_case_model_provider)
    service = DebugJobService(
        repository,
        meta_agent_budget_units=1.0,
        auto_downgrade_meta_agents=True,
    )
    submitted = service.submit_case_debug(
        case.case_id, baseline_trials=1, artifact_group_id="batch-budget"
    )

    await service.run_job(submitted.job_id)

    attribution_stage = next(
        stage
        for stage in repository.list_debug_run_stages(submitted.job_id)
        if stage.stage == "attribution"
    )
    assert "meta agent budget exceeded" in attribution_stage.input["downgrade_reason"]
    assert "meta agent budget exceeded" in attribution_stage.output["downgrade_reason"]


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
            model_provider=lambda debug_case: FakeModelAdapter(
                outputs=[debug_case.predictions[0].raw_output]
            ),
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


def _fake_case_model_provider(case: DebugCase) -> FakeModelAdapter:
    return FakeModelAdapter(outputs=[case.predictions[0].raw_output], model_name="fake-service")
