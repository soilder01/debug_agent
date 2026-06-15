from debug_agent.cases.fixtures import load_fixture_case
from debug_agent.experiments.runner import ExperimentEvidence
from debug_agent.judging.runner import JudgeResult
from debug_agent.jobs.service import SubmittedDebugJob
from debug_agent.reports.generator import (
    DebugReport,
    ExperimentSummary,
    ObservedFailure,
    RootCause,
)
from debug_agent.spreadsheets.writeback import (
    build_report_writeback_fields,
    make_spreadsheet_writeback_completion_hook,
    write_report_for_job,
    write_report_to_spreadsheet_row,
)
from debug_agent.storage.database import create_sqlite_memory_session_factory
from debug_agent.storage.models import Base
from debug_agent.storage.repository import DebugJobRepository


class RecordingWritebackClient:
    def __init__(self) -> None:
        self.spreadsheet_id = ""
        self.sheet_id = ""
        self.row_id = ""
        self.fields: dict[str, str] = {}

    def update_row(self, spreadsheet_id: str, sheet_id: str, row_id: str, fields: dict[str, str]) -> None:
        self.spreadsheet_id = spreadsheet_id
        self.sheet_id = sheet_id
        self.row_id = row_id
        self.fields = fields


class FailingWritebackClient:
    def update_row(self, spreadsheet_id: str, sheet_id: str, row_id: str, fields: dict[str, str]) -> None:
        raise RuntimeError("permission denied")


def test_build_report_writeback_fields_includes_root_cause_feedback_and_link() -> None:
    report = _make_report()

    fields = build_report_writeback_fields(report, report_url="https://debug-agent.local/reports/job-1")

    assert fields["debug1状态"] == "待人工确认"
    assert fields["错误原因"] == "模型无法稳定识别涂改后的最终答案。"
    assert fields["分析报告链接"] == "https://debug-agent.local/reports/job-1"
    assert "当前样本低分且人工备注指向涂改区域识别失败。" in fields["评估问题反馈"]
    assert "复测稳定性：unstable" in fields["评估问题反馈"]
    assert "复测通过率：40%" in fields["评估问题反馈"]
    assert "失败次数：3/5" in fields["评估问题反馈"]


def test_build_report_writeback_fields_preserves_native_target_delta_and_artifacts() -> None:
    report = _make_report().model_copy(
        update={
            "suggested_sheet_fields": {
                "debug1状态": "待人工确认",
                "错误原因": "结构化评分显示 multimodal:conflict:1 存在 conflict_actual_mismatch。",
                "影响目标": "multimodal:conflict:1",
                "结构化差异": (
                    "multimodal:conflict:1 conflict_actual_mismatch: "
                    "expected=image and caption both describe a cat actual=image shows dog while caption says cat"
                ),
                "证据产物": "multimodal-writeback:baseline:0:input-snapshot",
            }
        }
    )

    fields = build_report_writeback_fields(report, report_url="https://debug-agent.local/reports/job-1")

    assert fields["影响目标"] == "multimodal:conflict:1"
    assert fields["结构化差异"].startswith("multimodal:conflict:1 conflict_actual_mismatch")
    assert fields["证据产物"] == "multimodal-writeback:baseline:0:input-snapshot"
    assert fields["分析报告链接"] == "https://debug-agent.local/reports/job-1"


def test_build_report_writeback_fields_includes_recommended_actions() -> None:
    report = _make_report().model_copy(
        update={
            "recommended_actions": [
                {
                    "category": "prompt",
                    "priority": "high",
                    "summary": "强化跨模态对比步骤。",
                    "detail": "要求模型先分别列出 image/text 证据，再输出冲突结论。",
                },
                {
                    "category": "model_capability",
                    "priority": "high",
                    "summary": "将跨模态融合短板纳入模型能力归因。",
                    "detail": "单模态通过但跨模态失败，优先检查 fusion/alignment 能力。",
                },
            ]
        }
    )

    fields = build_report_writeback_fields(report, report_url="https://debug-agent.local/reports/job-1")

    assert fields["推荐操作"] == (
        "prompt/high：强化跨模态对比步骤。 - 要求模型先分别列出 image/text 证据，再输出冲突结论。\n"
        "model_capability/high：将跨模态融合短板纳入模型能力归因。 - 单模态通过但跨模态失败，优先检查 fusion/alignment 能力。"
    )
    assert "prompt/high：强化跨模态对比步骤。" in fields["评估问题反馈"]


