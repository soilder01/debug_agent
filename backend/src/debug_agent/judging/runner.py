import json

from pydantic import BaseModel, Field

from debug_agent.cases.comparator import (
    compare_answer_sets,
    compare_classification_outputs,
    compare_image_detection_outputs,
    compare_multimodal_detection_outputs,
    compare_video_detection_outputs,
    parse_json_payload,
)
from debug_agent.cases.models import (
    AnswerSet,
    ClassificationOutput,
    ImageDetectionOutput,
    MultimodalDetectionOutput,
    VideoDetectionOutput,
    VideoSegmentOutput,
)


class JudgeResult(BaseModel):
    score: int
    reasons: list[str]
    scoring_standard: str = ""
    affected_box_ids: list[int] = Field(default_factory=list)
    deltas: list[dict[str, object]] = Field(default_factory=list)


def judge_answer(expected: AnswerSet, predicted: AnswerSet, scoring_standard: str = "") -> JudgeResult:
    diff = compare_answer_sets(expected, predicted)
    if not diff.has_differences:
        return JudgeResult(score=1, reasons=[], scoring_standard=scoring_standard)
    return JudgeResult(
        score=0,
        reasons=[f"box {delta.box_id} {delta.reason}" for delta in diff.deltas],
        scoring_standard=scoring_standard,
        affected_box_ids=diff.affected_box_ids,
        deltas=[delta.model_dump() for delta in diff.detection_deltas],
    )


def judge_generic_json_output(
    expected_payload: object,
    raw_output: str,
    scoring_standard: str = "",
) -> JudgeResult:
    predicted_payload = parse_json_payload(raw_output)
    if _canonical_json(predicted_payload) == _canonical_json(expected_payload):
        return JudgeResult(score=1, reasons=[], scoring_standard=scoring_standard)
    return JudgeResult(
        score=0,
        reasons=["generic_json_mismatch"],
        scoring_standard=scoring_standard,
        deltas=[
            {
                "target_id": "generic_json:root",
                "reason": "json_payload_mismatch",
                "expected": expected_payload,
                "actual": predicted_payload,
            }
        ],
    )


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def judge_classification_output(
    expected: ClassificationOutput,
    predicted: ClassificationOutput,
    scoring_standard: str = "",
) -> JudgeResult:
    diff = compare_classification_outputs(expected, predicted)
    if not diff.has_differences:
        return JudgeResult(score=1, reasons=[], scoring_standard=scoring_standard)
    return JudgeResult(
        score=0,
        reasons=[f"{delta['target_id']} {delta['reason']}" for delta in diff.detection_deltas],
        scoring_standard=scoring_standard,
        deltas=diff.detection_deltas,
    )


def judge_image_detection_output(
    expected: ImageDetectionOutput,
    predicted: ImageDetectionOutput,
    scoring_standard: str = "",
) -> JudgeResult:
    diff = compare_image_detection_outputs(expected, predicted)
    if not diff.has_differences:
        return JudgeResult(score=1, reasons=[], scoring_standard=scoring_standard)
    return JudgeResult(
        score=0,
        reasons=[f"{delta['target_id']} {delta['reason']}" for delta in diff.detection_deltas],
        scoring_standard=scoring_standard,
        deltas=diff.detection_deltas,
    )


def judge_video_detection_output(
    expected: VideoDetectionOutput,
    predicted: VideoDetectionOutput,
    scoring_standard: str = "",
) -> JudgeResult:
    timestamp_result = _judge_check_timestamp(expected, predicted, scoring_standard)
    if timestamp_result is not None:
        return timestamp_result
    diff = compare_video_detection_outputs(expected, predicted)
    if not diff.has_differences:
        return JudgeResult(score=1, reasons=[], scoring_standard=scoring_standard)
    return JudgeResult(
        score=0,
        reasons=[f"{delta['target_id']} {delta['reason']}" for delta in diff.detection_deltas],
        scoring_standard=scoring_standard,
        deltas=diff.detection_deltas,
    )


