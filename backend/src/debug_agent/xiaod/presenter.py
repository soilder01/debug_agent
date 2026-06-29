from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal, Protocol
from uuid import uuid4

from debug_agent.lark.bot import (
    LarkBotCommandResponse,
    LarkBotReplyPayload,
    lark_bot_idempotency_key,
    lark_bot_reply_cli_args,
)
from debug_agent.xiaod.schemas import XiaoDTurnHandleRequest


class BadcaseDraftView(Protocol):
    draft_id: str
    status: str
    missing_fields: list[str]
    attachments: list[dict[str, object]]
    input_source: str
    model_output: str
    expected_output: str
    issue_summary: str
    submitted_case_id: str
    submitted_job_id: str


class SubmittedJobView(Protocol):
    job_id: str
    status: str


class BadcaseConfirmResponseView(Protocol):
    draft: BadcaseDraftView
    submitted_job: SubmittedJobView | None


class PendingCommandView(Protocol):
    command_id: str
    action_kind: str
    command_text: str
    status: str
    action: dict[str, object]


def turn_reply_payload(
    *,
    request: XiaoDTurnHandleRequest,
    action_kind: str,
    markdown: str,
    message_type: Literal["post", "interactive"] = "post",
    content: dict[str, object] | None = None,
) -> LarkBotReplyPayload:
    payload = LarkBotReplyPayload(
        command_id=f"xiaod-{uuid4()}",
        action_kind=action_kind,
        status="handled",
        target_type=turn_reply_target_type(request),
        message_id=request.message_id,
        chat_id=request.chat_id,
        user_id=request.open_id,
        markdown=markdown,
        message_type=message_type,
        content=content or {},
        idempotency_key=lark_bot_idempotency_key("xiaod"),
    )
    return payload.model_copy(
        update={
            "delivery_args": lark_bot_reply_cli_args(
                payload,
                identity=request.identity,
                dry_run=False,
            )
        }
    )


def pending_command_reply_payload(
    *,
    request: XiaoDTurnHandleRequest,
    preview: LarkBotCommandResponse,
    pending: PendingCommandView,
    report_base_url: str,
) -> LarkBotReplyPayload:
    markdown = pending_command_markdown(
        preview=preview,
        pending=pending,
        report_base_url=report_base_url,
    )
    content = (
        spreadsheet_rerun_pending_card(
            preview=preview,
            pending=pending,
            report_base_url=report_base_url,
        )
        if preview.action.kind == "spreadsheet_rerun"
        else pending_command_card(
            preview=preview,
            pending=pending,
            markdown=markdown,
            report_base_url=report_base_url,
        )
    )
    return turn_reply_payload(
        request=request,
        action_kind=preview.action.kind,
        markdown=markdown,
        message_type="interactive",
        content=content,
    )


def pending_command_continuation_reply_payload(
    *,
    request: XiaoDTurnHandleRequest,
    pending: PendingCommandView,
    report_base_url: str,
) -> LarkBotReplyPayload:
    markdown = pending_command_continuation_markdown(
        pending=pending,
        report_base_url=report_base_url,
    )
    return turn_reply_payload(
        request=request,
        action_kind="continue_pending_command",
        markdown=markdown,
        message_type="interactive",
        content=pending_command_continuation_card(
            pending=pending,
            markdown=markdown,
            report_base_url=report_base_url,
        ),
    )


def turn_reply_target_type(
    request: XiaoDTurnHandleRequest,
) -> Literal["message", "chat", "user", "none"]:
    if request.message_id:
        return "message"
    if request.chat_id:
        return "chat"
    if request.open_id:
        return "user"
    return "none"


def backend_command_markdown(
    *,
    preview: LarkBotCommandResponse,
    read_summary_lines: Sequence[str],
) -> str:
    lines = [f"**{preview.card.title}**"]
    if preview.card.summary:
        lines.append(preview.card.summary)
    lines.extend(read_summary_lines)
    if preview.card.fields:
        lines.append("")
        for field in preview.card.fields[:6]:
            label = field.get("label", "")
            value = field.get("value", "")
            if label or value:
                lines.append(f"- {label}: {value}")
    if preview.warnings:
        lines.append("")
        for warning in preview.warnings[:3]:
            lines.append(f"> {warning}")
    return "\n".join(lines)


