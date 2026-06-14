import json
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ValidationError

from debug_agent.artifacts.store import artifact_store
from debug_agent.cases.fixtures import load_fixture_case
from debug_agent.cases.models import DebugCase
from debug_agent.experiments.planner import plan_experiments
from debug_agent.experiments.runner import ExperimentEvidence, run_experiments
from debug_agent.imports.csv_cases import CsvRejectedRow, parse_csv_cases
from debug_agent.imports.spreadsheet_rows import SpreadsheetRejectedRow, parse_spreadsheet_rows
from debug_agent.jobs.service import DebugJobService, RetryRecommendationDetail, SubmittedDebugJob
from debug_agent.jobs.worker import AsyncJobWorker, AsyncJobWorkerStatus
from debug_agent.models.fake import FakeModelAdapter
from debug_agent.reports.generator import DebugReport, generate_initial_report
from debug_agent.reports.job_report import build_report_for_job
from debug_agent.settings import DebugAgentSettings, LarkSpreadsheetSettings
from debug_agent.spreadsheets.lark import LarkCliError, LarkCliSheetsTransport, LarkSpreadsheetClient
from debug_agent.spreadsheets.writeback import (
    SpreadsheetWritebackClient,
    SpreadsheetWritebackResult,
    make_spreadsheet_writeback_completion_hook,
    write_report_to_spreadsheet_row,
)
from debug_agent.spreadsheets.sync import SpreadsheetClient, SpreadsheetSyncResult, sync_spreadsheet_rows
from debug_agent.storage.database import create_sqlite_session_factory, ensure_database_schema
from debug_agent.storage.models import DebugJobRow
from debug_agent.storage.repository import DebugJobRepository, RecommendedActionStatus, SpreadsheetWritebackAudit

settings = DebugAgentSettings.from_env()
session_factory, engine = create_sqlite_session_factory(settings.database_url)
ensure_database_schema(engine)
job_repository = DebugJobRepository(session_factory)
job_service = DebugJobService(job_repository, image_artifact_dir=settings.image_artifact_dir)
spreadsheet_writeback_client: SpreadsheetWritebackClient | None = None
spreadsheet_sync_client: SpreadsheetClient | None = None
lark_spreadsheet_settings = LarkSpreadsheetSettings.from_env()


def configure_spreadsheet_clients(lark_settings: LarkSpreadsheetSettings | None = None) -> None:
    global lark_spreadsheet_settings, spreadsheet_sync_client, spreadsheet_writeback_client

    resolved_settings = lark_settings or LarkSpreadsheetSettings.from_env()
    lark_spreadsheet_settings = resolved_settings
    if resolved_settings.reference is None:
        spreadsheet_sync_client = None
        spreadsheet_writeback_client = None
        return

    lark_client = LarkSpreadsheetClient(
        LarkCliSheetsTransport(timeout_seconds=resolved_settings.lark_cli_timeout_seconds)
    )
    spreadsheet_sync_client = lark_client
    spreadsheet_writeback_client = lark_client


def build_job_worker(
    *,
    service: DebugJobService,
    repository: DebugJobRepository,
    writeback_client: SpreadsheetWritebackClient | None,
    report_base_url: str,
    auto_writeback_enabled: bool,
) -> AsyncJobWorker:
    if writeback_client is None or not auto_writeback_enabled:
        return AsyncJobWorker(service)
    return AsyncJobWorker(
        service,
        on_job_completed=make_spreadsheet_writeback_completion_hook(
            repository=repository,
            client=writeback_client,
            report_base_url=report_base_url,
        ),
    )


configure_spreadsheet_clients(lark_spreadsheet_settings)
job_worker = build_job_worker(
    service=job_service,
    repository=job_repository,
    writeback_client=spreadsheet_writeback_client,
    report_base_url=settings.report_base_url,
    auto_writeback_enabled=settings.auto_writeback_enabled,
)

router = APIRouter()


class DebugJobStatus(BaseModel):
    job_id: str
    case_id: str
    status: str
    created_at: str
    updated_at: str
    attempt_count: int
    max_attempts: int
    remaining_attempts: int
    will_retry: bool
    retry_recommendation: str
    retry_recommendation_detail: RetryRecommendationDetail
    error_message: str | None
    evidence_ids: list[str]
    evidence_error_counts: dict[str, int]
    spreadsheet_writeback_audit: "SpreadsheetWritebackAuditSummary | None" = None


