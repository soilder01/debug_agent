from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable
from time import perf_counter
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from debug_agent.telemetry.performance import record_performance_event


CommandRunner = Callable[[list[str], str | None], str]
DEFAULT_LARK_CLI_TIMEOUT_SECONDS = 60
LARK_PERMISSION_CONSOLE_URL = "https://open.larkoffice.com/app?lang=zh-CN"
LarkIdentity = Literal["bot", "user", "unknown"]
LarkAuditSink = Callable[["LarkConnectorAuditEvent"], None]


class LarkConnectorProtocol(Protocol):
    def status(self) -> "LarkConnectorStatus":
        ...

    def run_json(self, args: list[str], stdin: str | None = None) -> dict[str, object]:
        ...


class LarkConnectorStatus(BaseModel):
    mode: Literal["cli", "openapi", "fake"] = "cli"
    identity: LarkIdentity = "unknown"
    profile: str = ""
    auth_status: str = "unknown"
    token_status: str = "unknown"


class LarkConnectorAuditEvent(BaseModel):
    connector_mode: Literal["cli", "openapi", "fake"] = "cli"
    service: str
    operation: str
    status: Literal["succeeded", "failed"]
    identity: LarkIdentity = "unknown"
    profile: str = ""
    context: str = ""
    error_type: str = ""
    hint: str = ""
    permission_scopes: list[str] = Field(default_factory=list)
    console_url: str = ""
    risk_action: str = ""
    duration_ms: int = 0


class LarkScopeRequirement(BaseModel):
    service: str
    operation: str
    required_scopes: list[str]
    risk_level: Literal["read", "write"]
    identity: Literal["bot", "user", "either"] = "bot"
    confirmation_required: bool = False
    repair_hint: str
    console_url: str = LARK_PERMISSION_CONSOLE_URL


LARK_SCOPE_REQUIREMENTS: tuple[LarkScopeRequirement, ...] = (
    LarkScopeRequirement(
        service="sheets",
        operation="+csv-get",
        required_scopes=["sheets:spreadsheet:readonly"],
        risk_level="read",
        repair_hint="在飞书开放平台为应用开通电子表格读取权限，重新安装或刷新授权后再检查连接。",
    ),
    LarkScopeRequirement(
        service="sheets",
        operation="+cells-set",
        required_scopes=["sheets:spreadsheet"],
        risk_level="write",
        confirmation_required=True,
        repair_hint="在飞书开放平台为应用开通电子表格编辑权限，确认写入风险后再执行回写。",
    ),
    LarkScopeRequirement(
        service="docs",
        operation="+create",
        required_scopes=["docx:document"],
        risk_level="write",
        identity="bot",
        confirmation_required=True,
        repair_hint="在飞书开放平台为应用开通新版文档写权限，用于生成调试报告云文档。",
    ),
    LarkScopeRequirement(
        service="base",
        operation="+record-upsert",
        required_scopes=["bitable:app"],
        risk_level="write",
        confirmation_required=True,
        repair_hint="在飞书开放平台为应用开通多维表格编辑权限，确认写入风险后再执行 Base 记录写回。",
    ),
    LarkScopeRequirement(
        service="im",
        operation="+messages-send",
        required_scopes=["im:message:send_as_bot"],
        risk_level="write",
        identity="bot",
        confirmation_required=True,
        repair_hint="在飞书开放平台为应用开通机器人发送消息权限，并确认机器人已加入目标群聊。",
    ),
    LarkScopeRequirement(
        service="im",
        operation="+messages-reply",
        required_scopes=["im:message:send_as_bot"],
        risk_level="write",
        identity="bot",
        confirmation_required=True,
        repair_hint="在飞书开放平台为应用开通机器人回复消息权限，并确认机器人可访问原消息所在会话。",
    ),
    LarkScopeRequirement(
        service="im",
        operation="+messages-send",
        required_scopes=["im:message.send_as_user", "im:message"],
        risk_level="write",
        identity="user",
        confirmation_required=True,
        repair_hint="用 user 身份发送消息时，需要用户完成 im:message.send_as_user 与 im:message 授权。",
    ),
    LarkScopeRequirement(
        service="im",
        operation="+messages-reply",
        required_scopes=["im:message.send_as_user", "im:message"],
        risk_level="write",
        identity="user",
        confirmation_required=True,
        repair_hint="用 user 身份回复消息时，需要用户完成 im:message.send_as_user 与 im:message 授权。",
    ),
)


