from __future__ import annotations

import json
from typing import Literal
from uuid import uuid4

from debug_agent.lark.events import _dict, _string
from debug_agent.lark.schemas import LarkBotReplyPayload

def build_lark_bot_pending_command_reply(
    command: object,
    *,
    identity: str = "bot",
    dry_run: bool = True,
) -> LarkBotReplyPayload:
    command_id = _attr_string(command, "command_id")
    status = _attr_string(command, "status") or "unknown"
    action_kind = _attr_string(command, "action_kind") or "unknown"
    message_id = _attr_string(command, "message_id")
    chat_id = _attr_string(command, "chat_id")
    user_id = _attr_string(command, "open_id")
    if message_id:
        target_type: Literal["message", "chat", "user", "none"] = "message"
    elif chat_id:
        target_type = "chat"
    elif user_id:
        target_type = "user"
    else:
        target_type = "none"
    markdown = _reply_markdown_for_command(command)
    message_type: Literal["post", "interactive"] = "post"
    content: dict[str, object] = {}
    if status == "confirmed" and action_kind == "spreadsheet_rerun":
        message_type = "interactive"
        content = _spreadsheet_rerun_confirmed_card(command)
    elif status == "executed" and action_kind == "spreadsheet_rerun":
        message_type = "interactive"
        content = _spreadsheet_rerun_executed_card(command)
    payload = LarkBotReplyPayload(
        command_id=command_id,
        action_kind=action_kind,
        status=status,
        target_type=target_type,
        message_id=message_id,
        chat_id=chat_id,
        user_id=user_id,
        markdown=markdown,
        message_type=message_type,
        content=content,
        idempotency_key=lark_bot_idempotency_key("bot"),
    )
    return payload.model_copy(
        update={
            "delivery_args": lark_bot_reply_cli_args(
                payload,
                identity=_normalized_identity(identity),
                dry_run=dry_run,
            )
        }
    )


def lark_bot_reply_cli_args(
    payload: LarkBotReplyPayload,
    *,
    identity: Literal["bot", "user", "unknown"] = "bot",
    dry_run: bool = True,
) -> list[str]:
    if payload.delivery_mode == "update_message":
        if not payload.message_id or payload.message_type != "interactive" or not payload.content:
            return []
        args = [
            "api",
            "PATCH",
            f"/open-apis/im/v1/messages/{payload.message_id}",
            "--data",
            _safe_cli_json_arg(
                {
                    "content": json.dumps(
                        payload.content,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                }
            ),
        ]
        if identity in {"bot", "user"}:
            args.extend(["--as", identity])
        return args
    if payload.target_type == "message" and payload.message_id:
        args = ["im", "+messages-reply", "--message-id", payload.message_id]
    elif payload.target_type == "chat" and payload.chat_id:
        args = ["im", "+messages-send", "--chat-id", payload.chat_id]
    elif payload.target_type == "user" and payload.user_id:
        args = ["im", "+messages-send", "--user-id", payload.user_id]
    else:
        return []
    if payload.message_type == "interactive" and payload.content:
        args.extend(
            [
                "--msg-type",
                "interactive",
                "--content",
                _safe_cli_json_arg(payload.content),
            ]
        )
    else:
        args.extend(["--markdown", payload.markdown])
    args.extend(["--idempotency-key", payload.idempotency_key])
    if identity in {"bot", "user"}:
        args.extend(["--as", identity])
    if dry_run:
        args.append("--dry-run")
    return args


def _safe_cli_json_arg(value: object) -> str:
    # lark-cli is commonly resolved to lark-cli.cmd on Windows. Keep shell
    # metacharacters out of JSON arguments so card URLs with query strings do
    # not get split by cmd before lark-cli receives them.
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        .replace("&", "\\u0026")
        .replace("|", "\\u007c")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )


def lark_bot_idempotency_key(prefix: str = "bot") -> str:
    normalized_prefix = "".join(char for char in prefix.lower() if char.isalnum())[:8] or "bot"
    return f"da-{normalized_prefix}-{uuid4().hex[:20]}"