class SpreadsheetWritebackAuditSummary(BaseModel):
    status: str
    row_id: str
    report_url: str
    error_message: str
    updated_at: str


class DebugJobListResponse(BaseModel):
    jobs: list[DebugJobStatus]
    total_count: int


class BatchDebugJobRequest(BaseModel):
    case_ids: list[str]
    baseline_trials: int = Field(default=5, ge=0, le=5)


class BatchDebugJobResponse(BaseModel):
    jobs: list[SubmittedDebugJob]
    rejected_case_ids: list[str]


class JsonlImportRequest(BaseModel):
    jsonl: str
    create_jobs: bool = True
    baseline_trials: int = Field(default=5, ge=0, le=5)


class JsonlRejectedLine(BaseModel):
    line_number: int
    error_message: str


class JsonlImportResponse(BaseModel):
    imported_case_ids: list[str]
    jobs: list[SubmittedDebugJob]
    rejected_lines: list[JsonlRejectedLine]


class CsvImportRequest(BaseModel):
    csv_text: str
    create_jobs: bool = True
    baseline_trials: int = Field(default=5, ge=0, le=5)


class CsvImportResponse(BaseModel):
    imported_case_ids: list[str]
    jobs: list[SubmittedDebugJob]
    rejected_rows: list[CsvRejectedRow]


class SpreadsheetRowImportRequest(BaseModel):
    rows: list[dict[str, object]]
    create_jobs: bool = True
    baseline_trials: int = Field(default=5, ge=0, le=5)


class SpreadsheetImportedRowResponse(BaseModel):
    sheet_row_id: str
    case_id: str


class SpreadsheetRowImportResponse(BaseModel):
    imported_case_ids: list[str]
    imported_rows: list[SpreadsheetImportedRowResponse]
    jobs: list[SubmittedDebugJob]
    rejected_rows: list[SpreadsheetRejectedRow]


class JobReportWritebackRequest(BaseModel):
    report_url: str


class RecommendedActionStatusRequest(BaseModel):
    status: Literal["pending", "accepted", "rejected", "applied"]
    actor: str = ""
    note: str = ""


class RecommendedActionStatusListResponse(BaseModel):
    statuses: list[RecommendedActionStatus]


class SpreadsheetSyncRequest(BaseModel):
    spreadsheet_id: str
    sheet_id: str
    create_jobs: bool = True
    baseline_trials: int = Field(default=5, ge=0, le=5)


class LarkSpreadsheetStatusResponse(BaseModel):
    configured: bool
    spreadsheet_id: str
    sheet_id: str
    lark_cli_timeout_seconds: int
    connectivity_status: Literal["not_checked", "ok", "failed"] = "not_checked"
    error_message: str = ""


class SpreadsheetWritebackAuditSummaryResponse(BaseModel):
    by_status: dict[str, int]
    total_count: int


class SpreadsheetWritebackAuditListResponse(BaseModel):
    audits: list[SpreadsheetWritebackAudit]
    total_count: int


class WorkerRuntimeStatus(AsyncJobWorkerStatus):
    report_base_url: str
    auto_writeback_enabled: bool


class ObservabilityJobSummary(BaseModel):
    by_status: dict[str, int]
    total_count: int
    pending_count: int
    running_count: int
    failed_count: int
    completed_count: int


class ObservabilityEvidenceSummary(BaseModel):
    total_evidence: int
    failed_judgements: int
    response_parse_errors: int
    model_call_errors: int
    average_latency_ms: float


class ObservabilityHealthSummary(BaseModel):
    level: Literal["healthy", "degraded", "critical"]
    reasons: list[str]
    actions: list[str]


class ObservabilityUsageSummary(BaseModel):
    model_call_count: int
    prompt_character_count: int
    estimated_cost_units: float
    budget_units: float
    budget_status: Literal["not_configured", "within_budget", "over_budget"]
    budget_utilization: float
    budget_enforcement_enabled: bool


