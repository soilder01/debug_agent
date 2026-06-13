import json
from pathlib import Path

from debug_agent.cases.models import DebugCase
from debug_agent.experiments.planner import plan_experiments
from debug_agent.experiments.runner import ExperimentEvidence, ExperimentRunResult
from debug_agent.judging.runner import JudgeResult
from debug_agent.reports.generator import generate_initial_report


def test_generate_initial_report_for_failed_case() -> None:
    fixture_path = Path(__file__).parents[1] / "fixtures" / "handwrite233.json"
    case = DebugCase.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))
    plan = plan_experiments(case)

    report = generate_initial_report(case, plan)

    assert report.case_id == "handwrite233"
    assert report.status == "needs_human_review"
    assert report.root_cause.label == "erasure_revision_failure"
    assert report.suggested_sheet_fields["debug1状态"] == "待人工确认"


def test_generate_report_includes_experiment_summary() -> None:
    fixture_path = Path(__file__).parents[1] / "fixtures" / "handwrite233.json"
    case = DebugCase.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))
    plan = plan_experiments(case)
    run_result = ExperimentRunResult(
        case_id=case.case_id,
        total_trials=1,
        success_count=0,
        evidence=[
            ExperimentEvidence(
                evidence_id="e1",
                step_name="baseline_replay",
                trial=0,
                image_artifacts=[
                    {
                        "artifact_id": "case-1:box-7:localized-candidate",
                        "kind": "affected_box_candidate",
                        "source_image_uri": "file:///tmp/case-1.png",
                    }
                ],
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=0, reasons=["box 1 student_answer_mismatch"]),
            )
        ],
    )

    report = generate_initial_report(case, plan, run_result)

    assert report.experiment_summary is not None
    assert report.experiment_summary.total_trials == 1
    assert report.experiment_summary.success_count == 0
    assert report.experiment_summary.evidence_ids == ["e1"]
    assert report.experiment_summary.image_artifact_ids == ["case-1:box-7:localized-candidate"]


def test_generate_report_summarizes_replay_stability() -> None:
    fixture_path = Path(__file__).parents[1] / "fixtures" / "handwrite233.json"
    case = DebugCase.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))
    plan = plan_experiments(case)
    run_result = ExperimentRunResult(
        case_id=case.case_id,
        total_trials=3,
        success_count=1,
        evidence=[
            ExperimentEvidence(
                evidence_id="e-pass",
                step_name="baseline_replay",
                trial=0,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=1, reasons=[]),
            ),
            ExperimentEvidence(
                evidence_id="e-fail-1",
                step_name="baseline_replay",
                trial=1,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=0, reasons=["box 1 student_answer_mismatch"]),
            ),
            ExperimentEvidence(
                evidence_id="e-fail-2",
                step_name="baseline_replay",
                trial=2,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=0, reasons=["box 2 student_answer_mismatch"]),
            ),
        ],
    )

    report = generate_initial_report(case, plan, run_result)

    assert report.experiment_summary is not None
    assert report.experiment_summary.failed_trial_count == 2
    assert report.experiment_summary.success_rate == 1 / 3
    assert report.experiment_summary.stability_label == "unstable"


def test_generate_report_infers_root_cause_from_structured_judge_deltas() -> None:
    fixture_path = Path(__file__).parents[1] / "fixtures" / "handwrite233.json"
    case = DebugCase.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))
    plan = plan_experiments(case)
    run_result = ExperimentRunResult(
        case_id=case.case_id,
        total_trials=1,
        success_count=0,
        evidence=[
            ExperimentEvidence(
                evidence_id="e-structured",
                step_name="baseline_replay",
                trial=0,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(
                    score=0,
                    reasons=["box 7 student_answer_mismatch"],
                    scoring_standard=case.scoring_standard,
                    affected_box_ids=[7],
                    deltas=[
                        {
                            "box_id": 7,
                            "expected": "低昷烘干",
                            "predicted": "低温烘干",
                            "reason": "student_answer_mismatch",
                        }
                    ],
                ),
            )
        ],
    )

    report = generate_initial_report(case, plan, run_result)

    assert report.observed_failure.type == "answer_mismatch"
    assert report.observed_failure.affected_box_ids == [7]
    assert "box 7" in report.observed_failure.summary
    assert report.root_cause.label == "answer_mismatch"
    assert report.root_cause.confidence == "high"
    assert "student_answer_mismatch" in report.root_cause.evidence_summary
    assert "box 7" in report.suggested_sheet_fields["错误原因"]


def test_generate_report_prioritizes_runtime_failures_before_answer_mismatch() -> None:
    fixture_path = Path(__file__).parents[1] / "fixtures" / "handwrite233.json"
    case = DebugCase.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))
    plan = plan_experiments(case)
    run_result = ExperimentRunResult(
        case_id=case.case_id,
        total_trials=1,
        success_count=0,
        evidence=[
            ExperimentEvidence(
                evidence_id="e-timeout",
                step_name="baseline_replay",
                trial=0,
                model_call_error_type="TimeoutError",
                model_call_error_message="model request timed out",
                raw_output="",
                judge=JudgeResult(score=0, reasons=["model_call_error"]),
            )
        ],
    )

    report = generate_initial_report(case, plan, run_result)

    assert report.observed_failure.type == "model_call_error"
    assert report.root_cause.label == "model_call_error"
    assert report.root_cause.confidence == "high"
    assert "TimeoutError" in report.root_cause.evidence_summary
