from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Literal

from fastapi.responses import Response

from debug_agent.api.lark_bot_setup_routes import (
    LarkBotPermissionChecklistResponse,
    LarkBotPreflightResponse,
)
from debug_agent.settings import DebugAgentSettings
from debug_agent.storage.repository import LarkBotSetupAcknowledgement


class LarkBotSetupPackageBuilder:
    def __init__(
        self,
        *,
        settings: Callable[[], DebugAgentSettings],
        preflight: Callable[[], LarkBotPreflightResponse],
        permission_checklist: Callable[[], LarkBotPermissionChecklistResponse],
        setup_acknowledgements: Callable[[int], list[LarkBotSetupAcknowledgement]],
        verification_token: Callable[[], str],
        encrypt_key: Callable[[], str],
        permission_console_url: str,
        receive_event_type: str,
        long_connection_profile: str,
    ) -> None:
        self._settings = settings
        self._preflight = preflight
        self._permission_checklist = permission_checklist
        self._setup_acknowledgements = setup_acknowledgements
        self._verification_token = verification_token
        self._encrypt_key = encrypt_key
        self._permission_console_url = permission_console_url
        self._receive_event_type = receive_event_type
        self._long_connection_profile = long_connection_profile

    def export_package(self) -> Response:
        archive = self.build_archive()
        return Response(
            content=archive,
            media_type="application/zip",
            headers={
                "Content-Disposition": 'attachment; filename="debug-agent-lark-bot-setup-package.zip"'
            },
        )

    def build_archive(self) -> bytes:
        preflight = self._preflight()
        permission_checklist = self._permission_checklist()
        generated_at = datetime.now(UTC).isoformat(timespec="seconds")
        preflight_payload = preflight.model_dump(mode="json")
        setup_items = [item.model_dump(mode="json") for item in preflight.operator_required_items]
        required_scopes_payload = {
            "event_mode": preflight.event_mode,
            "required_bot_scopes": permission_checklist.required_scopes,
            "recommended_bot_scopes": permission_checklist.recommended_scopes,
            "recent_missing_scopes": permission_checklist.recent_missing_scopes,
            "blocking_scopes": permission_checklist.blocking_scopes,
            "permission_console_url": self._permission_console_url,
        }
        entries: dict[str, bytes] = {
            "README.txt": self.setup_package_readme(preflight=preflight).encode("utf-8"),
            "preflight.json": _json_bytes(preflight_payload),
            "permission-checklist.json": _json_bytes(permission_checklist.model_dump(mode="json")),
            "permission-checklist.md": permission_checklist.admin_handoff_markdown.encode("utf-8"),
            "setup-checklist.json": _json_bytes({"items": setup_items}),
            "setup-acknowledgements.json": _json_bytes(
                {
                    "acknowledgements": [
                        acknowledgement.model_dump(mode="json")
                        for acknowledgement in self._setup_acknowledgements(500)
                    ]
                }
            ),
            "setup-checklist.md": self.setup_checklist_markdown(preflight=preflight).encode(
                "utf-8"
            ),
            "feishu-admin-handoff.md": self.admin_handoff_markdown(preflight=preflight).encode(
                "utf-8"
            ),
            "required-scopes.json": _json_bytes(required_scopes_payload),
            "long-connection-diagnostics.ps1": self.long_connection_diagnostics_commands(
                preflight=preflight
            ).encode("utf-8"),
            "webhook-probe-commands.ps1": self.webhook_probe_commands(preflight=preflight).encode(
                "utf-8"
            ),
        }
        manifest = {
            "export_type": "lark_bot_setup_package",
            "generated_at": generated_at,
            "event_mode": preflight.event_mode,
            "event_endpoint_url": preflight.event_endpoint_url,
            "setup_package_url": preflight.setup_package_url,
            "contents": ["manifest.json", *entries.keys()],
            "redaction": "Secrets are not included. Verification Token and Encrypt Key are represented by placeholders only.",
        }
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", _json_bytes(manifest))
            for filename, content in entries.items():
                archive.writestr(filename, content)
        return buffer.getvalue()

    def setup_package_readme(self, *, preflight: LarkBotPreflightResponse) -> str:
        return (
            "Debug Agent 飞书机器人接入交付包\n"
            "\n"
            "用途：给 Debug Agent 运维、飞书应用管理员、空间管理员和安全管理员对齐真实接入前的配置事项。\n"
            f"事件模式：{lark_bot_event_mode_label(preflight.event_mode)}\n"
            f"回调地址：{preflight.event_endpoint_url}\n"
            f"预检状态：{lark_bot_preflight_status_label(preflight.status)}\n"
            "\n"
            "安全：该包不包含 Verification Token、Encrypt Key、App Secret、user token 或模型凭据。\n"
            "请将真实密钥只配置到部署环境变量或批准的密钥管理系统中。\n"
        )

    def setup_checklist_markdown(self, *, preflight: LarkBotPreflightResponse) -> str:
        lines = [
            "# 飞书机器人真实接入清单",
            "",
            f"- 生成时间：{preflight.generated_at}",
            f"- 事件模式：{lark_bot_event_mode_label(preflight.event_mode)}",
            f"- 回调地址：`{preflight.event_endpoint_url}`",
            f"- 预检状态：{lark_bot_preflight_status_label(preflight.status)}",
            "",
            "| 状态 | 归属 | 必需 | 事项 | 下一步 | 证据 |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for item in preflight.operator_required_items:
            lines.append(
                "| "
                f"{lark_bot_setup_status_label(item.status)} | "
                f"{lark_bot_setup_owner_label(item.owner)} | "
                f"{'是' if item.required else '否'} | "
                f"{item.title} | "
                f"{item.action} | "
                f"{item.evidence} |"
            )
        lines.extend(
            [
                "",
                "## 必需权限",
                "",
                ", ".join(preflight.required_bot_scopes)
                if preflight.required_bot_scopes
                else "暂无权限清单。",
            ]
        )
        return "\n".join(lines) + "\n"

    def admin_handoff_markdown(self, *, preflight: LarkBotPreflightResponse) -> str:
        token_state = "已配置" if self._verification_token() else "待配置"
        encrypt_state = "已配置" if self._encrypt_key() else "待配置"
        scopes = ", ".join(preflight.required_bot_scopes) if preflight.required_bot_scopes else "暂无"
        if preflight.event_mode == "long_connection":
            return (
                "# 飞书应用管理员交接说明\n"
                "\n"
                "当前为长连接模式。请在飞书开放平台应用后台完成以下事项，并把完成状态回填给 Debug Agent 运维。\n"
                "\n"
                f"1. 事件接收模式：`{preflight.event_mode}`，不需要 webhook 回调地址、Verification Token 或 Encrypt Key。\n"
                f"2. 事件订阅：`{self._receive_event_type}`。\n"
                f"3. 机器人 IM 权限：`{scopes}`。\n"
                f"4. CLI 身份：`LARK_CLI_IDENTITY=bot`，`LARK_CLI_PROFILE={self._long_connection_profile}`。\n"
                "5. 将机器人加入试点群，或开通应用可见范围给试点成员。\n"
                "\n"
                "完成后由 Debug Agent 运维通过长连接消费日志和真实 `/debug status` 消息验证。\n"
            )
        return (
            "# 飞书应用管理员交接说明\n"
            "\n"
            "请在飞书开放平台应用后台完成以下事项，并把完成状态回填给 Debug Agent 运维。\n"
            "\n"
            f"1. 事件订阅回调地址：`{preflight.event_endpoint_url}`。\n"
            f"2. Verification Token：{token_state}。真实值不要写入本交付包。\n"
            f"3. Encrypt Key：{encrypt_state}。真实值不要写入本交付包。\n"
            "4. 事件订阅：`im.message.receive_v1`。\n"
            f"5. 机器人 IM 权限：`{scopes}`。\n"
            "6. 将机器人加入试点群，或开通应用可见范围给试点成员。\n"
            "\n"
            "完成后由 Debug Agent 运维运行 `webhook-probe-commands.ps1` 中的探针命令，"
            "再进入真实消息 dogfood。\n"
        )

    def webhook_probe_commands(self, *, preflight: LarkBotPreflightResponse) -> str:
        if preflight.event_mode == "long_connection":
            return self.long_connection_diagnostics_commands(preflight=preflight)
        base_url = self._settings().report_base_url.rstrip("/")
        return (
            '$BaseUrl = "' + base_url + '"\n'
            '$VerificationToken = "<verification-token>"\n'
            '$EncryptKey = "<encrypt-key>"\n'
            "\n"
            "python scripts/lark_bot_webhook_probe.py --base-url $BaseUrl --mode url-verification --token $VerificationToken\n"
            'python scripts/lark_bot_webhook_probe.py --base-url $BaseUrl --mode message --text "/debug status" --token $VerificationToken\n'
            'python scripts/lark_bot_webhook_probe.py --base-url $BaseUrl --mode message --text "/debug status" --token $VerificationToken --encrypt-key $EncryptKey --encrypt\n'
            "\n"
            f"# 当前推导出的事件订阅地址：{preflight.event_endpoint_url}\n"
        )

    def long_connection_diagnostics_commands(self, *, preflight: LarkBotPreflightResponse) -> str:
        del preflight
        return (
            "# 小D长连接诊断命令。\n"
            "# 当前为长连接模式，不需要 webhook probe。\n"
            "# 该文件是小D主链路诊断入口；webhook probe 仅保留为遗留 HTTP parser 检查。\n"
            '$env:LARK_EVENT_MODE = "long_connection"\n'
            '$env:LARK_CLI_IDENTITY = "bot"\n'
            f'$env:LARK_CLI_PROFILE = "{self._long_connection_profile}"\n'
            "\n"
            "lark-cli event status --json\n"
            f"lark-cli event schema {self._receive_event_type} --json\n"
            f"lark-cli event consume {self._receive_event_type} --as bot --max-events 1 --timeout 30s\n"
            "\n"
            "# 生产候选请使用 SDK transport 同时验证消息接收和卡片 action：\n"
            "python scripts/lark_bot_long_connection_consumer.py --transport sdk --max-events 1 --timeout 30s\n"
            "# 然后在真实飞书会话发送：/debug status\n"
        )


def lark_bot_event_mode_label(event_mode: Literal["webhook", "long_connection"]) -> str:
    if event_mode == "long_connection":
        return "长连接模式"
    return "webhook 模式"


def lark_bot_preflight_status_label(status: Literal["passed", "warning", "failed"]) -> str:
    if status == "passed":
        return "通过"
    if status == "warning":
        return "需关注"
    return "阻塞"


def lark_bot_setup_status_label(status: Literal["done", "needs_action", "manual_check"]) -> str:
    if status == "done":
        return "已完成"
    if status == "needs_action":
        return "需要处理"
    return "需人工确认"


def lark_bot_setup_owner_label(
    owner: Literal["debug_agent_operator", "lark_app_admin", "workspace_admin", "security_admin"],
) -> str:
    labels = {
        "debug_agent_operator": "Debug Agent 运维",
        "lark_app_admin": "飞书应用管理员",
        "workspace_admin": "飞书空间管理员",
        "security_admin": "安全管理员",
    }
    return labels[owner]


def _json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
