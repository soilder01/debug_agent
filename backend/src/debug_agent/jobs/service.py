from uuid import uuid4
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pydantic import BaseModel

from debug_agent.artifacts.layout import DEFAULT_ARTIFACT_GROUP, job_artifact_dir
from debug_agent.artifacts.store import artifact_store
from debug_agent.cases.fixtures import load_fixture_case
from debug_agent.cases.models import DebugCase
from debug_agent.experiments.planner import plan_experiments
from debug_agent.experiments.runner import ExperimentEvidence, run_experiments
from debug_agent.models.config import (
    AgentModelConfig,
    build_stage_model_router,
    default_agent_model_config,
    downgrade_meta_agent_config,
)
from debug_agent.models.adapters import ModelAdapter
from debug_agent.models.factory import build_model_adapter
from debug_agent.reports.generator import generate_initial_report
from debug_agent.reports.meta_agents import run_report_meta_agents
from debug_agent.storage.repository import DebugJobRepository


class SubmittedDebugJob(BaseModel):
    job_id: str
    case_id: str
    status: str
    artifact_group_id: str = DEFAULT_ARTIFACT_GROUP


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
        retryable_error_types: set[str] | None = None,
        model_provider: Callable[[DebugCase], ModelAdapter] | None = None,
        image_artifact_dir: Path | None = None,
        enable_fixture_fallback: bool = False,
        meta_agent_budget_units: float = 0.0,
        auto_downgrade_meta_agents: bool = False,
    ) -> None:
        self._repository = repository
        self._max_attempts = max_attempts
        self._retryable_error_types = retryable_error_types or {
            "model_call_error",
            "model_timeout",
            "model_rate_limit",
            "artifact_error",
            "unknown_runtime_error",
        }
        self._model_provider = model_provider
        self._image_artifact_dir = image_artifact_dir
        self._enable_fixture_fallback = enable_fixture_fallback
        self._meta_agent_budget_units = meta_agent_budget_units
        self._auto_downgrade_meta_agents = auto_downgrade_meta_agents

    def submit_case_debug(
        self,
        case_id: str,
        baseline_trials: int = 0,
        artifact_group_id: str = DEFAULT_ARTIFACT_GROUP,
    ) -> SubmittedDebugJob:
        case = self._load_case(case_id)
        job_id = str(uuid4())
        self._repository.save_case(case)
        self._repository.create_job(
            job_id=job_id,
            case_id=case.case_id,
            baseline_trials=baseline_trials,
            artifact_group_id=artifact_group_id,
        )
        return SubmittedDebugJob(
            job_id=job_id,
            case_id=case.case_id,
            status="created",
            artifact_group_id=artifact_group_id,
        )

    async def run_next_job(self) -> SubmittedDebugJob | None:
        job = self._repository.claim_next_created_job()
        if job is None:
            return None
        return await self._run_claimed_job(job.job_id)

    async def run_job(self, job_id: str) -> SubmittedDebugJob:
        job = self._repository.get_job(job_id)
        if job is None:
            raise KeyError(f"Debug job not found: {job_id}")
        if job.status in {"completed", "running"}:
            return SubmittedDebugJob(
                job_id=job.job_id,
                case_id=job.case_id,
                status=job.status,
                artifact_group_id=job.artifact_group_id,
            )
        self._repository.mark_running(job_id)
        return await self._run_claimed_job(job_id)

    def load_case(self, case_id: str) -> DebugCase:
        return self._load_case(case_id)

    def agent_model_config_for_artifact_group(
        self, artifact_group_id: str
    ) -> AgentModelConfig | None:
        return self._agent_model_config_for_job(artifact_group_id)

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
        if status == "created" and attempt_count == 0:
            return "retry_waiting_for_next_attempt"
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

    def recover_stale_running_jobs(self, *, stale_after_seconds: float) -> list[str]:
        stale_before = (datetime.now(UTC) - timedelta(seconds=stale_after_seconds)).isoformat()
        return self._repository.recover_stale_running_jobs(stale_before=stale_before)

    async def _run_claimed_job(self, job_id: str) -> SubmittedDebugJob:
        job = self._repository.get_job(job_id)
        if job is None:
            raise KeyError(f"Debug job not found: {job_id}")
        self._repository.start_job_attempt(job_id)
        attempt_index = job.attempt_count
        try:
            cancelled = self._cancelled_job_result(
                job_id=job_id,
                attempt_index=attempt_index,
            )
            if cancelled is not None:
                return cancelled
            case = self._load_case(job.case_id)
            plan = plan_experiments(case, baseline_trials=job.baseline_trials or None)
            agent_model_config = self._agent_model_config_for_job(job.artifact_group_id)
            adapter = (self._model_provider or build_model_adapter)(case)
            adapter_resolver = None
            if self._model_provider is None:
                adapter_resolver = build_stage_model_router(
                    case=case,
                    config=agent_model_config,
                )
            run_result = await run_experiments(
                case=case,
                plan=plan,
                adapter=adapter,
                adapter_resolver=adapter_resolver,
                image_artifact_dir=self._artifact_dir_for_job(job_id, job.artifact_group_id),
                should_cancel=lambda: self._is_job_cancelled(job_id),
            )
            cancelled = self._cancelled_job_result(
                job_id=job_id,
                attempt_index=attempt_index,
            )
            if cancelled is not None:
                return cancelled
            artifact_store.save_case_evidence(case.case_id, run_result.evidence)
            self._repository.save_evidence(
                job_id=job_id,
                case_id=case.case_id,
                evidence=run_result.evidence,
            )
            self._repository.save_debug_run_stage(
                job_id=job_id,
                stage="baseline",
                status="completed",
                input={"case_id": case.case_id, "agent_role": "model_runner"},
                output={
                    "evidence_count": len(run_result.evidence),
                    "model_calls": run_result.total_trials,
                    "models": _models_from_evidence(run_result.evidence),
                    "usage": _usage_from_evidence(run_result.evidence),
                    "agent_model_config": (
                        agent_model_config.roles["model_runner"].model_dump()
                        if agent_model_config is not None
                        and "model_runner" in agent_model_config.roles
                        else {}
                    ),
                },
                failure_reason="",
                retryable=False,
            )
            cancelled = self._cancelled_job_result(
                job_id=job_id,
                attempt_index=attempt_index,
            )
            if cancelled is not None:
                return cancelled
            if agent_model_config is not None and self._model_provider is None:
                meta_agent_config, downgrade_reason = self._maybe_downgrade_meta_agent_config(
                    agent_model_config,
                    job.artifact_group_id,
                )
                report = generate_initial_report(
                    case=case, plan=plan, run_result=run_result, job_id=job_id
                )
                enrichment = await run_report_meta_agents(
                    case=case,
                    report=report,
                    run_result=run_result,
                    config=meta_agent_config,
                )
                self._repository.save_debug_run_stage(
                    job_id=job_id,
                    stage="attribution",
                    status=enrichment.status,
                    input={
                        "case_id": case.case_id,
                        "agent_roles": [
                            "report_root_cause",
                            "experiment_planner",
                            "judge_comparator",
                        ],
                        "downgrade_reason": downgrade_reason,
                    },
                    output={
                        "meta_agent_enrichment": enrichment.model_dump(mode="json"),
                        "downgrade_reason": downgrade_reason,
                    },
                    failure_reason="; ".join(
                        item.error_message for item in enrichment.telemetry if item.error_message
                    ),
                    retryable=False,
                )
            cancelled = self._cancelled_job_result(
                job_id=job_id,
                attempt_index=attempt_index,
            )
            if cancelled is not None:
                return cancelled
            self._repository.mark_completed(job_id)
            self._repository.finish_job_attempt(
                job_id=job_id,
                attempt_index=attempt_index,
                status="completed",
                retry_decision="no_retry_needed",
            )
        except Exception as exc:
            latest_job = self._repository.get_job(job_id)
            failure_type = classify_failure(exc)
            failure_stage = classify_failure_stage(exc)
            should_retry = (
                latest_job is not None
                and latest_job.attempt_count < self._max_attempts
                and failure_type in self._retryable_error_types
            )
            retry_decision = "retry_scheduled" if should_retry else "retry_stopped"
            self._repository.finish_job_attempt(
                job_id=job_id,
                attempt_index=attempt_index,
                status="failed",
                failure_type=failure_type,
                failure_stage=failure_stage,
                error_message=str(exc),
                retry_decision=retry_decision,
            )
            if should_retry:
                self._repository.release_for_retry(job_id, str(exc))
            else:
                self._repository.mark_failed(job_id, str(exc))
            raise
        return SubmittedDebugJob(
            job_id=job_id,
            case_id=job.case_id,
            status="completed",
            artifact_group_id=job.artifact_group_id,
        )

    def _cancelled_job_result(
        self,
        *,
        job_id: str,
        attempt_index: int,
    ) -> SubmittedDebugJob | None:
        latest_job = self._repository.get_job(job_id)
        if latest_job is None or latest_job.status != "cancelled":
            return None
        error_message = latest_job.error_message or "Cancelled by user."
        self._repository.finish_job_attempt(
            job_id=job_id,
            attempt_index=attempt_index,
            status="cancelled",
            failure_type="cancelled_by_user",
            failure_stage="user_control",
            error_message=error_message,
            retry_decision="cancelled_by_user",
        )
        return SubmittedDebugJob(
            job_id=latest_job.job_id,
            case_id=latest_job.case_id,
            status="cancelled",
            artifact_group_id=latest_job.artifact_group_id,
        )

    def _is_job_cancelled(self, job_id: str) -> bool:
        job = self._repository.get_job(job_id)
        return job is not None and job.status == "cancelled"

    def _artifact_dir_for_job(self, job_id: str, artifact_group_id: str) -> Path | None:
        if self._image_artifact_dir is None:
            return None
        return job_artifact_dir(
            self._image_artifact_dir, artifact_group_id=artifact_group_id, job_id=job_id
        )

    def _agent_model_config_for_job(self, artifact_group_id: str) -> AgentModelConfig | None:
        batch = self._repository.get_batch(artifact_group_id)
        if batch is None:
            if self._model_provider is not None:
                return None
            try:
                return default_agent_model_config()
            except RuntimeError:
                return None
        raw_config = batch.retry_policy.get("agent_model_config")
        if not isinstance(raw_config, dict):
            if self._model_provider is not None:
                return None
            try:
                return default_agent_model_config()
            except RuntimeError:
                return None
        return AgentModelConfig.model_validate(raw_config)

    def _maybe_downgrade_meta_agent_config(
        self,
        config: AgentModelConfig,
        artifact_group_id: str,
    ) -> tuple[AgentModelConfig, str]:
        if not self._auto_downgrade_meta_agents or self._meta_agent_budget_units <= 0:
            return config, ""
        current_cost = _completed_cost_units_for_group(self._repository, artifact_group_id)
        if current_cost <= self._meta_agent_budget_units:
            return config, ""
        reason = (
            f"meta agent budget exceeded: current={current_cost:.4f}, "
            f"budget={self._meta_agent_budget_units:.4f}"
        )
        return downgrade_meta_agent_config(config, reason), reason

    def _load_case(self, case_id: str) -> DebugCase:
        imported_case = self._repository.get_case(case_id)
        if imported_case is not None:
            return imported_case
        if not self._enable_fixture_fallback:
            raise FileNotFoundError(f"Debug case not found: {case_id}")
        return load_fixture_case(case_id)


