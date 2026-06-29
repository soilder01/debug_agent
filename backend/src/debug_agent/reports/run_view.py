from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from debug_agent.reports.action_queue import build_action_queue, summarize_action_queue
from debug_agent.reports.generator import DebugReport
from debug_agent.storage.repository import DebugJobRepository, DebugRunStage


class DebugRunJobView(BaseModel):
    job_id: str
    case_id: str
    status: str
    status_label: str
    created_at: str
    updated_at: str


class DebugRunSummaryView(BaseModel):
    headline: str
    current_phase: str
    next_step: str
    evidence_count: int
    agent_trace_count: int


class DebugRunTimelineItem(BaseModel):
    key: str
    label: str
    status: str
    status_label: str
    summary: str
    started_at: str
    updated_at: str


class DebugRunSectionStatus(BaseModel):
    status: str
    status_label: str
    summary: str
    stage_count: int = 0


class DebugRunWritebackView(BaseModel):
    status: str
    status_label: str
    row_id: str = ""
    report_url: str = ""
    error_message: str = ""
    updated_at: str = ""


class DebugRunActionQueueView(BaseModel):
    summary: dict[str, int] = Field(default_factory=dict)
    items: list[dict[str, Any]] = Field(default_factory=list)


class DebugRunHypothesisClosureView(BaseModel):
    status: str
    status_label: str
    summary: str
    hypothesis_count: int = 0
    probe_plan_count: int = 0
    probe_result_count: int = 0
    causal_comparison_count: int = 0
    verified_root_cause_count: int = 0
    unverified_hypothesis_count: int = 0
    fairness_lock: dict[str, Any] = Field(default_factory=dict)
    hypotheses: list[dict[str, Any]] = Field(default_factory=list)
    probe_plans: list[dict[str, Any]] = Field(default_factory=list)
    probe_results: list[dict[str, Any]] = Field(default_factory=list)
    causal_comparisons: list[dict[str, Any]] = Field(default_factory=list)
    verified_root_causes: list[dict[str, Any]] = Field(default_factory=list)
    unverified_hypotheses: list[dict[str, Any]] = Field(default_factory=list)


class DebugRunLoopView(BaseModel):
    status: str
    status_label: str
    summary: str
    current_iteration: int = 0
    decision: str = ""
    next_action: str = ""
    stop_reason: str = ""
    iterations: list[dict[str, Any]] = Field(default_factory=list)


class DebugRunView(BaseModel):
    job: DebugRunJobView
    summary: DebugRunSummaryView
    timeline: list[DebugRunTimelineItem] = Field(default_factory=list)
    agent_traces: list[dict[str, Any]] = Field(default_factory=list)
    hypothesis_closure: DebugRunHypothesisClosureView
    debug_loop: DebugRunLoopView
    auto_closure: DebugRunSectionStatus
    writeback: DebugRunWritebackView
    action_queue: DebugRunActionQueueView


def build_debug_run_view(
    *,
    repository: DebugJobRepository,
    job_id: str,
    report: DebugReport,
) -> DebugRunView | None:
    job = repository.get_job(job_id)
    if job is None:
        return None
    stages = repository.list_debug_run_stages(job_id)
    action_queue = report.action_queue or build_action_queue(
        repository=repository,
        job_id=job_id,
        report=report,
    )
    writeback = _writeback_view(repository=repository, job_id=job_id)
    timeline = [_timeline_item(stage) for stage in stages]
    agent_traces = [trace.model_dump(mode="json") for trace in report.agent_traces]
    summary = _summary_view(
        status=job.status,
        stages=stages,
        action_queue=action_queue,
        writeback=writeback,
        evidence_count=len(repository.list_evidence(job_id)),
        agent_trace_count=len(agent_traces),
    )
    return DebugRunView(
        job=DebugRunJobView(
            job_id=job.job_id,
            case_id=job.case_id,
            status=job.status,
            status_label=_status_label(job.status),
            created_at=job.created_at,
            updated_at=job.updated_at,
        ),
        summary=summary,
        timeline=timeline,
        agent_traces=agent_traces,
        hypothesis_closure=_hypothesis_closure_view(stages),
        debug_loop=_debug_loop_view(stages),
        auto_closure=_auto_closure_view(stages),
        writeback=writeback,
        action_queue=DebugRunActionQueueView(
            summary=summarize_action_queue(action_queue),
            items=action_queue,
        ),
    )


def _summary_view(
    *,
    status: str,
    stages: list[DebugRunStage],
    action_queue: list[dict[str, Any]],
    writeback: DebugRunWritebackView,
    evidence_count: int,
    agent_trace_count: int,
) -> DebugRunSummaryView:
    return DebugRunSummaryView(
        headline=_headline(status),
        current_phase=_current_phase(stages=stages, status=status),
        next_step=_next_step(action_queue=action_queue, writeback=writeback),
        evidence_count=evidence_count,
        agent_trace_count=agent_trace_count,
    )


