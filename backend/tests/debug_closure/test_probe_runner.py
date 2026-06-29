from debug_agent.cases.models import DebugCase
from debug_agent.debug_closure.hypotheses import DebugProbePlan
from debug_agent.debug_closure.probe_runner import (
    build_controlled_probe_draft,
    submit_controlled_probe_job,
)
from debug_agent.jobs.service import DebugJobService
from debug_agent.models.config import AgentModelConfig, AgentModelSelection
from debug_agent.settings import ArkSettings
from debug_agent.storage.database import (
    create_sqlite_memory_session_factory,
    ensure_database_schema,
)
from debug_agent.storage.repository import DebugJobRepository


def test_controlled_probe_runner_derives_prompt_patch_case_without_changing_runner_inputs() -> None:
    source_case = _video_case()
    plan = DebugProbePlan(
        probe_id="probe-h-prompt",
        hypothesis_id="h-prompt",
        intervention_type="prompt_patch",
        intervention_payload={
            "claim": "Prompt misses right-arm and both-arm requirements.",
            "prompt_patch": "每个子任务必须明确首个拿起物品的手臂，并说明是否双臂配合。",
        },
        trials=5,
        success_criteria={"must_include": ["右臂", "双臂配合"]},
        stop_condition="stop after 5 locked-source trials",
    )

    draft = build_controlled_probe_draft(
        source_case=source_case,
        source_job_id="job-source",
        plan=plan,
        agent_model_config=AgentModelConfig(
            roles={
                "model_runner": AgentModelSelection(
                    provider="ark",
                    model_id="unsafe-user-model",
                    mode="lite",
                    thinking="enabled",
                    locked=False,
                )
            }
        ),
        ark_settings=ArkSettings(
            api_key="",
            video_model_id="locked-video",
            video_mode="high",
            video_disable_thinking=True,
            seed2_pro_model_id="seedpro",
            seed2_lite_model_id="lite",
        ),
    )

    assert draft.should_submit_debug_job is True
    assert draft.derived_case.case_id == "JSZN-096__hypothesis_probe__probe_h_prompt"
    assert draft.derived_case.image_uri == source_case.image_uri
    assert draft.derived_case.scoring_standard == source_case.scoring_standard
    assert "受控假设验证" in draft.derived_case.prompt
    assert "右臂" in draft.derived_case.prompt
    assert draft.probe_result.status == "not_run"
    assert draft.probe_result.source_job_id == "job-source"
    assert draft.probe_result.probe_job_id == ""
    assert draft.probe_result.model_runner_config_snapshot == {
        "provider": "ark",
        "model_id": "locked-video",
        "base_url": "",
        "credential_ref": "",
        "mode": "high",
        "thinking": "disabled",
        "temperature": None,
        "top_p": None,
        "max_tokens": None,
        "locked": True,
    }


def test_controlled_probe_runner_marks_scoring_variant_as_non_runner_probe() -> None:
    plan = DebugProbePlan(
        probe_id="probe-h-scoring",
        hypothesis_id="h-scoring",
        intervention_type="scoring_variant",
        intervention_payload={"variant": "lenient_semantic"},
        trials=1,
        success_criteria={"lenient_score_gt_strict_score": True},
        stop_condition="single deterministic rescore",
    )

    draft = build_controlled_probe_draft(
        source_case=_video_case(),
        source_job_id="job-source",
        plan=plan,
        ark_settings=ArkSettings(
            api_key="",
            video_model_id="locked-video",
            video_mode="high",
            video_disable_thinking=True,
            seed2_pro_model_id="seedpro",
            seed2_lite_model_id="lite",
        ),
    )

    assert draft.should_submit_debug_job is False
    assert draft.derived_case.case_id == "JSZN-096__hypothesis_probe__probe_h_scoring"
    assert draft.derived_case.prompt == _video_case().prompt
    assert draft.probe_result.model_runner_config_snapshot == {}


def test_submit_controlled_probe_job_creates_created_debug_job_without_running_model() -> None:
    repository, job_service = _repository_and_service()
    plan = DebugProbePlan(
        probe_id="probe-h-stability",
        hypothesis_id="h-stability",
        intervention_type="stability_rerun",
        intervention_payload={"claim": "same prompt may be unstable"},
        trials=5,
        success_criteria={"variance_detected_across_locked_trials": True},
        stop_condition="stop after 5 locked-source trials",
    )
    draft = build_controlled_probe_draft(
        source_case=_video_case(),
        source_job_id="job-source",
        plan=plan,
        ark_settings=ArkSettings(
            api_key="",
            video_model_id="locked-video",
            video_mode="high",
            video_disable_thinking=True,
            seed2_pro_model_id="seedpro",
            seed2_lite_model_id="lite",
        ),
    )

    submitted = submit_controlled_probe_job(
        repository=repository,
        job_service=job_service,
        draft=draft,
        artifact_group_id="debug-run-1",
    )

    assert submitted.probe_result.probe_job_id
    job = repository.get_job(submitted.probe_result.probe_job_id)
    assert job is not None
    assert job.status == "created"
    assert job.case_id == "JSZN-096__hypothesis_probe__probe_h_stability"
    assert job.baseline_trials == 5
    assert job.artifact_group_id == "debug-run-1"
    assert repository.get_case(job.case_id) == submitted.derived_case
    assert repository.list_evidence(job.job_id) == []


def test_submit_controlled_probe_job_skips_non_runner_probe_submission() -> None:
    repository, job_service = _repository_and_service()
    plan = DebugProbePlan(
        probe_id="probe-h-scoring",
        hypothesis_id="h-scoring",
        intervention_type="scoring_variant",
        intervention_payload={"variant": "lenient_semantic"},
        trials=1,
        success_criteria={"lenient_score_gt_strict_score": True},
        stop_condition="single deterministic rescore",
    )
    draft = build_controlled_probe_draft(
        source_case=_video_case(),
        source_job_id="job-source",
        plan=plan,
    )

    submitted = submit_controlled_probe_job(
        repository=repository,
        job_service=job_service,
        draft=draft,
        artifact_group_id="debug-run-1",
    )

    assert submitted is draft
    assert submitted.probe_result.probe_job_id == ""
    assert repository.get_case(submitted.derived_case.case_id) is None


def _video_case() -> DebugCase:
    return DebugCase.model_validate(
        {
            "case_id": "JSZN-096",
            "task_type": "generic_video_json",
            "image_uri": "https://example.com/source.mp4",
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
            "predictions": [{"trial": 0, "raw_output": "{}", "score": 0}],
            "avg_score": 0.0,
        }
    )


def _repository_and_service() -> tuple[DebugJobRepository, DebugJobService]:
    session_factory, engine = create_sqlite_memory_session_factory()
    ensure_database_schema(engine)
    repository = DebugJobRepository(session_factory)
    return repository, DebugJobService(repository)
