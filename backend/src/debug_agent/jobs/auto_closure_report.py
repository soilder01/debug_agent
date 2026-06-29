from collections import Counter, defaultdict

from debug_agent.jobs.auto_closure import AutoDebugClosureResult
from debug_agent.reports.generator import DebugReport
from debug_agent.reports.composer import (
    build_audit_appendix_intro_lines,
    build_decision_brief_lines,
    build_debug_run_view_lines,
    build_evidence_chain_intro_lines,
    build_next_action_lines,
    build_supplemental_context_lines,
    human_label_with_confidence,
)


def build_auto_closure_markdown_report(
    *,
    report: DebugReport,
    closure: AutoDebugClosureResult,
    original_prompt: str,
    original_cot_excerpt: str,
    original_prediction: str,
    reference_answer: str,
    scoring_ops: str,
) -> str:
    lines = [
        f"# {report.case_id} 最终 Debug 报告",
        "",
        *build_decision_brief_lines(report=report, closure=closure),
        *build_debug_run_view_lines(report=report),
        "## 结论与处理建议",
        "",
        f"- **当前根因判断**：{human_label_with_confidence(report.root_cause.label, report.root_cause.confidence)}。",
        f"- **最终归因**：{_final_attribution_line(closure)}。",
        f"- **原始 vs Live**：{closure.badcase_live_comparison.get('original_badcase', '')} {closure.badcase_live_comparison.get('live_rerun', '')}",
        f"- **怎么读这个结论**：{_interpret_outcome_pattern(report=report, closure=closure)}",
        f"- **写回建议**：当前自动写回状态为 `{closure.writeback_status}`；确认报告无误前不要写回。",
        "",
        *build_next_action_lines(report=report, closure=closure),
        *build_supplemental_context_lines(report=report),
        *build_evidence_chain_intro_lines(report=report, closure=closure),
        "## 原始 Badcase 证据",
        "",
        "### 原 COT 摘录",
        _code_block(original_cot_excerpt, "text"),
        "",
        "### 原模型预测",
        _code_block(original_prediction, "json"),
        "",
        "### 参考答案",
        _code_block(reference_answer, "json"),
        "",
        "### 评分规则",
        _code_block(scoring_ops, "json"),
        "",
        "## 自动深挖链路",
        "",
        f"- 定向深挖任务：{_joined(closure.created_targeted_probe_jobs)}",
        f"- 稳定性跟进任务：{_joined(closure.created_strategy_follow_up_jobs)}",
        f"- 闭环验证任务：{_joined(closure.created_verification_jobs)}",
        f"- 阶段结果解读：{_interpret_outcome_pattern(report=report, closure=closure)}",
        "",
        "## 归因分析",
        "",
        *_attribution_analysis_lines(report=report, closure=closure),
        "",
        "## 定向深挖结果分析",
        "",
        *_targeted_probe_outcome_lines(closure),
        "",
        "## 证据明细",
        "",
        "说明：完整原始输出不在正文展开；正文只保留证据地图、关键证据卡片和精简索引，避免用大表挤占阅读空间。",
        "",
        *_evidence_overview_lines(closure),
    ]
    lines.extend(
        [
            "",
            "## 结构化差异",
            "",
            report.suggested_sheet_fields.get("结构化差异", "无"),
            "",
            "## 推荐后续",
            "",
            "- 如果局部定向深挖通过而 baseline 失败，优先归因提示词或时序定位触发不稳定。",
            "- 如果局部定向深挖仍失败，优先归因模型时间边界识别能力短板。",
            "- 如果评分时间窗与参考答案或动作定义不一致，优先修正评分资产或标答。",
            "",
            *build_audit_appendix_intro_lines(report=report),
            "## 输入与 Prompt 改动审计",
            "",
            *_prompt_audit_lines(
                original_prompt=original_prompt,
                reference_answer=reference_answer,
                scoring_ops=scoring_ops,
                closure=closure,
            ),
            "",
            "## Agent 输入与推理摘要",
            "",
            "说明：这里沉淀每个 agent 角色的可审计输入、可见输出和推理摘要；不采集模型不可见的隐藏 CoT。",
            "",
            *_agent_trace_lines(report),
            "",
            "## 阶段方法解释",
            "",
            *_stage_method_lines(report=report, closure=closure),
        ]
    )
    return "\n".join(lines) + "\n"


def _final_attribution_line(closure: AutoDebugClosureResult) -> str:
    if not closure.final_attribution_candidates:
        return "无"
    first = closure.final_attribution_candidates[0]
    summary = _trim_sentence_suffix(str(first.get("summary", "")))
    return (
        f"{human_label_with_confidence(str(first.get('category', 'unknown')), str(first.get('confidence', 'unknown')))}"
        f"：{summary}"
    )


