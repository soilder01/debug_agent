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
from debug_agent.artifacts.videos import (
    materialize_multimodal_conflict_manifest,
    materialize_video_segment_manifest,
    video_keyframe_thumbnails,
)
from debug_agent.cases.comparator import (
    compare_answer_sets,
    parse_classification_output,
    parse_image_detection_output,
    parse_multimodal_detection_output,
    parse_prediction_answer,
    parse_video_detection_output,
)
from debug_agent.cases.models import (
    AnswerSet,
    ClassificationOutput,
    DebugCase,
    ImageDetectionOutput,
    MultimodalDetectionOutput,
    VideoDetectionOutput,
)
from debug_agent.experiments.planner import AblationVariant, ExperimentPlan, ExperimentStep
from debug_agent.judging.runner import (
    JudgeResult,
    judge_answer,
    judge_classification_output,
    judge_image_detection_output,
    judge_multimodal_detection_output,
    judge_video_detection_output,
)
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
            ablation_variant = _ablation_variant_for_trial(step=step, trial_index=trial_index)
            prompt = _build_step_prompt(
                case=case,
                step_name=step.name,
                ablation_variant=ablation_variant,
            )
            request_image_uri = _image_uri_for_variant(case=case, ablation_variant=ablation_variant)
            try:
                response = await adapter.generate(prompt=prompt, image_uri=request_image_uri)
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
                            image_uri=request_image_uri,
                            scoring_standard=case.scoring_standard,
                            ablation_variant=ablation_variant,
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
                            judge=judge,
                            request_image_uri=request_image_uri,
                            ablation_variant=ablation_variant,
                            image_artifact_dir=image_artifact_dir,
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
                elif case.task_type == "image_detection":
                    judge = _judge_image_detection_response(case=case, raw_output=response.raw_output)
                elif case.task_type == "video_detection":
                    judge = _judge_video_detection_response(case=case, raw_output=response.raw_output)
                elif case.task_type == "multimodal_detection":
                    judge = _judge_multimodal_detection_response(case=case, raw_output=response.raw_output)
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
                        image_uri=request_image_uri,
                        scoring_standard=case.scoring_standard,
                        ablation_variant=ablation_variant,
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
                        judge=judge,
                        request_image_uri=request_image_uri,
                        ablation_variant=ablation_variant,
                        image_artifact_dir=image_artifact_dir,
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


def _build_request_summary(
    prompt: str,
    image_uri: str,
    scoring_standard: str,
    ablation_variant: AblationVariant | None = None,
) -> dict[str, object]:
    parsed_uri = urlparse(image_uri)
    summary: dict[str, object] = {
        "agent_role": "model_runner",
        "prompt_length": len(prompt),
        "has_image": bool(image_uri),
        "image_uri_scheme": parsed_uri.scheme,
        "scoring_standard_present": bool(scoring_standard.strip()),
    }
    if ablation_variant is not None:
        summary["ablation_variant"] = ablation_variant.name
        summary["ablation_modalities"] = ablation_variant.modalities
    return summary


def _judge_classification_response(case: DebugCase, raw_output: str) -> JudgeResult:
    predicted = parse_classification_output(raw_output)
    expected = _classification_expected_output(case)
    return judge_classification_output(expected, predicted, scoring_standard=case.scoring_standard)


def _classification_expected_output(case: DebugCase) -> ClassificationOutput:
    label = case.expected_output.get("label")
    if isinstance(label, str) and label:
        confidence = case.expected_output.get("confidence")
        return ClassificationOutput(
            label=label,
            confidence=confidence if isinstance(confidence, int | float) else None,
        )
    if not case.golden_answer.answers:
        raise ValueError("classification case requires at least one golden answer label")
    return ClassificationOutput(label=case.golden_answer.answers[0].student_answer)


def _judge_image_detection_response(case: DebugCase, raw_output: str) -> JudgeResult:
    predicted = parse_image_detection_output(raw_output)
    expected = ImageDetectionOutput.model_validate(case.expected_output)
    return judge_image_detection_output(expected, predicted, scoring_standard=case.scoring_standard)


def _judge_video_detection_response(case: DebugCase, raw_output: str) -> JudgeResult:
    predicted = parse_video_detection_output(raw_output)
    expected = VideoDetectionOutput.model_validate(case.expected_output)
    return judge_video_detection_output(expected, predicted, scoring_standard=case.scoring_standard)


