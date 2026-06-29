from debug_agent.jobs.auto_closure import AutoDebugClosureResult
from debug_agent.jobs.auto_closure_report import build_auto_closure_markdown_report
from debug_agent.reports.composer import validate_product_report_markdown
from debug_agent.reports.generator import DebugReport, ExperimentSummary, ObservedFailure, RootCause


def test_auto_closure_report_has_three_layers_and_human_terms() -> None:
    report = _product_report(root_label="model_instability", confidence="high")
    closure = AutoDebugClosureResult(
        source_job_id="job-1",
        created_targeted_probe_jobs=["job-targeted"],
        created_strategy_follow_up_jobs=[],
        created_verification_jobs=["job-verify"],
        final_attribution_candidates=[
            {
                "category": "model_instability",
                "confidence": "high",
                "summary": "同一视频片段多次输出不一致，targeted 后可稳定修正。",
            }
        ],
        badcase_live_comparison={
            "original_badcase": "原 badcase：0/1。",
            "live_rerun": "Live 复测：baseline 0/3；targeted 1/1；verification 1/1。",
        },
        evidence_summaries=[
            {
                "job_id": "job-1",
                "evidence_id": "e-baseline",
                "step_name": "baseline_replay",
                "trial": "0",
                "judge_score": "0",
                "delta_reasons": ["timestamp_end_out_of_range"],
                "raw_output_excerpt": '{"end_s":34.0}',
                "model_call_error": "",
                "response_parse_error": "",
            }
        ],
        writeback_status="not_requested",
    )

    markdown = build_auto_closure_markdown_report(
        report=report,
        closure=closure,
        original_prompt="请拆解视频动作。",
        original_cot_excerpt="原推理把动作持续时间估长。",
        original_prediction='{"end_s":34.0}',
        reference_answer='{"end_s":23.0}',
        scoring_ops="结束时间必须在 22-24 秒。",
    )

    assert markdown.index("## 第一层：一页看懂") < markdown.index("## 第二层：证据链")
    assert markdown.index("## 第二层：证据链") < markdown.index("## 第三层：审计附录")
    assert "模型时序输出不稳定 / 高置信" in markdown
    assert "### 首屏摘要" in markdown
    assert "| 是否找到可验证根因 |" in markdown
    assert "### 本次探索路线" in markdown
    assert "## 调试过程一览" in markdown
    assert "统一状态：Debug 任务已完成" in markdown
    assert "循环探索：第 1 轮 / `verified_root_cause_found`" in markdown
    assert "循环决策：prompt probe supported." in markdown
    assert "假设闭环：已完成" in markdown
    assert "候选假设：1 个" in markdown
    assert "Probe 计划：1 个" in markdown
    assert "Probe 结果：1 个" in markdown
    assert "已完成 probe：1 个" in markdown
    assert "已验证根因明细：`h-prompt` / `probe-h-prompt`" in markdown
    assert "公平性锁：`locked_source`" in markdown
    assert "证据来源" in markdown
    assert "### 证据地图" in markdown
    assert "### 关键证据卡片" in markdown
    assert "### 证据解读" in markdown
    assert "### 原始输出索引（精简）" in markdown
    assert "| 任务 | 证据 | 阶段 | 轮次 | 得分 | 缺失/偏差 | 模型原始输出摘录 |" not in markdown
    assert "### Evidence 中文解释" not in markdown
    assert validate_product_report_markdown(markdown) == []


def test_product_report_quality_gate_rejects_missing_sections() -> None:
    markdown = '{"root_cause":"model_instability/high"}'

    violations = validate_product_report_markdown(markdown)

    assert "missing_decision_brief" in violations
    assert "missing_evidence_chain" in violations
    assert "missing_audit_appendix" in violations
    assert "missing_next_actions" in violations
    assert "json_only_report" in violations
    assert "raw_internal_terms_without_human_translation" in violations