def _agent_trace_lines(report: DebugReport) -> list[str]:
    if not report.agent_traces:
        return ["无 agent trace。"]
    lines: list[str] = []
    for trace in report.agent_traces[:30]:
        evidence_id = str(trace.input_summary.get("evidence_id", ""))
        step_name = str(trace.input_summary.get("step_name", ""))
        suffix = f" / `{step_name}` / `{evidence_id}`" if evidence_id or step_name else ""
        lines.extend(
            [
                f"### `{trace.agent_role}`{suffix}",
                "",
                f"- 输入摘要：{_compact(str(trace.input_summary), 800)}",
                f"- 推理摘要：{trace.reasoning_summary or '无'}",
                f"- CoT 策略：`{trace.raw_cot_policy}`",
                "- 输入摘录：",
                _code_block(_compact(trace.input_excerpt, 1200), "text"),
                "- 可见输出摘录：",
                _code_block(_compact(trace.output_excerpt, 1200), "text"),
                "",
            ]
        )
    if len(report.agent_traces) > 30:
        lines.append(
            f"仅展示前 30 条 agent trace；完整 JSON 报告包含 {len(report.agent_traces)} 条。"
        )
    return lines


def _stage_method_lines(*, report: DebugReport, closure: AutoDebugClosureResult) -> list[str]:
    observed = report.observed_failure.summary or report.root_cause.evidence_summary
    live_rerun = closure.badcase_live_comparison.get("live_rerun", "")
    lines = [
        "- **Baseline 复测**：不改变原始 prompt、视频、标答和评分规则，按原评测语境重复运行，用来确认坏案是否稳定复现。"
        f"本案观察到：{observed}",
        "  - 阶段输入：原视频/原题目/原评分规则/原标答。",
        "  - 阶段输出：多次原条件复测结果、失败 delta、原始模型回答摘录。",
        "  - 判断依据：如果 baseline 仍失败，说明原坏案不是表格记录偶然错误，而是可复现问题；如果多次结果波动，则提示稳定性或 prompt 敏感性。",
        "- **定向深挖**：不是重新给一个更容易的任务，而是围绕失败目标重新提问，"
        "把模型注意力集中到具体动作、时间窗、区域或评分点，验证模型是否在明确证据要求下可以做对。",
        "  - 阶段输入：失败目标、局部时间窗或局部区域、该目标的参考答案与评分点。",
        "  - 阶段输出：目标是否被清除、模型是否补齐关键证据、仍失败时的下一步升级方向。",
        "  - 判断依据：如果 targeted 做对，说明模型具备相关识别能力但原始任务没有稳定触发；如果 targeted 仍失败，才更支持模型能力短板或数据/标答问题。",
        "- **闭环验证**：在定向深挖成功后，再用验证任务复测推荐动作，"
        "排除只是 targeted prompt 临时诱导成功，确认修复建议是否能稳定提升原问题。",
        "  - 阶段输入：推荐修复动作、修复后的约束或提示词、同一评分规则。",
        "  - 阶段输出：修复是否稳定通过、是否回归、是否需要继续深挖。",
        "  - 判断依据：verification 通过才说明推荐动作具备复用价值；verification 不通过则不能把 targeted 的单次成功当作最终结论。",
    ]
    if live_rerun:
        lines.append(
            f"- **阶段结果总览**：{_trim_sentence_suffix(live_rerun)}。这不是简单地把 0/3、1/1、2/2 罗列出来，"
            "而是用 baseline 判断原问题是否复现，用 targeted 判断能力是否可被明确评分点触发，"
            "再用 verification 判断该触发方式是否能形成可复用修复。"
        )
    if closure.created_targeted_probe_jobs:
        lines.append(f"- **定向深挖任务**：{_joined(closure.created_targeted_probe_jobs)}。")
    if closure.created_verification_jobs:
        lines.append(f"- **闭环验证任务**：{_joined(closure.created_verification_jobs)}。")
    return lines


