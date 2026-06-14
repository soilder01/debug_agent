from debug_agent.recipes.classification import ClassificationRecipe
from debug_agent.recipes.handwriting_ocr import HandwritingOcrRecipe
from debug_agent.recipes.image_detection import ImageDetectionRecipe
from debug_agent.recipes.registry import GenericDebugRecipe, RecipeRegistry, recipe_for_task_type

__all__ = [
    "ClassificationRecipe",
    "GenericDebugRecipe",
    "HandwritingOcrRecipe",
    "ImageDetectionRecipe",
    "RecipeRegistry",
    "recipe_for_task_type",
]
