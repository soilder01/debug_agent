from __future__ import annotations

import re

from pydantic import BaseModel, Field

from debug_agent.assistant.knowledge_base import (
    DebugLesson,
    KnowledgeChunk,
    KnowledgeIndexStatus,
    ProjectKnowledgeBase,
)
from debug_agent.models.ark import ArkModelAdapter
from debug_agent.settings import ArkSettings


class AssistantCitation(BaseModel):
    title: str
    source: str
    snippet: str


class AssistantChatResult(BaseModel):
    answer: str
    citations: list[AssistantCitation]
    model_provider: str
    model_id: str


class ProjectAssistant:
    def __init__(self, knowledge_base: ProjectKnowledgeBase) -> None:
        self._knowledge_base = knowledge_base

    async def answer(self, question: str, *, model_id: str = "") -> AssistantChatResult:
        chunks = (
            self._knowledge_base.search(_retrieval_query(question), limit=5)
            if _should_use_knowledge(question)
            else []
        )
        citations = [_citation_from_chunk(chunk) for chunk in chunks]
        try:
            response = await _ark_answer(_build_prompt(question, chunks), model_id=model_id)
            answer = _model_answer_text(response)
            return AssistantChatResult(
                answer=answer,
                citations=citations,
                model_provider=response.model_provider,
                model_id=response.model_id,
            )
        except Exception as exc:
            model_error = _model_error_summary(exc)
            if not chunks:
                return AssistantChatResult(
                    answer=(
                        f"我现在没法调用配置的大模型（{model_error}），也没有从项目知识库检索到足够上下文。"
                        "你可以继续补充问题，或直接发飞书表格/Base/文档链接让我建立 badcase 草稿。"
                    ),
                    citations=[],
                    model_provider="local-rag",
                    model_id="retrieval-only",
                )
            return AssistantChatResult(
                answer=_fallback_answer(question, chunks, model_error=model_error),
                citations=citations,
                model_provider="local-rag",
                model_id="retrieval-only",
            )

    def knowledge_status(self) -> KnowledgeStatusResponse:
        return knowledge_status_response(self._knowledge_base.index_status())

    def search_knowledge(self, request: KnowledgeSearchRequest) -> KnowledgeSearchResponse:
        chunks = self._knowledge_base.search(request.query, limit=request.limit)
        return KnowledgeSearchResponse(
            query=request.query,
            chunks=[knowledge_chunk_response(chunk) for chunk in chunks],
            status=self.knowledge_status(),
        )

    def add_debug_lesson(self, request: DebugLessonRequest) -> DebugLessonResponse:
        return self.add_debug_lesson_object(debug_lesson_from_request(request))

    def add_debug_lesson_object(self, lesson: DebugLesson) -> DebugLessonResponse:
        chunk = self._knowledge_base.add_debug_lesson(lesson)
        return DebugLessonResponse(
            chunk=knowledge_chunk_response(chunk),
            status=self.knowledge_status(),
        )


class AssistantChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    model_id: str = Field(default="", max_length=160)


class AssistantChatResponse(AssistantChatResult):
    pass


class KnowledgeStatusResponse(BaseModel):
    document_count: int
    chunk_count: int
    debug_lesson_count: int
    embedding_provider: str
    database_url: str = ""


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=20)


class KnowledgeChunkResponse(BaseModel):
    chunk_id: str
    title: str
    content: str
    source: str
    source_type: str
    source_uri: str
    tags: list[str]
    metadata: dict[str, object]


class KnowledgeSearchResponse(BaseModel):
    query: str
    chunks: list[KnowledgeChunkResponse]
    status: KnowledgeStatusResponse


class DebugLessonRequest(BaseModel):
    lesson_id: str = Field(min_length=1, max_length=160)
    job_id: str = Field(default="", max_length=160)
    case_id: str = Field(default="", max_length=160)
    failure_summary: str = Field(min_length=1, max_length=2000)
    root_cause: str = Field(default="", max_length=240)
    confidence: str = Field(default="unknown", max_length=80)
    debug_loop_decision: str = Field(default="", max_length=160)
    evidence_boundary: str = Field(default="", max_length=2000)
    recommended_action: str = Field(default="", max_length=2000)
    source_uri: str = Field(default="", max_length=1000)
    approved: bool = False


class DebugLessonResponse(BaseModel):
    chunk: KnowledgeChunkResponse
    status: KnowledgeStatusResponse


def knowledge_status_response(status: KnowledgeIndexStatus) -> KnowledgeStatusResponse:
    return KnowledgeStatusResponse(
        document_count=status.document_count,
        chunk_count=status.chunk_count,
        debug_lesson_count=status.debug_lesson_count,
        embedding_provider=status.embedding_provider,
        database_url=status.database_url,
    )


def knowledge_chunk_response(chunk: KnowledgeChunk) -> KnowledgeChunkResponse:
    return KnowledgeChunkResponse(
        chunk_id=chunk.chunk_id,
        title=chunk.title,
        content=chunk.content,
        source=chunk.source,
        source_type=chunk.source_type,
        source_uri=chunk.source_uri,
        tags=list(chunk.tags),
        metadata=chunk.metadata,
    )


