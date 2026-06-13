from pydantic import BaseModel, Field

from debug_agent.cases.comparator import compare_answer_sets
from debug_agent.cases.models import AnswerSet


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
        deltas=[delta.model_dump() for delta in diff.deltas],
    )
