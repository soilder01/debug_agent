from __future__ import annotations

from debug_agent.lark.connector import LarkConnectorStatus
from debug_agent.lark.schemas import (
    CONTROLLED_PROBE_OPTION_TOKENS,
    LarkBotAuditContext,
    LarkBotCard,
    LarkBotCardButton,
    LarkBotCommandAction,
    LarkBotCommandRequest,
    LarkBotCommandResponse,
    SPREADSHEET_RERUN_WRITEBACK_OPTION_TOKENS,
)

STATIC_READ_COMMANDS: dict[str, tuple[str, str]] = {
    **dict.fromkeys(
        ["status", "状态", "readiness", "ready", "就绪"], ("readiness", "/api/operations/readiness")
    ),
    **dict.fromkeys(
        ["pilot", "pilot-gate", "gate", "准入", "试点"],
        ("pilot_gate", "/api/operations/pilot-gate"),
    ),
    **dict.fromkeys(
        ["observability", "observe", "观测", "观测摘要", "总览"],
        ("observability_summary", "/api/observability/summary"),
    ),
    **dict.fromkeys(
        ["artifact-retention", "artifacts", "产物", "产物保留", "产物清理"],
        ("artifact_retention", "/api/operations/artifact-retention"),
    ),
    **dict.fromkeys(
        ["cases", "case-list", "样本列表", "case列表", "样本清单"], ("case_list", "/cases?limit=10")
    ),
    **dict.fromkeys(
        ["models", "model", "模型", "模型目录", "agent-models", "agents"],
        ("model_catalog", "/agent-models"),
    ),
    **dict.fromkeys(
        ["performance", "perf", "性能", "p95"], ("performance_summary", "/api/performance/summary")
    ),
    **dict.fromkeys(
        ["preflight", "预检", "bot预检", "机器人预检"],
        ("lark_preflight", "/api/lark/bot/preflight"),
    ),
    **dict.fromkeys(
        ["go-live", "golive", "上线门禁", "真实上线"],
        ("lark_go_live_gate", "/api/lark/bot/go-live-gate"),
    ),
    **dict.fromkeys(
        ["permissions", "permission", "scopes", "scope", "权限", "权限清单"],
        ("lark_permission_checklist", "/api/lark/bot/permission-checklist"),
    ),
    **dict.fromkeys(
        ["scope-check", "scope-checks", "scope检查", "权限检查"],
        ("lark_scope_check", "/api/lark/scopes/check"),
    ),
    **dict.fromkeys(
        ["sheet-status", "spreadsheet-status", "表格连接", "表格状态"],
        ("lark_spreadsheet_status", "/spreadsheets/lark/status"),
    ),
    **dict.fromkeys(
        ["audits", "audit", "操作审计", "lark审计"],
        ("lark_operation_audits", "/api/lark/operation-audits?limit=10"),
    ),
    **dict.fromkeys(
        ["drafts", "草稿", "badcase草稿"],
        ("badcase_drafts", "/api/lark/bot/badcase-drafts?limit=10"),
    ),
    **dict.fromkeys(
        ["pending", "pending-commands", "待确认", "待确认命令"],
        ("pending_commands", "/api/lark/bot/commands/pending?limit=10"),
    ),
    **dict.fromkeys(
        ["export", "debug-export", "任务导出", "导出任务"],
        ("debug_jobs_export", "/api/exports/debug-jobs.zip"),
    ),
    **dict.fromkeys(
        ["support-bundle", "support", "支持包", "运维支持包"],
        ("support_bundle", "/api/operations/support-bundle.zip"),
    ),
    **dict.fromkeys(
        ["database-backup", "db-backup", "数据库备份"],
        ("database_backup", "/api/operations/database-backup.zip"),
    ),
    **dict.fromkeys(
        ["jobs", "job-list", "任务列表", "任务清单"],
        ("job_list", "/jobs?limit=10&sort=created_at_desc"),
    ),
    **dict.fromkeys(
        ["batch-comparison", "batch-compare", "批次对比", "ab", "a/b"],
        ("batch_comparison", "/api/debug-batches/comparison"),
    ),
}


