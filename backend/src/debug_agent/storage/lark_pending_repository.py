from __future__ import annotations

import json

from sqlalchemy import desc, func, select

from debug_agent.storage.models import (
    LarkBotPendingCommandRow,
    LarkBotSetupAcknowledgementRow,
    XiaoDCommandAuditRow,
    XiaoDExecutionRunRow,
    XiaoDPendingDecisionRow,
)
from debug_agent.storage.row_mappers import (
    _lark_bot_pending_command_from_row,
    _lark_bot_setup_acknowledgement_from_row,
    _utc_now_iso,
    _xiaod_command_audit_from_row,
    _xiaod_command_audit_row_for_command,
    _xiaod_execution_run_from_row,
    _xiaod_pending_decision_from_row,
)
from debug_agent.storage.schemas import (
    LarkBotPendingCommand,
    LarkBotSetupAcknowledgement,
    XiaoDCommandAudit,
    XiaoDExecutionRun,
    XiaoDPendingDecision,
)


XIAOD_TERMINAL_RUN_STATUSES = {"completed", "failed", "cancelled"}


class LarkPendingRepositoryMixin:
    def create_lark_bot_pending_command(
        self,
        *,
        command_id: str,
        actor: str,
        open_id: str,
        chat_id: str,
        message_id: str,
        tenant_key: str,
        identity: str,
        profile: str,
        command_text: str,
        action_kind: str,
        action: dict[str, object],
        card: dict[str, object],
        note: str,
        expires_at: str,
    ) -> LarkBotPendingCommand:
        with self._lock:
            with self._session_factory() as session:
                row = LarkBotPendingCommandRow(
                    command_id=command_id,
                    actor=actor,
                    open_id=open_id,
                    chat_id=chat_id,
                    message_id=message_id,
                    tenant_key=tenant_key,
                    identity=identity,
                    profile=profile,
                    command_text=command_text,
                    action_kind=action_kind,
                    action_json=json.dumps(action),
                    card_json=json.dumps(card),
                    status="pending",
                    note=note,
                    execution_result_json="{}",
                    error_message="",
                    created_at=_utc_now_iso(),
                    expires_at=expires_at,
                )
                session.add(row)
                session.commit()
                return _lark_bot_pending_command_from_row(row)

    def get_lark_bot_pending_command(self, command_id: str) -> LarkBotPendingCommand | None:
        with self._lock:
            with self._session_factory() as session:
                row = session.get(LarkBotPendingCommandRow, command_id)
                return _lark_bot_pending_command_from_row(row) if row is not None else None

    def list_lark_bot_pending_commands(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[LarkBotPendingCommand]:
        with self._lock:
            with self._session_factory() as session:
                query = select(LarkBotPendingCommandRow).order_by(
                    desc(LarkBotPendingCommandRow.created_at),
                    desc(LarkBotPendingCommandRow.command_id),
                )
                if status is not None:
                    query = query.where(LarkBotPendingCommandRow.status == status)
                if offset > 0:
                    query = query.offset(offset)
                query = query.limit(limit)
                return [_lark_bot_pending_command_from_row(row) for row in session.scalars(query)]

    def count_lark_bot_pending_commands(self, status: str | None = None) -> int:
        with self._lock:
            with self._session_factory() as session:
                query = select(func.count()).select_from(LarkBotPendingCommandRow)
                if status is not None:
                    query = query.where(LarkBotPendingCommandRow.status == status)
                return session.scalar(query) or 0

    def get_active_lark_bot_pending_command_for_user(
        self,
        *,
        tenant_key: str,
        chat_id: str,
        open_id: str,
        action_kind: str | None = None,
    ) -> LarkBotPendingCommand | None:
        with self._lock:
            with self._session_factory() as session:
                query = (
                    select(LarkBotPendingCommandRow)
                    .where(LarkBotPendingCommandRow.status == "pending")
                    .where(LarkBotPendingCommandRow.tenant_key == tenant_key)
                    .where(LarkBotPendingCommandRow.chat_id == chat_id)
                    .where(LarkBotPendingCommandRow.open_id == open_id)
                    .order_by(
                        desc(LarkBotPendingCommandRow.created_at),
                        desc(LarkBotPendingCommandRow.command_id),
                    )
                    .limit(1)
                )
                if action_kind is not None:
                    query = query.where(LarkBotPendingCommandRow.action_kind == action_kind)
                row = session.scalars(query).first()
                return _lark_bot_pending_command_from_row(row) if row is not None else None

    def list_active_lark_bot_pending_commands_for_user(
        self,
        *,
        tenant_key: str,
        chat_id: str,
        open_id: str,
        action_kind: str | None = None,
        limit: int = 50,
    ) -> list[LarkBotPendingCommand]:
        with self._lock:
            with self._session_factory() as session:
                query = (
                    select(LarkBotPendingCommandRow)
                    .where(LarkBotPendingCommandRow.status == "pending")
                    .where(LarkBotPendingCommandRow.tenant_key == tenant_key)
                    .where(LarkBotPendingCommandRow.chat_id == chat_id)
                    .where(LarkBotPendingCommandRow.open_id == open_id)
                    .order_by(
                        desc(LarkBotPendingCommandRow.created_at),
                        desc(LarkBotPendingCommandRow.command_id),
                    )
                    .limit(limit)
                )
                if action_kind is not None:
                    query = query.where(LarkBotPendingCommandRow.action_kind == action_kind)
                return [_lark_bot_pending_command_from_row(row) for row in session.scalars(query)]

    def create_xiaod_execution_run(
        self,
        *,
        run_id: str,
        tenant_key: str,
        chat_id: str,
        open_id: str,
        command_id: str = "",
        batch_id: str = "",
        job_id: str = "",
        action_kind: str = "",
        status: str = "active",
        summary: dict[str, object] | None = None,
    ) -> XiaoDExecutionRun:
        with self._lock:
            with self._session_factory() as session:
                now = _utc_now_iso()
                row = XiaoDExecutionRunRow(
                    run_id=run_id,
                    tenant_key=tenant_key,
                    chat_id=chat_id,
                    open_id=open_id,
                    command_id=command_id,
                    batch_id=batch_id,
                    job_id=job_id,
                    action_kind=action_kind,
                    status=status,
                    summary_json=json.dumps(summary or {}),
                    created_at=now,
                    updated_at=now,
                    completed_at=now if status in XIAOD_TERMINAL_RUN_STATUSES else "",
                )
                session.add(row)
                session.commit()
                return _xiaod_execution_run_from_row(row)

    def get_active_xiaod_execution_run(
        self,
        *,
        tenant_key: str,
        chat_id: str,
        open_id: str,
    ) -> XiaoDExecutionRun | None:
        with self._lock:
            with self._session_factory() as session:
                query = (
                    select(XiaoDExecutionRunRow)
                    .where(XiaoDExecutionRunRow.tenant_key == tenant_key)
                    .where(XiaoDExecutionRunRow.chat_id == chat_id)
                    .where(XiaoDExecutionRunRow.open_id == open_id)
                    .where(~XiaoDExecutionRunRow.status.in_(XIAOD_TERMINAL_RUN_STATUSES))
                    .order_by(
                        desc(XiaoDExecutionRunRow.updated_at),
                        desc(XiaoDExecutionRunRow.created_at),
                        desc(XiaoDExecutionRunRow.run_id),
                    )
                    .limit(1)
                )
                row = session.scalars(query).first()
                return _xiaod_execution_run_from_row(row) if row is not None else None

    def list_xiaod_execution_runs(
        self,
        *,
        status: str | None = None,
        active_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[XiaoDExecutionRun]:
        with self._lock:
            with self._session_factory() as session:
                query = select(XiaoDExecutionRunRow).order_by(
                    desc(XiaoDExecutionRunRow.updated_at),
                    desc(XiaoDExecutionRunRow.created_at),
                    desc(XiaoDExecutionRunRow.run_id),
                )
                if status is not None:
                    query = query.where(XiaoDExecutionRunRow.status == status)
                if active_only:
                    query = query.where(
                        ~XiaoDExecutionRunRow.status.in_(XIAOD_TERMINAL_RUN_STATUSES)
                    )
                if offset > 0:
                    query = query.offset(offset)
                query = query.limit(limit)
                return [_xiaod_execution_run_from_row(row) for row in session.scalars(query)]

    def complete_xiaod_execution_run(
        self,
        run_id: str,
        *,
        status: str = "completed",
        summary: dict[str, object] | None = None,
    ) -> XiaoDExecutionRun | None:
        with self._lock:
            with self._session_factory() as session:
                row = session.get(XiaoDExecutionRunRow, run_id)
                if row is None:
                    return None
                now = _utc_now_iso()
                row.status = status
                if summary is not None:
                    row.summary_json = json.dumps(summary)
                row.updated_at = now
                if status in XIAOD_TERMINAL_RUN_STATUSES:
                    row.completed_at = now
                session.commit()
                return _xiaod_execution_run_from_row(row)

    def create_xiaod_pending_decision(
        self,
        *,
        decision_id: str,
        tenant_key: str,
        chat_id: str,
        open_id: str,
        decision_kind: str,
        command_id: str = "",
        run_id: str = "",
        payload: dict[str, object] | None = None,
        note: str = "",
        expires_at: str = "",
    ) -> XiaoDPendingDecision:
        with self._lock:
            with self._session_factory() as session:
                row = XiaoDPendingDecisionRow(
                    decision_id=decision_id,
                    tenant_key=tenant_key,
                    chat_id=chat_id,
                    open_id=open_id,
                    decision_kind=decision_kind,
                    command_id=command_id,
                    run_id=run_id,
                    status="pending",
                    payload_json=json.dumps(payload or {}),
                    note=note,
                    created_at=_utc_now_iso(),
                    expires_at=expires_at,
                )
                session.add(row)
                session.commit()
                return _xiaod_pending_decision_from_row(row)

    def get_pending_xiaod_decision(
        self,
        *,
        tenant_key: str,
        chat_id: str,
        open_id: str,
        decision_kind: str | None = None,
    ) -> XiaoDPendingDecision | None:
        with self._lock:
            with self._session_factory() as session:
                query = (
                    select(XiaoDPendingDecisionRow)
                    .where(XiaoDPendingDecisionRow.status == "pending")
                    .where(XiaoDPendingDecisionRow.tenant_key == tenant_key)
                    .where(XiaoDPendingDecisionRow.chat_id == chat_id)
                    .where(XiaoDPendingDecisionRow.open_id == open_id)
                    .order_by(
                        desc(XiaoDPendingDecisionRow.created_at),
                        desc(XiaoDPendingDecisionRow.decision_id),
                    )
                    .limit(1)
                )
                if decision_kind is not None:
                    query = query.where(XiaoDPendingDecisionRow.decision_kind == decision_kind)
                row = session.scalars(query).first()
                return _xiaod_pending_decision_from_row(row) if row is not None else None

    def list_pending_xiaod_decisions(
        self,
        *,
        decision_kind: str | None = None,
        expires_before: str | None = None,
        limit: int = 50,
    ) -> list[XiaoDPendingDecision]:
        with self._lock:
            with self._session_factory() as session:
                query = (
                    select(XiaoDPendingDecisionRow)
                    .where(XiaoDPendingDecisionRow.status == "pending")
                    .order_by(
                        desc(XiaoDPendingDecisionRow.expires_at),
                        desc(XiaoDPendingDecisionRow.created_at),
                    )
                    .limit(limit)
                )
                if decision_kind is not None:
                    query = query.where(XiaoDPendingDecisionRow.decision_kind == decision_kind)
                if expires_before is not None:
                    query = query.where(XiaoDPendingDecisionRow.expires_at != "")
                    query = query.where(XiaoDPendingDecisionRow.expires_at <= expires_before)
                return [_xiaod_pending_decision_from_row(row) for row in session.scalars(query)]

    def resolve_xiaod_pending_decision(
        self,
        decision_id: str,
        *,
        status: str,
        actor: str,
        note: str = "",
        payload: dict[str, object] | None = None,
    ) -> XiaoDPendingDecision | None:
        with self._lock:
            with self._session_factory() as session:
                row = session.get(XiaoDPendingDecisionRow, decision_id)
                if row is None:
                    return None
                row.status = status
                row.resolved_by = actor
                row.resolved_at = _utc_now_iso()
                if note:
                    row.note = note
                if payload is not None:
                    row.payload_json = json.dumps(payload)
                session.commit()
                return _xiaod_pending_decision_from_row(row)

    def retain_lark_bot_pending_command(
        self,
        command_id: str,
        *,
        actor: str,
        note: str = "",
    ) -> LarkBotPendingCommand | None:
        with self._lock:
            with self._session_factory() as session:
                row = session.get(LarkBotPendingCommandRow, command_id)
                if row is None:
                    return None
                now = _utc_now_iso()
                row.status = "retained"
                row.confirmed_by = actor
                row.confirmed_at = now
                if note:
                    row.note = note
                session.add(
                    _xiaod_command_audit_row_for_command(
                        row,
                        event_kind="command_retained",
                        status="retained",
                        actor=actor,
                        reason=note,
                        created_at=now,
                    )
                )
                session.commit()
                return _lark_bot_pending_command_from_row(row)

    def delete_lark_bot_pending_command(
        self,
        command_id: str,
        *,
        actor: str,
        note: str = "",
        default_delete: bool = False,
    ) -> LarkBotPendingCommand | None:
        with self._lock:
            with self._session_factory() as session:
                row = session.get(LarkBotPendingCommandRow, command_id)
                if row is None:
                    return None
                now = _utc_now_iso()
                status = "default_deleted" if default_delete else "deleted"
                row.status = status
                row.confirmed_by = actor
                row.confirmed_at = now
                if note:
                    row.note = note
                session.add(
                    _xiaod_command_audit_row_for_command(
                        row,
                        event_kind=(
                            "command_default_deleted" if default_delete else "command_deleted"
                        ),
                        status=status,
                        actor=actor,
                        reason=note,
                        created_at=now,
                    )
                )
                session.commit()
                return _lark_bot_pending_command_from_row(row)

    def default_delete_lark_bot_pending_command(
        self,
        command_id: str,
        *,
        actor: str,
        note: str = "",
    ) -> LarkBotPendingCommand | None:
        return self.delete_lark_bot_pending_command(
            command_id,
            actor=actor,
            note=note,
            default_delete=True,
        )

    def list_xiaod_command_audits(
        self,
        *,
        command_id: str | None = None,
        tenant_key: str | None = None,
        chat_id: str | None = None,
        open_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[XiaoDCommandAudit]:
        with self._lock:
            with self._session_factory() as session:
                query = select(XiaoDCommandAuditRow).order_by(
                    desc(XiaoDCommandAuditRow.created_at),
                    desc(XiaoDCommandAuditRow.audit_id),
                )
                if command_id is not None:
                    query = query.where(XiaoDCommandAuditRow.command_id == command_id)
                if tenant_key is not None:
                    query = query.where(XiaoDCommandAuditRow.tenant_key == tenant_key)
                if chat_id is not None:
                    query = query.where(XiaoDCommandAuditRow.chat_id == chat_id)
                if open_id is not None:
                    query = query.where(XiaoDCommandAuditRow.open_id == open_id)
                if status is not None:
                    query = query.where(XiaoDCommandAuditRow.status == status)
                if offset > 0:
                    query = query.offset(offset)
                query = query.limit(limit)
                return [_xiaod_command_audit_from_row(row) for row in session.scalars(query)]

    def save_xiaod_command_audit(
        self,
        *,
        tenant_key: str = "",
        chat_id: str = "",
        open_id: str = "",
        command_id: str = "",
        run_id: str = "",
        decision_id: str = "",
        event_kind: str,
        status: str,
        actor: str,
        reason: str = "",
        payload: dict[str, object] | None = None,
    ) -> XiaoDCommandAudit:
        with self._lock:
            with self._session_factory() as session:
                row = XiaoDCommandAuditRow(
                    tenant_key=tenant_key,
                    chat_id=chat_id,
                    open_id=open_id,
                    command_id=command_id,
                    run_id=run_id,
                    decision_id=decision_id,
                    event_kind=event_kind,
                    status=status,
                    actor=actor,
                    reason=reason,
                    payload_json=json.dumps(payload or {}),
                    created_at=_utc_now_iso(),
                )
                session.add(row)
                session.commit()
                return _xiaod_command_audit_from_row(row)

    def confirm_lark_bot_pending_command(
        self,
        command_id: str,
        *,
        actor: str,
        note: str = "",
    ) -> LarkBotPendingCommand | None:
        with self._lock:
            with self._session_factory() as session:
                row = session.get(LarkBotPendingCommandRow, command_id)
                if row is None:
                    return None
                row.status = "confirmed"
                row.confirmed_by = actor
                row.confirmed_at = _utc_now_iso()
                if note:
                    row.note = note
                session.commit()
                return _lark_bot_pending_command_from_row(row)

    def cancel_lark_bot_pending_command(
        self,
        command_id: str,
        *,
        actor: str,
        note: str = "",
    ) -> LarkBotPendingCommand | None:
        with self._lock:
            with self._session_factory() as session:
                row = session.get(LarkBotPendingCommandRow, command_id)
                if row is None:
                    return None
                row.status = "cancelled"
                row.confirmed_by = actor
                row.confirmed_at = _utc_now_iso()
                if note:
                    row.note = note
                session.commit()
                return _lark_bot_pending_command_from_row(row)

    def complete_lark_bot_pending_command(
        self,
        command_id: str,
        *,
        status: str,
        execution_result: dict[str, object] | None = None,
        error_message: str = "",
    ) -> LarkBotPendingCommand | None:
        with self._lock:
            with self._session_factory() as session:
                row = session.get(LarkBotPendingCommandRow, command_id)
                if row is None:
                    return None
                row.status = status
                row.execution_result_json = json.dumps(execution_result or {})
                row.error_message = error_message
                row.executed_at = _utc_now_iso()
                session.commit()
                return _lark_bot_pending_command_from_row(row)

    def expire_lark_bot_pending_command(self, command_id: str) -> LarkBotPendingCommand | None:
        with self._lock:
            with self._session_factory() as session:
                row = session.get(LarkBotPendingCommandRow, command_id)
                if row is None:
                    return None
                row.status = "expired"
                session.commit()
                return _lark_bot_pending_command_from_row(row)

    def create_lark_bot_setup_acknowledgement(
        self,
        *,
        item_key: str,
        actor: str,
        evidence: str,
        note: str = "",
    ) -> LarkBotSetupAcknowledgement:
        with self._lock:
            with self._session_factory() as session:
                row = LarkBotSetupAcknowledgementRow(
                    item_key=item_key,
                    actor=actor,
                    evidence=evidence,
                    note=note,
                    created_at=_utc_now_iso(),
                )
                session.add(row)
                session.commit()
                return _lark_bot_setup_acknowledgement_from_row(row)

    def list_lark_bot_setup_acknowledgements(
        self,
        *,
        item_key: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[LarkBotSetupAcknowledgement]:
        with self._lock:
            with self._session_factory() as session:
                query = select(LarkBotSetupAcknowledgementRow).order_by(
                    desc(LarkBotSetupAcknowledgementRow.created_at),
                    desc(LarkBotSetupAcknowledgementRow.acknowledgement_id),
                )
                if item_key is not None:
                    query = query.where(LarkBotSetupAcknowledgementRow.item_key == item_key)
                if offset > 0:
                    query = query.offset(offset)
                query = query.limit(limit)
                return [
                    _lark_bot_setup_acknowledgement_from_row(row) for row in session.scalars(query)
                ]

    def latest_lark_bot_setup_acknowledgements(self) -> dict[str, LarkBotSetupAcknowledgement]:
        latest: dict[str, LarkBotSetupAcknowledgement] = {}
        for acknowledgement in self.list_lark_bot_setup_acknowledgements(limit=1_000):
            latest.setdefault(acknowledgement.item_key, acknowledgement)
        return latest
