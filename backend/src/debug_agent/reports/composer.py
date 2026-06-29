from __future__ import annotations

import re

from debug_agent.reports.generator import DebugReport


def build_decision_brief_lines(*, report: DebugReport, closure: object) -> list[str]:
    final_label = _final_attribution_label(report=report, closure=closure)
    final_summary = _final_attribution_summary(report=report, closure=closure)
    root_cause_resolution = _root_cause_resolution_line(closure)
    evidence_boundary = _evidence_boundary_summary(report=report, closure=closure)
    return [
        "## 第一层：一页看懂",
        "",
        "## 一页看懂",
        "",
        "这份报告先回答用户最关心的 5 个问题：结论是什么、为什么可信、系统跑了什么、还要做什么、结果能不能写回。",
        "",
        "### 首屏摘要",
        "",
        f"1. **最终判断**：{final_label}。{_table_text(final_summary)}",
        f"2. **证据边界**：{evidence_boundary}",
        f"3. **建议动作**：{_next_action_summary(report=report, closure=closure)}",
        "",
        "### 结论总览",
        "",
        "| 问题 | 当前结论 |",
        "| --- | --- |",
        f"| 这次失败是什么 | {_table_text(report.observed_failure.summary or report.root_cause.evidence_summary)} |",
        f"| 最终归因 | {final_label}：{_table_text(final_summary)} |",
        f"| 是否找到可验证根因 | {root_cause_resolution} |",
        f"| 系统到底跑了什么 | {_pipeline_summary(closure)} |",
        f"| 为什么可信 | {_trust_summary(closure)} |",
        f"| 已排除/弱化什么 | {_ruled_out_summary(closure)} |",
        f"| 仍缺什么证据 | {_missing_evidence_summary(closure)} |",
        f"| 后续动作 | {_next_action_summary(report=report, closure=closure)} |",
        f"| 写回状态 | `{_closure_attr(closure, 'writeback_status') or 'not_requested'}` |",
        "",
        "### 本次探索路线",
        "",
        *_debug_loop_route_lines(closure),
        "",
    ]


def build_debug_run_view_lines(*, report: DebugReport) -> list[str]:
    run_view = getattr(report, "run_view", {})
    if not isinstance(run_view, dict) or not run_view:
        return []
    summary = run_view.get("summary")
    auto_closure = run_view.get("auto_closure")
    debug_loop = run_view.get("debug_loop")
    hypothesis_closure = run_view.get("hypothesis_closure")
    writeback = run_view.get("writeback")
    action_queue = run_view.get("action_queue")
    if not isinstance(summary, dict):
        return []
    lines = ["## 调试过程一览", ""]
    lines.append("这一节把内部运行状态翻译成用户可读的过程：现在在哪、做过哪些验证、为什么停在这里。")
    lines.append("")
    headline = str(summary.get("headline", "")).strip()
    current_phase = str(summary.get("current_phase", "")).strip()
    next_step = str(summary.get("next_step", "")).strip()
    if headline:
        lines.append(f"- 统一状态：{headline}")
    if current_phase:
        lines.append(f"- 当前阶段：`{current_phase}`")
    if next_step:
        lines.append(f"- 下一步：{next_step}")
    if isinstance(auto_closure, dict):
        lines.append(
            f"- 自动闭环：{auto_closure.get('status_label', auto_closure.get('status', '未知'))}"
        )
    if isinstance(debug_loop, dict):
        lines.extend(_debug_loop_run_view_lines(debug_loop))
    if isinstance(hypothesis_closure, dict):
        lines.extend(_hypothesis_closure_run_view_lines(hypothesis_closure))
    if isinstance(writeback, dict):
        lines.append(f"- 写回：{writeback.get('status_label', writeback.get('status', '未知'))}")
    if isinstance(action_queue, dict):
        action_summary = action_queue.get("summary")
        if isinstance(action_summary, dict):
            lines.append(f"- Action Queue：{action_summary.get('total', 0)} 项")
    lines.append("")
    return lines


