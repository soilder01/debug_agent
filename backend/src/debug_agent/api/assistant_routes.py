from __future__ import annotations

from fastapi import APIRouter

from debug_agent.assistant.chat import (
    AssistantChatRequest,
    AssistantChatResponse,
    DebugLessonRequest,
    DebugLessonResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeStatusResponse,
    ProjectAssistant,
)


def build_assistant_router(project_assistant: ProjectAssistant) -> APIRouter:
    router = APIRouter()

    @router.post("/assistant/chat")
    @router.post("/api/assistant/chat")
    async def chat_with_project_assistant(
        request: AssistantChatRequest,
    ) -> AssistantChatResponse:
        result = await project_assistant.answer(request.question, model_id=request.model_id)
        return AssistantChatResponse.model_validate(result.model_dump())

    @router.get("/assistant/knowledge/status")
    @router.get("/api/assistant/knowledge/status")
    def get_knowledge_status() -> KnowledgeStatusResponse:
        return project_assistant.knowledge_status()

    @router.post("/assistant/knowledge/search")
    @router.post("/api/assistant/knowledge/search")
    def search_knowledge(request: KnowledgeSearchRequest) -> KnowledgeSearchResponse:
        return project_assistant.search_knowledge(request)

    @router.post("/assistant/knowledge/debug-lessons")
    @router.post("/api/assistant/knowledge/debug-lessons")
    def add_debug_lesson(request: DebugLessonRequest) -> DebugLessonResponse:
        return project_assistant.add_debug_lesson(request)

    return router
