from collections.abc import Callable

from debug_agent.cases.models import DebugCase
from debug_agent.experiments.planner import ExperimentStep
from debug_agent.recipes.classification import ClassificationRecipe
from debug_agent.recipes.handwriting_ocr import HandwritingOcrRecipe
from debug_agent.recipes.image_detection import ImageDetectionRecipe
from debug_agent.recipes.multimodal_detection import MultimodalDetectionRecipe
from debug_agent.recipes.video_detection import VideoDetectionRecipe

class GenericDebugRecipe:
    task_type = "generic"

    def plan_steps(self, *, case: DebugCase, baseline_trials: int) -> list[ExperimentStep]:
        del case
        return [
            ExperimentStep(
                name="baseline_replay",
                description="Replay the original prompt and input to confirm the failure.",
                trials=baseline_trials,
            ),
            ExperimentStep(
                name="schema_review",
                description="Review whether the model output follows the expected structured response.",
                trials=1,
            ),
        ]

    def build_step_prompt(self, *, case: DebugCase, step_name: str) -> str:
        if step_name != "schema_review":
            return case.prompt
        return "\n".join(
            [
                case.prompt,
                "",
                "schema_review:",
                "Focus on whether the output schema, labels, and values match the scoring standard.",
            ]
        )


DebugRecipeInstance = (
    ClassificationRecipe
    | HandwritingOcrRecipe
    | ImageDetectionRecipe
    | MultimodalDetectionRecipe
    | VideoDetectionRecipe
    | GenericDebugRecipe
)
DebugRecipeFactory = Callable[[], DebugRecipeInstance]


class RecipeRegistry:
    def __init__(self) -> None:
        self._recipes: dict[str, DebugRecipeFactory] = {
            "classification": ClassificationRecipe,
            "handwriting_ocr": HandwritingOcrRecipe,
            "image_detection": ImageDetectionRecipe,
            "multimodal_detection": MultimodalDetectionRecipe,
            "video_detection": VideoDetectionRecipe,
        }

    def recipe_for_task_type(self, task_type: str) -> DebugRecipeInstance:
        recipe_factory = self._recipes.get(task_type)
        if recipe_factory is None:
            return GenericDebugRecipe()
        return recipe_factory()


_REGISTRY = RecipeRegistry()


def recipe_for_task_type(task_type: str) -> DebugRecipeInstance:
    return _REGISTRY.recipe_for_task_type(task_type)
