from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter

from debug_agent.lark.xiaod_orchestrator import XiaoDConversationContext
from debug_agent.xiaod.schemas import (
    XiaoDTurnDecisionResponse,
    XiaoDTurnHandleRequest,
    XiaoDTurnHandleResponse,
    XiaoDTurnHandler,
    XiaoDTurnPreviewRequest,
)
from debug_agent.xiaod.service import handle_turn as handle_xiaod_turn_core
from debug_agent.xiaod.service import preview_turn
from debug_agent.xiaod.service import XiaoDSemanticTurnDecider


def build_xiaod_turn_router(
    handle_turn: XiaoDTurnHandler,
    *,
    resolve_context: Callable[[XiaoDTurnHandleRequest], XiaoDConversationContext] | None = None,
    semantic_decider: XiaoDSemanticTurnDecider | None = None,
) -> APIRouter:
    router = APIRouter()

    @router.post("/lark/bot/xiaod/turns/preview")
    @router.post("/api/lark/bot/xiaod/turns/preview")
    def preview_xiaod_turn(request: XiaoDTurnPreviewRequest) -> XiaoDTurnDecisionResponse:
        return preview_turn(request)

    @router.post("/lark/bot/xiaod/turns/handle")
    @router.post("/api/lark/bot/xiaod/turns/handle")
    async def handle_xiaod_turn(request: XiaoDTurnHandleRequest) -> XiaoDTurnHandleResponse:
        context = resolve_context(request) if resolve_context is not None else None
        return await handle_xiaod_turn_core(
            request,
            handler=handle_turn,
            context=context,
            semantic_decider=semantic_decider,
        )

    return router
