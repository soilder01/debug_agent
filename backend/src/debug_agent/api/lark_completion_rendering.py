from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import cast

from debug_agent.api.badcase_intake_parsers import _clip_text
from debug_agent.api.lark_bot_routes import LarkBotBadcaseDraftCompletionFailedRequest
from debug_agent.reports.generator import DebugReport
from debug_agent.storage.models import DebugJobRow


def _completion_card_root_cause(report: DebugReport | None) -> str:
    if report is None:
        return "报告生成中"
    return f"{report.root_cause.label} / {report.root_cause.confidence}"


def _lark_bot_run_view_summary_lines(report: object | None) -> list[str]:
    run_view = getattr(report, "run_view", {}) if report is not None else {}
    if not isinstance(run_view, dict) or not run_view:
        return []
    summary = run_view.get("summary")
    debug_loop = run_view.get("debug_loop")
    hypothesis_closure = run_view.get("hypothesis_closure")
    writeback = run_view.get("writeback")
    if not isinstance(summary, dict):
        return []
    lines = []
    headline = str(summary.get("headline", "")).strip()
    next_step = str(summary.get("next_step", "")).strip()
    if headline:
        lines.append(f"**统一状态视图**：{headline}")
    if next_step:
        lines.append(f"**下一步**：{next_step}")
    if isinstance(debug_loop, dict):
        lines.extend(_lark_bot_debug_loop_summary_lines(debug_loop))
    if isinstance(hypothesis_closure, dict):
        lines.extend(_lark_bot_hypothesis_closure_summary_lines(hypothesis_closure))
    if isinstance(writeback, dict):
        writeback_label = str(writeback.get("status_label", "")).strip()
        if writeback_label:
            lines.append(f"**写回**：{writeback_label}")
    return lines


def _lark_bot_debug_loop_summary_lines(debug_loop: dict[object, object]) -> list[str]:
    current_iteration = _int_field(debug_loop, "current_iteration")
    decision = str(debug_loop.get("decision", "")).strip()
    next_action = str(debug_loop.get("next_action", "")).strip()
    lines: list[str] = []
    if current_iteration or decision:
        lines.append(f"**循环探索**：第 {current_iteration} 轮 / {decision or 'unknown'}")
    if next_action:
        lines.append(f"**循环下一步**：{next_action}")
    return lines


def _lark_bot_hypothesis_closure_summary_lines(
    hypothesis_closure: dict[object, object],
) -> list[str]:
    lines: list[str] = []
    status_label = str(
        hypothesis_closure.get(
            "status_label",
            hypothesis_closure.get("status", ""),
        )
    ).strip()
    if status_label:
        lines.append(f"**假设闭环**：{status_label}")
    lines.append(
        "**候选假设**："
        f"{_int_field(hypothesis_closure, 'hypothesis_count')} 个，"
        f"已验证根因 {_int_field(hypothesis_closure, 'verified_root_cause_count')} 个，"
        f"未验证 {_int_field(hypothesis_closure, 'unverified_hypothesis_count')} 个"
    )
    probe_results = hypothesis_closure.get("probe_results")
    if isinstance(probe_results, list) and probe_results:
        completed_count = sum(
            1
            for item in probe_results
            if isinstance(item, dict) and str(item.get("status", "")) == "completed"
        )
        lines.append(f"**Probe 结果**：{len(probe_results)} 个，已完成 {completed_count} 个")
    verified_root_causes = hypothesis_closure.get("verified_root_causes")
    if isinstance(verified_root_causes, list):
        first_verified = next(
            (item for item in verified_root_causes if isinstance(item, dict)), None
        )
        if isinstance(first_verified, dict):
            hypothesis_id = str(first_verified.get("hypothesis_id", "")).strip()
            probe_id = str(first_verified.get("probe_id", "")).strip()
            if hypothesis_id or probe_id:
                lines.append(f"**已验证根因**：{hypothesis_id} / {probe_id}")
    fairness_ref = _fairness_lock_ref(hypothesis_closure)
    if fairness_ref:
        lines.append(f"**公平性锁**：{fairness_ref}")
    return lines


def _int_field(data: dict[object, object], key: str) -> int:
    value = data.get(key)
    return value if isinstance(value, int) else 0


def _fairness_lock_ref(data: dict[object, object]) -> str:
    fairness_lock = data.get("fairness_lock")
    if not isinstance(fairness_lock, dict):
        return ""
    value = fairness_lock.get("model_runner_config_ref", "")
    return value if isinstance(value, str) else ""