class LarkCliError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        error_type: str = "cli_error",
        hint: str = "",
        permission_scopes: list[str] | None = None,
        console_url: str = "",
        risk_action: str = "",
    ) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.hint = hint
        self.permission_scopes = permission_scopes or []
        self.console_url = console_url
        self.risk_action = risk_action


def lark_scope_requirements(service: str = "", operation: str = "") -> list[LarkScopeRequirement]:
    normalized_service = service.strip()
    normalized_operation = _normalize_operation(operation)
    return [
        requirement
        for requirement in LARK_SCOPE_REQUIREMENTS
        if (not normalized_service or requirement.service == normalized_service)
        and (not normalized_operation or requirement.operation == normalized_operation)
    ]


def lark_required_scopes(service: str, operation: str) -> list[str]:
    scopes: list[str] = []
    for requirement in lark_scope_requirements(service=service, operation=operation):
        for scope in requirement.required_scopes:
            if scope not in scopes:
                scopes.append(scope)
    return scopes


class LarkCliConnector:
    def __init__(
        self,
        *,
        command_runner: CommandRunner | None = None,
        cli_command: str = "lark-cli",
        timeout_seconds: int = DEFAULT_LARK_CLI_TIMEOUT_SECONDS,
        profile: str = "",
        identity: LarkIdentity = "unknown",
        allowed_commands: set[tuple[str, str]] | None = None,
        audit_sink: LarkAuditSink | None = None,
    ) -> None:
        self._command_runner = command_runner or _subprocess_lark_cli_runner(timeout_seconds)
        self._cli_command = cli_command if command_runner is not None else _resolve_lark_cli_command(cli_command)
        self._profile = profile.strip()
        self._identity: LarkIdentity = identity if identity in {"bot", "user", "unknown"} else "unknown"
        self._allowed_commands = allowed_commands or {
            ("sheets", "+csv-get"),
            ("sheets", "+cells-set"),
            ("im", "+messages-send"),
            ("im", "+messages-reply"),
        }
        self._audit_sink = audit_sink

    def status(self) -> LarkConnectorStatus:
        return LarkConnectorStatus(identity=self._identity, profile=self._profile)

    def run_json(self, args: list[str], stdin: str | None = None) -> dict[str, object]:
        service, operation = _service_and_operation(args)
        if (service, operation) not in self._allowed_commands:
            self._emit_audit(
                service=service,
                operation=operation,
                status="failed",
                context=f"{service} {operation}".strip(),
                error_type="command_not_allowed",
                duration_ms=0,
            )
            raise LarkCliError(
                f"lark-cli command is not allowed by connector policy: {service} {operation}",
                error_type="command_not_allowed",
            )
        full_args = self._full_args(args)
        context = _safe_command_context(full_args)
        started_at = perf_counter()
        try:
            output = self._command_runner(full_args, stdin)
            data = _parse_lark_cli_data(output, context=context)
        except Exception as exc:
            duration_ms = int((perf_counter() - started_at) * 1000)
            record_performance_event(
                component="lark_cli",
                operation=operation,
                duration_ms=duration_ms,
                status="failed",
                metadata={
                    "context": context,
                    "error_type": getattr(exc, "error_type", type(exc).__name__),
                    "identity": self._identity,
                    "profile": self._profile,
                },
            )
            self._emit_audit(
                service=service,
                operation=operation,
                status="failed",
                context=context,
                error_type=getattr(exc, "error_type", type(exc).__name__),
                hint=getattr(exc, "hint", ""),
                permission_scopes=getattr(exc, "permission_scopes", []),
                console_url=getattr(exc, "console_url", ""),
                risk_action=getattr(exc, "risk_action", ""),
                duration_ms=duration_ms,
            )
            raise
        duration_ms = int((perf_counter() - started_at) * 1000)
        record_performance_event(
            component="lark_cli",
            operation=operation,
            duration_ms=duration_ms,
            metadata={"context": context, "identity": self._identity, "profile": self._profile},
        )
        self._emit_audit(
            service=service,
            operation=operation,
            status="succeeded",
            context=context,
            duration_ms=duration_ms,
        )
        return data

    def _full_args(self, args: list[str]) -> list[str]:
        full_args = [self._cli_command]
        if self._profile:
            full_args.extend(["--profile", self._profile])
        full_args.extend(args)
        return full_args

    def _emit_audit(
        self,
        *,
        service: str,
        operation: str,
        status: Literal["succeeded", "failed"],
        context: str,
        error_type: str = "",
        hint: str = "",
        permission_scopes: list[str] | None = None,
        console_url: str = "",
        risk_action: str = "",
        duration_ms: int = 0,
    ) -> None:
        if self._audit_sink is None:
            return
        self._audit_sink(
            LarkConnectorAuditEvent(
                service=service,
                operation=operation,
                status=status,
                identity=self._identity,
                profile=self._profile,
                context=context,
                error_type=error_type,
                hint=hint,
                permission_scopes=permission_scopes or [],
                console_url=console_url,
                risk_action=risk_action,
                duration_ms=duration_ms,
            )
        )


