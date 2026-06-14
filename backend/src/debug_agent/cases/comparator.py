import json

from pydantic import BaseModel

from debug_agent.cases.models import (
    AnswerSet,
    ClassificationOutput,
    ImageDetectionOutput,
    ImageRegionOutput,
    VideoDetectionOutput,
    VideoSegmentOutput,
)


class AnswerDelta(BaseModel):
    box_id: int
    expected: str | None
    predicted: str | None
    reason: str


class DetectionDelta(BaseModel):
    target_id: str
    expected: str | None
    actual: str | None
    reason: str
    metadata: dict[str, object]


class AnswerDiff(BaseModel):
    has_differences: bool
    affected_box_ids: list[int]
    deltas: list[AnswerDelta]
    detection_deltas: list[DetectionDelta]


class ClassificationDiff(BaseModel):
    has_differences: bool
    detection_deltas: list[dict[str, object]]


class ImageDetectionDiff(BaseModel):
    has_differences: bool
    detection_deltas: list[dict[str, object]]


class VideoDetectionDiff(BaseModel):
    has_differences: bool
    detection_deltas: list[dict[str, object]]


def parse_prediction_answer(raw_output: str) -> AnswerSet:
    payload = json.loads(raw_output)
    return AnswerSet.model_validate(payload)


def parse_classification_output(raw_output: str) -> ClassificationOutput:
    payload = json.loads(raw_output)
    return ClassificationOutput.model_validate(payload)


def parse_image_detection_output(raw_output: str) -> ImageDetectionOutput:
    payload = json.loads(raw_output)
    return ImageDetectionOutput.model_validate(payload)


def parse_video_detection_output(raw_output: str) -> VideoDetectionOutput:
    payload = json.loads(raw_output)
    return VideoDetectionOutput.model_validate(payload)


def compare_classification_outputs(
    expected: ClassificationOutput,
    predicted: ClassificationOutput,
) -> ClassificationDiff:
    if expected.label == predicted.label:
        return ClassificationDiff(has_differences=False, detection_deltas=[])
    return ClassificationDiff(
        has_differences=True,
        detection_deltas=[
            DetectionDelta(
                target_id="label:classification",
                expected=expected.label,
                actual=predicted.label,
                reason="label_mismatch",
                metadata={"field": "label", "confidence": predicted.confidence},
            ).model_dump()
        ],
    )


def compare_image_detection_outputs(
    expected: ImageDetectionOutput,
    predicted: ImageDetectionOutput,
) -> ImageDetectionDiff:
    expected_by_target = {region.target_id: region for region in expected.regions}
    predicted_by_target = {region.target_id: region for region in predicted.regions}
    all_target_ids = sorted(set(expected_by_target) | set(predicted_by_target))
    deltas: list[dict[str, object]] = []

    for target_id in all_target_ids:
        expected_region = expected_by_target.get(target_id)
        predicted_region = predicted_by_target.get(target_id)
        delta = _image_region_delta(target_id, expected_region, predicted_region)
        if delta is not None:
            deltas.append(delta)

    return ImageDetectionDiff(has_differences=bool(deltas), detection_deltas=deltas)


def compare_video_detection_outputs(
    expected: VideoDetectionOutput,
    predicted: VideoDetectionOutput,
) -> VideoDetectionDiff:
    expected_by_target = {segment.target_id: segment for segment in expected.temporal_segments}
    predicted_by_target = {segment.target_id: segment for segment in predicted.temporal_segments}
    all_target_ids = sorted(set(expected_by_target) | set(predicted_by_target))
    deltas: list[dict[str, object]] = []

    for target_id in all_target_ids:
        expected_segment = expected_by_target.get(target_id)
        predicted_segment = predicted_by_target.get(target_id)
        delta = _video_segment_delta(target_id, expected_segment, predicted_segment)
        if delta is not None:
            deltas.append(delta)

    return VideoDetectionDiff(has_differences=bool(deltas), detection_deltas=deltas)


