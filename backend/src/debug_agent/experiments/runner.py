from pathlib import Path
from time import perf_counter
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from debug_agent.artifacts.images import (
    ImageArtifact,
    ImageRegion,
    image_artifact_preview_url,
    materialize_image_crop,
)
from debug_agent.cases.comparator import compare_answer_sets, parse_prediction_answer
from debug_agent.cases.models import AnswerSet, DebugCase
from debug_agent.experiments.planner import ExperimentPlan
from debug_agent.judging.runner import JudgeResult, judge_answer
from debug_agent.models.adapters import ModelAdapter


class ExperimentEvidence(BaseModel):
    evidence_id: str
    step_name: str
    trial: int
    model_name: str = ""
    model_provider: str = ""
    model_id: str = ""
    request_summary: dict[str, object] = {}
    latency_ms: int = 0
    response_parse_error: str = ""
    model_call_error_type: str = ""
    model_call_error_message: str = ""
    image_artifacts: list[ImageArtifact] = Field(default_factory=list)
    raw_output: str
    judge: JudgeResult


class ExperimentRunResult(BaseModel):
    case_id: str
    total_trials: int
    success_count: int
    evidence: list[ExperimentEvidence]


async def run_experiments(
    case: DebugCase,
    plan: ExperimentPlan,
    adapter: ModelAdapter,
    image_artifact_dir: Path | None = None,
) -> ExperimentRunResult:
    evidence: list[ExperimentEvidence] = []
    success_count = 0
    for step in plan.steps:
        for trial_index in range(step.trials):
            started_at = perf_counter()
            model_call_error_type = ""
            model_call_error_message = ""
            prompt = _build_step_prompt(case=case, step_name=step.name)
            try:
                response = await adapter.generate(prompt=prompt, image_uri=case.image_uri)
            except Exception as exc:
                latency_ms = int((perf_counter() - started_at) * 1000)
                model_call_error_type = type(exc).__name__
                model_call_error_message = str(exc)
                judge = JudgeResult(score=0, reasons=["model_call_error"])
                evidence.append(
                    ExperimentEvidence(
                        evidence_id=f"{case.case_id}:{step.name}:{trial_index}",
                        step_name=step.name,
                        trial=trial_index,
                        request_summary=_build_request_summary(
                            prompt=prompt,
                            image_uri=case.image_uri,
                            scoring_standard=case.scoring_standard,
                        ),
                        latency_ms=latency_ms,
                        model_call_error_type=model_call_error_type,
                        model_call_error_message=model_call_error_message,
                        raw_output="",
                        judge=judge,
                    )
                )
                continue
            latency_ms = int((perf_counter() - started_at) * 1000)
            response_parse_error = ""
            image_artifacts: list[ImageArtifact] = []
            try:
                predicted = parse_prediction_answer(response.raw_output)
                judge = judge_answer(case.golden_answer, predicted, scoring_standard=case.scoring_standard)
                image_artifacts = _build_localized_image_artifacts(
                    case=case,
                    step_name=step.name,
                    predicted=predicted,
                    image_artifact_dir=image_artifact_dir,
                )
            except Exception as exc:
                response_parse_error = str(exc)
                judge = JudgeResult(score=0, reasons=["response_parse_error"])
            success_count += judge.score
            evidence.append(
                ExperimentEvidence(
                    evidence_id=f"{case.case_id}:{step.name}:{trial_index}",
                    step_name=step.name,
                    trial=trial_index,
                    model_name=response.model_name,
                    model_provider=response.model_provider,
                    model_id=response.model_id,
                    request_summary=_build_request_summary(
                        prompt=prompt,
                        image_uri=case.image_uri,
                        scoring_standard=case.scoring_standard,
                    ),
                    latency_ms=latency_ms,
                    response_parse_error=response_parse_error,
                    model_call_error_type=model_call_error_type,
                    model_call_error_message=model_call_error_message,
                    image_artifacts=image_artifacts,
                    raw_output=response.raw_output,
                    judge=judge,
                )
            )
    return ExperimentRunResult(
        case_id=case.case_id,
        total_trials=len(evidence),
        success_count=success_count,
        evidence=evidence,
    )


def _build_request_summary(prompt: str, image_uri: str, scoring_standard: str) -> dict[str, object]:
    parsed_uri = urlparse(image_uri)
    return {
        "prompt_length": len(prompt),
        "has_image": bool(image_uri),
        "image_uri_scheme": parsed_uri.scheme,
        "scoring_standard_present": bool(scoring_standard.strip()),
    }


def _build_step_prompt(case: DebugCase, step_name: str) -> str:
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


def _build_localized_image_artifacts(
    case: DebugCase,
    step_name: str,
    predicted: AnswerSet,
    image_artifact_dir: Path | None = None,
) -> list[ImageArtifact]:
    if step_name != "localized_observation_request" or not case.image_uri:
        return []

    diff = compare_answer_sets(case.golden_answer, predicted)
    regions_by_box_id = {
        region.box_id: ImageRegion(
            x=region.x,
            y=region.y,
            width=region.width,
            height=region.height,
            unit=region.unit,
            label=region.label,
        )
        for region in case.box_regions
    }
    artifacts: list[ImageArtifact] = []
    for box_id in diff.affected_box_ids:
        artifact_id = f"{case.case_id}:box-{box_id}:localized-candidate"
        region = regions_by_box_id.get(box_id)
        derived_image_uri = ""
        preview_image_url = ""
        if image_artifact_dir is not None and region is not None:
            try:
                derived_image_uri = materialize_image_crop(
                    source_image_uri=case.image_uri,
                    region=region,
                    output_dir=image_artifact_dir,
                    artifact_id=artifact_id,
                )
                preview_image_url = image_artifact_preview_url(artifact_id)
            except (OSError, ValueError):
                derived_image_uri = ""
                preview_image_url = ""
        artifacts.append(
            ImageArtifact(
                artifact_id=artifact_id,
                kind="affected_box_candidate",
                source_image_uri=case.image_uri,
                region=region,
                derived_image_uri=derived_image_uri,
                preview_image_url=preview_image_url,
            )
        )
    return artifacts
