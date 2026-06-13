import json
from pathlib import Path

from debug_agent.cases.models import (
    DebugCase,
    DetectionCase,
    DetectionOutput,
    DetectionPrediction,
    DetectionRegion,
)


def test_debug_case_parses_fixture() -> None:
    fixture_path = Path(__file__).parents[1] / "fixtures" / "handwrite233.json"
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))

    case = DebugCase.model_validate(raw)

    assert case.case_id == "handwrite233"
    assert case.task_type == "handwriting_ocr"
    assert case.golden_answer.answers[0].box_id == 1
    assert case.predictions[0].trial == 0
    assert case.avg_score == 0.0


def test_debug_case_parses_optional_box_regions() -> None:
    case = DebugCase.model_validate(
        {
            "case_id": "case-with-regions",
            "image_uri": "file:///tmp/case.png",
            "prompt": "识别作答区域。",
            "golden_answer": {"answers": [{"box_id": 7, "student_answer": "低昷烘干"}]},
            "scoring_standard": "box_id and student_answer must match.",
            "predictions": [
                {
                    "trial": 0,
                    "raw_output": "{\"answers\":[{\"box_id\":7,\"student_answer\":\"低温烘干\"}]}",
                    "score": 0,
                }
            ],
            "avg_score": 0.0,
            "box_regions": [
                {
                    "box_id": 7,
                    "x": 12,
                    "y": 34,
                    "width": 56,
                    "height": 78,
                    "unit": "pixel",
                    "label": "box-7",
                }
            ],
        }
    )

    assert case.box_regions[0].box_id == 7
    assert case.box_regions[0].x == 12
    assert case.box_regions[0].label == "box-7"


def test_detection_case_aliases_preserve_handwriting_ocr_compatibility() -> None:
    case = DetectionCase.model_validate(
        {
            "case_id": "generic-alias-ocr",
            "image_uri": "file:///tmp/case.png",
            "prompt": "Return JSON with answers.",
            "golden_answer": {"answers": [{"box_id": 1, "student_answer": "42"}]},
            "scoring_standard": "box_id and student_answer must match.",
            "predictions": [{"trial": 0, "raw_output": "{\"answers\":[{\"box_id\":1,\"student_answer\":\"24\"}]}", "score": 0}],
            "avg_score": 0.0,
            "box_regions": [{"box_id": 1, "x": 1, "y": 2, "width": 3, "height": 4}],
        }
    )

    assert isinstance(case.golden_answer, DetectionOutput)
    assert isinstance(case.predictions[0], DetectionPrediction)
    assert isinstance(case.box_regions[0], DetectionRegion)
    assert case.task_type == "handwriting_ocr"


def test_detection_case_accepts_non_ocr_task_type_for_future_recipes() -> None:
    case = DetectionCase.model_validate(
        {
            "case_id": "classification-case",
            "task_type": "classification",
            "image_uri": "",
            "prompt": "Classify the text sentiment and return JSON.",
            "golden_answer": {"answers": [{"box_id": 1, "student_answer": "positive"}]},
            "scoring_standard": "label must match exactly.",
            "predictions": [{"trial": 0, "raw_output": "{\"answers\":[{\"box_id\":1,\"student_answer\":\"negative\"}]}", "score": 0}],
            "avg_score": 0.0,
        }
    )

    assert case.task_type == "classification"
    assert case.case_id == "classification-case"
