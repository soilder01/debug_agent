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
