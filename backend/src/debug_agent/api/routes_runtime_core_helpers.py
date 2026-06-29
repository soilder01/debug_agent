from __future__ import annotations

# ruff: noqa: F821

from datetime import UTC, datetime, timedelta
from types import ModuleType
from uuid import uuid4

_RUNTIME: ModuleType | None = None
EXPORTED_NAMES: tuple[str, ...] = (
    "_resolved_actor",
    "_record_lark_connector_audit",
    "build_job_worker",
    "_combined_completion_hook",
    "make_auto_closure_completion_hook",
    "_should_auto_close_completed_job",
    "_fetch_compatible_model_ids",
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


def _resolved_actor(actor: str) -> str:
    normalized_actor = actor.strip()
    if normalized_actor:
        return normalized_actor
    if settings.require_trusted_actor:
        raise HTTPException(
            status_code=400, detail="Actor is required when trusted actor enforcement is enabled."
        )
    return LOCAL_DEV_OPERATOR


def _record_lark_connector_audit(event: LarkConnectorAuditEvent) -> None:
    job_repository.save_lark_operation_audit(
        actor=LOCAL_DEV_OPERATOR,
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


def build_job_worker(
    *,
    service: DebugJobService,
    repository: DebugJobRepository,
    writeback_client: SpreadsheetWritebackClient | None,
    report_base_url: str,
    auto_writeback_enabled: bool,
    auto_closure_enabled: bool,
    max_concurrency: int | None = None,
) -> AsyncJobWorker:
    resolved_max_concurrency = max_concurrency or settings.queue_max_concurrency
    writeback_hook = (
        make_spreadsheet_writeback_completion_hook(
            repository=repository,
            client=writeback_client,
            report_base_url=report_base_url,
        )
        if writeback_client is not None and auto_writeback_enabled
        else None
    )
    auto_closure_hook = (
        make_auto_closure_completion_hook(
            repository=repository,
            service=service,
        )
        if auto_closure_enabled
        else None
    )
    return AsyncJobWorker(
        service,
        max_concurrency=resolved_max_concurrency,
        stale_running_job_seconds=settings.stale_running_job_seconds,
        on_job_completed=_combined_completion_hook(writeback_hook, auto_closure_hook),
    )


def _combined_completion_hook(*hooks: Callable[[SubmittedDebugJob], object] | None):
    active_hooks = [hook for hook in hooks if hook is not None]
    if not active_hooks:
        return None

    async def run_hooks(job: SubmittedDebugJob) -> None:
        for hook in active_hooks:
            result = hook(job)
            if inspect.isawaitable(result):
                await result

    return run_hooks


def make_auto_closure_completion_hook(
    *,
    repository: DebugJobRepository,
    service: DebugJobService,
):
    async def run_auto_closure_for_completed_job(job: SubmittedDebugJob) -> None:
        controlled_probe_source_job_id = _controlled_probe_source_job_id(
            repository=repository,
            job=job,
        )
        if controlled_probe_source_job_id:
            source_job = repository.get_job(controlled_probe_source_job_id)
            if source_job is None or source_job.status != "completed":
                return
            job = source_job
        if not _should_auto_close_completed_job(repository=repository, job=job):
            return
        retry_policy = _completion_hook_retry_policy(
            repository=repository,
            artifact_group_id=job.artifact_group_id,
        )
        _save_auto_closure_status_stage(
            repository=repository,
            job_id=job.job_id,
            status="running",
            output={},
            failure_reason="",
        )
        try:
            if _completion_hook_should_build_spreadsheet_report(retry_policy):
                report = await auto_closure_report_controller.run_report_for_completed_job(
                    job.job_id,
                    writeback_requested=_policy_bool(retry_policy, "writeback"),
                    submit_controlled_probes=_policy_bool(
                        retry_policy,
                        "submit_controlled_probes",
                    ),
                    execute_follow_up_jobs=False,
                )
                _record_xiaod_spreadsheet_report_ready(
                    repository=repository,
                    job=job,
                    report=report,
                    writeback_requested=_policy_bool(retry_policy, "writeback"),
                )
                return
            closure = await run_auto_debug_closure(
                repository=repository,
                job_service=service,
                job_id=job.job_id,
                actor="auto-debug-agent",
                writeback_client=None,
                video_clipper=_video_clipper_for_job(job.job_id),
                report_url=_internal_job_report_url(job.job_id),
                submit_controlled_probes=_completion_hook_submit_controlled_probes(
                    repository=repository,
                    artifact_group_id=job.artifact_group_id,
                ),
            )
        except Exception as exc:
            _save_auto_closure_status_stage(
                repository=repository,
                job_id=job.job_id,
                status="failed",
                output={},
                failure_reason=str(exc),
            )
            raise
        _save_auto_closure_run_stages(repository=repository, job_id=job.job_id, closure=closure)

    return run_auto_closure_for_completed_job


def _completion_hook_retry_policy(
    *,
    repository: DebugJobRepository,
    artifact_group_id: str,
) -> dict[str, object]:
    batch = repository.get_batch(artifact_group_id)
    if batch is None or not isinstance(batch.retry_policy, dict):
        return {}
    return dict(batch.retry_policy)


def _completion_hook_should_build_spreadsheet_report(policy: dict[str, object]) -> bool:
    return _string_value(policy.get("source")) == "spreadsheet_rerun" and _policy_bool(
        policy, "auto_closure"
    )


def _completion_hook_submit_controlled_probes(
    *,
    repository: DebugJobRepository,
    artifact_group_id: str,
) -> bool:
    return _policy_bool(
        _completion_hook_retry_policy(
            repository=repository,
            artifact_group_id=artifact_group_id,
        ),
        "submit_controlled_probes",
    )


def _record_xiaod_spreadsheet_report_ready(
    *,
    repository: DebugJobRepository,
    job: SubmittedDebugJob,
    report: object,
    writeback_requested: bool,
) -> None:
    batch_id = _string_value(job.artifact_group_id)
    run = _active_xiaod_spreadsheet_rerun_run_for_batch(
        repository=repository,
        batch_id=batch_id,
    )
    if run is None:
        return
    summary = dict(getattr(run, "summary", {}) or {})
    reports = _merge_report_payload(
        _dict_list(summary.get("auto_closure_reports")),
        _model_dump_dict(report),
    )
    jobs = repository.list_jobs(artifact_group_id=batch_id, limit=1000)
    if not jobs:
        job_row = repository.get_job(job.job_id)
        jobs = [job_row] if job_row is not None else []
    row_results = _spreadsheet_rerun_row_results(
        repository=repository,
        jobs=jobs,
        reports=reports,
    )
    job_ids = _unique_strings(
        [
            *_string_list(summary.get("job_ids")),
            *[_string_value(getattr(item, "job_id", "")) for item in jobs],
        ]
    )
    reports_complete = _spreadsheet_rerun_reports_complete(
        repository=repository,
        jobs=jobs,
        reports=reports,
    )
    decision_pending = writeback_requested and reports_complete
    updated_summary = {
        **summary,
        "batch_id": batch_id or _string_value(summary.get("batch_id")),
        "job_ids": job_ids,
        "row_results": row_results,
        "report_requested": True,
        "report_count": len(reports),
        "writeback_requested": writeback_requested,
        "writeback_decision_status": "pending"
        if decision_pending
        else "not_ready"
        if writeback_requested
        else "not_requested",
        "auto_closure_reports": reports,
    }
    run_id = _string_value(getattr(run, "run_id", ""))
    if run_id:
        repository.complete_xiaod_execution_run(
            run_id,
            status="writeback_decision_pending" if decision_pending else "active",
            summary=updated_summary,
        )
    if decision_pending:
        _ensure_xiaod_spreadsheet_writeback_decision(
            repository=repository,
            run=run,
            summary=updated_summary,
            row_results=row_results,
            reports=reports,
        )


def _active_xiaod_spreadsheet_rerun_run_for_batch(
    *,
    repository: DebugJobRepository,
    batch_id: str,
) -> object | None:
    for run in repository.list_xiaod_execution_runs(active_only=True, limit=500):
        if _string_value(getattr(run, "action_kind", "")) != "spreadsheet_rerun":
            continue
        summary = getattr(run, "summary", {})
        if not isinstance(summary, dict):
            summary = {}
        if _string_value(getattr(run, "batch_id", "")) == batch_id:
            return run
        if _string_value(summary.get("batch_id")) == batch_id:
            return run
    return None


def _spreadsheet_rerun_row_results(
    *,
    repository: DebugJobRepository,
    jobs: list[object],
    reports: list[dict[str, object]],
) -> list[dict[str, object]]:
    reports_by_job_id = {
        _string_value(report.get("job_id")): report
        for report in reports
        if _string_value(report.get("job_id"))
    }
    row_results: list[dict[str, object]] = []
    for job in jobs:
        job_id = _string_value(getattr(job, "job_id", ""))
        mapping = repository.get_spreadsheet_row_mapping_by_job_id(job_id) if job_id else None
        if mapping is None:
            continue
        report = reports_by_job_id.get(job_id, {})
        report_url = _spreadsheet_rerun_report_url(
            repository=repository,
            job=job,
            report=report,
        )
        row_results.append(
            {
                "row_id": mapping.row_id if mapping is not None else "",
                "case_id": _string_value(getattr(job, "case_id", "")),
                "job_id": job_id,
                "job_status": _string_value(getattr(job, "status", "")) or "unknown",
                "report_url": report_url,
                "writeback_status": _string_value(report.get("writeback_status")) or "not_ready",
                "source_mapped": mapping is not None,
                "spreadsheet_id": mapping.spreadsheet_id if mapping is not None else "",
                "sheet_id": mapping.sheet_id if mapping is not None else "",
            }
        )
    return row_results


def _spreadsheet_rerun_report_url(
    *,
    repository: DebugJobRepository,
    job: object,
    report: dict[str, object],
) -> str:
    job_id = _string_value(getattr(job, "job_id", ""))
    if not job_id:
        return _string_value(report.get("report_artifact_url"))
    document = repository.get_lark_report_document(job_id)
    if document is not None and document.status == "published" and document.document_url:
        return document.document_url
    try:
        canonical_url = _canonical_report_url_for_job(job=job, actor=LOCAL_DEV_OPERATOR)
    except Exception:
        canonical_url = ""
    return (
        canonical_url
        or _internal_job_report_url(job_id)
        or _string_value(report.get("report_artifact_url"))
    )


def _spreadsheet_rerun_reports_complete(
    *,
    repository: DebugJobRepository,
    jobs: list[object],
    reports: list[dict[str, object]],
) -> bool:
    source_jobs = [
        job
        for job in jobs
        if repository.get_spreadsheet_row_mapping_by_job_id(
            _string_value(getattr(job, "job_id", ""))
        )
        is not None
    ]
    if not source_jobs:
        return False
    reports_by_job_id = {
        _string_value(report.get("job_id"))
        for report in reports
        if _string_value(report.get("job_id"))
    }
    return all(
        _string_value(getattr(job, "status", "")) == "completed"
        and _string_value(getattr(job, "job_id", "")) in reports_by_job_id
        for job in source_jobs
    )


def _ensure_xiaod_spreadsheet_writeback_decision(
    *,
    repository: DebugJobRepository,
    run: object,
    summary: dict[str, object],
    row_results: list[dict[str, object]],
    reports: list[dict[str, object]],
) -> None:
    command_id = _string_value(summary.get("command_id")) or _string_value(
        getattr(run, "command_id", "")
    )
    if not command_id:
        return
    existing = repository.get_pending_xiaod_decision(
        tenant_key=_string_value(getattr(run, "tenant_key", "")),
        chat_id=_string_value(getattr(run, "chat_id", "")),
        open_id=_string_value(getattr(run, "open_id", "")),
        decision_kind="spreadsheet_rerun_writeback_sync",
    )
    if existing is not None and _string_value(getattr(existing, "command_id", "")) == command_id:
        return
    decision = repository.create_xiaod_pending_decision(
        decision_id=str(uuid4()),
        tenant_key=_string_value(getattr(run, "tenant_key", "")),
        chat_id=_string_value(getattr(run, "chat_id", "")),
        open_id=_string_value(getattr(run, "open_id", "")),
        decision_kind="spreadsheet_rerun_writeback_sync",
        command_id=command_id,
        run_id=_string_value(getattr(run, "run_id", "")),
        payload={
            "row_results": row_results,
            "report_count": len(reports),
            "default": "no_sync",
        },
        note="Reports generated; waiting for explicit spreadsheet sync decision.",
        expires_at=(datetime.now(UTC) + timedelta(minutes=30)).isoformat(timespec="seconds"),
    )
    repository.save_xiaod_command_audit(
        tenant_key=_string_value(getattr(run, "tenant_key", "")),
        chat_id=_string_value(getattr(run, "chat_id", "")),
        open_id=_string_value(getattr(run, "open_id", "")),
        command_id=command_id,
        run_id=_string_value(getattr(run, "run_id", "")),
        decision_id=decision.decision_id,
        event_kind="spreadsheet_rerun_writeback_decision_created",
        status="pending",
        actor=_string_value(getattr(run, "open_id", "")),
        reason="reports_ready",
        payload={"row_results": row_results, "report_count": len(reports)},
    )


def _merge_report_payload(
    existing_reports: list[dict[str, object]],
    report: dict[str, object],
) -> list[dict[str, object]]:
    job_id = _string_value(report.get("job_id"))
    if not job_id:
        return existing_reports
    merged = [
        existing for existing in existing_reports if _string_value(existing.get("job_id")) != job_id
    ]
    merged.append(report)
    return merged


def _model_dump_dict(value: object) -> dict[str, object]:
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(mode="json")
        return dumped if isinstance(dumped, dict) else {}
    return value if isinstance(value, dict) else {}


def _dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_string_value(item) for item in value if _string_value(item)]


def _unique_strings(values: list[str]) -> list[str]:
    unique: list[str] = []
    for value in values:
        stripped = _string_value(value)
        if stripped and stripped not in unique:
            unique.append(stripped)
    return unique


def _policy_bool(policy: dict[str, object], key: str) -> bool:
    value = policy.get(key)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _string_value(value: object) -> str:
    if value is None:
        return ""
    return value.strip() if isinstance(value, str) else str(value).strip()


def _should_auto_close_completed_job(
    *,
    repository: DebugJobRepository,
    job: SubmittedDebugJob,
) -> bool:
    if job.status != "completed":
        return False
    if (
        "__auto_probe__" in job.case_id
        or "__auto_verify__" in job.case_id
        or "__hypothesis_probe__" in job.case_id
    ):
        return False
    if repository.list_targeted_probe_sources(job.job_id):
        return False
    if repository.list_strategy_follow_up_sources(job.job_id):
        return False
    if repository.list_targeted_probe_jobs(job.job_id):
        return False
    if repository.list_strategy_follow_up_jobs(job.job_id):
        return False
    if repository.list_recommended_action_verifications(job.job_id):
        return False
    return True


def _controlled_probe_source_job_id(
    *,
    repository: DebugJobRepository,
    job: SubmittedDebugJob,
) -> str:
    if "__hypothesis_probe__" not in job.case_id:
        return ""
    candidates = repository.list_jobs(artifact_group_id=job.artifact_group_id, limit=1000)
    for candidate in candidates:
        if candidate.job_id == job.job_id:
            continue
        for stage in repository.list_debug_run_stages(candidate.job_id):
            if stage.stage != "hypothesis":
                continue
            payload = stage.output.get("hypothesis_closure")
            if not isinstance(payload, dict):
                continue
            probe_results = payload.get("probe_results")
            if not isinstance(probe_results, list):
                continue
            for result in probe_results:
                if not isinstance(result, dict):
                    continue
                if str(result.get("probe_job_id", "")).strip() == job.job_id:
                    return candidate.job_id
    return ""


def _fetch_compatible_model_ids(*, base_url: str, api_key: str) -> list[str]:
    return _model_routes_fetch_compatible_model_ids(base_url=base_url, api_key=api_key)