def _prompt_audit_lines(
    *,
    original_prompt: str,
    reference_answer: str,
    scoring_ops: str,
    closure: AutoDebugClosureResult,
) -> list[str]:
    failed_reasons = _failed_reasons(closure)
    targeted_addition = _targeted_prompt_addition(reference_answer, scoring_ops, failed_reasons)
    verification_addition = _verification_prompt_addition(reference_answer, scoring_ops)
    return [
        "- **原始 prompt 使用方式**：Baseline 复测直接使用原始 prompt，不追加参考答案、评分规则或失败原因，用来确认坏案是否能在原条件下复现。",
        f"  - 原始 prompt 摘要：{_compact(original_prompt, 500)}",
        "- **评分关键点清单**：这些关键点来自参考答案、评分规则和 baseline 暴露的失败点；agent 后续只围绕这些点增强约束。",
        f"  - 参考答案约束：{_compact(reference_answer, 600)}",
        f"  - 评分规则约束：{_compact(scoring_ops, 600)}",
        f"  - baseline 暴露的失败点：{', '.join(failed_reasons[:20]) if failed_reasons else '无结构化失败点'}",
        "- **定向深挖相对原 prompt 的改动**：保留原始任务要求不变，追加 baseline 失败点、参考答案和评分规则，要求模型只针对失败点重新观察并按原 schema 输出。",
        "- **定向深挖本阶段实际输入给模型的增强约束**：",
        _code_block(targeted_addition, "text"),
        "- **闭环验证相对原 prompt 的改动**：保留原始任务要求不变，追加参考答案和评分规则，显式要求模型逐条满足参考答案和评分规则。",
        "- **闭环验证本阶段实际输入给模型的增强约束**：",
        _code_block(verification_addition, "text"),
    ]


def _targeted_prompt_addition(
    reference_answer: str, scoring_ops: str, failed_reasons: list[str]
) -> str:
    return "\n\n".join(
        [
            "targeted_debug_probe:",
            "上一次 baseline 失败原因如下，请只针对这些失败点重新观察视频，并输出符合原 schema 的最终 JSON。",
            ", ".join(failed_reasons[:20])
            or "baseline 未返回结构化失败点，请围绕原 badcase 差异做局部复核。",
            "参考答案:",
            reference_answer,
            "评分规则:",
            scoring_ops,
            "要求：不要改变输出 schema；不要增加解释文本；只输出最终 JSON。",
        ]
    )


def _verification_prompt_addition(reference_answer: str, scoring_ops: str) -> str:
    return "\n\n".join(
        [
            "debug_scoring_alignment:",
            "你必须逐条满足参考答案和评分规则。特别注意 task 数量、时间窗、左右臂、物品顺序、关键词和格式约束。",
            "参考答案:",
            reference_answer,
            "评分规则:",
            scoring_ops,
            "要求：输出前自检每个评分点是否满足；最终只输出原任务要求的 JSON。",
        ]
    )


def _failed_reasons(closure: AutoDebugClosureResult) -> list[str]:
    reasons: list[str] = []
    for item in closure.evidence_summaries:
        delta_reasons = item.get("delta_reasons", [])
        if isinstance(delta_reasons, list):
            reasons.extend(str(reason) for reason in delta_reasons if str(reason))
        elif str(delta_reasons):
            reasons.append(str(delta_reasons))
    return list(dict.fromkeys(reasons))


def _compact(value: str, limit: int) -> str:
    normalized = " ".join(str(value).split())
    return normalized if len(normalized) <= limit else f"{normalized[:limit]}..."


def _attribution_analysis_lines(
    *, report: DebugReport, closure: AutoDebugClosureResult
) -> list[str]:
    if not closure.final_attribution_candidates:
        return [
            "- 当前没有足够最终归因候选；需要继续补充 targeted probe、verification job 或人工审阅证据。"
        ]
    lines: list[str] = []
    for candidate in closure.final_attribution_candidates:
        category = str(candidate.get("category", "unknown"))
        confidence = str(candidate.get("confidence", "unknown"))
        summary = str(candidate.get("summary", ""))
        lines.append(
            f"- **为什么归因为 {human_label_with_confidence(category, confidence)}**：{summary}"
        )
        lines.append(
            f"  中文解释：{_category_explanation(category, report=report, closure=closure)}"
        )
    structure_diff = report.suggested_sheet_fields.get("结构化差异", "")
    if structure_diff:
        lines.append(f"- **结构化差异如何支撑归因**：{structure_diff}")
    decision = closure.badcase_live_comparison.get("decision", "")
    if decision:
        lines.append(
            f"- **原始 badcase 与 live 复测决策**：闭环判断为 `{decision}`，"
            "该判断来自原始坏案、baseline 复现、targeted 深挖和 verification 复测之间的差异。"
        )
    return lines