def build_lark_bot_command_response(
    request: LarkBotCommandRequest,
    *,
    actor: str,
    connector_status: LarkConnectorStatus,
    default_profile: str = "",
) -> LarkBotCommandResponse:
    action = parse_lark_bot_command(request.text)
    profile = request.profile.strip() or default_profile
    audit = LarkBotAuditContext(
        actor=actor,
        open_id=request.open_id.strip(),
        chat_id=request.chat_id.strip(),
        message_id=request.message_id.strip(),
        tenant_key=request.tenant_key.strip(),
        identity=request.identity,
        profile=profile,
        safe_command=_safe_command_text(request.text),
    )
    return LarkBotCommandResponse(
        action=action,
        card=_card_for_action(action),
        audit=audit,
        connector=connector_status,
        warnings=_warnings_for_action(action),
    )


def parse_lark_bot_command(text: str) -> LarkBotCommandAction:
    tokens = _command_tokens(text)
    if not tokens or tokens[0] in {"help", "帮助", "?"}:
        return _help_action()

    command = tokens[0]
    static_action = _static_read_action(command)
    if static_action is not None:
        return static_action

    if command in {"worker", "队列", "后台进程"}:
        if len(tokens) >= 2 and tokens[1] in {"start", "启动"}:
            return LarkBotCommandAction(
                kind="worker_start",
                method="POST",
                path="/worker/start",
                side_effect=True,
                confirmation_required=True,
                risk_level="write",
            )
        if len(tokens) >= 2 and tokens[1] in {"stop", "停止"}:
            return LarkBotCommandAction(
                kind="worker_stop",
                method="POST",
                path="/worker/stop",
                side_effect=True,
                confirmation_required=True,
                risk_level="write",
            )
        return LarkBotCommandAction(
            kind="worker_status",
            method="GET",
            path="/worker/status",
            risk_level="read",
        )
    if command in {"writeback", "写回"} and len(tokens) >= 2:
        job_id = tokens[1]
        return LarkBotCommandAction(
            kind="spreadsheet_writeback_confirmation",
            method="POST",
            path=f"/api/jobs/{job_id}/spreadsheet-writeback/confirmation",
            side_effect=True,
            confirmation_required=True,
            risk_level="write",
            parameters={"job_id": job_id},
        )
    if command in {"base-writeback", "base写回"} and len(tokens) >= 2:
        job_id = tokens[1]
        return LarkBotCommandAction(
            kind="base_writeback_confirmation",
            method="POST",
            path=f"/api/jobs/{job_id}/base-writeback/confirmation",
            side_effect=True,
            confirmation_required=True,
            risk_level="write",
            parameters={"job_id": job_id},
        )
    if command in {"writebacks", "writeback", "写回", "写回审计"}:
        return LarkBotCommandAction(
            kind="writeback_audits",
            method="GET",
            path="/spreadsheets/writeback/audits/summary",
            risk_level="read",
        )
    if command in {"export", "debug-export", "任务导出", "导出任务"}:
        return LarkBotCommandAction(
            kind="debug_jobs_export",
            method="GET",
            path="/api/exports/debug-jobs.zip",
            risk_level="read",
        )
    if command in {"support-bundle", "support", "支持包", "运维支持包"}:
        return LarkBotCommandAction(
            kind="support_bundle",
            method="GET",
            path="/api/operations/support-bundle.zip",
            risk_level="read",
        )
    if command in {"database-backup", "db-backup", "数据库备份"}:
        return LarkBotCommandAction(
            kind="database_backup",
            method="GET",
            path="/api/operations/database-backup.zip",
            risk_level="read",
        )
    if command in {"jobs", "job-list", "任务列表", "任务清单"}:
        return LarkBotCommandAction(
            kind="job_list",
            method="GET",
            path="/jobs?limit=10&sort=created_at_desc",
            risk_level="read",
        )
    job_read_action = _job_read_action(command, tokens)
    if job_read_action is not None:
        return job_read_action
    workflow_action = _workflow_action(command, tokens)
    if workflow_action is not None:
        return workflow_action
    batch_or_submit_action = _batch_spreadsheet_or_submit_action(command, tokens)
    if batch_or_submit_action is not None:
        return batch_or_submit_action
    return LarkBotCommandAction(kind="unknown", method="NONE")


