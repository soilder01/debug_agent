from debug_agent.cases.comparator import compare_answer_sets, parse_prediction_answer
from debug_agent.cases.models import DebugCase
from debug_agent.experiments.planner import ExperimentStep


class HandwritingOcrRecipe:
    task_type = "handwriting_ocr"

    def plan_steps(self, *, case: DebugCase, baseline_trials: int) -> list[ExperimentStep]:
        del case
        return [
            ExperimentStep(
                name="baseline_replay",
                description="Replay the original prompt and image condition to confirm the failure.",
                trials=baseline_trials,
            ),
            ExperimentStep(
                name="strict_prompt_replay",
                description="Replay with stronger instruction to avoid semantic correction and guessing.",
                trials=3,
            ),
            ExperimentStep(
                name="localized_observation_request",
                description="Ask the model to describe the affected answer region before extracting final JSON.",
                trials=2,
            ),
        ]

    def build_step_prompt(self, *, case: DebugCase, step_name: str) -> str:
        if step_name != "localized_observation_request":
            return case.prompt

        affected_box_ids = _affected_box_ids_from_predictions(case)
        if not affected_box_ids:
            return case.prompt

        regions_by_box_id = {region.box_id: region for region in case.box_regions}
        region_lines: list[str] = []
        for box_id in affected_box_ids:
            region = regions_by_box_id.get(box_id)
            if region is None:
                region_lines.append(f"- box {box_id}: region unknown")
                continue
            region_lines.append(
                f"- box {box_id}: x={region.x}, y={region.y}, width={region.width}, "
                f"height={region.height}, unit={region.unit}, label={region.label}"
            )

        return "\n".join(
            [
                case.prompt,
                "",
                "localized_observation_request:",
                "Focus on the following affected answer regions before producing final JSON.",
                *region_lines,
            ]
        )


def recipe_for_task_type(task_type: str) -> HandwritingOcrRecipe:
    del task_type
    return HandwritingOcrRecipe()


def _affected_box_ids_from_predictions(case: DebugCase) -> list[int]:
    for prediction in case.predictions:
        try:
            predicted = parse_prediction_answer(prediction.raw_output)
        except Exception:
            continue
        diff = compare_answer_sets(case.golden_answer, predicted)
        if diff.affected_box_ids:
            return diff.affected_box_ids
    return []
