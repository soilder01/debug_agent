from __future__ import annotations

import csv
import io
from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from debug_agent.api.operations_routes import PilotGateBatchEvidence
from debug_agent.api.schemas import (
    BatchDebugJobRequest,
    BatchDebugJobResponse,
    DebugBatchComparisonItem,
    DebugBatchComparisonResponse,
    DebugBatchEvaluationSummary,
    DebugBatchListResponse,
    DebugBatchProgressResponse,
    DebugJobStatus,
)
from debug_agent.jobs.service import DebugJobService, SubmittedDebugJob
from debug_agent.models.config import sanitize_agent_model_config
from debug_agent.storage.models import DebugJobRow
from debug_agent.storage.repository import DebugBatch, DebugJobRepository
from debug_agent.telemetry.performance import measure_performance


class DebugBatchViewBuilder:
    def __init__(
        self,
        *,
        job_repository: DebugJobRepository,
        build_job_status: Callable[[DebugJobRow], DebugJobStatus],
        usage_budget_units: float,
    ) -> None:
        self._job_repository = job_repository
        self._build_job_status = build_job_status
        self._usage_budget_units = usage_budget_units

    def build_progress(self, batch_id: str) -> DebugBatchProgressResponse:
        batch = self._job_repository.get_batch(batch_id)
        if batch is None:
            raise HTTPException(status_code=404, detail=f"Debug batch not found: {batch_id}")
        status_counts = self._job_repository.count_jobs_by_status(artifact_group_id=batch_id)
        metrics = self._job_repository.attempt_metrics(batch_id)
        agent_metrics = self._agent_metrics_for_batch(batch_id)
        completed_count = status_counts.get("completed", 0)
        failed_count = status_counts.get("failed", 0)
        running_count = status_counts.get("running", 0)
        pending_count = status_counts.get("created", 0)
        total = max(1, batch.total_jobs)
        recent_jobs = [
            self._build_job_status(job)
            for job in self._job_repository.list_jobs(
                artifact_group_id=batch_id, limit=10, sort="created_at_desc"
            )
        ]
        return DebugBatchProgressResponse(
            batch=batch,
            status_counts=status_counts,
            failure_types=self._job_repository.failure_type_distribution(batch_id),
            failure_stages=self._job_repository.failure_stage_distribution(batch_id),
            metrics=metrics,
            agent_metrics=agent_metrics,
            evaluation_summary=self._build_evaluation_summary(
                batch=batch,
                status_counts=status_counts,
                metrics=metrics,
                agent_metrics=agent_metrics,
            ),
            progress_percent=round((completed_count + failed_count) / total * 100, 2),
            pending_count=pending_count,
            running_count=running_count,
            completed_count=completed_count,
            failed_count=failed_count,
            recent_jobs=recent_jobs,
            recent_attempts=self._job_repository.list_job_attempts(batch_id=batch_id)[-10:],
        )

    def build_comparison_response(
        self, batch_ids: str | None, *, limit: int
    ) -> DebugBatchComparisonResponse:
        progress_items = self._resolve_comparison_progress(batch_ids=batch_ids, limit=limit)
        items = [self._comparison_item(progress) for progress in progress_items]
        best_item = max(
            items, key=lambda item: (item.quality_score, item.efficiency_score), default=None
        )
        best_batch_id = best_item.batch_id if best_item is not None else ""
        export_batch_ids = ",".join(item.batch_id for item in items)
        return DebugBatchComparisonResponse(
            generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
            batch_ids=[item.batch_id for item in items],
            items=items,
            best_batch_id=best_batch_id,
            summary=self._ab_summary(items=items, best_batch_id=best_batch_id),
            export_url=f"/api/debug-batches/comparison.csv?batch_ids={export_batch_ids}"
            if export_batch_ids
            else "",
        )

    def build_pilot_gate_batch_evidence(
        self,
        *,
        compared_batches: list[DebugBatchProgressResponse],
        comparison: DebugBatchComparisonResponse,
    ) -> PilotGateBatchEvidence:
        best_item = best_batch_comparison_item(comparison)
        return PilotGateBatchEvidence(
            compared_batch_count=len(compared_batches),
            completed_jobs=sum(batch.completed_count for batch in compared_batches),
            best_batch_id=best_item.batch_id if best_item is not None else "",
            best_success_rate=best_item.success_rate if best_item is not None else 0,
            best_p95_duration_ms=best_item.p95_duration_ms if best_item is not None else 0,
            best_estimated_cost_units=best_item.estimated_cost_units if best_item is not None else 0,
            best_quality_score=best_item.quality_score if best_item is not None else 0,
            best_efficiency_score=best_item.efficiency_score if best_item is not None else 0,
        )

    def comparison_csv(self, comparison: DebugBatchComparisonResponse) -> str:
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "batch_id",
                "status",
                "total_jobs",
                "model_profile",
                "model_runner_model",
                "model_runner_locked",
                "thinking_enabled_roles",
                "success_rate",
                "p95_duration_ms",
                "estimated_cost_units",
                "model_call_errors",
                "writeback_failed",
                "quality_score",
                "efficiency_score",
            ],
        )
        writer.writeheader()
        for item in comparison.items:
            row = item.model_dump(mode="json")
            row["thinking_enabled_roles"] = ",".join(item.thinking_enabled_roles)
            writer.writerow({field: row.get(field, "") for field in writer.fieldnames or []})
        return output.getvalue()

    def _build_evaluation_summary(
        self,
        *,
        batch: DebugBatch,
        status_counts: dict[str, int],
        metrics: dict[str, int | float],
        agent_metrics: dict[str, dict[str, int | float]],
    ) -> DebugBatchEvaluationSummary:
        jobs = self._job_repository.list_jobs(artifact_group_id=batch.batch_id, limit=1000)
        completed_jobs = status_counts.get("completed", 0)
        failed_jobs = status_counts.get("failed", 0)
        pending_jobs = status_counts.get("created", 0)
        running_jobs = status_counts.get("running", 0)
        terminal_jobs = completed_jobs + failed_jobs
        model_call_count = int(
            sum(_number_from_metrics(item, "call_count") for item in agent_metrics.values())
        )
        estimated_cost_units = round(
            sum(
                _number_from_metrics(item, "estimated_cost_units")
                for item in agent_metrics.values()
            ),
            4,
        )
        model_call_errors = sum(
            int(self._job_repository.count_evidence_errors(job.job_id).get("model_call_errors", 0))
            for job in jobs
        )
        writeback_counts = self._writeback_counts_for_jobs(jobs)
        success_rate = round(completed_jobs / terminal_jobs, 4) if terminal_jobs else 0
        failure_rate = round(failed_jobs / terminal_jobs, 4) if terminal_jobs else 0
        p95_duration_ms = int(metrics.get("p95_duration_ms", 0))
        speed_label = _batch_speed_label(
            p95_duration_ms=p95_duration_ms, terminal_jobs=terminal_jobs
        )
        cost_label = self._cost_label(estimated_cost_units)
        stability_label = _batch_stability_label(
            failed_jobs=failed_jobs,
            model_call_errors=model_call_errors,
            retry_scheduled_count=int(metrics.get("retry_scheduled_count", 0)),
        )
        trust_label = _batch_trust_label(
            failed_jobs=failed_jobs,
            model_call_errors=model_call_errors,
            writeback_failed=writeback_counts["failed"],
        )
        return DebugBatchEvaluationSummary(
            row_count=batch.total_jobs,
            created_jobs=len(jobs),
            completed_jobs=completed_jobs,
            failed_jobs=failed_jobs,
            pending_jobs=pending_jobs,
            running_jobs=running_jobs,
            success_rate=success_rate,
            failure_rate=failure_rate,
            average_duration_ms=float(metrics.get("average_duration_ms", 0)),
            p50_duration_ms=int(metrics.get("p50_duration_ms", 0)),
            p95_duration_ms=p95_duration_ms,
            max_duration_ms=int(metrics.get("max_duration_ms", 0)),
            retry_scheduled_count=int(metrics.get("retry_scheduled_count", 0)),
            model_call_count=model_call_count,
            model_call_errors=model_call_errors,
            estimated_cost_units=estimated_cost_units,
            writeback_succeeded=writeback_counts["succeeded"],
            writeback_failed=writeback_counts["failed"],
            writeback_skipped=writeback_counts["skipped"],
            speed_label=speed_label,
            cost_label=cost_label,
            stability_label=stability_label,
            trust_label=trust_label,
            comparison_summary=_batch_comparison_summary(
                success_rate=success_rate,
                p95_duration_ms=p95_duration_ms,
                estimated_cost_units=estimated_cost_units,
                speed_label=speed_label,
                cost_label=cost_label,
                stability_label=stability_label,
                trust_label=trust_label,
            ),
        )

    def _resolve_comparison_progress(
        self, batch_ids: str | None, *, limit: int
    ) -> list[DebugBatchProgressResponse]:
        requested_ids = [item.strip() for item in (batch_ids or "").split(",") if item.strip()]
        if not requested_ids:
            requested_ids = [
                batch.batch_id for batch in self._job_repository.list_batches(limit=limit)
            ]
        seen: set[str] = set()
        progress_items: list[DebugBatchProgressResponse] = []
        for batch_id in requested_ids[:limit]:
            if batch_id in seen:
                continue
            seen.add(batch_id)
            progress_items.append(self.build_progress(batch_id))
        return progress_items

    def _comparison_item(self, progress: DebugBatchProgressResponse) -> DebugBatchComparisonItem:
        summary = progress.evaluation_summary
        model_runner = _batch_role_selection(progress.batch.retry_policy, "model_runner")
        thinking_enabled_roles = _thinking_enabled_roles(progress.batch.retry_policy)
        quality_score = round(
            summary.success_rate * 100
            - summary.failure_rate * 30
            - summary.model_call_errors * 5
            - summary.writeback_failed * 3,
            2,
        )
        efficiency_score = round(
            summary.success_rate * 100
            - summary.estimated_cost_units
            - summary.p95_duration_ms / 1000,
            2,
        )
        return DebugBatchComparisonItem(
            batch_id=progress.batch.batch_id,
            status=progress.batch.status,
            total_jobs=progress.batch.total_jobs,
            model_profile=_batch_model_profile(progress.batch.retry_policy),
            model_runner_model=str(model_runner.get("model_id", "")),
            model_runner_locked=model_runner.get("locked") is True,
            thinking_enabled_roles=thinking_enabled_roles,
            success_rate=summary.success_rate,
            p95_duration_ms=summary.p95_duration_ms,
            estimated_cost_units=summary.estimated_cost_units,
            model_call_errors=summary.model_call_errors,
            writeback_failed=summary.writeback_failed,
            quality_score=quality_score,
            efficiency_score=efficiency_score,
            summary=(
                f"成功率 {round(summary.success_rate * 100, 2)}%，P95 {summary.p95_duration_ms}ms，"
                f"成本 {summary.estimated_cost_units}，质量分 {quality_score}，效率分 {efficiency_score}。"
            ),
        )

    def _ab_summary(self, *, items: list[DebugBatchComparisonItem], best_batch_id: str) -> str:
        if not items:
            return "暂无可对比批次。"
        if len(items) == 1:
            return f"当前仅有 1 个批次：{items[0].batch_id}，需要至少两个批次才能形成 A/B 对照。"
        best = next((item for item in items if item.batch_id == best_batch_id), items[0])
        return (
            f"当前对比 {len(items)} 个批次，推荐 {best.batch_id}；"
            f"质量分 {best.quality_score}，效率分 {best.efficiency_score}。"
            "评分不会改变 model_runner 公平复测锁定，只比较 meta agent 配置带来的成本、稳定性和耗时差异。"
        )

    def _writeback_counts_for_jobs(self, jobs: list[DebugJobRow]) -> dict[str, int]:
        counts = {"succeeded": 0, "failed": 0, "skipped": 0}
        for job in jobs:
            audit = self._job_repository.get_spreadsheet_writeback_audit(job.job_id)
            if audit is None:
                continue
            if audit.status in counts:
                counts[audit.status] += 1
        return counts

    def _cost_label(self, estimated_cost_units: float) -> str:
        if estimated_cost_units <= 0:
            return "无模型成本"
        if self._usage_budget_units > 0 and estimated_cost_units > self._usage_budget_units:
            return "超预算"
        return "预算内"

    def _agent_metrics_for_batch(self, batch_id: str) -> dict[str, dict[str, int | float]]:
        metrics: dict[str, dict[str, int | float]] = {}
        jobs = self._job_repository.list_jobs(artifact_group_id=batch_id, limit=1000)
        for job in jobs:
            for stage in self._job_repository.list_debug_run_stages(job.job_id):
                _collect_baseline_agent_metrics(metrics, stage.output)
                _collect_meta_agent_metrics(metrics, stage.output)
        for item in metrics.values():
            calls = int(item.get("call_count", 0))
            failures = int(item.get("failure_count", 0))
            latency = float(item.get("latency_ms_total", 0))
            item["average_latency_ms"] = round(latency / calls, 2) if calls else 0
            item["failure_rate"] = round(failures / calls, 4) if calls else 0
        return metrics


