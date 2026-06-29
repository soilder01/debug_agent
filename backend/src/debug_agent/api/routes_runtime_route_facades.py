from __future__ import annotations

# ruff: noqa: F821

from types import ModuleType

_RUNTIME: ModuleType | None = None
EXPORTED_NAMES: tuple[str, ...] = (
    "get_operations_readiness",
    "get_lark_bot_permission_checklist",
    "get_lark_bot_preflight",
    "get_lark_bot_go_live_gate",
    "list_lark_bot_setup_acknowledgements",
    "acknowledge_lark_bot_setup_item",
    "get_artifact_retention_status",
    "cleanup_artifact_retention",
    "get_pilot_gate",
    "list_cases",
    "get_case_detail",
    "debug_case",
    "submit_debug_job",
    "sync_spreadsheet",
    "rerun_spreadsheet",
    "run_next_job",
    "list_jobs",
    "export_debug_jobs",
    "export_operations_support_bundle",
    "export_lark_bot_setup_package",
    "get_job_evidence",
    "get_worker_status",
    "start_worker",
    "stop_worker",
    "get_job_spreadsheet_writeback_audit",
    "get_job_action_queue",
    "get_job_run_view",
    "get_job_status",
    "get_job_run_stages",
    "get_job_evidence_ledger",
    "get_job_report",
    "_spreadsheet_writeback_target_for_job",
    "_base_writeback_target_for_job",
    "_lark_bot_badcase_draft_for_job",
    "update_recommended_action_status",
    "create_recommended_action_verification_job",
    "create_strategy_follow_up_job",
    "create_final_attribution_verification_job",
    "create_final_attribution_recovery_job",
    "create_final_attribution_reinvestigation_job",
    "list_strategy_follow_up_jobs",
    "create_targeted_probe_job",
    "list_targeted_probe_jobs",
    "run_job_auto_debug_closure",
    "run_job_auto_debug_closure_report",
    "update_human_handoff_status",
    "list_human_handoff_statuses",
    "list_recommended_action_statuses",
    "create_job_report_writeback_confirmation",
    "create_job_report_base_writeback_confirmation",
    "confirm_lark_write_confirmation",
    "write_job_report_to_spreadsheet",
    "write_job_report_to_base_record",
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


def get_operations_readiness() -> ProductionReadinessResponse:
    return operations_status_controller.get_readiness()


def get_lark_bot_permission_checklist() -> LarkBotPermissionChecklistResponse:
    return lark_bot_setup_controller.get_permission_checklist()


def get_lark_bot_preflight() -> LarkBotPreflightResponse:
    return lark_bot_setup_controller.get_preflight()


def get_lark_bot_go_live_gate() -> LarkBotGoLiveGateResponse:
    return lark_bot_setup_controller.get_go_live_gate()


def list_lark_bot_setup_acknowledgements(
    item_key: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> LarkBotSetupAcknowledgementListResponse:
    return lark_bot_setup_controller.list_setup_acknowledgements(
        item_key=item_key, limit=limit, offset=offset
    )


def acknowledge_lark_bot_setup_item(
    item_key: str,
    request: LarkBotSetupAcknowledgementRequest,
) -> LarkBotSetupAcknowledgement:
    return lark_bot_setup_controller.acknowledge_setup_item(item_key, request)


def get_artifact_retention_status(
    limit: int = 20,
) -> ArtifactRetentionStatus:
    return artifact_route_controller.build_retention_status(limit=limit)


def cleanup_artifact_retention(
    request: ArtifactRetentionCleanupRequest,
) -> ArtifactRetentionCleanupResponse:
    return artifact_route_controller.cleanup_retention(request)


def get_pilot_gate(
    limit: int = 5,
    min_completed_jobs: int = 20,
    min_success_rate: float = 0.8,
    max_p95_duration_ms: int = 12_000,
    max_estimated_cost_units: float | None = None,
    max_model_call_errors: int = 0,
    max_writeback_failed: int = 0,
    max_lark_operation_failures: int = 0,
) -> PilotGateResponse:
    return operations_status_controller.get_pilot_gate(
        limit=limit,
        min_completed_jobs=min_completed_jobs,
        min_success_rate=min_success_rate,
        max_p95_duration_ms=max_p95_duration_ms,
        max_estimated_cost_units=max_estimated_cost_units,
        max_model_call_errors=max_model_call_errors,
        max_writeback_failed=max_writeback_failed,
        max_lark_operation_failures=max_lark_operation_failures,
    )


def list_cases(
    has_regions: bool = False, limit: int | None = None, offset: int = 0
) -> DebugCaseListResponse:
    return case_route_controller.list_cases(has_regions=has_regions, limit=limit, offset=offset)


def get_case_detail(case_id: str) -> DebugCase:
    return case_route_controller.get_case_detail(case_id)


async def debug_case(case_id: str) -> DebugReport:
    return await case_route_controller.debug_case(case_id)


async def submit_debug_job(
    case_id: str,
    auto_run: bool = False,
    baseline_trials: int = 0,
) -> SubmittedDebugJob:
    return await case_route_controller.submit_debug_job(
        case_id=case_id,
        auto_run=auto_run,
        baseline_trials=baseline_trials,
    )


def sync_spreadsheet(request: SpreadsheetSyncRequest) -> SpreadsheetSyncResult:
    return spreadsheet_route_controller.sync_spreadsheet(request)


async def rerun_spreadsheet(request: SpreadsheetRerunRequest) -> SpreadsheetRerunApiResult:
    return await spreadsheet_route_controller.rerun_spreadsheet(request)


async def run_next_job() -> SubmittedDebugJob | None:
    return await job_read_route_controller.run_next_job()


def list_jobs(
    status: str | None = None,
    limit: int | None = None,
    offset: int = 0,
    sort: Literal["created_at_asc", "created_at_desc"] = "created_at_asc",
) -> DebugJobListResponse:
    return job_read_route_controller.list_jobs(status=status, limit=limit, offset=offset, sort=sort)


def export_debug_jobs(
    job_ids: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    sort: Literal["created_at_asc", "created_at_desc"] = "created_at_desc",
) -> Response:
    return debug_job_export_controller.export_debug_jobs(
        job_ids=job_ids, status=status, limit=limit, offset=offset, sort=sort
    )


def export_operations_support_bundle(
    audit_limit: int = 100,
) -> Response:
    return operations_export_controller.export_support_bundle(audit_limit=audit_limit)


def export_lark_bot_setup_package() -> Response:
    return lark_bot_setup_package_builder.export_package()


def get_job_evidence(job_id: str, evidence_id: str) -> ExperimentEvidence:
    return job_read_route_controller.get_job_evidence(job_id, evidence_id)


def get_worker_status() -> WorkerRuntimeStatus:
    return job_read_route_controller.get_worker_status()


async def start_worker() -> WorkerRuntimeStatus:
    return await job_read_route_controller.start_worker()


async def stop_worker() -> WorkerRuntimeStatus:
    return await job_read_route_controller.stop_worker()


def get_job_spreadsheet_writeback_audit(job_id: str) -> SpreadsheetWritebackAudit:
    return job_read_route_controller.get_job_spreadsheet_writeback_audit(job_id)


def get_job_action_queue(job_id: str) -> ActionQueueResponse:
    return job_read_route_controller.get_job_action_queue(job_id)


def get_job_run_view(job_id: str) -> DebugRunView:
    return job_read_route_controller.get_job_run_view(job_id)


def get_job_status(job_id: str) -> DebugJobStatus:
    return job_read_route_controller.get_job_status(job_id)


def get_job_run_stages(job_id: str) -> DebugRunStageListResponse:
    return job_read_route_controller.get_job_run_stages(job_id)


def get_job_evidence_ledger(job_id: str) -> EvidenceLedgerResponse:
    return job_read_route_controller.get_job_evidence_ledger(job_id)


def get_job_report(job_id: str) -> DebugReport:
    return job_read_route_controller.get_job_report(job_id)


def _spreadsheet_writeback_target_for_job(job_id: str) -> tuple[str, str, str] | None:
    mapping = job_repository.get_spreadsheet_row_mapping_by_job_id(job_id)
    if mapping is not None:
        return mapping.spreadsheet_id, mapping.sheet_id, mapping.row_id

    existing_audit = job_repository.get_spreadsheet_writeback_audit(job_id)
    reference = lark_spreadsheet_settings.reference
    job = job_repository.get_job(job_id)
    if existing_audit is None or not existing_audit.row_id or reference is None or job is None:
        return None

    job_repository.save_spreadsheet_row_mapping(
        spreadsheet_id=reference.spreadsheet_id,
        sheet_id=reference.sheet_id,
        row_id=existing_audit.row_id,
        case_id=job.case_id,
        job_id=job_id,
    )
    return reference.spreadsheet_id, reference.sheet_id, existing_audit.row_id


def _base_writeback_target_for_job(job_id: str) -> tuple[str, str, str] | None:
    draft = _lark_bot_badcase_draft_for_job(job_id)
    if draft is None:
        return None
    mapping = _lark_bot_badcase_base_mapping(draft=draft)
    if mapping is None:
        return None
    job = job_repository.get_job(job_id)
    if job is not None:
        base_token, table_id, record_id = mapping
        job_repository.save_spreadsheet_row_mapping(
            spreadsheet_id=base_token,
            sheet_id=table_id,
            row_id=record_id,
            case_id=job.case_id,
            job_id=job_id,
        )
    return mapping


def _lark_bot_badcase_draft_for_job(job_id: str) -> LarkBotBadcaseDraft | None:
    for draft in job_repository.list_lark_bot_badcase_drafts(limit=200):
        if draft.submitted_job_id == job_id:
            return draft
    return None


def update_recommended_action_status(
    job_id: str,
    action_index: int,
    request: RecommendedActionStatusRequest,
) -> RecommendedActionStatus:
    return job_action_route_controller.update_recommended_action_status(
        job_id=job_id,
        action_index=action_index,
        request=request,
    )


def create_recommended_action_verification_job(
    job_id: str,
    action_index: int,
    request: RecommendedActionVerificationRequest,
) -> RecommendedActionVerificationResponse:
    return job_action_route_controller.create_recommended_action_verification_job(
        job_id=job_id,
        action_index=action_index,
        request=request,
    )


def create_strategy_follow_up_job(
    job_id: str,
    stage: str,
    request: StrategyFollowUpJobRequest,
) -> StrategyFollowUpJobResponse:
    return job_action_route_controller.create_strategy_follow_up_job(
        job_id=job_id,
        stage=stage,
        request=request,
    )


def create_final_attribution_verification_job(
    job_id: str,
    target_id: str,
    request: StrategyFollowUpJobRequest,
) -> StrategyFollowUpJobResponse:
    return job_action_route_controller.create_final_attribution_verification_job(
        job_id=job_id,
        target_id=target_id,
        request=request,
    )


def create_final_attribution_recovery_job(
    job_id: str,
    target_id: str,
    request: StrategyFollowUpJobRequest,
) -> StrategyFollowUpJobResponse:
    return job_action_route_controller.create_final_attribution_recovery_job(
        job_id=job_id,
        target_id=target_id,
        request=request,
    )


def create_final_attribution_reinvestigation_job(
    job_id: str,
    target_id: str,
    request: StrategyFollowUpJobRequest,
) -> StrategyFollowUpJobResponse:
    return job_action_route_controller.create_final_attribution_reinvestigation_job(
        job_id=job_id,
        target_id=target_id,
        request=request,
    )


def list_strategy_follow_up_jobs(job_id: str) -> StrategyFollowUpJobListResponse:
    return job_action_route_controller.list_strategy_follow_up_jobs(job_id)


def create_targeted_probe_job(
    job_id: str,
    target_id: str,
    request: TargetedProbeJobRequest,
) -> TargetedProbeJobResponse:
    return job_action_route_controller.create_targeted_probe_job(
        job_id=job_id,
        target_id=target_id,
        request=request,
    )


def list_targeted_probe_jobs(job_id: str) -> TargetedProbeJobListResponse:
    return job_action_route_controller.list_targeted_probe_jobs(job_id)


async def run_job_auto_debug_closure(
    job_id: str,
    request: AutoDebugClosureRequest,
) -> AutoDebugClosureResult:
    return await job_action_route_controller.run_job_auto_debug_closure(
        job_id=job_id,
        request=request,
    )


async def run_job_auto_debug_closure_report(
    job_id: str,
    request: AutoDebugClosureRequest,
) -> AutoDebugClosureReportResponse:
    return await job_action_route_controller.run_job_auto_debug_closure_report(
        job_id=job_id,
        request=request,
    )


def update_human_handoff_status(
    job_id: str,
    target_id: str,
    request: HumanHandoffStatusRequest,
) -> HumanHandoffStatus:
    return job_action_route_controller.update_human_handoff_status(
        job_id=job_id,
        target_id=target_id,
        request=request,
    )


def list_human_handoff_statuses(job_id: str) -> HumanHandoffStatusListResponse:
    return job_action_route_controller.list_human_handoff_statuses(job_id)


def list_recommended_action_statuses(job_id: str) -> RecommendedActionStatusListResponse:
    return job_action_route_controller.list_recommended_action_statuses(job_id)


def create_job_report_writeback_confirmation(
    job_id: str,
    request: JobReportWritebackConfirmationRequest,
) -> LarkWriteConfirmation:
    return writeback_controller.create_spreadsheet_confirmation(job_id, request)


def create_job_report_base_writeback_confirmation(
    job_id: str,
    request: JobReportBaseWritebackConfirmationRequest,
) -> LarkWriteConfirmation:
    return writeback_controller.create_base_confirmation(job_id, request)


def confirm_lark_write_confirmation(
    confirmation_id: str,
    request: LarkWriteConfirmationConfirmRequest,
) -> LarkWriteConfirmation:
    return writeback_controller.confirm_lark_write(confirmation_id, request)


def write_job_report_to_spreadsheet(
    job_id: str, request: JobReportWritebackRequest
) -> SpreadsheetWritebackResult:
    return writeback_controller.write_spreadsheet(job_id, request)


def write_job_report_to_base_record(
    job_id: str,
    request: JobReportBaseWritebackRequest,
) -> BaseWritebackResult:
    return writeback_controller.write_base(job_id, request)
