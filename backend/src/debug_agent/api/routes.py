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
from debug_agent.jobs.service import DebugJobService, RetryRecommendationDetail, SubmittedDebugJob
from debug_agent.jobs.worker import AsyncJobWorker, AsyncJobWorkerStatus
from debug_agent.models.fake import FakeModelAdapter
from debug_agent.reports.generator import DebugReport, generate_initial_report
from debug_agent.settings import DebugAgentSettings
from debug_agent.storage.database import create_sqlite_session_factory, ensure_database_schema
from debug_agent.storage.models import DebugJobRow
from debug_agent.storage.repository import DebugJobRepository

settings = DebugAgentSettings.from_env()
session_factory, engine = create_sqlite_session_factory(settings.database_url)
ensure_database_schema(engine)
job_repository = DebugJobRepository(session_factory)
job_service = DebugJobService(job_repository, image_artifact_dir=settings.image_artifact_dir)
job_worker = AsyncJobWorker(job_service)

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
    try:
        submitted = job_service.submit_case_debug(case_id, baseline_trials=baseline_trials)
        if auto_run:
            await job_service.run_job(submitted.job_id)
        return submitted
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/debug-jobs/batch", status_code=202)
def submit_batch_debug_jobs(request: BatchDebugJobRequest) -> BatchDebugJobResponse:
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
def get_worker_status() -> AsyncJobWorkerStatus:
    return job_worker.status()


@router.get("/artifacts/images/{filename}")
def get_artifact_image(filename: str) -> FileResponse:
    artifact_dir = settings.image_artifact_dir.resolve()
    artifact_path = (artifact_dir / filename).resolve()
    if artifact_path.parent != artifact_dir or not artifact_path.is_file():
        raise HTTPException(status_code=404, detail=f"Artifact image not found: {filename}")
    return FileResponse(artifact_path, media_type="image/png")


@router.post("/worker/start", status_code=202)
async def start_worker() -> AsyncJobWorkerStatus:
    job_worker.start()
    return job_worker.status()


@router.post("/worker/stop")
async def stop_worker() -> AsyncJobWorkerStatus:
    await job_worker.stop()
    return job_worker.status()


@router.get("/jobs/{job_id}")
def get_job_status(job_id: str) -> DebugJobStatus:
    job = job_repository.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Debug job not found: {job_id}")
    return _build_job_status(job)


def _build_job_status(job: DebugJobRow) -> DebugJobStatus:
    retry_status = job_service.retry_status(attempt_count=job.attempt_count, status=job.status)
    evidence_error_counts = job_repository.count_evidence_errors(job.job_id)
    retry_recommendation = job_service.retry_recommendation(
        status=job.status,
        attempt_count=job.attempt_count,
        evidence_error_counts=evidence_error_counts,
    )
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
    )


@router.get("/cases/{case_id}/evidence/{evidence_id:path}")
def get_evidence(case_id: str, evidence_id: str) -> ExperimentEvidence:
    evidence = artifact_store.get_evidence(case_id, evidence_id)
    if evidence is None:
        raise HTTPException(status_code=404, detail=f"Evidence not found: {evidence_id}")
    return evidence
