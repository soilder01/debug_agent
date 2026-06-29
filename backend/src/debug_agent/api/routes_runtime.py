import asyncio
import hmac
import inspect
import json
import sys
import types
import threading

# ruff: noqa: F401, F821

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, cast
from urllib.parse import unquote, urlparse
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from debug_agent.assistant.chat import AssistantChatResponse, ProjectAssistant
from debug_agent.assistant.knowledge_base import default_knowledge_base
from debug_agent.artifacts.layout import (
    DEFAULT_ARTIFACT_GROUP,
    job_artifact_dir,
    safe_path_fragment,
)
from debug_agent.artifacts.store import artifact_store
from debug_agent.cases.models import AnswerSet, DebugCase, HumanNotes, Prediction
from debug_agent.experiments.runner import ExperimentEvidence
from debug_agent.imports.schema_mapping import (
    SpreadsheetSchemaMappingAgent,
)
from debug_agent.jobs.auto_closure import (
    AutoDebugClosureResult,
    LocalVideoClipper,
    run_auto_debug_closure,
)
from debug_agent.jobs.service import DebugJobService, SubmittedDebugJob
from debug_agent.jobs.worker import AsyncJobWorker
from debug_agent.lark.connector import (
    LARK_PERMISSION_CONSOLE_URL,
    LarkCliConnector,
    LarkConnectorAuditEvent,
    LarkConnectorStatus,
)
from debug_agent.lark.bot import (
    LarkBotCommandAction,
    LarkBotCommandRequest,
    LarkBotCommandResponse,
    LarkBotReplyPayload,
    build_lark_bot_command_response,
    lark_bot_idempotency_key,
    lark_bot_reply_cli_args,
)
from debug_agent.lark.xiaod_orchestrator import XiaoDTurnDecision
from debug_agent.xiaod.brain import XiaoDSemanticBrain
from debug_agent.api.artifact_routes import ArtifactRouteController, build_artifact_router
from debug_agent.api.assistant_routes import build_assistant_router
from debug_agent.api.auto_closure_report_controller import AutoClosureReportController
from debug_agent.api.badcase_intake_parsers import _input_source_requires_media_resolution
from debug_agent.api.case_routes import CaseRouteController, build_case_router
from debug_agent.api.debug_batch_routes import (
    DebugBatchViewBuilder,
    build_debug_batch_router,
    compare_debug_batches_view,
    get_debug_batch_view,
    list_debug_batches_view,
)
from debug_agent.api.debug_job_export import DebugJobExportController
from debug_agent.api.import_routes import build_import_router
from debug_agent.api.job_action_routes import JobActionRouteController, build_job_action_router
from debug_agent.api.job_read_routes import JobReadRouteController, build_job_read_router
from debug_agent.api.lark_bot_routes import (
    LarkBotBadcaseDraftCancelRequest,
    LarkBotBadcaseDraftCompletionFailedRequest,
    LarkBotBadcaseDraftCompletionNotification,
    LarkBotBadcaseDraftCompletionNotificationListResponse,
    LarkBotBadcaseDraftCompletionNotifiedRequest,
    LarkBotBadcaseDraftConfirmRequest,
    LarkBotBadcaseDraftConfirmResponse,
    LarkBotBadcaseDraftListResponse,
    LarkBotBadcaseDraftProgressNotificationListResponse,
    LarkBotBadcaseDraftProgressNotifiedRequest,
    LarkBotBadcaseDraftRequest,
    LarkBotNotificationEnvelope,
    LarkBotNotificationOutboxFailedRequest,
    LarkBotNotificationListResponse,
    LarkBotNotificationOutboxListResponse,
    LarkBotNotificationOutboxSentRequest,
    build_lark_bot_router,
)
from debug_agent.api.lark_bot_setup_routes import (
    LarkBotGoLiveGateResponse,
    LarkBotPermissionChecklistResponse,
    LarkBotPreflightResponse,
    LarkBotSetupAcknowledgementListResponse,
    LarkBotSetupAcknowledgementRequest,
    build_lark_bot_setup_router,
)
from debug_agent.api.lark_bot_setup_package import LarkBotSetupPackageBuilder
from debug_agent.api.lark_bot_setup_controller import LarkBotSetupController
from debug_agent.api.lark_bot_event_controller import LarkBotEventController
from debug_agent.api.lark_badcase_link_context import LarkBadcaseLinkContextResolver
from debug_agent.api.lark_badcase_draft_intake import LarkBadcaseDraftIntakeController
from debug_agent.api.lark_badcase_actions import LarkBadcaseActionController
from debug_agent.api.lark_badcase_rendering import LarkBadcaseRenderer, action_result_html
from debug_agent.api.lark_badcase_submission import LarkBadcaseSubmissionController
from debug_agent.api.lark_card_action_controller import LarkCardActionController
from debug_agent.api.lark_completion_delivery import LarkCompletionDeliveryController
from debug_agent.api.lark_notification_outbox import LarkNotificationOutboxController
from debug_agent.api.lark_pending_command_controller import LarkPendingCommandController
from debug_agent.api.lark_pending_command_reply import LarkPendingCommandReplyController
from debug_agent.api.lark_pending_command_lifecycle import LarkPendingCommandLifecycleController
from debug_agent.api.lark_progress_notifications import LarkProgressNotificationController
from debug_agent.api.lark_completion_rendering import (
    _lark_bot_completion_delivery_failure_message,
    _lark_bot_completion_delivery_failure_state,
)
from debug_agent.api.lark_pending_command_execution import (
    LarkPendingCommandExecutionController,
    action_bool as pending_command_action_bool,
    payload_dict as pending_command_payload_dict,
    payload_dict_list as pending_command_payload_dict_list,
    spreadsheet_rerun_preflight_from_action as pending_command_spreadsheet_rerun_preflight_from_action,
)
from debug_agent.api.lark_progress_controller import LarkProgressController
from debug_agent.api.model_routes import (
    _fetch_compatible_model_ids as _model_routes_fetch_compatible_model_ids,
    build_model_router,
    get_agent_model_catalog,
)
from debug_agent.api.observability_controller import ObservabilityController
from debug_agent.api.operations_routes import (
    ArtifactRetentionCleanupRequest,
    ArtifactRetentionCleanupResponse,
    ArtifactRetentionStatus,
    PilotGateResponse,
    ProductionReadinessResponse,
    build_operations_router,
)
from debug_agent.api.operations_export import OperationsExportController
from debug_agent.api.operations_status_controller import OperationsStatusController
from debug_agent.api.spreadsheet_routes import SpreadsheetRouteController, build_spreadsheet_router
from debug_agent.api.spreadsheet_rerun_preflight import SpreadsheetRerunPreflightController
from debug_agent.api.system_routes import build_system_router, get_performance_summary
from debug_agent.api.xiaod_turn_routes import (
    build_xiaod_turn_router,
)
from debug_agent.api.xiaod_spreadsheet_writeback_decision import (
    XiaoDSpreadsheetWritebackDecisionController,
)
from debug_agent.api.xiaod_action_summary import XiaoDActionSummaryReader
from debug_agent.api.xiaod_task_panel_controller import XiaoDTaskPanelController
from debug_agent.api.xiaod_run_progress_notifications import XiaoDRunProgressNotificationController
from debug_agent.api.xiaod_pending_interactions import XiaoDPendingInteractionController
from debug_agent.api.xiaod_turn_adapter import XiaoDTurnAdapterController
from debug_agent.api.xiaod_user_view_routes import build_xiaod_user_view_router
from debug_agent.api.schemas import (
    DebugJobStatus,
    DebugRunStageListResponse,
    EvidenceLedgerRecord,
    EvidenceLedgerResponse,
    SpreadsheetWritebackAuditSummary,
    DebugJobListResponse,
    RecommendedActionStatusRequest,
    RecommendedActionVerificationRequest,
    StrategyFollowUpJobRequest,
    TargetedProbeJobRequest,
    AutoDebugClosureRequest,
    AutoDebugClosureReportResponse,
    HumanHandoffStatusRequest,
    RecommendedActionVerificationResponse,
    StrategyFollowUpJobResponse,
    TargetedProbeJobResponse,
    StrategyFollowUpJobListResponse,
    TargetedProbeJobListResponse,
    HumanHandoffStatusListResponse,
    ActionQueueResponse,
    RecommendedActionStatusListResponse,
    SpreadsheetSyncRequest,
    SpreadsheetRerunRequest,
    SpreadsheetRerunAutoClosureReport,
    SpreadsheetRerunApiResult,
    WorkerRuntimeStatus,
    ObservabilityUsageSummary,
    ObservabilitySummaryResponse,
    DebugCaseListResponse,
)
from debug_agent.api.writeback_routes import (
    BaseWritebackResult,
    JobReportBaseWritebackConfirmationRequest,
    JobReportBaseWritebackRequest,
    JobReportWritebackConfirmationRequest,
    JobReportWritebackRequest,
    LarkWriteConfirmationConfirmRequest,
    build_writeback_router,
)
from debug_agent.api.writeback_controller import WritebackController
from debug_agent.models.config import (
    build_adapter_for_selection,
    default_agent_model_config,
)
from debug_agent.reports.generator import DebugReport
from debug_agent.reports.run_view import DebugRunView
from debug_agent.reports.job_report import (
    build_report_for_job,
    build_targeted_probe_results,
)
from debug_agent.settings import DebugAgentSettings, LarkSpreadsheetSettings
from debug_agent.spreadsheets.lark import (
    LarkCliError,
    LarkCliSheetsTransport,
    LarkSpreadsheetClient,
    parse_lark_spreadsheet_reference,
)
from debug_agent.spreadsheets.writeback import (
    SpreadsheetWritebackClient,
    SpreadsheetWritebackResult,
    make_spreadsheet_writeback_completion_hook,
)
from debug_agent.spreadsheets.sync import (
    SpreadsheetClient,
    SpreadsheetSourceRow,
    SpreadsheetSyncResult,
)
from debug_agent.storage.database import create_sqlite_session_factory, ensure_database_schema
from debug_agent.storage.models import DebugJobRow
from debug_agent.storage.repository import (
    DebugJobRepository,
    HumanHandoffStatus,
    RecommendedActionStatus,
    LarkBotBadcaseDraft,
    LarkBotPendingCommand,
    LarkBotSetupAcknowledgement,
    LarkWriteConfirmation,
    SpreadsheetWritebackAudit,
)

