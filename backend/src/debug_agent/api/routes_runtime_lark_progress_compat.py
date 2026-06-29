from __future__ import annotations

# ruff: noqa: F821

from types import ModuleType

_RUNTIME: ModuleType | None = None
EXPORTED_NAMES: tuple[str, ...] = (
    "_published_or_internal_report_url",
    "list_lark_bot_badcase_completion_notifications",
    "list_lark_bot_notifications",
    "list_lark_bot_notification_outbox",
    "mark_lark_bot_notification_outbox_sent",
    "mark_lark_bot_notification_outbox_failed",
    "sweep_expired_xiaod_pending_decisions",
    "list_xiaod_run_progress_notifications",
    "list_lark_bot_badcase_progress_notifications",
    "mark_lark_bot_badcase_progress_notified",
    "_lark_bot_progress_state",
    "_lark_bot_progress_card",
    "_lark_progress_card_for_job",
    "_stable_lark_progress_idempotency_key",
    "_stable_lark_completion_idempotency_key",
    "_lark_bot_completion_notification_for_draft",
    "_internal_job_report_url",
    "_canonical_report_url_for_job",
    "_lark_bot_reply_target_type",
    "_http_exception_detail_text",
    "_lark_bot_completion_notification_ready",
    "_lark_bot_completion_card",
    "_roles_from_meta_agent_enrichment",
)


def bind_runtime(runtime: ModuleType) -> None:
    global _RUNTIME
    _RUNTIME = runtime
    for name, value in vars(runtime).items():
        if not name.startswith("__"):
            globals()[name] = value


def runtime_module() -> ModuleType:
    if _RUNTIME is None:
        raise RuntimeError("routes runtime helpers are not bound")
    return _RUNTIME


def _published_or_internal_report_url(job_id: str) -> str:
    document = job_repository.get_lark_report_document(job_id)
    if document is not None and document.status == "published" and document.document_url:
        return document.document_url
    return _internal_job_report_url(job_id)


def list_lark_bot_badcase_completion_notifications(
    limit: int = 20,
) -> LarkBotBadcaseDraftCompletionNotificationListResponse:
    notifications: list[LarkBotBadcaseDraftCompletionNotification] = []
    drafts = job_repository.list_lark_bot_badcase_drafts(status="submitted", limit=200)
    for draft in drafts:
        if len(notifications) >= limit:
            break
        if not draft.submitted_job_id:
            continue
        job = job_repository.get_job(draft.submitted_job_id)
        if job is None or job.status != "completed":
            continue
        if not _lark_bot_completion_notification_ready(job=job):
            continue
        notifications.append(_lark_bot_completion_notification_for_draft(draft=draft, job=job))
    return LarkBotBadcaseDraftCompletionNotificationListResponse(
        notifications=notifications,
        total_count=len(notifications),
    )


def list_lark_bot_notifications(limit: int = 20) -> LarkBotNotificationListResponse:
    return lark_notification_outbox_controller.list_notifications(limit=limit)


def list_lark_bot_notification_outbox(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> LarkBotNotificationOutboxListResponse:
    return lark_notification_outbox_controller.list_outbox(
        status=status,
        limit=limit,
        offset=offset,
    )


def mark_lark_bot_notification_outbox_sent(
    notification_id: str,
    request: LarkBotNotificationOutboxSentRequest,
):
    return lark_notification_outbox_controller.mark_sent(notification_id, request)


def mark_lark_bot_notification_outbox_failed(
    notification_id: str,
    request: LarkBotNotificationOutboxFailedRequest,
):
    return lark_notification_outbox_controller.mark_failed(notification_id, request)


def sweep_expired_xiaod_pending_decisions(limit: int = 50) -> dict[str, int]:
    return xiaod_pending_interaction_controller.sweep_expired_decisions(limit=limit)


def list_xiaod_run_progress_notifications(limit: int = 20) -> list[LarkBotNotificationEnvelope]:
    return xiaod_run_progress_notification_controller.list_notifications(limit=limit)


def list_lark_bot_badcase_progress_notifications(
    limit: int = 20,
) -> LarkBotBadcaseDraftProgressNotificationListResponse:
    return lark_progress_notification_controller.list_notifications(limit=limit)


def mark_lark_bot_badcase_progress_notified(
    draft_id: str,
    request: LarkBotBadcaseDraftProgressNotifiedRequest,
) -> LarkBotBadcaseDraft:
    return lark_progress_notification_controller.mark_notified(draft_id, request)


def _lark_bot_progress_state(*, job: DebugJobRow) -> dict[str, object] | None:
    return lark_progress_controller.progress_state(job=job)


def _lark_bot_progress_card(*, job: DebugJobRow, progress: dict[str, object]) -> dict[str, object]:
    return _lark_progress_card_for_job(
        job=job,
        progress=progress,
        title=str(progress["title"]),
    )


def _lark_progress_card_for_job(
    *,
    job: DebugJobRow,
    progress: dict[str, object],
    title: str,
) -> dict[str, object]:
    return lark_progress_controller.progress_card_for_job(
        job=job,
        progress=progress,
        title=title,
    )


def _stable_lark_progress_idempotency_key(progress_key: str) -> str:
    return lark_progress_controller.stable_progress_idempotency_key(progress_key)


def _stable_lark_completion_idempotency_key(*, draft_id: str, job_id: str) -> str:
    return lark_progress_controller.stable_completion_idempotency_key(
        draft_id=draft_id, job_id=job_id
    )


def _lark_bot_completion_notification_for_draft(
    *, draft: LarkBotBadcaseDraft, job: DebugJobRow
) -> LarkBotBadcaseDraftCompletionNotification:
    return lark_completion_delivery_controller.completion_notification_for_draft(
        draft=draft,
        job=job,
    )


def _internal_job_report_url(job_id: str) -> str:
    return lark_completion_delivery_controller.internal_job_report_url(job_id)


def _canonical_report_url_for_job(*, job: DebugJobRow, actor: str = "") -> str:
    return lark_completion_delivery_controller.canonical_report_url_for_job(
        job=job,
        actor=actor,
    )


def _lark_bot_reply_target_type(
    draft: LarkBotBadcaseDraft,
) -> Literal["message", "chat", "user", "none"]:
    if draft.message_id:
        return "message"
    if draft.chat_id:
        return "chat"
    if draft.open_id:
        return "user"
    return "none"


def _http_exception_detail_text(detail: object) -> str:
    if isinstance(detail, str):
        return detail
    try:
        return json.dumps(detail, ensure_ascii=False, separators=(",", ":"))
    except TypeError:
        return str(detail)


def _lark_bot_completion_notification_ready(*, job: DebugJobRow) -> bool:
    return lark_completion_delivery_controller.completion_notification_ready(job=job)


def _lark_bot_completion_card(
    *,
    draft: LarkBotBadcaseDraft,
    job: DebugJobRow,
    job_url: str,
    report_url: str,
    internal_report_url: str,
    report_document: object | None,
    markdown: str,
) -> dict[str, object]:
    return lark_completion_delivery_controller.completion_card(
        draft=draft,
        job=job,
        job_url=job_url,
        report_url=report_url,
        internal_report_url=internal_report_url,
        report_document=report_document,
        markdown=markdown,
    )


def _roles_from_meta_agent_enrichment(enrichment: dict[str, object]) -> list[str]:
    from debug_agent.api.lark_completion_delivery import _roles_from_meta_agent_enrichment

    return _roles_from_meta_agent_enrichment(enrichment)