class LarkOpenApiConnector:
    def __init__(
        self,
        *,
        identity: LarkIdentity = "bot",
        profile: str = "",
        base_url: str = "https://open.larkoffice.com/open-apis",
        audit_sink: LarkAuditSink | None = None,
    ) -> None:
        self._identity: LarkIdentity = identity if identity in {"bot", "user", "unknown"} else "unknown"
        self._profile = profile.strip()
        self._base_url = base_url.rstrip("/")
        self._audit_sink = audit_sink

    def status(self) -> LarkConnectorStatus:
        return LarkConnectorStatus(
            mode="openapi",
            identity=self._identity,
            profile=self._profile,
            auth_status="not_configured",
            token_status="not_configured",
        )

    def run_json(self, args: list[str], stdin: str | None = None) -> dict[str, object]:
        service, operation = _service_and_operation(args)
        context = _safe_command_context(args)
        self._emit_audit(service=service, operation=operation, context=context)
        raise LarkCliError(
            "Lark OpenAPI connector skeleton is available but not configured for live OpenAPI calls.",
            error_type="connector_not_implemented",
            hint=f"Implement OpenAPI transport for {self._base_url} or keep using the CLI connector.",
        )

    def _emit_audit(self, *, service: str, operation: str, context: str) -> None:
        if self._audit_sink is None:
            return
        self._audit_sink(
            LarkConnectorAuditEvent(
                connector_mode="openapi",
                service=service,
                operation=operation,
                status="failed",
                identity=self._identity,
                profile=self._profile,
                context=context,
                error_type="connector_not_implemented",
                hint=f"Implement OpenAPI transport for {self._base_url} or keep using the CLI connector.",
            )
        )


class FakeLarkConnector:
    def __init__(
        self,
        *,
        responses: dict[tuple[str, str], dict[str, object]] | None = None,
        identity: LarkIdentity = "bot",
        profile: str = "fake",
        audit_sink: LarkAuditSink | None = None,
    ) -> None:
        self._responses = responses or {}
        self._identity: LarkIdentity = identity if identity in {"bot", "user", "unknown"} else "unknown"
        self._profile = profile.strip()
        self._audit_sink = audit_sink

    def status(self) -> LarkConnectorStatus:
        return LarkConnectorStatus(mode="fake", identity=self._identity, profile=self._profile, auth_status="ok", token_status="ok")

    def run_json(self, args: list[str], stdin: str | None = None) -> dict[str, object]:
        service, operation = _service_and_operation(args)
        context = _safe_command_context(args)
        response = self._responses.get((service, operation), {})
        if self._audit_sink is not None:
            self._audit_sink(
                LarkConnectorAuditEvent(
                    connector_mode="fake",
                    service=service,
                    operation=operation,
                    status="succeeded",
                    identity=self._identity,
                    profile=self._profile,
                    context=context,
                )
            )
        return response


