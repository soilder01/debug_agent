from pydantic import BaseModel

from debug_agent.cases.comparator import compare_answer_sets
from debug_agent.cases.models import AnswerSet


class JudgeResult(BaseModel):
    score: int
    reasons: list[str]


def judge_answer(expected: AnswerSet, predicted: AnswerSet) -> JudgeResult:
    diff = compare_answer_sets(expected, predicted)
    if not diff.has_differences:
        return JudgeResult(score=1, reasons=[])
    return JudgeResult(
        score=0,
        reasons=[f"box {delta.box_id} {delta.reason}" for delta in diff.deltas],
    )
