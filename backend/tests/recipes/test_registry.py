from debug_agent.recipes import recipe_for_task_type
from debug_agent.recipes.handwriting_ocr import HandwritingOcrRecipe


def test_registry_routes_handwriting_ocr_to_ocr_recipe() -> None:
    recipe = recipe_for_task_type("handwriting_ocr")

    assert isinstance(recipe, HandwritingOcrRecipe)


def test_registry_routes_unknown_task_type_to_generic_recipe() -> None:
    recipe = recipe_for_task_type("unknown_task")

    assert recipe.task_type == "generic"
    assert not isinstance(recipe, HandwritingOcrRecipe)