def test_build_report_writeback_fields_includes_recommended_action_verification_results() -> None:
    report = _make_report().model_copy(
        update={
            "verification_results": [
                {
                    "action_index": 0,
                    "verification_job_id": "job-verify-1",
                    "result": "resolved",
                    "source_success_rate": 0.4,
                    "verification_success_rate": 1.0,
                    "summary": "验证任务通过率 100%，高于原任务 40%，推荐操作可能已修复该问题。",
                },
                {
                    "action_index": 1,
                    "verification_job_id": "job-verify-2",
                    "result": "regressed",
                    "source_success_rate": 0.4,
                    "verification_success_rate": 0.2,
                    "summary": "验证任务通过率 20%，低于原任务 40%，推荐操作可能引入回归。",
                },
            ]
        }
    )

    fields = build_report_writeback_fields(report, report_url="https://debug-agent.local/reports/job-1")

    assert "推荐操作验证：" in fields["评估问题反馈"]
    assert "操作 1/resolved：验证任务通过率 100%，高于原任务 40%，推荐操作可能已修复该问题。" in fields["评估问题反馈"]
    assert "操作 2/regressed：验证任务通过率 20%，低于原任务 40%，推荐操作可能引入回归。" in fields["评估问题反馈"]


def test_build_report_writeback_fields_includes_strategy_follow_up_results() -> None:
    report = _make_report().model_copy(
        update={
            "strategy_follow_up_results": [
                {
                    "source_job_id": "job-1",
                    "stage": "evidence_audit",
                    "planned_steps": "strategy_evidence_audit_probe",
                    "follow_up_job_id": "job-strategy-follow-up-1",
                    "actor": "strategy-operator",
                    "note": "audit evidence chain",
                    "created_at": "2026-06-15T00:00:02+00:00",
                    "outcome": "passed_stop_condition",
                    "success_rate": 1.0,
                    "summary": "Strategy follow-up job passed all probes; stop condition is likely satisfied.",
                    "escalation": "",
                },
                {
                    "source_job_id": "job-1",
                    "stage": "ablation_expansion",
                    "planned_steps": "strategy_ablation_expansion_probe",
                    "follow_up_job_id": "job-strategy-follow-up-2",
                    "actor": "strategy-operator",
                    "note": "expand ablation",
                    "created_at": "2026-06-15T00:00:03+00:00",
                    "outcome": "needs_escalation",
                    "success_rate": 0.0,
                    "summary": "Strategy follow-up job still failed; escalation is recommended.",
                    "escalation": "Run single-modality capability probes before keeping cross-modal attribution.",
                },
            ]
        }
    )

    fields = build_report_writeback_fields(report, report_url="https://debug-agent.local/reports/job-1")

    assert "策略 Follow-up：" in fields["评估问题反馈"]
    assert (
        "evidence_audit/passed_stop_condition：Strategy follow-up job passed all probes; stop condition is likely satisfied."
        in fields["评估问题反馈"]
    )
    assert "ablation_expansion/needs_escalation：Strategy follow-up job still failed; escalation is recommended." in fields[
        "评估问题反馈"
    ]
    assert "升级：Run single-modality capability probes before keeping cross-modal attribution." in fields["评估问题反馈"]


def test_build_report_writeback_fields_includes_targeted_probe_results() -> None:
    report = _make_report().model_copy(
        update={
            "targeted_probe_results": [
                {
                    "source_job_id": "job-1",
                    "target_id": "multimodal:conflict:1",
                    "planned_steps": "targeted_multimodal_conflict_probe",
                    "probe_job_id": "job-targeted-probe-1",
                    "actor": "targeted-operator",
                    "note": "probe conflict target",
                    "created_at": "2026-06-15T00:00:02+00:00",
                    "outcome": "target_still_failing",
                    "success_rate": 0.0,
                    "summary": "Targeted probe still failed on multimodal:conflict:1; escalation is recommended.",
                    "escalation": "Run deeper localized replay or modality-specific probes for multimodal:conflict:1.",
                }
            ]
        }
    )

    fields = build_report_writeback_fields(report, report_url="https://debug-agent.local/reports/job-1")

    assert "Targeted Probe：" in fields["评估问题反馈"]
    assert "multimodal:conflict:1/target_still_failing" in fields["评估问题反馈"]
    assert "Targeted probe still failed on multimodal:conflict:1; escalation is recommended." in fields["评估问题反馈"]
    assert "升级：Run deeper localized replay or modality-specific probes for multimodal:conflict:1." in fields[
        "评估问题反馈"
    ]