def _debug_loop_run_view_lines(debug_loop: dict[object, object]) -> list[str]:
    current_iteration = _int_value(debug_loop.get("current_iteration"))
    decision = str(debug_loop.get("decision", "")).strip()
    next_action = str(debug_loop.get("next_action", "")).strip()
    stop_reason = str(debug_loop.get("stop_reason", "")).strip()
    summary = str(debug_loop.get("summary", "")).strip()
    lines = [
        f"- 循环探索：第 {current_iteration} 轮 / `{decision or 'unknown'}`",
    ]
    if next_action:
        lines.append(f"- 循环下一步：{_table_text(next_action)}")
    if stop_reason:
        lines.append(f"- 循环决策：{_table_text(stop_reason)}")
    if summary:
        lines.append(f"- 循环摘要：{_table_text(summary)}")
    iterations = debug_loop.get("iterations")
    if isinstance(iterations, list):
        for item in iterations[:3]:
            if not isinstance(item, dict):
                continue
            lines.append(
                "- 循环轮次明细："
                f"第 {_int_value(item.get('iteration'))} 轮 / "
                f"{str(item.get('decision', '')).strip() or 'unknown'} / "
                f"pending={_int_value(item.get('pending_probe_count'))} / "
                f"completed={_int_value(item.get('completed_probe_count'))} / "
                f"supported={_int_value(item.get('supported_comparison_count'))}"
            )
    return lines


def _hypothesis_closure_run_view_lines(hypothesis_closure: dict[object, object]) -> list[str]:
    status_label = str(
        hypothesis_closure.get(
            "status_label",
            hypothesis_closure.get("status", "未知"),
        )
    )
    summary = str(hypothesis_closure.get("summary", "")).strip()
    fairness_lock = hypothesis_closure.get("fairness_lock")
    model_runner_ref = ""
    if isinstance(fairness_lock, dict):
        model_runner_ref = str(fairness_lock.get("model_runner_config_ref", "")).strip()
    lines = [
        f"- 假设闭环：{status_label}",
        f"- 候选假设：{_int_value(hypothesis_closure.get('hypothesis_count'))} 个",
        f"- Probe 计划：{_int_value(hypothesis_closure.get('probe_plan_count'))} 个",
        f"- Probe 结果：{_int_value(hypothesis_closure.get('probe_result_count'))} 个",
        f"- 因果比较：{_int_value(hypothesis_closure.get('causal_comparison_count'))} 个",
        f"- 已验证根因：{_int_value(hypothesis_closure.get('verified_root_cause_count'))} 个",
        f"- 未验证假设：{_int_value(hypothesis_closure.get('unverified_hypothesis_count'))} 个",
    ]
    lines.extend(_hypothesis_probe_result_lines(hypothesis_closure))
    lines.extend(_verified_root_cause_lines(hypothesis_closure))
    if model_runner_ref:
        lines.append(f"- 公平性锁：`{model_runner_ref}`")
    if summary:
        lines.append(f"- 假设闭环摘要：{summary}")
    return lines


def _int_value(value: object) -> int:
    return value if isinstance(value, int) else 0


def _hypothesis_probe_result_lines(hypothesis_closure: dict[object, object]) -> list[str]:
    probe_results = hypothesis_closure.get("probe_results")
    if not isinstance(probe_results, list):
        return []
    completed = [
        item
        for item in probe_results
        if isinstance(item, dict) and str(item.get("status", "")) == "completed"
    ]
    if not completed:
        return []
    completed_runner = [
        item for item in completed if str(item.get("probe_job_id", "")).strip()
    ]
    completed_non_runner_count = len(completed) - len(completed_runner)
    lines = [
        (
            f"- 已完成 probe：{len(completed)} 个"
            f"（runner {len(completed_runner)} 个 / non-runner {completed_non_runner_count} 个）"
        )
    ]
    for item in completed[:5]:
        probe_id = str(item.get("probe_id", "")).strip()
        probe_job_id = str(item.get("probe_job_id", "")).strip()
        evidence_ids = item.get("evidence_ids")
        evidence_text = ""
        if isinstance(evidence_ids, list):
            evidence_text = ", ".join(f"`{str(evidence_id)}`" for evidence_id in evidence_ids[:5])
        lines.append(
            f"- Probe 结果明细：`{probe_id}` / job `{probe_job_id}` / evidence {evidence_text or 'none'}"
        )
    return lines


