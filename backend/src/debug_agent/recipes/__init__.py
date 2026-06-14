from debug_agent.recipes.classification import ClassificationRecipe
from debug_agent.recipes.handwriting_ocr import HandwritingOcrRecipe
from debug_agent.recipes.image_detection import ImageDetectionRecipe
from debug_agent.recipes.registry import GenericDebugRecipe, RecipeRegistry, recipe_for_task_type
from debug_agent.recipes.video_detection import VideoDetectionRecipe

__all__ = [
    "ClassificationRecipe",
    "GenericDebugRecipe",
    "HandwritingOcrRecipe",
    "ImageDetectionRecipe",
    "RecipeRegistry",
    "VideoDetectionRecipe",
    "recipe_for_task_type",
]
