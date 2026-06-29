from __future__ import annotations

# ruff: noqa: F821

from types import ModuleType

_RUNTIME: ModuleType | None = None
EXPORTED_NAMES: tuple[str, ...] = (
    "_lark_report_document_connector",
    "_lark_report_doc_identity",
    "_lark_report_doc_profile",
    "_lark_bot_read_connector",
    "_lark_bot_read_identity",
    "_lark_bot_write_identity",
    "_lark_bot_base_write_connector",
    "_save_lark_bot_audit",
    "_lark_bot_im_connector",
    "_record_lark_connector_audit_for_actor",
)


def bind_runtime(runtime: ModuleType) -> None:
    global _RUNTIME
    _RUNTIME = runtime
    for name, value in vars(runtime).items():
        if not name.startswith("__"):
            globals()[name] = value


def runtime_module() -> ModuleType:
    if _RUNTIME is None:
        raise RuntimeError("routes runtime helpers are not bound")
    return _RUNTIME


def _lark_report_document_connector(*, actor: str) -> LarkCliConnector:
    return LarkCliConnector(
        timeout_seconds=lark_spreadsheet_settings.lark_cli_timeout_seconds,
        profile=_lark_report_doc_profile(),
        identity=_lark_report_doc_identity(),
        allowed_commands={("docs", "+create")},
        audit_sink=lambda event: _record_lark_connector_audit_for_actor(actor, event),
    )


def _lark_report_doc_identity() -> Literal["bot", "user", "unknown"]:
    return cast(Literal["bot", "user", "unknown"], settings.lark_report_doc_identity)


def _lark_report_doc_profile() -> str:
    if settings.lark_report_doc_profile:
        return settings.lark_report_doc_profile
    if _lark_report_doc_identity() == "bot":
        return lark_spreadsheet_settings.lark_cli_profile
    return ""


def _lark_bot_read_connector(*, actor: str) -> LarkCliConnector:
    return LarkCliConnector(
        timeout_seconds=lark_spreadsheet_settings.lark_cli_timeout_seconds,
        profile=lark_spreadsheet_settings.lark_cli_profile,
        identity=_lark_bot_read_identity(),
        allowed_commands={
            ("docs", "+fetch"),
            ("sheets", "+csv-get"),
            ("sheets", "+cells-get"),
            ("drive", "+download"),
            ("api", "GET"),
            ("base", "+table-list"),
            ("base", "+record-list"),
        },
        audit_sink=lambda event: _record_lark_connector_audit_for_actor(actor, event),
    )


def _lark_bot_read_identity() -> Literal["bot", "user", "unknown"]:
    identity = lark_spreadsheet_settings.lark_cli_identity
    return cast(
        Literal["bot", "user", "unknown"], identity if identity in {"bot", "user"} else "bot"
    )


def _lark_bot_write_identity() -> Literal["bot", "user", "unknown"]:
    identity = lark_spreadsheet_settings.lark_cli_identity
    return cast(
        Literal["bot", "user", "unknown"], identity if identity in {"bot", "user"} else "bot"
    )


def _lark_bot_base_write_connector(*, actor: str) -> LarkCliConnector:
    return LarkCliConnector(
        timeout_seconds=lark_spreadsheet_settings.lark_cli_timeout_seconds,
        profile=lark_spreadsheet_settings.lark_cli_profile,
        identity=_lark_bot_write_identity(),
        allowed_commands={("base", "+record-upsert")},
        audit_sink=lambda event: _record_lark_connector_audit_for_actor(actor, event),
    )


def _save_lark_bot_audit(
    *,
    actor: str,
    identity: str,
    profile: str,
    operation: str,
    context: str,
    risk_action: str,
    status: Literal["succeeded", "failed"] = "succeeded",
    error_type: str = "",
    hint: str = "",
) -> None:
    connector_status = _lark_connector_status_for_client(spreadsheet_sync_client)
    job_repository.save_lark_operation_audit(
        actor=actor,
        connector_mode=connector_status.mode,
        identity=identity,
        profile=profile,
        service="bot",
        operation=operation,
        status=status,
        context=context,
        error_type=error_type,
        hint=hint,
        risk_action=risk_action,
        duration_ms=0,
    )


def _lark_bot_im_connector(*, actor: str, identity: str, profile: str) -> LarkCliConnector:
    resolved_identity = cast(
        Literal["bot", "user", "unknown"],
        identity if identity in {"bot", "user", "unknown"} else "unknown",
    )
    return LarkCliConnector(
        timeout_seconds=lark_spreadsheet_settings.lark_cli_timeout_seconds,
        profile=profile or lark_spreadsheet_settings.lark_cli_profile,
        identity=resolved_identity,
        allowed_commands={("im", "+messages-send"), ("im", "+messages-reply")},
        audit_sink=lambda event: _record_lark_connector_audit_for_actor(actor, event),
    )


def _record_lark_connector_audit_for_actor(actor: str, event: LarkConnectorAuditEvent) -> None:
    job_repository.save_lark_operation_audit(
        actor=actor,
        connector_mode=event.connector_mode,
        identity=event.identity,
        profile=event.profile,
        service=event.service,
        operation=event.operation,
        status=event.status,
        context=event.context,
        error_type=event.error_type,
        hint=event.hint,
        permission_scopes=event.permission_scopes,
        console_url=event.console_url,
        risk_action=event.risk_action,
        duration_ms=event.duration_ms,
    )
