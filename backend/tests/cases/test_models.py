import json
from pathlib import Path

from debug_agent.cases.models import DebugCase


def test_debug_case_parses_fixture() -> None:
    fixture_path = Path(__file__).parents[1] / "fixtures" / "handwrite233.json"
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))

    case = DebugCase.model_validate(raw)

    assert case.case_id == "handwrite233"
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
