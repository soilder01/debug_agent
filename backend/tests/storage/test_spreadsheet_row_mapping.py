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
