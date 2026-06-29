from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter
from pydantic import BaseModel, Field

from debug_agent.spreadsheets.writeback import SpreadsheetWritebackResult
from debug_agent.storage.repository import LarkWriteConfirmation


class JobReportWritebackRequest(BaseModel):
    report_url: str
    spreadsheet_url: str = ""
    spreadsheet_id: str = ""
    sheet_id: str = ""
    require_confirmation: bool = False
    confirmation_id: str = ""
    actor: str = ""
    note: str = ""


class JobReportWritebackConfirmationRequest(BaseModel):
    report_url: str = ""
    spreadsheet_url: str = ""
    spreadsheet_id: str = ""
    sheet_id: str = ""
    actor: str = ""
    note: str = ""
    ttl_minutes: int = Field(default=30, ge=1, le=1440)


class JobReportBaseWritebackRequest(BaseModel):
    report_url: str
    require_confirmation: bool = False
    confirmation_id: str = ""
    actor: str = ""
    note: str = ""


class JobReportBaseWritebackConfirmationRequest(BaseModel):
    report_url: str = ""
    actor: str = ""
    note: str = ""
    ttl_minutes: int = Field(default=30, ge=1, le=1440)


class BaseWritebackResult(BaseModel):
    base_token: str
    table_id: str
    record_id: str
    fields: dict[str, str]
    result: dict[str, object] = Field(default_factory=dict)


class LarkWriteConfirmationConfirmRequest(BaseModel):
    actor: str = ""
    note: str = ""


def build_writeback_router(
    *,
    create_spreadsheet_confirmation: Callable[
        [str, JobReportWritebackConfirmationRequest], LarkWriteConfirmation
    ],
    create_base_confirmation: Callable[
        [str, JobReportBaseWritebackConfirmationRequest], LarkWriteConfirmation
    ],
    confirm_lark_write: Callable[
        [str, LarkWriteConfirmationConfirmRequest], LarkWriteConfirmation
    ],
    write_spreadsheet: Callable[[str, JobReportWritebackRequest], SpreadsheetWritebackResult],
    write_base: Callable[[str, JobReportBaseWritebackRequest], BaseWritebackResult],
) -> APIRouter:
    router = APIRouter()

    @router.post("/jobs/{job_id}/spreadsheet-writeback/confirmation")
    def create_job_report_writeback_confirmation(
        job_id: str,
        request: JobReportWritebackConfirmationRequest,
    ) -> LarkWriteConfirmation:
        return create_spreadsheet_confirmation(job_id, request)

    @router.post("/jobs/{job_id}/base-writeback/confirmation")
    @router.post("/api/jobs/{job_id}/base-writeback/confirmation")
    def create_job_report_base_writeback_confirmation(
        job_id: str,
        request: JobReportBaseWritebackConfirmationRequest,
    ) -> LarkWriteConfirmation:
        return create_base_confirmation(job_id, request)

    @router.post("/lark/write-confirmations/{confirmation_id}/confirm")
    @router.post("/api/lark/write-confirmations/{confirmation_id}/confirm")
    def confirm_lark_write_confirmation(
        confirmation_id: str,
        request: LarkWriteConfirmationConfirmRequest,
    ) -> LarkWriteConfirmation:
        return confirm_lark_write(confirmation_id, request)

    @router.post("/jobs/{job_id}/spreadsheet-writeback")
    def write_job_report_to_spreadsheet(
        job_id: str,
        request: JobReportWritebackRequest,
    ) -> SpreadsheetWritebackResult:
        return write_spreadsheet(job_id, request)

    @router.post("/jobs/{job_id}/base-writeback")
    @router.post("/api/jobs/{job_id}/base-writeback")
    def write_job_report_to_base_record(
        job_id: str,
        request: JobReportBaseWritebackRequest,
    ) -> BaseWritebackResult:
        return write_base(job_id, request)

    return router