def _job_read_action(command: str, tokens: list[str]) -> LarkBotCommandAction | None:
    if command in {"job", "任务"} and len(tokens) >= 2:
        job_id = tokens[1]
        return LarkBotCommandAction(
            kind="job_status",
            method="GET",
            path=f"/api/jobs/{job_id}",
            risk_level="read",
            parameters={"job_id": job_id},
        )
    if command in {"report", "报告"} and len(tokens) >= 2:
        job_id = tokens[1]
        return LarkBotCommandAction(
            kind="job_report",
            method="GET",
            path=f"/jobs/{job_id}/report",
            risk_level="read",
            parameters={"job_id": job_id},
        )
    if command in {"evidence", "证据"} and len(tokens) >= 2:
        job_id = tokens[1]
        return LarkBotCommandAction(
            kind="job_evidence",
            method="GET",
            path=f"/jobs/{job_id}/evidence-ledger",
            risk_level="read",
            parameters={"job_id": job_id},
        )
    if command in {"stages", "阶段", "运行阶段"} and len(tokens) >= 2:
        job_id = tokens[1]
        return LarkBotCommandAction(
            kind="job_run_stages",
            method="GET",
            path=f"/jobs/{job_id}/run-stages",
            risk_level="read",
            parameters={"job_id": job_id},
        )
    return None


