from debug_agent.reports.generator import (
    DebugReport,
    ExperimentSummary,
    ObservedFailure,
    RootCause,
)
from debug_agent.spreadsheets.writeback import (
    build_report_writeback_fields,
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
