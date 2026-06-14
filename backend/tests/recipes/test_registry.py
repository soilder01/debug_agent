from debug_agent.recipes import recipe_for_task_type
from debug_agent.recipes.handwriting_ocr import HandwritingOcrRecipe
from debug_agent.recipes.image_detection import ImageDetectionRecipe
from debug_agent.recipes.multimodal_detection import MultimodalDetectionRecipe
from debug_agent.recipes.video_detection import VideoDetectionRecipe


def test_registry_routes_handwriting_ocr_to_ocr_recipe() -> None:
    recipe = recipe_for_task_type("handwriting_ocr")

    assert isinstance(recipe, HandwritingOcrRecipe)


def test_registry_routes_unknown_task_type_to_generic_recipe() -> None:
    recipe = recipe_for_task_type("unknown_task")

    assert recipe.task_type == "generic"
    assert not isinstance(recipe, HandwritingOcrRecipe)


def test_registry_routes_image_detection_to_image_recipe() -> None:
    recipe = recipe_for_task_type("image_detection")

    assert isinstance(recipe, ImageDetectionRecipe)


def test_registry_routes_video_detection_to_video_recipe() -> None:
    recipe = recipe_for_task_type("video_detection")

    assert isinstance(recipe, VideoDetectionRecipe)


def test_registry_routes_multimodal_detection_to_multimodal_recipe() -> None:
    recipe = recipe_for_task_type("multimodal_detection")

    assert isinstance(recipe, MultimodalDetectionRecipe)
