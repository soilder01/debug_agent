from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Literal
from urllib.parse import urlencode
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query

from debug_agent.api.debug_batch_routes import DebugBatchViewBuilder
from debug_agent.api.schemas import (
    LarkAuthSessionCompleteRequest,
    LarkAuthSessionRequest,
    LarkOperationAuditListResponse,
    LarkScopeCheckResponse,
    LarkScopeRequirementStatus,
    LarkSpreadsheetStatusResponse,
    SpreadsheetImportedRowResponse,
    SpreadsheetRerunApiResult,
    SpreadsheetRerunAutoClosureReport,
    SpreadsheetRerunRequest,
    SpreadsheetSyncRequest,
    SpreadsheetWritebackAuditListResponse,
    SpreadsheetWritebackAuditSummaryResponse,
)
from debug_agent.jobs.service import DebugJobService
from debug_agent.jobs.spreadsheet_rerun import rerun_spreadsheet_rows
from debug_agent.lark.connector import (
    LARK_PERMISSION_CONSOLE_URL,
    LarkConnectorStatus,
    LarkScopeRequirement,
    lark_scope_requirements,
)
from debug_agent.models.config import default_agent_model_config
from debug_agent.settings import LarkSpreadsheetSettings
from debug_agent.spreadsheets.lark import LarkCliError
from debug_agent.spreadsheets.sync import (
    SpreadsheetClient,
    SpreadsheetSourceRow,
    SpreadsheetSyncResult,
    sync_spreadsheet_rows,
)
from debug_agent.storage.repository import (
    DebugJobRepository,
    LarkAuthSession,
    LarkOperationAudit,
)
from debug_agent.telemetry.performance import measure_performance


