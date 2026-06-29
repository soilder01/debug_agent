from debug_agent.jobs.auto_closure import AutoDebugClosureResult
from debug_agent.jobs.auto_closure_report import build_auto_closure_markdown_report
from debug_agent.reports.generator import DebugReport, ExperimentSummary, ObservedFailure, RootCause


def test_build_auto_closure_markdown_report_includes_deep_debug_evidence() -> None:
    report = DebugReport(
        job_id="job-source",
        case_id="JSZN-131",
        status="needs_human_review",
        observed_failure=ObservedFailure(
            type="video_timestamp_mismatch",
            summary="视频时间窗评分发现 video:segment:1 存在时间边界偏差。",
            affected_box_ids=[],
        ),
        planned_experiments=["baseline_replay", "temporal_grounding_check"],
        experiment_summary=ExperimentSummary(
            total_trials=9,
            success_count=4,
            failed_trial_count=5,
            success_rate=4 / 9,
            stability_label="unstable",
            evidence_ids=["e-source"],
            image_artifact_ids=[],
        ),
        root_cause=RootCause(
            label="video_timestamp_boundary_error",
            confidence="high",
            evidence_summary="video:segment:1 end_s 超出期望窗口 22.0-24.0s，实际 33.0s。",
        ),
        suggested_sheet_fields={
            "错误原因": "视频时间边界定位失败",
            "结构化差异": "video:segment:1 end_s 超出期望窗口 22.0-24.0s，实际 33.0s。",
        },
    )
    closure = AutoDebugClosureResult(
        source_job_id="job-source",
        created_targeted_probe_jobs=["job-probe"],
        created_strategy_follow_up_jobs=["job-stability"],
        created_verification_jobs=["job-verify"],
        targeted_probe_outcomes=[
            {
                "probe_job_id": "job-probe",
                "target_id": "video:segment:1",
                "outcome": "corrected_boundary",
                "summary": "Clipped targeted probe cleared video:segment:1.",
            }
        ],
        evidence_summaries=[
            {
                "job_id": "job-source",
                "evidence_id": "e-source",
                "step_name": "baseline_replay",
                "trial": "0",
                "judge_score": "0",
                "delta_reasons": ["timestamp_end_out_of_range"],
                "raw_output_excerpt": '{"video_action_segments":[{"end_s":33.0}]}',
                "model_call_error": "",
                "response_parse_error": "",
            },
            {
                "job_id": "job-probe",
                "evidence_id": "e-probe",
                "step_name": "temporal_grounding_check",
                "trial": "0",
                "judge_score": "1",
                "delta_reasons": [],
                "raw_output_excerpt": '{"video_action_segments":[{"end_s":23.0}]}',
                "model_call_error": "",
                "response_parse_error": "",
            },
        ],
        final_attribution_candidates=[
            {
                "category": "model_instability",
                "confidence": "high",
                "summary": "Live rerun passed 4/9 trials.",
            }
        ],
        badcase_live_comparison={
            "original_badcase": "原 badcase：0/1 通过，avg_score=0.0。",
            "live_rerun": "Live 复测：4/9 通过，success_rate=44%。",
            "decision": "model_instability",
        },
        writeback_status="succeeded",
    )

    markdown = build_auto_closure_markdown_report(
        report=report,
        closure=closure,
        original_prompt="请拆解视频动作并输出 video_action_segments。",
        original_cot_excerpt="原 COT 里把第一段结束时间推到了 34 秒。",
        original_prediction='{"video_action_segments":[{"end_s":34.0}]}',
        reference_answer='{"video_action_segments":[{"end_s":23.1}]}',
        scoring_ops='[{"op_name":"check_timestamp"}]',
    )

    assert "# JSZN-131 最终 Debug 报告" in markdown
    assert "原 COT 里把第一段结束时间推到了 34 秒。" in markdown
    assert "job-probe" in markdown
    assert "job-stability" in markdown
    assert "job-verify" in markdown
    assert "corrected_boundary" in markdown
    assert "timestamp_end_out_of_range" in markdown
    assert "### 证据地图" in markdown
    assert "### 关键证据卡片" in markdown
    assert "### 证据解读" in markdown
    assert "### 原始输出索引（精简）" in markdown
    assert "| temporal_grounding_check | 1 条" in markdown
    assert "| 任务 | 证据 | 阶段 | 轮次 | 得分 | 缺失/偏差 | 模型原始输出摘录 |" not in markdown
    assert "### Evidence 中文解释" not in markdown
    assert "模型时序输出不稳定 / 高置信" in markdown


