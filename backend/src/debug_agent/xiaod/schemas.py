from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Literal

from pydantic import BaseModel, Field

from debug_agent.lark.bot import LarkBotReplyPayload
from debug_agent.lark.xiaod_orchestrator import XiaoDTurnDecision, XiaoDTurnKind


class XiaoDTurnPreviewRequest(BaseModel):
    text: str = Field(default="", max_length=10_000)
    has_attachments: bool = False


class XiaoDTurnHandleRequest(XiaoDTurnPreviewRequest):
    actor: str = ""
    open_id: str = ""
    chat_id: str = ""
    message_id: str = ""
    tenant_key: str = ""
    identity: Literal["bot", "user", "unknown"] = "bot"
    profile: str = ""
    attachments: list[dict[str, object]] = Field(default_factory=list)
    resolve_link_content: bool = True


class XiaoDTurnDecisionResponse(BaseModel):
    kind: XiaoDTurnKind
    clean_text: str
    backend_command: str = ""
    assistant_question: str = ""
    assistant_model_id: str = ""
    reason: str = ""
    extracted_fields: dict[str, str] = Field(default_factory=dict)


class XiaoDTurnHandleResponse(BaseModel):
    decision: XiaoDTurnDecisionResponse
    handled: bool
    reply: LarkBotReplyPayload | None = None


XiaoDTurnHandler = Callable[
    [XiaoDTurnHandleRequest, XiaoDTurnDecision, XiaoDTurnDecisionResponse],
    Awaitable[XiaoDTurnHandleResponse],
]