def _judge_check_timestamp(
    expected: VideoDetectionOutput,
    predicted: VideoDetectionOutput,
    scoring_standard: str,
) -> JudgeResult | None:
    grids = _check_timestamp_grids(scoring_standard)
    if grids is None:
        return None
    expected_by_target = {segment.target_id: segment for segment in expected.temporal_segments}
    predicted_by_target = {segment.target_id: segment for segment in predicted.temporal_segments}
    deltas: list[dict[str, object]] = []
    previous_predicted_end_s: float | None = None
    for index, grid in enumerate(grids, start=1):
        target_id = f"video:segment:{index}"
        expected_segment = expected_by_target.get(target_id)
        predicted_segment = predicted_by_target.get(target_id)
        if predicted_segment is None:
            deltas.append(
                _timestamp_delta(
                    target_id=target_id,
                    expected_segment=expected_segment,
                    predicted_segment=None,
                    reason="missing_segment",
                    field="temporal_segments",
                    expected_range="",
                    actual_s=None,
                    delta_seconds=None,
                    grid=grid,
                )
            )
            continue
        start_delta = _timestamp_start_delta(
            target_id=target_id,
            expected_segment=expected_segment,
            predicted_segment=predicted_segment,
            grid=grid,
            previous_predicted_end_s=previous_predicted_end_s,
        )
        if start_delta is not None:
            deltas.append(start_delta)
        end_delta = _timestamp_end_delta(
            target_id=target_id,
            expected_segment=expected_segment,
            predicted_segment=predicted_segment,
            grid=grid,
        )
        if end_delta is not None:
            deltas.append(end_delta)
        previous_predicted_end_s = predicted_segment.end_ms / 1000
    if not deltas:
        return JudgeResult(score=1, reasons=[], scoring_standard=scoring_standard)
    return JudgeResult(
        score=0,
        reasons=[f"{delta['target_id']} {delta['reason']}" for delta in deltas],
        scoring_standard=scoring_standard,
        deltas=deltas,
    )


def _check_timestamp_grids(scoring_standard: str) -> list[dict[str, object]] | None:
    try:
        payload = json.loads(scoring_standard)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, list):
        return None
    for item in payload:
        if isinstance(item, dict) and item.get("op_name") == "check_timestamp":
            grids = item.get("grids")
            if isinstance(grids, list):
                return [grid for grid in grids if isinstance(grid, dict)]
    return None


def _timestamp_start_delta(
    *,
    target_id: str,
    expected_segment: VideoSegmentOutput | None,
    predicted_segment: VideoSegmentOutput,
    grid: dict[str, object],
    previous_predicted_end_s: float | None,
) -> dict[str, object] | None:
    start_rule = grid.get("start_s")
    actual_s = predicted_segment.start_ms / 1000
    if not isinstance(start_rule, dict):
        return None
    rule_type = start_rule.get("type")
    if rule_type == "range":
        min_s = _float_or_none(start_rule.get("min"))
        max_s = _float_or_none(start_rule.get("max"))
        if min_s is not None and max_s is not None and not min_s <= actual_s <= max_s:
            return _timestamp_delta(
                target_id=target_id,
                expected_segment=expected_segment,
                predicted_segment=predicted_segment,
                reason="timestamp_start_out_of_range",
                field="start_s",
                expected_range=f"{min_s:.1f}-{max_s:.1f}s",
                actual_s=actual_s,
                delta_seconds=_range_delta(actual_s, min_s, max_s),
                grid=grid,
            )
    if rule_type == "continue" and previous_predicted_end_s is not None:
        offset = _float_or_none(start_rule.get("offset")) or 0.0
        expected_s = round(previous_predicted_end_s + offset, 3)
        if abs(actual_s - expected_s) > 0.001:
            return _timestamp_delta(
                target_id=target_id,
                expected_segment=expected_segment,
                predicted_segment=predicted_segment,
                reason="timestamp_start_not_continuous",
                field="start_s",
                expected_range=f"{expected_s:.1f}s",
                actual_s=actual_s,
                delta_seconds=round(actual_s - expected_s, 3),
                grid=grid,
            )
    return None