def test_build_auto_closure_markdown_report_explains_probe_method_and_attribution_in_chinese() -> (
    None
):
    report = DebugReport(
        job_id="job-source",
        case_id="JSZN-096",
        status="needs_human_review",
        observed_failure=ObservedFailure(
            type="action_sequence_missing",
            summary="原始坏案漏掉右臂套入垃圾袋动作。",
            affected_box_ids=[],
        ),
        planned_experiments=[
            "baseline_replay",
            "targeted_arm_attribution_probe",
            "verification_regression_probe",
        ],
        experiment_summary=ExperimentSummary(
            total_trials=7,
            success_count=3,
            failed_trial_count=4,
            success_rate=3 / 7,
            stability_label="prompt_sensitive",
            evidence_ids=["e-baseline", "e-targeted", "e-verification"],
            image_artifact_ids=[],
        ),
        root_cause=RootCause(
            label="prompt_scoring_alignment_gap",
            confidence="high",
            evidence_summary="baseline 0/3 失败，但 targeted 1/1 和 verification 2/2 通过。",
        ),
        suggested_sheet_fields={
            "错误原因": "原 prompt 没有把右臂动作作为必须判分点。",
            "结构化差异": "baseline 漏右臂；targeted/verification 能在明确评分点后补齐右臂动作。",
        },
    )
    closure = AutoDebugClosureResult(
        source_job_id="job-source",
        created_targeted_probe_jobs=["job-targeted"],
        created_strategy_follow_up_jobs=[],
        created_verification_jobs=["job-verify-1", "job-verify-2"],
        targeted_probe_outcomes=[
            {
                "probe_job_id": "job-targeted",
                "target_id": "right_arm_action",
                "outcome": "target_cleared",
                "summary": "targeted 1/1 succeeded after explicitly asking for right arm bagging evidence.",
            }
        ],
        evidence_summaries=[
            {
                "job_id": "job-source",
                "evidence_id": "e-baseline",
                "step_name": "baseline_replay",
                "trial": "0",
                "judge_score": "0",
                "delta_reasons": ["missing_right_arm_action"],
                "raw_output_excerpt": "模型原文：The person lifts the bag with both hands.",
                "model_call_error": "",
                "response_parse_error": "",
            },
            {
                "job_id": "job-targeted",
                "evidence_id": "e-targeted",
                "step_name": "targeted_arm_attribution_probe",
                "trial": "0",
                "judge_score": "1",
                "delta_reasons": [],
                "raw_output_excerpt": "模型原文：右臂向前伸并配合左手把垃圾袋套入。",
                "model_call_error": "",
                "response_parse_error": "",
            },
            {
                "job_id": "job-verify-1",
                "evidence_id": "e-verification",
                "step_name": "verification_regression_probe",
                "trial": "0",
                "judge_score": "1",
                "delta_reasons": [],
                "raw_output_excerpt": "模型原文：right arm pushes the bag opening into place.",
                "model_call_error": "",
                "response_parse_error": "",
            },
        ],
        final_attribution_candidates=[
            {
                "category": "prompt_scoring_alignment_gap",
                "confidence": "high",
                "summary": "baseline 0/3，但 targeted 1/1、verification 2/2，说明能力可触发，主要是 prompt 与评分点对齐不足。",
            }
        ],
        badcase_live_comparison={
            "original_badcase": "原 badcase：0/1 通过，avg_score=0.0。",
            "live_rerun": "Live 复测：baseline 0/3；targeted 1/1；verification 2/2。",
            "decision": "prompt_scoring_alignment_gap",
        },
        writeback_status="succeeded",
    )

    markdown = build_auto_closure_markdown_report(
        report=report,
        closure=closure,
        original_prompt="请根据视频拆分子任务，描述每个子任务中哪只手臂对什么物品进行了什么操作。",
        original_cot_excerpt="Model reasoning: arm movement was summarized too coarsely.",
        original_prediction="The person uses the bag.",
        reference_answer="必须描述右臂向前伸、撑开/套入垃圾袋。",
        scoring_ops="右臂动作、双臂配合、垃圾袋套入均为必须得分点。",
    )

    assert "## 阶段方法解释" in markdown
    assert "Baseline 复测" in markdown
    assert "不改变原始 prompt、视频、标答和评分规则" in markdown
    assert "阶段输入：原视频/原题目/原评分规则/原标答" in markdown
    assert "阶段输出：多次原条件复测结果、失败 delta、原始模型回答摘录" in markdown
    assert "定向深挖" in markdown
    assert "围绕失败目标重新提问" in markdown
    assert "阶段输入：失败目标、局部时间窗或局部区域、该目标的参考答案与评分点" in markdown
    assert "阶段输出：目标是否被清除、模型是否补齐关键证据、仍失败时的下一步升级方向" in markdown
    assert "闭环验证" in markdown
    assert "排除只是 targeted prompt 临时诱导成功" in markdown
    assert "阶段输入：推荐修复动作、修复后的约束或提示词、同一评分规则" in markdown
    assert "阶段输出：修复是否稳定通过、是否回归、是否需要继续深挖" in markdown
    assert "baseline 0/3；targeted 1/1；verification 2/2" in markdown
    assert "这不是简单地把 0/3、1/1、2/2 罗列出来" in markdown
    assert "。。" not in markdown
    assert "为什么归因为 提示词与评分规则未对齐 / 高置信" in markdown
    assert "完整原始输出不在正文展开" in markdown
    assert "模型原文：The person lifts the bag with both hands." in markdown
    assert "### 证据地图" in markdown
    assert "### 关键证据卡片" in markdown
    assert "### 证据解读" in markdown
    assert "baseline_replay / trial 0 / score 0" in markdown
    assert "关键偏差：missing_right_arm_action" in markdown
    assert "## 输入与 Prompt 改动审计" in markdown
    assert "原始 prompt 使用方式" in markdown
    assert "评分关键点清单" in markdown
    assert "参考答案约束：必须描述右臂向前伸、撑开/套入垃圾袋。" in markdown
    assert "baseline 暴露的失败点：missing_right_arm_action" in markdown
    assert "定向深挖相对原 prompt 的改动" in markdown
    assert "定向深挖本阶段实际输入给模型的增强约束" in markdown
    assert "闭环验证相对原 prompt 的改动" in markdown
    assert "闭环验证本阶段实际输入给模型的增强约束" in markdown
    assert "请根据视频拆分子任务" in markdown
    assert "只针对这些失败点重新观察" in markdown
    assert "逐条满足参考答案和评分规则" in markdown
    assert "## 证据明细" in markdown
    assert "定向深挖任务：" in markdown
    assert "稳定性跟进任务：" in markdown
    assert "闭环验证任务：" in markdown
    assert "## 定向深挖结果分析" in markdown
    assert "### 证据地图" in markdown
    assert "### 原始输出索引（精简）" in markdown
    assert "| 任务 | 证据 | 阶段 | 轮次 | 得分 | 缺失/偏差 | 模型原始输出摘录 |" not in markdown
    assert "### Evidence 中文解释" not in markdown
    assert "Targeted Probe：" not in markdown
    assert "Targeted Probe 定向深挖" not in markdown
    assert "Stability Follow-up：" not in markdown
    assert "Verification Job：" not in markdown
    assert "Verification 闭环验证" not in markdown
    assert "## Targeted Probe Outcome" not in markdown
    assert "## Evidence 明细" not in markdown
    assert "| Job | Evidence | Step | Trial | Score | Delta | Raw Output 摘录 |" not in markdown
    assert "clipped targeted probe" not in markdown
    assert "scoring asset" not in markdown