def _verified_root_cause_lines(hypothesis_closure: dict[object, object]) -> list[str]:
    verified_root_causes = hypothesis_closure.get("verified_root_causes")
    if not isinstance(verified_root_causes, list):
        return []
    lines: list[str] = []
    for item in verified_root_causes[:5]:
        if not isinstance(item, dict):
            continue
        hypothesis_id = str(item.get("hypothesis_id", "")).strip()
        probe_id = str(item.get("probe_id", "")).strip()
        summary = _table_text(str(item.get("summary", "")).strip())
        lines.append(f"- 已验证根因明细：`{hypothesis_id}` / `{probe_id}`：{summary}")
    return lines


def build_next_action_lines(*, report: DebugReport, closure: object) -> list[str]:
    lines = ["## 后续动作清单", ""]
    action_number = 1
    action_queue = getattr(report, "action_queue", [])
    if action_queue:
        lines.extend(["### Action Queue", ""])
        for item in action_queue:
            priority = str(item.get("priority", f"P{action_number}"))
            state_label = str(item.get("state_label", item.get("state", "pending")))
            title = str(item.get("title", "")).strip() or "未填写动作摘要"
            owner = str(item.get("owner", "debug_agent_operator"))
            verification_job_id = str(item.get("verification_job_id", ""))
            writeback_status = str(item.get("writeback_status", "not_requested"))
            lines.append(f"{action_number}. `{priority}` / {state_label}：{title}")
            lines.append(f"   - 负责人：{owner}")
            if verification_job_id:
                lines.append(f"   - 验证任务：`{verification_job_id}`")
            lines.append(f"   - 写回状态：`{writeback_status}`")
            next_operation = str(item.get("next_operation", ""))
            if next_operation:
                lines.append(f"   - 下一步：{next_operation}")
            action_number += 1
    elif report.recommended_actions:
        for action in report.recommended_actions:
            priority = str(action.get("priority", f"P{action_number}"))
            status = str(action.get("status", "pending"))
            summary = str(action.get("summary", "")).strip() or "未填写动作摘要"
            detail = str(action.get("detail", "")).strip()
            lines.append(f"{action_number}. `{priority}` / `{status}`：{summary}")
            if detail and detail != summary:
                lines.append(f"   - 说明：{detail}")
            action_number += 1
    else:
        lines.append(f"{action_number}. 当前没有可直接执行的推荐动作，需要先补充证据或人工复核。")
        action_number += 1
    verification_jobs = _closure_list_attr(closure, "created_verification_jobs")
    if verification_jobs:
        lines.append(
            f"{action_number}. 已创建推荐动作验证任务：{', '.join(f'`{job_id}`' for job_id in verification_jobs)}。"
        )
        action_number += 1
    writeback_status = _closure_attr(closure, "writeback_status") or "not_requested"
    if writeback_status != "succeeded":
        lines.append(
            f"{action_number}. 写回状态为 `{writeback_status}`，需要在确认报告无误后再执行表格/Base 写回。"
        )
    lines.append("")
    return lines


def build_supplemental_context_lines(*, report: DebugReport) -> list[str]:
    if not report.supplemental_contexts:
        return []
    lines = [
        "## 用户补充材料",
        "",
        "任务执行中追加的上下文会保留在这里，后续归因、复核和报告审计都应参考这些信息。",
        "",
    ]
    for index, context in enumerate(report.supplemental_contexts, start=1):
        text = _table_text(str(context.get("text", ""))).strip() or "未记录补充文本"
        message_id = _table_text(str(context.get("message_id", ""))).strip() or "unknown"
        attachment_count = str(context.get("attachment_count", 0))
        lines.append(f"{index}. 飞书消息 `{message_id}` / 附件数 `{attachment_count}`：{text}")
    lines.append("")
    return lines


def build_evidence_chain_intro_lines(*, report: DebugReport, closure: object) -> list[str]:
    evidence_ids = (
        report.experiment_summary.evidence_ids if report.experiment_summary is not None else []
    )
    confidence = _human_confidence(report.root_cause.confidence)
    sources = _evidence_source_summary(report=report, closure=closure)
    return [
        "## 第二层：证据链",
        "",
        f"- 证据来源：{sources}",
        f"- 置信度解释：{confidence}；{_confidence_reason_summary(report)}",
        f"- 关键 evidence：{', '.join(f'`{item}`' for item in evidence_ids[:8]) if evidence_ids else '暂无'}",
        "",
    ]


