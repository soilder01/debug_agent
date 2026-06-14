from pathlib import Path
from time import perf_counter
from typing import Self
from urllib.parse import urlparse

from pydantic import BaseModel, Field, model_validator

from debug_agent.artifacts.images import (
    EvidenceArtifact,
    ImageArtifact,
    ImageRegion,
    image_artifact_preview_url,
    materialize_image_crop,
)
from debug_agent.cases.comparator import compare_answer_sets, parse_classification_output, parse_prediction_answer
from debug_agent.cases.models import AnswerSet, ClassificationOutput, DebugCase
from debug_agent.experiments.planner import ExperimentPlan
from debug_agent.judging.runner import JudgeResult, judge_answer, judge_classification_output
from debug_agent.models.adapters import ModelAdapter
from debug_agent.recipes import recipe_for_task_type


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
    artifacts: list[EvidenceArtifact] = Field(default_factory=list)
    raw_output: str
    judge: JudgeResult

    @model_validator(mode="after")
    def _populate_generic_artifacts_from_images(self) -> Self:
        if not self.artifacts and self.image_artifacts:
            self.artifacts = _image_artifacts_to_evidence_artifacts(self.image_artifacts)
        return self


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
                        artifacts=_build_generic_artifacts(
                            case=case,
                            step_name=step.name,
                            trial_index=trial_index,
                            raw_output="",
                            image_artifacts=[],
                            response_parse_error="",
                        ),
                        raw_output="",
                        judge=judge,
                    )
                )
                continue
            latency_ms = int((perf_counter() - started_at) * 1000)
            response_parse_error = ""
            image_artifacts: list[ImageArtifact] = []
            try:
                if case.task_type == "classification":
                    judge = _judge_classification_response(case=case, raw_output=response.raw_output)
                else:
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
                    artifacts=_build_generic_artifacts(
                        case=case,
                        step_name=step.name,
                        trial_index=trial_index,
                        raw_output=response.raw_output,
                        image_artifacts=image_artifacts,
                        response_parse_error=response_parse_error,
                    ),
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
        "agent_role": "model_runner",
        "prompt_length": len(prompt),
        "has_image": bool(image_uri),
        "image_uri_scheme": parsed_uri.scheme,
        "scoring_standard_present": bool(scoring_standard.strip()),
    }


def _judge_classification_response(case: DebugCase, raw_output: str) -> JudgeResult:
    predicted = parse_classification_output(raw_output)
    expected = _classification_expected_output(case)
    return judge_classification_output(expected, predicted, scoring_standard=case.scoring_standard)


def _classification_expected_output(case: DebugCase) -> ClassificationOutput:
    if not case.golden_answer.answers:
        raise ValueError("classification case requires at least one golden answer label")
    return ClassificationOutput(label=case.golden_answer.answers[0].student_answer)


def _build_step_prompt(case: DebugCase, step_name: str) -> str:
    recipe = recipe_for_task_type(case.task_type)
    return recipe.build_step_prompt(case=case, step_name=step_name)


def _build_generic_artifacts(
    *,
    case: DebugCase,
    step_name: str,
    trial_index: int,
    raw_output: str,
    image_artifacts: list[ImageArtifact],
    response_parse_error: str,
) -> list[EvidenceArtifact]:
    artifacts = _image_artifacts_to_evidence_artifacts(image_artifacts)
    artifacts.append(
        EvidenceArtifact(
            artifact_id=f"{case.case_id}:{step_name}:{trial_index}:input-snapshot",
            kind="input_snapshot",
            artifact_type="request",
            source_uri=case.image_uri,
            metadata={
                "task_type": case.task_type,
                "prompt_length": len(case.prompt),
                "scoring_standard_present": bool(case.scoring_standard.strip()),
            },
        )
    )
    artifacts.append(
        EvidenceArtifact(
            artifact_id=f"{case.case_id}:{step_name}:{trial_index}:structured-output",
            kind="structured_output",
            artifact_type="model_output",
            metadata={
                "raw_output_length": len(raw_output),
                "response_parse_error": response_parse_error,
            },
        )
    )
    return artifacts


def _image_artifacts_to_evidence_artifacts(image_artifacts: list[ImageArtifact]) -> list[EvidenceArtifact]:
    return [_image_artifact_to_evidence_artifact(artifact) for artifact in image_artifacts]


def _image_artifact_to_evidence_artifact(artifact: ImageArtifact) -> EvidenceArtifact:
    target_id = _target_id_from_image_artifact(artifact)
    metadata: dict[str, object] = {"legacy_kind": artifact.kind}
    if target_id:
        metadata["target_id"] = target_id
    return EvidenceArtifact(
        artifact_id=artifact.artifact_id,
        kind=artifact.kind,
        artifact_type="image",
        source_uri=artifact.source_image_uri,
        derived_uri=artifact.derived_image_uri,
        preview_url=artifact.preview_image_url,
        region=artifact.region,
        metadata=metadata,
    )


def _target_id_from_image_artifact(artifact: ImageArtifact) -> str:
    for token in artifact.artifact_id.split(":"):
        if token.startswith("box-"):
            box_id = token.removeprefix("box-")
            if box_id.isdigit():
                return f"box:{box_id}"
    return ""


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