def _reply_markdown_for_command(command: object) -> str:
    status = _attr_string(command, "status") or "unknown"
    action_kind = _attr_string(command, "action_kind") or "unknown"
    title = _reply_title(status=status, action_kind=action_kind)
    lines = [
        f"## {title}",
        "",
        f"- 命令 ID：`{_attr_string(command, 'command_id') or '未知'}`",
        f"- 原始命令：`{_attr_string(command, 'command_text') or '未知'}`",
        f"- 操作：`{action_kind}`",
        f"- 状态：{_status_label(status)}",
    ]
    error_message = _attr_string(command, "error_message")
    if error_message:
        lines.append(f"- 错误：{error_message}")
    if status == "pending":
        lines.append(f"- 过期时间：{_attr_string(command, 'expires_at') or '未知'}")
        lines.append("")
        lines.append("该命令仍在等待操作者确认，确认前不会创建 Debug 任务。")
    elif status == "executed":
        lines.extend(_execution_result_lines(_attr_dict(command, "execution_result")))
    elif status == "failed":
        lines.append("")
        lines.append("执行失败，已写入 Lark 操作审计。请在运维面板查看错误类型和修复建议。")
    elif status == "expired":
        lines.append("")
        lines.append("该确认已过期；如仍需执行，请重新发送命令生成新的确认。")
    return "\n".join(lines)


def _reply_title(*, status: str, action_kind: str) -> str:
    if status == "executed":
        if action_kind == "submit_case":
            return "Debug Agent 已提交调试任务"
        if action_kind == "submit_batch":
            return "Debug Agent 已提交批量调试"
        if action_kind in {"batch_pause", "batch_resume", "batch_cancel"}:
            return "Debug Agent 已更新批次状态"
        if action_kind in {"worker_start", "worker_stop"}:
            return "Debug Agent 已更新 Worker 状态"
        return "Debug Agent 已执行确认操作"
    if status == "failed":
        return "Debug Agent 调试提交失败"
    if status == "expired":
        return "Debug Agent 调试确认已过期"
    if status == "cancelled":
        return "Debug Agent 已取消待确认操作"
    return "Debug Agent 等待确认"


def _status_label(status: str) -> str:
    return {
        "pending": "等待确认",
        "confirmed": "已确认",
        "executed": "已执行",
        "failed": "执行失败",
        "expired": "已过期",
        "cancelled": "已取消",
    }.get(status, status or "未知")


def _execution_result_lines(execution_result: dict[str, object]) -> list[str]:
    spreadsheet_rerun = _dict(execution_result.get("spreadsheet_rerun"))
    if spreadsheet_rerun:
        return ["", *_spreadsheet_rerun_execution_lines(execution_result)]
    submitted_job = _dict(execution_result.get("submitted_job"))
    if submitted_job:
        job_id = _string(submitted_job.get("job_id")) or "未知"
        case_id = _string(submitted_job.get("case_id")) or "未知"
        return [
            f"- 样本：`{case_id}`",
            f"- 任务：`{job_id}`",
            f"- 查看任务：`/xiaod/views/jobs/{job_id}`",
            "",
            "任务已进入 Debug Agent 队列，后续状态可通过 `/debug job <job_id>` 查询。",
        ]
    batch = _dict(execution_result.get("batch"))
    if batch:
        batch_id = _string(batch.get("batch_id")) or _nested_batch_id(batch) or "未知"
        jobs = batch.get("jobs")
        rejected_case_ids = batch.get("rejected_case_ids")
        accepted_count = len(jobs) if isinstance(jobs, list) else 0
        rejected_count = len(rejected_case_ids) if isinstance(rejected_case_ids, list) else 0
        return [
            f"- 批次：`{batch_id}`",
            f"- 已接收任务数：{accepted_count}",
            f"- 被拒绝样本数：{rejected_count}",
            f"- 查看批次：`/xiaod/views/debug-batches/{batch_id}`",
            "",
            "批量调试已提交，后续状态可通过 `/debug batch <batch_id>` 查询。",
        ]
    worker = _dict(execution_result.get("worker"))
    if worker:
        return [
            f"- Worker 状态：`{_string(worker.get('status')) or 'unknown'}`",
            f"- 待处理：{worker.get('pending_count', 0)}",
            f"- 运行中：{worker.get('running_count', 0)}",
            "",
            "后续可通过 `/debug worker` 查询 Worker 队列状态。",
        ]
    return ["", "命令已执行，但执行结果中没有可展示的任务或批次信息。"]


