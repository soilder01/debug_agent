from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from debug_agent.artifacts.store import artifact_store
from debug_agent.cases.fixtures import load_fixture_case
from debug_agent.experiments.planner import plan_experiments
from debug_agent.experiments.runner import ExperimentEvidence, run_experiments
from debug_agent.jobs.service import DebugJobService, SubmittedDebugJob
from debug_agent.models.fake import FakeModelAdapter
from debug_agent.reports.generator import DebugReport, generate_initial_report
from debug_agent.settings import DebugAgentSettings
from debug_agent.storage.database import create_sqlite_session_factory
from debug_agent.storage.models import Base
from debug_agent.storage.repository import DebugJobRepository

settings = DebugAgentSettings.from_env()
session_factory, engine = create_sqlite_session_factory(settings.database_url)
Base.metadata.create_all(engine)
job_repository = DebugJobRepository(session_factory)
job_service = DebugJobService(job_repository)

router = APIRouter()


class DebugJobStatus(BaseModel):
    job_id: str
    case_id: str
    status: str
    attempt_count: int
    error_message: str | None
    evidence_ids: list[str]


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "debug-agent-backend"}


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
def submit_debug_job(case_id: str) -> SubmittedDebugJob:
    try:
        return job_service.submit_case_debug(case_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/jobs/run-next")
async def run_next_job() -> SubmittedDebugJob | None:
    return await job_service.run_next_job()


@router.get("/jobs/{job_id}")
def get_job_status(job_id: str) -> DebugJobStatus:
    job = job_repository.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Debug job not found: {job_id}")
    return DebugJobStatus(
        job_id=job.job_id,
        case_id=job.case_id,
        status=job.status,
        attempt_count=job.attempt_count,
        error_message=job.error_message,
        evidence_ids=job_repository.list_evidence_ids(job_id),
    )


@router.get("/cases/{case_id}/evidence/{evidence_id:path}")
def get_evidence(case_id: str, evidence_id: str) -> ExperimentEvidence:
    evidence = artifact_store.get_evidence(case_id, evidence_id)
    if evidence is None:
        raise HTTPException(status_code=404, detail=f"Evidence not found: {evidence_id}")
    return evidence