def pending_command_markdown(
    *,
    preview: LarkBotCommandResponse,
    pending: PendingCommandView,
    report_base_url: str,
) -> str:
    if preview.action.kind == "spreadsheet_rerun":
        return spreadsheet_rerun_pending_markdown(
            preview=preview,
            pending=pending,
            report_base_url=report_base_url,
        )
    path = preview.action.path
    risk = preview.action.risk_level or "write"
    return "\n".join(
        [
            f"已生成待确认操作：{preview.card.title}。确认前不会执行。",
            "",
            f"你刚才要做的是：{preview.card.title}",
            f"原始消息：`{preview.audit.safe_command}`",
            f"风险级别：`{risk}`",
            f"待确认编号：`{pending.command_id}`",
            "",
            "原因：这个动作会创建或修改 Debug Agent 任务，属于写操作，必须先人工确认。",
            "下一步：请到 Debug Agent 操作台的“待确认机器人命令”里确认；确认前不会启动任务。",
            f"接口路径：`{path}`",
            f"操作台地址：{report_base_url.rstrip('/')}",
        ]
    )


def pending_command_card(
    *,
    preview: LarkBotCommandResponse,
    pending: PendingCommandView,
    markdown: str,
    report_base_url: str,
) -> dict[str, object]:
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "orange",
            "title": {"tag": "plain_text", "content": "Debug Agent 操作待确认"},
        },
        "elements": [
            {"tag": "markdown", "content": markdown},
            {
                "tag": "action",
                "actions": [
                    _confirm_pending_command_button(pending.command_id),
                    _cancel_pending_command_button(pending.command_id),
                    _open_console_button(report_base_url),
                ],
            },
        ],
    }


def pending_command_continuation_markdown(
    *,
    pending: PendingCommandView,
    report_base_url: str,
) -> str:
    lines = [
        "你还有一条未处理的小D待确认操作，我先不创建新的重复任务。",
        "",
        f"- 待确认编号：`{pending.command_id}`",
        f"- 操作：`{pending.action_kind}`",
        f"- 原始消息：`{pending.command_text or '未记录'}`",
        f"- 当前状态：`{pending.status}`",
    ]
    if pending.action_kind == "spreadsheet_rerun":
        lines.extend(_spreadsheet_rerun_pending_summary_lines(pending.action))
    lines.extend(
        [
            "",
            "你可以选择继续执行，或不继续后保留稍后处理/彻底删除。",
            f"操作台地址：{report_base_url.rstrip('/')}",
        ]
    )
    return "\n".join(lines)


def pending_command_continuation_card(
    *,
    pending: PendingCommandView,
    markdown: str,
    report_base_url: str,
) -> dict[str, object]:
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "orange",
            "title": {"tag": "plain_text", "content": "继续处理未执行任务？"},
        },
        "elements": [
            {"tag": "markdown", "content": markdown},
            {
                "tag": "action",
                "actions": [
                    _pending_lifecycle_button(
                        label="继续执行",
                        action="continue_pending_command",
                        command_id=pending.command_id,
                        style="primary",
                    ),
                    _pending_lifecycle_button(
                        label="不继续",
                        action="decline_pending_command",
                        command_id=pending.command_id,
                    ),
                    _pending_lifecycle_button(
                        label="保留稍后处理",
                        action="retain_pending_command",
                        command_id=pending.command_id,
                    ),
                    _pending_lifecycle_button(
                        label="彻底删除",
                        action="delete_pending_command",
                        command_id=pending.command_id,
                        style="danger",
                    ),
                    _open_console_button(report_base_url),
                ],
            },
        ],
    }


