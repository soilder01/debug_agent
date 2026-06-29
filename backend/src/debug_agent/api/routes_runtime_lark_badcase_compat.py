from __future__ import annotations

# ruff: noqa: F821

from types import ModuleType

_RUNTIME: ModuleType | None = None
EXPORTED_NAMES: tuple[str, ...] = (
    "_xiaod_latest_draft_for_chat",
    "_xiaod_latest_submitted_draft_for_chat",
    "create_lark_bot_badcase_draft",
    "list_lark_bot_badcase_drafts",
    "get_lark_bot_badcase_draft",
    "preview_lark_bot_badcase_confirmation_card",
    "preview_lark_bot_badcase_confirm_link",
    "submit_lark_bot_badcase_confirm_link",
    "preview_lark_bot_badcase_writeback_link",
    "submit_lark_bot_badcase_writeback_link",
    "preview_lark_bot_badcase_base_writeback_link",
    "submit_lark_bot_badcase_base_writeback_link",
    "mark_lark_bot_badcase_completion_notified",
    "mark_lark_bot_badcase_completion_delivery_failed",
    "cancel_lark_bot_badcase_draft",
    "confirm_lark_bot_badcase_draft",
    "_save_lark_bot_badcase_draft_from_request",
    "_case_intake_schema_mapping_agent",
    "_case_intake_model_context_case",
    "_lark_bot_badcase_base_mapping",
    "_lark_badcase_media_uri",
    "_badcase_input_source_is_missing_placeholder",
    "_normalized_lark_badcase_input_source",
    "_lark_bot_badcase_confirmation_card_payload",
    "_lark_bot_badcase_action_url",
    "_lark_bot_badcase_draft_for_action_link",
    "_lark_bot_badcase_action_token",
    "_lark_bot_action_token_secret",
    "_lark_bot_badcase_action_page_html",
    "_lark_bot_badcase_writeback_page_html",
    "_lark_bot_badcase_base_writeback_page_html",
    "_write_lark_bot_badcase_result_to_spreadsheet",
    "_ensure_spreadsheet_writeback_client_for_job",
    "_write_lark_bot_badcase_result_to_base",
    "_lark_bot_badcase_action_result_html",
    "_badcase_link_contexts",
    "_debug_case_from_sheet_rows",
    "_lark_sheet_cell",
    "_download_lark_sheet_attachment",
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


def _xiaod_latest_draft_for_chat(*, chat_id: str, open_id: str) -> LarkBotBadcaseDraft | None:
    open_draft = job_repository.latest_lark_bot_badcase_draft_for_chat(
        chat_id=chat_id,
        open_id=open_id,
    )
    submitted_draft = _xiaod_latest_submitted_draft_for_chat(chat_id=chat_id, open_id=open_id)
    if submitted_draft is None or not submitted_draft.submitted_job_id:
        return open_draft if open_draft is not None else submitted_draft
    job = job_repository.get_job(submitted_draft.submitted_job_id)
    if job is None or job.status in {"completed", "failed", "cancelled"}:
        return open_draft
    return submitted_draft


def _xiaod_latest_submitted_draft_for_chat(
    *,
    chat_id: str,
    open_id: str,
) -> LarkBotBadcaseDraft | None:
    if not chat_id:
        return None
    for draft in job_repository.list_lark_bot_badcase_drafts(limit=200):
        if draft.chat_id != chat_id:
            continue
        if open_id and draft.open_id != open_id:
            continue
        if draft.submitted_job_id:
            return draft
    return None


def create_lark_bot_badcase_draft(request: LarkBotBadcaseDraftRequest) -> LarkBotBadcaseDraft:
    actor = _resolved_actor(request.actor or request.open_id)
    existing = (
        job_repository.latest_lark_bot_badcase_draft_for_chat(
            chat_id=request.chat_id,
            open_id=request.open_id,
        )
        if request.chat_id
        else None
    )
    return _save_lark_bot_badcase_draft_from_request(
        request=request,
        actor=actor,
        draft_id=existing.draft_id if existing is not None else str(uuid4()),
        existing=existing,
    )


def list_lark_bot_badcase_drafts(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> LarkBotBadcaseDraftListResponse:
    normalized_status = status.strip() if isinstance(status, str) and status.strip() else None
    drafts = job_repository.list_lark_bot_badcase_drafts(
        status=normalized_status,
        limit=limit,
        offset=offset,
    )
    return LarkBotBadcaseDraftListResponse(drafts=drafts, total_count=len(drafts))


def get_lark_bot_badcase_draft(draft_id: str) -> LarkBotBadcaseDraft:
    draft = job_repository.get_lark_bot_badcase_draft(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail=f"Lark bot badcase draft not found: {draft_id}")
    return draft


def preview_lark_bot_badcase_confirmation_card(draft_id: str) -> LarkBotReplyPayload:
    return lark_badcase_action_controller.preview_confirmation_card(draft_id)


def preview_lark_bot_badcase_confirm_link(
    draft_id: str,
    action: Literal["confirm_badcase_draft", "cancel_badcase_draft"] = "confirm_badcase_draft",
    token: str = "",
) -> Response:
    return lark_badcase_action_controller.preview_confirm_link(draft_id, action, token)


def submit_lark_bot_badcase_confirm_link(
    draft_id: str,
    action: Literal["confirm_badcase_draft", "cancel_badcase_draft"] = "confirm_badcase_draft",
    token: str = "",
) -> Response:
    return lark_badcase_action_controller.submit_confirm_link(draft_id, action, token)


def preview_lark_bot_badcase_writeback_link(
    draft_id: str,
    token: str = "",
) -> Response:
    return lark_badcase_action_controller.preview_writeback_link(draft_id, token)


def submit_lark_bot_badcase_writeback_link(
    draft_id: str,
    token: str = "",
) -> Response:
    return lark_badcase_action_controller.submit_writeback_link(draft_id, token)


def preview_lark_bot_badcase_base_writeback_link(
    draft_id: str,
    token: str = "",
) -> Response:
    return lark_badcase_action_controller.preview_base_writeback_link(draft_id, token)


def submit_lark_bot_badcase_base_writeback_link(
    draft_id: str,
    token: str = "",
) -> Response:
    return lark_badcase_action_controller.submit_base_writeback_link(draft_id, token)


def mark_lark_bot_badcase_completion_notified(
    draft_id: str,
    request: LarkBotBadcaseDraftCompletionNotifiedRequest,
) -> LarkBotBadcaseDraft:
    return lark_badcase_action_controller.mark_completion_notified(draft_id, request)


def mark_lark_bot_badcase_completion_delivery_failed(
    draft_id: str,
    request: LarkBotBadcaseDraftCompletionFailedRequest,
) -> LarkBotBadcaseDraft:
    return lark_badcase_action_controller.mark_completion_delivery_failed(draft_id, request)


def cancel_lark_bot_badcase_draft(
    draft_id: str,
    request: LarkBotBadcaseDraftCancelRequest,
) -> LarkBotBadcaseDraft:
    return lark_badcase_submission_controller.cancel(draft_id, request)


def confirm_lark_bot_badcase_draft(
    draft_id: str,
    request: LarkBotBadcaseDraftConfirmRequest,
) -> LarkBotBadcaseDraftConfirmResponse:
    return lark_badcase_submission_controller.confirm(draft_id, request)


def _save_lark_bot_badcase_draft_from_request(
    *,
    request: LarkBotBadcaseDraftRequest,
    actor: str,
    draft_id: str,
    existing: LarkBotBadcaseDraft | None = None,
) -> LarkBotBadcaseDraft:
    return lark_badcase_draft_intake_controller.save_from_request(
        request=request,
        actor=actor,
        draft_id=draft_id,
        existing=existing,
    )


def _case_intake_schema_mapping_agent() -> SpreadsheetSchemaMappingAgent:
    try:
        selection = default_agent_model_config().roles.get("case_intake")
        if selection is None:
            return SpreadsheetSchemaMappingAgent(
                model_error="case_intake model selection is not configured"
            )
        adapter = build_adapter_for_selection(
            case=_case_intake_model_context_case(),
            selection=selection,
        )
        return SpreadsheetSchemaMappingAgent(model_adapter=adapter)
    except Exception as exc:
        return SpreadsheetSchemaMappingAgent(model_error=str(exc))


def _case_intake_model_context_case() -> DebugCase:
    return DebugCase(
        case_id="case-intake-schema-mapping",
        task_type="case_intake",
        image_uri="",
        prompt="Map spreadsheet headers and rows into DebugCase fields.",
        golden_answer=AnswerSet(answers=[]),
        expected_output={},
        output_schema={},
        scoring_standard="Return a JSON mapping from spreadsheet columns to DebugCase fields.",
        predictions=[Prediction(trial=0, raw_output="{}", score=0)],
        avg_score=0.0,
        human_notes=HumanNotes(debug_status="case_intake", root_cause=""),
    )


def _lark_bot_badcase_base_mapping(
    *,
    draft: LarkBotBadcaseDraft,
) -> tuple[str, str, str] | None:
    return lark_badcase_submission_controller.base_mapping(draft=draft)


def _lark_badcase_media_uri(input_source: str) -> str:
    return lark_badcase_submission_controller.media_uri(input_source)


def _badcase_input_source_is_missing_placeholder(value: str) -> bool:
    source = value.strip().lower()
    if not source:
        return False
    missing_markers = (
        "暂未提供",
        "未提供",
        "没有链接",
        "没链接",
        "无链接",
        "暂无链接",
        "没有附件",
        "无附件",
        "未上传",
        "待补充",
        "缺少",
        "帮我记一下",
        "先帮我记",
        "记一下",
        "missing",
        "not provided",
        "no link",
        "no attachment",
        "unknown",
        "n/a",
    )
    return any(marker in source for marker in missing_markers)


def _normalized_lark_badcase_input_source(input_source: str) -> str:
    source = input_source.strip()
    if not _input_source_requires_media_resolution(source):
        return source
    return _lark_badcase_media_uri(source)


def _lark_bot_badcase_confirmation_card_payload(
    *,
    draft: LarkBotBadcaseDraft,
    dry_run: bool,
) -> LarkBotReplyPayload:
    return lark_badcase_renderer.confirmation_card_payload(draft=draft, dry_run=dry_run)


def _lark_bot_badcase_action_url(
    *,
    draft: LarkBotBadcaseDraft,
    action: LarkBotBadcaseAction,
) -> str:
    return lark_badcase_renderer.action_url(draft=draft, action=action)


def _lark_bot_badcase_draft_for_action_link(
    *,
    draft_id: str,
    action: LarkBotBadcaseAction,
    token: str,
) -> LarkBotBadcaseDraft:
    draft = job_repository.get_lark_bot_badcase_draft(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail=f"Lark bot badcase draft not found: {draft_id}")
    expected = _lark_bot_badcase_action_token(draft=draft, action=action)
    if not token or not expected or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=403, detail="Invalid Lark bot action token.")
    return draft


def _lark_bot_badcase_action_token(
    *,
    draft: LarkBotBadcaseDraft,
    action: LarkBotBadcaseAction,
) -> str:
    return lark_badcase_renderer.action_token(draft=draft, action=action)


def _lark_bot_action_token_secret(*, draft: LarkBotBadcaseDraft) -> str:
    candidates = [
        settings.lark_bot_action_token_secret,
        settings.lark_bot_verification_token,
        settings.lark_bot_encrypt_key,
    ]
    for candidate in candidates:
        if candidate is not None and candidate.get_secret_value().strip():
            return candidate.get_secret_value().strip()
    return draft.message_id.strip()


def _lark_bot_badcase_action_page_html(
    *,
    draft: LarkBotBadcaseDraft,
    action: Literal["confirm_badcase_draft", "cancel_badcase_draft"],
    token: str,
) -> str:
    return lark_badcase_renderer.action_page_html(draft=draft, action=action, token=token)


def _lark_bot_badcase_writeback_page_html(*, draft: LarkBotBadcaseDraft, token: str) -> str:
    return lark_badcase_renderer.spreadsheet_writeback_page_html(draft=draft, token=token)


def _lark_bot_badcase_base_writeback_page_html(*, draft: LarkBotBadcaseDraft, token: str) -> str:
    return lark_badcase_renderer.base_writeback_page_html(draft=draft, token=token)


def _write_lark_bot_badcase_result_to_spreadsheet(
    *, draft: LarkBotBadcaseDraft
) -> SpreadsheetWritebackResult:
    if not draft.submitted_job_id:
        raise HTTPException(status_code=409, detail="Badcase draft has no submitted job.")
    job = job_repository.get_job(draft.submitted_job_id)
    if job is None:
        raise HTTPException(
            status_code=404, detail=f"Debug job not found: {draft.submitted_job_id}"
        )
    if job.status != "completed":
        raise HTTPException(status_code=409, detail=f"Debug job is not completed: {job.status}")
    _ensure_spreadsheet_writeback_client_for_job(job.job_id)
    actor = _resolved_actor(draft.open_id or draft.actor)
    report_url = _canonical_report_url_for_job(job=job, actor=actor)
    confirmation = create_job_report_writeback_confirmation(
        job.job_id,
        JobReportWritebackConfirmationRequest(
            report_url=report_url,
            actor=actor,
            note="Created from Lark writeback confirmation page.",
        ),
    )
    confirm_lark_write_confirmation(
        confirmation.confirmation_id,
        LarkWriteConfirmationConfirmRequest(
            actor=actor,
            note="Confirmed from Lark writeback confirmation page.",
        ),
    )
    return write_job_report_to_spreadsheet(
        job.job_id,
        JobReportWritebackRequest(
            report_url=report_url,
            require_confirmation=True,
            confirmation_id=confirmation.confirmation_id,
            actor=actor,
            note="Written from Lark writeback confirmation page.",
        ),
    )


def _ensure_spreadsheet_writeback_client_for_job(job_id: str) -> None:
    if spreadsheet_writeback_client is not None:
        return
    target = _spreadsheet_writeback_target_for_job(job_id)
    if target is None:
        return
    spreadsheet_id, sheet_id, _row_id = target
    configure_spreadsheet_clients(
        LarkSpreadsheetSettings(
            spreadsheet_url=spreadsheet_id,
            sheet_id=sheet_id,
            lark_cli_timeout_seconds=lark_spreadsheet_settings.lark_cli_timeout_seconds,
            lark_cli_profile=lark_spreadsheet_settings.lark_cli_profile,
            lark_cli_identity=lark_spreadsheet_settings.lark_cli_identity,
            reference=parse_lark_spreadsheet_reference(spreadsheet_id, sheet_id=sheet_id),
        )
    )


def _write_lark_bot_badcase_result_to_base(*, draft: LarkBotBadcaseDraft) -> "BaseWritebackResult":
    if not draft.submitted_job_id:
        raise HTTPException(status_code=409, detail="Badcase draft has no submitted job.")
    job = job_repository.get_job(draft.submitted_job_id)
    if job is None:
        raise HTTPException(
            status_code=404, detail=f"Debug job not found: {draft.submitted_job_id}"
        )
    if job.status != "completed":
        raise HTTPException(status_code=409, detail=f"Debug job is not completed: {job.status}")
    actor = _resolved_actor(draft.open_id or draft.actor)
    report_url = _canonical_report_url_for_job(job=job, actor=actor)
    confirmation = create_job_report_base_writeback_confirmation(
        job.job_id,
        JobReportBaseWritebackConfirmationRequest(
            report_url=report_url,
            actor=actor,
            note="Created from Lark Base writeback confirmation page.",
        ),
    )
    confirm_lark_write_confirmation(
        confirmation.confirmation_id,
        LarkWriteConfirmationConfirmRequest(
            actor=actor,
            note="Confirmed from Lark Base writeback confirmation page.",
        ),
    )
    return write_job_report_to_base_record(
        job.job_id,
        JobReportBaseWritebackRequest(
            report_url=report_url,
            require_confirmation=True,
            confirmation_id=confirmation.confirmation_id,
            actor=actor,
            note="Written from Lark Base writeback confirmation page.",
        ),
    )


def _lark_bot_badcase_action_result_html(*, title: str, lines: list[str]) -> str:
    return action_result_html(title=title, lines=lines)


def _badcase_link_contexts(
    links: list[str],
    *,
    resolve_content: bool = False,
    actor: str = "",
    target_label: str = "",
) -> list[dict[str, object]]:
    return lark_badcase_link_context_resolver.badcase_link_contexts(
        links,
        resolve_content=resolve_content,
        actor=actor,
        target_label=target_label,
    )


def _debug_case_from_sheet_rows(
    data: dict[str, object],
    *,
    preferred_row_id: str,
    preferred_row_label: str = "",
) -> dict[str, object]:
    return lark_badcase_link_context_resolver.debug_case_from_sheet_rows(
        data,
        preferred_row_id=preferred_row_id,
        preferred_row_label=preferred_row_label,
    )


def _lark_sheet_cell(
    *,
    connector: LarkCliConnector,
    spreadsheet_token: str,
    sheet_id: str,
    column: str,
    row: str,
) -> dict[str, object]:
    return lark_badcase_link_context_resolver.lark_sheet_cell(
        connector=connector,
        spreadsheet_token=spreadsheet_token,
        sheet_id=sheet_id,
        column=column,
        row=row,
    )


def _download_lark_sheet_attachment(
    *,
    connector: LarkCliConnector,
    attachment: dict[str, object],
    fallback_name: str,
) -> dict[str, object]:
    return lark_badcase_link_context_resolver.download_lark_sheet_attachment(
        connector=connector,
        attachment=attachment,
        fallback_name=fallback_name,
    )
