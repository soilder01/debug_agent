from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from debug_agent.lark.connector import LarkConnectorStatus

BotCommandKind = Literal[
    "help",
    "readiness",
    "pilot_gate",
    "worker_status",
    "worker_start",
    "worker_stop",
    "performance_summary",
    "model_catalog",
    "lark_preflight",
    "lark_go_live_gate",
    "lark_permission_checklist",
    "lark_operation_audits",
    "badcase_drafts",
    "pending_commands",
    "writeback_audits",
    "observability_summary",
    "artifact_retention",
    "case_list",
    "lark_spreadsheet_status",
    "lark_scope_check",
    "debug_jobs_export",
    "support_bundle",
    "database_backup",
    "job_list",
    "job_status",
    "job_report",
    "job_evidence",
    "job_run_stages",
    "recommended_action_statuses",
    "recommended_action_status_update",
    "recommended_action_verification",
    "human_handoff_statuses",
    "human_handoff_status_update",
    "strategy_followups",
    "strategy_followup_job",
    "targeted_probes",
    "targeted_probe_job",
    "auto_closure",
    "auto_closure_report",
    "batch_list",
    "batch_comparison",
    "batch_status",
    "batch_pause",
    "batch_resume",
    "batch_cancel",
    "submit_case",
    "submit_batch",
    "spreadsheet_sync",
    "spreadsheet_rerun",
    "spreadsheet_writeback_confirmation",
    "base_writeback_confirmation",
    "unknown",
]


SPREADSHEET_RERUN_WRITEBACK_OPTION_TOKENS = {
    "--writeback",
    "writeback",
    "写回",
    "回写",
    "对应列",
    "同步到飞书表格",
    "同步到飞书",
    "同步对应位置",
    "同步相应位置",
    "同步到对应位置",
    "同步到相应位置",
    "是否同步",
}

CONTROLLED_PROBE_OPTION_TOKENS = {
    "--controlled-probes",
    "--controlled-probe",
    "--submit-controlled-probes",
    "--submit-controlled-probe",
    "controlled-probes",
    "controlled-probe",
    "submit-controlled-probes",
    "受控probe",
    "受控探针",
    "提交受控probe",
    "提交受控探针",
    "假设probe",
}


class LarkBotCommandRequest(BaseModel):
    text: str
    actor: str = ""
    open_id: str = ""
    chat_id: str = ""
    message_id: str = ""
    tenant_key: str = ""
    identity: Literal["bot", "user", "unknown"] = "bot"
    profile: str = ""


class LarkBotCommandAction(BaseModel):
    kind: BotCommandKind
    method: Literal["GET", "POST", "PATCH", "NONE"]
    path: str = ""
    side_effect: bool = False
    confirmation_required: bool = False
    risk_level: Literal["none", "read", "write"] = "none"
    parameters: dict[str, object] = Field(default_factory=dict)


class LarkBotCardButton(BaseModel):
    label: str
    method: Literal["GET", "POST", "PATCH", "NONE"] = "GET"
    path: str = ""
    style: Literal["default", "primary", "danger"] = "default"
    confirmation_required: bool = False


class LarkBotCard(BaseModel):
    title: str
    status: Literal["info", "success", "warning", "critical"] = "info"
    summary: str
    fields: list[dict[str, str]] = Field(default_factory=list)
    buttons: list[LarkBotCardButton] = Field(default_factory=list)


class LarkBotAuditContext(BaseModel):
    actor: str
    open_id: str
    chat_id: str
    message_id: str
    tenant_key: str
    identity: Literal["bot", "user", "unknown"]
    profile: str
    safe_command: str


class LarkBotCommandResponse(BaseModel):
    action: LarkBotCommandAction
    card: LarkBotCard
    audit: LarkBotAuditContext
    connector: LarkConnectorStatus
    warnings: list[str] = Field(default_factory=list)


class LarkBotEventParseResult(BaseModel):
    event_type: str
    challenge: str = ""
    command_request: LarkBotCommandRequest | None = None
    ignored_reason: str = ""


class LarkBotEventResponse(BaseModel):
    event_type: str
    handled: bool
    challenge: str = ""
    ignored_reason: str = ""
    command: LarkBotCommandResponse | None = None


class LarkBotReplyPayload(BaseModel):
    command_id: str
    action_kind: str
    status: str
    target_type: Literal["message", "chat", "user", "none"] = "none"
    delivery_mode: Literal["send", "update_message"] = "send"
    message_id: str = ""
    chat_id: str = ""
    user_id: str = ""
    markdown: str
    message_type: Literal["post", "interactive"] = "post"
    content: dict[str, object] = Field(default_factory=dict)
    task_panel_key: str = ""
    task_panel_message_id: str = ""
    idempotency_key: str
    delivery_args: list[str] = Field(default_factory=list)
    fallback_delivery_args: list[str] = Field(default_factory=list)