def spreadsheet_rerun_pending_markdown(
    *,
    preview: LarkBotCommandResponse,
    pending: PendingCommandView,
    report_base_url: str,
) -> str:
    parameters = preview.action.parameters
    source = _parameter_string(parameters, "source")
    sheet_id = _parameter_string(parameters, "sheet_id")
    row_ids = _parameter_string_list(parameters, "row_ids")
    case_ids = _parameter_string_list(parameters, "case_ids")
    selection = _spreadsheet_rerun_selection(row_ids=row_ids, case_ids=case_ids)
    lines = [
        f"已识别为表格批处理待确认：{selection}。确认前不会创建或启动 Debug 任务。",
        "",
        "我解析到的内容：",
        f"- 表格：{source or '未识别'}",
        f"- 工作表：`{sheet_id or '未识别'}`",
    ]
    if row_ids:
        lines.append(f"- 行选择：`{', '.join(row_ids)}`")
    if case_ids:
        lines.append(f"- Case ID：`{', '.join(case_ids)}`")
    output_summary = _spreadsheet_rerun_requested_output_summary(parameters)
    if output_summary:
        lines.append(f"- 执行目标：{output_summary}")
    lines.extend(_spreadsheet_rerun_preflight_markdown(parameters))
    lines.extend(
        [
            f"- 待确认编号：`{pending.command_id}`",
            "",
            "下一步：先核对预检结果；确认后只会为预检有效的行创建 Debug 任务。",
            f"操作台地址：{report_base_url.rstrip('/')}",
        ]
    )
    return "\n".join(lines)


def spreadsheet_rerun_pending_card(
    *,
    preview: LarkBotCommandResponse,
    pending: PendingCommandView,
    report_base_url: str,
) -> dict[str, object]:
    parameters = preview.action.parameters
    source = _parameter_string(parameters, "source")
    sheet_id = _parameter_string(parameters, "sheet_id")
    row_ids = _parameter_string_list(parameters, "row_ids")
    case_ids = _parameter_string_list(parameters, "case_ids")
    selection = _spreadsheet_rerun_selection(row_ids=row_ids, case_ids=case_ids)
    details = [
        f"**识别结果**：{selection}",
        f"**表格**：{source or '未识别'}",
        f"**工作表**：`{sheet_id or '未识别'}`",
        f"**待确认编号**：`{pending.command_id}`",
        "",
        "点击“确认创建任务”后才会创建批处理 Debug 任务；确认前不会执行。",
    ]
    if row_ids:
        details.insert(3, f"**行选择**：`{', '.join(row_ids)}`")
    if case_ids:
        details.insert(3, f"**Case ID**：`{', '.join(case_ids)}`")
    output_summary = _spreadsheet_rerun_requested_output_summary(parameters)
    if output_summary:
        details.insert(4, f"**执行目标**：{output_summary}")
    preflight_lines = _spreadsheet_rerun_preflight_card_lines(parameters)
    if preflight_lines:
        details.extend(["", *preflight_lines])
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "orange",
            "title": {"tag": "plain_text", "content": "表格批处理任务待确认"},
        },
        "elements": [
            {"tag": "markdown", "content": "\n".join(details)},
            {
                "tag": "action",
                "actions": [
                    _confirm_pending_command_button(pending.command_id),
                    _cancel_pending_command_button(pending.command_id),
                    _open_console_button(report_base_url),
                ],
            },
        ],
    }


def _pending_lifecycle_button(
    *,
    label: str,
    action: str,
    command_id: str,
    style: Literal["default", "primary", "danger"] = "default",
) -> dict[str, object]:
    value = {
        "action": action,
        "command_id": command_id,
    }
    return {
        "tag": "button",
        "text": {"tag": "plain_text", "content": label},
        "type": style,
        "value": value,
        "behaviors": [{"type": "callback", "value": value}],
    }


def _confirm_pending_command_button(command_id: str) -> dict[str, object]:
    value = {
        "action": "confirm_pending_command",
        "command_id": command_id,
    }
    return {
        "tag": "button",
        "text": {"tag": "plain_text", "content": "确认创建任务"},
        "type": "primary",
        "value": value,
        "behaviors": [{"type": "callback", "value": value}],
    }


