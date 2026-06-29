from __future__ import annotations

import json

from sqlalchemy import desc, select

from debug_agent.storage.models import (
    LarkBotBadcaseDraftRow,
    LarkNotificationOutboxRow,
)
from debug_agent.storage.row_mappers import (
    _json_string_list,
    _lark_bot_badcase_draft_from_row,
    _lark_notification_outbox_from_row,
    _outbox_envelope_json_with_state,
    _utc_now_iso,
)
from debug_agent.storage.schemas import (
    LarkBotBadcaseDraft,
    LarkNotificationOutbox,
)


class LarkBadcaseRepositoryMixin:
    def save_lark_bot_badcase_draft(
        self,
        *,
        draft_id: str,
        actor: str,
        open_id: str = "",
        chat_id: str = "",
        message_id: str = "",
        status: str = "collecting",
        source_text: str = "",
        input_source: str = "",
        model_output: str = "",
        expected_output: str = "",
        issue_summary: str = "",
        task_type: str = "generic_json",
        scoring_standard: str = "",
        attachments: list[dict[str, object]] | None = None,
        links: list[str] | None = None,
        missing_fields: list[str] | None = None,
        progress_notified_keys: list[str] | None = None,
        progress_panel_message_id: str | None = None,
        submitted_case_id: str = "",
        submitted_job_id: str = "",
        error_message: str = "",
    ) -> LarkBotBadcaseDraft:
        with self._lock:
            with self._session_factory() as session:
                now = _utc_now_iso()
                existing = session.get(LarkBotBadcaseDraftRow, draft_id)
                created_at = existing.created_at if existing is not None else now
                progress_keys_json = (
                    json.dumps(progress_notified_keys or [])
                    if progress_notified_keys is not None
                    else existing.progress_notified_keys_json
                    if existing is not None
                    else "[]"
                )
                panel_message_id = (
                    progress_panel_message_id
                    if progress_panel_message_id is not None
                    else existing.progress_panel_message_id
                    if existing is not None
                    else ""
                )
                row = LarkBotBadcaseDraftRow(
                    draft_id=draft_id,
                    actor=actor,
                    open_id=open_id,
                    chat_id=chat_id,
                    message_id=message_id,
                    status=status,
                    source_text=source_text,
                    input_source=input_source,
                    model_output=model_output,
                    expected_output=expected_output,
                    issue_summary=issue_summary,
                    task_type=task_type,
                    scoring_standard=scoring_standard,
                    attachments_json=json.dumps(attachments or []),
                    links_json=json.dumps(links or []),
                    missing_fields_json=json.dumps(missing_fields or []),
                    progress_notified_keys_json=progress_keys_json,
                    progress_panel_message_id=panel_message_id,
                    submitted_case_id=submitted_case_id,
                    submitted_job_id=submitted_job_id,
                    error_message=error_message,
                    created_at=created_at,
                    updated_at=now,
                )
                session.merge(row)
                session.commit()
                return _lark_bot_badcase_draft_from_row(row)

    def get_lark_bot_badcase_draft(self, draft_id: str) -> LarkBotBadcaseDraft | None:
        with self._lock:
            with self._session_factory() as session:
                row = session.get(LarkBotBadcaseDraftRow, draft_id)
                return _lark_bot_badcase_draft_from_row(row) if row is not None else None

    def latest_lark_bot_badcase_draft_for_chat(
        self,
        *,
        chat_id: str,
        open_id: str = "",
    ) -> LarkBotBadcaseDraft | None:
        with self._lock:
            with self._session_factory() as session:
                query = (
                    select(LarkBotBadcaseDraftRow)
                    .where(LarkBotBadcaseDraftRow.chat_id == chat_id)
                    .where(
                        LarkBotBadcaseDraftRow.status.in_(
                            ["collecting", "needs_more_info", "ready_for_confirmation"]
                        )
                    )
                    .order_by(
                        desc(LarkBotBadcaseDraftRow.updated_at),
                        desc(LarkBotBadcaseDraftRow.created_at),
                    )
                    .limit(1)
                )
                if open_id:
                    query = query.where(LarkBotBadcaseDraftRow.open_id == open_id)
                row = session.scalars(query).first()
                return _lark_bot_badcase_draft_from_row(row) if row is not None else None

    def list_lark_bot_badcase_drafts(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[LarkBotBadcaseDraft]:
        with self._lock:
            with self._session_factory() as session:
                query = select(LarkBotBadcaseDraftRow).order_by(
                    desc(LarkBotBadcaseDraftRow.updated_at),
                    desc(LarkBotBadcaseDraftRow.created_at),
                )
                if status is not None:
                    query = query.where(LarkBotBadcaseDraftRow.status == status)
                if offset > 0:
                    query = query.offset(offset)
                query = query.limit(limit)
                return [_lark_bot_badcase_draft_from_row(row) for row in session.scalars(query)]

    def mark_lark_bot_badcase_progress_notified(
        self,
        *,
        draft_id: str,
        progress_key: str,
        panel_message_id: str = "",
    ) -> LarkBotBadcaseDraft | None:
        with self._lock:
            with self._session_factory() as session:
                row = session.get(LarkBotBadcaseDraftRow, draft_id)
                if row is None:
                    return None
                progress_keys = _json_string_list(row.progress_notified_keys_json)
                changed = False
                if progress_key not in progress_keys:
                    progress_keys.append(progress_key)
                    row.progress_notified_keys_json = json.dumps(progress_keys)
                    changed = True
                if panel_message_id and row.progress_panel_message_id != panel_message_id:
                    row.progress_panel_message_id = panel_message_id
                    changed = True
                if changed:
                    row.updated_at = _utc_now_iso()
                    session.add(row)
                    session.commit()
                return _lark_bot_badcase_draft_from_row(row)

    def save_lark_notification_outbox(
        self,
        *,
        notification_id: str,
        kind: str,
        dedupe_key: str,
        draft_id: str,
        job_id: str,
        case_id: str,
        job_status: str,
        payload: dict[str, object],
        envelope: dict[str, object],
        progress_key: str = "",
        status: str = "pending",
    ) -> LarkNotificationOutbox:
        with self._lock:
            with self._session_factory() as session:
                now = _utc_now_iso()
                existing = session.get(LarkNotificationOutboxRow, notification_id)
                created_at = existing.created_at if existing is not None else now
                attempts = existing.attempts if existing is not None else 0
                last_error = existing.last_error if existing is not None else ""
                sent_at = existing.sent_at if existing is not None else ""
                final_status = existing.status if existing is not None else status
                if final_status == "pending":
                    final_status = status
                envelope_payload = dict(envelope)
                envelope_payload["delivery_state"] = final_status
                row = LarkNotificationOutboxRow(
                    notification_id=notification_id,
                    kind=kind,
                    dedupe_key=dedupe_key,
                    status=final_status,
                    draft_id=draft_id,
                    job_id=job_id,
                    case_id=case_id,
                    job_status=job_status,
                    progress_key=progress_key,
                    payload_json=json.dumps(payload),
                    envelope_json=json.dumps(envelope_payload),
                    attempts=attempts,
                    last_error=last_error,
                    created_at=created_at,
                    updated_at=now,
                    sent_at=sent_at,
                )
                session.merge(row)
                session.commit()
                return _lark_notification_outbox_from_row(row)

    def get_lark_notification_outbox(self, notification_id: str) -> LarkNotificationOutbox | None:
        with self._lock:
            with self._session_factory() as session:
                row = session.get(LarkNotificationOutboxRow, notification_id)
                return _lark_notification_outbox_from_row(row) if row is not None else None

    def list_lark_notification_outbox(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[LarkNotificationOutbox]:
        with self._lock:
            with self._session_factory() as session:
                query = select(LarkNotificationOutboxRow).order_by(
                    LarkNotificationOutboxRow.created_at,
                    LarkNotificationOutboxRow.notification_id,
                )
                if status is not None:
                    query = query.where(LarkNotificationOutboxRow.status == status)
                if offset > 0:
                    query = query.offset(offset)
                query = query.limit(limit)
                return [_lark_notification_outbox_from_row(row) for row in session.scalars(query)]

    def mark_lark_notification_outbox_sent(
        self,
        notification_id: str,
    ) -> LarkNotificationOutbox | None:
        with self._lock:
            with self._session_factory() as session:
                row = session.get(LarkNotificationOutboxRow, notification_id)
                if row is None:
                    return None
                now = _utc_now_iso()
                row.status = "sent"
                row.updated_at = now
                row.sent_at = now
                row.last_error = ""
                row.envelope_json = _outbox_envelope_json_with_state(row.envelope_json, "sent")
                session.commit()
                return _lark_notification_outbox_from_row(row)

    def mark_lark_notification_outbox_failed(
        self,
        notification_id: str,
        *,
        last_error: str,
        terminal: bool = False,
    ) -> LarkNotificationOutbox | None:
        with self._lock:
            with self._session_factory() as session:
                row = session.get(LarkNotificationOutboxRow, notification_id)
                if row is None:
                    return None
                row.attempts += 1
                row.status = "failed" if terminal else "pending"
                row.last_error = last_error
                row.updated_at = _utc_now_iso()
                row.envelope_json = _outbox_envelope_json_with_state(row.envelope_json, row.status)
                session.commit()
                return _lark_notification_outbox_from_row(row)
