from debug_agent.cases.models import DebugCase, ImageDetectionOutput
from debug_agent.experiments.planner import ExperimentStep


class ImageDetectionRecipe:
    task_type = "image_detection"

    def plan_steps(self, *, case: DebugCase, baseline_trials: int) -> list[ExperimentStep]:
        del case
        return [
            ExperimentStep(
                name="baseline_replay",
                description="Replay the original image detection prompt and input to confirm the failure.",
                trials=baseline_trials,
            ),
            ExperimentStep(
                name="region_schema_check",
                description="Check whether region target ids, labels, and coordinates match the expected schema.",
                trials=2,
            ),
            ExperimentStep(
                name="localization_prompt_check",
                description="Ask the model to localize expected image targets explicitly and isolate grounding errors.",
                trials=2,
            ),
        ]

    def build_step_prompt(self, *, case: DebugCase, step_name: str) -> str:
        if step_name == "region_schema_check":
            return "\n".join(
                [
                    case.prompt,
                    "",
                    "region_schema_check:",
                    "Return only image-native JSON with a regions array.",
                    "Each region must include target_id, x, y, width, height, unit, label, and optional confidence.",
                    f"Expected target ids: {_expected_region_target_ids(case)}",
                    f"Scoring standard: {case.scoring_standard}",
                ]
            )
        if step_name == "localization_prompt_check":
            return "\n".join(
                [
                    case.prompt,
                    "",
                    "localization_prompt_check:",
                    "Ground each answer in the visual evidence before choosing the label.",
                    "Focus on the requested image regions and do not use OCR answer-box assumptions.",
                    f"Expected target ids: {_expected_region_target_ids(case)}",
                    f"Scoring standard: {case.scoring_standard}",
                ]
            )
        return case.prompt


def _expected_region_target_ids(case: DebugCase) -> str:
    expected = ImageDetectionOutput.model_validate(case.expected_output)
    target_ids = [region.target_id for region in expected.regions]
    return ", ".join(target_ids) if target_ids else "none"
