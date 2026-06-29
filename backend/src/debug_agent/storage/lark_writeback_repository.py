from __future__ import annotations

import json

from sqlalchemy import desc, func, select

from debug_agent.storage.models import (
    LarkAuthSessionRow,
    LarkOperationAuditRow,
    LarkReportDocumentRow,
    LarkWriteConfirmationRow,
    SpreadsheetWritebackAuditRow,
)
from debug_agent.storage.row_mappers import (
    _lark_auth_session_from_row,
    _lark_operation_audit_from_row,
    _lark_report_document_from_row,
    _lark_write_confirmation_from_row,
    _spreadsheet_writeback_audit_from_row,
    _utc_now_iso,
)
from debug_agent.storage.schemas import (
    LarkAuthSession,
    LarkOperationAudit,
    LarkReportDocument,
    LarkWriteConfirmation,
    SpreadsheetWritebackAudit,
)


class LarkWritebackRepositoryMixin:
    def save_spreadsheet_writeback_audit(
        self,
        *,
        job_id: str,
        status: str,
        row_id: str,
        report_url: str,
        fields: dict[str, str],
        error_message: str,
    ) -> None:
        with self._lock:
            with self._session_factory() as session:
                now = _utc_now_iso()
                existing = session.get(SpreadsheetWritebackAuditRow, job_id)
                created_at = existing.created_at if existing is not None else now
                session.merge(
                    SpreadsheetWritebackAuditRow(
                        job_id=job_id,
                        status=status,
                        row_id=row_id,
                        report_url=report_url,
                        fields_json=json.dumps(fields, ensure_ascii=False),
                        error_message=error_message,
                        created_at=created_at,
                        updated_at=now,
                    )
                )
                session.commit()

    def get_spreadsheet_writeback_audit(self, job_id: str) -> SpreadsheetWritebackAudit | None:
        with self._lock:
            with self._session_factory() as session:
                row = session.get(SpreadsheetWritebackAuditRow, job_id)
                if row is None:
                    return None
                return _spreadsheet_writeback_audit_from_row(row)

    def save_lark_report_document(
        self,
        *,
        job_id: str,
        status: str,
        document_url: str,
        document_token: str,
        internal_report_url: str,
        error_message: str = "",
    ) -> LarkReportDocument:
        with self._lock:
            with self._session_factory() as session:
                now = _utc_now_iso()
                existing = session.get(LarkReportDocumentRow, job_id)
                created_at = existing.created_at if existing is not None else now
                row = LarkReportDocumentRow(
                    job_id=job_id,
                    status=status,
                    document_url=document_url,
                    document_token=document_token,
                    internal_report_url=internal_report_url,
                    error_message=error_message,
                    created_at=created_at,
                    updated_at=now,
                )
                session.merge(row)
                session.commit()
                return _lark_report_document_from_row(row)

    def get_lark_report_document(self, job_id: str) -> LarkReportDocument | None:
        with self._lock:
            with self._session_factory() as session:
                row = session.get(LarkReportDocumentRow, job_id)
                return _lark_report_document_from_row(row) if row is not None else None

    def count_spreadsheet_writeback_audits_by_status(self) -> dict[str, int]:
        with self._lock:
            with self._session_factory() as session:
                rows = session.execute(
                    select(SpreadsheetWritebackAuditRow.status, func.count())
                    .group_by(SpreadsheetWritebackAuditRow.status)
                    .order_by(SpreadsheetWritebackAuditRow.status)
                )
                return {str(status): int(count) for status, count in rows}

    def list_spreadsheet_writeback_audits(
        self,
        status: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[SpreadsheetWritebackAudit]:
        with self._lock:
            with self._session_factory() as session:
                query = select(SpreadsheetWritebackAuditRow).order_by(
                    desc(SpreadsheetWritebackAuditRow.updated_at),
                    desc(SpreadsheetWritebackAuditRow.job_id),
                )
                if status is not None:
                    query = query.where(SpreadsheetWritebackAuditRow.status == status)
                if offset > 0:
                    query = query.offset(offset)
                if limit is not None:
                    query = query.limit(limit)
                return [
                    _spreadsheet_writeback_audit_from_row(row) for row in session.scalars(query)
                ]

    def count_spreadsheet_writeback_audits(self, status: str | None = None) -> int:
        with self._lock:
            with self._session_factory() as session:
                query = select(func.count()).select_from(SpreadsheetWritebackAuditRow)
                if status is not None:
                    query = query.where(SpreadsheetWritebackAuditRow.status == status)
                return session.scalar(query) or 0

    def save_lark_operation_audit(
        self,
        *,
        actor: str,
        connector_mode: str,
        identity: str,
        profile: str,
        service: str,
        operation: str,
        status: str,
        context: str,
        error_type: str = "",
        hint: str = "",
        permission_scopes: list[str] | None = None,
        console_url: str = "",
        risk_action: str = "",
        duration_ms: int = 0,
    ) -> LarkOperationAudit:
        with self._lock:
            with self._session_factory() as session:
                row = LarkOperationAuditRow(
                    actor=actor,
                    connector_mode=connector_mode,
                    identity=identity,
                    profile=profile,
                    service=service,
                    operation=operation,
                    status=status,
                    context=context,
                    error_type=error_type,
                    hint=hint,
                    permission_scopes_json=json.dumps(permission_scopes or []),
                    console_url=console_url,
                    risk_action=risk_action,
                    duration_ms=max(0, duration_ms),
                    created_at=_utc_now_iso(),
                )
                session.add(row)
                session.commit()
                return _lark_operation_audit_from_row(row)

    def list_lark_operation_audits(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[LarkOperationAudit]:
        with self._lock:
            with self._session_factory() as session:
                query = select(LarkOperationAuditRow).order_by(
                    desc(LarkOperationAuditRow.created_at),
                    desc(LarkOperationAuditRow.audit_id),
                )
                if status is not None:
                    query = query.where(LarkOperationAuditRow.status == status)
                if offset > 0:
                    query = query.offset(offset)
                query = query.limit(limit)
                return [_lark_operation_audit_from_row(row) for row in session.scalars(query)]

    def count_lark_operation_audits(self, status: str | None = None) -> int:
        with self._lock:
            with self._session_factory() as session:
                query = select(func.count()).select_from(LarkOperationAuditRow)
                if status is not None:
                    query = query.where(LarkOperationAuditRow.status == status)
                return session.scalar(query) or 0

    def create_lark_write_confirmation(
        self,
        *,
        confirmation_id: str,
        actor: str,
        service: str,
        operation: str,
        resource_id: str,
        resource_summary: str,
        risk_action: str,
        required_scopes: list[str],
        note: str = "",
        expires_at: str,
    ) -> LarkWriteConfirmation:
        with self._lock:
            with self._session_factory() as session:
                row = LarkWriteConfirmationRow(
                    confirmation_id=confirmation_id,
                    actor=actor,
                    service=service,
                    operation=operation,
                    resource_id=resource_id,
                    resource_summary=resource_summary,
                    risk_action=risk_action,
                    required_scopes_json=json.dumps(required_scopes),
                    status="pending",
                    note=note,
                    created_at=_utc_now_iso(),
                    expires_at=expires_at,
                )
                session.add(row)
                session.commit()
                return _lark_write_confirmation_from_row(row)

    def get_lark_write_confirmation(self, confirmation_id: str) -> LarkWriteConfirmation | None:
        with self._lock:
            with self._session_factory() as session:
                row = session.get(LarkWriteConfirmationRow, confirmation_id)
                return _lark_write_confirmation_from_row(row) if row is not None else None

    def confirm_lark_write_confirmation(
        self,
        confirmation_id: str,
        *,
        actor: str,
        note: str = "",
    ) -> LarkWriteConfirmation | None:
        with self._lock:
            with self._session_factory() as session:
                row = session.get(LarkWriteConfirmationRow, confirmation_id)
                if row is None:
                    return None
                row.status = "confirmed"
                row.confirmed_by = actor
                row.confirmed_at = _utc_now_iso()
                if note:
                    row.note = note
                session.commit()
                return _lark_write_confirmation_from_row(row)

    def create_lark_auth_session(
        self,
        *,
        auth_session_id: str,
        actor: str,
        identity: str,
        profile: str,
        scopes: list[str],
        state: str,
        auth_url: str,
        redirect_url: str,
        note: str,
        expires_at: str,
    ) -> LarkAuthSession:
        with self._lock:
            with self._session_factory() as session:
                row = LarkAuthSessionRow(
                    auth_session_id=auth_session_id,
                    actor=actor,
                    identity=identity,
                    profile=profile,
                    scopes_json=json.dumps(scopes),
                    state=state,
                    auth_url=auth_url,
                    redirect_url=redirect_url,
                    status="pending",
                    note=note,
                    created_at=_utc_now_iso(),
                    expires_at=expires_at,
                )
                session.add(row)
                session.commit()
                return _lark_auth_session_from_row(row)

    def get_lark_auth_session(self, auth_session_id: str) -> LarkAuthSession | None:
        with self._lock:
            with self._session_factory() as session:
                row = session.get(LarkAuthSessionRow, auth_session_id)
                return _lark_auth_session_from_row(row) if row is not None else None

    def complete_lark_auth_session(
        self,
        auth_session_id: str,
        *,
        actor: str,
        note: str = "",
    ) -> LarkAuthSession | None:
        with self._lock:
            with self._session_factory() as session:
                row = session.get(LarkAuthSessionRow, auth_session_id)
                if row is None:
                    return None
                row.status = "authorized"
                row.completed_by = actor
                row.completed_at = _utc_now_iso()
                if note:
                    row.note = note
                session.commit()
                return _lark_auth_session_from_row(row)