def _timeline_item(stage: DebugRunStage) -> DebugRunTimelineItem:
    return DebugRunTimelineItem(
        key=stage.stage,
        label=_stage_label(stage.stage),
        status=stage.status,
        status_label=_status_label(stage.status),
        summary=_stage_summary(stage),
        started_at=stage.created_at,
        updated_at=stage.updated_at,
    )


def _hypothesis_closure_view(stages: list[DebugRunStage]) -> DebugRunHypothesisClosureView:
    stage = next((item for item in reversed(stages) if item.stage == "hypothesis"), None)
    if stage is None:
        return DebugRunHypothesisClosureView(
            status="not_started",
            status_label="未开始",
            summary="尚未生成候选根因假设。",
        )
    payload = stage.output.get("hypothesis_closure")
    if not isinstance(payload, dict):
        return DebugRunHypothesisClosureView(
            status=stage.status,
            status_label=_status_label(stage.status),
            summary=stage.failure_reason or "假设闭环阶段没有输出结构化结果。",
        )
    hypotheses = _payload_list(payload, "hypotheses")
    probe_plans = _payload_list(payload, "probe_plans")
    probe_results = _payload_list(payload, "probe_results")
    causal_comparisons = _payload_list(payload, "causal_comparisons")
    verified_root_causes = _payload_list(payload, "verified_root_causes")
    unverified_hypotheses = _payload_list(payload, "unverified_hypotheses")
    fairness_lock = payload.get("fairness_lock")
    return DebugRunHypothesisClosureView(
        status=stage.status,
        status_label=_status_label(stage.status),
        summary=_hypothesis_closure_summary(
            stage=stage,
            hypothesis_count=len(hypotheses),
            probe_plan_count=len(probe_plans),
            causal_comparison_count=len(causal_comparisons),
            verified_root_cause_count=len(verified_root_causes),
            unverified_hypothesis_count=len(unverified_hypotheses),
        ),
        hypothesis_count=len(hypotheses),
        probe_plan_count=len(probe_plans),
        probe_result_count=len(probe_results),
        causal_comparison_count=len(causal_comparisons),
        verified_root_cause_count=len(verified_root_causes),
        unverified_hypothesis_count=len(unverified_hypotheses),
        fairness_lock=fairness_lock if isinstance(fairness_lock, dict) else {},
        hypotheses=hypotheses,
        probe_plans=probe_plans,
        probe_results=probe_results,
        causal_comparisons=causal_comparisons,
        verified_root_causes=verified_root_causes,
        unverified_hypotheses=unverified_hypotheses,
    )