class SpreadsheetRouteController:
    def __init__(
        self,
        *,
        job_repository: DebugJobRepository,
        job_service: DebugJobService,
        spreadsheet_settings: Callable[[], LarkSpreadsheetSettings],
        spreadsheet_sync_client: Callable[[], SpreadsheetClient | None],
        configure_clients_from_request: Callable[[object], None],
        spreadsheet_settings_from_request: Callable[..., LarkSpreadsheetSettings | None],
        lark_client_for_settings: Callable[
            [LarkSpreadsheetSettings | None], SpreadsheetClient | None
        ],
        lark_connector_status_for_client: Callable[[SpreadsheetClient | None], LarkConnectorStatus],
        lark_spreadsheet_error: Callable[[LarkCliError], HTTPException],
        resolved_actor: Callable[[str], str],
        raise_if_usage_budget_blocks_submission: Callable[[], None],
        spreadsheet_rerun_row_media_resolver: Callable[
            [SpreadsheetRerunRequest], Callable[[SpreadsheetSourceRow], SpreadsheetSourceRow] | None
        ],
        run_spreadsheet_rerun_auto_closures: Callable[
            ..., Awaitable[list[SpreadsheetRerunAutoClosureReport]]
        ],
        debug_batch_view_builder: DebugBatchViewBuilder,
    ) -> None:
        self._job_repository = job_repository
        self._job_service = job_service
        self._spreadsheet_settings = spreadsheet_settings
        self._spreadsheet_sync_client = spreadsheet_sync_client
        self._configure_clients_from_request = configure_clients_from_request
        self._spreadsheet_settings_from_request = spreadsheet_settings_from_request
        self._lark_client_for_settings = lark_client_for_settings
        self._lark_connector_status_for_client = lark_connector_status_for_client
        self._lark_spreadsheet_error = lark_spreadsheet_error
        self._resolved_actor = resolved_actor
        self._raise_if_usage_budget_blocks_submission = raise_if_usage_budget_blocks_submission
        self._spreadsheet_rerun_row_media_resolver = spreadsheet_rerun_row_media_resolver
        self._run_spreadsheet_rerun_auto_closures = run_spreadsheet_rerun_auto_closures
        self._debug_batch_view_builder = debug_batch_view_builder

    def get_lark_spreadsheet_status(
        self,
        *,
        check_connectivity: bool,
        spreadsheet_url: str,
        spreadsheet_id: str,
        sheet_id: str,
    ) -> LarkSpreadsheetStatusResponse:
        current_settings = self._spreadsheet_settings()
        request_settings = self._spreadsheet_settings_from_request(
            spreadsheet_url=spreadsheet_url,
            spreadsheet_id=spreadsheet_id,
            sheet_id=sheet_id,
        )
        reference = (
            request_settings.reference
            if request_settings is not None
            else current_settings.reference
        )
        status_client = (
            self._lark_client_for_settings(request_settings)
            if request_settings is not None
            else self._spreadsheet_sync_client()
        )
        timeout_seconds = (
            request_settings.lark_cli_timeout_seconds
            if request_settings is not None
            else current_settings.lark_cli_timeout_seconds
        )
        connector_status = self._lark_connector_status_for_client(status_client)
        if reference is None:
            return LarkSpreadsheetStatusResponse(
                configured=False,
                spreadsheet_id="",
                sheet_id="",
                lark_cli_timeout_seconds=timeout_seconds,
                connector_mode=connector_status.mode,
                connector_identity=connector_status.identity,
                connector_profile=connector_status.profile,
                connector_auth_status=connector_status.auth_status,
                connector_token_status=connector_status.token_status,
            )

        connectivity_status: Literal["not_checked", "ok", "failed"] = "not_checked"
        error_message = ""
        error_type = ""
        permission_scopes: list[str] = []
        console_url = ""
        risk_action = ""
        if check_connectivity:
            if status_client is None:
                connectivity_status = "failed"
                error_message = "Spreadsheet sync client is not configured"
                error_type = "client_not_configured"
            else:
                try:
                    status_client.list_rows(
                        spreadsheet_id=reference.spreadsheet_id,
                        sheet_id=reference.sheet_id,
                    )
                    connectivity_status = "ok"
                except LarkCliError as exc:
                    connectivity_status = "failed"
                    error_message = str(exc)
                    error_type = exc.error_type
                    permission_scopes = exc.permission_scopes
                    console_url = exc.console_url
                    risk_action = exc.risk_action
                except OSError as exc:
                    connectivity_status = "failed"
                    error_message = str(exc)
                    error_type = type(exc).__name__

        return LarkSpreadsheetStatusResponse(
            configured=True,
            spreadsheet_id=reference.spreadsheet_id,
            sheet_id=reference.sheet_id,
            lark_cli_timeout_seconds=timeout_seconds,
            connector_mode=connector_status.mode,
            connector_identity=connector_status.identity,
            connector_profile=connector_status.profile,
            connector_auth_status=connector_status.auth_status,
            connector_token_status=connector_status.token_status,
            connectivity_status=connectivity_status,
            error_message=error_message,
            error_type=error_type,
            permission_scopes=permission_scopes,
            console_url=console_url,
            risk_action=risk_action,
        )

    def list_lark_operation_audits(
        self,
        *,
        status: str | None,
        limit: int,
        offset: int,
    ) -> LarkOperationAuditListResponse:
        return LarkOperationAuditListResponse(
            audits=self._job_repository.list_lark_operation_audits(
                status=status, limit=limit, offset=offset
            ),
            total_count=self._job_repository.count_lark_operation_audits(status=status),
        )

    def check_lark_scopes(
        self,
        *,
        service: str,
        operation: str,
        recent_limit: int,
    ) -> LarkScopeCheckResponse:
        requirements = lark_scope_requirements(service=service, operation=operation)
        recent_failures = self._job_repository.list_lark_operation_audits(
            status="failed", limit=recent_limit, offset=0
        )
        connector_status = self._lark_connector_status_for_client(self._spreadsheet_sync_client())
        return LarkScopeCheckResponse(
            connector_mode=connector_status.mode,
            connector_identity=connector_status.identity,
            connector_profile=connector_status.profile,
            requirements=[
                _scope_requirement_status(requirement=requirement, recent_failures=recent_failures)
                for requirement in requirements
            ],
            recent_missing_scopes=_recent_missing_scopes(recent_failures),
            repair_steps=_lark_scope_repair_steps(
                requirements=requirements, recent_failures=recent_failures
            ),
        )

    def create_lark_auth_session(self, request: LarkAuthSessionRequest) -> LarkAuthSession:
        actor = self._resolved_actor(request.actor)
        scopes = _lark_auth_session_scopes(request.scopes)
        state = str(uuid4())
        profile = request.profile.strip() or self._spreadsheet_settings().lark_cli_profile
        redirect_url = request.redirect_url.strip()
        return self._job_repository.create_lark_auth_session(
            auth_session_id=str(uuid4()),
            actor=actor,
            identity=request.identity,
            profile=profile,
            scopes=scopes,
            state=state,
            auth_url=_lark_auth_url(
                identity=request.identity,
                profile=profile,
                scopes=scopes,
                state=state,
                redirect_url=redirect_url,
            ),
            redirect_url=redirect_url,
            note=request.note,
            expires_at=(datetime.now(UTC) + timedelta(minutes=request.ttl_minutes)).isoformat(
                timespec="seconds"
            ),
        )

    def get_lark_auth_session(self, auth_session_id: str) -> LarkAuthSession:
        auth_session = self._job_repository.get_lark_auth_session(auth_session_id)
        if auth_session is None:
            raise HTTPException(
                status_code=404, detail=f"Lark auth session not found: {auth_session_id}"
            )
        return auth_session

    def complete_lark_auth_session(
        self,
        auth_session_id: str,
        request: LarkAuthSessionCompleteRequest,
    ) -> LarkAuthSession:
        auth_session = self._job_repository.get_lark_auth_session(auth_session_id)
        if auth_session is None:
            raise HTTPException(
                status_code=404, detail=f"Lark auth session not found: {auth_session_id}"
            )
        if _lark_auth_session_expired(auth_session):
            raise HTTPException(
                status_code=409,
                detail={
                    "type": "lark_auth_session_expired",
                    "auth_session_id": auth_session_id,
                    "expires_at": auth_session.expires_at,
                },
            )
        actor = self._resolved_actor(request.actor or auth_session.actor)
        completed = self._job_repository.complete_lark_auth_session(
            auth_session_id, actor=actor, note=request.note
        )
        if completed is None:
            raise HTTPException(
                status_code=404, detail=f"Lark auth session not found: {auth_session_id}"
            )
        return completed

    def sync_spreadsheet(self, request: SpreadsheetSyncRequest) -> SpreadsheetSyncResult:
        self._configure_clients_from_request(request)
        spreadsheet_sync_client = self._spreadsheet_sync_client()
        if spreadsheet_sync_client is None:
            raise HTTPException(status_code=503, detail="Spreadsheet sync client is not configured")
        if request.create_jobs:
            self._raise_if_usage_budget_blocks_submission()
        try:
            with measure_performance(
                component="spreadsheet",
                operation="sync_rows",
                metadata={"spreadsheet_id": request.spreadsheet_id, "sheet_id": request.sheet_id},
            ):
                return sync_spreadsheet_rows(
                    client=spreadsheet_sync_client,
                    spreadsheet_id=request.spreadsheet_id,
                    sheet_id=request.sheet_id,
                    repository=self._job_repository,
                    job_service=self._job_service,
                    create_jobs=request.create_jobs,
                    baseline_trials=request.baseline_trials,
                )
        except LarkCliError as exc:
            raise self._lark_spreadsheet_error(exc) from exc
        except OSError as exc:
            raise HTTPException(
                status_code=502, detail=f"Lark spreadsheet operation failed: {exc}"
            ) from exc

    async def rerun_spreadsheet(
        self, request: SpreadsheetRerunRequest
    ) -> SpreadsheetRerunApiResult:
        self._configure_clients_from_request(request)
        spreadsheet_sync_client = self._spreadsheet_sync_client()
        if spreadsheet_sync_client is None:
            raise HTTPException(status_code=503, detail="Spreadsheet sync client is not configured")
        if request.auto_run:
            self._raise_if_usage_budget_blocks_submission()
        try:
            with measure_performance(
                component="spreadsheet",
                operation="rerun_rows",
                metadata={
                    "spreadsheet_id": request.spreadsheet_id,
                    "sheet_id": request.sheet_id,
                    "requested_row_count": len(request.row_ids),
                    "requested_case_count": len(request.case_ids),
                    "auto_run": request.auto_run,
                },
            ):
                result = await rerun_spreadsheet_rows(
                    client=spreadsheet_sync_client,
                    spreadsheet_id=request.spreadsheet_id,
                    sheet_id=request.sheet_id,
                    repository=self._job_repository,
                    job_service=self._job_service,
                    row_ids=request.row_ids,
                    case_ids=request.case_ids,
                    baseline_trials=request.baseline_trials,
                    auto_run=request.auto_run,
                    artifact_group_id=request.artifact_group_id,
                    row_media_resolver=self._spreadsheet_rerun_row_media_resolver(request),
                    retry_policy={
                        "source": "spreadsheet_rerun",
                        "row_ids": request.row_ids,
                        "case_ids": request.case_ids,
                        "queue_priority": request.queue_priority,
                        "baseline_trials": request.baseline_trials,
                        "auto_run": request.auto_run,
                        "auto_closure": request.auto_closure,
                        "submit_controlled_probes": request.submit_controlled_probes,
                        "writeback": request.writeback,
                        "agent_model_config": default_agent_model_config().model_dump(),
                    },
                )
            auto_closure_reports = (
                await self._run_spreadsheet_rerun_auto_closures(
                    jobs=result.jobs,
                    writeback_requested=request.writeback,
                    submit_controlled_probes=request.submit_controlled_probes,
                )
                if request.auto_closure
                else []
            )
            return SpreadsheetRerunApiResult(
                imported_case_ids=result.imported_case_ids,
                imported_rows=[
                    SpreadsheetImportedRowResponse(
                        sheet_row_id=imported_row.sheet_row_id,
                        case_id=imported_row.case.case_id,
                    )
                    for imported_row in result.imported_rows
                ],
                rejected_rows=result.rejected_rows,
                skipped_row_ids=result.skipped_row_ids,
                jobs=result.jobs,
                batch=self._debug_batch_view_builder.build_progress(
                    result.jobs[0].artifact_group_id
                )
                if result.jobs
                else None,
                auto_closure_reports=auto_closure_reports,
            )
        except LarkCliError as exc:
            raise self._lark_spreadsheet_error(exc) from exc
        except OSError as exc:
            raise HTTPException(
                status_code=502, detail=f"Lark spreadsheet operation failed: {exc}"
            ) from exc

    def get_spreadsheet_writeback_audit_summary(
        self,
    ) -> SpreadsheetWritebackAuditSummaryResponse:
        by_status = self._job_repository.count_spreadsheet_writeback_audits_by_status()
        return SpreadsheetWritebackAuditSummaryResponse(
            by_status=by_status,
            total_count=sum(by_status.values()),
        )

    def list_spreadsheet_writeback_audits(
        self,
        *,
        status: str | None,
        limit: int | None,
        offset: int,
    ) -> SpreadsheetWritebackAuditListResponse:
        return SpreadsheetWritebackAuditListResponse(
            audits=self._job_repository.list_spreadsheet_writeback_audits(
                status=status, limit=limit, offset=offset
            ),
            total_count=self._job_repository.count_spreadsheet_writeback_audits(status=status),
        )