def _cancel_pending_command_button(command_id: str) -> dict[str, object]:
    value = {
        "action": "cancel_pending_command",
        "command_id": command_id,
    }
    return {
        "tag": "button",
        "text": {"tag": "plain_text", "content": "取消"},
        "type": "danger",
        "value": value,
        "behaviors": [{"type": "callback", "value": value}],
    }


def _open_console_button(report_base_url: str) -> dict[str, object]:
    return {
        "tag": "button",
        "text": {"tag": "plain_text", "content": "打开操作台"},
        "type": "default",
        "url": report_base_url.rstrip("/"),
    }


def _spreadsheet_rerun_selection(*, row_ids: list[str], case_ids: list[str]) -> str:
    if row_ids:
        return f"第 {'、'.join(row_ids)} 行"
    if case_ids:
        return f"Case ID {'、'.join(case_ids)}"
    return "未指定行或 Case ID"


def _spreadsheet_rerun_requested_output_summary(parameters: dict[str, object]) -> str:
    targets = ["创建 Debug 任务"]
    if _parameter_bool(parameters, "report") or _parameter_bool(parameters, "auto_closure"):
        targets.append("生成自动闭环报告")
    if _parameter_bool(parameters, "writeback"):
        targets.append("完成后询问是否同步到飞书表格")
    return "、".join(targets) if len(targets) > 1 else ""


def _spreadsheet_rerun_pending_summary_lines(action: dict[str, object]) -> list[str]:
    parameters = action.get("parameters")
    if not isinstance(parameters, dict):
        return []
    source = _parameter_string(parameters, "source")
    sheet_id = _parameter_string(parameters, "sheet_id")
    row_ids = _parameter_string_list(parameters, "row_ids")
    case_ids = _parameter_string_list(parameters, "case_ids")
    lines = [
        f"- 表格：{source or '未识别'}",
        f"- 工作表：`{sheet_id or '未识别'}`",
    ]
    if row_ids:
        lines.append(f"- 行选择：`{', '.join(row_ids)}`")
    if case_ids:
        lines.append(f"- Case ID：`{', '.join(case_ids)}`")
    output_summary = _spreadsheet_rerun_requested_output_summary(parameters)
    if output_summary:
        lines.append(f"- 执行目标：{output_summary}")
    return lines


def _spreadsheet_rerun_preflight_markdown(parameters: dict[str, object]) -> list[str]:
    lines = _spreadsheet_rerun_preflight_card_lines(parameters)
    if not lines:
        return []
    return ["", "预检结果：", *[f"- {line}" for line in lines]]


def _spreadsheet_rerun_preflight_card_lines(parameters: dict[str, object]) -> list[str]:
    preflight = parameters.get("preflight")
    if not isinstance(preflight, dict):
        return []
    if preflight.get("status") != "ok":
        error = _parameter_string(preflight, "error") or "预检失败"
        return [f"**预检**：失败，{error}"]
    requested_count = _parameter_int(preflight, "requested_row_count")
    present_count = _parameter_int(preflight, "present_row_count")
    valid_count = _parameter_int(preflight, "valid_job_count")
    rejected_count = _parameter_int(preflight, "rejected_row_count")
    missing_count = _parameter_int(preflight, "missing_row_count")
    valid_row_ids = _parameter_string_list(preflight, "valid_row_ids")
    missing_row_ids = _parameter_string_list(preflight, "missing_row_ids")
    skipped_case_row_ids = _parameter_string_list(preflight, "skipped_case_row_ids")
    rejected_rows = preflight.get("rejected_rows")
    lines = [
        (
            f"**预检**：请求 {requested_count} 行，读到 {present_count} 行，"
            f"可创建 {valid_count} 个任务；无效 {rejected_count} 行，缺失 {missing_count} 行。"
        )
    ]
    if valid_row_ids:
        lines.append(f"**将创建任务的行**：`{', '.join(valid_row_ids)}`")
    if missing_row_ids:
        lines.append(f"**表格中未读到的行**：`{', '.join(missing_row_ids)}`")
    if skipped_case_row_ids:
        lines.append(f"**Case ID 过滤跳过行**：`{', '.join(skipped_case_row_ids)}`")
    if isinstance(rejected_rows, list) and rejected_rows:
        rejected_summaries = []
        for row in rejected_rows[:3]:
            if not isinstance(row, dict):
                continue
            row_id = _parameter_string(row, "row_id") or "未知行"
            error = _parameter_string(row, "error") or "解析失败"
            rejected_summaries.append(f"{row_id}: {error[:80]}")
        if rejected_summaries:
            lines.append(f"**无效行原因**：{'；'.join(rejected_summaries)}")
    return lines