def build_audit_appendix_intro_lines(*, report: DebugReport) -> list[str]:
    trace_count = len(report.agent_traces)
    return [
        "## 第三层：审计附录",
        "",
        f"- Agent trace 数量：{trace_count}",
        "- 审计范围：原始输入、Prompt 改动、Agent 输入与可见输出、阶段方法解释。",
        "",
    ]


def build_product_summary(*, report: DebugReport, closure: object | None = None) -> dict[str, str]:
    resolved_closure = closure or object()
    return {
        "root_cause_label": _final_attribution_label(report=report, closure=resolved_closure),
        "failure_summary": _table_text(
            report.observed_failure.summary or report.root_cause.evidence_summary
        ),
        "evidence_source": _evidence_source_summary(report=report, closure=resolved_closure),
        "confidence_explanation": (
            f"{_human_confidence(report.root_cause.confidence)}；{_confidence_reason_summary(report)}"
        ),
        "next_action": _next_action_summary(report=report, closure=resolved_closure),
    }


def validate_product_report_markdown(markdown: str) -> list[str]:
    violations: list[str] = []
    normalized = markdown.strip()
    if not normalized:
        return [
            "missing_decision_brief",
            "missing_evidence_chain",
            "missing_audit_appendix",
            "missing_next_actions",
            "missing_confidence_explanation",
            "missing_evidence_source",
        ]
    if normalized.startswith("{") and normalized.endswith("}"):
        violations.append("json_only_report")
    if "## 第一层：一页看懂" not in markdown or "## 一页看懂" not in markdown:
        violations.append("missing_decision_brief")
    if "## 第二层：证据链" not in markdown or "## 证据明细" not in markdown:
        violations.append("missing_evidence_chain")
    if "## 第三层：审计附录" not in markdown or "## Agent 输入与推理摘要" not in markdown:
        violations.append("missing_audit_appendix")
    if "## 后续动作清单" not in markdown:
        violations.append("missing_next_actions")
    if "置信度解释" not in markdown and "为什么可信" not in markdown:
        violations.append("missing_confidence_explanation")
    if "证据来源" not in markdown:
        violations.append("missing_evidence_source")
    if _has_untranslated_internal_terms(markdown):
        violations.append("raw_internal_terms_without_human_translation")
    return violations


def _final_attribution_label(*, report: DebugReport, closure: object) -> str:
    candidates = _closure_list_attr(closure, "final_attribution_candidates")
    if candidates:
        first = candidates[0]
        if isinstance(first, dict):
            category = str(first.get("category", report.root_cause.label))
            confidence = str(first.get("confidence", report.root_cause.confidence))
            return _human_label_with_confidence(category, confidence)
    return _human_label_with_confidence(report.root_cause.label, report.root_cause.confidence)


def _final_attribution_summary(*, report: DebugReport, closure: object) -> str:
    candidates = _closure_list_attr(closure, "final_attribution_candidates")
    if candidates:
        first = candidates[0]
        if isinstance(first, dict):
            summary = str(first.get("summary", "")).strip()
            if summary:
                return summary
    return report.root_cause.evidence_summary


def _pipeline_summary(closure: object) -> str:
    steps = ["原始坏案", "baseline 原条件复测"]
    if _closure_list_attr(closure, "created_targeted_probe_jobs"):
        steps.append("targeted 定向深挖")
    if _closure_list_attr(closure, "created_strategy_follow_up_jobs"):
        steps.append("strategy 稳定性跟进")
    if _closure_list_attr(closure, "created_verification_jobs"):
        steps.append("verification 推荐动作验证")
    steps.append("最终归因")
    return " → ".join(steps)


def _trust_summary(closure: object) -> str:
    parts = ["baseline 用原条件复现问题"]
    if _closure_list_attr(closure, "created_targeted_probe_jobs") or _closure_list_attr(
        closure, "created_verification_jobs"
    ):
        parts.append("targeted/verification 用失败目标和推荐动作复核结论")
    comparison = _closure_dict_attr(closure, "badcase_live_comparison")
    live_rerun = str(comparison.get("live_rerun", "")).strip()
    if live_rerun:
        parts.append(live_rerun)
    return "；".join(parts)