def _lark_bot_action_queue_summary_line(report: DebugReport | None) -> str:
    action_queue = getattr(report, "action_queue", []) if report is not None else []
    if not isinstance(action_queue, list) or not action_queue:
        return ""
    labels: list[str] = []
    for state in (
        "pending",
        "accepted",
        "ready_to_verify",
        "verifying",
        "verified",
        "needs_manual",
    ):
        matching = [
            item
            for item in action_queue
            if isinstance(item, dict) and str(item.get("state", "pending")) == state
        ]
        if matching:
            label = str(matching[0].get("state_label", state))
            labels.append(f"{label} {len(matching)} 项")
    return f"**Action Queue**：{len(action_queue)} 项，{', '.join(labels)}"


def _lark_bot_action_queue_card_buttons(
    *,
    job: DebugJobRow,
    report: DebugReport | None,
) -> list[dict[str, object]]:
    action_queue = getattr(report, "action_queue", []) if report is not None else []
    if not isinstance(action_queue, list):
        return []
    action_index = _first_recommended_action_queue_index(action_queue)
    if action_index is None:
        return []
    return [
        _lark_callback_button(
            "接受首个动作",
            {"action": "action_queue_accept", "job_id": job.job_id, "action_index": action_index},
            style="primary",
        ),
        _lark_callback_button(
            "验证首个动作",
            {"action": "action_queue_verify", "job_id": job.job_id, "action_index": action_index},
        ),
        _lark_callback_button(
            "转人工处理",
            {"action": "action_queue_manual", "job_id": job.job_id, "action_index": action_index},
        ),
    ]


def _first_recommended_action_queue_index(action_queue: list[object]) -> int | None:
    for item in action_queue:
        if not isinstance(item, dict):
            continue
        if str(item.get("kind", "")) != "recommended_action":
            continue
        item_id = str(item.get("id", ""))
        if item_id.startswith("recommended:"):
            try:
                return int(item_id.split(":", 1)[1])
            except ValueError:
                return None
    return None


def _lark_callback_button(
    label: str,
    value: dict[str, object],
    *,
    style: str = "default",
) -> dict[str, object]:
    return {
        "tag": "button",
        "text": {"tag": "plain_text", "content": label},
        "type": style,
        "value": value,
        "behaviors": [{"type": "callback", "value": value}],
    }


def _lark_url_button(label: str, url: str, *, style: str = "default") -> dict[str, object]:
    return {
        "tag": "button",
        "text": {"tag": "plain_text", "content": label},
        "type": style,
        "url": url,
    }


def _debug_report_has_agent_traces(report: object) -> bool:
    agent_traces = getattr(report, "agent_traces", [])
    return isinstance(agent_traces, list) and bool(agent_traces)


def _markdown_dict_items(items: list[dict[str, object]]) -> list[str]:
    lines: list[str] = []
    for item in items[:20]:
        compact = json.dumps(item, ensure_ascii=False, separators=(",", ":"))
        lines.append(f"- `{_clip_text(compact, 500)}`")
    return lines


def _is_lark_document_url(url: str) -> bool:
    normalized = url.lower()
    return "/docx/" in normalized and (
        "larkoffice.com" in normalized or "feishu.cn" in normalized or "doubao.com" in normalized
    )


def _lark_bot_completion_report_summary_lines(report: DebugReport) -> list[str]:
    lines = [
        f"- 根因判断：{report.root_cause.label} / {report.root_cause.confidence}",
    ]
    evidence_summary = report.root_cause.evidence_summary.strip()
    if evidence_summary:
        lines.append(f"- 根因证据：{_clip_text(evidence_summary, 180)}")
    if report.recommended_actions:
        first_action = report.recommended_actions[0]
        summary = str(first_action.get("summary", "")).strip()
        priority = str(first_action.get("priority", "")).strip()
        if summary:
            prefix = f"{priority} / " if priority else ""
            lines.append(f"- 推荐动作：{prefix}{_clip_text(summary, 160)}")
    return lines


def _lark_bot_completion_delivery_failure_state(error_message: str) -> dict[str, object]:
    if not error_message.strip():
        return {}
    try:
        data = json.loads(error_message)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    state = data.get("completion_delivery_failure")
    return cast(dict[str, object], state) if isinstance(state, dict) else {}


def _lark_bot_completion_delivery_failure_message(
    *,
    attempts: int,
    max_attempts: int,
    request: LarkBotBadcaseDraftCompletionFailedRequest,
) -> str:
    return json.dumps(
        {
            "completion_delivery_failure": {
                "attempts": attempts,
                "max_attempts": max_attempts,
                "last_error": _clip_text(request.error_message or request.note, 1_000),
                "note": _clip_text(request.note, 500),
                "failed_at": datetime.now(UTC).isoformat(timespec="seconds"),
            }
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
