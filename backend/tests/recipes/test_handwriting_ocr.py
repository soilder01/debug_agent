import json
from pathlib import Path

from debug_agent.cases.models import DebugCase
from debug_agent.recipes.handwriting_ocr import HandwritingOcrRecipe


def test_handwriting_ocr_recipe_builds_existing_experiment_steps() -> None:
    fixture_path = Path(__file__).parents[1] / "fixtures" / "handwrite233.json"
    case = DebugCase.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))
    recipe = HandwritingOcrRecipe()

    steps = recipe.plan_steps(case=case, baseline_trials=5)

    assert [step.name for step in steps] == [
        "baseline_replay",
        "strict_prompt_replay",
        "localized_observation_request",
    ]
    assert steps[0].trials == 5
    assert steps[1].trials == 3
    assert steps[2].trials == 2


def test_handwriting_ocr_recipe_adds_localized_region_prompt_context() -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "recipe-localized",
            "image_uri": "file:///tmp/recipe-localized.png",
            "prompt": "识别作答区域。",
            "golden_answer": {"answers": [{"box_id": 7, "student_answer": "低昷烘干"}]},
            "scoring_standard": "box_id and student_answer must match.",
            "predictions": [
                {
                    "trial": 0,
                    "raw_output": "{\"answers\":[{\"box_id\":7,\"student_answer\":\"低温烘干\"}]}",
                    "score": 0,
                }
            ],
            "avg_score": 0.0,
            "box_regions": [
                {
                    "box_id": 7,
                    "x": 12,
                    "y": 34,
                    "width": 56,
                    "height": 78,
                    "unit": "pixel",
                    "label": "box-7",
                }
            ],
        }
    )
    recipe = HandwritingOcrRecipe()

    prompt = recipe.build_step_prompt(case=case, step_name="localized_observation_request")

    assert "localized_observation_request" in prompt
    assert "Focus on the following affected answer regions before producing final JSON." in prompt
    assert "box 7" in prompt
    assert "x=12, y=34, width=56, height=78, unit=pixel, label=box-7" in prompt
