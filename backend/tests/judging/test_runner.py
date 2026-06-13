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