class ObservabilitySummaryResponse(BaseModel):
    jobs: ObservabilityJobSummary
    worker: WorkerRuntimeStatus
    writeback_audits: SpreadsheetWritebackAuditSummaryResponse
    evidence: ObservabilityEvidenceSummary
    health: ObservabilityHealthSummary
    usage: ObservabilityUsageSummary


class DebugCaseSummary(BaseModel):
    case_id: str
    image_uri: str
    avg_score: float
    debug_status: str
    root_cause: str
    box_region_count: int


class DebugCaseListResponse(BaseModel):
    cases: list[DebugCaseSummary]
    total_count: int
    filtered_count: int


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "debug-agent-backend"}


@router.get("/observability/summary")
def get_observability_summary() -> ObservabilitySummaryResponse:
    job_counts = job_repository.count_jobs_by_status()
    writeback_counts = job_repository.count_spreadsheet_writeback_audits_by_status()
    worker_status = _build_worker_runtime_status()
    evidence_summary = ObservabilityEvidenceSummary.model_validate(job_repository.summarize_evidence_quality())
    usage_summary = _build_usage_summary(
        job_repository.summarize_usage(),
        budget_units=settings.usage_budget_units,
        budget_enforcement_enabled=settings.enforce_usage_budget,
    )
    job_summary = ObservabilityJobSummary(
        by_status=job_counts,
        total_count=sum(job_counts.values()),
        pending_count=job_counts.get("created", 0),
        running_count=job_counts.get("running", 0),
        failed_count=job_counts.get("failed", 0),
        completed_count=job_counts.get("completed", 0),
    )
    writeback_summary = SpreadsheetWritebackAuditSummaryResponse(
        by_status=writeback_counts,
        total_count=sum(writeback_counts.values()),
    )
    return ObservabilitySummaryResponse(
        jobs=job_summary,
        worker=worker_status,
        writeback_audits=writeback_summary,
        evidence=evidence_summary,
        health=_build_observability_health(
            jobs=job_summary,
            worker=worker_status,
            writeback_audits=writeback_summary,
            evidence=evidence_summary,
            usage=usage_summary,
        ),
        usage=usage_summary,
    )


@router.get("/cases")
def list_cases(has_regions: bool = False, limit: int | None = None, offset: int = 0) -> DebugCaseListResponse:
    total_count = job_repository.count_cases()
    filtered_count = job_repository.count_cases(has_regions=has_regions)
    cases = job_repository.list_cases(has_regions=has_regions, limit=limit, offset=offset)
    return DebugCaseListResponse(
        total_count=total_count,
        filtered_count=filtered_count,
        cases=[
            DebugCaseSummary(
                case_id=case.case_id,
                image_uri=case.image_uri,
                avg_score=case.avg_score,
                debug_status=case.human_notes.debug_status,
                root_cause=case.human_notes.root_cause,
                box_region_count=len(case.box_regions),
            )
            for case in cases
        ]
    )


