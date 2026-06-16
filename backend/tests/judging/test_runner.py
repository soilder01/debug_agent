from debug_agent.cases.models import (
    AnswerSet,
    ClassificationOutput,
    ImageDetectionOutput,
    MultimodalDetectionOutput,
    VideoDetectionOutput,
)
from debug_agent.judging.runner import (
    judge_answer,
    judge_classification_output,
    judge_image_detection_output,
    judge_multimodal_detection_output,
    judge_video_detection_output,
)


def test_judge_answer_passes_exact_match() -> None:
    expected = AnswerSet.model_validate({"answers": [{"box_id": 1, "student_answer": "A"}]})
    predicted = AnswerSet.model_validate({"answers": [{"box_id": 1, "student_answer": "A"}]})

    result = judge_answer(expected, predicted)

    assert result.score == 1
    assert result.reasons == []


def test_judge_answer_explains_mismatch() -> None:
    expected = AnswerSet.model_validate({"answers": [{"box_id": 1, "student_answer": "低昷烘干"}]})
    predicted = AnswerSet.model_validate({"answers": [{"box_id": 1, "student_answer": "低温烘干"}]})

    result = judge_answer(expected, predicted, scoring_standard="box_id and student_answer must match exactly.")

    assert result.score == 0
    assert result.reasons == ["box 1 student_answer_mismatch"]
    assert result.scoring_standard == "box_id and student_answer must match exactly."
    assert result.affected_box_ids == [1]
    assert result.deltas == [
        {
            "target_id": "box:1",
            "expected": "低昷烘干",
            "actual": "低温烘干",
            "reason": "student_answer_mismatch",
            "metadata": {
                "box_id": 1,
                "field": "student_answer",
                "legacy_reason": "student_answer_mismatch",
            },
        }
    ]


def test_judge_answer_structures_missing_and_extra_boxes() -> None:
    expected = AnswerSet.model_validate(
        {"answers": [{"box_id": 1, "student_answer": "A"}, {"box_id": 2, "student_answer": "B"}]}
    )
    predicted = AnswerSet.model_validate(
        {"answers": [{"box_id": 1, "student_answer": "A"}, {"box_id": 3, "student_answer": "C"}]}
    )

    result = judge_answer(expected, predicted, scoring_standard="All expected boxes must be present.")

    assert result.score == 0
    assert result.reasons == ["box 2 missing_box", "box 3 extra_box"]
    assert result.affected_box_ids == [2, 3]
    assert result.deltas == [
        {
            "target_id": "box:2",
            "expected": "B",
            "actual": None,
            "reason": "missing_box",
            "metadata": {"box_id": 2, "field": "student_answer", "legacy_reason": "missing_box"},
        },
        {
            "target_id": "box:3",
            "expected": None,
            "actual": "C",
            "reason": "extra_box",
            "metadata": {"box_id": 3, "field": "student_answer", "legacy_reason": "extra_box"},
        },
    ]


def test_judge_classification_output_passes_exact_label_match() -> None:
    expected = ClassificationOutput(label="positive")
    predicted = ClassificationOutput(label="positive", confidence=0.91)

    result = judge_classification_output(expected, predicted, scoring_standard="label must match exactly.")

    assert result.score == 1
    assert result.reasons == []
    assert result.scoring_standard == "label must match exactly."


def test_judge_classification_output_returns_label_delta() -> None:
    expected = ClassificationOutput(label="positive")
    predicted = ClassificationOutput(label="negative", confidence=0.61)

    result = judge_classification_output(expected, predicted, scoring_standard="label must match exactly.")

    assert result.score == 0
    assert result.reasons == ["label:classification label_mismatch"]
    assert result.affected_box_ids == []
    assert result.deltas == [
        {
            "target_id": "label:classification",
            "expected": "positive",
            "actual": "negative",
            "reason": "label_mismatch",
            "metadata": {"field": "label", "confidence": 0.61},
        }
    ]


