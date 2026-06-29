from __future__ import annotations

import json
from collections.abc import Callable

from fastapi import APIRouter
from pydantic import ValidationError

from debug_agent.api.schemas import (
    CsvImportRequest,
    CsvImportResponse,
    JsonlImportRequest,
    JsonlImportResponse,
    JsonlRejectedLine,
    SpreadsheetImportedRowResponse,
    SpreadsheetRowImportRequest,
    SpreadsheetRowImportResponse,
)
from debug_agent.artifacts.layout import DEFAULT_ARTIFACT_GROUP
from debug_agent.cases.models import DebugCase
from debug_agent.imports.csv_cases import parse_csv_cases
from debug_agent.imports.spreadsheet_rows import parse_spreadsheet_rows
from debug_agent.jobs.service import DebugJobService, SubmittedDebugJob
from debug_agent.storage.repository import DebugJobRepository


def build_import_router(
    *,
    job_repository: DebugJobRepository,
    job_service: DebugJobService,
    raise_if_usage_budget_blocks_submission: Callable[[], None],
    new_artifact_group_id: Callable[[str], str],
) -> APIRouter:
    router = APIRouter()

    @router.post("/imports/jsonl", status_code=202)
    def import_jsonl_cases(request: JsonlImportRequest) -> JsonlImportResponse:
        if request.create_jobs:
            raise_if_usage_budget_blocks_submission()
        artifact_group_id = (
            new_artifact_group_id("jsonl-import")
            if request.create_jobs
            else DEFAULT_ARTIFACT_GROUP
        )
        imported_case_ids: list[str] = []
        jobs: list[SubmittedDebugJob] = []
        rejected_lines: list[JsonlRejectedLine] = []
        for line_number, line in enumerate(request.jsonl.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                case = DebugCase.model_validate(json.loads(line))
                job_repository.save_case(case)
                imported_case_ids.append(case.case_id)
                if request.create_jobs:
                    jobs.append(
                        job_service.submit_case_debug(
                            case.case_id,
                            baseline_trials=request.baseline_trials,
                            artifact_group_id=artifact_group_id,
                        )
                    )
            except (json.JSONDecodeError, ValidationError, FileNotFoundError) as exc:
                rejected_lines.append(
                    JsonlRejectedLine(line_number=line_number, error_message=str(exc))
                )
        return JsonlImportResponse(
            imported_case_ids=imported_case_ids, jobs=jobs, rejected_lines=rejected_lines
        )

    @router.post("/imports/csv", status_code=202)
    def import_csv_cases(request: CsvImportRequest) -> CsvImportResponse:
        if request.create_jobs:
            raise_if_usage_budget_blocks_submission()
        artifact_group_id = (
            new_artifact_group_id("csv-import")
            if request.create_jobs
            else DEFAULT_ARTIFACT_GROUP
        )
        parse_result = parse_csv_cases(request.csv_text)
        imported_case_ids: list[str] = []
        jobs: list[SubmittedDebugJob] = []
        for case in parse_result.cases:
            job_repository.save_case(case)
            imported_case_ids.append(case.case_id)
            if request.create_jobs:
                jobs.append(
                    job_service.submit_case_debug(
                        case.case_id,
                        baseline_trials=request.baseline_trials,
                        artifact_group_id=artifact_group_id,
                    )
                )
        return CsvImportResponse(
            imported_case_ids=imported_case_ids,
            jobs=jobs,
            rejected_rows=parse_result.rejected_rows,
        )

    @router.post("/imports/spreadsheet-rows", status_code=202)
    def import_spreadsheet_rows(
        request: SpreadsheetRowImportRequest,
    ) -> SpreadsheetRowImportResponse:
        if request.create_jobs:
            raise_if_usage_budget_blocks_submission()
        artifact_group_id = (
            new_artifact_group_id("spreadsheet-import")
            if request.create_jobs
            else DEFAULT_ARTIFACT_GROUP
        )
        parse_result = parse_spreadsheet_rows(request.rows)
        imported_case_ids: list[str] = []
        imported_rows: list[SpreadsheetImportedRowResponse] = []
        jobs: list[SubmittedDebugJob] = []
        for imported_row in parse_result.imported_rows:
            case = imported_row.case
            job_repository.save_case(case)
            imported_case_ids.append(case.case_id)
            imported_rows.append(
                SpreadsheetImportedRowResponse(
                    sheet_row_id=imported_row.sheet_row_id,
                    case_id=case.case_id,
                )
            )
            if request.create_jobs:
                jobs.append(
                    job_service.submit_case_debug(
                        case.case_id,
                        baseline_trials=request.baseline_trials,
                        artifact_group_id=artifact_group_id,
                    )
                )
        return SpreadsheetRowImportResponse(
            imported_case_ids=imported_case_ids,
            imported_rows=imported_rows,
            jobs=jobs,
            rejected_rows=parse_result.rejected_rows,
        )

    return router