def _judge_multimodal_detection_response(case: DebugCase, raw_output: str) -> JudgeResult:
    predicted = parse_multimodal_detection_output(raw_output)
    expected = MultimodalDetectionOutput.model_validate(case.expected_output)
    return judge_multimodal_detection_output(expected, predicted, scoring_standard=case.scoring_standard)


def _build_step_prompt(
    case: DebugCase,
    step_name: str,
    ablation_variant: AblationVariant | None = None,
) -> str:
    recipe = recipe_for_task_type(case.task_type)
    prompt = recipe.build_step_prompt(case=case, step_name=step_name)
    if ablation_variant is None:
        return prompt
    return "\n".join(
        [
            prompt,
            "",
            f"Ablation variant: {ablation_variant.name}",
            f"Ablation modalities: {', '.join(ablation_variant.modalities) or 'none'}",
            ablation_variant.prompt_instructions,
        ]
    )


def _build_generic_artifacts(
    *,
    case: DebugCase,
    step_name: str,
    trial_index: int,
    raw_output: str,
    image_artifacts: list[ImageArtifact],
    response_parse_error: str,
    judge: JudgeResult | None = None,
    request_image_uri: str | None = None,
    ablation_variant: AblationVariant | None = None,
    image_artifact_dir: Path | None = None,
) -> list[EvidenceArtifact]:
    artifacts = _image_artifacts_to_evidence_artifacts(image_artifacts)
    if judge is not None:
        artifacts.extend(
            _build_native_delta_artifacts(
                case=case,
                step_name=step_name,
                trial_index=trial_index,
                deltas=judge.deltas,
                source_image_uri=request_image_uri if request_image_uri is not None else case.image_uri,
                image_artifact_dir=image_artifact_dir,
            )
        )
    artifacts.append(
        EvidenceArtifact(
            artifact_id=f"{case.case_id}:{step_name}:{trial_index}:input-snapshot",
            kind="input_snapshot",
            artifact_type="request",
            source_uri=request_image_uri if request_image_uri is not None else case.image_uri,
            metadata=_input_snapshot_metadata(
                case=case,
                ablation_variant=ablation_variant,
            ),
        )
    )
    artifacts.append(
        EvidenceArtifact(
            artifact_id=f"{case.case_id}:{step_name}:{trial_index}:structured-output",
            kind="structured_output",
            artifact_type="model_output",
            derived_uri=_materialize_structured_output(
                raw_output=raw_output,
                output_dir=image_artifact_dir,
                artifact_id=f"{case.case_id}:{step_name}:{trial_index}:structured-output",
            ),
            metadata={
                "raw_output_length": len(raw_output),
                "response_parse_error": response_parse_error,
                "raw_output_persisted": image_artifact_dir is not None,
            },
        )
    )
    return artifacts


def _materialize_structured_output(*, raw_output: str, output_dir: Path | None, artifact_id: str) -> str:
    if output_dir is None:
        return ""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{_safe_artifact_filename(artifact_id)}.txt"
    output_path.write_text(raw_output, encoding="utf-8")
    return output_path.resolve().as_uri()


def _safe_artifact_filename(artifact_id: str) -> str:
    return "".join(character if character.isalnum() or character in {"-", "_"} else "_" for character in artifact_id)


def _input_snapshot_metadata(
    *,
    case: DebugCase,
    ablation_variant: AblationVariant | None,
) -> dict[str, object]:
    metadata: dict[str, object] = {
        "task_type": case.task_type,
        "prompt_length": len(case.prompt),
        "scoring_standard_present": bool(case.scoring_standard.strip()),
    }
    if ablation_variant is not None:
        metadata["ablation_variant"] = ablation_variant.name
        metadata["ablation_modalities"] = ablation_variant.modalities
    return metadata


def _ablation_variant_for_trial(*, step: ExperimentStep, trial_index: int) -> AblationVariant | None:
    if not step.ablation_variants:
        return None
    return step.ablation_variants[trial_index % len(step.ablation_variants)]


def _image_uri_for_variant(*, case: DebugCase, ablation_variant: AblationVariant | None) -> str:
    if ablation_variant is not None and ablation_variant.image_uri is not None:
        return ablation_variant.image_uri
    return case.image_uri