def test_build_report_writeback_fields_includes_targeted_probe_guardrails() -> None:
    report = _make_report().model_copy(
        update={
            "follow_up_experiments": [
                {
                    "source": "targeted_probe_guardrail",
                    "target_id": "multimodal:conflict:1",
                    "result": "target_still_failing",
                    "planned_steps": "",
                    "summary": (
                        "Targeted probe chain for multimodal:conflict:1 reached max depth 3; "
                        "stop automatic escalation and require human review."
                    ),
                    "stop_condition": "max_targeted_probe_depth_reached",
                }
            ],
            "human_handoff_requests": [
                {
                    "source": "targeted_probe_guardrail",
                    "target_id": "multimodal:conflict:1",
                    "priority": "high",
                    "reason": "max_targeted_probe_depth_reached",
                    "summary": "Targeted probe chain for multimodal:conflict:1 reached max depth 3.",
                    "recommended_owner": "human-debugger",
                    "next_action": "Review the full targeted probe chain, inspect evidence artifacts, and decide whether to update prompt, evaluation assets, or model capability attribution.",
                }
            ],
            "human_handoff_statuses": [
                {
                    "job_id": "job-1",
                    "target_id": "multimodal:conflict:1",
                    "status": "resolved",
                    "actor": "human-debugger",
                    "note": "Final attribution: prompt lacks cross-modal conflict checklist; update prompt before model capability attribution.",
                    "created_at": "2026-06-15T00:00:00+00:00",
                    "updated_at": "2026-06-15T00:00:01+00:00",
                }
            ],
            "final_attributions": [
                {
                    "source": "human_handoff",
                    "target_id": "multimodal:conflict:1",
                    "category": "prompt_issue",
                    "status": "resolved",
                    "actor": "human-debugger",
                    "summary": "Final attribution: prompt lacks cross-modal conflict checklist; update prompt before model capability attribution.",
                    "recommended_action": "Update prompt instructions and rerun verification before assigning model capability blame.",
                }
            ],
            "final_attribution_verification_results": [
                {
                    "source": "final_attribution",
                    "target_id": "multimodal:conflict:1",
                    "category": "prompt_issue",
                    "verification_job_id": "job-final-attribution-verify",
                    "result": "resolved",
                    "success_rate": 1.0,
                    "summary": "Final attribution verification for multimodal:conflict:1 resolved the issue.",
                }
            ],
            "final_attribution_recovery_results": [
                {
                    "source": "final_attribution_recovery",
                    "target_id": "multimodal:conflict:1",
                    "category": "prompt_issue",
                    "recovery_job_id": "job-final-attribution-recovery",
                    "result": "closed",
                    "success_rate": 1.0,
                    "summary": "Final attribution recovery for multimodal:conflict:1 closed the attribution loop.",
                }
            ],
        }
    )

    fields = build_report_writeback_fields(report, report_url="https://debug-agent.local/reports/job-1")

    assert "Targeted Guardrail：" in fields["评估问题反馈"]
    assert "multimodal:conflict:1/target_still_failing：Targeted probe chain for multimodal:conflict:1" in fields[
        "评估问题反馈"
    ]
    assert "停止条件：max_targeted_probe_depth_reached" in fields["评估问题反馈"]
    assert "人工接管：" in fields["评估问题反馈"]
    assert "multimodal:conflict:1/high/max_targeted_probe_depth_reached" in fields["评估问题反馈"]
    assert "负责人：human-debugger" in fields["评估问题反馈"]
    assert "人工接管状态：" in fields["评估问题反馈"]
    assert "multimodal:conflict:1/resolved" in fields["评估问题反馈"]
    assert "处理人：human-debugger" in fields["评估问题反馈"]
    assert "结论：Final attribution: prompt lacks cross-modal conflict checklist" in fields["评估问题反馈"]
    assert "最终归因：" in fields["评估问题反馈"]
    assert "multimodal:conflict:1/prompt_issue/resolved" in fields["评估问题反馈"]
    assert "建议：Update prompt instructions and rerun verification before assigning model capability blame." in fields[
        "评估问题反馈"
    ]
    assert "最终归因验证：" in fields["评估问题反馈"]
    assert "multimodal:conflict:1/prompt_issue/resolved" in fields["评估问题反馈"]
    assert "验证任务：job-final-attribution-verify" in fields["评估问题反馈"]
    assert "通过率：100%" in fields["评估问题反馈"]
    assert "最终归因恢复：" in fields["评估问题反馈"]
    assert "multimodal:conflict:1/prompt_issue/closed" in fields["评估问题反馈"]
    assert "恢复任务：job-final-attribution-recovery" in fields["评估问题反馈"]


