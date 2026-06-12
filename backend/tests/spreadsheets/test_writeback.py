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
