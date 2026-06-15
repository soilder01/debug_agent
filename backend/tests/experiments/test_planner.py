import json
from pathlib import Path

from debug_agent.cases.models import DebugCase
from debug_agent.experiments.planner import plan_experiments, plan_verification_follow_up_experiments
from debug_agent.recipes.classification import ClassificationRecipe
from debug_agent.recipes.handwriting_ocr import HandwritingOcrRecipe
from debug_agent.recipes.image_detection import ImageDetectionRecipe
from debug_agent.recipes.multimodal_detection import MultimodalDetectionRecipe
from debug_agent.recipes.registry import GenericDebugRecipe
from debug_agent.recipes.video_detection import VideoDetectionRecipe


def test_plan_experiments_for_low_score_case() -> None:
    fixture_path = Path(__file__).parents[1] / "fixtures" / "handwrite233.json"
    case = DebugCase.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))

    plan = plan_experiments(case)

    assert plan.case_id == "handwrite233"
    assert plan.max_model_calls == 10
    assert [step.name for step in plan.steps] == [
        "baseline_replay",
        "strict_prompt_replay",
        "localized_observation_request",
    ]


def test_plan_experiments_uses_requested_baseline_trials() -> None:
    fixture_path = Path(__file__).parents[1] / "fixtures" / "handwrite233.json"
    case = DebugCase.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))

    plan = plan_experiments(case, baseline_trials=5)

    assert plan.steps[0].name == "baseline_replay"
    assert plan.steps[0].trials == 5
    assert plan.max_model_calls == 10


def test_plan_experiments_routes_handwriting_ocr_case_to_recipe(monkeypatch) -> None:
    fixture_path = Path(__file__).parents[1] / "fixtures" / "handwrite233.json"
    case = DebugCase.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))
    called = False
    original_plan_steps = HandwritingOcrRecipe.plan_steps

    def recording_steps(self, *, case: DebugCase, baseline_trials: int):
        nonlocal called
        called = True
        return original_plan_steps(self, case=case, baseline_trials=baseline_trials)

    monkeypatch.setattr(HandwritingOcrRecipe, "plan_steps", recording_steps)

    plan = plan_experiments(case, baseline_trials=5)

    assert called is True
    assert [step.name for step in plan.steps] == [
        "baseline_replay",
        "strict_prompt_replay",
        "localized_observation_request",
    ]


def test_plan_experiments_routes_unknown_case_to_generic_recipe(monkeypatch) -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "unknown-generic",
            "task_type": "unknown_task",
            "image_uri": "",
            "prompt": "Return JSON.",
            "golden_answer": {"answers": [{"box_id": 1, "student_answer": "positive"}]},
            "scoring_standard": "label must match exactly.",
            "predictions": [{"trial": 0, "raw_output": "{\"answers\":[]}", "score": 0}],
            "avg_score": 0.0,
        }
    )
    called = False
    original_plan_steps = GenericDebugRecipe.plan_steps

    def recording_steps(self, *, case: DebugCase, baseline_trials: int):
        nonlocal called
        called = True
        return original_plan_steps(self, case=case, baseline_trials=baseline_trials)

    monkeypatch.setattr(GenericDebugRecipe, "plan_steps", recording_steps)

    plan = plan_experiments(case, baseline_trials=2)

    assert called is True
    assert [step.name for step in plan.steps] == ["baseline_replay", "schema_review"]


def test_plan_experiments_routes_classification_case_to_classification_recipe(monkeypatch) -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "classification-specific",
            "task_type": "classification",
            "image_uri": "",
            "prompt": "Classify sentiment and return JSON.",
            "golden_answer": {"answers": [{"box_id": 1, "student_answer": "positive"}]},
            "scoring_standard": "label must match exactly.",
            "predictions": [{"trial": 0, "raw_output": "{\"answers\":[]}", "score": 0}],
            "avg_score": 0.0,
        }
    )
    called = False
    original_plan_steps = ClassificationRecipe.plan_steps

    def recording_steps(self, *, case: DebugCase, baseline_trials: int):
        nonlocal called
        called = True
        return original_plan_steps(self, case=case, baseline_trials=baseline_trials)

    monkeypatch.setattr(ClassificationRecipe, "plan_steps", recording_steps)

    plan = plan_experiments(case, baseline_trials=2)

    assert called is True
    assert [step.name for step in plan.steps] == [
        "baseline_replay",
        "label_schema_check",
        "counterfactual_prompt_check",
    ]