def test_write_report_to_spreadsheet_row_updates_client_with_payload() -> None:
    client = RecordingWritebackClient()
    report = _make_report()

    result = write_report_to_spreadsheet_row(
        client=client,
        spreadsheet_id="spreadsheet-1",
        sheet_id="sheet-1",
        row_id="row-1",
        report=report,
        report_url="https://debug-agent.local/reports/job-1",
    )

    assert client.spreadsheet_id == "spreadsheet-1"
    assert client.sheet_id == "sheet-1"
    assert client.row_id == "row-1"
    assert client.fields["错误原因"] == "模型无法稳定识别涂改后的最终答案。"
    assert result.row_id == "row-1"
    assert result.fields == client.fields


def test_write_report_for_job_resolves_mapping_and_updates_row() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    repository.save_spreadsheet_row_mapping(
        spreadsheet_id="spreadsheet-1",
        sheet_id="sheet-1",
        row_id="row-1",
        case_id="case-1",
        job_id="job-1",
    )
    client = RecordingWritebackClient()

    result = write_report_for_job(
        repository=repository,
        client=client,
        job_id="job-1",
        report=_make_report(),
        report_url="https://debug-agent.local/reports/job-1",
    )

    assert result is not None
    assert result.row_id == "row-1"
    assert client.spreadsheet_id == "spreadsheet-1"
    assert client.sheet_id == "sheet-1"
    assert client.row_id == "row-1"
    assert client.fields["分析报告链接"] == "https://debug-agent.local/reports/job-1"


def test_write_report_for_job_returns_none_when_mapping_is_missing() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    client = RecordingWritebackClient()

    result = write_report_for_job(
        repository=repository,
        client=client,
        job_id="missing-job",
        report=_make_report(),
        report_url="https://debug-agent.local/reports/job-1",
    )

    assert result is None
    assert client.fields == {}


def test_completion_hook_builds_report_and_writes_mapped_row() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    case = load_fixture_case("handwrite233").model_copy(update={"case_id": "auto-writeback-case"})
    repository.save_case(case)
    repository.create_job(job_id="job-1", case_id=case.case_id, baseline_trials=2)
    repository.save_evidence(
        job_id="job-1",
        case_id=case.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id="auto-writeback-case:baseline:0",
                step_name="baseline_replay",
                trial=0,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=0, reasons=["student_answer_mismatch"]),
            )
        ],
    )
    repository.mark_completed("job-1")
    repository.save_spreadsheet_row_mapping(
        spreadsheet_id="spreadsheet-1",
        sheet_id="sheet-1",
        row_id="7",
        case_id=case.case_id,
        job_id="job-1",
    )
    client = RecordingWritebackClient()
    hook = make_spreadsheet_writeback_completion_hook(
        repository=repository,
        client=client,
        report_base_url="https://debug-agent.local/",
    )

    hook(SubmittedDebugJob(job_id="job-1", case_id=case.case_id, status="completed"))

    assert client.spreadsheet_id == "spreadsheet-1"
    assert client.sheet_id == "sheet-1"
    assert client.row_id == "7"
    assert client.fields["分析报告链接"] == "https://debug-agent.local/jobs/job-1/report"
    assert client.fields["错误原因"]
    assert "复测稳定性：" in client.fields["评估问题反馈"]
    audit = repository.get_spreadsheet_writeback_audit("job-1")
    assert audit is not None
    assert audit.status == "succeeded"
    assert audit.row_id == "7"
    assert audit.report_url == "https://debug-agent.local/jobs/job-1/report"
    assert audit.fields == client.fields
    assert audit.error_message == ""


