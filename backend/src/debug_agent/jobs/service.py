from uuid import uuid4

from pydantic import BaseModel

from debug_agent.artifacts.store import artifact_store
from debug_agent.cases.fixtures import load_fixture_case
from debug_agent.experiments.planner import plan_experiments
from debug_agent.experiments.runner import run_experiments
from debug_agent.models.fake import FakeModelAdapter
from debug_agent.storage.repository import DebugJobRepository


class SubmittedDebugJob(BaseModel):
    job_id: str
    case_id: str
    status: str


class DebugJobService:
    def __init__(self, repository: DebugJobRepository, max_attempts: int = 2) -> None:
        self._repository = repository
        self._max_attempts = max_attempts

    def submit_case_debug(self, case_id: str) -> SubmittedDebugJob:
        case = load_fixture_case(case_id)
        job_id = str(uuid4())
        self._repository.create_job(job_id=job_id, case_id=case.case_id)
        return SubmittedDebugJob(job_id=job_id, case_id=case.case_id, status="created")

    async def run_next_job(self) -> SubmittedDebugJob | None:
        job = self._repository.claim_next_created_job()
        if job is None:
            return None
        return await self._run_claimed_job(job.job_id)

    async def run_job(self, job_id: str) -> SubmittedDebugJob:
        job = self._repository.get_job(job_id)
        if job is None:
            raise KeyError(f"Debug job not found: {job_id}")
        self._repository.mark_running(job_id)
        return await self._run_claimed_job(job_id)

    async def _run_claimed_job(self, job_id: str) -> SubmittedDebugJob:
        job = self._repository.get_job(job_id)
        if job is None:
            raise KeyError(f"Debug job not found: {job_id}")
        try:
            case = load_fixture_case(job.case_id)
            plan = plan_experiments(case)
            adapter = FakeModelAdapter(outputs=[prediction.raw_output for prediction in case.predictions])
            run_result = await run_experiments(case=case, plan=plan, adapter=adapter)
            artifact_store.save_case_evidence(case.case_id, run_result.evidence)
            self._repository.save_evidence(
                job_id=job_id,
                case_id=case.case_id,
                evidence=run_result.evidence,
            )
            self._repository.mark_completed(job_id)
        except Exception as exc:
            latest_job = self._repository.get_job(job_id)
            if latest_job is not None and latest_job.attempt_count < self._max_attempts:
                self._repository.release_for_retry(job_id, str(exc))
            else:
                self._repository.mark_failed(job_id, str(exc))
            raise
        return SubmittedDebugJob(job_id=job_id, case_id=job.case_id, status="completed")
