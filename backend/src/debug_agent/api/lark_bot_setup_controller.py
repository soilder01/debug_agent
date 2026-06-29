from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Literal, cast

from fastapi import HTTPException

from debug_agent.api.lark_bot_setup_routes import (
    LarkBotGoLiveGateCheck,
    LarkBotGoLiveGateResponse,
    LarkBotPermissionChecklistResponse,
    LarkBotPermissionRequirement,
    LarkBotPreflightCheck,
    LarkBotPreflightResponse,
    LarkBotSetupAcknowledgementListResponse,
    LarkBotSetupAcknowledgementRequest,
    LarkBotSetupChecklistItem,
)
from debug_agent.api.operations_routes import ProductionReadinessResponse
from debug_agent.lark.bot import parse_lark_bot_event_payload
from debug_agent.lark.connector import LarkConnectorStatus
from debug_agent.settings import DebugAgentSettings
from debug_agent.storage.repository import DebugJobRepository, LarkBotSetupAcknowledgement


LarkBotEventMode = Literal["webhook", "long_connection"]
LarkBotPermissionPhase = Literal["required_now", "recommended_next"]
LarkBotPermissionType = Literal["event_subscription", "oauth_scope"]
LarkBotPermissionRisk = Literal["event", "read", "write"]


class LarkBotSetupController:
    def __init__(
        self,
        *,
        settings: Callable[[], DebugAgentSettings],
        job_repository: DebugJobRepository,
        event_mode: Callable[[], LarkBotEventMode],
        connector_status: Callable[[], LarkConnectorStatus],
        operations_readiness: Callable[[], ProductionReadinessResponse],
        resolved_actor: Callable[[str], str],
        verification_token: Callable[[], str],
        encrypt_key: Callable[[], str],
        lark_cli_profile: Callable[[], str],
        setup_item_keys: set[str],
        permission_catalog: tuple[dict[str, object], ...],
        permission_console_url: str,
        setup_package_url: str,
        permission_checklist_url: str,
        receive_event_type: str,
        card_action_event_type: str,
        long_connection_profile: str,
    ) -> None:
        self._settings = settings
        self._job_repository = job_repository
        self._event_mode = event_mode
        self._connector_status = connector_status
        self._operations_readiness = operations_readiness
        self._resolved_actor = resolved_actor
        self._verification_token = verification_token
        self._encrypt_key = encrypt_key
        self._lark_cli_profile = lark_cli_profile
        self._setup_item_keys = setup_item_keys
        self._permission_catalog = permission_catalog
        self._permission_console_url = permission_console_url
        self._setup_package_url = setup_package_url
        self._permission_checklist_url = permission_checklist_url
        self._receive_event_type = receive_event_type
        self._card_action_event_type = card_action_event_type
        self._long_connection_profile = long_connection_profile

    def get_permission_checklist(self) -> LarkBotPermissionChecklistResponse:
        event_mode = self._event_mode()
        recent_missing_scopes = self.recent_missing_scopes()
        requirements = self.permission_requirements(
            event_mode=event_mode,
            recent_missing_scopes=recent_missing_scopes,
        )
        blocking_scopes = sorted(
            {requirement.scope for requirement in requirements if requirement.blocking}
        )
        required_scopes = self.scopes_for_phase(requirements=requirements, phase="required_now")
        recommended_scopes = self.scopes_for_phase(
            requirements=requirements,
            phase="recommended_next",
        )
        status = self.permission_checklist_status(
            requirements=requirements,
            blocking_scopes=blocking_scopes,
        )
        return LarkBotPermissionChecklistResponse(
            generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
            status=status,
            event_mode=event_mode,
            required_scopes=required_scopes,
            recommended_scopes=recommended_scopes,
            recent_missing_scopes=recent_missing_scopes,
            blocking_scopes=blocking_scopes,
            requirements=requirements,
            admin_handoff_markdown=self.permission_admin_handoff_markdown(
                requirements=requirements,
                blocking_scopes=blocking_scopes,
            ),
            console_url=self._permission_console_url,
        )

    def get_preflight(self) -> LarkBotPreflightResponse:
        event_mode = self._event_mode()
        connector_status = self._connector_status()
        required_bot_scopes = self.required_scopes(event_mode=event_mode)
        recent_missing_scopes = [
            scope for scope in self.recent_missing_scopes() if scope in required_bot_scopes
        ]
        pending_command_count = self._job_repository.count_lark_bot_pending_commands(
            status="pending"
        )
        failed_command_count = self._job_repository.count_lark_bot_pending_commands(
            status="failed"
        )
        event_endpoint_url = self.event_endpoint_url()
        checks = self.preflight_checks(
            event_mode=event_mode,
            connector_status=connector_status,
            required_bot_scopes=required_bot_scopes,
            recent_missing_scopes=recent_missing_scopes,
            pending_command_count=pending_command_count,
            failed_command_count=failed_command_count,
            event_endpoint_url=event_endpoint_url,
        )
        operator_required_items = self.setup_checklist(
            event_mode=event_mode,
            connector_status=connector_status,
            required_bot_scopes=required_bot_scopes,
            recent_missing_scopes=recent_missing_scopes,
            event_endpoint_url=event_endpoint_url,
        )
        return LarkBotPreflightResponse(
            generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
            status=self.preflight_status(checks),
            connector=connector_status,
            event_mode=event_mode,
            event_endpoint_url=event_endpoint_url,
            setup_package_url=self._setup_package_url,
            required_bot_scopes=required_bot_scopes,
            pending_command_count=pending_command_count,
            failed_command_count=failed_command_count,
            recent_missing_scopes=recent_missing_scopes,
            operator_required_items=operator_required_items,
            checks=checks,
        )

    def get_go_live_gate(self) -> LarkBotGoLiveGateResponse:
        preflight = self.get_preflight()
        checks = self.go_live_gate_checks(preflight=preflight)
        status = self.go_live_gate_status(checks)
        allowed = status == "passed"
        return LarkBotGoLiveGateResponse(
            generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
            status=status,
            allowed=allowed,
            decision="允许进入真实飞书机器人 dogfood。"
            if allowed
            else "暂不允许进入真实飞书机器人 dogfood。",
            preflight=preflight,
            checks=checks,
            export_urls={
                "preflight": "/api/lark/bot/preflight",
                "permission_checklist": self._permission_checklist_url,
                "setup_package": self._setup_package_url,
                "setup_acknowledgements": "/api/lark/bot/setup-acknowledgements",
                "operation_audits": "/api/lark/operation-audits",
                "support_bundle": "/api/operations/support-bundle.zip",
            },
        )

    def list_setup_acknowledgements(
        self,
        item_key: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> LarkBotSetupAcknowledgementListResponse:
        return LarkBotSetupAcknowledgementListResponse(
            acknowledgements=self._job_repository.list_lark_bot_setup_acknowledgements(
                item_key=item_key,
                limit=limit,
                offset=offset,
            )
        )

    def acknowledge_setup_item(
        self,
        item_key: str,
        request: LarkBotSetupAcknowledgementRequest,
    ) -> LarkBotSetupAcknowledgement:
        normalized_item_key = item_key.strip()
        self.raise_if_unknown_setup_item(normalized_item_key)
        actor = self._resolved_actor(request.actor)
        evidence = request.evidence.strip()
        if not evidence:
            raise HTTPException(
                status_code=400, detail="Evidence is required for Lark bot setup acknowledgement."
            )
        acknowledgement = self._job_repository.create_lark_bot_setup_acknowledgement(
            item_key=normalized_item_key,
            actor=actor,
            evidence=evidence,
            note=request.note.strip(),
        )
        self._job_repository.save_lark_operation_audit(
            actor=actor,
            connector_mode="cli",
            identity="bot",
            profile=self._lark_cli_profile(),
            service="bot",
            operation="setup_acknowledge",
            status="succeeded",
            context=normalized_item_key,
            risk_action="lark_bot_real_app_setup",
            hint="已记录真实飞书接入项人工确认。",
        )
        return acknowledgement

    def permission_requirements(
        self,
        *,
        event_mode: LarkBotEventMode,
        recent_missing_scopes: list[str],
    ) -> list[LarkBotPermissionRequirement]:
        recent_missing = set(recent_missing_scopes)
        requirements: list[LarkBotPermissionRequirement] = []
        for entry in self._permission_catalog:
            permission_type = cast(LarkBotPermissionType, entry["permission_type"])
            phase = cast(LarkBotPermissionPhase, entry["phase"])
            if entry.get("key") == "doc_write" and self._settings().lark_report_docs_enabled:
                phase = "required_now"
            scope = str(entry["scope"])
            scope_missing = permission_type == "oauth_scope" and scope in recent_missing
            requirements.append(
                LarkBotPermissionRequirement(
                    key=str(entry["key"]),
                    title=str(entry["title"]),
                    category=str(entry["category"]),
                    permission_type=permission_type,
                    scope=scope,
                    phase=phase,
                    risk_level=cast(LarkBotPermissionRisk, entry["risk_level"]),
                    operation=str(entry["operation"]),
                    required_for=str(entry["required_for"]),
                    repair_hint=str(entry["repair_hint"]),
                    status="needs_action" if scope_missing else "manual_check",
                    recent_missing=scope_missing,
                    blocking=phase == "required_now" and scope_missing,
                    console_url=self._permission_console_url,
                )
            )
        if event_mode == "webhook":
            return requirements
        return requirements

    def scopes_for_phase(
        self,
        *,
        requirements: list[LarkBotPermissionRequirement],
        phase: LarkBotPermissionPhase,
    ) -> list[str]:
        scopes: list[str] = []
        for requirement in requirements:
            if requirement.permission_type != "oauth_scope" or requirement.phase != phase:
                continue
            if requirement.scope not in scopes:
                scopes.append(requirement.scope)
        return scopes

    def permission_checklist_status(
        self,
        *,
        requirements: list[LarkBotPermissionRequirement],
        blocking_scopes: list[str],
    ) -> Literal["passed", "warning", "failed"]:
        del requirements
        if blocking_scopes:
            return "failed"
        return "passed"

    def permission_admin_handoff_markdown(
        self,
        *,
        requirements: list[LarkBotPermissionRequirement],
        blocking_scopes: list[str],
    ) -> str:
        lines = ["# 小D Bot 飞书权限申请清单", "", "## 当前阻塞"]
        if blocking_scopes:
            lines.extend(f"- `{scope}`" for scope in blocking_scopes)
        else:
            lines.append("- 暂未观察到必需权限缺失；仍需管理员按清单确认授权和事件订阅。")
        lines.extend(
            [
                "",
                "## 必须先申请 / 确认",
                "",
                "| 类别 | 权限 / 配置 | 用途 | 修复动作 |",
                "| --- | --- | --- | --- |",
            ]
        )
        for requirement in requirements:
            if requirement.phase != "required_now":
                continue
            lines.append(
                "| "
                f"{requirement.category} | `{requirement.scope}` | "
                f"{requirement.required_for} | {requirement.repair_hint} |"
            )
        lines.extend(["", "## 建议一并申请", "", "| 类别 | 权限 | 用途 |", "| --- | --- | --- |"])
        for requirement in requirements:
            if requirement.phase != "recommended_next":
                continue
            lines.append(
                f"| {requirement.category} | `{requirement.scope}` | {requirement.required_for} |"
            )
        lines.extend(["", f"权限控制台：{self._permission_console_url}"])
        return "\n".join(lines)

    def required_scopes(self, *, event_mode: LarkBotEventMode) -> list[str]:
        requirements = self.permission_requirements(
            event_mode=event_mode,
            recent_missing_scopes=[],
        )
        return sorted(self.scopes_for_phase(requirements=requirements, phase="required_now"))

    def recent_missing_scopes(self) -> list[str]:
        known_scopes = {
            str(entry["scope"])
            for entry in self._permission_catalog
            if entry["permission_type"] == "oauth_scope"
        }
        scopes: set[str] = set()
        for audit in self._job_repository.list_lark_operation_audits(status="failed", limit=50):
            for scope in audit.permission_scopes:
                if scope in known_scopes:
                    scopes.add(scope)
        for draft in self._job_repository.list_lark_bot_badcase_drafts(limit=50):
            for attachment in draft.attachments:
                collect_lark_bot_permission_scopes(
                    value=attachment,
                    scopes=scopes,
                    known_scopes=known_scopes,
                )
        return sorted(scopes)

    def event_endpoint_url(self) -> str:
        return f"{self._settings().report_base_url.rstrip('/')}/api/lark/bot/events"

    def setup_checklist(
        self,
        *,
        event_mode: LarkBotEventMode,
        connector_status: LarkConnectorStatus,
        required_bot_scopes: list[str],
        recent_missing_scopes: list[str],
        event_endpoint_url: str,
    ) -> list[LarkBotSetupChecklistItem]:
        required_scope_text = ", ".join(required_bot_scopes) if required_bot_scopes else "暂无"
        missing_scope_text = (
            ", ".join(recent_missing_scopes) if recent_missing_scopes else "暂无近期缺失"
        )
        settings = self._settings()
        is_long_connection = event_mode == "long_connection"
        event_url_is_public = not is_local_url(settings.report_base_url)
        verification_configured = bool(self._verification_token())
        encrypt_configured = bool(self._encrypt_key())
        bot_identity_configured = self.connector_ready_for_event_mode(
            connector_status=connector_status,
            event_mode=event_mode,
        )
        acknowledgements = self._job_repository.latest_lark_bot_setup_acknowledgements()
        items = [
            LarkBotSetupChecklistItem(
                key="deploy_callback_url",
                title="部署可被飞书访问的回调地址",
                owner="debug_agent_operator",
                required=not is_long_connection,
                status="done" if is_long_connection or event_url_is_public else "needs_action",
                detail=(
                    "mode=long_connection; webhook callback not required"
                    if is_long_connection
                    else event_endpoint_url
                ),
                action=(
                    "长连接模式不需要公网事件回调；确认事件消费者使用 xiaoD bot profile 建立长连接。"
                    if is_long_connection
                    else "将 DEBUG_AGENT_REPORT_BASE_URL 配置为飞书可访问的内网或公网地址，并把该地址填入飞书事件订阅。"
                ),
                evidence="由当前 DEBUG_AGENT_REPORT_BASE_URL 推导。",
            ),
            LarkBotSetupChecklistItem(
                key="copy_verification_token",
                title="同步 Verification Token",
                owner="lark_app_admin",
                required=not is_long_connection,
                status="done" if is_long_connection or verification_configured else "needs_action",
                detail=f"mode={event_mode}; configured={verification_configured}",
                action=(
                    "长连接模式不使用 webhook Verification Token；无需配置 LARK_BOT_VERIFICATION_TOKEN。"
                    if is_long_connection
                    else "在飞书开放平台应用事件订阅页复制 Verification Token 到 LARK_BOT_VERIFICATION_TOKEN。"
                ),
                evidence="后端只记录是否已配置，不回显密钥内容。",
            ),
            LarkBotSetupChecklistItem(
                key="copy_encrypt_key",
                title="同步 Encrypt Key",
                owner="lark_app_admin",
                required=not is_long_connection,
                status="done" if is_long_connection or encrypt_configured else "needs_action",
                detail=f"mode={event_mode}; configured={encrypt_configured}",
                action=(
                    "长连接模式不使用 webhook Encrypt Key；无需配置 LARK_BOT_ENCRYPT_KEY。"
                    if is_long_connection
                    else "在飞书开放平台应用事件订阅页复制 Encrypt Key 到 LARK_BOT_ENCRYPT_KEY，启用签名校验和密文回调解密。"
                ),
                evidence="后端只记录是否已配置，不回显密钥内容。",
            ),
            LarkBotSetupChecklistItem(
                key="subscribe_message_event",
                title="订阅消息接收事件",
                owner="lark_app_admin",
                required=True,
                status="manual_check",
                detail=(
                    f"mode=long_connection; event={self._receive_event_type}"
                    if is_long_connection
                    else f"event={self._receive_event_type}; callback={event_endpoint_url}"
                ),
                action=(
                    f"在飞书开放平台事件订阅中订阅 {self._receive_event_type}，并确认 xiaoD 长连接消费者能收到该事件。"
                    if is_long_connection
                    else f"在飞书开放平台事件订阅中订阅 {self._receive_event_type}，并通过 URL verification 或 webhook probe 验证回调。"
                ),
                evidence="当前后端不能主动读取开放平台事件订阅配置，需要管理员确认。",
            ),
            LarkBotSetupChecklistItem(
                key="configure_card_callback",
                title="配置消息卡片交互回调",
                owner="lark_app_admin",
                required=not is_long_connection,
                status="done" if is_long_connection else "manual_check",
                detail=(
                    f"mode=long_connection; webhook card callback not required; "
                    f"event={self._card_action_event_type}"
                    if is_long_connection
                    else f"callback={event_endpoint_url}; actions=confirm_badcase_draft,cancel_badcase_draft"
                ),
                action=(
                    "长连接模式不配置 webhook 卡片回调；需要补齐长连接消费者对 "
                    f"{self._card_action_event_type} 的消费能力，当前 lark-cli event list 未暴露该 EventKey。"
                    if is_long_connection
                    else (
                        "在飞书开放平台为 xiaoD 应用配置消息卡片交互回调地址，"
                        f"回调地址使用 {event_endpoint_url}；配置并发布后，用真实确认卡片点击验证。"
                    )
                ),
                evidence=(
                    "当前长连接封装只能消费 im.message.receive_v1；卡片点击先通过确认页或自然语言确认兜底，不能作为卡片交互验收通过证据。"
                    if is_long_connection
                    else "当前后端不能主动读取开放平台卡片交互回调配置，需要管理员确认；未配置或配置到不可达地址时，点击卡片按钮会在飞书端报错。"
                ),
            ),
            LarkBotSetupChecklistItem(
                key="grant_im_bot_scope",
                title="开通小D Bot 产品权限",
                owner="lark_app_admin",
                required=True,
                status="needs_action" if recent_missing_scopes else "manual_check",
                detail=f"required={required_scope_text}; recent_missing={missing_scope_text}",
                action=(
                    f"在飞书开放平台为 xiaoD bot 开通 {required_scope_text}，尤其是表格读取和附件下载权限；必要时进入 {self._permission_console_url} 处理权限申请。"
                    if is_long_connection
                    else f"在飞书开放平台开通 {required_scope_text}，尤其是表格读取和附件下载权限；必要时进入 {self._permission_console_url} 处理权限申请。"
                ),
                evidence="机器可读清单见 /api/lark/bot/permission-checklist；近期 Lark 操作审计会记录缺失权限。",
            ),
            LarkBotSetupChecklistItem(
                key="configure_bot_identity",
                title="配置 bot 身份调用飞书 CLI",
                owner="debug_agent_operator",
                required=True,
                status="done" if bot_identity_configured else "needs_action",
                detail=f"{connector_status.mode}/{connector_status.identity}/{connector_status.profile or 'default'}",
                action=(
                    f"配置 LARK_CLI_IDENTITY=bot 和 LARK_CLI_PROFILE={self._long_connection_profile}，确认 Debug Agent 使用小D机器人身份收发消息。"
                    if is_long_connection
                    else "配置 LARK_CLI_IDENTITY=bot 和 LARK_CLI_PROFILE，确认 Debug Agent 使用机器人身份发送回复。"
                ),
                evidence="由当前 Lark Connector 运行配置推导。",
            ),
            LarkBotSetupChecklistItem(
                key="enable_trusted_actor",
                title="开启操作者约束",
                owner="security_admin",
                required=True,
                status="done" if settings.require_trusted_actor else "needs_action",
                detail=f"require_trusted_actor={settings.require_trusted_actor}",
                action="生产候选环境开启 DEBUG_AGENT_REQUIRE_TRUSTED_ACTOR，避免匿名写风险命令进入执行链路。",
                evidence="由当前 Debug Agent 安全配置推导。",
            ),
            LarkBotSetupChecklistItem(
                key="add_bot_to_target_chat",
                title="把机器人加入目标群或开通可见范围",
                owner="workspace_admin",
                required=True,
                status="manual_check",
                detail="需要目标群可见、可接收消息、可回复消息。",
                action="将飞书应用机器人加入试点群，或在应用可见范围中开放给试点成员，然后发送 /debug status 做真实消息验证。",
                evidence="当前后端无法主动判断机器人是否已进入目标群。",
            ),
            LarkBotSetupChecklistItem(
                key="run_webhook_probe",
                title="运行 webhook 探针",
                owner="debug_agent_operator",
                required=not is_long_connection,
                status="done" if is_long_connection else "manual_check",
                detail="not_required" if is_long_connection else "scripts/lark_bot_webhook_probe.py",
                action=(
                    "长连接模式不需要 webhook 探针；用长连接消费日志或真实 /debug status 消息做验证。"
                    if is_long_connection
                    else "在部署地址上运行 URL verification 和 encrypted message probe，确认签名、解密、token、命令解析全部通过。"
                ),
                evidence="探针报告由运维执行后归档；不会访问真实飞书或发送真实消息。",
            ),
        ]
        return [
            self.setup_item_with_acknowledgement(item, acknowledgements.get(item.key))
            for item in items
        ]

    def setup_item_with_acknowledgement(
        self,
        item: LarkBotSetupChecklistItem,
        acknowledgement: LarkBotSetupAcknowledgement | None,
    ) -> LarkBotSetupChecklistItem:
        if acknowledgement is None:
            return item
        status = "done" if item.status == "manual_check" else item.status
        evidence = f"{item.evidence}；最近人工确认：{acknowledgement.evidence}"
        return item.model_copy(
            update={
                "status": status,
                "evidence": evidence,
                "acknowledgement": acknowledgement,
            }
        )

    def raise_if_unknown_setup_item(self, item_key: str) -> None:
        if item_key not in self._setup_item_keys:
            raise HTTPException(status_code=404, detail=f"Unknown Lark bot setup item: {item_key}")

    def connector_ready_for_event_mode(
        self,
        *,
        connector_status: LarkConnectorStatus,
        event_mode: LarkBotEventMode,
    ) -> bool:
        if connector_status.identity != "bot":
            return False
        if event_mode == "long_connection":
            return connector_status.profile == self._long_connection_profile
        return True

    def receive_event_schema_available(self) -> bool:
        try:
            parsed = parse_lark_bot_event_payload(
                {
                    "schema": "2.0",
                    "header": {
                        "event_type": self._receive_event_type,
                        "tenant_key": "tenant-1",
                    },
                    "event": {
                        "sender": {"sender_id": {"open_id": "ou_schema_probe"}},
                        "message": {
                            "message_id": "om_schema_probe",
                            "chat_id": "oc_schema_probe",
                            "message_type": "text",
                            "content": '{"text":"/debug status"}',
                        },
                    },
                }
            )
        except Exception:
            return False
        return parsed.event_type == self._receive_event_type and parsed.command_request is not None

    def card_action_sdk_available(self) -> bool:
        try:
            __import__("lark_oapi")
        except ImportError:
            return False
        return True

    def preflight_checks(
        self,
        *,
        event_mode: LarkBotEventMode,
        connector_status: LarkConnectorStatus,
        required_bot_scopes: list[str],
        recent_missing_scopes: list[str],
        pending_command_count: int,
        failed_command_count: int,
        event_endpoint_url: str,
    ) -> list[LarkBotPreflightCheck]:
        checks: list[LarkBotPreflightCheck] = []
        settings = self._settings()
        if event_mode == "long_connection":
            card_action_sdk_available = self.card_action_sdk_available()
            checks.extend(
                [
                    lark_bot_preflight_check(
                        key="event_receiver_mode",
                        label="事件接收模式",
                        passed=True,
                        warning=False,
                        detail="mode=long_connection; webhook callback/token/encrypt not required",
                        action="无需处理。",
                    ),
                    lark_bot_preflight_check(
                        key="event_schema",
                        label="长连接事件 schema",
                        passed=self.receive_event_schema_available(),
                        warning=False,
                        detail=f"event={self._receive_event_type}",
                        action=f"修复 {self._receive_event_type} 解析能力后再接入长连接事件。",
                    ),
                    lark_bot_preflight_check(
                        key="card_action_event_schema",
                        label="长连接卡片交互事件",
                        passed=card_action_sdk_available,
                        warning=False,
                        detail=(
                            f"event={self._card_action_event_type}; "
                            f"transport=sdk; lark_oapi_available={card_action_sdk_available}"
                        ),
                        action=(
                            "使用 scripts/lark_bot_long_connection_consumer.py --transport sdk "
                            f"启动小D长连接消费者，以同时消费 {self._receive_event_type} "
                            f"和 {self._card_action_event_type}。"
                        ),
                    ),
                ]
            )
        else:
            checks.extend(
                [
                    lark_bot_preflight_check(
                        key="event_endpoint",
                        label="事件回调地址",
                        passed=not is_local_url(settings.report_base_url),
                        warning=settings.environment == "local",
                        detail=event_endpoint_url,
                        action="生产候选需要配置飞书可访问的内网或公网回调地址。",
                    ),
                    lark_bot_preflight_check(
                        key="verification_token",
                        label="Verification Token",
                        passed=bool(self._verification_token()),
                        warning=settings.environment == "local",
                        detail=f"configured={bool(self._verification_token())}",
                        action="配置 LARK_BOT_VERIFICATION_TOKEN，并与飞书事件订阅保持一致。",
                    ),
                    lark_bot_preflight_check(
                        key="encrypt_key",
                        label="Encrypt Key",
                        passed=bool(self._encrypt_key()),
                        warning=settings.environment == "local",
                        detail=f"configured={bool(self._encrypt_key())}",
                        action="配置 LARK_BOT_ENCRYPT_KEY 以启用签名校验和加密回调解密。",
                    ),
                ]
            )
        checks.extend(
            [
                lark_bot_preflight_check(
                    key="trusted_actor",
                    label="操作者约束",
                    passed=settings.require_trusted_actor,
                    warning=settings.environment == "local",
                    detail=f"require_trusted_actor={settings.require_trusted_actor}",
                    action="生产候选建议开启 DEBUG_AGENT_REQUIRE_TRUSTED_ACTOR。",
                ),
                lark_bot_preflight_check(
                    key="connector_identity",
                    label="机器人身份",
                    passed=self.connector_ready_for_event_mode(
                        connector_status=connector_status,
                        event_mode=event_mode,
                    ),
                    warning=(
                        event_mode == "webhook"
                        and (
                            connector_status.identity == "unknown"
                            or settings.environment == "local"
                        )
                    ),
                    detail=f"{connector_status.mode}/{connector_status.identity}/{connector_status.profile or 'default'}",
                    action=(
                        f"配置 LARK_CLI_IDENTITY=bot 和 LARK_CLI_PROFILE={self._long_connection_profile}，确认长连接使用小D机器人身份。"
                        if event_mode == "long_connection"
                        else "配置 LARK_CLI_IDENTITY=bot 和 LARK_CLI_PROFILE，确认机器人具备发送消息身份。"
                    ),
                ),
                lark_bot_preflight_check(
                    key="im_scope_catalog",
                    label="Bot 产品权限清单",
                    passed=bool(required_bot_scopes) and not recent_missing_scopes,
                    warning=bool(required_bot_scopes) and not recent_missing_scopes,
                    detail=(
                        f"required={','.join(required_bot_scopes) or 'none'}; "
                        f"recent_missing={','.join(recent_missing_scopes) or 'none'}"
                    ),
                    action=(
                        f"在飞书开放平台开通 {','.join(required_bot_scopes) or 'none'}，并用表格附件样本和 xiaoD 长连接消息验证。"
                        if event_mode == "long_connection"
                        else f"在飞书开放平台开通 {','.join(required_bot_scopes) or 'none'}，并用真实群聊 dry-run/发送验证。"
                    ),
                ),
                lark_bot_preflight_check(
                    key="pending_commands",
                    label="待确认命令积压",
                    passed=pending_command_count == 0,
                    warning=pending_command_count > 0,
                    detail=f"pending={pending_command_count}",
                    action="上线前处理或确认待执行的机器人命令。",
                ),
                lark_bot_preflight_check(
                    key="failed_commands",
                    label="失败机器人命令",
                    passed=failed_command_count == 0,
                    warning=failed_command_count > 0,
                    detail=f"failed={failed_command_count}",
                    action="上线前复盘失败机器人命令和 Lark 操作审计。",
                ),
            ]
        )
        return checks

    def preflight_status(
        self,
        checks: list[LarkBotPreflightCheck],
    ) -> Literal["passed", "warning", "failed"]:
        if any(check.status == "failed" for check in checks):
            return "failed"
        if any(check.status == "warning" for check in checks):
            return "warning"
        return "passed"

    def go_live_gate_checks(
        self, *, preflight: LarkBotPreflightResponse
    ) -> list[LarkBotGoLiveGateCheck]:
        readiness = self._operations_readiness()
        required_items = [item for item in preflight.operator_required_items if item.required]
        incomplete_items = [item.title for item in required_items if item.status != "done"]
        manual_acknowledgement_keys = {
            "subscribe_message_event",
            "grant_im_bot_scope",
            "add_bot_to_target_chat",
        }
        if preflight.event_mode == "webhook":
            manual_acknowledgement_keys.add("configure_card_callback")
            manual_acknowledgement_keys.add("run_webhook_probe")
        missing_acknowledgements = [
            item.title
            for item in required_items
            if item.key in manual_acknowledgement_keys and item.acknowledgement is None
        ]
        return [
            lark_bot_go_live_gate_check(
                key="production_readiness",
                label="生产运行就绪",
                status=go_live_readiness_status(
                    readiness=readiness, event_mode=preflight.event_mode
                ),
                detail=f"level={readiness.level}",
                action="先处理生产运行就绪里的严重项和需关注项。",
            ),
            lark_bot_go_live_gate_check(
                key="bot_preflight",
                label="机器人上线预检",
                status=preflight.status,
                detail=f"preflight={preflight.status}",
                action="先处理机器人上线预检中的阻塞项和需关注项。",
            ),
            lark_bot_go_live_gate_check(
                key="setup_items",
                label="真实接入清单",
                status="passed" if not incomplete_items else "failed",
                detail="全部接入项已完成"
                if not incomplete_items
                else "未完成：" + "、".join(incomplete_items),
                action="完成所有必需接入项后再进入真实 dogfood。",
            ),
            lark_bot_go_live_gate_check(
                key="manual_acknowledgements",
                label="人工确认记录",
                status="passed" if not missing_acknowledgements else "failed",
                detail="人工确认齐全"
                if not missing_acknowledgements
                else "缺少确认：" + "、".join(missing_acknowledgements),
                action="用记录确认表单补齐管理员确认和证据。",
            ),
            lark_bot_go_live_gate_check(
                key="missing_scopes",
                label="近期缺失权限",
                status="passed" if not preflight.recent_missing_scopes else "failed",
                detail=", ".join(preflight.recent_missing_scopes)
                if preflight.recent_missing_scopes
                else "none",
                action="先在飞书开放平台补齐缺失权限并重新验证。",
            ),
            lark_bot_go_live_gate_check(
                key="pending_commands",
                label="待确认机器人命令",
                status="passed" if preflight.pending_command_count == 0 else "failed",
                detail=f"pending={preflight.pending_command_count}",
                action="上线前处理或清空待确认命令积压。",
            ),
            lark_bot_go_live_gate_check(
                key="failed_commands",
                label="失败机器人命令",
                status="passed" if preflight.failed_command_count == 0 else "warning",
                detail=f"failed={preflight.failed_command_count}",
                action="复盘失败机器人命令后再进入真实 dogfood。",
            ),
        ]

    def go_live_gate_status(
        self,
        checks: list[LarkBotGoLiveGateCheck],
    ) -> Literal["passed", "warning", "failed"]:
        if any(check.status == "failed" for check in checks):
            return "failed"
        if any(check.status == "warning" for check in checks):
            return "warning"
        return "passed"


def collect_lark_bot_permission_scopes(
    *,
    value: object,
    scopes: set[str],
    known_scopes: set[str],
) -> None:
    if isinstance(value, dict):
        permission_scopes = value.get("permission_scopes")
        if isinstance(permission_scopes, list):
            for scope in permission_scopes:
                if isinstance(scope, str) and scope in known_scopes:
                    scopes.add(scope)
        for nested in value.values():
            collect_lark_bot_permission_scopes(
                value=nested,
                scopes=scopes,
                known_scopes=known_scopes,
            )
    elif isinstance(value, list):
        for item in value:
            collect_lark_bot_permission_scopes(
                value=item,
                scopes=scopes,
                known_scopes=known_scopes,
            )


def lark_bot_preflight_check(
    *,
    key: str,
    label: str,
    passed: bool,
    warning: bool,
    detail: str,
    action: str,
) -> LarkBotPreflightCheck:
    if passed:
        return LarkBotPreflightCheck(
            key=key, label=label, status="passed", detail=detail, action="无需处理。"
        )
    if warning:
        return LarkBotPreflightCheck(
            key=key, label=label, status="warning", detail=detail, action=action
        )
    return LarkBotPreflightCheck(
        key=key, label=label, status="failed", detail=detail, action=action
    )


def lark_bot_go_live_gate_check(
    *,
    key: str,
    label: str,
    status: Literal["passed", "warning", "failed"],
    detail: str,
    action: str,
) -> LarkBotGoLiveGateCheck:
    return LarkBotGoLiveGateCheck(
        key=key,
        label=label,
        status=status,
        detail=detail,
        action="无需处理。" if status == "passed" else action,
    )


def go_live_readiness_status(
    *,
    readiness: ProductionReadinessResponse,
    event_mode: LarkBotEventMode,
) -> Literal["passed", "warning", "failed"]:
    if readiness.level == "critical":
        return "failed"
    ignored_warning_keys = {"report_base_url"} if event_mode == "long_connection" else set()
    blocking_warnings = [
        check
        for check in readiness.checks
        if check.status == "warning" and check.key not in ignored_warning_keys
    ]
    if blocking_warnings:
        return "warning"
    return "passed"


def is_local_url(value: str) -> bool:
    return "localhost" in value or "127.0.0.1" in value
