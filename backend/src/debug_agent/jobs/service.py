from uuid import uuid4
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel

from debug_agent.artifacts.store import artifact_store
from debug_agent.cases.fixtures import load_fixture_case
from debug_agent.cases.models import DebugCase
from debug_agent.experiments.planner import plan_experiments
from debug_agent.experiments.runner import run_experiments
from debug_agent.models.adapters import ModelAdapter
from debug_agent.models.factory import build_model_adapter
from debug_agent.storage.repository import DebugJobRepository


class SubmittedDebugJob(BaseModel):
    job_id: str
    case_id: str
    status: str


class RetryStatus(BaseModel):
    max_attempts: int
    remaining_attempts: int
    will_retry: bool


class RetryRecommendationDetail(BaseModel):
    code: str
    label: str
    action: str
    severity: str


class DebugJobService:
    def __init__(
        self,
        repository: DebugJobRepository,
        max_attempts: int = 2,
        model_provider: Callable[[DebugCase], ModelAdapter] = build_model_adapter,
        image_artifact_dir: Path | None = None,
    ) -> None:
        self._repository = repository
        self._max_attempts = max_attempts
        self._model_provider = model_provider
        self._image_artifact_dir = image_artifact_dir

    def submit_case_debug(self, case_id: str, baseline_trials: int = 0) -> SubmittedDebugJob:
        case = self._load_case(case_id)
        job_id = str(uuid4())
        self._repository.create_job(job_id=job_id, case_id=case.case_id, baseline_trials=baseline_trials)
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

    def load_case(self, case_id: str) -> DebugCase:
        return self._load_case(case_id)

    def retry_status(self, attempt_count: int, status: str) -> RetryStatus:
        remaining_attempts = max(0, self._max_attempts - attempt_count)
        return RetryStatus(
            max_attempts=self._max_attempts,
            remaining_attempts=remaining_attempts,
            will_retry=status == "created" and attempt_count > 0 and remaining_attempts > 0,
        )

    def retry_recommendation(
        self,
        status: str,
        attempt_count: int,
        evidence_error_counts: dict[str, int],
    ) -> str:
        retry_status = self.retry_status(attempt_count=attempt_count, status=status)
        if status == "completed":
            return "no_retry_needed"
        if evidence_error_counts["model_call_errors"] > 0 and retry_status.will_retry:
            return "retry_model_call_error"
        if evidence_error_counts["response_parse_errors"] > 0:
            return "inspect_parse_error"
        if not retry_status.will_retry:
            return "retry_budget_exhausted"
        return "retry_waiting_for_next_attempt"

    def retry_recommendation_detail(self, code: str) -> RetryRecommendationDetail:
        details = {
            "no_retry_needed": RetryRecommendationDetail(
                code="no_retry_needed",
                label="无需重试",
                action="任务已完成，直接查看证据链和结论。",
                severity="info",
            ),
            "retry_waiting_for_next_attempt": RetryRecommendationDetail(
                code="retry_waiting_for_next_attempt",
                label="等待自动重试",
                action="保留在队列中，等待 worker 执行下一次尝试。",
                severity="warning",
            ),
            "retry_model_call_error": RetryRecommendationDetail(
                code="retry_model_call_error",
                label="建议重试模型调用",
                action="模型调用失败且仍有重试预算，优先重新执行该任务。",
                severity="warning",
            ),
            "inspect_parse_error": RetryRecommendationDetail(
                code="inspect_parse_error",
                label="检查解析错误",
                action="模型已有返回但解析失败，优先检查输出格式、prompt 或解析器。",
                severity="warning",
            ),
            "retry_budget_exhausted": RetryRecommendationDetail(
                code="retry_budget_exhausted",
                label="重试预算已耗尽",
                action="不要继续自动重试，转人工检查任务错误和证据链。",
                severity="critical",
            ),
        }
        return details.get(
            code,
            RetryRecommendationDetail(
                code=code,
                label="未知重试建议",
                action="检查任务状态、错误信息和证据链后再决定下一步。",
                severity="warning",
            ),
        )

    async def _run_claimed_job(self, job_id: str) -> SubmittedDebugJob:
        job = self._repository.get_job(job_id)
        if job is None:
            raise KeyError(f"Debug job not found: {job_id}")
        try:
            case = self._load_case(job.case_id)
            plan = plan_experiments(case, baseline_trials=job.baseline_trials or None)
            adapter = self._model_provider(case)
            run_result = await run_experiments(
                case=case,
                plan=plan,
                adapter=adapter,
                image_artifact_dir=self._image_artifact_dir,
            )
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

    def _load_case(self, case_id: str) -> DebugCase:
        imported_case = self._repository.get_case(case_id)
        if imported_case is not None:
            return imported_case
        return load_fixture_case(case_id)