def classify_failure(exc: Exception) -> str:
    message = str(exc).lower()
    if isinstance(exc, FileNotFoundError) or "not found" in message or "missing" in message:
        return (
            "missing_media"
            if any(token in message for token in ("mp4", "image", "video", "file://"))
            else "invalid_input"
        )
    if "rate limit" in message or "429" in message:
        return "model_rate_limit"
    if "timeout" in message or "timed out" in message:
        return "model_timeout"
    if "parse" in message or "json" in message:
        return "parse_error"
    if "ark" in message or "model" in message or "http 4" in message or "http 5" in message:
        return "model_call_error"
    if "artifact" in message or "ffmpeg" in message:
        return "artifact_error"
    if "budget" in message:
        return "budget_exceeded"
    return "unknown_runtime_error"


def _models_from_evidence(evidence: list[ExperimentEvidence]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str]] = set()
    models: list[dict[str, str]] = []
    for item in evidence:
        key = (item.model_provider, item.model_id, item.model_name)
        if key in seen:
            continue
        seen.add(key)
        models.append(
            {
                "provider": item.model_provider,
                "model_id": item.model_id,
                "model_name": item.model_name,
            }
        )
    return models


def _usage_from_evidence(evidence: list[ExperimentEvidence]) -> dict[str, int | float]:
    prompt_tokens = sum(_numeric_usage(item.model_usage, "prompt_tokens") for item in evidence)
    completion_tokens = sum(
        _numeric_usage(item.model_usage, "completion_tokens") for item in evidence
    )
    total_tokens = sum(_numeric_usage(item.model_usage, "total_tokens") for item in evidence)
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_units": round(float(total_tokens) / 1000, 4),
    }


