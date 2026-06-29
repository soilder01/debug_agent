from __future__ import annotations

# ruff: noqa: F821

from types import ModuleType

_RUNTIME: ModuleType | None = None
EXPORTED_NAMES: tuple[str, ...] = ()


def bind_runtime(runtime: ModuleType) -> None:
    global _RUNTIME
    _RUNTIME = runtime
    for name, value in vars(runtime).items():
        if not name.startswith("__"):
            globals()[name] = value


def configure_runtime(runtime: ModuleType) -> None:
    bind_runtime(runtime)
    spreadsheet_rerun_preflight_controller = SpreadsheetRerunPreflightController(
        spreadsheet_client=lambda: spreadsheet_sync_client,
        configure_clients_from_request=lambda request: _configure_spreadsheet_clients_from_request(
            request
        ),
        request_from_action=lambda action: _spreadsheet_rerun_request_from_action(action),
        read_connector=lambda actor: _lark_bot_read_connector(actor=actor),
        lark_sheet_cell=lambda **kwargs: _lark_sheet_cell(**kwargs),
        download_lark_sheet_attachment=lambda **kwargs: _download_lark_sheet_attachment(**kwargs),
    )
    spreadsheet_route_controller = SpreadsheetRouteController(
        job_repository=job_repository,
        job_service=job_service,
        spreadsheet_settings=lambda: lark_spreadsheet_settings,
        spreadsheet_sync_client=lambda: spreadsheet_sync_client,
        configure_clients_from_request=lambda request: _configure_spreadsheet_clients_from_request(
            request
        ),
        spreadsheet_settings_from_request=lambda **kwargs: _spreadsheet_settings_from_request(
            **kwargs
        ),
        lark_client_for_settings=lambda lark_settings: _lark_client_for_settings(lark_settings),
        lark_connector_status_for_client=lambda client: _lark_connector_status_for_client(client),
        lark_spreadsheet_error=lambda exc: _lark_spreadsheet_error(exc),
        resolved_actor=lambda actor: _resolved_actor(actor),
        raise_if_usage_budget_blocks_submission=lambda: _raise_if_usage_budget_blocks_submission(),
        spreadsheet_rerun_row_media_resolver=lambda request: (
            spreadsheet_rerun_preflight_controller.row_media_resolver(request)
        ),
        run_spreadsheet_rerun_auto_closures=lambda **kwargs: (
            auto_closure_report_controller.run_spreadsheet_rerun_auto_closures(**kwargs)
        ),
        debug_batch_view_builder=debug_batch_view_builder,
    )
    artifact_route_controller = ArtifactRouteController(
        settings=lambda: settings,
        resolved_actor=lambda actor: _resolved_actor(actor),
    )
    debug_job_export_controller = DebugJobExportController(
        settings=lambda: settings,
        job_repository=job_repository,
        build_job_status=lambda job: _build_job_status(job),
        evidence_ledger_record=lambda **kwargs: _evidence_ledger_record(**kwargs),
        artifact_file_path=lambda filename: artifact_route_controller.artifact_file_path(filename),
    )
    operations_export_controller = OperationsExportController(
        settings=lambda: settings,
        job_repository=job_repository,
        readiness=lambda: operations_status_controller.get_readiness(),
        observability_summary=lambda: get_observability_summary(),
        worker_status=lambda: _build_worker_runtime_status(),
        artifact_retention=lambda limit: artifact_route_controller.build_retention_status(
            limit=limit
        ),
        pilot_gate=lambda: operations_status_controller.get_pilot_gate(
            limit=5,
            min_completed_jobs=20,
            min_success_rate=0.8,
            max_p95_duration_ms=12_000,
            max_estimated_cost_units=None,
            max_model_call_errors=0,
            max_writeback_failed=0,
            max_lark_operation_failures=0,
        ),
        lark_bot_preflight=lambda: lark_bot_setup_controller.get_preflight(),
        lark_bot_go_live_gate=lambda: lark_bot_setup_controller.get_go_live_gate(),
        lark_bot_permission_checklist=lambda: lark_bot_setup_controller.get_permission_checklist(),
        sqlite_database_path=lambda database_url: _sqlite_database_path(database_url),
        database_kind=lambda database_url: _database_kind(database_url),
        redacted_database_url=lambda database_url: _redacted_database_url(database_url),
    )
    lark_progress_controller = LarkProgressController(
        settings=lambda: settings,
        job_repository=job_repository,
        report_url=lambda job_id: _published_or_internal_report_url(job_id),
    )
    auto_closure_report_controller = AutoClosureReportController(
        job_repository=lambda: job_repository,
        job_service=lambda: job_service,
        build_report=lambda job_id: build_report_for_job(job_repository, job_id),
        artifact_dir_for_job_id=lambda job_id: _artifact_dir_for_job_id(job_id),
        video_clipper_for_job=lambda job_id: _video_clipper_for_job(job_id),
        original_cot_excerpt=lambda case: _original_cot_excerpt(case),
        original_prediction=lambda case: _original_prediction(case),
        record_debug_lesson=lambda lesson: runtime.project_assistant.add_debug_lesson_object(
            lesson
        ),
    )
    pending_command_execution_controller = LarkPendingCommandExecutionController(
        settings=lambda: settings,
        job_repository=lambda: job_repository,
        job_service=lambda: job_service,
        job_worker=lambda: runtime.job_worker,
        debug_batch_view_builder=lambda: debug_batch_view_builder,
        run_coroutine_from_sync=lambda runner: _run_coroutine_from_sync(runner),
        usage_budget_guard=lambda: _raise_if_usage_budget_blocks_submission(),
        new_artifact_group_id=lambda prefix: _new_artifact_group_id(prefix),
        worker_runtime_status=lambda: _build_worker_runtime_status(),
        sync_spreadsheet=lambda request: sync_spreadsheet(request),
        rerun_spreadsheet=lambda request: rerun_spreadsheet(request),
        run_spreadsheet_rerun_auto_closures=lambda **kwargs: (
            auto_closure_report_controller.run_spreadsheet_rerun_auto_closures(**kwargs)
        ),
        xiaod_spreadsheet_rerun_batch_id=lambda sheet_id: (
            pending_command_controller.spreadsheet_rerun_batch_id(sheet_id)
        ),
        mark_xiaod_spreadsheet_rerun_batch_started=lambda **kwargs: (
            pending_command_controller.mark_spreadsheet_rerun_batch_started(**kwargs)
        ),
        active_xiaod_spreadsheet_rerun_run_for_command=lambda command: (
            pending_command_controller.active_spreadsheet_rerun_run_for_command(command)
        ),
        create_job_report_writeback_confirmation=lambda job_id, request: (
            create_job_report_writeback_confirmation(job_id, request)
        ),
        create_job_report_base_writeback_confirmation=lambda job_id, request: (
            create_job_report_base_writeback_confirmation(job_id, request)
        ),
        update_recommended_action_status=lambda *args, **kwargs: update_recommended_action_status(
            *args, **kwargs
        ),
        create_recommended_action_verification_job=lambda *args, **kwargs: (
            create_recommended_action_verification_job(*args, **kwargs)
        ),
        update_human_handoff_status=lambda *args, **kwargs: update_human_handoff_status(
            *args, **kwargs
        ),
        create_strategy_follow_up_job=lambda *args, **kwargs: create_strategy_follow_up_job(
            *args, **kwargs
        ),
        create_targeted_probe_job=lambda *args, **kwargs: create_targeted_probe_job(
            *args, **kwargs
        ),
        run_job_auto_debug_closure=lambda *args, **kwargs: run_job_auto_debug_closure(
            *args, **kwargs
        ),
        run_job_auto_debug_closure_report=lambda *args, **kwargs: run_job_auto_debug_closure_report(
            *args, **kwargs
        ),
    )
    pending_command_controller = LarkPendingCommandController(
        job_repository=lambda: job_repository,
        preview_command=lambda request: _preview_lark_bot_command(request),
        resolved_actor=lambda actor: _resolved_actor(actor),
        save_audit=lambda **kwargs: _save_lark_bot_audit(**kwargs),
        attach_spreadsheet_rerun_preflight=lambda action: _attach_spreadsheet_rerun_preflight(
            action
        ),
        action_bool=lambda action, key: _action_bool(action, key),
        spreadsheet_rerun_preflight_from_action=lambda action: (
            _spreadsheet_rerun_preflight_from_action(action)
        ),
        execute_pending_command=lambda command: _execute_lark_bot_pending_command(command),
        fail_background=lambda **kwargs: _fail_lark_bot_pending_command_background(**kwargs),
        http_exception_detail_text=lambda detail: _http_exception_detail_text(detail),
    )
    observability_controller = ObservabilityController(
        job_repository=job_repository,
        worker_status=lambda: _build_worker_runtime_status(),
        usage_budget_units=lambda: settings.usage_budget_units,
        budget_enforcement_enabled=lambda: settings.enforce_usage_budget,
    )
    operations_status_controller = OperationsStatusController(
        settings=lambda: settings,
        spreadsheet_settings=lambda: lark_spreadsheet_settings,
        writeback_client_configured=lambda: spreadsheet_writeback_client is not None,
        job_repository=job_repository,
        debug_batch_view_builder=debug_batch_view_builder,
        worker_status=lambda: _build_worker_runtime_status(),
        connector_status=lambda: _lark_connector_status_for_client(spreadsheet_sync_client),
        database_kind=lambda database_url: _database_kind(database_url),
        database_path=lambda database_url: _database_path(database_url),
        sqlite_database_path=lambda database_url: _sqlite_database_path(database_url),
        redacted_database_url=lambda database_url: _redacted_database_url(database_url),
        lark_event_mode=lambda: _lark_event_mode(),
        lark_bot_verification_token=lambda: _lark_bot_verification_token(),
        lark_bot_encrypt_key=lambda: _lark_bot_encrypt_key(),
        webhook_token_readiness_status=lambda: _lark_bot_webhook_token_readiness_status(),
        encrypt_key_readiness_status=lambda: _lark_bot_encrypt_key_readiness_status(),
    )
    LOCAL_DEV_OPERATOR = "local-dev-operator"
    lark_bot_setup_package_builder = LarkBotSetupPackageBuilder(
        settings=lambda: settings,
        preflight=lambda: lark_bot_setup_controller.get_preflight(),
        permission_checklist=lambda: lark_bot_setup_controller.get_permission_checklist(),
        setup_acknowledgements=lambda limit: job_repository.list_lark_bot_setup_acknowledgements(
            limit=limit
        ),
        verification_token=lambda: _lark_bot_verification_token(),
        encrypt_key=lambda: _lark_bot_encrypt_key(),
        permission_console_url=LARK_PERMISSION_CONSOLE_URL,
        receive_event_type=LARK_BOT_RECEIVE_EVENT_TYPE,
        long_connection_profile=LARK_BOT_LONG_CONNECTION_PROFILE,
    )
    LarkBotEventMode = Literal["webhook", "long_connection"]
    LarkBotBadcaseAction = Literal[
        "confirm_badcase_draft",
        "cancel_badcase_draft",
        "writeback_spreadsheet",
        "writeback_base",
    ]
    lark_badcase_renderer = LarkBadcaseRenderer(
        report_base_url=lambda: settings.report_base_url,
        token_secret=lambda draft: _lark_bot_action_token_secret(draft=draft),
        reply_target_type=lambda draft: _lark_bot_reply_target_type(draft),
        idempotency_key=lambda kind: lark_bot_idempotency_key(kind),
        reply_cli_args=lambda payload, identity, dry_run: lark_bot_reply_cli_args(
            payload, identity=identity, dry_run=dry_run
        ),
        spreadsheet_writeback_target=lambda job_id: _spreadsheet_writeback_target_for_job(job_id),
        base_writeback_target=lambda job_id: _base_writeback_target_for_job(job_id),
    )
    lark_badcase_link_context_resolver = LarkBadcaseLinkContextResolver(
        read_identity=lambda: _lark_bot_read_identity(),
        read_connector=lambda actor: _lark_bot_read_connector(actor=actor),
        schema_mapping_agent=lambda: _case_intake_schema_mapping_agent(),
        media_dir=lambda: settings.image_artifact_dir / "lark-bot-media",
    )
    lark_badcase_draft_intake_controller = LarkBadcaseDraftIntakeController(
        job_repository=lambda: job_repository,
        link_contexts=lambda links, resolve_content, actor, target_label: _badcase_link_contexts(
            links,
            resolve_content=resolve_content,
            actor=actor,
            target_label=target_label,
        ),
        input_source_is_missing_placeholder=lambda value: (
            _badcase_input_source_is_missing_placeholder(value)
        ),
        normalized_input_source=lambda value: _normalized_lark_badcase_input_source(value),
        lark_cli_profile=lambda: lark_spreadsheet_settings.lark_cli_profile,
        save_audit=lambda **kwargs: _save_lark_bot_audit(**kwargs),
    )
    lark_badcase_submission_controller = LarkBadcaseSubmissionController(
        job_repository=lambda: job_repository,
        job_service=lambda: job_service,
        resolved_actor=lambda actor: _resolved_actor(actor),
        raise_if_usage_budget_blocks_submission=lambda: _raise_if_usage_budget_blocks_submission(),
        lark_cli_profile=lambda: lark_spreadsheet_settings.lark_cli_profile,
        save_audit=lambda **kwargs: _save_lark_bot_audit(**kwargs),
    )
    lark_badcase_action_controller = LarkBadcaseActionController(
        job_repository=lambda: job_repository,
        resolved_actor=lambda actor: _resolved_actor(actor),
        lark_cli_profile=lambda: lark_spreadsheet_settings.lark_cli_profile,
        save_audit=lambda **kwargs: _save_lark_bot_audit(**kwargs),
        confirmation_card_payload=lambda draft, dry_run: (
            _lark_bot_badcase_confirmation_card_payload(draft=draft, dry_run=dry_run)
        ),
        draft_for_action_link=lambda draft_id, action, token: (
            _lark_bot_badcase_draft_for_action_link(
                draft_id=draft_id,
                action=action,
                token=token,
            )
        ),
        action_page_html=lambda draft, action, token: _lark_bot_badcase_action_page_html(
            draft=draft,
            action=action,
            token=token,
        ),
        spreadsheet_writeback_page_html=lambda draft, token: _lark_bot_badcase_writeback_page_html(
            draft=draft, token=token
        ),
        base_writeback_page_html=lambda draft, token: _lark_bot_badcase_base_writeback_page_html(
            draft=draft, token=token
        ),
        write_spreadsheet=lambda draft: _write_lark_bot_badcase_result_to_spreadsheet(draft=draft),
        write_base=lambda draft: _write_lark_bot_badcase_result_to_base(draft=draft),
        action_result_html=lambda title, lines: _lark_bot_badcase_action_result_html(
            title=title, lines=lines
        ),
        http_exception_detail_text=lambda detail: _http_exception_detail_text(detail),
        confirm_badcase_draft=lambda draft_id, request: confirm_lark_bot_badcase_draft(
            draft_id, request
        ),
        cancel_badcase_draft=lambda draft_id, request: cancel_lark_bot_badcase_draft(
            draft_id, request
        ),
        completion_delivery_failure_state=lambda text: _lark_bot_completion_delivery_failure_state(
            text
        ),
        completion_delivery_failure_message=lambda **kwargs: (
            _lark_bot_completion_delivery_failure_message(**kwargs)
        ),
    )
    lark_completion_delivery_controller = LarkCompletionDeliveryController(
        settings=lambda: settings,
        job_repository=lambda: job_repository,
        build_report=lambda job_id: build_report_for_job(job_repository, job_id),
        build_targeted_probe_results=lambda job_id: build_targeted_probe_results(
            job_repository, job_id
        ),
        report_document_connector=lambda actor: _lark_report_document_connector(actor=actor),
        report_doc_identity=lambda: _lark_report_doc_identity(),
        reply_target_type=lambda draft: _lark_bot_reply_target_type(draft),
        stable_completion_idempotency_key=lambda draft_id, job_id: (
            _stable_lark_completion_idempotency_key(draft_id=draft_id, job_id=job_id)
        ),
        spreadsheet_writeback_target=lambda job_id: _spreadsheet_writeback_target_for_job(job_id),
        base_writeback_target=lambda job_id: _base_writeback_target_for_job(job_id),
        badcase_action_url=lambda draft, action: _lark_bot_badcase_action_url(
            draft=draft,
            action=action,
        ),
        should_auto_close_completed_job=lambda job: _should_auto_close_completed_job(
            repository=job_repository,
            job=job,
        ),
        original_cot_excerpt=lambda case: _original_cot_excerpt(case),
        original_prediction=lambda case: _original_prediction(case),
    )
    xiaod_spreadsheet_writeback_decision_controller = XiaoDSpreadsheetWritebackDecisionController(
        job_repository=lambda: job_repository,
        spreadsheet_writeback_client=lambda: spreadsheet_writeback_client,
        build_report=lambda job_id: build_report_for_job(job_repository, job_id),
        reply_target_type=lambda command: pending_command_controller.reply_target_type(command),
    )
    lark_card_action_controller = LarkCardActionController(
        confirm_pending_command=lambda command_id, request: (
            pending_command_lifecycle_controller.confirm(command_id, request)
        ),
        cancel_pending_command=lambda command_id, request: (
            pending_command_lifecycle_controller.cancel(command_id, request)
        ),
        retain_pending_command=lambda command_id, request: (
            pending_command_lifecycle_controller.retain(command_id, request)
        ),
        delete_pending_command=lambda command_id, request: (
            pending_command_lifecycle_controller.delete(command_id, request)
        ),
        default_delete_pending_command=lambda command_id, request: (
            pending_command_lifecycle_controller.default_delete(command_id, request)
        ),
        pending_command_for_lifecycle_action=lambda command_id: (
            _pending_command_for_lifecycle_action(command_id)
        ),
        assert_pending_command_actor=lambda command, actor: _assert_lark_bot_pending_command_actor(
            command,
            actor,
        ),
        create_pending_command_cleanup_decision=lambda command: (
            pending_command_controller.create_cleanup_decision(command)
        ),
        pending_command_action_reply=lambda command, action_kind, markdown, content: (
            pending_command_controller.action_reply(
                command=command,
                action_kind=action_kind,
                markdown=markdown,
                content=content,
            )
        ),
        pending_cleanup_decision_card=lambda command: (
            xiaod_pending_interaction_controller.pending_cleanup_decision_card(command)
        ),
        get_pending_command=lambda command_id: job_repository.get_lark_bot_pending_command(
            command_id
        ),
        get_pending_writeback_decision=lambda command: job_repository.get_pending_xiaod_decision(
            tenant_key=command.tenant_key,
            chat_id=command.chat_id,
            open_id=command.open_id,
            decision_kind="spreadsheet_rerun_writeback_sync",
        ),
        resolve_writeback_decision=lambda command, decision, actor, sync_requested, default_skip: (
            _resolve_spreadsheet_rerun_writeback_decision(
                command=command,
                decision=decision,
                actor=actor,
                sync_requested=sync_requested,
                default_skip=default_skip,
            )
        ),
        writeback_decision_markdown=lambda command, status, row_results, default_skip, completed_summary: (
            _spreadsheet_rerun_writeback_decision_markdown(
                command=command,
                status=status,
                row_results=row_results,
                default_skip=default_skip,
                completed_summary=completed_summary,
            )
        ),
        payload_dict=lambda value: _payload_dict(value),
        payload_dict_list=lambda value: _payload_dict_list(value),
        confirm_badcase_draft=lambda draft_id, request: confirm_lark_bot_badcase_draft(
            draft_id, request
        ),
        cancel_badcase_draft=lambda draft_id, request: cancel_lark_bot_badcase_draft(
            draft_id, request
        ),
        reply_target_type=lambda draft: _lark_bot_reply_target_type(draft),
        default_actor=LOCAL_DEV_OPERATOR,
        update_recommended_action_status=lambda job_id, action_index, request: (
            update_recommended_action_status(job_id, action_index, request)
        ),
        create_recommended_action_verification_job=lambda job_id, action_index, request: (
            create_recommended_action_verification_job(job_id, action_index, request)
        ),
    )
    lark_bot_event_controller = LarkBotEventController(
        event_mode=lambda: _lark_event_mode(),
        verification_token=lambda: _lark_bot_verification_token(),
        encrypt_key=lambda: _lark_bot_encrypt_key(),
        lark_cli_profile=lambda: lark_spreadsheet_settings.lark_cli_profile,
        save_audit=lambda **kwargs: _save_lark_bot_audit(**kwargs),
        handle_card_action_event=lambda payload: _handle_lark_bot_card_action_event(payload),
        preview_command=lambda request: _preview_lark_bot_command(request),
    )
    writeback_controller = WritebackController(
        job_repository=lambda: job_repository,
        configure_clients_from_request=lambda request: _configure_spreadsheet_clients_from_request(
            request
        ),
        build_report=lambda job_id: build_report_for_job(job_repository, job_id),
        spreadsheet_writeback_target=lambda job_id: _spreadsheet_writeback_target_for_job(job_id),
        base_writeback_target=lambda job_id: _base_writeback_target_for_job(job_id),
        spreadsheet_writeback_client=lambda: spreadsheet_writeback_client,
        resolved_actor=lambda actor: _resolved_actor(actor),
        base_write_connector=lambda actor: _lark_bot_base_write_connector(actor=actor),
        lark_bot_write_identity=lambda: _lark_bot_write_identity(),
        lark_spreadsheet_error=lambda exc: _lark_spreadsheet_error(exc),
    )
    pending_command_lifecycle_controller = LarkPendingCommandLifecycleController(
        job_repository=lambda: job_repository,
        resolved_actor=lambda actor: _resolved_actor(actor),
        pending_command_expired=lambda command: _lark_bot_pending_command_expired(command),
        ensure_spreadsheet_rerun_active_run=lambda command: (
            pending_command_controller.ensure_spreadsheet_rerun_active_run(command)
        ),
        start_pending_command_background=lambda command_id, actor: (
            pending_command_controller.start_background(command_id, actor=actor)
        ),
        execute_pending_command=lambda command: _execute_lark_bot_pending_command(command),
        save_audit=lambda **kwargs: _save_lark_bot_audit(**kwargs),
        http_exception_detail_text=lambda detail: _http_exception_detail_text(detail),
        active_spreadsheet_rerun_run_for_command=lambda command: (
            pending_command_controller.active_spreadsheet_rerun_run_for_command(command)
        ),
    )
    pending_command_reply_controller = LarkPendingCommandReplyController(
        job_repository=lambda: job_repository,
        resolved_actor=lambda actor: _resolved_actor(actor),
        im_connector=lambda actor, identity, profile: _lark_bot_im_connector(
            actor=actor,
            identity=identity,
            profile=profile,
        ),
        save_audit=lambda **kwargs: _save_lark_bot_audit(**kwargs),
    )
    xiaod_pending_interaction_controller = XiaoDPendingInteractionController(
        job_repository=lambda: job_repository,
        resolved_actor=lambda actor: _resolved_actor(actor),
        pending_command_expired=lambda command: _lark_bot_pending_command_expired(command),
        default_delete_pending_command=lambda command_id, request: (
            pending_command_lifecycle_controller.default_delete(command_id, request)
        ),
        confirm_pending_command=lambda command_id, request: (
            pending_command_lifecycle_controller.confirm(command_id, request)
        ),
        retain_pending_command=lambda command_id, request: (
            pending_command_lifecycle_controller.retain(command_id, request)
        ),
        delete_pending_command=lambda command_id, request: (
            pending_command_lifecycle_controller.delete(command_id, request)
        ),
        assert_pending_command_actor=lambda command, actor: _assert_lark_bot_pending_command_actor(
            command, actor
        ),
        resolve_writeback_decision=lambda **kwargs: _resolve_spreadsheet_rerun_writeback_decision(
            **kwargs
        ),
        writeback_decision_markdown=lambda **kwargs: _spreadsheet_rerun_writeback_decision_markdown(
            **kwargs
        ),
    )
    xiaod_task_panel_controller = XiaoDTaskPanelController(
        job_repository=lambda: job_repository,
        report_base_url=lambda: settings.report_base_url,
        latest_draft_for_chat=lambda chat_id, open_id: _xiaod_latest_draft_for_chat(
            chat_id=chat_id,
            open_id=open_id,
        ),
        latest_submitted_draft_for_chat=lambda chat_id, open_id: (
            _xiaod_latest_submitted_draft_for_chat(chat_id=chat_id, open_id=open_id)
        ),
        published_or_internal_report_url=lambda job_id: _published_or_internal_report_url(job_id),
        lark_bot_progress_state=lambda job: _lark_bot_progress_state(job=job),
        lark_progress_card_for_job=lambda job, progress, title: _lark_progress_card_for_job(
            job=job,
            progress=progress,
            title=title,
        ),
    )
    xiaod_action_summary_reader = XiaoDActionSummaryReader(
        report_base_url=lambda: settings.report_base_url,
        http_exception_detail_text=lambda detail: _http_exception_detail_text(detail),
        operations_readiness=lambda: operations_status_controller.get_readiness(),
        pilot_gate=lambda: operations_status_controller.get_pilot_gate(),
        observability_summary=lambda: get_observability_summary(),
        artifact_retention_status=lambda limit: artifact_route_controller.build_retention_status(
            limit=limit
        ),
        list_cases=lambda limit: case_route_controller.list_cases(limit=limit),
        worker_runtime_status=lambda: _build_worker_runtime_status(),
        count_jobs=lambda status: job_repository.count_jobs(status=status),
        performance_summary=lambda: get_performance_summary(),
        model_catalog=lambda: get_agent_model_catalog(),
        lark_preflight=lambda: lark_bot_setup_controller.get_preflight(),
        lark_go_live_gate=lambda: lark_bot_setup_controller.get_go_live_gate(),
        lark_permission_checklist=lambda: lark_bot_setup_controller.get_permission_checklist(),
        lark_scope_check=lambda: spreadsheet_route_controller.check_lark_scopes(
            service="", operation="", recent_limit=50
        ),
        lark_spreadsheet_status=lambda: spreadsheet_route_controller.get_lark_spreadsheet_status(
            check_connectivity=False,
            spreadsheet_url="",
            spreadsheet_id="",
            sheet_id="",
        ),
        lark_operation_audits=lambda limit: job_repository.list_lark_operation_audits(limit=limit),
        badcase_drafts=lambda limit: job_repository.list_lark_bot_badcase_drafts(limit=limit),
        pending_commands=lambda limit: job_repository.list_lark_bot_pending_commands(limit=limit),
        writeback_audit_summary=lambda: (
            spreadsheet_route_controller.get_spreadsheet_writeback_audit_summary()
        ),
        list_jobs=lambda limit, sort: job_read_route_controller.list_jobs(limit=limit, sort=sort),
        get_job_status=lambda job_id: job_read_route_controller.get_job_status(job_id),
        get_job_report=lambda job_id: job_read_route_controller.get_job_report(job_id),
        get_job_evidence_ledger=lambda job_id: job_read_route_controller.get_job_evidence_ledger(
            job_id
        ),
        get_job_run_stages=lambda job_id: job_read_route_controller.get_job_run_stages(job_id),
        recommended_action_statuses=lambda job_id: (
            job_action_route_controller.list_recommended_action_statuses(job_id)
        ),
        human_handoff_statuses=lambda job_id: (
            job_action_route_controller.list_human_handoff_statuses(job_id)
        ),
        strategy_followups=lambda job_id: job_action_route_controller.list_strategy_follow_up_jobs(
            job_id
        ),
        targeted_probes=lambda job_id: job_action_route_controller.list_targeted_probe_jobs(job_id),
        debug_batches=lambda limit: list_debug_batches_view(
            job_repository=job_repository,
            view_builder=debug_batch_view_builder,
            limit=limit,
        ),
        debug_batch_comparison=lambda limit: compare_debug_batches_view(
            view_builder=debug_batch_view_builder,
            batch_ids=None,
            limit=limit,
        ),
        debug_batch=lambda batch_id: get_debug_batch_view(
            view_builder=debug_batch_view_builder,
            batch_id=batch_id,
        ),
    )
    lark_progress_notification_controller = LarkProgressNotificationController(
        job_repository=lambda: job_repository,
        resolved_actor=lambda actor: _resolved_actor(actor),
        lark_cli_profile=lambda: lark_spreadsheet_settings.lark_cli_profile,
        save_audit=lambda **kwargs: _save_lark_bot_audit(**kwargs),
        completion_notification_ready=lambda job: _lark_bot_completion_notification_ready(job=job),
        reply_target_type=lambda draft: _lark_bot_reply_target_type(draft),
        progress_state=lambda job: _lark_bot_progress_state(job=job),
        progress_card=lambda job, progress: _lark_bot_progress_card(job=job, progress=progress),
        stable_progress_idempotency_key=lambda progress_key: _stable_lark_progress_idempotency_key(
            progress_key
        ),
    )
    xiaod_run_progress_notification_controller = XiaoDRunProgressNotificationController(
        job_repository=lambda: job_repository,
        report_base_url=lambda: settings.report_base_url,
    )
    lark_notification_outbox_controller = LarkNotificationOutboxController(
        job_repository=lambda: job_repository,
        sweep_expired_decisions=lambda limit: sweep_expired_xiaod_pending_decisions(limit=limit),
        list_progress_notifications=lambda limit: list_lark_bot_badcase_progress_notifications(
            limit=limit
        ),
        list_xiaod_run_notifications=lambda limit: list_xiaod_run_progress_notifications(
            limit=limit
        ),
        list_completion_notifications=lambda limit: list_lark_bot_badcase_completion_notifications(
            limit=limit
        ),
        resolved_actor=lambda actor: _resolved_actor(actor),
        lark_cli_profile=lambda: lark_spreadsheet_settings.lark_cli_profile,
        save_audit=lambda **kwargs: _save_lark_bot_audit(**kwargs),
    )
    lark_bot_setup_controller = LarkBotSetupController(
        settings=lambda: settings,
        job_repository=job_repository,
        event_mode=lambda: _lark_event_mode(),
        connector_status=lambda: _lark_bot_preflight_connector_status(),
        operations_readiness=lambda: get_operations_readiness(),
        resolved_actor=lambda actor: _resolved_actor(actor),
        verification_token=lambda: _lark_bot_verification_token(),
        encrypt_key=lambda: _lark_bot_encrypt_key(),
        lark_cli_profile=lambda: lark_spreadsheet_settings.lark_cli_profile,
        setup_item_keys=LARK_BOT_SETUP_ITEM_KEYS,
        permission_catalog=LARK_BOT_PERMISSION_CATALOG,
        permission_console_url=LARK_PERMISSION_CONSOLE_URL,
        setup_package_url=LARK_BOT_SETUP_PACKAGE_URL,
        permission_checklist_url=LARK_BOT_PERMISSION_CHECKLIST_URL,
        receive_event_type=LARK_BOT_RECEIVE_EVENT_TYPE,
        card_action_event_type=LARK_BOT_CARD_ACTION_EVENT_TYPE,
        long_connection_profile=LARK_BOT_LONG_CONNECTION_PROFILE,
    )

    runtime._bind_runtime_compat_modules()
    runtime.configure_spreadsheet_clients(lark_spreadsheet_settings)
    runtime._bind_runtime_compat_modules()
    bind_runtime(runtime)

    job_worker = build_job_worker(
        service=job_service,
        repository=job_repository,
        writeback_client=spreadsheet_writeback_client,
        report_base_url=settings.report_base_url,
        auto_writeback_enabled=settings.auto_writeback_enabled,
        auto_closure_enabled=settings.auto_closure_enabled,
        max_concurrency=settings.queue_max_concurrency,
    )
    job_read_route_controller = JobReadRouteController(
        job_repository=job_repository,
        job_service=job_service,
        job_worker=lambda: runtime.job_worker,
        build_worker_runtime_status=lambda: _build_worker_runtime_status(),
        build_job_status=lambda job: _build_job_status(job),
        evidence_ledger_record=lambda **kwargs: _evidence_ledger_record(**kwargs),
    )
    job_action_route_controller = JobActionRouteController(
        job_repository=job_repository,
        job_service=lambda: job_service,
        spreadsheet_writeback_client=lambda: spreadsheet_writeback_client,
        resolved_actor=lambda actor: _resolved_actor(actor),
        raise_if_usage_budget_blocks_submission=lambda: _raise_if_usage_budget_blocks_submission(),
        video_clipper_for_job=lambda job_id: _video_clipper_for_job(job_id),
        save_auto_closure_run_stages=lambda **kwargs: _save_auto_closure_run_stages(**kwargs),
        persist_auto_closure_markdown_report=lambda **kwargs: _persist_auto_closure_markdown_report(
            **kwargs
        ),
        original_cot_excerpt=lambda case: _original_cot_excerpt(case),
        original_prediction=lambda case: _original_prediction(case),
    )
    knowledge_base = default_knowledge_base(database_url=settings.database_url)
    project_assistant = ProjectAssistant(knowledge_base)
    xiaod_semantic_brain = XiaoDSemanticBrain(knowledge_base)
    xiaod_turn_adapter = XiaoDTurnAdapterController(
        report_base_url=lambda: settings.report_base_url,
        job_repository=lambda: job_repository,
        project_assistant=lambda: runtime.project_assistant,
        semantic_brain=lambda: runtime.xiaod_semantic_brain,
        resolved_actor=lambda actor: _resolved_actor(actor),
        save_badcase_draft_from_request=lambda **kwargs: _save_lark_bot_badcase_draft_from_request(
            **kwargs
        ),
        input_source_is_missing_placeholder=lambda value: (
            _badcase_input_source_is_missing_placeholder(value)
        ),
        confirm_badcase_draft=lambda draft_id, request: confirm_lark_bot_badcase_draft(
            draft_id, request
        ),
        cancel_badcase_draft=lambda draft_id, request: cancel_lark_bot_badcase_draft(
            draft_id, request
        ),
        confirmation_card_payload=lambda draft, dry_run: (
            _lark_bot_badcase_confirmation_card_payload(
                draft=draft,
                dry_run=dry_run,
            )
        ),
        preview_backend_command=lambda request: _preview_lark_bot_command(request),
        create_pending_command=lambda preview, note: _create_xiaod_pending_command(
            preview=preview,
            note=note,
        ),
        active_pending_command=lambda request: (
            xiaod_pending_interaction_controller.active_pending_command(request)
        ),
        continue_pending_command=lambda pending, request: (
            xiaod_pending_interaction_controller.continue_pending_command_payload(pending, request)
        ),
        decline_pending_command=lambda pending, request: (
            xiaod_pending_interaction_controller.decline_pending_command_payload(pending, request)
        ),
        retain_pending_command=lambda pending, request: (
            xiaod_pending_interaction_controller.retain_pending_command_payload(pending, request)
        ),
        delete_pending_command=lambda pending, request: (
            xiaod_pending_interaction_controller.delete_pending_command_payload(pending, request)
        ),
        read_action_summary=lambda action: xiaod_action_summary_reader.read(action=action),
        current_progress_payload=lambda request: (
            xiaod_task_panel_controller.current_progress_payload(request)
        ),
        recent_tasks_payload=lambda request: xiaod_task_panel_controller.recent_tasks_payload(
            request
        ),
        current_job_control_payload=lambda request, operation: (
            xiaod_task_panel_controller.current_job_control_payload(request, operation)
        ),
        spreadsheet_rerun_writeback_decision=lambda request, sync_requested: (
            xiaod_pending_interaction_controller.spreadsheet_rerun_writeback_decision_payload(
                request, sync_requested
            )
        ),
        pending_spreadsheet_rerun_writeback_decision=lambda request: (
            xiaod_pending_interaction_controller.pending_spreadsheet_rerun_writeback_decision(
                request
            )
        ),
        http_exception_detail_text=lambda detail: _http_exception_detail_text(detail),
    )

    setattr(runtime, "LOCAL_DEV_OPERATOR", LOCAL_DEV_OPERATOR)
    setattr(runtime, "LarkBotBadcaseAction", LarkBotBadcaseAction)
    setattr(runtime, "LarkBotEventMode", LarkBotEventMode)
    setattr(runtime, "artifact_route_controller", artifact_route_controller)
    setattr(runtime, "auto_closure_report_controller", auto_closure_report_controller)
    setattr(runtime, "debug_job_export_controller", debug_job_export_controller)
    setattr(runtime, "job_action_route_controller", job_action_route_controller)
    setattr(runtime, "job_read_route_controller", job_read_route_controller)
    setattr(runtime, "job_worker", job_worker)
    setattr(runtime, "lark_badcase_action_controller", lark_badcase_action_controller)
    setattr(runtime, "lark_badcase_draft_intake_controller", lark_badcase_draft_intake_controller)
    setattr(runtime, "lark_badcase_link_context_resolver", lark_badcase_link_context_resolver)
    setattr(runtime, "lark_badcase_renderer", lark_badcase_renderer)
    setattr(runtime, "lark_badcase_submission_controller", lark_badcase_submission_controller)
    setattr(runtime, "lark_bot_event_controller", lark_bot_event_controller)
    setattr(runtime, "lark_bot_setup_controller", lark_bot_setup_controller)
    setattr(runtime, "lark_bot_setup_package_builder", lark_bot_setup_package_builder)
    setattr(runtime, "lark_card_action_controller", lark_card_action_controller)
    setattr(runtime, "lark_completion_delivery_controller", lark_completion_delivery_controller)
    setattr(runtime, "lark_notification_outbox_controller", lark_notification_outbox_controller)
    setattr(runtime, "lark_progress_controller", lark_progress_controller)
    setattr(runtime, "lark_progress_notification_controller", lark_progress_notification_controller)
    setattr(runtime, "observability_controller", observability_controller)
    setattr(runtime, "operations_export_controller", operations_export_controller)
    setattr(runtime, "operations_status_controller", operations_status_controller)
    setattr(runtime, "pending_command_controller", pending_command_controller)
    setattr(runtime, "pending_command_execution_controller", pending_command_execution_controller)
    setattr(runtime, "pending_command_lifecycle_controller", pending_command_lifecycle_controller)
    setattr(runtime, "pending_command_reply_controller", pending_command_reply_controller)
    setattr(runtime, "project_assistant", project_assistant)
    setattr(
        runtime, "spreadsheet_rerun_preflight_controller", spreadsheet_rerun_preflight_controller
    )
    setattr(runtime, "spreadsheet_route_controller", spreadsheet_route_controller)
    setattr(runtime, "writeback_controller", writeback_controller)
    setattr(runtime, "xiaod_action_summary_reader", xiaod_action_summary_reader)
    setattr(runtime, "xiaod_pending_interaction_controller", xiaod_pending_interaction_controller)
    setattr(
        runtime,
        "xiaod_run_progress_notification_controller",
        xiaod_run_progress_notification_controller,
    )
    setattr(runtime, "xiaod_semantic_brain", xiaod_semantic_brain)
    setattr(
        runtime,
        "xiaod_spreadsheet_writeback_decision_controller",
        xiaod_spreadsheet_writeback_decision_controller,
    )
    setattr(runtime, "xiaod_task_panel_controller", xiaod_task_panel_controller)
    setattr(runtime, "xiaod_turn_adapter", xiaod_turn_adapter)