def test_plan_experiments_routes_image_detection_case_to_image_recipe(monkeypatch) -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "image-detection-specific",
            "task_type": "image_detection",
            "image_uri": "file:///tmp/image.png",
            "prompt": "Detect objects and return region JSON.",
            "golden_answer": {"answers": [{"box_id": 1, "student_answer": "legacy-cat"}]},
            "expected_output": {
                "regions": [
                    {"target_id": "image:region:1", "x": 10, "y": 20, "width": 30, "height": 40, "label": "cat"}
                ]
            },
            "scoring_standard": "region target ids and labels must match.",
            "predictions": [{"trial": 0, "raw_output": "{\"regions\":[]}", "score": 0}],
            "avg_score": 0.0,
        }
    )
    called = False
    original_plan_steps = ImageDetectionRecipe.plan_steps

    def recording_steps(self, *, case: DebugCase, baseline_trials: int):
        nonlocal called
        called = True
        return original_plan_steps(self, case=case, baseline_trials=baseline_trials)

    monkeypatch.setattr(ImageDetectionRecipe, "plan_steps", recording_steps)

    plan = plan_experiments(case, baseline_trials=2)

    assert called is True
    assert [step.name for step in plan.steps] == [
        "baseline_replay",
        "region_schema_check",
        "localization_prompt_check",
    ]


def test_plan_experiments_routes_video_detection_case_to_video_recipe(monkeypatch) -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "video-detection-specific",
            "task_type": "video_detection",
            "image_uri": "file:///tmp/video.mp4",
            "prompt": "Detect events and return temporal segment JSON.",
            "golden_answer": {"answers": [{"box_id": 1, "student_answer": "legacy-event"}]},
            "expected_output": {
                "temporal_segments": [
                    {
                        "target_id": "video:segment:1",
                        "start_ms": 1000,
                        "end_ms": 2500,
                        "label": "person_enters",
                    }
                ]
            },
            "scoring_standard": "temporal segment target ids and labels must match.",
            "predictions": [{"trial": 0, "raw_output": "{\"temporal_segments\":[]}", "score": 0}],
            "avg_score": 0.0,
        }
    )
    called = False
    original_plan_steps = VideoDetectionRecipe.plan_steps

    def recording_steps(self, *, case: DebugCase, baseline_trials: int):
        nonlocal called
        called = True
        return original_plan_steps(self, case=case, baseline_trials=baseline_trials)

    monkeypatch.setattr(VideoDetectionRecipe, "plan_steps", recording_steps)

    plan = plan_experiments(case, baseline_trials=2)

    assert called is True
    assert [step.name for step in plan.steps] == [
        "baseline_replay",
        "temporal_schema_check",
        "temporal_grounding_check",
    ]


def test_plan_experiments_routes_multimodal_detection_case_to_multimodal_recipe(monkeypatch) -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "multimodal-detection-specific",
            "task_type": "multimodal_detection",
            "image_uri": "file:///tmp/multimodal-input.mp4",
            "prompt": "Compare the image and caption, then return cross-modal conflict JSON.",
            "golden_answer": {"answers": [{"box_id": 1, "student_answer": "legacy-conflict"}]},
            "expected_output": {
                "conflicts": [
                    {
                        "target_id": "multimodal:conflict:1",
                        "conflict_type": "visual_text_conflict",
                        "modalities": ["image", "text"],
                        "expected": "caption matches the visual subject",
                        "actual": "image and caption both describe a cat",
                    }
                ]
            },
            "scoring_standard": "cross-modal claims must agree.",
            "predictions": [{"trial": 0, "raw_output": "{\"conflicts\":[]}", "score": 0}],
            "avg_score": 0.0,
        }
    )
    called = False
    original_plan_steps = MultimodalDetectionRecipe.plan_steps

    def recording_steps(self, *, case: DebugCase, baseline_trials: int):
        nonlocal called
        called = True
        return original_plan_steps(self, case=case, baseline_trials=baseline_trials)

    monkeypatch.setattr(MultimodalDetectionRecipe, "plan_steps", recording_steps)

    plan = plan_experiments(case, baseline_trials=2)

    assert called is True
    assert [step.name for step in plan.steps] == [
        "baseline_replay",
        "cross_modal_schema_check",
        "modality_ablation_check",
        "conflict_grounding_check",
    ]