def _parameter_string(parameters: dict[str, object], key: str) -> str:
    value = parameters.get(key)
    return value.strip() if isinstance(value, str) else ""


def _parameter_int(parameters: dict[str, object], key: str) -> int:
    value = parameters.get(key)
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return 0


def _parameter_bool(parameters: dict[str, object], key: str) -> bool:
    value = parameters.get(key)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _parameter_string_list(parameters: dict[str, object], key: str) -> list[str]:
    value = parameters.get(key)
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def help_markdown() -> str:
    return "\n".join(
        [
            "小D使用说明：Debug Agent 企业入口",
            "",
            "我连接的是 Debug Agent 整个企业级多模态调试平台，不是单独的 bot 壳。",
            "",
            "我应该能把飞书消息接到这些已有能力：",
            "- 数据接入：飞书表格/Base/文档/Wiki/云盘/妙记/幻灯片、图片、视频、JSONL、CSV。",
            "- 调试执行：创建单样本 DebugJob、批量 DebugBatch、查看任务/批次状态、worker 队列。",
            "- 证据报告：回推 run stages、evidence ledger、artifact、根因报告、推荐动作和报告链接。",
            "- 表格闭环：表格同步、表格行重跑、富文本附件下载、写回确认、写回审计。",
            "- Base 闭环：Base 记录来源、确认后写回 Base。",
            "- 治理闭环：推荐动作状态/验证任务、人工交接状态、策略跟进、定向探针、自动闭环报告。",
            "- Agent/模型：查看 Agent 拓扑、模型目录、不同角色模型路由和连接测试结果。",
            "- 运维观测：readiness、pilot gate、performance、Lark 权限清单、预检、go-live gate、操作审计、support bundle。",
            "",
            "你可以这样发：",
            "- 帮我调试这个表格：<飞书表格链接>，定位 JSZN-131",
            "- 原始输入：... 模型输出：... 正确答案：... 错误现象：...",
            "- 查看任务 <job_id> / 查看批次 <batch_id>",
            "- 这个任务的报告在哪里？",
            "- 表格写回怎么确认？",
            "- 验证推荐动作 <job_id> 0",
            "- 人工交接已解决 <job_id> <target_id>",
            "- 自动闭环报告 <job_id>",
            "- 当前 worker 和上线门禁怎么样？",
            "",
            "如果只发一个链接，我会交给后端识别来源并建草稿；后端需要更多调试语义时会追问，确认前不会创建任务。",
            "任务创建、批量调试、表格/Base 写回、推荐动作验证、人工交接更新和自动闭环等写操作必须二次确认。",
        ]
    )