from debug_agent.api import routes_runtime_core_helpers as _runtime_core_helpers
from debug_agent.api import routes_runtime_job_helpers as _runtime_job_helpers
from debug_agent.api import routes_runtime_lark_badcase_compat as _runtime_lark_badcase_compat
from debug_agent.api import routes_runtime_lark_compat as _runtime_lark_compat
from debug_agent.api import routes_runtime_lark_pending_compat as _runtime_lark_pending_compat
from debug_agent.api import routes_runtime_lark_progress_compat as _runtime_lark_progress_compat
from debug_agent.api import routes_runtime_route_facades as _runtime_route_facades
from debug_agent.api import routes_runtime_assembly as _runtime_assembly
from debug_agent.api.routes_runtime_setup_catalog import (
    LARK_BOT_CARD_ACTION_EVENT_TYPE,
    LARK_BOT_LONG_CONNECTION_PROFILE,
    LARK_BOT_LONG_CONNECTION_RECEIVE_SCOPE,
    LARK_BOT_PERMISSION_CATALOG,
    LARK_BOT_PERMISSION_CHECKLIST_URL,
    LARK_BOT_RECEIVE_EVENT_TYPE,
    LARK_BOT_SETUP_ITEM_KEYS,
    LARK_BOT_SETUP_PACKAGE_URL,
    LarkBotPermissionPhase,
    LarkBotPermissionRisk,
    LarkBotPermissionType,
)