def test_judge_image_detection_output_returns_region_delta() -> None:
    expected = ImageDetectionOutput.model_validate(
        {"regions": [{"target_id": "image:region:1", "x": 1, "y": 2, "width": 3, "height": 4, "label": "cat"}]}
    )
    predicted = ImageDetectionOutput.model_validate(
        {
            "regions": [
                {
                    "target_id": "image:region:1",
                    "x": 1,
                    "y": 2,
                    "width": 3,
                    "height": 4,
                    "label": "dog",
                    "confidence": 0.57,
                }
            ]
        }
    )

    result = judge_image_detection_output(expected, predicted, scoring_standard="region labels must match.")

    assert result.score == 0
    assert result.reasons == ["image:region:1 region_label_mismatch"]
    assert result.affected_box_ids == []
    assert result.scoring_standard == "region labels must match."
    assert result.deltas == [
        {
            "target_id": "image:region:1",
            "expected": "cat",
            "actual": "dog",
            "reason": "region_label_mismatch",
            "metadata": {
                "field": "label",
                "confidence": 0.57,
                "expected_region": {"x": 1, "y": 2, "width": 3, "height": 4, "unit": "pixel", "label": "cat"},
                "actual_region": {"x": 1, "y": 2, "width": 3, "height": 4, "unit": "pixel", "label": "dog"},
            },
        }
    ]


def test_judge_video_detection_output_returns_segment_delta() -> None:
    expected = VideoDetectionOutput.model_validate(
        {
            "temporal_segments": [
                {"target_id": "video:segment:1", "start_ms": 1000, "end_ms": 2500, "label": "person_enters"}
            ]
        }
    )
    predicted = VideoDetectionOutput.model_validate(
        {
            "temporal_segments": [
                {
                    "target_id": "video:segment:1",
                    "start_ms": 1000,
                    "end_ms": 2500,
                    "label": "person_leaves",
                    "confidence": 0.62,
                }
            ]
        }
    )

    result = judge_video_detection_output(expected, predicted, scoring_standard="temporal segments must match.")

    assert result.score == 0
    assert result.reasons == ["video:segment:1 segment_label_mismatch"]
    assert result.affected_box_ids == []
    assert result.scoring_standard == "temporal segments must match."
    assert result.deltas == [
        {
            "target_id": "video:segment:1",
            "expected": "person_enters",
            "actual": "person_leaves",
            "reason": "segment_label_mismatch",
            "metadata": {
                "field": "label",
                "confidence": 0.62,
                "expected_segment": {"start_ms": 1000, "end_ms": 2500, "label": "person_enters"},
                "actual_segment": {"start_ms": 1000, "end_ms": 2500, "label": "person_leaves"},
            },
        }
    ]


def test_judge_video_detection_output_applies_check_timestamp_ranges() -> None:
    expected = VideoDetectionOutput.model_validate(
        {
            "temporal_segments": [
                {
                    "target_id": "video:segment:1",
                    "start_ms": 100,
                    "end_ms": 24000,
                    "label": "The right arm picks up the crab clamp and adjusts its position",
                }
            ]
        }
    )
    predicted = VideoDetectionOutput.model_validate(
        {
            "temporal_segments": [
                {
                    "target_id": "video:segment:1",
                    "start_ms": 0,
                    "end_ms": 34000,
                    "label": "The right arm picks up the crab clamp and adjusts its position",
                }
            ]
        }
    )
    scoring_standard = """
    [
      {
        "op_name": "check_timestamp",
        "format": "float",
        "in_key": "video_action_segments",
        "grids": [
          {
            "start_s": {"type": "range", "min": 0.0, "max": 1.0},
            "end_s": {"type": "range", "min": 22.0, "max": 24.0}
          }
        ]
      }
    ]
    """

    result = judge_video_detection_output(expected, predicted, scoring_standard=scoring_standard)

    assert result.score == 0
    assert result.reasons == ["video:segment:1 timestamp_end_out_of_range"]
    assert result.deltas == [
        {
            "target_id": "video:segment:1",
            "expected": "22.0-24.0s",
            "actual": "34.0s",
            "reason": "timestamp_end_out_of_range",
            "metadata": {
                "field": "end_s",
                "expected_start_s_range": "0.0-1.0",
                "expected_end_s_range": "22.0-24.0",
                "actual_start_s": 0.0,
                "actual_end_s": 34.0,
                "delta_seconds": 10.0,
                "expected_segment": {
                    "start_ms": 100,
                    "end_ms": 24000,
                    "label": "The right arm picks up the crab clamp and adjusts its position",
                },
                "actual_segment": {
                    "start_ms": 0,
                    "end_ms": 34000,
                    "label": "The right arm picks up the crab clamp and adjusts its position",
                },
            },
        }
    ]


