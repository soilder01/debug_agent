from typing import Protocol

from pydantic import BaseModel

from debug_agent.imports.spreadsheet_rows import (
    SpreadsheetImportedRow,
    SpreadsheetRejectedRow,
    parse_spreadsheet_rows,
)
from debug_agent.jobs.service import DebugJobService, SubmittedDebugJob
from debug_agent.storage.repository import DebugJobRepository


class SpreadsheetSourceRow(BaseModel):
    row_id: str
    values: dict[str, object]


class SpreadsheetClient(Protocol):
    def list_rows(self, spreadsheet_id: str, sheet_id: str) -> list[SpreadsheetSourceRow]:
        """Return raw spreadsheet rows from one worksheet."""


class SpreadsheetSyncResult(BaseModel):
    imported_case_ids: list[str]
    imported_rows: list[SpreadsheetImportedRow]
    rejected_rows: list[SpreadsheetRejectedRow]
    jobs: list[SubmittedDebugJob]


def sync_spreadsheet_rows(
    *,
    client: SpreadsheetClient,
    spreadsheet_id: str,
    sheet_id: str,
    repository: DebugJobRepository,
    job_service: DebugJobService,
    create_jobs: bool = True,
    baseline_trials: int = 5,
) -> SpreadsheetSyncResult:
    source_rows = client.list_rows(spreadsheet_id=spreadsheet_id, sheet_id=sheet_id)
    parse_result = parse_spreadsheet_rows([_row_values_with_id(row) for row in source_rows])
    imported_case_ids: list[str] = []
    jobs: list[SubmittedDebugJob] = []
    for imported_row in parse_result.imported_rows:
        case = imported_row.case
        repository.save_case(case)
        imported_case_ids.append(case.case_id)
        job_id = ""
        if create_jobs:
            submitted_job = job_service.submit_case_debug(case.case_id, baseline_trials=baseline_trials)
            jobs.append(submitted_job)
            job_id = submitted_job.job_id
        repository.save_spreadsheet_row_mapping(
            spreadsheet_id=spreadsheet_id,
            sheet_id=sheet_id,
            row_id=imported_row.sheet_row_id,
            case_id=case.case_id,
            job_id=job_id,
        )
    return SpreadsheetSyncResult(
        imported_case_ids=imported_case_ids,
        imported_rows=parse_result.imported_rows,
        rejected_rows=parse_result.rejected_rows,
        jobs=jobs,
    )


def _row_values_with_id(row: SpreadsheetSourceRow) -> dict[str, object]:
    values = dict(row.values)
    values.setdefault("sheet_row_id", row.row_id)
    return values