def _category_explanation(
    category: str, *, report: DebugReport, closure: AutoDebugClosureResult
) -> str:
    live_rerun = closure.badcase_live_comparison.get("live_rerun", "")
    if category == "prompt_scoring_alignment_gap":
        return (
            "baseline 失败说明原始任务语境下模型没有稳定命中评分点；targeted/verification 通过说明模型并非完全不会，"
            "而是在原 prompt 或评分约束没有把关键动作/区域/时间窗说清时容易漏答。"
            f"本案阶段证据：{live_rerun or report.root_cause.evidence_summary}"
        )
    if category == "model_instability":
        return "同一或相近输入下通过率波动，说明错误不只是单次解析问题；需要从模型稳定性、采样波动或版本差异继续定位。"
    if category == "model_capability_or_asset_gap":
        return "baseline、targeted、verification 都未能稳定做对时，优先考虑模型能力短板、标答/评分资产不清或数据本身不充分。"
    if category == "video_timestamp_boundary_error":
        return "证据集中指向时间边界偏移，需要检查动作起止定义、时间窗评分规则和模型时序 grounding 能力。"
    return "该归因由自动闭环候选给出，需结合证据明细中的失败差异、定向深挖结果和闭环验证结果判断。"


def _interpret_outcome_pattern(*, report: DebugReport, closure: AutoDebugClosureResult) -> str:
    live_rerun = closure.badcase_live_comparison.get("live_rerun", "")
    attribution = _final_attribution_line(closure)
    if live_rerun:
        return (
            f"{live_rerun} 说明 baseline 用原始条件复现问题，targeted 用失败目标定向确认模型是否能抓到关键证据，"
            f"verification 再验证推荐修复是否可复用；当前归因为 {attribution}。"
        )
    summary = report.root_cause.evidence_summary or report.observed_failure.summary
    return f"{summary} 当前归因候选为 {attribution}。"


def _trim_sentence_suffix(value: str) -> str:
    return value.rstrip().rstrip("。.")


def _joined(values: list[str]) -> str:
    return ", ".join(f"`{value}`" for value in values) if values else "无"


def _code_block(value: str, lang: str) -> str:
    return f"```{lang}\n{value.strip()}\n```"


def _targeted_probe_outcome_lines(closure: AutoDebugClosureResult) -> list[str]:
    if not closure.targeted_probe_outcomes:
        return ["无"]
    return [
        f"- `{item.get('target_id', '')}` / `{item.get('outcome', '')}` / `{item.get('probe_job_id', '')}`："
        f"{_trim_sentence_suffix(str(item.get('summary', '')))}。中文解读：该 probe 只围绕失败目标验证模型是否能在更明确证据约束下做对，"
        "用于区分模型能力不会、prompt/评分点不清、还是原始评测资产问题。"
        for item in closure.targeted_probe_outcomes
    ]


def _evidence_overview_lines(closure: AutoDebugClosureResult) -> list[str]:
    if not closure.evidence_summaries:
        return ["无 evidence 明细，当前报告可信度不足，需要补充原始输出和判分 delta。"]
    return [
        "### 证据地图",
        "",
        *_evidence_map_lines(closure),
        "",
        "### 关键证据卡片",
        "",
        *_key_evidence_card_lines(closure),
        "",
        "### 证据解读",
        "",
        *_evidence_interpretation_lines(closure),
        "",
        "### 原始输出索引（精简）",
        "",
        *_raw_output_index_lines(closure),
    ]


