import hashlib
from collections.abc import Callable
from uuid import uuid4

from pydantic import BaseModel, Field

from debug_agent.artifacts.layout import safe_path_fragment
from debug_agent.imports.spreadsheet_rows import (
    SpreadsheetImportedRow,
    SpreadsheetRejectedRow,
    parse_spreadsheet_rows,
)
from debug_agent.jobs.service import DebugJobService, SubmittedDebugJob
from debug_agent.spreadsheets.sync import SpreadsheetClient, SpreadsheetSourceRow
from debug_agent.storage.repository import DebugJobRepository


SpreadsheetRowMediaResolver = Callable[[SpreadsheetSourceRow], SpreadsheetSourceRow]


class SpreadsheetRerunResult(BaseModel):
    imported_case_ids: list[str] = Field(default_factory=list)
    imported_rows: list[SpreadsheetImportedRow] = Field(default_factory=list)
    rejected_rows: list[SpreadsheetRejectedRow] = Field(default_factory=list)
    skipped_row_ids: list[str] = Field(default_factory=list)
    jobs: list[SubmittedDebugJob] = Field(default_factory=list)


async def rerun_spreadsheet_rows(
    *,
    client: SpreadsheetClient,
    spreadsheet_id: str,
    sheet_id: str,
    repository: DebugJobRepository,
    job_service: DebugJobService,
    row_ids: list[str],
    case_ids: list[str] | None = None,
    baseline_trials: int = 5,
    auto_run: bool = True,
    artifact_group_id: str = "",
    max_concurrency: int = 1,
    retry_policy: dict[str, object] | None = None,
    row_media_resolver: SpreadsheetRowMediaResolver | None = None,
) -> SpreadsheetRerunResult:
    resolved_artifact_group_id = artifact_group_id or _spreadsheet_rerun_artifact_group_id(sheet_id)
    selected_row_ids = {str(row_id) for row_id in row_ids if str(row_id).strip()}
    selected_case_ids = {str(case_id).strip() for case_id in case_ids or [] if str(case_id).strip()}
    source_rows = client.list_rows(spreadsheet_id=spreadsheet_id, sheet_id=sheet_id)
    rows_to_import, skipped_row_ids = _filter_rows(source_rows, selected_row_ids)
    if row_media_resolver is not None:
        rows_to_import = [row_media_resolver(row) for row in rows_to_import]
    parse_result = parse_spreadsheet_rows([_row_values_with_id(row) for row in rows_to_import])
    imported_rows, case_skipped_row_ids = _filter_imported_rows_by_case_ids(
        parse_result.imported_rows,
        selected_case_ids,
    )
    skipped_row_ids = _unique_strings([*skipped_row_ids, *case_skipped_row_ids])
    if repository.get_batch(resolved_artifact_group_id) is None:
        repository.create_batch(
            batch_id=resolved_artifact_group_id,
            total_jobs=len(imported_rows),
            max_concurrency=max_concurrency,
            retry_policy=retry_policy
            or {
                "source": "spreadsheet_rerun",
                "spreadsheet_id": spreadsheet_id,
                "sheet_id": sheet_id,
                "row_ids": sorted(selected_row_ids),
                "case_ids": sorted(selected_case_ids),
                "baseline_trials": baseline_trials,
                "auto_run": auto_run,
            },
        )
    imported_case_ids: list[str] = []
    jobs: list[SubmittedDebugJob] = []
    for imported_row in imported_rows:
        case = imported_row.case
        repository.save_case(case)
        imported_case_ids.append(case.case_id)
        submitted_job = job_service.submit_case_debug(
            case.case_id,
            baseline_trials=baseline_trials,
            artifact_group_id=resolved_artifact_group_id,
        )
        repository.save_spreadsheet_row_mapping(
            spreadsheet_id=spreadsheet_id,
            sheet_id=sheet_id,
            row_id=imported_row.sheet_row_id,
            case_id=case.case_id,
            job_id=submitted_job.job_id,
        )
        if auto_run:
            submitted_job = await job_service.run_job(submitted_job.job_id)
        jobs.append(submitted_job)
    return SpreadsheetRerunResult(
        imported_case_ids=imported_case_ids,
        imported_rows=imported_rows,
        rejected_rows=parse_result.rejected_rows,
        skipped_row_ids=skipped_row_ids,
        jobs=jobs,
    )


def _filter_rows(
    source_rows: list[SpreadsheetSourceRow],
    selected_row_ids: set[str],
) -> tuple[list[SpreadsheetSourceRow], list[str]]:
    if not selected_row_ids:
        return source_rows, []
    rows_to_import = [row for row in source_rows if row.row_id in selected_row_ids]
    skipped_row_ids = [row.row_id for row in source_rows if row.row_id not in selected_row_ids]
    return rows_to_import, skipped_row_ids


def _filter_imported_rows_by_case_ids(
    imported_rows: list[SpreadsheetImportedRow],
    selected_case_ids: set[str],
) -> tuple[list[SpreadsheetImportedRow], list[str]]:
    if not selected_case_ids:
        return imported_rows, []
    selected = [row for row in imported_rows if row.case.case_id.strip() in selected_case_ids]
    skipped_row_ids = [
        row.sheet_row_id
        for row in imported_rows
        if row.case.case_id.strip() not in selected_case_ids
    ]
    return selected, skipped_row_ids


def _unique_strings(values: list[str]) -> list[str]:
    unique: list[str] = []
    for value in values:
        stripped = value.strip()
        if stripped and stripped not in unique:
            unique.append(stripped)
    return unique


def _row_values_with_id(row: SpreadsheetSourceRow) -> dict[str, object]:
    values = dict(row.values)
    values.setdefault("sheet_row_id", row.row_id)
    return values


def _spreadsheet_rerun_artifact_group_id(sheet_id: str) -> str:
    safe_sheet_id = safe_path_fragment(sheet_id)
    digest = hashlib.sha1(safe_sheet_id.encode("utf-8")).hexdigest()[:8]
    return f"sheet-rerun-{digest}-{uuid4().hex[:12]}"