def build_debug_batch_router(
    *,
    job_repository: DebugJobRepository,
    job_service: DebugJobService,
    view_builder: DebugBatchViewBuilder,
    raise_if_usage_budget_blocks_submission: Callable[[], None],
    new_artifact_group_id: Callable[[str], str],
) -> APIRouter:
    router = APIRouter()

    @router.post("/debug-jobs/batch", status_code=202)
    def submit_batch_debug_jobs(request: BatchDebugJobRequest) -> BatchDebugJobResponse:
        return submit_debug_batch_jobs(
            request=request,
            job_repository=job_repository,
            job_service=job_service,
            view_builder=view_builder,
            raise_if_usage_budget_blocks_submission=raise_if_usage_budget_blocks_submission,
            new_artifact_group_id=new_artifact_group_id,
        )

    @router.get("/debug-batches")
    def list_debug_batches(
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> DebugBatchListResponse:
        return list_debug_batches_view(
            job_repository=job_repository,
            view_builder=view_builder,
            limit=limit,
            offset=offset,
        )

    @router.get("/debug-batches/comparison")
    @router.get("/api/debug-batches/comparison")
    def compare_debug_batches(
        batch_ids: str | None = None,
        limit: int = Query(default=2, ge=2, le=10),
    ) -> DebugBatchComparisonResponse:
        return compare_debug_batches_view(
            view_builder=view_builder, batch_ids=batch_ids, limit=limit
        )

    @router.get("/debug-batches/comparison.csv")
    @router.get("/api/debug-batches/comparison.csv")
    def export_debug_batch_comparison_csv(
        batch_ids: str | None = None,
        limit: int = Query(default=2, ge=2, le=10),
    ) -> Response:
        comparison = view_builder.build_comparison_response(batch_ids=batch_ids, limit=limit)
        return Response(
            content=view_builder.comparison_csv(comparison).encode("utf-8-sig"),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="debug-batch-comparison.csv"'},
        )

    @router.get("/debug-batches/{batch_id}")
    def get_debug_batch(batch_id: str) -> DebugBatchProgressResponse:
        return get_debug_batch_view(view_builder=view_builder, batch_id=batch_id)

    @router.post("/debug-batches/{batch_id}/pause")
    def pause_debug_batch(batch_id: str) -> DebugBatchProgressResponse:
        return update_debug_batch_status(
            job_repository=job_repository,
            view_builder=view_builder,
            batch_id=batch_id,
            status="paused",
        )

    @router.post("/debug-batches/{batch_id}/resume")
    def resume_debug_batch(batch_id: str) -> DebugBatchProgressResponse:
        return update_debug_batch_status(
            job_repository=job_repository,
            view_builder=view_builder,
            batch_id=batch_id,
            status="running",
        )

    @router.post("/debug-batches/{batch_id}/cancel")
    def cancel_debug_batch(batch_id: str) -> DebugBatchProgressResponse:
        return update_debug_batch_status(
            job_repository=job_repository,
            view_builder=view_builder,
            batch_id=batch_id,
            status="cancelled",
        )

    return router


def submit_debug_batch_jobs(
    *,
    request: BatchDebugJobRequest,
    job_repository: DebugJobRepository,
    job_service: DebugJobService,
    view_builder: DebugBatchViewBuilder,
    raise_if_usage_budget_blocks_submission: Callable[[], None],
    new_artifact_group_id: Callable[[str], str],
) -> BatchDebugJobResponse:
    raise_if_usage_budget_blocks_submission()
    with measure_performance(
        component="batch",
        operation="submit_debug_jobs",
        metadata={"case_count": len(request.case_ids), "baseline_trials": request.baseline_trials},
    ):
        artifact_group_id = new_artifact_group_id("batch")
        agent_model_config = sanitize_agent_model_config(request.agent_model_config)
        retry_policy = {
            "max_attempts": request.max_attempts,
            "retryable_error_types": sorted(job_service._retryable_error_types),
            "agent_model_config": agent_model_config.model_dump(),
        }
        job_repository.create_batch(
            batch_id=artifact_group_id,
            total_jobs=len(request.case_ids),
            max_concurrency=request.max_concurrency,
            retry_policy=retry_policy,
        )
        jobs: list[SubmittedDebugJob] = []
        rejected_case_ids: list[str] = []
        for case_id in request.case_ids:
            try:
                jobs.append(
                    job_service.submit_case_debug(
                        case_id,
                        baseline_trials=request.baseline_trials,
                        artifact_group_id=artifact_group_id,
                    )
                )
            except FileNotFoundError:
                rejected_case_ids.append(case_id)
    return BatchDebugJobResponse(
        batch_id=artifact_group_id,
        batch=view_builder.build_progress(artifact_group_id),
        jobs=jobs,
        rejected_case_ids=rejected_case_ids,
    )


def list_debug_batches_view(
    *,
    job_repository: DebugJobRepository,
    view_builder: DebugBatchViewBuilder,
    limit: int,
    offset: int = 0,
) -> DebugBatchListResponse:
    return DebugBatchListResponse(
        batches=[
            view_builder.build_progress(batch.batch_id)
            for batch in job_repository.list_batches(limit=limit, offset=offset)
        ]
    )


def compare_debug_batches_view(
    *,
    view_builder: DebugBatchViewBuilder,
    batch_ids: str | None,
    limit: int,
) -> DebugBatchComparisonResponse:
    return view_builder.build_comparison_response(batch_ids=batch_ids, limit=limit)


def get_debug_batch_view(
    *,
    view_builder: DebugBatchViewBuilder,
    batch_id: str,
) -> DebugBatchProgressResponse:
    return view_builder.build_progress(batch_id)


def update_debug_batch_status(
    *,
    job_repository: DebugJobRepository,
    view_builder: DebugBatchViewBuilder,
    batch_id: str,
    status: str,
) -> DebugBatchProgressResponse:
    job_repository.update_batch_status(batch_id, status)
    return view_builder.build_progress(batch_id)


def best_batch_comparison_item(
    comparison: DebugBatchComparisonResponse,
) -> DebugBatchComparisonItem | None:
    if not comparison.items:
        return None
    return next(
        (item for item in comparison.items if item.batch_id == comparison.best_batch_id),
        comparison.items[0],
    )


def _batch_model_profile(retry_policy: dict[str, object]) -> str:
    roles = _batch_agent_roles(retry_policy)
    if not roles:
        return "默认 Agent 配置"
    model_runner = roles.get("model_runner", {})
    meta_models = {
        str(selection.get("model_id", ""))
        for role_id, selection in roles.items()
        if role_id != "model_runner" and selection.get("model_id")
    }
    return (
        f"公平复测={model_runner.get('model_id', '默认锁定')}；"
        f"Meta Agent 模型数={len(meta_models)}；thinking 角色={len(_thinking_enabled_roles(retry_policy))}"
    )


def _batch_role_selection(retry_policy: dict[str, object], role_id: str) -> dict[str, object]:
    return _batch_agent_roles(retry_policy).get(role_id, {})


def _batch_agent_roles(retry_policy: dict[str, object]) -> dict[str, dict[str, object]]:
    raw_config = retry_policy.get("agent_model_config")
    if not isinstance(raw_config, dict):
        return {}
    raw_roles = raw_config.get("roles")
    if not isinstance(raw_roles, dict):
        return {}
    return {
        str(role_id): selection
        for role_id, selection in raw_roles.items()
        if isinstance(selection, dict)
    }


def _thinking_enabled_roles(retry_policy: dict[str, object]) -> list[str]:
    return [
        role_id
        for role_id, selection in _batch_agent_roles(retry_policy).items()
        if selection.get("thinking") == "enabled"
    ]


def _batch_speed_label(*, p95_duration_ms: int, terminal_jobs: int) -> str:
    if terminal_jobs == 0:
        return "等待基线"
    if p95_duration_ms <= 5_000:
        return "快速"
    if p95_duration_ms <= 12_000:
        return "可接受"
    return "偏慢"


def _batch_stability_label(
    *, failed_jobs: int, model_call_errors: int, retry_scheduled_count: int
) -> str:
    if failed_jobs == 0 and model_call_errors == 0 and retry_scheduled_count == 0:
        return "稳定"
    if retry_scheduled_count > 0:
        return "有重试恢复"
    return "需排查"


def _batch_trust_label(*, failed_jobs: int, model_call_errors: int, writeback_failed: int) -> str:
    if failed_jobs == 0 and model_call_errors == 0 and writeback_failed == 0:
        return "可信"
    if writeback_failed > 0:
        return "写回需复核"
    return "需人工确认"


def _batch_comparison_summary(
    *,
    success_rate: float,
    p95_duration_ms: int,
    estimated_cost_units: float,
    speed_label: str,
    cost_label: str,
    stability_label: str,
    trust_label: str,
) -> str:
    return (
        f"当前批次完成成功率 {round(success_rate * 100, 2)}%，P95 {p95_duration_ms}ms，"
        f"估算成本 {estimated_cost_units}；速度={speed_label}，成本={cost_label}，"
        f"稳定性={stability_label}，可信度={trust_label}。"
    )


def _number_from_metrics(metrics: dict[str, int | float], key: str) -> float:
    value = metrics.get(key, 0)
    return float(value) if isinstance(value, int | float) else 0.0


def _collect_baseline_agent_metrics(
    metrics: dict[str, dict[str, int | float]], output: dict[str, object]
) -> None:
    model_calls = output.get("model_calls")
    usage = output.get("usage")
    if not isinstance(model_calls, int | float) or not isinstance(usage, dict):
        return
    item = metrics.setdefault("model_runner", _empty_agent_metrics())
    item["call_count"] += int(model_calls)
    item["total_tokens"] += _numeric_metric(usage, "total_tokens")
    item["estimated_cost_units"] += _numeric_metric(usage, "estimated_cost_units")


def _collect_meta_agent_metrics(
    metrics: dict[str, dict[str, int | float]], output: dict[str, object]
) -> None:
    enrichment = output.get("meta_agent_enrichment")
    if not isinstance(enrichment, dict):
        return
    telemetry = enrichment.get("telemetry")
    if not isinstance(telemetry, list):
        return
    for row in telemetry:
        if not isinstance(row, dict):
            continue
        role = row.get("agent_role")
        if not isinstance(role, str) or not role:
            continue
        item = metrics.setdefault(role, _empty_agent_metrics())
        item["call_count"] += 1
        item["latency_ms_total"] += _numeric_metric(row, "latency_ms")
        item["total_tokens"] += _numeric_metric(row, "total_tokens")
        item["estimated_cost_units"] += _numeric_metric(row, "estimated_cost_units")
        if row.get("status") == "fallback" or row.get("error_message"):
            item["failure_count"] += 1


def _empty_agent_metrics() -> dict[str, int | float]:
    return {
        "call_count": 0,
        "failure_count": 0,
        "latency_ms_total": 0,
        "average_latency_ms": 0,
        "failure_rate": 0,
        "total_tokens": 0,
        "estimated_cost_units": 0.0,
    }


def _numeric_metric(payload: dict[object, object], key: str) -> float:
    value = payload.get(key)
    return float(value) if isinstance(value, int | float) else 0.0
