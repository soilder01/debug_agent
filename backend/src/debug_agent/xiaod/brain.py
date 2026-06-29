from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, get_args

from pydantic import BaseModel, Field

from debug_agent.assistant.chat import _knowledge_context, _xiaod_product_context
from debug_agent.assistant.knowledge_base import KnowledgeChunk, ProjectKnowledgeBase
from debug_agent.lark.xiaod_orchestrator import (
    XiaoDConversationContext,
    XiaoDTurnDecision,
    XiaoDTurnKind,
    XiaoDTurnRequest,
    strip_bot_mention_prefix,
)
from debug_agent.models.ark import ArkModelAdapter
from debug_agent.settings import ArkSettings


BrainAnswer = Callable[[str], Awaitable[str]]

ALLOWED_INTENTS = set(get_args(XiaoDTurnKind))
FIELD_KEYS = (
    "input_source",
    "model_output",
    "expected_output",
    "issue_summary",
    "task_type",
    "scoring_standard",
)


class XiaoDSemanticResult(BaseModel):
    intent: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str = ""
    clean_text: str = ""
    backend_command: str = ""
    assistant_question: str = ""
    assistant_model_id: str = ""
    fields: dict[str, str] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)


@dataclass
class XiaoDSemanticBrain:
    knowledge_base: ProjectKnowledgeBase
    model_answer: BrainAnswer | None = None
    confidence_threshold: float = 0.55

    async def decide(
        self,
        request: XiaoDTurnRequest,
        *,
        context: XiaoDConversationContext | None = None,
    ) -> XiaoDTurnDecision | None:
        prompt = build_semantic_prompt(
            request=request,
            context=context,
            chunks=self.knowledge_base.search(_semantic_query(request.text), limit=5),
        )
        try:
            raw_answer = await self._answer(prompt)
            semantic = parse_semantic_result(raw_answer)
        except Exception:
            return None
        return semantic_result_to_decision(
            semantic,
            request=request,
            context=context,
            confidence_threshold=self.confidence_threshold,
        )

    async def _answer(self, prompt: str) -> str:
        if self.model_answer is not None:
            return await self.model_answer(prompt)
        settings = ArkSettings.from_env()
        adapter = ArkModelAdapter(
            settings=settings,
            model_id=settings.chat_model_id,
            temperature=0.0,
            max_tokens=1200,
        )
        response = await adapter.generate(prompt=prompt, image_uri="")
        return response.raw_output


def build_semantic_prompt(
    *,
    request: XiaoDTurnRequest,
    context: XiaoDConversationContext | None,
    chunks: list[KnowledgeChunk],
) -> str:
    context_lines = semantic_context_lines(context)
    knowledge_context = _knowledge_context(chunks)
    return "\n".join(
        [
            _xiaod_product_context(),
            "",
            "你现在是小D的语义理解层，不直接执行动作，只输出严格 JSON。",
            "目标：判断用户意图、抽取 badcase 字段、给后端一个可校验的下一步。",
            "",
            "允许的 intent：",
            ", ".join(sorted(ALLOWED_INTENTS)),
            "",
            "字段说明：",
            "- input_source：图片、视频、文档、表格、Base、文件链接，或用户描述的输入来源。",
            "- model_output：模型实际输出。",
            "- expected_output：正确答案或期望输出。",
            "- issue_summary：错误现象，保持简短、可读。",
            "- task_type/scoring_standard：有明确说明时再填写。",
            "",
            "安全规则：",
            "- 写操作只识别意图，不要声称已经执行。",
            "- backend_command 只能输出 /debug 开头的命令。",
            "- 不确定时 intent 用 clarify_intent 或 assistant_chat，confidence 降低。",
            "- 用户问怎么提交 badcase 或需要哪些信息时，用 badcase_intake_guidance。",
            "- 用户提供调试样本、模型输出、正确答案、错误现象或链接时，用 save_badcase_draft，并尽量抽 fields。",
            "- input_source 未提供时必须留空并在 missing_fields 写 input_source，不要编造“暂未提供链接/附件”这类占位值。",
            "- 用户问进度/报告/结论/写回时，结合上下文选择 query_current_progress、backend_command 或 clarify_intent。",
            "",
            "当前会话上下文：",
            *context_lines,
            "",
            "可参考的项目知识：",
            knowledge_context or "无",
            "",
            f"用户消息：{request.text}",
            f"是否有附件：{request.has_attachments}",
            "",
            "只输出 JSON，不要 Markdown，不要解释。JSON schema：",
            json.dumps(
                {
                    "intent": "save_badcase_draft",
                    "confidence": 0.0,
                    "reason": "short_reason",
                    "clean_text": "去掉 @ 小D 后的用户原文",
                    "backend_command": "",
                    "assistant_question": "",
                    "assistant_model_id": "",
                    "fields": {
                        "input_source": "",
                        "model_output": "",
                        "expected_output": "",
                        "issue_summary": "",
                        "task_type": "",
                        "scoring_standard": "",
                    },
                    "missing_fields": [],
                },
                ensure_ascii=False,
            ),
        ]
    )