__all__ = ["AssistantChatResponse", "XiaoDTurnDecision"]

_RUNTIME_COMPAT_MODULES = (
    _runtime_assembly,
    _runtime_core_helpers,
    _runtime_lark_badcase_compat,
    _runtime_lark_pending_compat,
    _runtime_lark_progress_compat,
    _runtime_lark_compat,
    _runtime_route_facades,
    _runtime_job_helpers,
)


def _install_runtime_exports() -> None:
    for module in _RUNTIME_COMPAT_MODULES:
        for name in module.EXPORTED_NAMES:
            globals()[name] = getattr(module, name)


def _bind_runtime_compat_modules() -> None:
    runtime = sys.modules[__name__]
    for module in _RUNTIME_COMPAT_MODULES:
        module.bind_runtime(runtime)


_install_runtime_exports()

settings = DebugAgentSettings.from_env()
session_factory, engine = create_sqlite_session_factory(settings.database_url)
ensure_database_schema(engine)
job_repository = DebugJobRepository(session_factory)
job_service = DebugJobService(
    job_repository,
    max_attempts=settings.retry_max_attempts,
    image_artifact_dir=settings.image_artifact_dir,
    enable_fixture_fallback=settings.enable_fixture_fallback,
    meta_agent_budget_units=settings.usage_budget_units,
    auto_downgrade_meta_agents=settings.auto_downgrade_meta_agents,
)
case_route_controller = CaseRouteController(
    job_repository=job_repository,
    job_service=job_service,
    raise_if_usage_budget_blocks_submission=lambda: _raise_if_usage_budget_blocks_submission(),
    artifact_dir_for_job_id=lambda job_id: _artifact_dir_for_job_id(job_id),
)
debug_batch_view_builder = DebugBatchViewBuilder(
    job_repository=job_repository,
    build_job_status=lambda job: _build_job_status(job),
    usage_budget_units=settings.usage_budget_units,
)
spreadsheet_writeback_client: SpreadsheetWritebackClient | None = None
spreadsheet_sync_client: SpreadsheetClient | None = None
lark_spreadsheet_settings = LarkSpreadsheetSettings.from_env()


