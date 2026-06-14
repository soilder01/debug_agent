import json
from pathlib import Path

from debug_agent.cases.models import DebugCase
from debug_agent.experiments.planner import plan_experiments
from debug_agent.recipes.classification import ClassificationRecipe
from debug_agent.recipes.handwriting_ocr import HandwritingOcrRecipe
from debug_agent.recipes.image_detection import ImageDetectionRecipe
from debug_agent.recipes.registry import GenericDebugRecipe


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