def _spreadsheet_rerun_confirmed_card(command: object) -> dict[str, object]:
    action = _attr_dict(command, "action")
    parameters = _dict(action.get("parameters"))
    preflight = _dict(action.get("preflight")) or _dict(parameters.get("preflight"))
    valid_rows = _string_list(preflight.get("valid_row_ids"))
    missing_rows = _string_list(preflight.get("missing_row_ids"))
    report_requested = (
        _bool_value(action.get("auto_closure"))
        or _bool_value(action.get("report"))
        or _bool_value(parameters.get("auto_closure"))
        or _bool_value(parameters.get("report"))
    )
    writeback_requested = _bool_value(action.get("writeback")) or _bool_value(
        parameters.get("writeback")
    )
    lines = [
        "## 表格批处理已确认，后台执行中",
        "",
        f"- 命令 ID：`{_attr_string(command, 'command_id') or '未知'}`",
        f"- 有效行：`{', '.join(valid_rows) if valid_rows else '等待后台解析'}`",
    ]
    if missing_rows:
        lines.append(f"- 跳过/缺失行：`{', '.join(missing_rows)}`")
    lines.extend(
        [
            f"- 报告生成：{'会自动生成' if report_requested else '未请求'}",
            "- 写回策略：完成后询问是否同步，默认不同步"
            if writeback_requested
            else "- 写回策略：本次未请求同步",
            "",
            "小D已经把真实执行放到后台，后续会在当前会话继续推送创建、运行、报告和同步决策进度。",
        ]
    )
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"tag": "plain_text", "content": "表格批处理已确认，后台执行中"},
        },
        "elements": [{"tag": "markdown", "content": "\n".join(lines)}],
    }


def _spreadsheet_rerun_executed_card(command: object) -> dict[str, object]:
    execution_result = _attr_dict(command, "execution_result")
    action_elements = _spreadsheet_rerun_writeback_actions(
        command_id=_attr_string(command, "command_id"),
        execution_result=execution_result,
    )
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "green",
            "title": {
                "tag": "plain_text",
                "content": "表格批处理报告已生成，等待同步确认"
                if action_elements
                else "表格批处理已开始运行",
            },
        },
        "elements": [
            {
                "tag": "markdown",
                "content": "\n".join(_spreadsheet_rerun_execution_lines(execution_result)),
            },
            *([{"tag": "action", "actions": action_elements}] if action_elements else []),
        ],
    }


def _spreadsheet_rerun_execution_lines(execution_result: dict[str, object]) -> list[str]:
    result = _dict(execution_result.get("spreadsheet_rerun"))
    preflight = _dict(execution_result.get("preflight"))
    jobs = _dict_list(result.get("jobs"))
    imported_rows = _dict_list(result.get("imported_rows"))
    reports = _dict_list(result.get("auto_closure_reports"))
    row_results = _dict_list(execution_result.get("row_results"))
    batch_id = _spreadsheet_rerun_batch_id(result, jobs)
    writeback_decision_status = _string(execution_result.get("writeback_decision_status"))
    requested_count = _int_value(preflight.get("requested_row_count"))
    present_count = _int_value(preflight.get("present_row_count"))
    valid_count = _int_value(preflight.get("valid_job_count"))
    missing_count = _int_value(preflight.get("missing_row_count"))
    rejected_count = _int_value(preflight.get("rejected_row_count"))
    valid_row_ids = _string_list(preflight.get("valid_row_ids"))
    missing_row_ids = _string_list(preflight.get("missing_row_ids"))
    lines = [
        "**表格批处理运行面板**",
        "",
        f"- 批次：`{batch_id or '未知'}`",
        f"- 已创建 Debug 任务：{len(jobs)} 个",
    ]
    if preflight:
        lines.append(
            f"- 预检：请求 {requested_count} 行，读到 {present_count} 行，"
            f"有效 {valid_count} 行，缺失 {missing_count} 行，无效 {rejected_count} 行。"
        )
    if valid_row_ids:
        lines.append(f"- 有效行：`{', '.join(valid_row_ids)}`")
    if missing_row_ids:
        lines.append(f"- 缺失行：`{', '.join(missing_row_ids)}`")
    if reports:
        lines.append(f"- 自动闭环报告：已生成 {len(reports)} 份")
        lines.append(
            "- 写回决策："
            f"{_spreadsheet_rerun_writeback_decision_status_label(writeback_decision_status)}"
        )
    else:
        lines.append("- 自动闭环报告：未请求或尚未生成")
    if row_results:
        mapped_count = sum(1 for row in row_results if bool(row.get("source_mapped")))
        lines.append(f"- 可同步行：{mapped_count}/{len(row_results)} 行有 source mapping")
    lines.extend(["", "**任务清单**"])
    if not jobs:
        lines.append("- 未创建任务。")
    for index, job in enumerate(jobs[:8], start=1):
        imported_row = imported_rows[index - 1] if index - 1 < len(imported_rows) else {}
        row_id = _string(imported_row.get("sheet_row_id")) or "未知行"
        case_id = _string(job.get("case_id")) or _string(imported_row.get("case_id")) or "未知样本"
        job_id = _string(job.get("job_id")) or "未知任务"
        status = _string(job.get("status")) or "unknown"
        lines.append(f"- {index}. 行 `{row_id}` / `{case_id}` / `{job_id}` / `{status}`")
    if len(jobs) > 8:
        lines.append(f"- 其余 {len(jobs) - 8} 个任务请在批次页查看。")
    if row_results:
        lines.extend(["", "**每行报告结果**"])
        for row in row_results[:8]:
            lines.append(
                "- 行 `{row_id}` / `{case_id}` / `{job_id}`：报告 `{report}`，"
                "source mapping `{mapping}`".format(
                    row_id=_string(row.get("row_id")) or "未知行",
                    case_id=_string(row.get("case_id")) or "未知样本",
                    job_id=_string(row.get("job_id")) or "未知任务",
                    report=_string(row.get("report_url")) or "未生成",
                    mapping="yes" if bool(row.get("source_mapped")) else "no",
                )
            )
        if len(row_results) > 8:
            lines.append(f"- 其余 {len(row_results) - 8} 行请在批次页查看。")
    lines.extend(
        [
            "",
            "如需写回，请在报告完成后点击“同步到飞书表格”；不操作将默认不同步。",
        ]
    )
    return lines