def _evidence_map_lines(closure: AutoDebugClosureResult) -> list[str]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for item in closure.evidence_summaries:
        grouped[_evidence_step(item)].append(item)

    lines = [
        "| 阶段 | 证据数 | 通过 | 异常/偏差 | 代表证据 |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for step, items in grouped.items():
        passed = sum(1 for item in items if _evidence_passed(item))
        failed = len(items) - passed
        representative = _evidence_id(_representative_evidence(items))
        lines.append(f"| {step} | {len(items)} 条 | {passed} | {failed} | `{representative}` |")
    return lines


def _key_evidence_card_lines(closure: AutoDebugClosureResult) -> list[str]:
    candidates = [
        item
        for item in closure.evidence_summaries
        if not _evidence_passed(item) or _evidence_has_runtime_error(item)
    ]
    if not candidates:
        candidates = closure.evidence_summaries[:3]

    lines: list[str] = []
    for index, item in enumerate(candidates[:5], start=1):
        lines.extend(
            [
                f"#### 证据卡 {index}：{_evidence_step(item)} / trial {_evidence_trial(item)} / score {_evidence_score(item)}",
                "",
                f"- 证据 ID：`{_evidence_id(item)}`",
                f"- 任务 ID：`{item.get('job_id', '')}`",
                f"- 关键偏差：{_evidence_delta_text(item) or '无结构化偏差'}",
                f"- 归因价值：{_evidence_value_line(item)}",
                f"- 原始输出摘要：`{_compact(_raw_output_excerpt(item), 260)}`",
                "",
            ]
        )
    return lines


def _evidence_interpretation_lines(closure: AutoDebugClosureResult) -> list[str]:
    total = len(closure.evidence_summaries)
    passed_items = [item for item in closure.evidence_summaries if _evidence_passed(item)]
    failed_items = [item for item in closure.evidence_summaries if not _evidence_passed(item)]
    error_items = [item for item in closure.evidence_summaries if _evidence_has_runtime_error(item)]
    top_deltas = _top_delta_reasons(failed_items)

    lines = [
        f"- 证据总量：{total} 条；通过 {len(passed_items)} 条，异常/偏差 {len(failed_items)} 条。",
    ]
    if top_deltas:
        lines.append(f"- 主要失败信号：{', '.join(top_deltas)}。")
    if failed_items:
        lines.append(
            "- 失败证据的作用：确认原始 badcase 或局部复测仍能暴露问题，不能只看最终通过样本。"
        )
    if passed_items:
        lines.append(
            "- 通过证据的作用：确认在 targeted / verification 约束下，推荐动作或补充约束具备复用价值。"
        )
    if error_items:
        lines.append(
            f"- 运行错误：{len(error_items)} 条证据存在模型调用或解析错误，这部分不参与正向置信度加权。"
        )
    if not failed_items:
        lines.append("- 当前证据没有结构化失败项，报告结论主要依赖稳定通过与回归验证。")
    return lines


def _raw_output_index_lines(closure: AutoDebugClosureResult) -> list[str]:
    lines = [
        "完整原始输出不在正文展开；需要逐字审计时请进入 Evidence Ledger 或 Agent 审计附录。",
        "",
    ]
    selected = _selected_raw_output_items(closure.evidence_summaries)
    for item in selected:
        lines.append(
            f"- `{_evidence_id(item)}`：{_evidence_step(item)} / score {_evidence_score(item)} / "
            f"`{_compact(_raw_output_excerpt(item), 220)}`"
        )
    if len(closure.evidence_summaries) > len(selected):
        lines.append(
            f"- 其余 {len(closure.evidence_summaries) - len(selected)} 条证据不在正文展开。"
        )
    return lines


def _selected_raw_output_items(items: list[dict[str, object]]) -> list[dict[str, object]]:
    failed = [item for item in items if not _evidence_passed(item)]
    selected = failed[:3]
    for item in items:
        if len(selected) >= 5:
            break
        if item not in selected:
            selected.append(item)
    return selected


def _representative_evidence(items: list[dict[str, object]]) -> dict[str, object]:
    for item in items:
        if not _evidence_passed(item) or _evidence_has_runtime_error(item):
            return item
    return items[0]


def _top_delta_reasons(items: list[dict[str, object]]) -> list[str]:
    counter: Counter[str] = Counter()
    for item in items:
        delta = _evidence_delta_text(item)
        if delta:
            for reason in delta.split(", "):
                counter[reason] += 1
    return [reason for reason, _count in counter.most_common(5)]


def _evidence_value_line(item: dict[str, object]) -> str:
    if _evidence_has_runtime_error(item):
        return "这条证据说明链路本身存在运行错误，需要先排除调用或解析问题。"
    if _evidence_passed(item):
        return "这条证据说明当前约束下模型输出已满足评分要求，可作为修复动作有效性的支撑。"
    return "这条证据说明原问题仍可复现或仍存在偏差，是根因判断的主要支撑。"


def _evidence_passed(item: dict[str, object]) -> bool:
    score = _evidence_score(item)
    return (
        score in {"1", "1.0"}
        and not _evidence_delta_text(item)
        and not _evidence_has_runtime_error(item)
    )


def _evidence_has_runtime_error(item: dict[str, object]) -> bool:
    return bool(str(item.get("model_call_error", "")).strip()) or bool(
        str(item.get("response_parse_error", "")).strip()
    )


def _evidence_delta_text(item: dict[str, object]) -> str:
    delta_reasons = item.get("delta_reasons", [])
    if isinstance(delta_reasons, list):
        return ", ".join(str(value) for value in delta_reasons if str(value).strip())
    return str(delta_reasons).strip()


def _raw_output_excerpt(item: dict[str, object]) -> str:
    return str(item.get("raw_output_excerpt", "")).replace("\n", " ")


def _evidence_step(item: dict[str, object]) -> str:
    return str(item.get("step_name", "unknown"))


def _evidence_trial(item: dict[str, object]) -> str:
    return str(item.get("trial", ""))


def _evidence_score(item: dict[str, object]) -> str:
    return str(item.get("judge_score", ""))


def _evidence_id(item: dict[str, object]) -> str:
    return str(item.get("evidence_id", ""))
