from debug_agent.cases.models import DebugCase
from debug_agent.experiments.planner import ExperimentStep


class ClassificationRecipe:
    task_type = "classification"

    def plan_steps(self, *, case: DebugCase, baseline_trials: int) -> list[ExperimentStep]:
        del case
        return [
            ExperimentStep(
                name="baseline_replay",
                description="Replay the original classification prompt and input to confirm the failure.",
                trials=baseline_trials,
            ),
            ExperimentStep(
                name="label_schema_check",
                description="Check whether the response label schema matches the expected output contract.",
                trials=2,
            ),
            ExperimentStep(
                name="counterfactual_prompt_check",
                description="Replay with explicit label options to isolate prompt sensitivity.",
                trials=2,
            ),
        ]

    def build_step_prompt(self, *, case: DebugCase, step_name: str) -> str:
        if step_name == "label_schema_check":
            return "\n".join(
                [
                    case.prompt,
                    "",
                    "label_schema_check:",
                    "Verify that the response includes the expected label and follows the scoring standard.",
                    f"Scoring standard: {case.scoring_standard}",
                ]
            )
        if step_name == "counterfactual_prompt_check":
            return "\n".join(
                [
                    case.prompt,
                    "",
                    "counterfactual_prompt_check:",
                    "Focus only on the classification label. Do not infer extra fields beyond the expected output.",
                    f"Scoring standard: {case.scoring_standard}",
                ]
            )
        return case.prompt