def _product_report(*, root_label: str, confidence: str) -> DebugReport:
    return DebugReport(
        job_id="job-1",
        case_id="case-1",
        status="needs_human_review",
        observed_failure=ObservedFailure(
            type="video_timestamp_mismatch",
            summary="模型把第一段动作结束时间输出到 34 秒，但标答要求 22-24 秒。",
            affected_box_ids=[],
        ),
        planned_experiments=["baseline_replay", "targeted_video_segment_probe"],
        experiment_summary=ExperimentSummary(
            total_trials=4,
            success_count=1,
            failed_trial_count=3,
            success_rate=0.25,
            stability_label="unstable",
            evidence_ids=["e-baseline", "e-targeted"],
            image_artifact_ids=[],
        ),
        root_cause=RootCause(
            label=root_label,
            confidence=confidence,
            evidence_summary="baseline 复测持续暴露时间边界偏移；定向深挖能在明确时间窗后修正。",
        ),
        run_view={
            "summary": {
                "headline": "Debug 任务已完成",
                "current_phase": "auto_closure",
                "next_step": "确认报告后执行写回。",
            },
            "auto_closure": {"status": "completed", "status_label": "已完成"},
            "debug_loop": {
                "status": "completed",
                "status_label": "已完成",
                "summary": "第 1 轮探索已找到 verified root cause；prompt probe supported.",
                "current_iteration": 1,
                "decision": "verified_root_cause_found",
                "next_action": "查看已验证根因并决定是否同步报告。",
                "stop_reason": "prompt probe supported.",
                "iterations": [
                    {
                        "iteration": 1,
                        "decision": "verified_root_cause_found",
                        "pending_probe_count": 0,
                        "completed_probe_count": 1,
                        "supported_comparison_count": 1,
                    }
                ],
            },
            "hypothesis_closure": {
                "status": "completed",
                "status_label": "已完成",
                "summary": "已生成 1 个候选假设、1 个 probe 计划、1 个因果比较；prompt probe 已完成。",
                "hypothesis_count": 1,
                "probe_plan_count": 1,
                "probe_result_count": 1,
                "causal_comparison_count": 1,
                "verified_root_cause_count": 1,
                "unverified_hypothesis_count": 0,
                "fairness_lock": {"model_runner_config_ref": "locked_source"},
                "hypotheses": [
                    {
                        "hypothesis_id": "h-prompt",
                        "category": "prompt_constraint",
                        "claim": "原 prompt 没有稳定触发时间窗约束。",
                        "status": "candidate",
                    }
                ],
                "probe_plans": [
                    {
                        "probe_id": "probe-h-prompt",
                        "hypothesis_id": "h-prompt",
                        "intervention_type": "prompt_patch",
                        "model_runner_config_ref": "locked_source",
                    }
                ],
                "causal_comparisons": [
                    {
                        "hypothesis_id": "h-prompt",
                        "probe_id": "probe-h-prompt",
                        "verdict": "supported",
                    }
                ],
                "probe_results": [
                    {
                        "probe_id": "probe-h-prompt",
                        "hypothesis_id": "h-prompt",
                        "status": "completed",
                        "probe_job_id": "job-probe-h-prompt",
                        "evidence_ids": ["job-probe-h-prompt:success"],
                    }
                ],
                "verified_root_causes": [
                    {
                        "hypothesis_id": "h-prompt",
                        "probe_id": "probe-h-prompt",
                        "summary": "Prompt patch improved success rate with locked source runner.",
                    }
                ],
                "unverified_hypotheses": [],
            },
            "writeback": {"status": "not_requested", "status_label": "未请求"},
            "action_queue": {"summary": {"total": 1}},
        },
        recommended_actions=[
            {
                "priority": "P0",
                "summary": "把动作起止时间窗和评分规则显式写入 prompt 后重跑验证。",
                "status": "pending",
            }
        ],
        confidence_reasons=[
            {
                "source": "evidence_count",
                "level": "high",
                "summary": "4 条 evidence 支撑当前判断。",
            }
        ],
        suggested_sheet_fields={
            "错误原因": "视频时间边界定位失败",
            "结构化差异": "baseline 失败，targeted 在明确时间窗后通过。",
        },
    )