def configure_spreadsheet_clients(lark_settings: LarkSpreadsheetSettings | None = None) -> None:
    global lark_spreadsheet_settings, spreadsheet_sync_client, spreadsheet_writeback_client

    resolved_settings = lark_settings or LarkSpreadsheetSettings.from_env()
    lark_spreadsheet_settings = resolved_settings
    if resolved_settings.reference is None:
        spreadsheet_sync_client = None
        spreadsheet_writeback_client = None
        _bind_runtime_compat_modules()
        return

    lark_client = LarkSpreadsheetClient(
        LarkCliSheetsTransport(
            timeout_seconds=resolved_settings.lark_cli_timeout_seconds,
            profile=resolved_settings.lark_cli_profile,
            identity=resolved_settings.lark_cli_identity,
            audit_sink=_record_lark_connector_audit,
        )
    )
    spreadsheet_sync_client = lark_client
    spreadsheet_writeback_client = lark_client
    _bind_runtime_compat_modules()


_runtime_assembly.configure_runtime(sys.modules[__name__])
_bind_runtime_compat_modules()

router = APIRouter()
router.include_router(build_assistant_router(project_assistant))
router.include_router(
    build_model_router(
        fetch_compatible_model_ids=lambda **kwargs: _fetch_compatible_model_ids(**kwargs)
    )
)
router.include_router(build_system_router())


router.include_router(
    build_xiaod_turn_router(
        xiaod_turn_adapter.handle_turn,
        resolve_context=xiaod_turn_adapter.conversation_context,
        semantic_decider=xiaod_turn_adapter.semantic_decision,
    )
)


router.include_router(
    build_lark_bot_router(
        create_badcase_draft=create_lark_bot_badcase_draft,
        list_badcase_drafts=list_lark_bot_badcase_drafts,
        list_notifications=list_lark_bot_notifications,
        list_notification_outbox=list_lark_bot_notification_outbox,
        mark_notification_outbox_sent=mark_lark_bot_notification_outbox_sent,
        mark_notification_outbox_failed=mark_lark_bot_notification_outbox_failed,
        list_completion_notifications=list_lark_bot_badcase_completion_notifications,
        list_progress_notifications=list_lark_bot_badcase_progress_notifications,
        mark_progress_notified=mark_lark_bot_badcase_progress_notified,
        get_badcase_draft=get_lark_bot_badcase_draft,
        preview_confirmation_card=preview_lark_bot_badcase_confirmation_card,
        preview_confirm_link=preview_lark_bot_badcase_confirm_link,
        submit_confirm_link=submit_lark_bot_badcase_confirm_link,
        preview_writeback_link=preview_lark_bot_badcase_writeback_link,
        submit_writeback_link=submit_lark_bot_badcase_writeback_link,
        preview_base_writeback_link=preview_lark_bot_badcase_base_writeback_link,
        submit_base_writeback_link=submit_lark_bot_badcase_base_writeback_link,
        mark_completion_notified=mark_lark_bot_badcase_completion_notified,
        mark_completion_delivery_failed=mark_lark_bot_badcase_completion_delivery_failed,
        cancel_badcase_draft=cancel_lark_bot_badcase_draft,
        confirm_badcase_draft=confirm_lark_bot_badcase_draft,
        preview_command=lambda request: _preview_lark_bot_command(request),
        create_pending_command=pending_command_controller.create,
        list_pending_commands=lambda status, limit, offset: (
            pending_command_controller.list_commands(
                status=status,
                limit=limit,
                offset=offset,
            )
        ),
        get_pending_command=pending_command_controller.get,
        preview_pending_command_reply=pending_command_reply_controller.preview,
        send_pending_command_reply=pending_command_reply_controller.send,
        confirm_pending_command=pending_command_lifecycle_controller.confirm,
        cancel_pending_command=pending_command_lifecycle_controller.cancel,
        retain_pending_command=pending_command_lifecycle_controller.retain,
        delete_pending_command=pending_command_lifecycle_controller.delete,
        default_delete_pending_command=pending_command_lifecycle_controller.default_delete,
        handle_event=handle_lark_bot_event,
    )
)