@router.get("/cases/{case_id}")
def get_case_detail(case_id: str) -> DebugCase:
    try:
        return job_service.load_case(case_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/cases/{case_id}/debug")
async def debug_case(case_id: str) -> DebugReport:
    try:
        case = load_fixture_case(case_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    job_id = str(uuid4())
    job_repository.create_job(job_id=job_id, case_id=case.case_id)
    job_repository.mark_running(job_id)
    plan = plan_experiments(case)
    adapter = FakeModelAdapter(outputs=[prediction.raw_output for prediction in case.predictions])
    try:
        run_result = await run_experiments(case=case, plan=plan, adapter=adapter)
        artifact_store.save_case_evidence(case.case_id, run_result.evidence)
        job_repository.save_evidence(
            job_id=job_id,
            case_id=case.case_id,
            evidence=run_result.evidence,
        )
        job_repository.mark_completed(job_id)
    except Exception as exc:
        job_repository.mark_failed(job_id, str(exc))
        raise
    return generate_initial_report(case, plan, run_result, job_id=job_id)


@router.post("/cases/{case_id}/debug-jobs", status_code=202)
async def submit_debug_job(
    case_id: str,
    auto_run: bool = False,
    baseline_trials: int = Query(default=0, ge=0, le=5),
) -> SubmittedDebugJob:
    _raise_if_usage_budget_blocks_submission()
    try:
        submitted = job_service.submit_case_debug(case_id, baseline_trials=baseline_trials)
        if auto_run:
            await job_service.run_job(submitted.job_id)
        return submitted
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/debug-jobs/batch", status_code=202)
def submit_batch_debug_jobs(request: BatchDebugJobRequest) -> BatchDebugJobResponse:
    _raise_if_usage_budget_blocks_submission()
    jobs: list[SubmittedDebugJob] = []
    rejected_case_ids: list[str] = []
    for case_id in request.case_ids:
        try:
            jobs.append(job_service.submit_case_debug(case_id, baseline_trials=request.baseline_trials))
        except FileNotFoundError:
            rejected_case_ids.append(case_id)
    return BatchDebugJobResponse(jobs=jobs, rejected_case_ids=rejected_case_ids)


@router.post("/imports/jsonl", status_code=202)
def import_jsonl_cases(request: JsonlImportRequest) -> JsonlImportResponse:
    if request.create_jobs:
        _raise_if_usage_budget_blocks_submission()
    imported_case_ids: list[str] = []
    jobs: list[SubmittedDebugJob] = []
    rejected_lines: list[JsonlRejectedLine] = []
    for line_number, line in enumerate(request.jsonl.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            case = DebugCase.model_validate(json.loads(line))
            job_repository.save_case(case)
            imported_case_ids.append(case.case_id)
            if request.create_jobs:
                jobs.append(job_service.submit_case_debug(case.case_id, baseline_trials=request.baseline_trials))
        except (json.JSONDecodeError, ValidationError, FileNotFoundError) as exc:
            rejected_lines.append(JsonlRejectedLine(line_number=line_number, error_message=str(exc)))
    return JsonlImportResponse(imported_case_ids=imported_case_ids, jobs=jobs, rejected_lines=rejected_lines)


@router.post("/imports/csv", status_code=202)
def import_csv_cases(request: CsvImportRequest) -> CsvImportResponse:
    if request.create_jobs:
        _raise_if_usage_budget_blocks_submission()
    parse_result = parse_csv_cases(request.csv_text)
    imported_case_ids: list[str] = []
    jobs: list[SubmittedDebugJob] = []
    for case in parse_result.cases:
        job_repository.save_case(case)
        imported_case_ids.append(case.case_id)
        if request.create_jobs:
            jobs.append(job_service.submit_case_debug(case.case_id, baseline_trials=request.baseline_trials))
    return CsvImportResponse(
        imported_case_ids=imported_case_ids,
        jobs=jobs,
        rejected_rows=parse_result.rejected_rows,
    )


@router.post("/imports/spreadsheet-rows", status_code=202)
def import_spreadsheet_rows(request: SpreadsheetRowImportRequest) -> SpreadsheetRowImportResponse:
    if request.create_jobs:
        _raise_if_usage_budget_blocks_submission()
    parse_result = parse_spreadsheet_rows(request.rows)
    imported_case_ids: list[str] = []
    imported_rows: list[SpreadsheetImportedRowResponse] = []
    jobs: list[SubmittedDebugJob] = []
    for imported_row in parse_result.imported_rows:
        case = imported_row.case
        job_repository.save_case(case)
        imported_case_ids.append(case.case_id)
        imported_rows.append(
            SpreadsheetImportedRowResponse(
                sheet_row_id=imported_row.sheet_row_id,
                case_id=case.case_id,
            )
        )
        if request.create_jobs:
            jobs.append(job_service.submit_case_debug(case.case_id, baseline_trials=request.baseline_trials))
    return SpreadsheetRowImportResponse(
        imported_case_ids=imported_case_ids,
        imported_rows=imported_rows,
        jobs=jobs,
        rejected_rows=parse_result.rejected_rows,
    )




@router.get("/spreadsheets/lark/status")
def get_lark_spreadsheet_status(check_connectivity: bool = False) -> LarkSpreadsheetStatusResponse:
    reference = lark_spreadsheet_settings.reference
    if reference is None:
        return LarkSpreadsheetStatusResponse(
            configured=False,
            spreadsheet_id="",
            sheet_id="",
            lark_cli_timeout_seconds=lark_spreadsheet_settings.lark_cli_timeout_seconds,
        )

    connectivity_status: Literal["not_checked", "ok", "failed"] = "not_checked"
    error_message = ""
    if check_connectivity:
        if spreadsheet_sync_client is None:
            connectivity_status = "failed"
            error_message = "Spreadsheet sync client is not configured"
        else:
            try:
                spreadsheet_sync_client.list_rows(
                    spreadsheet_id=reference.spreadsheet_id,
                    sheet_id=reference.sheet_id,
                )
                connectivity_status = "ok"
            except LarkCliError as exc:
                connectivity_status = "failed"
                error_message = str(exc)

    return LarkSpreadsheetStatusResponse(
        configured=True,
        spreadsheet_id=reference.spreadsheet_id,
        sheet_id=reference.sheet_id,
        lark_cli_timeout_seconds=lark_spreadsheet_settings.lark_cli_timeout_seconds,
        connectivity_status=connectivity_status,
        error_message=error_message,
    )


@router.post("/spreadsheets/sync", status_code=202)
def sync_spreadsheet(request: SpreadsheetSyncRequest) -> SpreadsheetSyncResult:
    if spreadsheet_sync_client is None:
        raise HTTPException(status_code=503, detail="Spreadsheet sync client is not configured")
    if request.create_jobs:
        _raise_if_usage_budget_blocks_submission()
    try:
        return sync_spreadsheet_rows(
            client=spreadsheet_sync_client,
            spreadsheet_id=request.spreadsheet_id,
            sheet_id=request.sheet_id,
            repository=job_repository,
            job_service=job_service,
            create_jobs=request.create_jobs,
            baseline_trials=request.baseline_trials,
        )
    except LarkCliError as exc:
        raise _lark_spreadsheet_error(exc) from exc


@router.get("/spreadsheets/writeback/audits/summary")
def get_spreadsheet_writeback_audit_summary() -> SpreadsheetWritebackAuditSummaryResponse:
    by_status = job_repository.count_spreadsheet_writeback_audits_by_status()
    return SpreadsheetWritebackAuditSummaryResponse(
        by_status=by_status,
        total_count=sum(by_status.values()),
    )


@router.get("/spreadsheets/writeback/audits")
def list_spreadsheet_writeback_audits(
    status: str | None = None,
    limit: int | None = Query(default=None, ge=0),
    offset: int = Query(default=0, ge=0),
) -> SpreadsheetWritebackAuditListResponse:
    return SpreadsheetWritebackAuditListResponse(
        audits=job_repository.list_spreadsheet_writeback_audits(status=status, limit=limit, offset=offset),
        total_count=job_repository.count_spreadsheet_writeback_audits(status=status),
    )


@router.post("/jobs/run-next")
async def run_next_job() -> SubmittedDebugJob | None:
    return await job_service.run_next_job()


@router.get("/jobs")
def list_jobs(
    status: str | None = None,
    limit: int | None = None,
    offset: int = 0,
    sort: Literal["created_at_asc", "created_at_desc"] = "created_at_asc",
) -> DebugJobListResponse:
    return DebugJobListResponse(
        jobs=[
            _build_job_status(job)
            for job in job_repository.list_jobs(status=status, limit=limit, offset=offset, sort=sort)
        ],
        total_count=job_repository.count_jobs(status=status),
    )


@router.get("/jobs/{job_id}/evidence/{evidence_id:path}")
def get_job_evidence(job_id: str, evidence_id: str) -> ExperimentEvidence:
    evidence = job_repository.get_evidence(job_id, evidence_id)
    if evidence is None:
        raise HTTPException(status_code=404, detail=f"Evidence not found: {evidence_id}")
    return evidence


@router.get("/worker/status")
def get_worker_status() -> WorkerRuntimeStatus:
    return _build_worker_runtime_status()


@router.get("/artifacts/images/{filename}")
def get_artifact_image(filename: str) -> FileResponse:
    artifact_dir = settings.image_artifact_dir.resolve()
    artifact_path = (artifact_dir / filename).resolve()
    if artifact_path.parent != artifact_dir or not artifact_path.is_file():
        raise HTTPException(status_code=404, detail=f"Artifact image not found: {filename}")
    return FileResponse(artifact_path, media_type="image/png")


@router.post("/worker/start", status_code=202)
async def start_worker() -> WorkerRuntimeStatus:
    job_worker.start()
    return _build_worker_runtime_status()


@router.post("/worker/stop")
async def stop_worker() -> WorkerRuntimeStatus:
    await job_worker.stop()
    return _build_worker_runtime_status()


@router.get("/jobs/{job_id}/spreadsheet-writeback/audit")
def get_job_spreadsheet_writeback_audit(job_id: str) -> SpreadsheetWritebackAudit:
    audit = job_repository.get_spreadsheet_writeback_audit(job_id)
    if audit is None:
        raise HTTPException(status_code=404, detail=f"Spreadsheet writeback audit not found for job: {job_id}")
    return audit


@router.get("/jobs/{job_id}")
def get_job_status(job_id: str) -> DebugJobStatus:
    job = job_repository.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Debug job not found: {job_id}")
    return _build_job_status(job)


@router.get("/jobs/{job_id}/report")
def get_job_report(job_id: str) -> DebugReport:
    report = build_report_for_job(job_repository, job_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Debug report not found for job: {job_id}")
    return report


@router.patch("/jobs/{job_id}/recommended-actions/{action_index}/status")
def update_recommended_action_status(
    job_id: str,
    action_index: int,
    request: RecommendedActionStatusRequest,
) -> RecommendedActionStatus:
    if job_repository.get_job(job_id) is None:
        raise HTTPException(status_code=404, detail=f"Debug job not found: {job_id}")
    return job_repository.save_recommended_action_status(
        job_id=job_id,
        action_index=action_index,
        status=request.status,
        actor=request.actor,
        note=request.note,
    )


@router.get("/jobs/{job_id}/recommended-actions/statuses")
def list_recommended_action_statuses(job_id: str) -> RecommendedActionStatusListResponse:
    if job_repository.get_job(job_id) is None:
        raise HTTPException(status_code=404, detail=f"Debug job not found: {job_id}")
    return RecommendedActionStatusListResponse(
        statuses=job_repository.list_recommended_action_statuses(job_id)
    )


@router.post("/jobs/{job_id}/spreadsheet-writeback")
def write_job_report_to_spreadsheet(job_id: str, request: JobReportWritebackRequest) -> SpreadsheetWritebackResult:
    if spreadsheet_writeback_client is None:
        raise HTTPException(status_code=503, detail="Spreadsheet writeback client is not configured")
    report = build_report_for_job(job_repository, job_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Debug report not found for job: {job_id}")
    mapping = job_repository.get_spreadsheet_row_mapping_by_job_id(job_id)
    if mapping is None:
        raise HTTPException(status_code=404, detail=f"Spreadsheet row mapping not found for job: {job_id}")
    try:
        result = write_report_to_spreadsheet_row(
            client=spreadsheet_writeback_client,
            spreadsheet_id=mapping.spreadsheet_id,
            sheet_id=mapping.sheet_id,
            row_id=mapping.row_id,
            report=report,
            report_url=request.report_url,
        )
    except LarkCliError as exc:
        job_repository.save_spreadsheet_writeback_audit(
            job_id=job_id,
            status="failed",
            row_id=mapping.row_id,
            report_url=request.report_url,
            fields={},
            error_message=str(exc),
        )
        raise _lark_spreadsheet_error(exc) from exc
    job_repository.save_spreadsheet_writeback_audit(
        job_id=job_id,
        status="succeeded",
        row_id=result.row_id,
        report_url=request.report_url,
        fields=result.fields,
        error_message="",
    )
    return result


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


def _build_worker_runtime_status() -> WorkerRuntimeStatus:
    status = job_worker.status()
    return WorkerRuntimeStatus(
        **status.model_dump(),
        report_base_url=settings.report_base_url,
        auto_writeback_enabled=settings.auto_writeback_enabled,
    )


def _build_usage_summary(
    raw_usage: dict[str, int | float],
    *,
    budget_units: float,
    budget_enforcement_enabled: bool,
) -> ObservabilityUsageSummary:
    estimated_cost_units = float(raw_usage["estimated_cost_units"])
    budget_status: Literal["not_configured", "within_budget", "over_budget"] = "not_configured"
    budget_utilization = 0.0
    if budget_units > 0:
        budget_utilization = round(estimated_cost_units / budget_units, 4)
        budget_status = "over_budget" if estimated_cost_units > budget_units else "within_budget"
    return ObservabilityUsageSummary(
        model_call_count=int(raw_usage["model_call_count"]),
        prompt_character_count=int(raw_usage["prompt_character_count"]),
        estimated_cost_units=estimated_cost_units,
        budget_units=budget_units,
        budget_status=budget_status,
        budget_utilization=budget_utilization,
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
        raise HTTPException(status_code=429, detail="Usage budget exceeded; new debug jobs are disabled.")


def _build_observability_health(
    *,
    jobs: ObservabilityJobSummary,
    worker: WorkerRuntimeStatus,
    writeback_audits: SpreadsheetWritebackAuditSummaryResponse,
    evidence: ObservabilityEvidenceSummary,
    usage: ObservabilityUsageSummary,
) -> ObservabilityHealthSummary:
    critical_reasons: list[str] = []
    degraded_reasons: list[str] = []
    if jobs.failed_count > 0:
        critical_reasons.append("failed jobs present")
    if worker.error_count > 0:
        critical_reasons.append("worker errors present")
    if writeback_audits.by_status.get("failed", 0) > 0:
        critical_reasons.append("failed spreadsheet writebacks present")
    if evidence.model_call_errors > 0:
        critical_reasons.append("model call errors present")
    if usage.budget_status == "over_budget":
        critical_reasons.append("usage budget exceeded")
    if jobs.pending_count > 0:
        degraded_reasons.append("pending jobs present")
    if jobs.running_count > 0:
        degraded_reasons.append("jobs currently running")
    if evidence.response_parse_errors > 0:
        degraded_reasons.append("response parse errors present")
    if writeback_audits.by_status.get("skipped", 0) > 0:
        degraded_reasons.append("skipped spreadsheet writebacks present")
    if critical_reasons:
        reasons = critical_reasons + degraded_reasons
        return ObservabilityHealthSummary(level="critical", reasons=reasons, actions=_observability_actions(reasons))
    if degraded_reasons:
        return ObservabilityHealthSummary(
            level="degraded",
            reasons=degraded_reasons,
            actions=_observability_actions(degraded_reasons),
        )
    return ObservabilityHealthSummary(level="healthy", reasons=[], actions=[])


def _observability_actions(reasons: list[str]) -> list[str]:
    action_by_reason = {
        "failed jobs present": "Inspect failed jobs and open their evidence chain.",
        "worker errors present": "Check worker logs and restart the worker if the error persists.",
        "failed spreadsheet writebacks present": (
            "Retry failed spreadsheet writebacks after checking Lark permissions and sheet headers."
        ),
        "model call errors present": "Check model endpoint health, timeout settings, and retry affected jobs.",
        "usage budget exceeded": "Pause new submissions or raise the usage budget before continuing.",
        "pending jobs present": "Start or scale workers to drain the pending job backlog.",
        "jobs currently running": "Monitor running jobs for timeout or stuck execution.",
        "response parse errors present": "Inspect prompts and parser assumptions for malformed model outputs.",
        "skipped spreadsheet writebacks present": "Check spreadsheet row mappings before retrying writeback.",
    }
    actions: list[str] = []
    for reason in reasons:
        action = action_by_reason.get(reason)
        if action and action not in actions:
            actions.append(action)
    return actions


def _lark_spreadsheet_error(exc: LarkCliError) -> HTTPException:
    return HTTPException(status_code=502, detail=f"Lark spreadsheet operation failed: {exc}")


@router.get("/cases/{case_id}/evidence/{evidence_id:path}")
def get_evidence(case_id: str, evidence_id: str) -> ExperimentEvidence:
    evidence = artifact_store.get_evidence(case_id, evidence_id)
    if evidence is None:
        raise HTTPException(status_code=404, detail=f"Evidence not found: {evidence_id}")
    return evidence