def _root_cause_resolution_line(closure: object) -> str:
    debug_loop = _closure_dict_attr(closure, "debug_loop")
    decision = str(debug_loop.get("decision", "")).strip()
    iteration = _int_value(debug_loop.get("current_iteration"))
    if decision == "verified_root_cause_found":
        return f"已在第 {iteration or 1} 轮找到 supported causal comparison。"
    if decision == "stopped_evidence_exhausted":
        reason = str(debug_loop.get("stop_reason", "")).strip()
        return (
            f"没有找到可验证根因；第 {iteration or 1} 轮后证据预算耗尽"
            f"（{_table_text(reason) or '没有 supported causal comparison'}）。"
        )
    verified = _closure_list_attr(closure, "verified_root_causes")
    if verified:
        return f"已找到 {len(verified)} 个候选 verified root cause。"
    if decision:
        return f"尚未最终收口，当前循环状态为 `{decision}`。"
    if _closure_list_attr(closure, "final_attribution_candidates"):
        return "已有最终归因候选，但仍需结合证据链人工复核。"
    return "没有形成 verified root cause，需补充证据或人工复核。"


def _evidence_boundary_summary(*, report: DebugReport, closure: object) -> str:
    debug_loop = _closure_dict_attr(closure, "debug_loop")
    evidence_count = len(_closure_list_attr(closure, "evidence_summaries"))
    if evidence_count == 0 and report.experiment_summary is not None:
        evidence_count = len(report.experiment_summary.evidence_ids)
    decision = str(debug_loop.get("decision", "")).strip()
    if decision == "stopped_evidence_exhausted":
        return (
            f"已审阅 {evidence_count} 条 evidence 和多轮 probe；仍没有 supported comparison，"
            "因此报告不会把猜测包装成确定根因。"
        )
    if decision == "verified_root_cause_found":
        return f"已审阅 {evidence_count} 条 evidence，并通过受控 probe 形成 supported comparison。"
    return f"当前证据量 {evidence_count} 条；可信度需结合证据地图、关键证据卡片和审计附录判断。"


def _ruled_out_summary(closure: object) -> str:
    debug_loop = _closure_dict_attr(closure, "debug_loop")
    iterations = debug_loop.get("iterations")
    if not isinstance(iterations, list):
        return "暂无可明确排除项。"
    weak_iterations = [
        item
        for item in iterations
        if isinstance(item, dict)
        and _int_value(item.get("causal_comparison_count")) > 0
        and _int_value(item.get("supported_count")) == 0
    ]
    if not weak_iterations:
        return "没有被明确证伪的假设；报告以现有 supported evidence 收口。"
    return f"{len(weak_iterations)} 轮因果比较没有 supported 结果，对应假设被弱化。"


def _missing_evidence_summary(closure: object) -> str:
    debug_loop = _closure_dict_attr(closure, "debug_loop")
    decision = str(debug_loop.get("decision", "")).strip()
    stop_reason = _table_text(str(debug_loop.get("stop_reason", "")).strip())
    if decision == "stopped_evidence_exhausted":
        return stop_reason or "需要新增 probe、人工标注或更强对照样本。"
    if decision in {"waiting_for_probe_completion", "waiting_for_probe_submission"}:
        return "还需要 probe job 完成并回流 evidence。"
    return "如需提升置信度，可继续补充同类样本、人工标注和 targeted replay。"


def _debug_loop_route_lines(closure: object) -> list[str]:
    debug_loop = _closure_dict_attr(closure, "debug_loop")
    iterations = debug_loop.get("iterations")
    if not isinstance(iterations, list) or not iterations:
        return ["- 暂无多轮自动探索记录；请查看证据链和审计附录。"]
    lines = ["| 轮次 | 系统做了什么 | 结果 | 下一步/停止原因 |", "| --- | --- | --- | --- |"]
    for item in iterations[:5]:
        if not isinstance(item, dict):
            continue
        iteration = _int_value(item.get("iteration"))
        probe_plan_count = _int_value(item.get("probe_plan_count"))
        completed_probe_count = _int_value(item.get("completed_probe_count"))
        comparison_count = _int_value(item.get("causal_comparison_count"))
        supported_count = _int_value(item.get("supported_count"))
        decision = str(item.get("decision", "")).strip() or "unknown"
        stop_reason = _table_text(str(item.get("stop_reason", "")).strip())
        next_action = _table_text(str(item.get("next_action", "")).strip())
        lines.append(
            "| "
            f"第 {iteration} 轮 | "
            f"生成 {probe_plan_count} 个 probe 计划，完成 {completed_probe_count} 个 probe，"
            f"形成 {comparison_count} 个因果比较 | "
            f"`{decision}`，supported={supported_count} | "
            f"{stop_reason or next_action or '继续观察'} |"
        )
    if len(iterations) > 5:
        lines.append(f"| 其余 | 还有 {len(iterations) - 5} 轮详见审计附录 | - | - |")
    return lines