def _subprocess_lark_cli_runner(timeout_seconds: int) -> CommandRunner:
    def run(args: list[str], stdin: str | None = None) -> str:
        return _run_lark_cli(args=args, stdin=stdin, timeout_seconds=timeout_seconds)

    return run


def _run_lark_cli(
    args: list[str],
    stdin: str | None = None,
    timeout_seconds: int = DEFAULT_LARK_CLI_TIMEOUT_SECONDS,
) -> str:
    context = _safe_command_context(args)
    try:
        completed = subprocess.run(
            args,
            input=stdin,
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout_seconds,
        )
    except FileNotFoundError as exc:
        raise LarkCliError(
            "lark-cli executable was not found. Install @larksuite/cli or set PATH so lark-cli.cmd is available.",
            error_type="missing_executable",
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise LarkCliError(
            f"lark-cli {context} timed out after {timeout_seconds} seconds",
            error_type="timeout",
        ) from exc
    if completed.returncode != 0:
        message = _prefer_json_error_output(
            stdout=completed.stdout.strip(),
            stderr=completed.stderr.strip(),
            fallback=f"lark-cli exited {completed.returncode}",
        )
        raise _lark_cli_error_from_raw(
            raw=message,
            fallback_message=f"lark-cli {context} failed: {message}",
            fallback_type="cli_error",
        )
    return completed.stdout


def _parse_lark_cli_data(output: str, *, context: str) -> dict[str, object]:
    try:
        envelope = json.loads(output)
    except json.JSONDecodeError as exc:
        raise LarkCliError("lark-cli returned invalid JSON", error_type="invalid_json") from exc
    if not isinstance(envelope, dict):
        raise LarkCliError("lark-cli returned a non-object envelope", error_type="invalid_json")
    if envelope.get("ok") is False:
        raise _lark_cli_error_from_envelope(
            envelope,
            fallback_message=f"lark-cli {context} failed: {envelope.get('error', 'lark-cli command failed')}",
        )
    data = envelope.get("data", {})
    if not isinstance(data, dict):
        raise LarkCliError("lark-cli returned an invalid data envelope", error_type="invalid_json")
    return data


def _lark_cli_error_from_raw(*, raw: str, fallback_message: str, fallback_type: str) -> LarkCliError:
    try:
        envelope = json.loads(raw)
    except json.JSONDecodeError:
        envelope = _json_object_embedded_in_text(raw)
        if envelope is None:
            return LarkCliError(fallback_message, error_type=fallback_type)
    if not isinstance(envelope, dict):
        return LarkCliError(fallback_message, error_type=fallback_type)
    return _lark_cli_error_from_envelope(envelope, fallback_message=fallback_message)


def _prefer_json_error_output(*, stdout: str, stderr: str, fallback: str) -> str:
    if _json_object_embedded_in_text(stdout) is not None:
        return stdout
    if _json_object_embedded_in_text(stderr) is not None:
        return stderr
    return stderr or stdout or fallback


def _json_object_embedded_in_text(text: str) -> dict[str, object] | None:
    json_start = text.find("{")
    if json_start < 0:
        return None
    try:
        decoded = json.loads(text[json_start:])
    except json.JSONDecodeError:
        return None
    return decoded if isinstance(decoded, dict) else None


def _lark_cli_error_from_envelope(envelope: dict[str, object], *, fallback_message: str) -> LarkCliError:
    error = envelope.get("error")
    if not isinstance(error, dict):
        return LarkCliError(str(error or fallback_message), error_type="cli_error")
    message = str(error.get("message") or fallback_message)
    hint = str(error.get("hint") or "")
    error_type = str(error.get("type") or "cli_error")
    permission_scopes = _permission_scopes(error)
    console_url = str(error.get("console_url") or "")
    risk_action = _risk_action(error)
    if error_type == "confirmation_required":
        normalized_type = "confirmation_required"
    elif permission_scopes:
        normalized_type = "permission_denied"
    elif "auth" in error_type or "token" in error_type:
        normalized_type = "auth_required"
    else:
        normalized_type = error_type
    detail = message
    if hint:
        detail = f"{detail} Hint: {hint}"
    return LarkCliError(
        detail,
        error_type=normalized_type,
        hint=hint,
        permission_scopes=permission_scopes,
        console_url=console_url,
        risk_action=risk_action,
    )


def _permission_scopes(error: dict[str, object]) -> list[str]:
    missing_scopes = error.get("missing_scopes")
    if isinstance(missing_scopes, list):
        scopes = [scope for scope in missing_scopes if isinstance(scope, str)]
        if scopes:
            return scopes
    violations = error.get("permission_violations")
    if isinstance(violations, list):
        scopes: list[str] = []
        for item in violations:
            if isinstance(item, str):
                scopes.append(item)
            elif isinstance(item, dict):
                scope = item.get("scope") or item.get("permission") or item.get("subject")
                if isinstance(scope, str):
                    scopes.append(scope)
        return scopes
    scope = error.get("scope")
    if isinstance(scope, str):
        return [scope]
    message = error.get("message")
    if isinstance(message, str):
        return _permission_scopes_from_embedded_message(message)
    return []


def _permission_scopes_from_embedded_message(message: str) -> list[str]:
    decoded = _json_object_embedded_in_text(message)
    if decoded is None:
        return []
    nested_error = decoded.get("error")
    if isinstance(nested_error, dict):
        return _permission_scopes(nested_error)
    return []


def _risk_action(error: dict[str, object]) -> str:
    risk = error.get("risk")
    if not isinstance(risk, dict):
        return ""
    action = risk.get("action")
    return action if isinstance(action, str) else ""


def _resolve_lark_cli_command(command: str) -> str:
    resolved = shutil.which(command)
    if resolved is not None:
        return resolved
    if not command.lower().endswith(".cmd"):
        resolved_cmd = shutil.which(f"{command}.cmd")
        if resolved_cmd is not None:
            return resolved_cmd
    return command


def _service_and_operation(args: list[str]) -> tuple[str, str]:
    non_flag_args = [item for item in args if not item.startswith("-")]
    if len(non_flag_args) >= 2 and non_flag_args[0] == "api":
        return "api", non_flag_args[1].upper()
    service = ""
    operation = ""
    for index, item in enumerate(args):
        if item.startswith("-"):
            continue
        if not service:
            service = item
            continue
        if item.startswith("+"):
            operation = item
            break
        if index + 1 < len(args) and args[index + 1].startswith("+"):
            operation = args[index + 1]
            break
    return service, operation or "command"


def _normalize_operation(operation: str) -> str:
    normalized = operation.strip()
    if normalized and not normalized.startswith("+"):
        normalized = f"+{normalized}"
    return normalized


def _safe_command_context(args: list[str]) -> str:
    safe_flags = {
        "--spreadsheet-token",
        "--sheet-id",
        "--range",
        "--profile",
        "--chat-id",
        "--user-id",
        "--message-id",
        "--idempotency-key",
        "--as",
    }
    parts: list[str] = []
    for item in args:
        if item.startswith("+"):
            parts.append(item)
            break
    index = 0
    while index < len(args):
        item = args[index]
        if item in safe_flags and index + 1 < len(args):
            parts.append(f"{item} {args[index + 1]}")
            index += 2
            continue
        index += 1
    return " ".join(parts) or "command"