def _build_native_delta_artifacts(
    *,
    case: DebugCase,
    step_name: str,
    trial_index: int,
    deltas: list[dict[str, object]],
    source_image_uri: str,
    image_artifact_dir: Path | None,
) -> list[EvidenceArtifact]:
    artifacts: list[EvidenceArtifact] = []
    for delta in deltas:
        target_id = _delta_target_id(delta)
        artifact_type = _artifact_type_from_target_id(target_id)
        if not target_id or not artifact_type:
            continue
        metadata = _native_delta_metadata(delta)
        artifact_id = f"{case.case_id}:{step_name}:{trial_index}:{_delta_artifact_fragment(target_id, metadata)}:delta"
        region = _image_region_from_delta(delta) if artifact_type == "image_region" else None
        derived_uri = ""
        preview_url = ""
        if image_artifact_dir is not None and region is not None:
            try:
                derived_uri = materialize_image_crop(
                    source_image_uri=source_image_uri,
                    region=region,
                    output_dir=image_artifact_dir,
                    artifact_id=artifact_id,
                )
                preview_url = image_artifact_preview_url(artifact_id)
            except (OSError, ValueError):
                derived_uri = ""
                preview_url = ""
        if image_artifact_dir is not None and artifact_type == "video_segment":
            metadata["keyframe_thumbnails"] = video_keyframe_thumbnails(artifact_id=artifact_id, metadata=metadata)
            derived_uri = materialize_video_segment_manifest(
                artifact_id=artifact_id,
                source_uri=source_image_uri,
                metadata=metadata,
                output_dir=image_artifact_dir,
            )
            metadata["manifest_type"] = "video_segment_delta"
        if image_artifact_dir is not None and artifact_type == "multimodal_conflict":
            derived_uri = materialize_multimodal_conflict_manifest(
                artifact_id=artifact_id,
                source_uri=source_image_uri,
                metadata=metadata,
                output_dir=image_artifact_dir,
            )
            metadata["manifest_type"] = "multimodal_conflict_delta"
        artifacts.append(
            EvidenceArtifact(
                artifact_id=artifact_id,
                kind=f"{artifact_type}_delta",
                artifact_type=artifact_type,
                source_uri=source_image_uri,
                derived_uri=derived_uri,
                preview_url=preview_url,
                region=region,
                metadata=metadata,
            )
        )
    return artifacts


def _delta_target_id(delta: dict[str, object]) -> str:
    target_id = delta.get("target_id")
    return target_id if isinstance(target_id, str) else ""


def _artifact_type_from_target_id(target_id: str) -> str:
    if target_id.startswith("image:region:"):
        return "image_region"
    if target_id.startswith("video:segment:"):
        return "video_segment"
    if target_id.startswith("multimodal:conflict:"):
        return "multimodal_conflict"
    return ""


def _safe_target_fragment(target_id: str) -> str:
    return target_id.replace(":", "_")


def _delta_artifact_fragment(target_id: str, metadata: dict[str, object]) -> str:
    fragment = _safe_target_fragment(target_id)
    reason = str(metadata.get("reason") or "")
    field = str(metadata.get("field") or "")
    if reason.startswith("timestamp_"):
        return "_".join(part for part in [fragment, field, reason] if part)
    return fragment


def _image_region_from_delta(delta: dict[str, object]) -> ImageRegion | None:
    metadata = delta.get("metadata")
    if not isinstance(metadata, dict):
        return None
    region_payload = metadata.get("actual_region") or metadata.get("expected_region")
    if not isinstance(region_payload, dict):
        return None
    try:
        return ImageRegion.model_validate(region_payload)
    except ValueError:
        return None


def _native_delta_metadata(delta: dict[str, object]) -> dict[str, object]:
    metadata: dict[str, object] = {
        "target_id": str(delta.get("target_id") or ""),
        "reason": str(delta.get("reason") or ""),
        "expected": _metadata_value(delta.get("expected")),
        "actual": _metadata_value(delta.get("actual")),
    }
    nested_metadata = delta.get("metadata")
    if isinstance(nested_metadata, dict):
        metadata.update(nested_metadata)
    return metadata


def _metadata_value(value: object) -> object:
    if value is None or isinstance(value, str | int | float | bool | list | dict):
        return value
    return str(value)


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
