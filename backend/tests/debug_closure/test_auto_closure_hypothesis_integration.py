import pytest

from debug_agent.cases.models import DebugCase
from debug_agent.experiments.runner import ExperimentEvidence
from debug_agent.jobs import auto_closure
from debug_agent.jobs.auto_closure import run_auto_debug_closure
from debug_agent.jobs.service import DebugJobService
from debug_agent.judging.runner import JudgeResult
from debug_agent.models.fake import FakeModelAdapter
from debug_agent.storage.database import (
    create_sqlite_memory_session_factory,
    ensure_database_schema,
)
from debug_agent.storage.repository import DebugJobRepository


@pytest.mark.asyncio
async def test_auto_closure_writes_hypothesis_closure_stage_without_promoting_candidates() -> None:
    repository, service, source_job_id = _repository_service_and_job()

    result = await run_auto_debug_closure(
        repository=repository,
        job_service=service,
        job_id=source_job_id,
        actor="auto-debug-agent",
    )

    hypothesis_stage = next(
        stage
        for stage in repository.list_debug_run_stages(source_job_id)
        if stage.stage == "hypothesis"
    )
    closure = hypothesis_stage.output["hypothesis_closure"]
    assert hypothesis_stage.status == "completed"
    assert closure["fairness_lock"]["model_runner_config_ref"] == "locked_source"
    assert closure["hypotheses"]
    assert closure["probe_plans"]
    assert all(item["status"] == "candidate" for item in closure["hypotheses"])
    assert all(
        item["model_runner_config_ref"] == "locked_source" for item in closure["probe_plans"]
    )
    assert all(not item["probe_job_id"] for item in closure["probe_results"])
    assert all(item["verdict"] != "supported" for item in closure["causal_comparisons"])
    assert result.verified_root_causes == []
    assert result.unverified_hypotheses


@pytest.mark.asyncio
async def test_auto_closure_keeps_running_when_hypothesis_stage_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, service, source_job_id = _repository_service_and_job()

    def fail_synthesis(*args: object, **kwargs: object) -> object:
        raise RuntimeError("synthetic hypothesis failure")

    monkeypatch.setattr(auto_closure, "synthesize_probe_plans", fail_synthesis)

    result = await run_auto_debug_closure(
        repository=repository,
        job_service=service,
        job_id=source_job_id,
        actor="auto-debug-agent",
    )

    hypothesis_stage = next(
        stage
        for stage in repository.list_debug_run_stages(source_job_id)
        if stage.stage == "hypothesis"
    )
    assert hypothesis_stage.status == "failed"
    assert "synthetic hypothesis failure" in hypothesis_stage.failure_reason
    assert result.source_job_id == source_job_id
    assert result.unverified_hypotheses == [
        {
            "hypothesis_id": "hypothesis_closure_failed",
            "status": "inconclusive",
            "summary": "synthetic hypothesis failure",
        }
    ]


@pytest.mark.asyncio
async def test_auto_closure_uses_configured_hypothesis_strategy_agent() -> None:
    repository, service, source_job_id = _repository_service_and_job(
        strategy_agent_output="""
        {
          "hypotheses": [
            {
              "hypothesis_id": "h-agent-prompt",
              "category": "prompt_constraint",
              "claim": "Agent thinks prompt omitted right-arm detail.",
              "supporting_evidence_ids": [],
              "confidence_before_probe": "high",
              "status": "supported"
            }
          ]
        }
        """
    )

    result = await run_auto_debug_closure(
        repository=repository,
        job_service=service,
        job_id=source_job_id,
        actor="auto-debug-agent",
    )

    hypothesis_stage = next(
        stage
        for stage in repository.list_debug_run_stages(source_job_id)
        if stage.stage == "hypothesis"
    )
    closure = hypothesis_stage.output["hypothesis_closure"]
    agent_hypothesis = next(
        item for item in closure["hypotheses"] if item["hypothesis_id"] == "h-agent-prompt"
    )
    assert agent_hypothesis["status"] == "candidate"
    assert agent_hypothesis["confidence_before_probe"] == "low"
    assert hypothesis_stage.output["strategy_agent_trace"]["agent_role"] == "hypothesis_strategist"
    assert (
        hypothesis_stage.output["strategy_agent_trace"]["raw_cot_policy"]
        == "visible_output_summary_only"
    )
    assert any(item["hypothesis_id"] == "h-agent-prompt" for item in result.hypotheses)


