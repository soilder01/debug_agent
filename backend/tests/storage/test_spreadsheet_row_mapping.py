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
