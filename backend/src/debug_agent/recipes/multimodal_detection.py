from debug_agent.cases.models import DebugCase, MultimodalDetectionOutput
from debug_agent.experiments.planner import ExperimentStep


class MultimodalDetectionRecipe:
    task_type = "multimodal_detection"

    def plan_steps(self, *, case: DebugCase, baseline_trials: int) -> list[ExperimentStep]:
        del case
        return [
            ExperimentStep(
                name="baseline_replay",
                description="Replay the original multimodal prompt and inputs to confirm the failure.",
                trials=baseline_trials,
            ),
            ExperimentStep(
                name="cross_modal_schema_check",
                description="Check whether conflict target ids, modalities, and conflict types match the output contract.",
                trials=2,
            ),
            ExperimentStep(
                name="modality_ablation_check",
                description="Isolate modality contribution through prompt ablation and single-modality reasoning.",
                trials=2,
            ),
            ExperimentStep(
                name="conflict_grounding_check",
                description="Ground each conflict in exact image, video, text, or audio evidence before judging.",
                trials=2,
            ),
        ]

    def build_step_prompt(self, *, case: DebugCase, step_name: str) -> str:
        if step_name == "cross_modal_schema_check":
            return "\n".join(
                [
                    case.prompt,
                    "",
                    "cross_modal_schema_check:",
                    "Return only multimodal-native JSON with a conflicts array.",
                    "Each conflict must include target_id, conflict_type, modalities, expected, actual, and optional confidence.",
                    f"Expected conflicts: {_expected_conflict_summary(case)}",
                    f"Scoring standard: {case.scoring_standard}",
                ]
            )
        if step_name == "modality_ablation_check":
            return "\n".join(
                [
                    case.prompt,
                    "",
                    "modality_ablation_check:",
                    "Reason about each modality independently, then compare the cross-modal claims.",
                    "State which modality provides the strongest evidence for each conflict target.",
                    f"Expected conflicts: {_expected_conflict_summary(case)}",
                    f"Scoring standard: {case.scoring_standard}",
                ]
            )
        if step_name == "conflict_grounding_check":
            return "\n".join(
                [
                    case.prompt,
                    "",
                    "conflict_grounding_check:",
                    "Ground each conflict in concrete multimodal evidence and avoid single-modality shortcuts.",
                    f"Expected conflicts: {_expected_conflict_summary(case)}",
                    f"Scoring standard: {case.scoring_standard}",
                ]
            )
        return case.prompt


def _expected_conflict_summary(case: DebugCase) -> str:
    expected = MultimodalDetectionOutput.model_validate(case.expected_output)
    summaries = [
        f"{conflict.target_id} ({conflict.conflict_type}: {', '.join(conflict.modalities)})"
        for conflict in expected.conflicts
    ]
    return "; ".join(summaries) if summaries else "none"