def test_judge_video_detection_output_accepts_check_timestamp_continue_rules() -> None:
    expected = VideoDetectionOutput.model_validate(
        {
            "temporal_segments": [
                {"target_id": "video:segment:1", "start_ms": 100, "end_ms": 24000, "label": "first"},
                {"target_id": "video:segment:2", "start_ms": 24100, "end_ms": 44000, "label": "second"},
            ]
        }
    )
    predicted = VideoDetectionOutput.model_validate(
        {
            "temporal_segments": [
                {"target_id": "video:segment:1", "start_ms": 0, "end_ms": 23000, "label": "first"},
                {"target_id": "video:segment:2", "start_ms": 23100, "end_ms": 43500, "label": "second"},
            ]
        }
    )
    scoring_standard = """
    [
      {
        "op_name": "check_timestamp",
        "format": "float",
        "in_key": "video_action_segments",
        "grids": [
          {
            "start_s": {"type": "range", "min": 0.0, "max": 1.0},
            "end_s": {"type": "range", "min": 22.0, "max": 24.0}
          },
          {
            "start_s": {"type": "continue", "offset": 0.1},
            "end_s": {"type": "range", "min": 42.0, "max": 44.0}
          }
        ]
      }
    ]
    """

    result = judge_video_detection_output(expected, predicted, scoring_standard=scoring_standard)

    assert result.score == 1
    assert result.reasons == []
    assert result.deltas == []


def test_judge_multimodal_detection_output_returns_conflict_delta() -> None:
    expected = MultimodalDetectionOutput.model_validate(
        {
            "conflicts": [
                {
                    "target_id": "multimodal:conflict:1",
                    "conflict_type": "visual_text_conflict",
                    "modalities": ["image", "text"],
                    "expected": "caption matches the visual subject",
                    "actual": "image and caption both describe a cat",
                }
            ]
        }
    )
    predicted = MultimodalDetectionOutput.model_validate(
        {
            "conflicts": [
                {
                    "target_id": "multimodal:conflict:1",
                    "conflict_type": "visual_text_conflict",
                    "modalities": ["image", "text"],
                    "expected": "caption matches the visual subject",
                    "actual": "image shows dog while caption says cat",
                    "confidence": 0.76,
                }
            ]
        }
    )

    result = judge_multimodal_detection_output(expected, predicted, scoring_standard="cross-modal claims must agree.")

    assert result.score == 0
    assert result.reasons == ["multimodal:conflict:1 conflict_actual_mismatch"]
    assert result.affected_box_ids == []
    assert result.scoring_standard == "cross-modal claims must agree."
    assert result.deltas == [
        {
            "target_id": "multimodal:conflict:1",
            "expected": "image and caption both describe a cat",
            "actual": "image shows dog while caption says cat",
            "reason": "conflict_actual_mismatch",
            "metadata": {
                "field": "actual",
                "conflict_type": "visual_text_conflict",
                "modalities": ["image", "text"],
                "confidence": 0.76,
                "expected_conflict_type": "visual_text_conflict",
                "expected_modalities": ["image", "text"],
                "actual_conflict_type": "visual_text_conflict",
                "actual_modalities": ["image", "text"],
            },
        }
    ]
