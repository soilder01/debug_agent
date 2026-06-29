from __future__ import annotations

from collections.abc import Awaitable, Callable

from debug_agent.lark.xiaod_orchestrator import (
    XiaoDConversationContext,
    XiaoDTurnDecision,
    XiaoDTurnRequest,
    decide_xiaod_turn,
)
from debug_agent.xiaod.schemas import (
    XiaoDTurnDecisionResponse,
    XiaoDTurnHandleRequest,
    XiaoDTurnHandleResponse,
    XiaoDTurnHandler,
    XiaoDTurnPreviewRequest,
)


XiaoDSemanticTurnDecider = Callable[
    [XiaoDTurnPreviewRequest, XiaoDConversationContext | None],
    Awaitable[XiaoDTurnDecision | None],
]

PREEMPTIVE_DETERMINISTIC_KINDS = {
    "backend_command",
    "continue_pending_command",
    "decline_pending_command",
    "retain_pending_command",
    "delete_pending_command",
    "sync_writeback_decision",
    "skip_writeback_decision",
}


def decide_turn(
    request: XiaoDTurnPreviewRequest,
    *,
    context: XiaoDConversationContext | None = None,
) -> XiaoDTurnDecision:
    return decide_xiaod_turn(
        XiaoDTurnRequest(
            text=request.text,
            has_attachments=request.has_attachments,
        ),
        context=context,
    )


def decision_response(decision: XiaoDTurnDecision) -> XiaoDTurnDecisionResponse:
    return XiaoDTurnDecisionResponse(
        kind=decision.kind,
        clean_text=decision.clean_text,
        backend_command=decision.backend_command,
        assistant_question=decision.assistant_question,
        assistant_model_id=decision.assistant_model_id,
        reason=decision.reason,
        extracted_fields=decision.extracted_fields,
    )


def preview_turn(request: XiaoDTurnPreviewRequest) -> XiaoDTurnDecisionResponse:
    return decision_response(decide_turn(request))


async def handle_turn(
    request: XiaoDTurnHandleRequest,
    *,
    handler: XiaoDTurnHandler,
    context: XiaoDConversationContext | None = None,
    semantic_decider: XiaoDSemanticTurnDecider | None = None,
) -> XiaoDTurnHandleResponse:
    deterministic_decision = decide_turn(request, context=context)
    decision: XiaoDTurnDecision | None = (
        deterministic_decision
        if deterministic_decision.kind in PREEMPTIVE_DETERMINISTIC_KINDS
        else None
    )
    if semantic_decider is not None:
        decision = decision or await semantic_decider(request, context)
    if decision is None:
        decision = deterministic_decision
    response = decision_response(decision)
    return await handler(request, decision, response)
