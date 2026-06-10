import json

from debug_agent.cases.comparator import compare_answer_sets, parse_prediction_answer
from debug_agent.cases.models import AnswerSet


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
    assert json.loads(diff.model_dump_json())["affected_box_ids"] == [1]
