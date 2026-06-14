from debug_agent.cases.models import DebugCase, VideoDetectionOutput
from debug_agent.experiments.planner import ExperimentStep


class VideoDetectionRecipe:
    task_type = "video_detection"

    def plan_steps(self, *, case: DebugCase, baseline_trials: int) -> list[ExperimentStep]:
        del case
        return [
            ExperimentStep(
                name="baseline_replay",
                description="Replay the original video detection prompt and input to confirm the failure.",
                trials=baseline_trials,
            ),
            ExperimentStep(
                name="temporal_schema_check",
                description="Check whether temporal segment target ids, labels, and time windows match the expected schema.",
                trials=2,
            ),
            ExperimentStep(
                name="temporal_grounding_check",
                description="Ask the model to ground events in time windows and isolate temporal reasoning errors.",
                trials=2,
            ),
        ]

    def build_step_prompt(self, *, case: DebugCase, step_name: str) -> str:
        if step_name == "temporal_schema_check":
            return "\n".join(
                [
                    case.prompt,
                    "",
                    "temporal_schema_check:",
                    "Return only video-native JSON with a temporal_segments array.",
                    "Each segment must include target_id, start_ms, end_ms, label, and optional confidence.",
                    f"Expected target ids: {_expected_segment_target_ids(case)}",
                    f"Scoring standard: {case.scoring_standard}",
                ]
            )
        if step_name == "temporal_grounding_check":
            return "\n".join(
                [
                    case.prompt,
                    "",
                    "temporal_grounding_check:",
                    "Ground each event in the visual timeline before choosing the label.",
                    "Focus on temporal evidence and do not use still-image or OCR answer-box assumptions.",
                    f"Expected target ids: {_expected_segment_target_ids(case)}",
                    f"Scoring standard: {case.scoring_standard}",
                ]
            )
        return case.prompt


def _expected_segment_target_ids(case: DebugCase) -> str:
    expected = VideoDetectionOutput.model_validate(case.expected_output)
    target_ids = [segment.target_id for segment in expected.temporal_segments]
    return ", ".join(target_ids) if target_ids else "none"