def _evidence_source_summary(*, report: DebugReport, closure: object) -> str:
    parts: list[str] = []
    if report.experiment_summary is not None:
        parts.append(f"{report.experiment_summary.total_trials} 次 baseline/实验 evidence")
    if _closure_list_attr(closure, "created_targeted_probe_jobs"):
        parts.append("定向深挖任务")
    if _closure_list_attr(closure, "created_verification_jobs"):
        parts.append("推荐动作验证任务")
    if report.supplemental_contexts:
        parts.append("用户补充材料")
    return "、".join(parts) if parts else "暂无结构化证据"


def _confidence_reason_summary(report: DebugReport) -> str:
    if report.confidence_reasons:
        first = report.confidence_reasons[0]
        summary = str(first.get("summary", "")).strip()
        source = str(first.get("source", "")).strip()
        if summary and source:
            return f"{summary} 来源：{source}。"
        if summary:
            return summary
    if report.experiment_summary is not None:
        return (
            f"成功率 {report.experiment_summary.success_rate:.2f}，"
            f"稳定性 `{report.experiment_summary.stability_label}`。"
        )
    return "当前报告没有足够统计信号，需人工复核。"


def _next_action_summary(*, report: DebugReport, closure: object) -> str:
    if report.recommended_actions:
        first = report.recommended_actions[0]
        priority = str(first.get("priority", "P0"))
        summary = str(first.get("summary", "")).strip() or "查看推荐动作详情"
        return f"{priority}：{summary}"
    if _closure_list_attr(closure, "created_verification_jobs"):
        return "等待/查看推荐动作验证任务结果"
    return "人工复核报告证据后决定是否写回"


def _closure_attr(closure: object, name: str) -> str:
    value = getattr(closure, name, "")
    return str(value).strip() if value is not None else ""


def _closure_list_attr(closure: object, name: str) -> list[object]:
    value = getattr(closure, name, [])
    return value if isinstance(value, list) else []


def _closure_dict_attr(closure: object, name: str) -> dict[str, object]:
    value = getattr(closure, name, {})
    return value if isinstance(value, dict) else {}


def _table_text(value: str) -> str:
    return " ".join(str(value).replace("|", "\\|").split())


def _human_label_with_confidence(label: str, confidence: str) -> str:
    return human_label_with_confidence(label, confidence)


def human_label_with_confidence(label: str, confidence: str) -> str:
    return f"{_human_term(label)} / {_human_confidence(confidence)}"


def _human_term(value: str) -> str:
    normalized = value.strip()
    return {
        "model_instability": "模型时序输出不稳定",
        "video_timestamp_boundary_error": "视频时间边界定位失败",
        "prompt_scoring_alignment_gap": "提示词与评分规则未对齐",
        "answer_mismatch": "答案与标答不一致",
        "model_call_error": "模型调用失败",
        "parse_error": "输出解析失败",
        "evaluation_asset_issue": "评测资产问题",
    }.get(normalized, normalized.replace("_", " "))


def _human_confidence(value: str) -> str:
    normalized = value.strip().lower()
    return {
        "high": "高置信",
        "medium": "中置信",
        "low": "低置信",
        "unknown": "置信度未知",
    }.get(normalized, value or "置信度未知")


def _has_untranslated_internal_terms(markdown: str) -> bool:
    for raw_term in ("model_instability/high", "model_instability / high"):
        if raw_term in markdown and "模型时序输出不稳定 / 高置信" not in markdown:
            return True
    return bool(re.search(r"\bmodel_instability\s*/\s*(high|medium|low)\b", markdown))