def test_completion_hook_writes_source_report_when_strategy_follow_up_completes() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    case = load_fixture_case("handwrite233").model_copy(update={"case_id": "auto-writeback-strategy-case"})
    repository.save_case(case)
    repository.create_job(job_id="job-source", case_id=case.case_id, baseline_trials=1)
    repository.save_evidence(
        job_id="job-source",
        case_id=case.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id="auto-writeback-strategy-case:baseline:0",
                step_name="baseline_replay",
                trial=0,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=0, reasons=["student_answer_mismatch"]),
            )
        ],
    )
    repository.create_job(job_id="job-strategy-follow-up", case_id=case.case_id, baseline_trials=1)
    repository.save_evidence(
        job_id="job-strategy-follow-up",
        case_id=case.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id="job-strategy-follow-up:strategy-pass",
                step_name="strategy_evidence_audit_probe",
                trial=0,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=1, reasons=[]),
            )
        ],
    )
    repository.mark_completed("job-strategy-follow-up")
    repository.save_strategy_follow_up_job(
        source_job_id="job-source",
        stage="evidence_audit",
        planned_steps="strategy_evidence_audit_probe",
        follow_up_job_id="job-strategy-follow-up",
        actor="strategy-operator",
        note="audit evidence chain",
    )
    repository.save_spreadsheet_row_mapping(
        spreadsheet_id="spreadsheet-1",
        sheet_id="sheet-1",
        row_id="source-row",
        case_id=case.case_id,
        job_id="job-source",
    )
    client = RecordingWritebackClient()
    hook = make_spreadsheet_writeback_completion_hook(
        repository=repository,
        client=client,
        report_base_url="https://debug-agent.local",
    )

    hook(SubmittedDebugJob(job_id="job-strategy-follow-up", case_id=case.case_id, status="completed"))

    assert client.row_id == "source-row"
    assert client.fields["分析报告链接"] == "https://debug-agent.local/jobs/job-source/report"
    assert "策略 Follow-up：" in client.fields["评估问题反馈"]
    assert "evidence_audit/passed_stop_condition" in client.fields["评估问题反馈"]
    audit = repository.get_spreadsheet_writeback_audit("job-source")
    assert audit is not None
    assert audit.status == "succeeded"
    assert audit.row_id == "source-row"
    assert audit.report_url == "https://debug-agent.local/jobs/job-source/report"


def test_completion_hook_writes_source_report_when_targeted_probe_completes() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    case = load_fixture_case("handwrite233").model_copy(update={"case_id": "auto-writeback-targeted-case"})
    repository.save_case(case)
    repository.create_job(job_id="job-source", case_id=case.case_id, baseline_trials=1)
    repository.save_evidence(
        job_id="job-source",
        case_id=case.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id="auto-writeback-targeted-case:baseline:0",
                step_name="baseline_replay",
                trial=0,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=0, reasons=["box:1 student_answer_mismatch"]),
            )
        ],
    )
    repository.create_job(job_id="job-targeted-probe", case_id=case.case_id, baseline_trials=1)
    repository.save_evidence(
        job_id="job-targeted-probe",
        case_id=case.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id="job-targeted-probe:still-fail",
                step_name="targeted_image_region_probe",
                trial=0,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=0, reasons=["image:region:1 region_label_mismatch"]),
            )
        ],
    )
    repository.mark_completed("job-targeted-probe")
    repository.save_targeted_probe_job(
        source_job_id="job-source",
        target_id="image:region:1",
        planned_steps="targeted_image_region_probe",
        probe_job_id="job-targeted-probe",
        actor="targeted-operator",
        note="probe image region",
    )
    repository.save_spreadsheet_row_mapping(
        spreadsheet_id="spreadsheet-1",
        sheet_id="sheet-1",
        row_id="source-row",
        case_id=case.case_id,
        job_id="job-source",
    )
    client = RecordingWritebackClient()
    hook = make_spreadsheet_writeback_completion_hook(
        repository=repository,
        client=client,
        report_base_url="https://debug-agent.local",
    )

    hook(SubmittedDebugJob(job_id="job-targeted-probe", case_id=case.case_id, status="completed"))

    assert client.row_id == "source-row"
    assert client.fields["分析报告链接"] == "https://debug-agent.local/jobs/job-source/report"
    assert "Targeted Probe：" in client.fields["评估问题反馈"]
    assert "image:region:1/target_still_failing" in client.fields["评估问题反馈"]
    audit = repository.get_spreadsheet_writeback_audit("job-source")
    assert audit is not None
    assert audit.status == "succeeded"
    assert audit.row_id == "source-row"
    assert audit.report_url == "https://debug-agent.local/jobs/job-source/report"