def test_plan_experiments_adds_multimodal_ablation_variants() -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "multimodal-detection-ablation-variants",
            "task_type": "multimodal_detection",
            "image_uri": "file:///tmp/multimodal-input.mp4",
            "prompt": "Compare the image and caption, then return cross-modal conflict JSON.",
            "golden_answer": {"answers": []},
            "expected_output": {
                "conflicts": [
                    {
                        "target_id": "multimodal:conflict:1",
                        "conflict_type": "visual_text_conflict",
                        "modalities": ["image", "text"],
                        "expected": "caption matches the visual subject",
                        "actual": "image and caption both describe a cat",
                    }
                ]
            },
            "scoring_standard": "cross-modal claims must agree.",
            "predictions": [{"trial": 0, "raw_output": "{\"conflicts\":[]}", "score": 0}],
            "avg_score": 0.0,
        }
    )

    plan = plan_experiments(case, baseline_trials=1)

    ablation_step = next(step for step in plan.steps if step.name == "modality_ablation_check")
    assert ablation_step.trials == 3
    assert [variant.name for variant in ablation_step.ablation_variants] == [
        "image_only",
        "text_only",
        "cross_modal_compare",
    ]
    assert ablation_step.ablation_variants[0].modalities == ["image"]
    assert "Ignore text" in ablation_step.ablation_variants[0].prompt_instructions
    assert ablation_step.ablation_variants[1].modalities == ["text"]
    assert "Ignore visual" in ablation_step.ablation_variants[1].prompt_instructions
    assert ablation_step.ablation_variants[2].modalities == ["image", "text"]


def test_plan_verification_follow_up_experiments_for_unresolved_multimodal_result() -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "multimodal-verification-unresolved",
            "task_type": "multimodal_detection",
            "image_uri": "file:///tmp/multimodal-input.mp4",
            "prompt": "Compare the image and caption, then return cross-modal conflict JSON.",
            "golden_answer": {"answers": []},
            "expected_output": {
                "conflicts": [
                    {
                        "target_id": "multimodal:conflict:1",
                        "conflict_type": "visual_text_conflict",
                        "modalities": ["image", "text"],
                        "expected": "caption matches the visual subject",
                        "actual": "image and caption both describe a cat",
                    }
                ]
            },
            "scoring_standard": "cross-modal claims must agree.",
            "predictions": [{"trial": 0, "raw_output": "{\"conflicts\":[]}", "score": 0}],
            "avg_score": 0.0,
        }
    )

    plan = plan_verification_follow_up_experiments(
        case,
        {
            "verification_job_id": "job-verify-1",
            "result": "not_resolved",
        },
        baseline_trials=2,
    )

    assert plan.case_id == "multimodal-verification-unresolved"
    assert [step.name for step in plan.steps] == [
        "baseline_replay",
        "cross_modal_schema_check",
        "modality_ablation_check",
        "conflict_grounding_check",
        "verification_unresolved_probe",
    ]
    follow_up_step = plan.steps[-1]
    assert follow_up_step.trials == 1
    assert follow_up_step.description == (
        "Probe unresolved verification job job-verify-1 with a targeted follow-up experiment."
    )


def test_plan_verification_follow_up_experiments_for_regressed_video_result() -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "video-verification-regressed",
            "task_type": "video_detection",
            "image_uri": "file:///tmp/video-input.mp4",
            "prompt": "Detect events and return temporal segment JSON.",
            "golden_answer": {"answers": []},
            "expected_output": {
                "temporal_segments": [
                    {"target_id": "video:segment:1", "start_ms": 1000, "end_ms": 2500, "label": "person_enters"}
                ]
            },
            "scoring_standard": "temporal segment target ids and labels must match.",
            "predictions": [{"trial": 0, "raw_output": "{\"temporal_segments\":[]}", "score": 0}],
            "avg_score": 0.0,
        }
    )

    plan = plan_verification_follow_up_experiments(
        case,
        {
            "verification_job_id": "job-verify-video",
            "result": "regressed",
        },
        baseline_trials=1,
    )

    assert [step.name for step in plan.steps] == [
        "baseline_replay",
        "temporal_schema_check",
        "temporal_grounding_check",
        "verification_regression_probe",
    ]
    assert plan.steps[-1].description == (
        "Probe regressed verification job job-verify-video with a targeted follow-up experiment."
    )