def test_build_auto_closure_markdown_report_starts_with_readable_decision_brief() -> None:
    report = DebugReport(
        job_id="job-source",
        case_id="JSZN-QUALITY",
        status="needs_human_review",
        observed_failure=ObservedFailure(
            type="video_timestamp_mismatch",
            summary="模型把第一段动作结束时间输出到 34 秒，但标答要求 22-24 秒。",
            affected_box_ids=[],
        ),
        planned_experiments=["baseline_replay", "targeted_video_segment_probe"],
        experiment_summary=ExperimentSummary(
            total_trials=5,
            success_count=2,
            failed_trial_count=3,
            success_rate=0.4,
            stability_label="unstable",
            evidence_ids=["e-baseline", "e-targeted"],
            image_artifact_ids=[],
        ),
        root_cause=RootCause(
            label="video_timestamp_boundary_error",
            confidence="high",
            evidence_summary="baseline 复测持续暴露时间边界偏移；定向深挖能在明确时间窗后修正。",
        ),
        recommended_actions=[
            {
                "priority": "P0",
                "summary": "把动作起止时间窗和评分规则显式写入 prompt 后重跑验证。",
                "status": "pending",
            }
        ],
        supplemental_contexts=[
            {
                "text": "补充材料：视频第 2 秒右侧按钮闪了一下。",
                "message_id": "om_supplement_1",
                "attachment_count": 1,
            }
        ],
        suggested_sheet_fields={
            "错误原因": "视频时间边界定位失败",
            "结构化差异": "baseline 失败，targeted 在明确时间窗后通过。",
        },
    )
    closure = AutoDebugClosureResult(
        source_job_id="job-source",
        created_targeted_probe_jobs=["job-targeted"],
        created_strategy_follow_up_jobs=[],
        created_verification_jobs=["job-verify"],
        targeted_probe_outcomes=[
            {
                "probe_job_id": "job-targeted",
                "target_id": "video:segment:1",
                "outcome": "target_cleared",
                "summary": "明确时间窗后，模型把结束时间修正到 23 秒。",
            }
        ],
        evidence_summaries=[
            {
                "job_id": "job-source",
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
        final_attribution_candidates=[
            {
                "category": "prompt_scoring_alignment_gap",
                "confidence": "high",
                "summary": "模型不是完全不会识别动作，而是原 prompt 没有稳定触发时间窗约束。",
            }
        ],
        badcase_live_comparison={
            "original_badcase": "原 badcase：0/1 通过，avg_score=0.0。",
            "live_rerun": "Live 复测：baseline 0/3；targeted 1/1；verification 1/1。",
            "decision": "prompt_scoring_alignment_gap",
        },
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

    assert markdown.index("## 一页看懂") < markdown.index("## 原始 Badcase 证据")
    assert "这份报告先回答用户最关心的 5 个问题" in markdown
    assert "| 问题 | 当前结论 |" in markdown
    assert "| 最终归因 | 提示词与评分规则未对齐 / 高置信" in markdown
    assert (
        "| 系统到底跑了什么 | 原始坏案 → baseline 原条件复测 → targeted 定向深挖 → verification 推荐动作验证 → 最终归因 |"
        in markdown
    )
    assert (
        "| 为什么可信 | baseline 用原条件复现问题；targeted/verification 用失败目标和推荐动作复核结论"
        in markdown
    )
    assert "## 后续动作清单" in markdown
    assert "P0" in markdown
    assert "把动作起止时间窗和评分规则显式写入 prompt 后重跑验证" in markdown
    assert "## 用户补充材料" in markdown
    assert "视频第 2 秒右侧按钮闪了一下" in markdown
    assert "`om_supplement_1`" in markdown
    assert markdown.index("## 后续动作清单") < markdown.index("## 证据明细")