def semantic_context_lines(context: XiaoDConversationContext | None) -> list[str]:
    if context is None:
        return ["- 无上下文"]
    return [
        f"- has_open_draft={context.has_open_draft}",
        f"- has_ready_draft={context.has_ready_draft}",
        f"- latest_open_draft_status={context.latest_open_draft_status or 'none'}",
        f"- latest_submitted_job_id={context.latest_submitted_job_id or 'none'}",
        f"- latest_submitted_job_status={context.latest_submitted_job_status or 'none'}",
        f"- latest_report_url={'present' if context.latest_report_url else 'none'}",
        f"- has_pending_command={context.has_pending_command}",
        f"- has_pending_writeback_decision={context.has_pending_writeback_decision}",
    ]


def parse_semantic_result(raw_answer: str) -> XiaoDSemanticResult:
    data = _first_json_object(raw_answer)
    return XiaoDSemanticResult.model_validate(data)


def semantic_result_to_decision(
    semantic: XiaoDSemanticResult,
    *,
    request: XiaoDTurnRequest,
    context: XiaoDConversationContext | None,
    confidence_threshold: float,
) -> XiaoDTurnDecision | None:
    if semantic.confidence < confidence_threshold:
        return None
    intent = semantic.intent.strip()
    if intent not in ALLOWED_INTENTS:
        return None
    clean_text = semantic.clean_text.strip() or strip_bot_mention_prefix(request.text)
    backend_command = semantic.backend_command.strip()
    if intent == "backend_command":
        if not backend_command.startswith("/debug"):
            return None
    else:
        backend_command = ""
    del context
    return XiaoDTurnDecision(
        kind=intent,  # type: ignore[arg-type]
        clean_text=clean_text,
        backend_command=backend_command,
        assistant_question=semantic.assistant_question.strip(),
        assistant_model_id=semantic.assistant_model_id.strip(),
        reason=f"semantic_brain:{semantic.reason.strip() or intent}",
        extracted_fields=_clean_fields(semantic.fields),
    )


def _clean_fields(fields: dict[str, str]) -> dict[str, str]:
    cleaned: dict[str, str] = {}
    for key in FIELD_KEYS:
        value = str(fields.get(key, "")).strip()
        if value:
            cleaned[key] = value
    return cleaned


def _first_json_object(raw_answer: str) -> dict[str, Any]:
    text = raw_answer.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    decoder = json.JSONDecoder()
    start = text.find("{")
    while start >= 0:
        try:
            value, _ = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            start = text.find("{", start + 1)
            continue
        if isinstance(value, dict):
            return value
        start = text.find("{", start + 1)
    raise ValueError("semantic brain did not return a JSON object")


def _semantic_query(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return "小D Debug Agent 用户意图识别 badcase 提交流程"
    return f"{stripped}\n小D Debug Agent 用户意图识别 badcase 提交流程 任务状态 报告 写回"
