import json

from debug_agent.cases.comparator import (
    compare_answer_sets,
    compare_classification_outputs,
    compare_image_detection_outputs,
    parse_classification_output,
    parse_image_detection_output,
    parse_prediction_answer,
)
from debug_agent.cases.models import AnswerSet, ClassificationOutput, ImageDetectionOutput


def test_parse_prediction_answer_reads_valid_json() -> None:
    raw = '{"answers":[{"box_id":1,"student_answer":"A"}]}'

    parsed = parse_prediction_answer(raw)

    assert parsed.answers[0].box_id == 1
    assert parsed.answers[0].student_answer == "A"


def test_compare_answer_sets_detects_text_delta() -> None:
    expected = AnswerSet.model_validate(
        {"answers": [{"box_id": 1, "student_answer": "低昷烘干"}]}
    )
    predicted = AnswerSet.model_validate(
        {"answers": [{"box_id": 1, "student_answer": "低温烘干"}]}
    )

    diff = compare_answer_sets(expected, predicted)

    assert diff.has_differences is True
    assert diff.affected_box_ids == [1]
    assert diff.deltas[0].reason == "student_answer_mismatch"
    assert diff.detection_deltas[0].target_id == "box:1"
    assert diff.detection_deltas[0].expected == "低昷烘干"
    assert diff.detection_deltas[0].actual == "低温烘干"
    assert diff.detection_deltas[0].reason == "student_answer_mismatch"
    assert diff.detection_deltas[0].metadata == {
        "box_id": 1,
        "field": "student_answer",
        "legacy_reason": "student_answer_mismatch",
    }
    assert json.loads(diff.model_dump_json())["affected_box_ids"] == [1]
    assert json.loads(diff.model_dump_json())["detection_deltas"][0]["target_id"] == "box:1"


def test_parse_classification_output_reads_task_native_json() -> None:
    parsed = parse_classification_output('{"label":"positive","confidence":0.92}')

    assert parsed.label == "positive"
    assert parsed.confidence == 0.92


def test_compare_classification_outputs_detects_label_delta() -> None:
    expected = ClassificationOutput(label="positive")
    predicted = ClassificationOutput(label="negative", confidence=0.61)

    diff = compare_classification_outputs(expected, predicted)

    assert diff.has_differences is True
    assert diff.detection_deltas == [
        {
            "target_id": "label:classification",
            "expected": "positive",
            "actual": "negative",
            "reason": "label_mismatch",
            "metadata": {"field": "label", "confidence": 0.61},
        }
    ]


def test_parse_image_detection_output_reads_region_targets() -> None:
    parsed = parse_image_detection_output(
        """
        {
          "regions": [
            {
              "target_id": "image:region:1",
              "x": 10,
              "y": 20,
              "width": 30,
              "height": 40,
              "unit": "pixel",
              "label": "cat",
              "confidence": 0.88
            }
          ]
        }
        """
    )

    assert parsed.regions[0].target_id == "image:region:1"
    assert parsed.regions[0].label == "cat"
    assert parsed.regions[0].confidence == 0.88


def test_compare_image_detection_outputs_detects_region_label_delta() -> None:
    expected = ImageDetectionOutput.model_validate(
        {
            "regions": [
                {
                    "target_id": "image:region:1",
                    "x": 10,
                    "y": 20,
                    "width": 30,
                    "height": 40,
                    "label": "cat",
                }
            ]
        }
    )
    predicted = ImageDetectionOutput.model_validate(
        {
            "regions": [
                {
                    "target_id": "image:region:1",
                    "x": 10,
                    "y": 20,
                    "width": 30,
                    "height": 40,
                    "label": "dog",
                    "confidence": 0.57,
                }
            ]
        }
    )

    diff = compare_image_detection_outputs(expected, predicted)

    assert diff.has_differences is True
    assert diff.detection_deltas == [
        {
            "target_id": "image:region:1",
            "expected": "cat",
            "actual": "dog",
            "reason": "region_label_mismatch",
            "metadata": {"field": "label", "confidence": 0.57},
        }
    ]


def test_compare_image_detection_outputs_detects_missing_region_without_ocr_fields() -> None:
    expected = ImageDetectionOutput.model_validate(
        {
            "regions": [
                {
                    "target_id": "image:region:2",
                    "x": 50,
                    "y": 60,
                    "width": 70,
                    "height": 80,
                    "label": "traffic light",
                }
            ]
        }
    )
    predicted = ImageDetectionOutput(regions=[])

    diff = compare_image_detection_outputs(expected, predicted)

    assert diff.has_differences is True
    assert diff.detection_deltas == [
        {
            "target_id": "image:region:2",
            "expected": "traffic light",
            "actual": None,
            "reason": "missing_region",
            "metadata": {"field": "regions"},
        }
    ]
