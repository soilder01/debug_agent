import json

import pytest

from debug_agent.cases.models import DebugCase
from debug_agent.experiments.runner import ExperimentEvidence
from debug_agent.jobs.auto_closure import run_auto_debug_closure
from debug_agent.jobs.auto_closure_report import build_auto_closure_markdown_report
from debug_agent.jobs.service import DebugJobService
from debug_agent.judging.runner import JudgeResult
from debug_agent.models.fake import FakeModelAdapter
from debug_agent.reports.job_report import build_report_for_job
from debug_agent.storage.database import (
    create_sqlite_memory_session_factory,
    ensure_database_schema,
)
from debug_agent.storage.repository import DebugJobRepository


@pytest.mark.asyncio
async def test_fixture_backed_hypothesis_closure_dogfood_path() -> None:
    repository, service, source_job_id, case = _repository_service_case_and_job()

    queued = await run_auto_debug_closure(
        repository=repository,
        job_service=service,
        job_id=source_job_id,
        actor="auto-debug-agent",
        submit_controlled_probes=True,
    )
    queued_prompt_probe = next(
        item for item in queued.probe_results if item["probe_id"] == "probe-h-prompt-constraint"
    )
    probe_job_id = str(queued_prompt_probe["probe_job_id"])
    probe_job = repository.get_job(probe_job_id)
    assert probe_job is not None
    assert probe_job.status == "created"

    repository.save_evidence(
        job_id=probe_job_id,
        case_id=probe_job.case_id,
        evidence=[_successful_prompt_probe_evidence(probe_job_id)],
    )
    repository.mark_completed(probe_job_id)

    compared = await run_auto_debug_closure(
        repository=repository,
        job_service=service,
        job_id=source_job_id,
        actor="auto-debug-agent",
        submit_controlled_probes=True,
    )
    report = build_report_for_job(repository, source_job_id)
    assert report is not None

    run_view = report.run_view["hypothesis_closure"]
    assert run_view["verified_root_cause_count"] == 1
    assert run_view["probe_results"][0]["status"] == "completed"
    assert run_view["verified_root_causes"][0]["probe_id"] == "probe-h-prompt-constraint"
    assert compared.writeback_status == "skipped_no_mapping"

    markdown = build_auto_closure_markdown_report(
        report=report,
        closure=compared,
        original_prompt=case.prompt,
        original_cot_excerpt="baseline omitted right-arm detail",
        original_prediction='{"video_action_segments":[]}',
        reference_answer=json.dumps(case.expected_output, ensure_ascii=False),
        scoring_ops=case.scoring_standard,
    )

    assert "## 调试过程一览" in markdown
    assert "runner 1 个" in markdown
    assert "已验证根因明细：`h-prompt-constraint` / `probe-h-prompt-constraint`" in markdown
    assert "Intervention improved success rate" in markdown
    assert "当前自动写回状态为 `skipped_no_mapping`" in markdown


def _repository_service_case_and_job() -> tuple[
    DebugJobRepository,
    DebugJobService,
    str,
    DebugCase,
]:
    session_factory, engine = create_sqlite_memory_session_factory()
    ensure_database_schema(engine)
    repository = DebugJobRepository(session_factory)
    service = DebugJobService(
        repository,
        model_provider=lambda _: FakeModelAdapter(outputs=['{"video_action_segments":[]}']),
    )
    case = _case()
    source_job_id = "dogfood-hypothesis-source-job"
    repository.save_case(case)
    repository.create_job(source_job_id, case.case_id, baseline_trials=1)
    repository.save_evidence(
        job_id=source_job_id,
        case_id=case.case_id,
        evidence=[_failed_baseline_evidence(source_job_id)],
    )
    repository.mark_completed(source_job_id)
    return repository, service, source_job_id, case


def _case() -> DebugCase:
    return DebugCase.model_validate(
        {
            "case_id": "JSZN-096-dogfood",
            "task_type": "generic_video_json",
            "image_uri": "file:///tmp/jszn-096.mp4",
            "prompt": "Return video_action_segments JSON and describe right-arm actions.",
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


def _failed_baseline_evidence(job_id: str) -> ExperimentEvidence:
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


def _successful_prompt_probe_evidence(job_id: str) -> ExperimentEvidence:
    return ExperimentEvidence(
        evidence_id=f"{job_id}:success",
        step_name="prompt_patch_intervention_rerun",
        trial=0,
        raw_output='{"video_action_segments":[{"detail":"右臂拿起，双臂配合套入"}]}',
        judge=JudgeResult(score=1, reasons=[]),
    )
