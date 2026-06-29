from __future__ import annotations

# ruff: noqa: F821

from types import ModuleType

_RUNTIME: ModuleType | None = None
EXPORTED_NAMES: tuple[str, ...] = (
    "_ensure_xiaod_spreadsheet_rerun_active_run",
    "_mark_xiaod_spreadsheet_rerun_batch_started",
    "_xiaod_spreadsheet_rerun_batch_id",
    "_fail_lark_bot_pending_command_background",
    "_active_xiaod_spreadsheet_rerun_run_for_command",
    "_pending_command_for_lifecycle_action",
    "_assert_lark_bot_pending_command_actor",
    "handle_lark_bot_event",
    "_handle_lark_bot_card_action_event",
    "_resolve_spreadsheet_rerun_writeback_decision",
    "_spreadsheet_rerun_writeback_decision_markdown",
    "_preview_lark_bot_command",
    "_run_coroutine_from_sync",
    "_execute_lark_bot_pending_command",
    "_payload_dict",
    "_payload_dict_list",
    "_spreadsheet_rerun_request_from_action",
    "_spreadsheet_rerun_preflight_from_action",
    "_action_bool",
    "_create_xiaod_pending_command",
    "_attach_spreadsheet_rerun_preflight",
    "_spreadsheet_rerun_row_media_resolver",
    "_lark_bot_pending_command_expired",
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


def _ensure_xiaod_spreadsheet_rerun_active_run(command: LarkBotPendingCommand) -> object:
    return pending_command_controller.ensure_spreadsheet_rerun_active_run(command)


def _mark_xiaod_spreadsheet_rerun_batch_started(
    *,
    command: LarkBotPendingCommand,
    batch_id: str,
) -> None:
    pending_command_controller.mark_spreadsheet_rerun_batch_started(
        command=command,
        batch_id=batch_id,
    )


def _xiaod_spreadsheet_rerun_batch_id(sheet_id: str) -> str:
    return pending_command_controller.spreadsheet_rerun_batch_id(sheet_id)


def _fail_lark_bot_pending_command_background(
    *,
    command: LarkBotPendingCommand,
    actor: str,
    error_message: str,
    error_type: str,
) -> None:
    pending_command_lifecycle_controller.fail_background(
        command=command,
        actor=actor,
        error_message=error_message,
        error_type=error_type,
    )


def _active_xiaod_spreadsheet_rerun_run_for_command(
    command: LarkBotPendingCommand,
) -> object | None:
    return pending_command_controller.active_spreadsheet_rerun_run_for_command(command)


def _pending_command_for_lifecycle_action(command_id: str) -> LarkBotPendingCommand:
    return pending_command_lifecycle_controller.pending_command_for_lifecycle_action(command_id)


def _assert_lark_bot_pending_command_actor(
    command: LarkBotPendingCommand,
    actor: str,
) -> None:
    pending_command_lifecycle_controller.assert_actor(command, actor)


async def handle_lark_bot_event(request: Request) -> dict[str, object]:
    return await lark_bot_event_controller.handle_event(request)


def _handle_lark_bot_card_action_event(payload: dict[str, object]) -> dict[str, object] | None:
    return lark_card_action_controller.handle_card_action_event(payload)


def _resolve_spreadsheet_rerun_writeback_decision(
    *,
    command: LarkBotPendingCommand,
    decision: object,
    actor: str,
    sync_requested: bool,
    default_skip: bool,
) -> dict[str, object]:
    return xiaod_spreadsheet_writeback_decision_controller.resolve_decision(
        command=command,
        decision=decision,
        actor=actor,
        sync_requested=sync_requested,
        default_skip=default_skip,
    )


def _spreadsheet_rerun_writeback_decision_markdown(
    *,
    command: LarkBotPendingCommand,
    status: str,
    row_results: list[dict[str, object]],
    default_skip: bool,
    completed_summary: dict[str, object] | None = None,
) -> str:
    return xiaod_spreadsheet_writeback_decision_controller.decision_markdown(
        command=command,
        status=status,
        row_results=row_results,
        default_skip=default_skip,
        completed_summary=completed_summary,
    )


def _preview_lark_bot_command(request: LarkBotCommandRequest) -> LarkBotCommandResponse:
    actor = _resolved_actor(request.actor or request.open_id)
    connector_status = _lark_connector_status_for_client(spreadsheet_sync_client)
    response = build_lark_bot_command_response(
        request,
        actor=actor,
        connector_status=connector_status,
        default_profile=lark_spreadsheet_settings.lark_cli_profile,
    )
    job_repository.save_lark_operation_audit(
        actor=actor,
        connector_mode=connector_status.mode,
        identity=response.audit.identity,
        profile=response.audit.profile,
        service="bot",
        operation=response.action.kind,
        status="succeeded",
        context=response.audit.safe_command,
        risk_action="confirmation_required" if response.action.confirmation_required else "",
        duration_ms=0,
    )
    return response


def _run_coroutine_from_sync(factory: Callable[[], Awaitable[object]]) -> object:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(factory())

    result: list[object | None] = []
    errors: list[BaseException] = []

    def runner() -> None:
        try:
            result.append(asyncio.run(factory()))
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join()
    if errors:
        raise errors[0]
    return result[0] if result else None


def _execute_lark_bot_pending_command(command: LarkBotPendingCommand) -> dict[str, object]:
    return pending_command_execution_controller.execute(command)


def _payload_dict(value: object) -> dict[str, object]:
    return pending_command_payload_dict(value)


def _payload_dict_list(value: object) -> list[dict[str, object]]:
    return pending_command_payload_dict_list(value)


def _spreadsheet_rerun_request_from_action(action: dict[str, object]) -> "SpreadsheetRerunRequest":
    return pending_command_execution_controller.spreadsheet_rerun_request_from_action(action)


def _spreadsheet_rerun_preflight_from_action(action: dict[str, object]) -> dict[str, object]:
    return pending_command_spreadsheet_rerun_preflight_from_action(action)


def _action_bool(action: dict[str, object], key: str) -> bool:
    return pending_command_action_bool(action, key)


def _create_xiaod_pending_command(
    *,
    preview: LarkBotCommandResponse,
    note: str,
) -> LarkBotPendingCommand:
    _attach_spreadsheet_rerun_preflight(preview.action)
    command = job_repository.create_lark_bot_pending_command(
        command_id=str(uuid4()),
        actor=preview.audit.actor,
        open_id=preview.audit.open_id,
        chat_id=preview.audit.chat_id,
        message_id=preview.audit.message_id,
        tenant_key=preview.audit.tenant_key,
        identity=preview.audit.identity,
        profile=preview.audit.profile,
        command_text=preview.audit.safe_command,
        action_kind=preview.action.kind,
        action=preview.action.model_dump(mode="json"),
        card=preview.card.model_dump(mode="json"),
        note=note,
        expires_at=(datetime.now(UTC) + timedelta(minutes=30)).isoformat(timespec="seconds"),
    )
    _save_lark_bot_audit(
        actor=command.actor,
        identity=command.identity,
        profile=command.profile,
        operation="pending_command_created",
        context=command.command_text,
        risk_action="confirmation_required",
    )
    return command


def _attach_spreadsheet_rerun_preflight(action: LarkBotCommandAction) -> None:
    spreadsheet_rerun_preflight_controller.attach_preflight(action)


def _spreadsheet_rerun_row_media_resolver(
    request: "SpreadsheetRerunRequest",
) -> Callable[[SpreadsheetSourceRow], SpreadsheetSourceRow] | None:
    return spreadsheet_rerun_preflight_controller.row_media_resolver(request)


def _lark_bot_pending_command_expired(command: LarkBotPendingCommand) -> bool:
    try:
        expires_at = datetime.fromisoformat(command.expires_at)
    except ValueError:
        return False
    return expires_at < datetime.now(UTC)