def _payload_list(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _debug_loop_view(stages: list[DebugRunStage]) -> DebugRunLoopView:
    stage = next((item for item in reversed(stages) if item.stage == "debug_loop"), None)
    if stage is None:
        return DebugRunLoopView(
            status="not_started",
            status_label="未开始",
            summary="尚未进入循环探索。",
        )
    payload = stage.output.get("debug_loop")
    if not isinstance(payload, dict):
        return DebugRunLoopView(
            status=stage.status,
            status_label=_status_label(stage.status),
            summary=stage.failure_reason or "循环探索阶段没有结构化输出。",
        )
    iterations = _payload_list(payload, "iterations")
    decision = str(payload.get("decision", ""))
    next_action = str(payload.get("next_action", ""))
    stop_reason = str(payload.get("stop_reason", ""))
    return DebugRunLoopView(
        status=stage.status,
        status_label=_status_label(stage.status),
        summary=_debug_loop_summary(
            decision=decision,
            current_iteration=_int_value(payload.get("current_iteration")),
            iterations=iterations,
            next_action=next_action,
            stop_reason=stop_reason,
        ),
        current_iteration=_int_value(payload.get("current_iteration")),
        decision=decision,
        next_action=next_action,
        stop_reason=stop_reason,
        iterations=iterations,
    )


def _debug_loop_summary(
    *,
    decision: str,
    current_iteration: int,
    iterations: list[dict[str, Any]],
    next_action: str,
    stop_reason: str,
) -> str:
    iteration = iterations[-1] if iterations else {}
    pending_probe_count = _int_value(iteration.get("pending_probe_count"))
    completed_probe_count = _int_value(iteration.get("completed_probe_count"))
    if decision == "waiting_for_probe_completion":
        return (
            f"第 {current_iteration} 轮探索已排队 probe，"
            f"{completed_probe_count} 个完成、{pending_probe_count} 个等待；{next_action}"
        )
    if decision == "verified_root_cause_found":
        return f"第 {current_iteration} 轮探索已找到 verified root cause；{stop_reason}"
    if decision == "continue_or_handoff":
        return f"第 {current_iteration} 轮探索未得到 supported 结论；{next_action}"
    if decision == "stopped_evidence_exhausted":
        return f"第 {current_iteration} 轮深度探索已停止；{stop_reason}"
    if decision == "escalated_to_next_iteration":
        return f"已升级到第 {current_iteration} 轮深度探索；{next_action}"
    if decision == "waiting_for_probe_submission":
        return f"第 {current_iteration} 轮探索已生成假设，等待提交受控 probe。"
    if decision == "failed":
        return stop_reason or "循环探索失败。"
    return next_action or "循环探索状态已更新。"


def _int_value(value: object) -> int:
    return int(value) if isinstance(value, int | float) else 0


def _hypothesis_closure_summary(
    *,
    stage: DebugRunStage,
    hypothesis_count: int,
    probe_plan_count: int,
    causal_comparison_count: int,
    verified_root_cause_count: int,
    unverified_hypothesis_count: int,
) -> str:
    if stage.status == "failed":
        return stage.failure_reason or "假设闭环生成失败，当前不能提升根因置信度。"
    if verified_root_cause_count:
        return (
            f"已验证 {verified_root_cause_count} 个根因；"
            f"仍有 {unverified_hypothesis_count} 个候选假设待确认。"
        )
    if hypothesis_count:
        return (
            f"已生成 {hypothesis_count} 个候选假设、{probe_plan_count} 个 probe 计划、"
            f"{causal_comparison_count} 个因果比较；受控 probe 尚未执行，不能提升为已验证根因。"
        )
    return "假设闭环已运行，但没有生成候选假设。"


def _auto_closure_view(stages: list[DebugRunStage]) -> DebugRunSectionStatus:
    related = [
        stage
        for stage in stages
        if stage.stage == "auto_closure"
        or "closure" in stage.stage
        or "verification" in stage.stage
    ]
    if not related:
        return DebugRunSectionStatus(
            status="not_started",
            status_label="未开始",
            summary="尚未进入自动闭环。",
            stage_count=0,
        )
    primary = next((stage for stage in related if stage.stage == "auto_closure"), related[-1])
    return DebugRunSectionStatus(
        status=primary.status,
        status_label=_status_label(primary.status),
        summary=_stage_summary(primary),
        stage_count=len(related),
    )


def _writeback_view(
    *,
    repository: DebugJobRepository,
    job_id: str,
) -> DebugRunWritebackView:
    audit = repository.get_spreadsheet_writeback_audit(job_id)
    if audit is None:
        return DebugRunWritebackView(
            status="not_requested",
            status_label="未请求",
        )
    return DebugRunWritebackView(
        status=audit.status,
        status_label=_status_label(audit.status),
        row_id=audit.row_id,
        report_url=audit.report_url,
        error_message=audit.error_message,
        updated_at=audit.updated_at,
    )


def _current_phase(*, stages: list[DebugRunStage], status: str) -> str:
    if stages:
        running = next((stage for stage in stages if stage.status == "running"), None)
        return (running or stages[-1]).stage
    return status


def _next_step(
    *,
    action_queue: list[dict[str, Any]],
    writeback: DebugRunWritebackView,
) -> str:
    if action_queue:
        for item in action_queue:
            next_operation = str(item.get("next_operation", "")).strip()
            if next_operation:
                return next_operation
    if writeback.status != "succeeded":
        return "确认报告后执行写回。"
    return "查看报告并沉淀结论。"


def _stage_summary(stage: DebugRunStage) -> str:
    summary = stage.output.get("summary")
    if isinstance(summary, str) and summary.strip():
        return summary.strip()
    if stage.failure_reason:
        return stage.failure_reason
    return f"{_stage_label(stage.stage)}{_status_label(stage.status)}。"


def _headline(status: str) -> str:
    return {
        "completed": "Debug 任务已完成",
        "running": "Debug 任务执行中",
        "created": "Debug 任务已创建",
        "cancelled": "Debug 任务已取消",
        "failed": "Debug 任务失败",
    }.get(status, f"Debug 任务{_status_label(status)}")


def _stage_label(stage: str) -> str:
    return {
        "baseline": "基础复测",
        "targeted": "定向复测",
        "hypothesis": "候选根因假设",
        "debug_loop": "循环探索",
        "intervention": "受控干预",
        "causal_comparison": "因果比较",
        "verification": "推荐动作验证",
        "attribution": "归因分析",
        "writeback": "写回",
        "auto_closure": "自动闭环",
        "supplemental_context": "用户补充材料",
    }.get(stage, stage.replace("_", " "))


def _status_label(status: str) -> str:
    return {
        "created": "已创建",
        "pending": "待处理",
        "waiting": "等待中",
        "running": "运行中",
        "completed": "已完成",
        "failed": "失败",
        "cancelled": "已取消",
        "skipped": "跳过",
        "succeeded": "成功",
        "not_requested": "未请求",
        "not_started": "未开始",
        "accepted": "已接受",
        "applied": "已应用",
        "rejected": "需人工",
    }.get(status, status)