@pytest.mark.asyncio
async def test_auto_closure_reuses_previous_strategy_hypotheses_on_probe_rerun(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, service, source_job_id = _repository_service_and_job(
        strategy_agent_output="""
        {
          "hypotheses": [
            {
              "hypothesis_id": "h-agent-prompt",
              "category": "prompt_constraint",
              "claim": "Agent thinks prompt omitted right-arm detail.",
              "supporting_evidence_ids": [],
              "confidence_before_probe": "high",
              "status": "candidate"
            }
          ]
        }
        """
    )

    first = await run_auto_debug_closure(
        repository=repository,
        job_service=service,
        job_id=source_job_id,
        actor="auto-debug-agent",
        submit_controlled_probes=True,
    )

    async def fail_strategy(*args: object, **kwargs: object) -> object:
        raise AssertionError("strategy agent should not rerun after hypothesis payload exists")

    monkeypatch.setattr(auto_closure, "_strategy_agent_hypotheses", fail_strategy)
    second = await run_auto_debug_closure(
        repository=repository,
        job_service=service,
        job_id=source_job_id,
        actor="auto-debug-agent",
        submit_controlled_probes=True,
    )

    assert [item["hypothesis_id"] for item in second.hypotheses] == [
        item["hypothesis_id"] for item in first.hypotheses
    ]


@pytest.mark.asyncio
async def test_auto_closure_can_submit_controlled_probe_jobs_when_explicitly_enabled() -> None:
    repository, service, source_job_id = _repository_service_and_job()

    result = await run_auto_debug_closure(
        repository=repository,
        job_service=service,
        job_id=source_job_id,
        actor="auto-debug-agent",
        submit_controlled_probes=True,
    )

    submitted_probe_results = [
        item for item in result.probe_results if str(item.get("probe_job_id", "")).strip()
    ]
    assert submitted_probe_results
    assert any(
        item["status"] == "not_run"
        and item["model_runner_config_snapshot"]["locked"] is True
        and item["model_runner_config_snapshot"]["mode"] == "high"
        and item["model_runner_config_snapshot"]["thinking"] == "disabled"
        for item in submitted_probe_results
    )
    for item in submitted_probe_results:
        probe_job = repository.get_job(str(item["probe_job_id"]))
        assert probe_job is not None
        assert probe_job.status == "created"
        assert repository.list_evidence(probe_job.job_id) == []

    non_runner_results = [
        item for item in result.probe_results if item["probe_id"] == "probe-h-scoring-strictness"
    ]
    assert non_runner_results
    assert non_runner_results[0]["probe_job_id"] == ""
    assert non_runner_results[0]["status"] == "completed"
    assert non_runner_results[0]["observed_success_rate"] == 0
    assert "scoring_variant" in non_runner_results[0]["diagnostic_summary"]
    assert result.verified_root_causes == []


@pytest.mark.asyncio
async def test_auto_closure_writes_debug_loop_iteration_waiting_for_probe_completion() -> None:
    repository, service, source_job_id = _repository_service_and_job()

    result = await run_auto_debug_closure(
        repository=repository,
        job_service=service,
        job_id=source_job_id,
        actor="auto-debug-agent",
        submit_controlled_probes=True,
    )

    loop_stage = next(
        stage
        for stage in repository.list_debug_run_stages(source_job_id)
        if stage.stage == "debug_loop"
    )
    loop = loop_stage.output["debug_loop"]
    assert loop_stage.status == "waiting"
    assert loop["current_iteration"] == 1
    assert loop["decision"] == "waiting_for_probe_completion"
    assert loop["next_action"] == "等待 queued probe job 完成后回流证据并重新进行因果比较。"
    assert loop["stop_reason"] == ""
    assert loop["iterations"][0]["iteration"] == 1
    assert loop["iterations"][0]["hypothesis_count"] == len(result.hypotheses)
    assert loop["iterations"][0]["probe_plan_count"] == len(result.probe_plans)
    assert loop["iterations"][0]["completed_probe_count"] >= 1
    assert loop["iterations"][0]["pending_probe_count"] > 0
    assert any(item["probe_job_id"] for item in loop["iterations"][0]["probe_results"])


def test_debug_loop_waits_for_pending_runner_probe_even_when_non_runner_supported() -> None:
    decision, next_action, stop_reason = auto_closure._debug_loop_decision(
        hypothesis_count=3,
        probe_plan_count=3,
        pending_probe_count=1,
        completed_probe_count=2,
        causal_comparison_count=3,
        supported_count=1,
        verified_root_cause_count=1,
        iteration_value=1,
        max_loop_iterations=3,
    )

    assert decision == "waiting_for_probe_completion"
    assert "已有 supported comparison" in next_action
    assert stop_reason == "存在未完成的 controlled runner probe。"


@pytest.mark.asyncio
async def test_auto_closure_compares_completed_controlled_probe_evidence() -> None:
    repository, service, source_job_id = _repository_service_and_job()
    queued = await run_auto_debug_closure(
        repository=repository,
        job_service=service,
        job_id=source_job_id,
        actor="auto-debug-agent",
        submit_controlled_probes=True,
    )
    prompt_probe = next(
        item for item in queued.probe_results if item["probe_id"] == "probe-h-prompt-constraint"
    )
    probe_job_id = str(prompt_probe["probe_job_id"])
    assert probe_job_id
    probe_job = repository.get_job(probe_job_id)
    assert probe_job is not None
    repository.save_evidence(
        job_id=probe_job_id,
        case_id=probe_job.case_id,
        evidence=[_successful_probe_evidence(probe_job_id)],
    )
    repository.mark_completed(probe_job_id)

    compared = await run_auto_debug_closure(
        repository=repository,
        job_service=service,
        job_id=source_job_id,
        actor="auto-debug-agent",
        submit_controlled_probes=True,
    )

    completed_prompt_probe = next(
        item for item in compared.probe_results if item["probe_id"] == "probe-h-prompt-constraint"
    )
    assert completed_prompt_probe["probe_job_id"] == probe_job_id
    assert completed_prompt_probe["status"] == "completed"
    assert completed_prompt_probe["evidence_ids"] == [f"{probe_job_id}:success"]
    assert (
        len(
            [
                item
                for item in compared.probe_results
                if item["probe_id"] == "probe-h-prompt-constraint"
                and item.get("probe_job_id") == probe_job_id
            ]
        )
        == 1
    )
    prompt_comparison = next(
        item
        for item in compared.causal_comparisons
        if item["probe_id"] == "probe-h-prompt-constraint"
    )
    assert prompt_comparison["verdict"] == "supported"
    assert prompt_comparison["intervention_success_rate"] == 1
    assert compared.verified_root_causes == [
        {
            "hypothesis_id": "h-prompt-constraint",
            "probe_id": "probe-h-prompt-constraint",
            "summary": prompt_comparison["evidence_summary"],
        }
    ]


@pytest.mark.asyncio
async def test_auto_closure_escalates_to_second_iteration_when_first_round_has_no_support() -> None:
    repository, service, source_job_id = _repository_service_and_job()
    queued = await run_auto_debug_closure(
        repository=repository,
        job_service=service,
        job_id=source_job_id,
        actor="auto-debug-agent",
        submit_controlled_probes=True,
    )
    _complete_runner_probe_jobs_with_failed_evidence(repository=repository, probe_results=queued.probe_results)

    escalated = await run_auto_debug_closure(
        repository=repository,
        job_service=service,
        job_id=source_job_id,
        actor="auto-debug-agent",
        submit_controlled_probes=True,
    )

    loop_stage = next(
        stage
        for stage in repository.list_debug_run_stages(source_job_id)
        if stage.stage == "debug_loop"
    )
    loop = loop_stage.output["debug_loop"]
    assert loop_stage.status == "waiting"
    assert loop["current_iteration"] == 2
    assert loop["decision"] == "waiting_for_probe_completion"
    assert loop["iterations"][0]["decision"] == "escalated_to_next_iteration"
    assert loop["iterations"][0]["next_action"] == "已升级到第 2 轮补充证据。"
    assert loop["iterations"][1]["iteration"] == 2
    assert loop["iterations"][1]["pending_probe_count"] > 0
    assert any(item["iteration"] == 2 for item in escalated.hypotheses)
    assert any(item["iteration"] == 2 for item in escalated.probe_plans)
    assert any(
        item["iteration"] == 2 and str(item.get("probe_job_id", "")).strip()
        for item in escalated.probe_results
    )


@pytest.mark.asyncio
async def test_auto_closure_stops_after_loop_budget_without_supported_comparison() -> None:
    repository, service, source_job_id = _repository_service_and_job()
    queued = await run_auto_debug_closure(
        repository=repository,
        job_service=service,
        job_id=source_job_id,
        actor="auto-debug-agent",
        submit_controlled_probes=True,
        max_loop_iterations=1,
    )
    _complete_runner_probe_jobs_with_failed_evidence(repository=repository, probe_results=queued.probe_results)

    stopped = await run_auto_debug_closure(
        repository=repository,
        job_service=service,
        job_id=source_job_id,
        actor="auto-debug-agent",
        submit_controlled_probes=True,
        max_loop_iterations=1,
    )

    assert stopped.debug_loop["current_iteration"] == 1
    assert stopped.debug_loop["decision"] == "stopped_evidence_exhausted"
    assert stopped.debug_loop["stop_reason"] == "达到最大探索轮次后仍没有 supported causal comparison。"


def _complete_runner_probe_jobs_with_failed_evidence(
    *,
    repository: DebugJobRepository,
    probe_results: list[dict[str, object]],
) -> None:
    for result in probe_results:
        probe_job_id = str(result.get("probe_job_id", "")).strip()
        if not probe_job_id:
            continue
        probe_job = repository.get_job(probe_job_id)
        assert probe_job is not None
        repository.save_evidence(
            job_id=probe_job_id,
            case_id=probe_job.case_id,
            evidence=[_failed_video_json_evidence(probe_job_id)],
        )
        repository.mark_completed(probe_job_id)


def _repository_service_and_job(
    *,
    strategy_agent_output: str = "",
) -> tuple[DebugJobRepository, DebugJobService, str]:
    session_factory, engine = create_sqlite_memory_session_factory()
    ensure_database_schema(engine)
    repository = DebugJobRepository(session_factory)
    case = _video_case(strategy_agent_output=strategy_agent_output)
    source_job_id = "hypothesis-source-job"
    artifact_group_id = "single"
    service = DebugJobService(
        repository,
        model_provider=lambda _: FakeModelAdapter(outputs=['{"video_action_segments":[]}']),
    )
    if strategy_agent_output:
        artifact_group_id = "hypothesis-agent-batch"
        repository.create_batch(
            batch_id=artifact_group_id,
            total_jobs=1,
            retry_policy={
                "agent_model_config": {
                    "roles": {
                        "hypothesis_strategist": {
                            "provider": "fake",
                            "model_id": "seedpro",
                            "thinking": "enabled",
                        }
                    }
                }
            },
        )
        service = DebugJobService(repository)
    repository.save_case(case)
    repository.create_job(
        source_job_id,
        case.case_id,
        baseline_trials=1,
        artifact_group_id=artifact_group_id,
    )
    repository.save_evidence(
        job_id=source_job_id,
        case_id=case.case_id,
        evidence=[_failed_video_json_evidence(source_job_id)],
    )
    repository.mark_completed(source_job_id)
    return (repository, service, source_job_id)


def _video_case(*, strategy_agent_output: str = "") -> DebugCase:
    return DebugCase.model_validate(
        {
            "case_id": "JSZN-096-hypothesis",
            "task_type": "generic_video_json",
            "image_uri": "file:///tmp/jszn-096.mp4",
            "prompt": "Return video_action_segments JSON.",
            "golden_answer": {"answers": []},
            "expected_output": {
                "video_action_segments": [
                    {
                        "subtask_label": "pick bag",
                        "expected_detail": "右臂拿起，双臂配合套入",
                    }
                ]
            },
            "output_schema": {},
            "scoring_standard": "必须包含右臂拿起和双臂配合。",
            "predictions": [{"trial": 0, "raw_output": strategy_agent_output or "{}", "score": 0}],
            "avg_score": 0.0,
        }
    )


def _failed_video_json_evidence(job_id: str) -> ExperimentEvidence:
    return ExperimentEvidence(
        evidence_id=f"{job_id}:failed",
        step_name="baseline_replay",
        trial=0,
        raw_output='{"video_action_segments":[]}',
        judge=JudgeResult(
            score=0,
            reasons=["video:segment:1 missing_right_arm_detail"],
            deltas=[
                {
                    "target_id": "video:segment:1",
                    "expected": "右臂拿起，双臂配合套入",
                    "actual": "双臂整理",
                    "reason": "missing_right_arm_detail",
                }
            ],
        ),
    )


def _successful_probe_evidence(job_id: str) -> ExperimentEvidence:
    return ExperimentEvidence(
        evidence_id=f"{job_id}:success",
        step_name="prompt_patch_intervention_rerun",
        trial=0,
        raw_output='{"video_action_segments":[{"detail":"右臂拿起，双臂配合套入"}]}',
        judge=JudgeResult(score=1, reasons=[]),
    )