def test_completion_hook_skips_when_report_cannot_be_rebuilt() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    client = RecordingWritebackClient()
    hook = make_spreadsheet_writeback_completion_hook(
        repository=repository,
        client=client,
        report_base_url="https://debug-agent.local",
    )

    hook(SubmittedDebugJob(job_id="missing-job", case_id="missing-case", status="completed"))

    assert client.fields == {}
    audit = repository.get_spreadsheet_writeback_audit("missing-job")
    assert audit is not None
    assert audit.status == "skipped"
    assert audit.row_id == ""
    assert audit.report_url == "https://debug-agent.local/jobs/missing-job/report"
    assert audit.fields == {}
    assert audit.error_message == "debug report could not be rebuilt"


def test_completion_hook_records_skipped_audit_when_mapping_is_missing() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    case = load_fixture_case("handwrite233").model_copy(update={"case_id": "auto-writeback-unmapped-case"})
    repository.save_case(case)
    repository.create_job(job_id="job-unmapped", case_id=case.case_id, baseline_trials=1)
    repository.save_evidence(
        job_id="job-unmapped",
        case_id=case.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id="auto-writeback-unmapped-case:baseline:0",
                step_name="baseline_replay",
                trial=0,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=0, reasons=["student_answer_mismatch"]),
            )
        ],
    )
    repository.mark_completed("job-unmapped")
    client = RecordingWritebackClient()
    hook = make_spreadsheet_writeback_completion_hook(
        repository=repository,
        client=client,
        report_base_url="https://debug-agent.local",
    )

    hook(SubmittedDebugJob(job_id="job-unmapped", case_id=case.case_id, status="completed"))

    assert client.fields == {}
    audit = repository.get_spreadsheet_writeback_audit("job-unmapped")
    assert audit is not None
    assert audit.status == "skipped"
    assert audit.row_id == ""
    assert audit.report_url == "https://debug-agent.local/jobs/job-unmapped/report"
    assert audit.fields == {}
    assert audit.error_message == "spreadsheet row mapping not found"


def test_completion_hook_records_failed_writeback_audit_before_reraising() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    case = load_fixture_case("handwrite233").model_copy(update={"case_id": "auto-writeback-failure-case"})
    repository.save_case(case)
    repository.create_job(job_id="job-1", case_id=case.case_id, baseline_trials=1)
    repository.save_evidence(
        job_id="job-1",
        case_id=case.case_id,
        evidence=[
            ExperimentEvidence(
                evidence_id="auto-writeback-failure-case:baseline:0",
                step_name="baseline_replay",
                trial=0,
                raw_output=case.predictions[0].raw_output,
                judge=JudgeResult(score=0, reasons=["student_answer_mismatch"]),
            )
        ],
    )
    repository.mark_completed("job-1")
    repository.save_spreadsheet_row_mapping(
        spreadsheet_id="spreadsheet-1",
        sheet_id="sheet-1",
        row_id="7",
        case_id=case.case_id,
        job_id="job-1",
    )
    hook = make_spreadsheet_writeback_completion_hook(
        repository=repository,
        client=FailingWritebackClient(),
        report_base_url="https://debug-agent.local",
    )

    try:
        hook(SubmittedDebugJob(job_id="job-1", case_id=case.case_id, status="completed"))
    except RuntimeError as exc:
        assert str(exc) == "permission denied"
    else:
        raise AssertionError("expected writeback failure")

    audit = repository.get_spreadsheet_writeback_audit("job-1")
    assert audit is not None
    assert audit.status == "failed"
    assert audit.row_id == "7"
    assert audit.report_url == "https://debug-agent.local/jobs/job-1/report"
    assert audit.fields == {}
    assert audit.error_message == "permission denied"


def _make_report() -> DebugReport:
    return DebugReport(
        job_id="job-1",
        case_id="case-1",
        status="needs_human_review",
        observed_failure=ObservedFailure(
            type="erasure_revision_failure",
            summary="模型在涂改区域识别不稳定。",
            affected_box_ids=[1],
        ),
        planned_experiments=["baseline_replay"],
        experiment_summary=ExperimentSummary(
            total_trials=5,
            success_count=2,
            failed_trial_count=3,
            success_rate=0.4,
            stability_label="unstable",
            evidence_ids=["e1", "e2"],
            image_artifact_ids=[],
        ),
        root_cause=RootCause(
            label="erasure_revision_failure",
            confidence="medium",
            evidence_summary="当前样本低分且人工备注指向涂改区域识别失败。",
        ),
        suggested_sheet_fields={
            "debug1状态": "待人工确认",
            "错误原因": "模型无法稳定识别涂改后的最终答案。",
        },
    )
