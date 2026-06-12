from debug_agent.storage.database import create_sqlite_memory_session_factory
from debug_agent.storage.models import Base
from debug_agent.storage.repository import DebugJobRepository


def test_repository_persists_spreadsheet_row_mapping() -> None:
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

    mapping = repository.get_spreadsheet_row_mapping(
        spreadsheet_id="spreadsheet-1",
        sheet_id="sheet-1",
        row_id="row-1",
    )

    assert mapping is not None
    assert mapping.spreadsheet_id == "spreadsheet-1"
    assert mapping.sheet_id == "sheet-1"
    assert mapping.row_id == "row-1"
    assert mapping.case_id == "case-1"
    assert mapping.job_id == "job-1"
    assert mapping.created_at
    assert mapping.updated_at


def test_repository_updates_existing_spreadsheet_row_mapping() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)

    repository.save_spreadsheet_row_mapping(
        spreadsheet_id="spreadsheet-1",
        sheet_id="sheet-1",
        row_id="row-1",
        case_id="case-old",
        job_id="job-old",
    )
    repository.save_spreadsheet_row_mapping(
        spreadsheet_id="spreadsheet-1",
        sheet_id="sheet-1",
        row_id="row-1",
        case_id="case-new",
        job_id="job-new",
    )

    mapping = repository.get_spreadsheet_row_mapping(
        spreadsheet_id="spreadsheet-1",
        sheet_id="sheet-1",
        row_id="row-1",
    )

    assert mapping is not None
    assert mapping.case_id == "case-new"
    assert mapping.job_id == "job-new"
    assert mapping.updated_at >= mapping.created_at


def test_repository_finds_spreadsheet_row_mapping_by_job_id() -> None:
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

    mapping = repository.get_spreadsheet_row_mapping_by_job_id("job-1")

    assert mapping is not None
    assert mapping.spreadsheet_id == "spreadsheet-1"
    assert mapping.sheet_id == "sheet-1"
    assert mapping.row_id == "row-1"
    assert mapping.case_id == "case-1"


def test_repository_records_spreadsheet_writeback_success() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)

    repository.save_spreadsheet_writeback_audit(
        job_id="job-1",
        status="succeeded",
        row_id="7",
        report_url="https://debug-agent.local/jobs/job-1/report",
        fields={"错误原因": "模型无法稳定识别涂改后的最终答案。"},
        error_message="",
    )

    audit = repository.get_spreadsheet_writeback_audit("job-1")

    assert audit is not None
    assert audit.job_id == "job-1"
    assert audit.status == "succeeded"
    assert audit.row_id == "7"
    assert audit.report_url == "https://debug-agent.local/jobs/job-1/report"
    assert audit.fields == {"错误原因": "模型无法稳定识别涂改后的最终答案。"}
    assert audit.error_message == ""
    assert audit.created_at
    assert audit.updated_at


def test_repository_records_spreadsheet_writeback_failure() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)

    repository.save_spreadsheet_writeback_audit(
        job_id="job-1",
        status="failed",
        row_id="7",
        report_url="https://debug-agent.local/jobs/job-1/report",
        fields={},
        error_message="permission denied",
    )

    audit = repository.get_spreadsheet_writeback_audit("job-1")

    assert audit is not None
    assert audit.status == "failed"
    assert audit.fields == {}
    assert audit.error_message == "permission denied"


def test_repository_counts_spreadsheet_writeback_audits_by_status() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    repository.save_spreadsheet_writeback_audit(
        job_id="job-success",
        status="succeeded",
        row_id="7",
        report_url="https://debug-agent.local/jobs/job-success/report",
        fields={},
        error_message="",
    )
    repository.save_spreadsheet_writeback_audit(
        job_id="job-failed",
        status="failed",
        row_id="8",
        report_url="https://debug-agent.local/jobs/job-failed/report",
        fields={},
        error_message="permission denied",
    )
    repository.save_spreadsheet_writeback_audit(
        job_id="job-skipped",
        status="skipped",
        row_id="",
        report_url="https://debug-agent.local/jobs/job-skipped/report",
        fields={},
        error_message="spreadsheet row mapping not found",
    )

    summary = repository.count_spreadsheet_writeback_audits_by_status()

    assert summary == {"failed": 1, "skipped": 1, "succeeded": 1}


def test_repository_lists_spreadsheet_writeback_audits_with_status_filter_and_pagination() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    for index, status in enumerate(["failed", "succeeded", "failed"], start=1):
        repository.save_spreadsheet_writeback_audit(
            job_id=f"job-{index}",
            status=status,
            row_id=str(index),
            report_url=f"https://debug-agent.local/jobs/job-{index}/report",
            fields={"index": str(index)},
            error_message="permission denied" if status == "failed" else "",
        )

    audits = repository.list_spreadsheet_writeback_audits(status="failed", limit=1, offset=1)

    assert repository.count_spreadsheet_writeback_audits(status="failed") == 2
    assert [audit.job_id for audit in audits] == ["job-1"]
    assert audits[0].status == "failed"
    assert audits[0].fields == {"index": "1"}


def test_repository_lists_spreadsheet_writeback_audits_newest_updates_first() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    repository.save_spreadsheet_writeback_audit(
        job_id="job-old",
        status="failed",
        row_id="7",
        report_url="https://debug-agent.local/jobs/job-old/report",
        fields={"attempt": "1"},
        error_message="permission denied",
    )
    repository.save_spreadsheet_writeback_audit(
        job_id="job-new",
        status="failed",
        row_id="8",
        report_url="https://debug-agent.local/jobs/job-new/report",
        fields={"attempt": "1"},
        error_message="permission denied",
    )
    repository.save_spreadsheet_writeback_audit(
        job_id="job-old",
        status="succeeded",
        row_id="7",
        report_url="https://debug-agent.local/jobs/job-old/report",
        fields={"attempt": "2"},
        error_message="",
    )

    audits = repository.list_spreadsheet_writeback_audits(limit=2)

    assert [audit.job_id for audit in audits] == ["job-old", "job-new"]
    assert audits[0].status == "succeeded"
    assert audits[0].fields == {"attempt": "2"}