def debug_lesson_from_request(request: DebugLessonRequest) -> DebugLesson:
    return DebugLesson(
        lesson_id=request.lesson_id,
        job_id=request.job_id,
        case_id=request.case_id,
        failure_summary=request.failure_summary,
        root_cause=request.root_cause,
        confidence=request.confidence,
        debug_loop_decision=request.debug_loop_decision,
        evidence_boundary=request.evidence_boundary,
        recommended_action=request.recommended_action,
        source_uri=request.source_uri,
        approved=request.approved,
    )


def _build_prompt(question: str, chunks: list[KnowledgeChunk]) -> str:
    context = _knowledge_context(chunks)
    if context:
        context = f"\n\n可参考的项目知识：\n{context}"
    return (
        f"{_xiaod_product_context()}"
        f"{context}\n\n"
        "回答策略：\n"
        "1. 优先像一个企业服务 Bot 一样直接回答用户，不要只复述资料。\n"
        "2. 用户问身份、能力、怎么用时，说明小D能做什么、当前边界和下一步可怎么发。\n"
        "3. 用户给飞书表格/Base/文档/附件链接时，引导进入 badcase 草稿和确认流程。\n"
        "4. 用户要求执行外部写操作时，必须说明需要确认门禁，不能声称已执行。\n"
        "5. 如果信息不足，要追问具体缺口，不要输出空泛套话。\n"
        "6. 输出保持专业、简洁、可执行；不要使用 emoji、颜文字、口癖或卖萌语气。\n\n"
        f"用户消息：{question}\n\n"
        "小D回复："
    )


def _knowledge_context(chunks: list[KnowledgeChunk]) -> str:
    return "\n\n".join(
        f"[{index}] {chunk.title}\n来源：{chunk.source}\n{chunk.content}"
        for index, chunk in enumerate(chunks, start=1)
    )


def _xiaod_product_context() -> str:
    return (
        "你是小D，Debug Agent 整个产品的企业飞书入口，不是重新实现的一套机器人后端，"
        "也不是命令行外壳。\n"
        "你的核心职责是把用户在飞书里的自然语言、链接和附件接到 Debug Agent 已有前后端能力上：\n"
        "- Case/数据接入：支持 JSONL、CSV、飞书表格行、Base/文档/Wiki/云盘/妙记/幻灯片、图片、视频和附件进入统一 DebugCase 协议。\n"
        "- 调试执行：支持单样本 DebugJob、批量 DebugBatch、worker 队列、暂停/恢复/取消、任务状态和失败重试。\n"
        "- Agent 编排：支持 case_intake、experiment_planner、model_runner、judge_comparator、evidence_artifact、report_root_cause、writeback_operator 等角色和模型路由。\n"
        "- 证据和报告：支持 run stages、evidence ledger、artifact 文件、根因报告、推荐动作、追问实验、自动闭环报告。\n"
        "- 表格/Base 闭环：支持飞书表格同步、富文本附件 media 下载、表格重跑、写回确认、写回审计、Base 记录写回。\n"
        "- 运维观测：支持 readiness、pilot gate、performance、Lark 权限清单、预检、go-live gate、操作审计、support bundle、数据库备份和产物保留。\n"
        "你的路由原则：\n"
        "- 先判断用户是在提交新 badcase、补充当前草稿、查询已有任务/报告/批次、操作表格/Base、查看模型/Agent 配置，还是做运维排查。\n"
        "- 能映射到已有 Debug Agent API、前端页面或报告链接时，明确告诉用户正在使用哪个既有能力，不要表现得像另做一套流程。\n"
        "- 信息不全时追问具体缺口；信息齐全后发确认卡片或确认页；确认前不创建 DebugJob。\n"
        "- 表格/Base 写回、任务创建、批量调试、清理产物等写操作必须二次确认，不能声称已执行。\n"
        "- 普通问答可以使用大模型直接回答，但不能假装已经执行尚未接入的外部动作。\n"
        "- 回复语气保持企业服务场景下的专业克制，不使用 emoji 或口语化后缀。"
    )


async def _ark_answer(prompt: str, *, model_id: str = ""):
    ark_settings = ArkSettings.from_env()
    adapter = ArkModelAdapter(
        settings=ark_settings,
        model_id=model_id.strip() or ark_settings.chat_model_id,
    )
    return await adapter.generate(prompt=prompt, image_uri="")


def _retrieval_query(question: str) -> str:
    if _is_identity_or_capability_question(question):
        return (
            "Debug Agent 完整产品能力 后端 API 前端页面 调试任务 报告 证据 批量调试 "
            "表格同步 写回 Base Lark 小D Agent 模型路由 worker 观测 运维 权限"
        )
    return question


