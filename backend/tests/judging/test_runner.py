from debug_agent.cases.models import AnswerSet
from debug_agent.judging.runner import judge_answer


def test_judge_answer_passes_exact_match() -> None:
    expected = AnswerSet.model_validate({"answers": [{"box_id": 1, "student_answer": "A"}]})
    predicted = AnswerSet.model_validate({"answers": [{"box_id": 1, "student_answer": "A"}]})

    result = judge_answer(expected, predicted)

    assert result.score == 1
    assert result.reasons == []


def test_judge_answer_explains_mismatch() -> None:
    expected = AnswerSet.model_validate({"answers": [{"box_id": 1, "student_answer": "低昷烘干"}]})
    predicted = AnswerSet.model_validate({"answers": [{"box_id": 1, "student_answer": "低温烘干"}]})

    result = judge_answer(expected, predicted)

    assert result.score == 0
    assert result.reasons == ["box 1 student_answer_mismatch"]
