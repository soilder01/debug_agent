from __future__ import annotations

# ruff: noqa: F821

from types import ModuleType

_RUNTIME: ModuleType | None = None
EXPORTED_NAMES: tuple[str, ...] = (
    "_build_job_status",
    "_recover_stale_running_jobs",
    "_build_worker_runtime_status",
    "_lark_event_mode",
    "_lark_bot_preflight_connector_status",
    "_lark_bot_verification_token",
    "_lark_bot_encrypt_key",
    "_lark_bot_webhook_token_readiness_status",
    "_lark_bot_encrypt_key_readiness_status",
    "_database_kind",
    "_database_path",
    "_sqlite_database_path",
    "_redacted_database_url",
    "_build_usage_summary",
    "_raise_if_usage_budget_blocks_submission",
    "_configure_spreadsheet_clients_from_request",
    "_spreadsheet_settings_from_request",
    "_lark_client_for_settings",
    "_lark_connector_status_for_client",
    "_evidence_ledger_record",
    "_enhanced_constraints_from_request_summary",
    "_persist_auto_closure_markdown_report",
    "_run_spreadsheet_rerun_auto_closures",
    "_save_auto_closure_run_stages",
    "_save_auto_closure_status_stage",
    "_new_artifact_group_id",
    "_artifact_dir_for_job_id",
    "_video_clipper_for_job",
    "_original_prediction",
    "_original_cot_excerpt",
    "_lark_spreadsheet_error",
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


def _build_job_status(job: DebugJobRow) -> DebugJobStatus:
    retry_status = job_service.retry_status(attempt_count=job.attempt_count, status=job.status)
    evidence_error_counts = job_repository.count_evidence_errors(job.job_id)
    retry_recommendation = job_service.retry_recommendation(
        status=job.status,
        attempt_count=job.attempt_count,
        evidence_error_counts=evidence_error_counts,
    )
    writeback_audit = job_repository.get_spreadsheet_writeback_audit(job.job_id)
    return DebugJobStatus(
        job_id=job.job_id,
        case_id=job.case_id,
        artifact_group_id=job.artifact_group_id,
        status=job.status,
        created_at=job.created_at,
        updated_at=job.updated_at,
        attempt_count=job.attempt_count,
        max_attempts=retry_status.max_attempts,
        remaining_attempts=retry_status.remaining_attempts,
        will_retry=retry_status.will_retry,
        retry_recommendation=retry_recommendation,
        retry_recommendation_detail=job_service.retry_recommendation_detail(retry_recommendation),
        error_message=job.error_message,
        evidence_ids=job_repository.list_evidence_ids(job.job_id),
        evidence_error_counts=evidence_error_counts,
        spreadsheet_writeback_audit=(
            SpreadsheetWritebackAuditSummary(
                status=writeback_audit.status,
                row_id=writeback_audit.row_id,
                report_url=writeback_audit.report_url,
                error_message=writeback_audit.error_message,
                updated_at=writeback_audit.updated_at,
            )
            if writeback_audit is not None
            else None
        ),
    )


def _recover_stale_running_jobs() -> list[str]:
    cutoff = datetime.now(UTC) - timedelta(seconds=settings.stale_running_job_seconds)
    return job_repository.recover_stale_running_jobs(
        stale_before=cutoff.isoformat(timespec="microseconds")
    )


def _build_worker_runtime_status() -> WorkerRuntimeStatus:
    status = job_worker.status()
    return WorkerRuntimeStatus(
        **status.model_dump(),
        report_base_url=settings.report_base_url,
        auto_writeback_enabled=settings.auto_writeback_enabled,
    )


def _lark_event_mode() -> LarkBotEventMode:
    mode = getattr(settings, "lark_event_mode", "long_connection")
    if mode == "long_connection":
        return "long_connection"
    if mode == "webhook":
        return "webhook"
    return "long_connection"


def _lark_bot_preflight_connector_status() -> LarkConnectorStatus:
    identity = lark_spreadsheet_settings.lark_cli_identity
    if identity not in {"bot", "user", "unknown"}:
        identity = "unknown"
    resolved_identity = cast(Literal["bot", "user", "unknown"], identity)
    return LarkConnectorStatus(
        mode="cli",
        identity=resolved_identity,
        profile=lark_spreadsheet_settings.lark_cli_profile,
    )


def _lark_bot_verification_token() -> str:
    token = settings.lark_bot_verification_token
    return token.get_secret_value() if token is not None else ""


def _lark_bot_encrypt_key() -> str:
    encrypt_key = settings.lark_bot_encrypt_key
    return encrypt_key.get_secret_value() if encrypt_key is not None else ""


def _lark_bot_webhook_token_readiness_status() -> Literal["ok", "warning", "critical"]:
    if _lark_event_mode() == "long_connection":
        return "ok"
    if _lark_bot_verification_token():
        return "ok"
    return "warning" if settings.environment == "local" else "critical"


def _lark_bot_encrypt_key_readiness_status() -> Literal["ok", "warning", "critical"]:
    if _lark_event_mode() == "long_connection":
        return "ok"
    if _lark_bot_encrypt_key():
        return "ok"
    return "warning" if settings.environment == "local" else "critical"


def _database_kind(database_url: str) -> str:
    parsed = urlparse(database_url)
    if parsed.scheme.startswith("sqlite"):
        return "sqlite"
    return parsed.scheme or "unknown"


def _database_path(database_url: str) -> str:
    path = _sqlite_database_path(database_url)
    return str(path) if path is not None else ""


def _sqlite_database_path(database_url: str) -> Path | None:
    if database_url.endswith(":memory:") or not database_url.startswith("sqlite"):
        return None
    parsed = urlparse(database_url)
    path_text = unquote(parsed.path)
    if len(path_text) >= 3 and path_text[0] == "/" and path_text[2] == ":":
        path_text = path_text[1:]
    return Path(path_text) if path_text else None


def _redacted_database_url(database_url: str) -> str:
    parsed = urlparse(database_url)
    if parsed.scheme.startswith("sqlite"):
        return database_url
    if parsed.scheme:
        return f"{parsed.scheme}://<redacted>"
    return "<configured>" if database_url else ""


def _build_usage_summary(
    raw_usage: dict[str, int | float],
    *,
    budget_units: float,
    budget_enforcement_enabled: bool,
) -> ObservabilityUsageSummary:
    return observability_controller.build_usage_summary(
        raw_usage,
        budget_units=budget_units,
        budget_enforcement_enabled=budget_enforcement_enabled,
    )


def _raise_if_usage_budget_blocks_submission() -> None:
    if not settings.enforce_usage_budget:
        return
    usage = _build_usage_summary(
        job_repository.summarize_usage(),
        budget_units=settings.usage_budget_units,
        budget_enforcement_enabled=settings.enforce_usage_budget,
    )
    if usage.budget_status == "over_budget":
        raise HTTPException(
            status_code=429, detail="Usage budget exceeded; new debug jobs are disabled."
        )


def _configure_spreadsheet_clients_from_request(
    request: (
        SpreadsheetSyncRequest
        | SpreadsheetRerunRequest
        | JobReportWritebackConfirmationRequest
        | JobReportWritebackRequest
    ),
) -> None:
    if not request.spreadsheet_url.strip():
        return
    if spreadsheet_sync_client is not None and not isinstance(
        spreadsheet_sync_client, LarkSpreadsheetClient
    ):
        return
    request_settings = _spreadsheet_settings_from_request(
        spreadsheet_url=request.spreadsheet_url,
        spreadsheet_id=request.spreadsheet_id,
        sheet_id=request.sheet_id,
    )
    if request_settings is not None:
        configure_spreadsheet_clients(request_settings)


def _spreadsheet_settings_from_request(
    *,
    spreadsheet_url: str,
    spreadsheet_id: str,
    sheet_id: str,
) -> LarkSpreadsheetSettings | None:
    if not spreadsheet_url.strip() and not spreadsheet_id.strip():
        return None
    source = spreadsheet_url.strip() or spreadsheet_id.strip()
    try:
        reference = parse_lark_spreadsheet_reference(source, sheet_id=sheet_id.strip() or None)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return LarkSpreadsheetSettings(
        spreadsheet_url=spreadsheet_url.strip(),
        sheet_id=sheet_id.strip(),
        lark_cli_timeout_seconds=lark_spreadsheet_settings.lark_cli_timeout_seconds,
        lark_cli_profile=lark_spreadsheet_settings.lark_cli_profile,
        lark_cli_identity=lark_spreadsheet_settings.lark_cli_identity,
        reference=reference,
    )


def _lark_client_for_settings(
    lark_settings: LarkSpreadsheetSettings | None,
) -> SpreadsheetClient | None:
    if lark_settings is None or lark_settings.reference is None:
        return None
    return LarkSpreadsheetClient(
        LarkCliSheetsTransport(
            timeout_seconds=lark_settings.lark_cli_timeout_seconds,
            profile=lark_settings.lark_cli_profile,
            identity=lark_settings.lark_cli_identity,
            audit_sink=_record_lark_connector_audit,
        )
    )


def _lark_connector_status_for_client(client: SpreadsheetClient | None) -> LarkConnectorStatus:
    status_provider = getattr(client, "connector_status", None)
    if callable(status_provider):
        return status_provider()
    return LarkConnectorStatus()


def _evidence_ledger_record(*, job_id: str, evidence: ExperimentEvidence) -> EvidenceLedgerRecord:
    return EvidenceLedgerRecord(
        job_id=job_id,
        evidence_id=evidence.evidence_id,
        step_name=evidence.step_name,
        prompt=dict(evidence.request_summary),
        enhanced_constraints=_enhanced_constraints_from_request_summary(evidence.request_summary),
        raw_output=evidence.raw_output,
        parsed_result={
            "response_parse_error": evidence.response_parse_error,
            "model_call_error_type": evidence.model_call_error_type,
            "model_call_error_message": evidence.model_call_error_message,
        },
        judge_version="debug-agent-judge-v1",
        score_delta={
            "score": evidence.judge.score,
            "reasons": evidence.judge.reasons,
            "deltas": evidence.judge.deltas,
        },
        artifact_links=[artifact.model_dump() for artifact in evidence.artifacts],
    )


def _enhanced_constraints_from_request_summary(
    request_summary: dict[str, object],
) -> dict[str, object]:
    constraint_keys = {
        "ablation_variant",
        "ablation_modalities",
        "target_id",
        "probe_window",
        "prompt_variant",
    }
    return {key: value for key, value in request_summary.items() if key in constraint_keys}


def _persist_auto_closure_markdown_report(*, job_id: str, case_id: str, markdown: str) -> str:
    return auto_closure_report_controller.persist_markdown_report(
        job_id=job_id,
        case_id=case_id,
        markdown=markdown,
    )


async def _run_spreadsheet_rerun_auto_closures(
    *,
    jobs: list[SubmittedDebugJob],
    writeback_requested: bool,
    submit_controlled_probes: bool = False,
) -> list[SpreadsheetRerunAutoClosureReport]:
    return await auto_closure_report_controller.run_spreadsheet_rerun_auto_closures(
        jobs=jobs,
        writeback_requested=writeback_requested,
        submit_controlled_probes=submit_controlled_probes,
    )


def _save_auto_closure_run_stages(
    *,
    repository: DebugJobRepository,
    job_id: str,
    closure: AutoDebugClosureResult,
) -> None:
    auto_closure_report_controller.save_run_stages(
        repository=repository,
        job_id=job_id,
        closure=closure,
    )


def _save_auto_closure_status_stage(
    *,
    repository: DebugJobRepository,
    job_id: str,
    status: str,
    output: dict[str, object],
    failure_reason: str,
) -> None:
    auto_closure_report_controller.save_status_stage(
        repository=repository,
        job_id=job_id,
        status=status,
        output=output,
        failure_reason=failure_reason,
    )


def _new_artifact_group_id(prefix: str) -> str:
    return f"{safe_path_fragment(prefix)}-{uuid4()}"


def _artifact_dir_for_job_id(job_id: str) -> Path:
    job = job_repository.get_job(job_id)
    artifact_group_id = job.artifact_group_id if job is not None else DEFAULT_ARTIFACT_GROUP
    return job_artifact_dir(
        settings.image_artifact_dir, artifact_group_id=artifact_group_id, job_id=job_id
    )


def _video_clipper_for_job(job_id: str) -> LocalVideoClipper:
    return LocalVideoClipper(
        _artifact_dir_for_job_id(job_id) / "video_clips", skip_missing_source=True
    )


def _original_prediction(case: DebugCase) -> str:
    if not case.predictions:
        return ""
    return case.predictions[0].raw_output


def _original_cot_excerpt(case: DebugCase) -> str:
    prediction = _original_prediction(case)
    if not prediction:
        return "未在导入样本中找到原始模型回答。"
    return "当前样本未单独保存 COT 字段；以下原始预测用于追溯原 badcase 回答：\n" + prediction


def _lark_spreadsheet_error(exc: LarkCliError) -> HTTPException:
    return HTTPException(status_code=502, detail=f"Lark spreadsheet operation failed: {exc}")
