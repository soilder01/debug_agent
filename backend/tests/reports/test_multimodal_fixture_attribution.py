from debug_agent.cases.comparator import (
    parse_image_detection_output,
    parse_multimodal_detection_output,
    parse_video_detection_output,
)
from debug_agent.cases.fixtures import load_fixture_case
from debug_agent.cases.models import ImageDetectionOutput, MultimodalDetectionOutput, VideoDetectionOutput
from debug_agent.experiments.planner import plan_experiments
from debug_agent.experiments.runner import ExperimentEvidence, ExperimentRunResult
from debug_agent.judging.runner import (
    JudgeResult,
    judge_image_detection_output,
    judge_multimodal_detection_output,
    judge_video_detection_output,
)
from debug_agent.reports.generator import generate_initial_report


def test_fixture_attribution_covers_image_text_alignment() -> None:
    case = load_fixture_case("multimodal_image_text_alignment_001")
    expected = MultimodalDetectionOutput.model_validate(case.expected_output)
    predicted = parse_multimodal_detection_output(case.predictions[0].raw_output)
    judge = judge_multimodal_detection_output(expected, predicted, case.scoring_standard)
    run_result = ExperimentRunResult(
        case_id=case.case_id,
        total_trials=3,
        success_count=2,
        evidence=[
            ExperimentEvidence(
                evidence_id="e-image-only",
                step_name="modality_ablation_check",
                trial=0,
                request_summary={"ablation_variant": "image_only", "ablation_modalities": ["image"]},
                raw_output="{\"conflicts\":[]}",
                judge=JudgeResult(score=1, reasons=[]),
            ),
            ExperimentEvidence(
                evidence_id="e-text-only",
                step_name="modality_ablation_check",
                trial=1,
                request_summary={"ablation_variant": "text_only", "ablation_modalities": ["text"]},
                raw_output="{\"conflicts\":[]}",
                judge=JudgeResult(score=1, reasons=[]),
            ),
            ExperimentEvidence(
                evidence_id="e-cross-modal",
                step_name="modality_ablation_check",
                trial=2,
                request_summary={"ablation_variant": "cross_modal_compare", "ablation_modalities": ["image", "text"]},
                raw_output=case.predictions[0].raw_output,
                judge=judge,
            ),
        ],
    )

    report = generate_initial_report(case, plan_experiments(case), run_result)

    assert report.root_cause.label == "cross_modal_alignment_failure"
    assert report.root_cause.confidence == "high"
    assert report.suggested_sheet_fields["错误原因"].startswith("跨模态对齐问题")


def test_fixture_attribution_covers_single_image_detection() -> None:
    case = load_fixture_case("single_image_detection_001")
    expected = ImageDetectionOutput.model_validate(case.expected_output)
    predicted = parse_image_detection_output(case.predictions[0].raw_output)
    judge = judge_image_detection_output(expected, predicted, case.scoring_standard)
    run_result = ExperimentRunResult(
        case_id=case.case_id,
        total_trials=1,
        success_count=0,
        evidence=[
            ExperimentEvidence(
                evidence_id="e-image-region",
                step_name="baseline_replay",
                trial=0,
                request_summary={"ablation_variant": "image_only", "ablation_modalities": ["image"]},
                raw_output=case.predictions[0].raw_output,
                judge=judge,
            )
        ],
    )

    report = generate_initial_report(case, plan_experiments(case), run_result)

    assert report.root_cause.label == "single_modality_capability_gap"
    assert report.root_cause_trace[0]["target_ids"] == ["image:region:1"]
    assert "image_only" in report.root_cause.evidence_summary


def test_fixture_attribution_covers_video_timestamp_boundaries() -> None:
    case = load_fixture_case("video_action_timestamp_001")
    expected = VideoDetectionOutput.model_validate(case.expected_output)
    predicted = parse_video_detection_output(case.predictions[0].raw_output)
    judge = judge_video_detection_output(expected, predicted, case.scoring_standard)
    run_result = ExperimentRunResult(
        case_id=case.case_id,
        total_trials=1,
        success_count=0,
        evidence=[
            ExperimentEvidence(
                evidence_id="e-video-timestamp",
                step_name="temporal_schema_check",
                trial=0,
                request_summary={"ablation_variant": "video_timestamp", "ablation_modalities": ["video"]},
                raw_output=case.predictions[0].raw_output,
                judge=judge,
            )
        ],
    )

    report = generate_initial_report(case, plan_experiments(case), run_result)

    assert report.root_cause.label == "video_timestamp_boundary_error"
    assert report.root_cause_trace[0]["variant"] == "video_timestamp"
    assert report.recommended_actions[0]["summary"] == "补强视频时序边界定位。"