@router.get("/observability/summary")
def get_observability_summary() -> ObservabilitySummaryResponse:
    return observability_controller.get_summary()


router.include_router(build_case_router(case_route_controller))


router.include_router(
    build_debug_batch_router(
        job_repository=job_repository,
        job_service=job_service,
        view_builder=debug_batch_view_builder,
        raise_if_usage_budget_blocks_submission=lambda: _raise_if_usage_budget_blocks_submission(),
        new_artifact_group_id=lambda prefix: _new_artifact_group_id(prefix),
    )
)


router.include_router(
    build_import_router(
        job_repository=job_repository,
        job_service=job_service,
        raise_if_usage_budget_blocks_submission=lambda: _raise_if_usage_budget_blocks_submission(),
        new_artifact_group_id=lambda prefix: _new_artifact_group_id(prefix),
    )
)


router.include_router(build_spreadsheet_router(spreadsheet_route_controller))


router.include_router(
    build_lark_bot_setup_router(
        permission_checklist=lark_bot_setup_controller.get_permission_checklist,
        preflight=lark_bot_setup_controller.get_preflight,
        go_live_gate=lark_bot_setup_controller.get_go_live_gate,
        setup_acknowledgements=lark_bot_setup_controller.list_setup_acknowledgements,
        acknowledge_setup_item=lark_bot_setup_controller.acknowledge_setup_item,
        setup_package=lark_bot_setup_package_builder.export_package,
    )
)


router.include_router(
    build_operations_router(
        readiness=operations_status_controller.get_readiness,
        artifact_retention=lambda limit: artifact_route_controller.build_retention_status(
            limit=limit
        ),
        cleanup_artifact_retention=artifact_route_controller.cleanup_retention,
        pilot_gate=get_pilot_gate,
        export_debug_jobs=export_debug_jobs,
        export_support_bundle=lambda audit_limit: (
            operations_export_controller.export_support_bundle(audit_limit=audit_limit)
        ),
        export_database_backup=operations_export_controller.export_database_backup,
    )
)


router.include_router(build_job_read_router(job_read_route_controller))
router.include_router(build_job_action_router(job_action_route_controller))
router.include_router(build_artifact_router(artifact_route_controller))
router.include_router(
    build_xiaod_user_view_router(
        job_repository=job_repository,
        build_job_status=lambda job: _build_job_status(job),
        build_batch_progress=lambda batch_id: debug_batch_view_builder.build_progress(batch_id),
        build_report=lambda job_id: build_report_for_job(job_repository, job_id),
        report_base_url=lambda: settings.report_base_url,
    )
)


router.include_router(
    build_writeback_router(
        create_spreadsheet_confirmation=writeback_controller.create_spreadsheet_confirmation,
        create_base_confirmation=writeback_controller.create_base_confirmation,
        confirm_lark_write=writeback_controller.confirm_lark_write,
        write_spreadsheet=writeback_controller.write_spreadsheet,
        write_base=writeback_controller.write_base,
    )
)


@router.get("/cases/{case_id}/evidence/{evidence_id:path}")
def get_evidence(case_id: str, evidence_id: str) -> ExperimentEvidence:
    evidence = artifact_store.get_evidence(case_id, evidence_id)
    if evidence is None:
        raise HTTPException(status_code=404, detail=f"Evidence not found: {evidence_id}")
    return evidence


class _RoutesRuntimeModule(types.ModuleType):
    def __setattr__(self, name: str, value: object) -> None:
        types.ModuleType.__setattr__(self, name, value)
        if name.startswith("__"):
            return
        for module in _RUNTIME_COMPAT_MODULES:
            setattr(module, name, value)

    def __delattr__(self, name: str) -> None:
        types.ModuleType.__delattr__(self, name)
        if name.startswith("__"):
            return
        for module in _RUNTIME_COMPAT_MODULES:
            if hasattr(module, name):
                delattr(module, name)


_bind_runtime_compat_modules()
sys.modules[__name__].__class__ = _RoutesRuntimeModule
