from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from fastapi import APIRouter, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from debug_agent.lark.connector import LarkConnectorStatus
from debug_agent.storage.repository import LarkBotSetupAcknowledgement


class LarkBotPreflightCheck(BaseModel):
    key: str
    label: str
    status: Literal["passed", "warning", "failed"]
    detail: str
    action: str


class LarkBotSetupChecklistItem(BaseModel):
    key: str
    title: str
    owner: Literal["debug_agent_operator", "lark_app_admin", "workspace_admin", "security_admin"]
    required: bool
    status: Literal["done", "needs_action", "manual_check"]
    detail: str
    action: str
    evidence: str
    acknowledgement: LarkBotSetupAcknowledgement | None = None


class LarkBotSetupAcknowledgementRequest(BaseModel):
    actor: str = ""
    evidence: str = Field(default="", max_length=2_000)
    note: str = Field(default="", max_length=2_000)


class LarkBotSetupAcknowledgementListResponse(BaseModel):
    acknowledgements: list[LarkBotSetupAcknowledgement]


class LarkBotPermissionRequirement(BaseModel):
    key: str
    title: str
    category: str
    permission_type: Literal["event_subscription", "oauth_scope"]
    scope: str
    phase: Literal["required_now", "recommended_next"]
    risk_level: Literal["event", "read", "write"]
    operation: str
    required_for: str
    repair_hint: str
    status: Literal["manual_check", "needs_action"]
    recent_missing: bool
    blocking: bool
    console_url: str


class LarkBotPermissionChecklistResponse(BaseModel):
    generated_at: str
    status: Literal["passed", "warning", "failed"]
    event_mode: Literal["webhook", "long_connection"]
    required_scopes: list[str]
    recommended_scopes: list[str]
    recent_missing_scopes: list[str]
    blocking_scopes: list[str]
    requirements: list[LarkBotPermissionRequirement]
    admin_handoff_markdown: str
    console_url: str


class LarkBotPreflightResponse(BaseModel):
    generated_at: str
    status: Literal["passed", "warning", "failed"]
    connector: LarkConnectorStatus
    event_mode: Literal["webhook", "long_connection"]
    event_endpoint_url: str
    setup_package_url: str
    required_bot_scopes: list[str]
    pending_command_count: int
    failed_command_count: int
    recent_missing_scopes: list[str]
    operator_required_items: list[LarkBotSetupChecklistItem]
    checks: list[LarkBotPreflightCheck]


class LarkBotGoLiveGateCheck(BaseModel):
    key: str
    label: str
    status: Literal["passed", "warning", "failed"]
    detail: str
    action: str


class LarkBotGoLiveGateResponse(BaseModel):
    generated_at: str
    status: Literal["passed", "warning", "failed"]
    allowed: bool
    decision: str
    preflight: LarkBotPreflightResponse
    checks: list[LarkBotGoLiveGateCheck]
    export_urls: dict[str, str]


def build_lark_bot_setup_router(
    *,
    permission_checklist: Callable[[], LarkBotPermissionChecklistResponse],
    preflight: Callable[[], LarkBotPreflightResponse],
    go_live_gate: Callable[[], LarkBotGoLiveGateResponse],
    setup_acknowledgements: Callable[
        [str | None, int, int], LarkBotSetupAcknowledgementListResponse
    ],
    acknowledge_setup_item: Callable[
        [str, LarkBotSetupAcknowledgementRequest], LarkBotSetupAcknowledgement
    ],
    setup_package: Callable[[], Response],
) -> APIRouter:
    router = APIRouter()

    @router.get("/lark/bot/permission-checklist")
    @router.get("/api/lark/bot/permission-checklist")
    def get_lark_bot_permission_checklist() -> LarkBotPermissionChecklistResponse:
        return permission_checklist()

    @router.get("/lark/bot/preflight")
    @router.get("/api/lark/bot/preflight")
    def get_lark_bot_preflight() -> LarkBotPreflightResponse:
        return preflight()

    @router.get("/lark/bot/go-live-gate")
    @router.get("/api/lark/bot/go-live-gate")
    def get_lark_bot_go_live_gate() -> LarkBotGoLiveGateResponse:
        return go_live_gate()

    @router.get("/lark/bot/setup-acknowledgements")
    @router.get("/api/lark/bot/setup-acknowledgements")
    def list_lark_bot_setup_acknowledgements(
        item_key: str | None = None,
        limit: int = Query(default=100, ge=0, le=500),
        offset: int = Query(default=0, ge=0),
    ) -> LarkBotSetupAcknowledgementListResponse:
        return setup_acknowledgements(item_key, limit, offset)

    @router.post("/lark/bot/setup-acknowledgements/{item_key}")
    @router.post("/api/lark/bot/setup-acknowledgements/{item_key}")
    def acknowledge_lark_bot_setup_item(
        item_key: str,
        request: LarkBotSetupAcknowledgementRequest,
    ) -> LarkBotSetupAcknowledgement:
        return acknowledge_setup_item(item_key, request)

    @router.get("/lark/bot/setup-package.zip")
    @router.get("/api/lark/bot/setup-package.zip")
    def export_lark_bot_setup_package() -> Response:
        return setup_package()

    return router