def _workflow_action(command: str, tokens: list[str]) -> LarkBotCommandAction | None:
    if (
        command in {"recommended-actions", "recommended", "推荐动作", "推荐动作状态"}
        and len(tokens) >= 2
    ):
        if len(tokens) >= 5 and tokens[1] in {"status", "update", "set", "标记", "更新"}:
            action_index = _int_token(tokens[3])
            status = _recommended_action_status(tokens[4])
            if action_index is not None and status:
                job_id = tokens[2]
                return LarkBotCommandAction(
                    kind="recommended_action_status_update",
                    method="PATCH",
                    path=f"/jobs/{job_id}/recommended-actions/{action_index}/status",
                    side_effect=True,
                    confirmation_required=True,
                    risk_level="write",
                    parameters={
                        "job_id": job_id,
                        "action_index": action_index,
                        "status": status,
                        "note": " ".join(tokens[5:]),
                    },
                )
        if len(tokens) >= 4 and tokens[1] in {"verify", "verification", "验证", "复验"}:
            action_index = _int_token(tokens[3])
            if action_index is not None:
                job_id = tokens[2]
                return LarkBotCommandAction(
                    kind="recommended_action_verification",
                    method="POST",
                    path=f"/jobs/{job_id}/recommended-actions/{action_index}/verification-jobs",
                    side_effect=True,
                    confirmation_required=True,
                    risk_level="write",
                    parameters={
                        "job_id": job_id,
                        "action_index": action_index,
                        "note": " ".join(tokens[4:]),
                    },
                )
        job_id = tokens[1]
        return LarkBotCommandAction(
            kind="recommended_action_statuses",
            method="GET",
            path=f"/jobs/{job_id}/recommended-actions/statuses",
            risk_level="read",
            parameters={"job_id": job_id},
        )
    if command in {"recommended-action-status", "推荐动作标记"} and len(tokens) >= 4:
        action_index = _int_token(tokens[2])
        status = _recommended_action_status(tokens[3])
        if action_index is not None and status:
            job_id = tokens[1]
            return LarkBotCommandAction(
                kind="recommended_action_status_update",
                method="PATCH",
                path=f"/jobs/{job_id}/recommended-actions/{action_index}/status",
                side_effect=True,
                confirmation_required=True,
                risk_level="write",
                parameters={
                    "job_id": job_id,
                    "action_index": action_index,
                    "status": status,
                    "note": " ".join(tokens[4:]),
                },
            )
    if command in {"recommended-action-verify", "推荐动作验证"} and len(tokens) >= 3:
        action_index = _int_token(tokens[2])
        if action_index is not None:
            job_id = tokens[1]
            return LarkBotCommandAction(
                kind="recommended_action_verification",
                method="POST",
                path=f"/jobs/{job_id}/recommended-actions/{action_index}/verification-jobs",
                side_effect=True,
                confirmation_required=True,
                risk_level="write",
                parameters={
                    "job_id": job_id,
                    "action_index": action_index,
                    "note": " ".join(tokens[3:]),
                },
            )
    if command in {"human-handoffs", "handoffs", "人工交接", "人类交接"} and len(tokens) >= 2:
        if len(tokens) >= 5 and tokens[1] in {"status", "update", "set", "标记", "更新"}:
            status = _human_handoff_status(tokens[4])
            if status:
                job_id = tokens[2]
                target_id = tokens[3]
                return LarkBotCommandAction(
                    kind="human_handoff_status_update",
                    method="PATCH",
                    path=f"/jobs/{job_id}/human-handoffs/{target_id}/status",
                    side_effect=True,
                    confirmation_required=True,
                    risk_level="write",
                    parameters={
                        "job_id": job_id,
                        "target_id": target_id,
                        "status": status,
                        "note": " ".join(tokens[5:]),
                    },
                )
        job_id = tokens[1]
        return LarkBotCommandAction(
            kind="human_handoff_statuses",
            method="GET",
            path=f"/jobs/{job_id}/human-handoffs/statuses",
            risk_level="read",
            parameters={"job_id": job_id},
        )
    if command in {"human-handoff-status", "人工交接标记"} and len(tokens) >= 4:
        status = _human_handoff_status(tokens[3])
        if status:
            job_id = tokens[1]
            target_id = tokens[2]
            return LarkBotCommandAction(
                kind="human_handoff_status_update",
                method="PATCH",
                path=f"/jobs/{job_id}/human-handoffs/{target_id}/status",
                side_effect=True,
                confirmation_required=True,
                risk_level="write",
                parameters={
                    "job_id": job_id,
                    "target_id": target_id,
                    "status": status,
                    "note": " ".join(tokens[4:]),
                },
            )
    if (
        command in {"strategy-followups", "strategy-follow-ups", "策略跟进", "跟进实验"}
        and len(tokens) >= 2
    ):
        if len(tokens) >= 4 and tokens[1] in {"run", "create", "submit", "创建", "提交", "执行"}:
            job_id = tokens[2]
            stage = tokens[3]
            return LarkBotCommandAction(
                kind="strategy_followup_job",
                method="POST",
                path=f"/jobs/{job_id}/strategy-follow-ups/{stage}/debug-jobs",
                side_effect=True,
                confirmation_required=True,
                risk_level="write",
                parameters={"job_id": job_id, "stage": stage, "note": " ".join(tokens[4:])},
            )
        job_id = tokens[1]
        return LarkBotCommandAction(
            kind="strategy_followups",
            method="GET",
            path=f"/jobs/{job_id}/strategy-follow-ups",
            risk_level="read",
            parameters={"job_id": job_id},
        )
    if command in {"strategy-followup-job", "策略跟进任务"} and len(tokens) >= 3:
        job_id = tokens[1]
        stage = tokens[2]
        return LarkBotCommandAction(
            kind="strategy_followup_job",
            method="POST",
            path=f"/jobs/{job_id}/strategy-follow-ups/{stage}/debug-jobs",
            side_effect=True,
            confirmation_required=True,
            risk_level="write",
            parameters={"job_id": job_id, "stage": stage, "note": " ".join(tokens[3:])},
        )
    if command in {"targeted-probes", "targeted", "定向探针", "探针"} and len(tokens) >= 2:
        if len(tokens) >= 4 and tokens[1] in {"run", "create", "submit", "创建", "提交", "执行"}:
            job_id = tokens[2]
            target_id = tokens[3]
            return LarkBotCommandAction(
                kind="targeted_probe_job",
                method="POST",
                path=f"/jobs/{job_id}/targeted-probes/{target_id}/debug-jobs",
                side_effect=True,
                confirmation_required=True,
                risk_level="write",
                parameters={"job_id": job_id, "target_id": target_id, "note": " ".join(tokens[4:])},
            )
        job_id = tokens[1]
        return LarkBotCommandAction(
            kind="targeted_probes",
            method="GET",
            path=f"/jobs/{job_id}/targeted-probes",
            risk_level="read",
            parameters={"job_id": job_id},
        )
    if command in {"targeted-probe-job", "定向探针任务"} and len(tokens) >= 3:
        job_id = tokens[1]
        target_id = tokens[2]
        return LarkBotCommandAction(
            kind="targeted_probe_job",
            method="POST",
            path=f"/jobs/{job_id}/targeted-probes/{target_id}/debug-jobs",
            side_effect=True,
            confirmation_required=True,
            risk_level="write",
            parameters={"job_id": job_id, "target_id": target_id, "note": " ".join(tokens[3:])},
        )
    if command in {"auto-closure", "auto-debug-closure", "自动闭环"} and len(tokens) >= 2:
        job_id = tokens[1]
        option_tokens = tokens[2:]
        return LarkBotCommandAction(
            kind="auto_closure",
            method="POST",
            path=f"/jobs/{job_id}/auto-closure",
            side_effect=True,
            confirmation_required=True,
            risk_level="write",
            parameters={
                "job_id": job_id,
                "writeback": _has_flag(option_tokens, {"--writeback", "writeback", "写回"}),
                "submit_controlled_probes": _has_flag(
                    option_tokens, CONTROLLED_PROBE_OPTION_TOKENS
                ),
                "report_url": _first_url(option_tokens),
                "note": " ".join(
                    token
                    for token in option_tokens
                    if not token.startswith("--") and not token.startswith("http")
                ),
            },
        )
    if (
        command in {"auto-closure-report", "auto-debug-closure-report", "闭环报告", "自动闭环报告"}
        and len(tokens) >= 2
    ):
        job_id = tokens[1]
        option_tokens = tokens[2:]
        return LarkBotCommandAction(
            kind="auto_closure_report",
            method="POST",
            path=f"/jobs/{job_id}/auto-closure/report",
            side_effect=True,
            confirmation_required=True,
            risk_level="write",
            parameters={
                "job_id": job_id,
                "writeback": _has_flag(option_tokens, {"--writeback", "writeback", "写回"}),
                "submit_controlled_probes": _has_flag(
                    option_tokens, CONTROLLED_PROBE_OPTION_TOKENS
                ),
                "report_url": _first_url(option_tokens),
                "note": " ".join(
                    token
                    for token in option_tokens
                    if not token.startswith("--") and not token.startswith("http")
                ),
            },
        )
    return None


