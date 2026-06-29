from debug_agent.assistant.debug_lessons import build_debug_lesson_from_report
from debug_agent.api.auto_closure_report_controller import AutoClosureReportController
from debug_agent.jobs.auto_closure import AutoDebugClosureResult
from debug_agent.reports.generator import DebugReport, ObservedFailure, RootCause


def test_build_debug_lesson_from_report_preserves_evidence_boundary() -> None:
    report = DebugReport(
        job_id="job-video-1",
        case_id="case-video-1",
        status="needs_human_review",
        observed_failure=ObservedFailure(
            type="video_action_missing",
            summary="视频动作片段漏掉右臂套袋动作。",
            affected_box_ids=[],
        ),
        root_cause=RootCause(
            label="prompt_scoring_alignment_gap",
            confidence="medium",
            evidence_summary="原 prompt 没有稳定触发右臂动作评分点。",
        ),
        planned_experiments=[],
        suggested_sheet_fields={},
        recommended_actions=[
            {"priority": "P0", "summary": "补充右臂动作评分点并重跑 controlled probe。"}
        ],
    )
    closure = AutoDebugClosureResult(
        source_job_id="job-video-1",
        evidence_summaries=[
            {"evidence_id": "e-baseline", "judge_score": "0"},
            {"evidence_id": "e-probe", "judge_score": "0"},
        ],
        final_attribution_candidates=[
            {
                "category": "prompt_scoring_alignment_gap",
                "confidence": "medium",
                "summary": "候选方向存在，但没有 supported comparison。",
            }
        ],
        debug_loop={
            "decision": "stopped_evidence_exhausted",
            "stop_reason": "达到最大探索轮次后仍没有 supported causal comparison。",
        },
        writeback_status="not_requested",
    )

    lesson = build_debug_lesson_from_report(
        report=report,
        closure=closure,
        source_uri="/api/artifacts/files/case-video-report.md",
    )

    assert lesson.job_id == "job-video-1"
    assert lesson.case_id == "case-video-1"
    assert lesson.root_cause == "prompt_scoring_alignment_gap"
    assert lesson.confidence == "medium"
    assert lesson.debug_loop_decision == "stopped_evidence_exhausted"
    assert "2 条 evidence" in lesson.evidence_boundary
    assert "supported causal comparison" in lesson.evidence_boundary
    assert "P0" in lesson.recommended_action
    assert lesson.approved is False


def test_auto_closure_controller_records_debug_lesson_without_blocking_report() -> None:
    recorded = []
    controller = AutoClosureReportController(
        job_repository=lambda: None,  # type: ignore[return-value]
        job_service=lambda: None,  # type: ignore[return-value]
        build_report=lambda job_id: None,
        artifact_dir_for_job_id=lambda job_id: None,  # type: ignore[return-value]
        video_clipper_for_job=lambda job_id: None,  # type: ignore[return-value]
        original_cot_excerpt=lambda case: "",
        original_prediction=lambda case: "",
        record_debug_lesson=recorded.append,
    )
    report = DebugReport(
        job_id="job-lesson",
        case_id="case-lesson",
        status="needs_human_review",
        observed_failure=ObservedFailure(
            type="answer_mismatch",
            summary="模型把正确答案 8 输出成 3。",
            affected_box_ids=[],
        ),
        root_cause=RootCause(
            label="answer_mismatch",
            confidence="high",
            evidence_summary="baseline 复现答案不一致。",
        ),
        planned_experiments=[],
        suggested_sheet_fields={},
    )
    closure = AutoDebugClosureResult(
        source_job_id="job-lesson",
        debug_loop={"decision": "verified_root_cause_found"},
        evidence_summaries=[{"evidence_id": "e1"}],
    )

    controller.record_debug_lesson(
        report=report,
        closure=closure,
        report_artifact_url="/api/artifacts/files/report.md",
    )

    assert recorded
    assert recorded[0].job_id == "job-lesson"
    assert recorded[0].debug_loop_decision == "verified_root_cause_found"