def _numeric_usage(usage: dict[str, int | float], key: str) -> int:
    value = usage.get(key, 0)
    return int(value) if isinstance(value, int | float) else 0


def _completed_cost_units_for_group(
    repository: DebugJobRepository, artifact_group_id: str
) -> float:
    cost = 0.0
    for job in repository.list_jobs(artifact_group_id=artifact_group_id, limit=1000):
        for stage in repository.list_debug_run_stages(job.job_id):
            usage = stage.output.get("usage")
            if isinstance(usage, dict):
                cost += _numeric_cost(usage)
            enrichment = stage.output.get("meta_agent_enrichment")
            if not isinstance(enrichment, dict):
                continue
            telemetry = enrichment.get("telemetry")
            if not isinstance(telemetry, list):
                continue
            for row in telemetry:
                if isinstance(row, dict):
                    cost += _numeric_cost(row)
    return cost


def _numeric_cost(payload: dict[object, object]) -> float:
    value = payload.get("estimated_cost_units", 0.0)
    return float(value) if isinstance(value, int | float) else 0.0


def classify_failure_stage(exc: Exception) -> str:
    message = str(exc).lower()
    if "writeback" in message or "spreadsheet" in message or "lark" in message:
        return "writeback"
    if "artifact" in message or "ffmpeg" in message:
        return "artifact_persist"
    if "judge" in message or "score" in message:
        return "attribution"
    if "verification" in message:
        return "verification"
    if "targeted" in message or "probe" in message:
        return "targeted"
    return "baseline"