def build_spreadsheet_router(controller: SpreadsheetRouteController) -> APIRouter:
    router = APIRouter()

    @router.get("/spreadsheets/lark/status")
    def get_lark_spreadsheet_status(
        check_connectivity: bool = False,
        spreadsheet_url: str = "",
        spreadsheet_id: str = "",
        sheet_id: str = "",
    ) -> LarkSpreadsheetStatusResponse:
        return controller.get_lark_spreadsheet_status(
            check_connectivity=check_connectivity,
            spreadsheet_url=spreadsheet_url,
            spreadsheet_id=spreadsheet_id,
            sheet_id=sheet_id,
        )

    @router.get("/lark/operation-audits")
    @router.get("/api/lark/operation-audits")
    def list_lark_operation_audits(
        status: str | None = None,
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> LarkOperationAuditListResponse:
        return controller.list_lark_operation_audits(status=status, limit=limit, offset=offset)

    @router.get("/lark/scopes/check")
    @router.get("/api/lark/scopes/check")
    def check_lark_scopes(
        service: str = "",
        operation: str = "",
        recent_limit: int = Query(default=50, ge=1, le=200),
    ) -> LarkScopeCheckResponse:
        return controller.check_lark_scopes(
            service=service, operation=operation, recent_limit=recent_limit
        )

    @router.post("/lark/auth-sessions")
    @router.post("/api/lark/auth-sessions")
    def create_lark_auth_session(request: LarkAuthSessionRequest) -> LarkAuthSession:
        return controller.create_lark_auth_session(request)

    @router.get("/lark/auth-sessions/{auth_session_id}")
    @router.get("/api/lark/auth-sessions/{auth_session_id}")
    def get_lark_auth_session(auth_session_id: str) -> LarkAuthSession:
        return controller.get_lark_auth_session(auth_session_id)

    @router.post("/lark/auth-sessions/{auth_session_id}/complete")
    @router.post("/api/lark/auth-sessions/{auth_session_id}/complete")
    def complete_lark_auth_session(
        auth_session_id: str,
        request: LarkAuthSessionCompleteRequest,
    ) -> LarkAuthSession:
        return controller.complete_lark_auth_session(auth_session_id, request)

    @router.post("/spreadsheets/sync", status_code=202)
    def sync_spreadsheet(request: SpreadsheetSyncRequest) -> SpreadsheetSyncResult:
        return controller.sync_spreadsheet(request)

    @router.post("/spreadsheets/rerun", status_code=202)
    async def rerun_spreadsheet(request: SpreadsheetRerunRequest) -> SpreadsheetRerunApiResult:
        return await controller.rerun_spreadsheet(request)

    @router.get("/spreadsheets/writeback/audits/summary")
    def get_spreadsheet_writeback_audit_summary() -> SpreadsheetWritebackAuditSummaryResponse:
        return controller.get_spreadsheet_writeback_audit_summary()

    @router.get("/spreadsheets/writeback/audits")
    def list_spreadsheet_writeback_audits(
        status: str | None = None,
        limit: int | None = Query(default=None, ge=0),
        offset: int = Query(default=0, ge=0),
    ) -> SpreadsheetWritebackAuditListResponse:
        return controller.list_spreadsheet_writeback_audits(
            status=status, limit=limit, offset=offset
        )

    return router


def _lark_auth_session_scopes(scopes: list[str]) -> list[str]:
    normalized = [scope.strip() for scope in scopes if scope.strip()]
    if normalized:
        return sorted(set(normalized))
    return sorted(
        {
            scope
            for requirement in lark_scope_requirements(service="sheets")
            for scope in requirement.required_scopes
        }
    )


def _lark_auth_url(
    *,
    identity: str,
    profile: str,
    scopes: list[str],
    state: str,
    redirect_url: str,
) -> str:
    query = {
        "debug_agent_auth": "1",
        "identity": identity,
        "state": state,
        "scopes": ",".join(scopes),
    }
    if profile:
        query["profile"] = profile
    if redirect_url:
        query["redirect_url"] = redirect_url
    return f"{LARK_PERMISSION_CONSOLE_URL}&{urlencode(query)}"


def _lark_auth_session_expired(auth_session: LarkAuthSession) -> bool:
    if not auth_session.expires_at:
        return False
    try:
        expires_at = datetime.fromisoformat(auth_session.expires_at)
    except ValueError:
        return True
    return expires_at < datetime.now(UTC)


def _scope_requirement_status(
    *,
    requirement: LarkScopeRequirement,
    recent_failures: list[LarkOperationAudit],
) -> LarkScopeRequirementStatus:
    matching_failures = [
        audit
        for audit in recent_failures
        if audit.service == requirement.service
        and audit.operation == requirement.operation
        and audit.permission_scopes
    ]
    recent_missing_scopes = sorted(
        {scope for audit in matching_failures for scope in audit.permission_scopes}
    )
    return LarkScopeRequirementStatus(
        service=requirement.service,
        operation=requirement.operation,
        required_scopes=requirement.required_scopes,
        risk_level=requirement.risk_level,
        identity=requirement.identity,
        confirmation_required=requirement.confirmation_required,
        repair_hint=requirement.repair_hint,
        console_url=requirement.console_url,
        status="missing_recently" if recent_missing_scopes else "not_observed_missing",
        recent_missing_scopes=recent_missing_scopes,
        recent_failure_count=len(matching_failures),
    )


def _recent_missing_scopes(recent_failures: list[LarkOperationAudit]) -> list[str]:
    return sorted({scope for audit in recent_failures for scope in audit.permission_scopes})


def _lark_scope_repair_steps(
    *,
    requirements: list[LarkScopeRequirement],
    recent_failures: list[LarkOperationAudit],
) -> list[str]:
    required_scopes = sorted(
        {scope for requirement in requirements for scope in requirement.required_scopes}
    )
    recent_missing = _recent_missing_scopes(recent_failures)
    if not requirements:
        return [
            "没有匹配到已登记的 Lark 操作，请先确认 service 和 operation 是否属于已接入的 connector 能力。"
        ]
    steps = [
        "当前本地 CLI connector 不能直接读取租户已授权 scope，因此检查状态为 not_verified。",
        f"在飞书开放平台打开当前应用的权限管理页面：{LARK_PERMISSION_CONSOLE_URL}",
        f"确认应用至少具备这些 scope：{', '.join(required_scopes)}。",
    ]
    if recent_missing:
        steps.append(f"最近失败审计明确缺少这些 scope：{', '.join(recent_missing)}。")
    steps.append("权限变更后重新安装或刷新授权，再回到 Debug Agent 执行连接检查。")
    return steps