def _batch_spreadsheet_or_submit_action(
    command: str, tokens: list[str]
) -> LarkBotCommandAction | None:
    if command in {"batches", "batch-list", "批次列表", "批次清单"} or (
        command in {"batch", "批次"} and len(tokens) == 1
    ):
        return LarkBotCommandAction(
            kind="batch_list",
            method="GET",
            path="/debug-batches?limit=10",
            risk_level="read",
        )
    if command in {"spreadsheet", "sheet", "表格"} and len(tokens) >= 3:
        operation = tokens[1]
        source = tokens[2]
        sheet_id = tokens[3] if len(tokens) >= 4 else ""
        if operation in {"sync", "同步"}:
            return LarkBotCommandAction(
                kind="spreadsheet_sync",
                method="POST",
                path="/spreadsheets/sync",
                side_effect=True,
                confirmation_required=True,
                risk_level="write",
                parameters={"source": source, "sheet_id": sheet_id, "create_jobs": True},
            )
        if operation in {"rerun", "重跑"}:
            selector = tokens[4] if len(tokens) >= 5 else ""
            option_tokens = tokens[5:] if len(tokens) >= 6 else []
            case_ids = (
                _csv_tokens(selector.split(":", 1)[1])
                if selector.startswith(("case:", "cases:", "id:", "ids:"))
                else []
            )
            row_ids = [] if case_ids else _csv_tokens(selector)
            report_requested = _has_flag(
                option_tokens,
                {"--report", "report", "报告", "返回报告", "生成报告"},
            )
            writeback_requested = _has_flag(
                option_tokens,
                SPREADSHEET_RERUN_WRITEBACK_OPTION_TOKENS,
            )
            submit_controlled_probes = _has_flag(
                option_tokens,
                CONTROLLED_PROBE_OPTION_TOKENS,
            )
            return LarkBotCommandAction(
                kind="spreadsheet_rerun",
                method="POST",
                path="/spreadsheets/rerun",
                side_effect=True,
                confirmation_required=True,
                risk_level="write",
                parameters={
                    "source": source,
                    "sheet_id": sheet_id,
                    "row_ids": row_ids,
                    "case_ids": case_ids,
                    "auto_closure": report_requested
                    or writeback_requested
                    or submit_controlled_probes,
                    "report": report_requested or writeback_requested or submit_controlled_probes,
                    "submit_controlled_probes": submit_controlled_probes,
                    "writeback": writeback_requested,
                },
            )
    if command in {"batch", "批次"} and len(tokens) >= 2 and tokens[1] not in {"run", "提交"}:
        if len(tokens) >= 3 and tokens[1] in {"pause", "暂停"}:
            batch_id = tokens[2]
            return LarkBotCommandAction(
                kind="batch_pause",
                method="POST",
                path=f"/debug-batches/{batch_id}/pause",
                side_effect=True,
                confirmation_required=True,
                risk_level="write",
                parameters={"batch_id": batch_id},
            )
        if len(tokens) >= 3 and tokens[1] in {"resume", "恢复"}:
            batch_id = tokens[2]
            return LarkBotCommandAction(
                kind="batch_resume",
                method="POST",
                path=f"/debug-batches/{batch_id}/resume",
                side_effect=True,
                confirmation_required=True,
                risk_level="write",
                parameters={"batch_id": batch_id},
            )
        if len(tokens) >= 3 and tokens[1] in {"cancel", "取消"}:
            batch_id = tokens[2]
            return LarkBotCommandAction(
                kind="batch_cancel",
                method="POST",
                path=f"/debug-batches/{batch_id}/cancel",
                side_effect=True,
                confirmation_required=True,
                risk_level="write",
                parameters={"batch_id": batch_id},
            )
        batch_id = tokens[1]
        return LarkBotCommandAction(
            kind="batch_status",
            method="GET",
            path=f"/api/debug-batches/{batch_id}",
            risk_level="read",
            parameters={"batch_id": batch_id},
        )
    if command in {"run", "debug", "调试"} and len(tokens) >= 2:
        case_id = tokens[2] if len(tokens) >= 3 and tokens[1] in {"case", "样本"} else tokens[1]
        return LarkBotCommandAction(
            kind="submit_case",
            method="POST",
            path=f"/api/cases/{case_id}/debug-jobs",
            side_effect=True,
            confirmation_required=True,
            risk_level="write",
            parameters={"case_id": case_id},
        )
    if command in {"batch-run", "批量调试"} or (
        command in {"batch", "批次"} and len(tokens) >= 3 and tokens[1] in {"run", "提交"}
    ):
        raw_case_ids = tokens[1] if command in {"batch-run", "批量调试"} else tokens[2]
        case_ids = [item.strip() for item in raw_case_ids.split(",") if item.strip()]
        return LarkBotCommandAction(
            kind="submit_batch",
            method="POST",
            path="/api/debug-jobs/batch",
            side_effect=True,
            confirmation_required=True,
            risk_level="write",
            parameters={"case_ids": case_ids},
        )
    return None


