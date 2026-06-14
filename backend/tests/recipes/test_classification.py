from debug_agent.cases.models import DebugCase
from debug_agent.recipes import recipe_for_task_type
from debug_agent.recipes.classification import ClassificationRecipe


def make_classification_case() -> DebugCase:
    return DebugCase.model_validate(
        {
            "case_id": "classification-recipe",
            "task_type": "classification",
            "image_uri": "",
            "prompt": "Classify sentiment and return JSON.",
            "golden_answer": {"answers": [{"box_id": 1, "student_answer": "positive"}]},
            "scoring_standard": "label must match exactly.",
            "predictions": [
                {
                    "trial": 0,
                    "raw_output": "{\"answers\":[{\"box_id\":1,\"student_answer\":\"negative\"}]}",
                    "score": 0,
                }
            ],
            "avg_score": 0.0,
        }
    )


def test_classification_recipe_builds_label_debug_steps() -> None:
    recipe = ClassificationRecipe()
    case = make_classification_case()

    steps = recipe.plan_steps(case=case, baseline_trials=4)

    assert [step.name for step in steps] == [
        "baseline_replay",
        "label_schema_check",
        "counterfactual_prompt_check",
    ]
    assert steps[0].trials == 4
    assert steps[1].trials == 2
    assert steps[2].trials == 2


def test_classification_recipe_builds_label_focused_prompts_without_ocr_terms() -> None:
    recipe = ClassificationRecipe()
    case = make_classification_case()

    prompt = recipe.build_step_prompt(case=case, step_name="label_schema_check")

    assert "label_schema_check" in prompt
    assert "expected label" in prompt
    assert "scoring standard" in prompt
    assert "handwriting" not in prompt.lower()
    assert "box region" not in prompt.lower()
    assert "affected answer region" not in prompt.lower()


def test_registry_routes_classification_to_classification_recipe() -> None:
    recipe = recipe_for_task_type("classification")

    assert isinstance(recipe, ClassificationRecipe)
