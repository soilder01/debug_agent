import json

from pydantic import BaseModel

from debug_agent.cases.models import AnswerSet, ClassificationOutput


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


def parse_prediction_answer(raw_output: str) -> AnswerSet:
    payload = json.loads(raw_output)
    return AnswerSet.model_validate(payload)


def parse_classification_output(raw_output: str) -> ClassificationOutput:
    payload = json.loads(raw_output)
    return ClassificationOutput.model_validate(payload)


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