def compare_answer_sets(expected: AnswerSet, predicted: AnswerSet) -> AnswerDiff:
    expected_by_box = {item.box_id: item.student_answer for item in expected.answers}
    predicted_by_box = {item.box_id: item.student_answer for item in predicted.answers}
    all_box_ids = sorted(set(expected_by_box) | set(predicted_by_box))
    deltas: list[AnswerDelta] = []

    for box_id in all_box_ids:
        expected_value = expected_by_box.get(box_id)
        predicted_value = predicted_by_box.get(box_id)
        if expected_value == predicted_value:
            continue
        reason = "student_answer_mismatch"
        if expected_value is None:
            reason = "extra_box"
        elif predicted_value is None:
            reason = "missing_box"
        deltas.append(
            AnswerDelta(
                box_id=box_id,
                expected=expected_value,
                predicted=predicted_value,
                reason=reason,
            )
        )

    return AnswerDiff(
        has_differences=bool(deltas),
        affected_box_ids=[delta.box_id for delta in deltas],
        deltas=deltas,
        detection_deltas=[_answer_delta_to_detection_delta(delta) for delta in deltas],
    )


def _answer_delta_to_detection_delta(delta: AnswerDelta) -> DetectionDelta:
    return DetectionDelta(
        target_id=f"box:{delta.box_id}",
        expected=delta.expected,
        actual=delta.predicted,
        reason=delta.reason,
        metadata={
            "box_id": delta.box_id,
            "field": "student_answer",
            "legacy_reason": delta.reason,
        },
    )


def _image_region_delta(
    target_id: str,
    expected_region: ImageRegionOutput | None,
    predicted_region: ImageRegionOutput | None,
) -> dict[str, object] | None:
    if expected_region is None and predicted_region is None:
        return None
    if expected_region is None:
        return DetectionDelta(
            target_id=target_id,
            expected=None,
            actual=_region_label(predicted_region),
            reason="extra_region",
            metadata={"field": "regions"},
        ).model_dump()
    if predicted_region is None:
        return DetectionDelta(
            target_id=target_id,
            expected=_region_label(expected_region),
            actual=None,
            reason="missing_region",
            metadata={"field": "regions"},
        ).model_dump()
    if expected_region.label != predicted_region.label:
        return DetectionDelta(
            target_id=target_id,
            expected=expected_region.label,
            actual=predicted_region.label,
            reason="region_label_mismatch",
            metadata={"field": "label", "confidence": predicted_region.confidence},
        ).model_dump()
    return None


def _region_label(region: ImageRegionOutput | None) -> str | None:
    if region is None or not region.label:
        return None
    return region.label


def _video_segment_delta(
    target_id: str,
    expected_segment: VideoSegmentOutput | None,
    predicted_segment: VideoSegmentOutput | None,
) -> dict[str, object] | None:
    if expected_segment is None and predicted_segment is None:
        return None
    if expected_segment is None:
        return DetectionDelta(
            target_id=target_id,
            expected=None,
            actual=_segment_label(predicted_segment),
            reason="extra_segment",
            metadata={"field": "temporal_segments"},
        ).model_dump()
    if predicted_segment is None:
        return DetectionDelta(
            target_id=target_id,
            expected=_segment_label(expected_segment),
            actual=None,
            reason="missing_segment",
            metadata={"field": "temporal_segments"},
        ).model_dump()
    if expected_segment.label != predicted_segment.label:
        return DetectionDelta(
            target_id=target_id,
            expected=expected_segment.label,
            actual=predicted_segment.label,
            reason="segment_label_mismatch",
            metadata={"field": "label", "confidence": predicted_segment.confidence},
        ).model_dump()
    return None


def _segment_label(segment: VideoSegmentOutput | None) -> str | None:
    if segment is None or not segment.label:
        return None
    return segment.label