def _fallback_answer(question: str, chunks: list[KnowledgeChunk], *, model_error: str = "") -> str:
    if _is_identity_or_capability_question(question):
        error_text = f"我尝试调用已配置的大模型失败：{model_error}。" if model_error else ""
        return (
            f"我是小D，Debug Agent 整个产品的飞书入口。{error_text}"
            "现在只能基于项目知识库做降级回答，但我连接的不是单独的 bot 壳。"
            "我应该把飞书里的自然语言、表格/Base/文档/附件接到已有后端能力上："
            "导入 Case、创建单样本或批量 DebugJob、查询任务/批次/worker、查看证据和报告、"
            "触发表格重跑、走表格或 Base 写回确认、查看模型路由和 Lark 权限/审计/上线门禁。"
        )
    lines = ["我先根据当前项目知识库回答："]
    bullet_count = 0
    for chunk in chunks[:3]:
        first_sentence = _best_chunk_sentence(chunk.content, question)
        if first_sentence:
            lines.append(f"- {chunk.title}：{first_sentence}。")
            bullet_count += 1
    if bullet_count == 0:
        return (
            "我没有从当前项目知识库里组织出可靠答案。请换成更具体的问题，"
            "例如“怎么提交 badcase”“表格链接怎么调试”“任务完成后报告在哪里看”。"
        )
    lines.append("需要更深入的解释时，可以继续追问具体页面、按钮、状态或流程。")
    return "\n".join(lines)


def _is_identity_or_capability_question(question: str) -> bool:
    normalized = question.strip().lower().rstrip(" ?？。!！")
    return any(
        term in normalized
        for term in (
            "你是谁",
            "你是",
            "你会什么",
            "你能干什么",
            "你能做什么",
            "你是什么",
            "小d是谁",
            "小d会什么",
            "who are you",
            "what can you do",
        )
    )


def _should_use_knowledge(question: str) -> bool:
    if _is_identity_or_capability_question(question):
        return True
    normalized = question.strip().lower()
    domain_terms = (
        "小d",
        "debug",
        "badcase",
        "报告",
        "证据",
        "表格",
        "飞书",
        "写回",
        "同步",
        "任务",
        "批次",
        "worker",
        "agent",
        "rag",
        "知识库",
        "调查工作台",
        "数据导入",
        "怎么用",
        "使用手册",
        "根因",
        "probe",
        "baseline",
        "验收",
        "交付",
    )
    return any(term in normalized for term in domain_terms)


def _model_answer_text(response: object) -> str:
    raw_output = getattr(response, "raw_output", "")
    answer = _safe_answer_text(str(raw_output))
    if not answer:
        raise ValueError("model returned an empty answer")
    return answer


def _model_error_summary(exc: Exception) -> str:
    message = str(exc).strip()
    if "InvalidEndpoint.ClosedEndpoint" in message:
        return "Ark endpoint 已关闭或临时不可用（InvalidEndpoint.ClosedEndpoint）"
    if "AccessDenied" in message:
        return "当前 ARK_API_KEY 对配置的 Ark endpoint/model 没有访问权限（AccessDenied）"
    if "ARK_API_KEY is required" in message:
        return "缺少 ARK_API_KEY"
    return message[:240] or type(exc).__name__


def _first_non_empty_sentence(content: str) -> str:
    normalized = _safe_answer_text(content)
    if not normalized:
        return ""
    for separator in ("。", "；", ";", "\n"):
        if separator in normalized:
            normalized = normalized.split(separator, 1)[0].strip()
            break
    return normalized


def _best_chunk_sentence(content: str, question: str) -> str:
    normalized = _safe_answer_text(content)
    if not normalized:
        return ""
    query_terms = [
        term
        for term in re.findall(r"[\u4e00-\u9fff]{2,}|[a-z0-9_:-]{2,}", question.lower())
        if term
    ]
    sentences = [
        sentence.strip()
        for sentence in re.split(r"[。；;\n]", normalized)
        if sentence.strip()
    ]
    for sentence in sentences:
        if any(term in sentence.lower() for term in query_terms):
            return sentence
    return _first_non_empty_sentence(content)


def _safe_answer_text(value: str) -> str:
    cleaned = "".join(_safe_answer_char(char) for char in value)
    normalized = " ".join(cleaned.strip().split())
    return re.sub(r"\s+([，。！？；：、,.!?;:])", r"\1", normalized)


def _safe_answer_char(char: str) -> str:
    code = ord(char)
    if code < 32 or 0x7F <= code <= 0x9F:
        return " "
    if _is_emoji_or_presentation_codepoint(code):
        return ""
    return char


def _is_emoji_or_presentation_codepoint(code: int) -> bool:
    return (
        0x1F000 <= code <= 0x1FAFF or 0x2600 <= code <= 0x27BF or code in {0x200D, 0xFE0E, 0xFE0F}
    )


def _citation_from_chunk(chunk: KnowledgeChunk) -> AssistantCitation:
    snippet = _safe_answer_text(chunk.content)
    if len(snippet) > 180:
        snippet = f"{snippet[:177]}..."
    return AssistantCitation(title=chunk.title, source=chunk.source, snippet=snippet)
