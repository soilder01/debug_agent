from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException

from debug_agent.api.writeback_routes import (
    BaseWritebackResult,
    JobReportBaseWritebackConfirmationRequest,
    JobReportBaseWritebackRequest,
    JobReportWritebackConfirmationRequest,
    JobReportWritebackRequest,
    LarkWriteConfirmationConfirmRequest,
)
from debug_agent.lark.connector import LarkCliConnector, lark_required_scopes
from debug_agent.reports.generator import DebugReport
from debug_agent.spreadsheets.lark import LarkCliError
from debug_agent.spreadsheets.writeback import (
    SpreadsheetWritebackClient,
    SpreadsheetWritebackResult,
    build_report_writeback_fields,
    write_report_to_spreadsheet_row,
)
from debug_agent.storage.repository import DebugJobRepository, LarkWriteConfirmation


class WritebackController:
    def __init__(
        self,
        *,
        job_repository: Callable[[], DebugJobRepository],
        configure_clients_from_request: Callable[[object], None],
        build_report: Callable[[str], DebugReport | None],
        spreadsheet_writeback_target: Callable[[str], tuple[str, str, str] | None],
        base_writeback_target: Callable[[str], tuple[str, str, str] | None],
        spreadsheet_writeback_client: Callable[[], SpreadsheetWritebackClient | None],
        resolved_actor: Callable[[str], str],
        base_write_connector: Callable[[str], LarkCliConnector],
        lark_bot_write_identity: Callable[[], str],
        lark_spreadsheet_error: Callable[[LarkCliError], HTTPException],
    ) -> None:
        self._job_repository = job_repository
        self._configure_clients_from_request = configure_clients_from_request
        self._build_report = build_report
        self._spreadsheet_writeback_target = spreadsheet_writeback_target
        self._base_writeback_target = base_writeback_target
        self._spreadsheet_writeback_client = spreadsheet_writeback_client
        self._resolved_actor = resolved_actor
        self._base_write_connector = base_write_connector
        self._lark_bot_write_identity = lark_bot_write_identity
        self._lark_spreadsheet_error = lark_spreadsheet_error

    def create_spreadsheet_confirmation(
        self,
        job_id: str,
        request: JobReportWritebackConfirmationRequest,
    ) -> LarkWriteConfirmation:
        self._configure_clients_from_request(request)
        repository = self._job_repository()
        if repository.get_job(job_id) is None:
            raise HTTPException(status_code=404, detail=f"Debug job not found: {job_id}")
        if self._build_report(job_id) is None:
            raise HTTPException(status_code=404, detail=f"Debug report not found for job: {job_id}")
        target = self._spreadsheet_writeback_target(job_id)
        if target is None:
            raise HTTPException(
                status_code=404, detail=f"Spreadsheet row mapping not found for job: {job_id}"
            )
        spreadsheet_id, sheet_id, row_id = target
        actor = self._resolved_actor(request.actor)
        resource_id = self.lark_write_resource_id(
            spreadsheet_id=spreadsheet_id,
            sheet_id=sheet_id,
            row_id=row_id,
            job_id=job_id,
        )
        return repository.create_lark_write_confirmation(
            confirmation_id=str(uuid4()),
            actor=actor,
            service="sheets",
            operation="+cells-set",
            resource_id=resource_id,
            resource_summary=f"写回任务 {job_id} 到表格 {spreadsheet_id}/{sheet_id} 行 {row_id}",
            risk_action="sheets +cells-set",
            required_scopes=lark_required_scopes("sheets", "+cells-set"),
            note=request.note,
            expires_at=(datetime.now(UTC) + timedelta(minutes=request.ttl_minutes)).isoformat(
                timespec="seconds"
            ),
        )

    def create_base_confirmation(
        self,
        job_id: str,
        request: JobReportBaseWritebackConfirmationRequest,
    ) -> LarkWriteConfirmation:
        repository = self._job_repository()
        if repository.get_job(job_id) is None:
            raise HTTPException(status_code=404, detail=f"Debug job not found: {job_id}")
        if self._build_report(job_id) is None:
            raise HTTPException(status_code=404, detail=f"Debug report not found for job: {job_id}")
        target = self._base_writeback_target(job_id)
        if target is None:
            raise HTTPException(
                status_code=404, detail=f"Base record mapping not found for job: {job_id}"
            )
        base_token, table_id, record_id = target
        actor = self._resolved_actor(request.actor)
        resource_id = self.base_write_resource_id(
            base_token=base_token,
            table_id=table_id,
            record_id=record_id,
            job_id=job_id,
        )
        return repository.create_lark_write_confirmation(
            confirmation_id=str(uuid4()),
            actor=actor,
            service="base",
            operation="+record-upsert",
            resource_id=resource_id,
            resource_summary=f"写回任务 {job_id} 到 Base {base_token}/{table_id} 记录 {record_id}",
            risk_action="base +record-upsert",
            required_scopes=lark_required_scopes("base", "+record-upsert"),
            note=request.note,
            expires_at=(datetime.now(UTC) + timedelta(minutes=request.ttl_minutes)).isoformat(
                timespec="seconds"
            ),
        )

    def confirm_lark_write(
        self,
        confirmation_id: str,
        request: LarkWriteConfirmationConfirmRequest,
    ) -> LarkWriteConfirmation:
        repository = self._job_repository()
        confirmation = repository.get_lark_write_confirmation(confirmation_id)
        if confirmation is None:
            raise HTTPException(
                status_code=404, detail=f"Lark write confirmation not found: {confirmation_id}"
            )
        if self.lark_write_confirmation_expired(confirmation):
            raise HTTPException(
                status_code=409,
                detail={
                    "type": "lark_write_confirmation_expired",
                    "confirmation_id": confirmation_id,
                    "expires_at": confirmation.expires_at,
                },
            )
        actor = self._resolved_actor(request.actor or confirmation.actor)
        confirmed = repository.confirm_lark_write_confirmation(
            confirmation_id, actor=actor, note=request.note
        )
        if confirmed is None:
            raise HTTPException(
                status_code=404, detail=f"Lark write confirmation not found: {confirmation_id}"
            )
        return confirmed

    def write_spreadsheet(
        self, job_id: str, request: JobReportWritebackRequest
    ) -> SpreadsheetWritebackResult:
        self._configure_clients_from_request(request)
        writeback_client = self._spreadsheet_writeback_client()
        if writeback_client is None:
            raise HTTPException(
                status_code=503, detail="Spreadsheet writeback client is not configured"
            )
        report = self._build_report(job_id)
        if report is None:
            raise HTTPException(status_code=404, detail=f"Debug report not found for job: {job_id}")
        target = self._spreadsheet_writeback_target(job_id)
        if target is None:
            raise HTTPException(
                status_code=404, detail=f"Spreadsheet row mapping not found for job: {job_id}"
            )
        spreadsheet_id, sheet_id, row_id = target
        repository = self._job_repository()
        existing_audit = repository.get_spreadsheet_writeback_audit(job_id)
        if (
            existing_audit is not None
            and existing_audit.status == "succeeded"
            and existing_audit.report_url == request.report_url
            and existing_audit.row_id == row_id
            and existing_audit.fields
        ):
            return SpreadsheetWritebackResult(
                row_id=existing_audit.row_id, fields=existing_audit.fields
            )
        if request.require_confirmation:
            self.raise_if_lark_write_confirmation_invalid(
                confirmation_id=request.confirmation_id,
                resource_id=self.lark_write_resource_id(
                    spreadsheet_id=spreadsheet_id,
                    sheet_id=sheet_id,
                    row_id=row_id,
                    job_id=job_id,
                ),
                service="sheets",
                operation="+cells-set",
            )
        try:
            result = write_report_to_spreadsheet_row(
                client=writeback_client,
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                row_id=row_id,
                report=report,
                report_url=request.report_url,
            )
        except LarkCliError as exc:
            repository.save_spreadsheet_writeback_audit(
                job_id=job_id,
                status="failed",
                row_id=row_id,
                report_url=request.report_url,
                fields={},
                error_message=str(exc),
            )
            raise self._lark_spreadsheet_error(exc) from exc
        repository.save_spreadsheet_writeback_audit(
            job_id=job_id,
            status="succeeded",
            row_id=result.row_id,
            report_url=request.report_url,
            fields=result.fields,
            error_message="",
        )
        return result

    def write_base(
        self, job_id: str, request: JobReportBaseWritebackRequest
    ) -> BaseWritebackResult:
        report = self._build_report(job_id)
        if report is None:
            raise HTTPException(status_code=404, detail=f"Debug report not found for job: {job_id}")
        target = self._base_writeback_target(job_id)
        if target is None:
            raise HTTPException(
                status_code=404, detail=f"Base record mapping not found for job: {job_id}"
            )
        base_token, table_id, record_id = target
        repository = self._job_repository()
        existing_audit = repository.get_spreadsheet_writeback_audit(job_id)
        if (
            existing_audit is not None
            and existing_audit.status == "succeeded"
            and existing_audit.report_url == request.report_url
            and existing_audit.row_id == record_id
            and existing_audit.fields
        ):
            return BaseWritebackResult(
                base_token=base_token,
                table_id=table_id,
                record_id=record_id,
                fields=existing_audit.fields,
            )
        if request.require_confirmation:
            self.raise_if_lark_write_confirmation_invalid(
                confirmation_id=request.confirmation_id,
                resource_id=self.base_write_resource_id(
                    base_token=base_token,
                    table_id=table_id,
                    record_id=record_id,
                    job_id=job_id,
                ),
                service="base",
                operation="+record-upsert",
            )
        fields = build_report_writeback_fields(report, report_url=request.report_url)
        actor = self._resolved_actor(request.actor)
        connector = self._base_write_connector(actor)
        try:
            result = connector.run_json(
                [
                    "base",
                    "+record-upsert",
                    "--base-token",
                    base_token,
                    "--table-id",
                    table_id,
                    "--record-id",
                    record_id,
                    "--json",
                    json.dumps(fields, ensure_ascii=False, separators=(",", ":")),
                    "--format",
                    "json",
                    "--as",
                    self._lark_bot_write_identity(),
                ]
            )
        except LarkCliError as exc:
            repository.save_spreadsheet_writeback_audit(
                job_id=job_id,
                status="failed",
                row_id=record_id,
                report_url=request.report_url,
                fields={},
                error_message=str(exc),
            )
            raise self._lark_spreadsheet_error(exc) from exc
        repository.save_spreadsheet_writeback_audit(
            job_id=job_id,
            status="succeeded",
            row_id=record_id,
            report_url=request.report_url,
            fields=fields,
            error_message="",
        )
        return BaseWritebackResult(
            base_token=base_token,
            table_id=table_id,
            record_id=record_id,
            fields=fields,
            result=result,
        )

    def lark_write_resource_id(
        self, *, spreadsheet_id: str, sheet_id: str, row_id: str, job_id: str
    ) -> str:
        return f"sheets:{spreadsheet_id}:{sheet_id}:{row_id}:job:{job_id}"

    def base_write_resource_id(
        self, *, base_token: str, table_id: str, record_id: str, job_id: str
    ) -> str:
        return f"base:{base_token}:{table_id}:{record_id}:job:{job_id}"

    def lark_write_confirmation_expired(self, confirmation: LarkWriteConfirmation) -> bool:
        if not confirmation.expires_at:
            return False
        try:
            expires_at = datetime.fromisoformat(confirmation.expires_at)
        except ValueError:
            return True
        return expires_at < datetime.now(UTC)

    def raise_if_lark_write_confirmation_invalid(
        self,
        *,
        confirmation_id: str,
        resource_id: str,
        service: str,
        operation: str,
    ) -> None:
        normalized_confirmation_id = confirmation_id.strip()
        if not normalized_confirmation_id:
            raise HTTPException(
                status_code=409,
                detail={
                    "type": "lark_write_confirmation_required",
                    "risk_action": f"{service} {operation}",
                    "resource_id": resource_id,
                },
            )
        confirmation = self._job_repository().get_lark_write_confirmation(
            normalized_confirmation_id
        )
        if confirmation is None:
            raise HTTPException(
                status_code=409,
                detail={
                    "type": "lark_write_confirmation_invalid",
                    "confirmation_id": normalized_confirmation_id,
                    "resource_id": resource_id,
                },
            )
        if (
            confirmation.service != service
            or confirmation.operation != operation
            or confirmation.resource_id != resource_id
        ):
            raise HTTPException(
                status_code=409,
                detail={
                    "type": "lark_write_confirmation_scope_mismatch",
                    "confirmation_id": normalized_confirmation_id,
                    "resource_id": resource_id,
                },
            )
        if confirmation.status != "confirmed":
            raise HTTPException(
                status_code=409,
                detail={
                    "type": "lark_write_confirmation_not_confirmed",
                    "confirmation_id": normalized_confirmation_id,
                    "status": confirmation.status,
                },
            )
        if self.lark_write_confirmation_expired(confirmation):
            raise HTTPException(
                status_code=409,
                detail={
                    "type": "lark_write_confirmation_expired",
                    "confirmation_id": normalized_confirmation_id,
                    "expires_at": confirmation.expires_at,
                },
            )