def _static_read_action(command: str) -> LarkBotCommandAction | None:
    action = STATIC_READ_COMMANDS.get(command)
    if action is None:
        return None
    kind, path = action
    return LarkBotCommandAction(kind=kind, method="GET", path=path, risk_level="read")


def _command_tokens(text: str) -> list[str]:
    normalized = " ".join(text.strip().split())
    if not normalized:
        return []
    tokens = normalized.split(" ")
    if tokens[0].lower() in {"/debug", "debug-agent", "@debug-agent"}:
        tokens = tokens[1:]
    return [token.strip() for token in tokens if token.strip()]


def _csv_tokens(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _int_token(value: str) -> int | None:
    if value.isdigit():
        return int(value)
    return None


def _recommended_action_status(value: str) -> str:
    aliases = {
        "pending": "pending",
        "待处理": "pending",
        "accepted": "accepted",
        "accept": "accepted",
        "接受": "accepted",
        "采纳": "accepted",
        "rejected": "rejected",
        "reject": "rejected",
        "拒绝": "rejected",
        "驳回": "rejected",
        "applied": "applied",
        "apply": "applied",
        "已应用": "applied",
        "应用": "applied",
    }
    return aliases.get(value.lower(), "")


def _human_handoff_status(value: str) -> str:
    aliases = {
        "pending": "pending",
        "待处理": "pending",
        "acknowledged": "acknowledged",
        "ack": "acknowledged",
        "已确认": "acknowledged",
        "确认": "acknowledged",
        "in_progress": "in_progress",
        "in-progress": "in_progress",
        "处理中": "in_progress",
        "处理": "in_progress",
        "resolved": "resolved",
        "resolve": "resolved",
        "已解决": "resolved",
        "解决": "resolved",
        "wont_fix": "wont_fix",
        "wont-fix": "wont_fix",
        "不修复": "wont_fix",
        "不处理": "wont_fix",
    }
    return aliases.get(value.lower(), "")


def _has_flag(tokens: list[str], names: set[str]) -> bool:
    return any(token.lower() in names for token in tokens)


def _first_url(tokens: list[str]) -> str:
    for token in tokens:
        if token.startswith(("http://", "https://")):
            return token
    return ""


def _help_action() -> LarkBotCommandAction:
    return LarkBotCommandAction(kind="help", method="NONE")


def _card_for_action(action: LarkBotCommandAction) -> LarkBotCard:
    if action.kind == "help":
        return LarkBotCard(
            title="Debug Agent 机器人帮助",
            summary="你可以直接用自然语言问小D；涉及创建任务的写操作会先进入待确认，不会自动执行。",
            fields=[
                {"label": "查看状态", "value": "查看生产运行就绪"},
                {"label": "试点准入", "value": "查看试点准入"},
                {"label": "查看任务 <job_id>", "value": "查看任务状态"},
                {"label": "查看批次 <batch_id>", "value": "查看批次状态"},
                {"label": "帮我调试这个识别错误", "value": "小D会先说明需要哪些 badcase 信息"},
                {
                    "label": "已导入样本",
                    "value": "请在操作台选择样本后启动调试；管理员可用精确命令",
                },
            ],
        )
    if action.kind == "unknown":
        return LarkBotCard(
            title="无法识别的 Debug Agent 命令",
            status="warning",
            summary="请发送 /debug help 查看支持的命令。",
            buttons=[LarkBotCardButton(label="查看帮助", method="NONE")],
        )
    title_map = {
        "readiness": "生产运行就绪",
        "pilot_gate": "试点准入评估",
        "worker_status": "Worker 队列状态",
        "worker_start": "启动 Worker",
        "worker_stop": "停止 Worker",
        "performance_summary": "性能摘要",
        "model_catalog": "Agent 模型目录",
        "lark_preflight": "机器人上线预检",
        "lark_go_live_gate": "机器人真实上线门禁",
        "lark_permission_checklist": "Lark 权限清单",
        "lark_operation_audits": "Lark 操作审计",
        "badcase_drafts": "飞书 badcase 草稿",
        "pending_commands": "待确认机器人命令",
        "writeback_audits": "表格写回审计",
        "observability_summary": "观测总览",
        "artifact_retention": "产物保留状态",
        "case_list": "样本列表",
        "lark_spreadsheet_status": "飞书表格连接状态",
        "lark_scope_check": "Lark Scope 检查",
        "debug_jobs_export": "DebugJob 导出包",
        "support_bundle": "运维支持包",
        "database_backup": "数据库备份包",
        "job_list": "任务列表",
        "job_status": "任务状态",
        "job_report": "任务报告",
        "job_evidence": "任务证据账本",
        "job_run_stages": "任务运行阶段",
        "recommended_action_statuses": "推荐动作状态",
        "recommended_action_status_update": "更新推荐动作状态",
        "recommended_action_verification": "创建推荐动作验证任务",
        "human_handoff_statuses": "人工交接状态",
        "human_handoff_status_update": "更新人工交接状态",
        "strategy_followups": "策略跟进任务",
        "strategy_followup_job": "创建策略跟进任务",
        "targeted_probes": "定向探针任务",
        "targeted_probe_job": "创建定向探针任务",
        "auto_closure": "运行自动闭环",
        "auto_closure_report": "生成自动闭环报告",
        "batch_list": "批次列表",
        "batch_comparison": "批次对比",
        "batch_status": "批次状态",
        "batch_pause": "暂停批次",
        "batch_resume": "恢复批次",
        "batch_cancel": "取消批次",
        "submit_case": "提交单样本调试",
        "submit_batch": "提交批量调试",
        "spreadsheet_sync": "同步飞书表格",
        "spreadsheet_rerun": "重跑飞书表格行",
        "spreadsheet_writeback_confirmation": "创建表格写回确认",
        "base_writeback_confirmation": "创建 Base 写回确认",
    }
    status = "warning" if action.confirmation_required else "info"
    summary = (
        "该操作会修改 Debug Agent 状态、创建调试任务或触发闭环流程，必须由操作者二次确认后才能执行。"
        if action.confirmation_required
        else "该操作只读取 Debug Agent 状态，不会修改任务或飞书数据。"
    )
    return LarkBotCard(
        title=title_map.get(action.kind, "Debug Agent"),
        status=status,
        summary=summary,
        fields=[
            {"label": "操作", "value": action.kind},
            {"label": "方法", "value": action.method},
            {"label": "路径", "value": action.path or "无"},
            {"label": "风险", "value": action.risk_level},
        ],
        buttons=[
            LarkBotCardButton(
                label="确认执行" if action.confirmation_required else "打开结果",
                method=action.method,
                path=action.path,
                style="danger" if action.confirmation_required else "primary",
                confirmation_required=action.confirmation_required,
            )
        ],
    )


def _warnings_for_action(action: LarkBotCommandAction) -> list[str]:
    if action.confirmation_required:
        return ["该命令映射到写操作；真实执行前必须完成操作者确认和审计记录。"]
    if action.kind == "unknown":
        return ["命令未识别，不会执行任何 Debug Agent 操作。"]
    return []


def _safe_command_text(text: str) -> str:
    normalized = " ".join(text.strip().split())
    if len(normalized) <= 200:
        return normalized
    return f"{normalized[:197]}..."
