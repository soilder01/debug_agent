import json

from debug_agent.jobs.service import DebugJobService
from debug_agent.spreadsheets.sync import SpreadsheetSourceRow, sync_spreadsheet_rows
from debug_agent.storage.database import create_sqlite_memory_session_factory
from debug_agent.storage.models import Base
from debug_agent.storage.repository import DebugJobRepository


class StaticSpreadsheetClient:
    def __init__(self, rows: list[SpreadsheetSourceRow]) -> None:
        self.rows = rows
        self.requested_spreadsheet_id = ""
        self.requested_sheet_id = ""

    def list_rows(self, spreadsheet_id: str, sheet_id: str) -> list[SpreadsheetSourceRow]:
        self.requested_spreadsheet_id = spreadsheet_id
        self.requested_sheet_id = sheet_id
        return self.rows


def test_sync_spreadsheet_rows_persists_cases_and_creates_five_replay_jobs() -> None:
    repository, service = _make_repository_and_service()
    golden_answer = {"answers": [{"box_id": 1, "student_answer": "42"}]}
    client = StaticSpreadsheetClient(
        [
            SpreadsheetSourceRow(
                row_id="row-1",
                values={
                    "case_id": "synced-case-1",
                    "image_uri": "file://synced-case-1.png",
                    "prompt": "Read the answer",
                    "golden_answer_json": golden_answer,
                    "scoring_standard": "exact match",
                    "predictions_json": [
                        {"trial": 1, "raw_output": json.dumps(golden_answer), "score": 1},
                    ],
                    "avg_score": 1.0,
                },
            )
        ]
    )

    result = sync_spreadsheet_rows(
        client=client,
        spreadsheet_id="spreadsheet-1",
        sheet_id="sheet-1",
        repository=repository,
        job_service=service,
    )

    assert client.requested_spreadsheet_id == "spreadsheet-1"
    assert client.requested_sheet_id == "sheet-1"
    assert result.imported_case_ids == ["synced-case-1"]
    assert result.imported_rows[0].sheet_row_id == "row-1"
    assert result.rejected_rows == []
    assert len(result.jobs) == 1
    job = repository.get_job(result.jobs[0].job_id)
    assert job is not None
    assert job.baseline_trials == 5
    assert repository.get_case("synced-case-1") is not None
    mapping = repository.get_spreadsheet_row_mapping(
        spreadsheet_id="spreadsheet-1",
        sheet_id="sheet-1",
        row_id="row-1",
    )
    assert mapping is not None
    assert mapping.case_id == "synced-case-1"
    assert mapping.job_id == result.jobs[0].job_id


def test_sync_spreadsheet_rows_reports_rejections_without_creating_jobs() -> None:
    repository, service = _make_repository_and_service()
    client = StaticSpreadsheetClient(
        [
            SpreadsheetSourceRow(
                row_id="bad-row",
                values={
                    "case_id": "bad-case",
                    "image_uri": "file://bad-case.png",
                    "prompt": "Read the answer",
                    "golden_answer_json": "not-json",
                    "scoring_standard": "exact match",
                    "predictions_json": [],
                    "avg_score": 0.0,
                },
            )
        ]
    )

    result = sync_spreadsheet_rows(
        client=client,
        spreadsheet_id="spreadsheet-1",
        sheet_id="sheet-1",
        repository=repository,
        job_service=service,
    )

    assert result.imported_case_ids == []
    assert result.jobs == []
    assert len(result.rejected_rows) == 1
    assert result.rejected_rows[0].sheet_row_id == "bad-row"
    assert repository.get_case("bad-case") is None


def _make_repository_and_service() -> tuple[DebugJobRepository, DebugJobService]:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    return repository, DebugJobService(repository)
