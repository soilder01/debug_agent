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
    assert '{"video_action_segments":[{"end_s":23.0}]}' in markdown
    assert "model_instability/high" in markdown
