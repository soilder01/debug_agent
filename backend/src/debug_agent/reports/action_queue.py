from __future__ import annotations

from collections import Counter
from typing import Any

from debug_agent.reports.generator import DebugReport
from debug_agent.storage.repository import (
    DebugJobRepository,
    RecommendedActionStatus,
    RecommendedActionVerification,
)

ACTION_QUEUE_STATE_LABELS = {
    "pending": "待处理",
    "accepted": "已接受",
    "ready_to_verify": "待验证",
    "verifying": "验证中",
    "verified": "已通过",
    "needs_manual": "需人工",
}


def build_action_queue(
    *,
    repository: DebugJobRepository,
    job_id: str,
    report: DebugReport,
) -> list[dict[str, Any]]:
    statuses = {
        status.action_index: status
        for status in repository.list_recommended_action_statuses(job_id)
    }
    verifications_by_index = _latest_verification_by_index(
        repository.list_recommended_action_verifications(job_id)
    )
    verification_results_by_job_id = {
        str(result.get("verification_job_id", "")): result
        for result in report.verification_results
        if str(result.get("verification_job_id", ""))
    }
    writeback_audit = repository.get_spreadsheet_writeback_audit(job_id)
    return [
        _recommended_action_queue_item(
            action=action,
            action_index=index,
            status=statuses.get(index),
            verification=verifications_by_index.get(index),
            verification_results_by_job_id=verification_results_by_job_id,
            writeback_status=writeback_audit.status
            if writeback_audit is not None
            else "not_requested",
            writeback_row_id=writeback_audit.row_id if writeback_audit is not None else "",
            writeback_report_url=writeback_audit.report_url if writeback_audit is not None else "",
        )
        for index, action in enumerate(report.recommended_actions)
    ]


def summarize_action_queue(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(item.get("state", "pending")) for item in items)
    return {
        "total": len(items),
        "pending": counts["pending"],
        "accepted": counts["accepted"],
        "ready_to_verify": counts["ready_to_verify"],
        "verifying": counts["verifying"],
        "verified": counts["verified"],
        "needs_manual": counts["needs_manual"],
    }


def _latest_verification_by_index(
    verifications: list[RecommendedActionVerification],
) -> dict[int, RecommendedActionVerification]:
    latest: dict[int, RecommendedActionVerification] = {}
    for verification in verifications:
        latest[verification.action_index] = verification
    return latest


def _recommended_action_queue_item(
    *,
    action: dict[str, str],
    action_index: int,
    status: RecommendedActionStatus | None,
    verification: RecommendedActionVerification | None,
    verification_results_by_job_id: dict[str, dict[str, object]],
    writeback_status: str,
    writeback_row_id: str,
    writeback_report_url: str,
) -> dict[str, Any]:
    verification_result = (
        verification_results_by_job_id.get(verification.verification_job_id)
        if verification is not None
        else None
    )
    raw_status = _action_status(action=action, status=status)
    state = _action_queue_state(
        raw_status=raw_status,
        verification=verification,
        verification_result=verification_result,
    )
    title = (
        action.get("summary", "").strip() or action.get("detail", "").strip() or "未填写动作摘要"
    )
    return {
        "id": f"recommended:{action_index}",
        "kind": "recommended_action",
        "title": title,
        "detail": action.get("detail", "").strip(),
        "priority": action.get("priority", f"P{action_index}").strip() or f"P{action_index}",
        "state": state,
        "state_label": ACTION_QUEUE_STATE_LABELS.get(state, state),
        "source": action.get("category", "recommended_action").strip() or "recommended_action",
        "source_ref": f"report.recommended_actions[{action_index}]",
        "owner": _action_owner(action=action, status=status, verification=verification),
        "status": raw_status,
        "status_updated_at": status.updated_at if status is not None else "",
        "verification_job_id": verification.verification_job_id if verification is not None else "",
        "verification_result": str(verification_result.get("result", "pending"))
        if verification_result is not None
        else "",
        "verification_summary": str(verification_result.get("summary", ""))
        if verification_result is not None
        else "",
        "writeback_status": writeback_status,
        "writeback_row_id": writeback_row_id,
        "writeback_report_url": writeback_report_url,
        "evidence_ids": action.get("evidence_ids", ""),
        "artifact_ids": action.get("artifact_ids", ""),
        "trace_refs": action.get("trace_refs", ""),
        "available_operations": _available_operations(
            state=state, writeback_status=writeback_status
        ),
        "next_operation": _next_operation(state=state, writeback_status=writeback_status),
    }


def _action_status(*, action: dict[str, str], status: RecommendedActionStatus | None) -> str:
    if status is not None and status.status:
        return status.status
    return action.get("status", "pending").strip() or "pending"


def _action_owner(
    *,
    action: dict[str, str],
    status: RecommendedActionStatus | None,
    verification: RecommendedActionVerification | None,
) -> str:
    if verification is not None and verification.actor.strip():
        return verification.actor.strip()
    if status is not None and status.actor.strip():
        return status.actor.strip()
    return (
        action.get("owner", "").strip()
        or action.get("recommended_owner", "").strip()
        or "debug_agent_operator"
    )


def _action_queue_state(
    *,
    raw_status: str,
    verification: RecommendedActionVerification | None,
    verification_result: dict[str, object] | None,
) -> str:
    result = str(verification_result.get("result", "")) if verification_result is not None else ""
    if result == "resolved":
        return "verified"
    if result in {"not_resolved", "regressed", "inconclusive"}:
        return "needs_manual"
    if verification is not None:
        return "verifying"
    if raw_status == "rejected":
        return "needs_manual"
    if raw_status == "applied":
        return "ready_to_verify"
    if raw_status == "accepted":
        return "accepted"
    return "pending"


def _available_operations(*, state: str, writeback_status: str) -> list[str]:
    operations: list[str] = []
    if state in {"pending", "accepted"}:
        operations.append("accept")
    if state in {"pending", "accepted", "ready_to_verify", "needs_manual"}:
        operations.append("mark_applied")
    operations.append("verify")
    operations.append("writeback")
    operations.append("manual_handoff")
    return operations


def _next_operation(*, state: str, writeback_status: str) -> str:
    if state == "verified" and writeback_status == "succeeded":
        return "已验证通过并写回，可以沉淀修复结论。"
    if state == "verified":
        return "确认报告后执行写回。"
    if state == "verifying":
        return "等待验证任务完成"
    if state == "ready_to_verify":
        return "创建验证任务"
    if state == "accepted":
        return "应用动作后标记已应用"
    if state == "needs_manual":
        return "转人工复核"
    return "接受或拒绝该动作"
