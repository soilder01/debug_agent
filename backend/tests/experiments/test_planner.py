import json
from pathlib import Path

from debug_agent.cases.models import DebugCase
from debug_agent.experiments.planner import plan_experiments
from debug_agent.recipes.handwriting_ocr import HandwritingOcrRecipe
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


def test_plan_experiments_routes_non_ocr_case_to_generic_recipe(monkeypatch) -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "classification-generic",
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
    original_plan_steps = GenericDebugRecipe.plan_steps

    def recording_steps(self, *, case: DebugCase, baseline_trials: int):
        nonlocal called
        called = True
        return original_plan_steps(self, case=case, baseline_trials=baseline_trials)

    monkeypatch.setattr(GenericDebugRecipe, "plan_steps", recording_steps)

    plan = plan_experiments(case, baseline_trials=2)

    assert called is True
    assert [step.name for step in plan.steps] == ["baseline_replay", "schema_review"]