def help_card(*, report_base_url: str) -> dict[str, object]:
    base_url = report_base_url.rstrip("/")
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"tag": "plain_text", "content": "小D Debug Agent 使用入口"},
        },
        "elements": [
            {
                "tag": "markdown",
                "content": "\n".join(
                    [
                        "**我能帮你把多模态 badcase 调试接到 Debug Agent 企业级闭环。**",
                        "- 适合对象：评测、算法、业务质量、平台运维和项目协作同学。",
                        "- 核心能力：飞书表格/Base/文档/附件接入，单样本或批量 Debug，证据链报告，默认安全写回决策。",
                        "- 使用方式：发 badcase 或表格链接，确认卡片后执行，完成后看报告，再决定同步或不同步。",
                        "- 安全边界：确认前不创建任务，默认不写回，证据不足不会伪造根因。",
                    ]
                ),
            },
            {
                "tag": "action",
                "actions": [
                    _xiaod_url_button(
                        "完整使用手册",
                        f"{base_url}/xiaod/views/manual",
                        style="primary",
                    ),
                    _xiaod_url_button(
                        "如何提交 badcase",
                        f"{base_url}/xiaod/views/manual#submit-badcase",
                    ),
                    _xiaod_url_button(
                        "表格重跑说明",
                        f"{base_url}/xiaod/views/manual#spreadsheet-rerun",
                    ),
                ],
            },
            {
                "tag": "action",
                "actions": [
                    _xiaod_url_button(
                        "报告怎么看",
                        f"{base_url}/xiaod/views/manual#report-reading",
                    ),
                    _xiaod_url_button(
                        "权限和上线",
                        f"{base_url}/xiaod/views/manual#operations",
                    ),
                    _xiaod_url_button(
                        "RAG知识库",
                        f"{base_url}/xiaod/views/manual#rag-learning",
                    ),
                ],
            },
        ],
    }


def _xiaod_url_button(label: str, url: str, *, style: str = "default") -> dict[str, object]:
    return {
        "tag": "button",
        "text": {"tag": "plain_text", "content": label},
        "type": style,
        "url": url,
    }


def clarify_intent_markdown(*, reason: str) -> str:
    if reason == "missing_context_for_report":
        title = "我没有定位到当前 Debug 任务，所以还不能直接给报告。"
    elif reason == "missing_context_for_result":
        title = "我没有定位到当前 Debug 任务，所以还不能判断这个结论是否可靠。"
    elif reason == "missing_context_for_writeback":
        title = "我没有定位到当前 Debug 任务，所以还不能判断是否已经写回。"
    elif reason == "missing_context_for_continue":
        title = "我还不知道你想继续哪一条任务或草稿。"
    else:
        title = "这句话里有上下文指代，但我没有定位到对应的任务或草稿。"
    return "\n".join(
        [
            title,
            "",
            "你可以这样继续：",
            "- 回复：最近任务",
            "- 发具体任务编号，例如：查看报告 <job_id>",
            "- 如果是新问题，直接发飞书表格/Base/文档链接或 badcase 详情。",
            "",
            "我不会在没有定位对象时猜测执行动作。",
        ]
    )


def badcase_draft_status_markdown(*, draft: BadcaseDraftView) -> str:
    return badcase_draft_markdown(
        draft=draft,
        intro="这是当前 badcase 草稿进度，我会接着这条草稿往下推进。",
    )


def badcase_draft_saved_markdown(*, draft: BadcaseDraftView) -> str:
    return badcase_draft_markdown(
        draft=draft,
        intro="我已把这条信息记录为 badcase 草稿。",
    )


def badcase_draft_markdown(*, draft: BadcaseDraftView, intro: str) -> str:
    missing_fields = [str(item) for item in draft.missing_fields]
    lines = [
        intro,
        "",
        f"草稿编号：`{draft.draft_id}`",
        f"当前状态：`{draft.status}`",
    ]
    context_lines = badcase_link_context_markdown_lines(draft=draft)
    if context_lines:
        lines.extend(["", "已识别的输入来源：", *context_lines])
    if missing_fields:
        lines.extend(
            [
                "",
                "后端还需要更多调试语义，补齐前我不会创建调试任务：",
                *[f"- {badcase_field_label(field)}" for field in missing_fields],
                "",
                "你可以直接继续发自然语言补充，例如：",
                "模型输出：xxx",
                "正确答案：yyy",
                "错误现象：把 8 识别成 3",
            ]
        )
        return "\n".join(lines)
    lines.extend(
        [
            "",
            "后端已整理出可提交的调试任务，可以确认提交。",
            "",
            f"- 原始输入：{draft.input_source}",
            f"- 模型输出：{draft.model_output}",
            f"- 期望结果：{draft.expected_output}",
            f"- 错误现象：{draft.issue_summary}",
            "",
            "如果确认无误，请回复：确认提交",
            "确认前不会创建任务。",
        ]
    )
    return "\n".join(lines)