def _timestamp_end_delta(
    *,
    target_id: str,
    expected_segment: VideoSegmentOutput | None,
    predicted_segment: VideoSegmentOutput,
    grid: dict[str, object],
) -> dict[str, object] | None:
    end_rule = grid.get("end_s")
    actual_s = predicted_segment.end_ms / 1000
    if not isinstance(end_rule, dict):
        return None
    if end_rule.get("type") != "range":
        return None
    min_s = _float_or_none(end_rule.get("min"))
    max_s = _float_or_none(end_rule.get("max"))
    if min_s is None or max_s is None or min_s <= actual_s <= max_s:
        return None
    return _timestamp_delta(
        target_id=target_id,
        expected_segment=expected_segment,
        predicted_segment=predicted_segment,
        reason="timestamp_end_out_of_range",
        field="end_s",
        expected_range=f"{min_s:.1f}-{max_s:.1f}s",
        actual_s=actual_s,
        delta_seconds=_range_delta(actual_s, min_s, max_s),
        grid=grid,
    )


def _timestamp_delta(
    *,
    target_id: str,
    expected_segment: VideoSegmentOutput | None,
    predicted_segment: VideoSegmentOutput | None,
    reason: str,
    field: str,
    expected_range: str,
    actual_s: float | None,
    delta_seconds: float | None,
    grid: dict[str, object],
) -> dict[str, object]:
    return {
        "target_id": target_id,
        "expected": expected_range,
        "actual": f"{actual_s:.1f}s" if actual_s is not None else None,
        "reason": reason,
        "metadata": {
            "field": field,
            "expected_start_s_range": _rule_range_text(grid.get("start_s")),
            "expected_end_s_range": _rule_range_text(grid.get("end_s")),
            "actual_start_s": predicted_segment.start_ms / 1000 if predicted_segment is not None else None,
            "actual_end_s": predicted_segment.end_ms / 1000 if predicted_segment is not None else None,
            "delta_seconds": delta_seconds,
            "expected_segment": _segment_context(expected_segment),
            "actual_segment": _segment_context(predicted_segment),
        },
    }


def _segment_context(segment: VideoSegmentOutput | None) -> dict[str, object] | None:
    if segment is None:
        return None
    return {"start_ms": segment.start_ms, "end_ms": segment.end_ms, "label": segment.label}


def _rule_range_text(rule: object) -> str:
    if not isinstance(rule, dict):
        return ""
    if rule.get("type") == "range":
        min_s = _float_or_none(rule.get("min"))
        max_s = _float_or_none(rule.get("max"))
        if min_s is not None and max_s is not None:
            return f"{min_s:.1f}-{max_s:.1f}"
    if rule.get("type") == "continue":
        offset = _float_or_none(rule.get("offset")) or 0.0
        return f"previous_end+{offset:.1f}"
    return ""


def _float_or_none(value: object) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


def _range_delta(actual_s: float, min_s: float, max_s: float) -> float:
    if actual_s < min_s:
        return round(actual_s - min_s, 3)
    return round(actual_s - max_s, 3)


def judge_multimodal_detection_output(
    expected: MultimodalDetectionOutput,
    predicted: MultimodalDetectionOutput,
    scoring_standard: str = "",
) -> JudgeResult:
    diff = compare_multimodal_detection_outputs(expected, predicted)
    if not diff.has_differences:
        return JudgeResult(score=1, reasons=[], scoring_standard=scoring_standard)
    return JudgeResult(
        score=0,
        reasons=[f"{delta['target_id']} {delta['reason']}" for delta in diff.detection_deltas],
        scoring_standard=scoring_standard,
        deltas=diff.detection_deltas,
    )
