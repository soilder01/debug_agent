from __future__ import annotations

import hashlib

from debug_agent.assistant.knowledge_base import DebugLesson
from debug_agent.jobs.auto_closure import AutoDebugClosureResult
from debug_agent.reports.generator import DebugReport


def build_debug_lesson_from_report(
    *,
    report: DebugReport,
    closure: AutoDebugClosureResult,
    source_uri: str = "",
    approved: bool = False,
) -> DebugLesson:
    failure_summary = (
        report.observed_failure.summary
        or report.root_cause.evidence_summary
        or f"Debug case {report.case_id}"
    )
    root_cause, confidence = _root_cause_and_confidence(report=report, closure=closure)
    debug_loop_decision = str(closure.debug_loop.get("decision", "") or "not_recorded")
    evidence_boundary = _evidence_boundary(closure)
    recommended_action = _recommended_action(report=report, closure=closure)
    lesson_id = _lesson_id(
        job_id=str(report.job_id or closure.source_job_id),
        case_id=report.case_id,
        failure_summary=failure_summary,
        debug_loop_decision=debug_loop_decision,
    )
    return DebugLesson(
        lesson_id=lesson_id,
        job_id=str(report.job_id or closure.source_job_id),
        case_id=report.case_id,
        failure_summary=failure_summary,
        root_cause=root_cause,
        confidence=confidence,
        debug_loop_decision=debug_loop_decision,
        evidence_boundary=evidence_boundary,
        recommended_action=recommended_action,
        source_uri=source_uri,
        approved=approved,
    )


def _root_cause_and_confidence(
    *,
    report: DebugReport,
    closure: AutoDebugClosureResult,
) -> tuple[str, str]:
    if closure.final_attribution_candidates:
        first = closure.final_attribution_candidates[0]
        return (
            str(first.get("category", report.root_cause.label)),
            str(first.get("confidence", report.root_cause.confidence)),
        )
    return report.root_cause.label, report.root_cause.confidence


def _evidence_boundary(closure: AutoDebugClosureResult) -> str:
    evidence_count = len(closure.evidence_summaries)
    debug_loop = closure.debug_loop if isinstance(closure.debug_loop, dict) else {}
    decision = str(debug_loop.get("decision", "")).strip()
    stop_reason = str(debug_loop.get("stop_reason", "")).strip()
    if decision == "stopped_evidence_exhausted":
        return (
            f"已审阅 {evidence_count} 条 evidence；{stop_reason or '达到探索预算后仍没有 supported causal comparison。'}"
        )
    if decision == "verified_root_cause_found":
        return f"已审阅 {evidence_count} 条 evidence，并形成 supported causal comparison。"
    if evidence_count:
        return f"已审阅 {evidence_count} 条 evidence；debug_loop={decision or 'not_recorded'}。"
    return "当前 lesson 没有 evidence_summaries，不能作为高置信经验。"


def _recommended_action(*, report: DebugReport, closure: AutoDebugClosureResult) -> str:
    if report.recommended_actions:
        first = report.recommended_actions[0]
        if isinstance(first, dict):
            summary = str(first.get("summary", "")).strip()
            priority = str(first.get("priority", "")).strip()
            if summary:
                return f"{priority}：{summary}" if priority else summary
    next_action = str(closure.debug_loop.get("next_action", "")).strip()
    if next_action:
        return next_action
    if closure.writeback_status and closure.writeback_status != "succeeded":
        return f"报告复核后再决定是否写回；当前写回状态为 {closure.writeback_status}。"
    return "人工复核报告证据后决定下一步。"


def _lesson_id(
    *,
    job_id: str,
    case_id: str,
    failure_summary: str,
    debug_loop_decision: str,
) -> str:
    digest = hashlib.sha1(
        f"{job_id}:{case_id}:{failure_summary}:{debug_loop_decision}".encode("utf-8")
    ).hexdigest()[:16]
    return f"lesson-{case_id}-{digest}"