def badcase_confirmed_markdown(*, response: BadcaseConfirmResponseView) -> str:
    draft = response.draft
    job = response.submitted_job
    lines = [
        "已确认提交，Debug 任务已经创建。",
        "",
        f"草稿编号：`{draft.draft_id}`",
        f"样本追踪号：`{draft.submitted_case_id}`",
    ]
    if job is not None:
        lines.extend([f"任务编号：`{job.job_id}`", f"任务状态：`{job.status}`"])
    if draft.submitted_job_id and (job is None or job.job_id != draft.submitted_job_id):
        lines.append(f"任务编号：`{draft.submitted_job_id}`")
    lines.extend(
        [
            "",
            "我会继续等后端 worker 完成任务；完成后会把摘要、报告链接和写回确认入口发回这里。",
        ]
    )
    return "\n".join(lines)


def badcase_cancelled_markdown(*, draft: BadcaseDraftView) -> str:
    return "\n".join(
        [
            "已取消这条 badcase 草稿。",
            "",
            f"草稿编号：`{draft.draft_id}`",
            f"当前状态：`{draft.status}`",
        ]
    )


def badcase_link_context_markdown_lines(*, draft: BadcaseDraftView) -> list[str]:
    lines: list[str] = []
    for attachment in draft.attachments:
        if not isinstance(attachment, dict) or attachment.get("type") != "link_context":
            continue
        resource = _object_string(attachment, "resource") or _object_string(attachment, "link_type")
        status = _object_string(attachment, "status")
        selected_row = _object_string(attachment, "selected_row")
        summary = f"- {resource}" if resource else "- link"
        if selected_row:
            summary += f" / 行 {selected_row}"
        if status:
            summary += f" / {badcase_link_status_label(status)}"
        media_input = attachment.get("media_input")
        if isinstance(media_input, dict):
            media_status = _object_string(media_input, "status")
            if media_status:
                summary += f"\n  媒体附件：{badcase_link_status_label(media_status)}"
        next_action = _object_string(attachment, "next_action")
        if next_action:
            summary += f"\n  下一步：{next_action}"
        lines.append(summary)
    return lines


def badcase_link_status_label(status: str) -> str:
    labels = {
        "metadata_only": "已识别链接",
        "content_resolved": "已读取内容",
        "downloaded": "已下载",
        "download_failed": "下载失败",
        "missing_attachment": "缺少附件",
        "reader_not_supported": "读取器未接入",
        "read_failed": "读取失败",
        "needs_locator": "需要定位行/记录",
        "spreadsheet_row_rejected": "表格行缺字段",
        "rejected": "表格行缺字段",
        "imported": "已按导入协议解析",
        "resolved_local": "已解析本地文件",
    }
    return labels.get(status, status)


def badcase_field_label(field: str) -> str:
    labels = {
        "input_source": "原始输入（图片、视频、文件、链接或样本文本）",
        "model_output": "模型输出",
        "expected_output": "期望结果/正确答案",
        "issue_summary": "错误现象",
        "case_id": "表格列：case_id / id / 样本ID",
        "prompt": "表格列：prompt / user prompt / 模型输入",
        "expected_output_json": "表格列：expected_output_json / 参考答案",
        "predictions_json": "表格列：predictions_json / predict",
        "scoring_standard": "表格列：scoring_standard / 评分标准，或 chains_alpha",
        "image_uri": "表格列：image_uri / video / 图片链接",
    }
    return labels.get(field, field)


def _object_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    return value.strip() if isinstance(value, str) else ""