def _spreadsheet_rerun_writeback_actions(
    *,
    command_id: str,
    execution_result: dict[str, object],
) -> list[dict[str, object]]:
    if _string(execution_result.get("writeback_decision_status")) != "pending":
        return []
    return [
        _spreadsheet_rerun_writeback_button(
            label="同步到飞书表格",
            action="sync_spreadsheet_rerun_writeback",
            command_id=command_id,
            style="primary",
        ),
        _spreadsheet_rerun_writeback_button(
            label="不同步",
            action="skip_spreadsheet_rerun_writeback",
            command_id=command_id,
        ),
    ]


def _spreadsheet_rerun_writeback_button(
    *,
    label: str,
    action: str,
    command_id: str,
    style: str = "default",
) -> dict[str, object]:
    value = {"action": action, "command_id": command_id}
    return {
        "tag": "button",
        "text": {"tag": "plain_text", "content": label},
        "type": style,
        "value": value,
        "behaviors": [{"type": "callback", "value": value}],
    }


def _spreadsheet_rerun_writeback_decision_status_label(status: str) -> str:
    return {
        "pending": "待用户确认，默认不同步",
        "not_ready": "报告未就绪，不能同步",
        "not_requested": "未请求同步",
        "synced": "已同步",
        "skipped": "不同步",
        "default_skipped": "超时默认不同步",
        "partially_failed": "部分同步失败",
    }.get(status, status or "未知")


def _spreadsheet_rerun_batch_id(
    result: dict[str, object],
    jobs: list[dict[str, object]],
) -> str:
    batch = _dict(result.get("batch"))
    batch_id = _string(batch.get("batch_id")) or _nested_batch_id(batch)
    if batch_id:
        return batch_id
    first_job = jobs[0] if jobs else {}
    return _string(first_job.get("artifact_group_id"))


def _dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _bool_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _int_value(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return 0


def _nested_batch_id(batch: dict[str, object]) -> str:
    batch_progress = _dict(batch.get("batch"))
    nested_batch = _dict(batch_progress.get("batch"))
    return _string(nested_batch.get("batch_id"))


def _attr_string(value: object, name: str) -> str:
    attr = getattr(value, name, "")
    return attr.strip() if isinstance(attr, str) else ""


def _attr_dict(value: object, name: str) -> dict[str, object]:
    attr = getattr(value, name, {})
    return attr if isinstance(attr, dict) else {}


def _normalized_identity(value: str) -> Literal["bot", "user", "unknown"]:
    return value if value in {"bot", "user"} else "unknown"
