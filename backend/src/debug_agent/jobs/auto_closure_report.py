from debug_agent.jobs.auto_closure import AutoDebugClosureResult
from debug_agent.reports.generator import DebugReport


def build_auto_closure_markdown_report(
    *,
    report: DebugReport,
    closure: AutoDebugClosureResult,
    original_cot_excerpt: str,
    original_prediction: str,
    reference_answer: str,
    scoring_ops: str,
) -> str:
    lines = [
        f"# {report.case_id} 最终 Debug 报告",
        "",
        "## 结论先行",
        "",
        f"- 根因：`{report.root_cause.label}` / `{report.root_cause.confidence}`。",
        f"- 归因：{_final_attribution_line(closure)}。",
        f"- 原始 vs Live：{closure.badcase_live_comparison.get('original_badcase', '')} {closure.badcase_live_comparison.get('live_rerun', '')}",
        f"- 自动写回状态：`{closure.writeback_status}`。",
        "",
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
        f"- Targeted Probe：{_joined(closure.created_targeted_probe_jobs)}",
        f"- Stability Follow-up：{_joined(closure.created_strategy_follow_up_jobs)}",
        f"- Verification Job：{_joined(closure.created_verification_jobs)}",
        "",
        "## Targeted Probe Outcome",
        "",
        *_targeted_probe_outcome_lines(closure),
        "",
        "## Evidence 明细",
        "",
        "| Job | Evidence | Step | Trial | Score | Delta | Raw Output 摘录 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in closure.evidence_summaries:
        lines.append(_evidence_row(item))
    lines.extend(
        [
            "",
            "## 结构化差异",
            "",
            report.suggested_sheet_fields.get("结构化差异", "无"),
            "",
            "## 推荐后续",
            "",
            "- 如果 clipped targeted probe 通过而 baseline 失败，优先归因 prompt/时序 grounding 敏感性。",
            "- 如果 clipped targeted probe 仍失败，优先归因模型时间边界能力短板。",
            "- 如果 scoring window 与参考答案/动作定义不一致，优先修 scoring asset 或标答。",
        ]
    )
    return "\n".join(lines) + "\n"


def _final_attribution_line(closure: AutoDebugClosureResult) -> str:
    if not closure.final_attribution_candidates:
        return "无"
    first = closure.final_attribution_candidates[0]
    return f"{first.get('category', 'unknown')}/{first.get('confidence', 'unknown')}：{first.get('summary', '')}"


def _joined(values: list[str]) -> str:
    return ", ".join(f"`{value}`" for value in values) if values else "无"


def _code_block(value: str, lang: str) -> str:
    return f"```{lang}\n{value.strip()}\n```"


def _targeted_probe_outcome_lines(closure: AutoDebugClosureResult) -> list[str]:
    if not closure.targeted_probe_outcomes:
        return ["无"]
    return [
        f"- `{item.get('target_id', '')}` / `{item.get('outcome', '')}` / `{item.get('probe_job_id', '')}`：{item.get('summary', '')}"
        for item in closure.targeted_probe_outcomes
    ]


def _evidence_row(item: dict[str, object]) -> str:
    raw_output = str(item.get("raw_output_excerpt", "")).replace("\n", " ").replace("|", "\\|")
    delta_reasons = item.get("delta_reasons", [])
    delta = ", ".join(str(value) for value in delta_reasons) if isinstance(delta_reasons, list) else str(delta_reasons)
    return (
        f"| `{item.get('job_id', '')}` | `{item.get('evidence_id', '')}` | `{item.get('step_name', '')}` | "
        f"`{item.get('trial', '')}` | `{item.get('judge_score', '')}` | {delta or '无'} | `{raw_output}` |"
    )
