import json

import pytest

from debug_agent.assistant.knowledge_base import KnowledgeChunk, ProjectKnowledgeBase
from debug_agent.lark.xiaod_orchestrator import XiaoDTurnRequest
from debug_agent.xiaod.brain import XiaoDSemanticBrain


@pytest.mark.asyncio
async def test_semantic_brain_maps_model_json_to_debug_intake_decision() -> None:
    async def model_answer(prompt: str) -> str:
        assert "只输出 JSON" in prompt
        return json.dumps(
            {
                "intent": "save_badcase_draft",
                "confidence": 0.91,
                "reason": "user_submitted_debug_case",
                "clean_text": "这张图识别错了",
                "fields": {
                    "input_source": "https://example.com/a.png",
                    "model_output": "3",
                    "expected_output": "8",
                    "issue_summary": "模型把 8 识别成 3",
                },
            },
            ensure_ascii=False,
        )

    brain = XiaoDSemanticBrain(_knowledge_base(), model_answer=model_answer)

    decision = await brain.decide(XiaoDTurnRequest(text="随便看看这个识别问题"))

    assert decision is not None
    assert decision.kind == "save_badcase_draft"
    assert decision.reason == "semantic_brain:user_submitted_debug_case"
    assert decision.extracted_fields == {
        "input_source": "https://example.com/a.png",
        "model_output": "3",
        "expected_output": "8",
        "issue_summary": "模型把 8 识别成 3",
    }


@pytest.mark.asyncio
async def test_semantic_brain_declines_low_confidence_result() -> None:
    async def model_answer(prompt: str) -> str:
        del prompt
        return '{"intent":"save_badcase_draft","confidence":0.2,"reason":"unclear"}'

    brain = XiaoDSemanticBrain(_knowledge_base(), model_answer=model_answer)

    decision = await brain.decide(XiaoDTurnRequest(text="这个可能有点怪"))

    assert decision is None


def _knowledge_base() -> ProjectKnowledgeBase:
    return ProjectKnowledgeBase(
        [
            KnowledgeChunk(
                chunk_id="workflow:1",
                title="小D badcase 提交流程",
                content="用户可以发原始输入、模型输出、正确答案、错误现象，小D创建草稿。",
                source="test",
            )
        ]
    )
