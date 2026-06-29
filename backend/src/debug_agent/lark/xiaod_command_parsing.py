from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

COMMAND_PREFIXES = ("/debug", "debug-agent")
BOT_MENTION_PREFIXES = (
    "@小d",
    "@debug-agent",
    "@debug_agent",
    "@debug agent",
    "@xiaod",
    "@xiao d",
)
HELP_KEYWORDS = ("帮助", "怎么用", "能做什么", "你能干什么")
LARK_RESOURCE_MARKERS = (
    "larkoffice.com/sheets/",
    "larkoffice.com/base/",
    "larkoffice.com/docx/",
    "larkoffice.com/wiki/",
    "larkoffice.com/file/",
    "larkoffice.com/folder/",
    "larkoffice.com/minutes/",
    "larkoffice.com/slides/",
    "doubao.com/sheets/",
    "doubao.com/base/",
    "doubao.com/docx/",
    "doubao.com/wiki/",
)
SPREADSHEET_URL_PATTERN = re.compile(
    r"https?://[^\s，,。；;）)\]<]+/sheets/[A-Za-z0-9_-]+"
    r"(?:\?sheet=[A-Za-z0-9_-]+)?"
)
SPREADSHEET_RERUN_WRITEBACK_OPTION_MARKERS = (
    "写回",
    "回写",
    "写入表格",
    "对应列",
    "同步到飞书表格",
    "同步到飞书",
    "同步对应位置",
    "同步相应位置",
    "同步到对应位置",
    "同步到相应位置",
    "是否同步",
)
WRITEBACK_DECISION_SKIP_MARKERS = (
    "不同步",
    "默认不同步",
    "不需要同步",
    "不用同步",
    "不要同步",
    "跳过同步",
    "不写回",
    "不用写回",
    "不要写回",
    "跳过写回",
    "nosync",
    "no sync",
    "skipsync",
    "skip sync",
    "donotsync",
    "do not sync",
    "nowriteback",
    "no writeback",
    "skipwriteback",
    "skip writeback",
)


def is_ambiguous_continue_request(compact: str) -> bool:
    return compact in {
        "继续",
        "继续吧",
        "继续推进",
        "然后呢",
        "下一步",
        "下一步呢",
        "接下来呢",
        "现在呢",
    }


def is_pending_command_continue_request(compact: str) -> bool:
    exact_continue_requests = {
        "继续",
        "继续吧",
        "继续执行",
        "确认执行",
        "确认创建任务",
        "执行",
        "执行吧",
    }
    if compact in exact_continue_requests:
        return True
    if any(
        marker in compact
        for marker in (
            "不继续",
            "不执行",
            "不用执行",
            "不要执行",
            "别执行",
            "不要点击确认",
            "不点击确认",
        )
    ):
        return False
    return any(compact.endswith(marker) for marker in ("继续执行", "确认执行", "确认创建任务"))


def is_pending_command_decline_request(compact: str) -> bool:
    return compact in {
        "不继续",
        "不继续执行",
        "不执行",
        "先不执行",
        "不用执行",
        "不要执行",
        "算了",
        "取消",
    }


def is_pending_command_retain_request(compact: str) -> bool:
    return compact in {
        "保留",
        "稍后处理",
        "保留稍后处理",
        "先留着",
        "先保留",
        "晚点处理",
    }


def is_pending_command_delete_request(compact: str) -> bool:
    return compact in {
        "删除",
        "彻底删除",
        "删掉",
        "清理",
        "清掉",
        "不要了",
        "放弃",
    }


def is_writeback_decision_skip_request(compact: str) -> bool:
    if compact in {
        "不同步",
        "不同步了",
        "先不同步",
        "默认不同步",
        "不需要同步",
        "不用同步",
        "不要同步",
        "跳过同步",
        "不写回",
        "先不写回",
        "不用写回",
        "不要写回",
        "跳过写回",
        "nosync",
        "no sync",
        "skipsync",
        "skip sync",
        "donotsync",
        "do not sync",
        "nowriteback",
        "no writeback",
        "skipwriteback",
        "skip writeback",
    }:
        return True
    return any(marker in compact for marker in WRITEBACK_DECISION_SKIP_MARKERS)


def is_writeback_decision_sync_request(compact: str) -> bool:
    return compact in {
        "同步",
        "同步吧",
        "确认同步",
        "同步到表格",
        "同步到飞书表格",
        "同步到飞书",
        "同步回飞书表格",
        "同步对应位置",
        "同步相应位置",
        "同步到对应位置",
        "同步到相应位置",
        "写回",
        "写回吧",
        "确认写回",
        "写回到表格",
        "写回飞书表格",
    }


def is_contextual_report_request(compact: str) -> bool:
    return any(
        marker in compact
        for marker in (
            "报告呢",
            "报告在哪",
            "报告在哪里",
            "给我报告",
            "看报告",
            "打开报告",
            "结果呢",
            "结论呢",
        )
    )


def is_result_confidence_request(compact: str) -> bool:
    return any(
        marker in compact
        for marker in (
            "靠谱吗",
            "可信么",
            "可信吗",
            "结论可靠吗",
            "这个结论",
            "为啥这么判",
            "为什么这么判",
            "证据够吗",
        )
    )


def is_contextual_pause_request(compact: str) -> bool:
    return any(marker in compact for marker in ("先别跑", "别跑了", "先停一下", "停一下"))


def is_contextual_cancel_request(compact: str) -> bool:
    return any(marker in compact for marker in ("不用跑了", "不要跑了", "终止吧", "取消吧"))


def is_contextual_resume_request(compact: str) -> bool:
    return any(marker in compact for marker in ("继续跑", "恢复跑", "继续执行"))


def is_contextual_writeback_request(compact: str) -> bool:
    return any(marker in compact for marker in ("写回了吗", "写回了没", "是否写回"))


def needs_context_to_resolve_reference(compact: str) -> bool:
    if not any(marker in compact for marker in ("刚才", "这个", "那个", "上一个")):
        return False
    return any(
        marker in compact
        for marker in (
            "任务",
            "case",
            "报告",
            "结果",
            "结论",
            "写回",
            "证据",
        )
    )


def command_text_for_backend(text: str) -> str | None:
    clean_text = strip_bot_mention_prefix(text)
    if (
        is_current_progress_request(clean_text)
        or is_recent_tasks_request(clean_text)
        or is_cancel_current_job_request(clean_text)
        or is_pause_current_job_request(clean_text)
        or is_resume_current_job_request(clean_text)
    ):
        return None
    normalized = normalized_text(clean_text)
    if has_command_prefix(normalized):
        return clean_text
    spreadsheet_row_batch_command = natural_spreadsheet_row_batch_command(clean_text)
    if spreadsheet_row_batch_command:
        return spreadsheet_row_batch_command
    spreadsheet_operation_command = natural_spreadsheet_operation_command(clean_text)
    if spreadsheet_operation_command:
        return spreadsheet_operation_command
    natural = natural_command_text(normalized)
    if natural:
        return natural
    return "/debug help" if any(keyword in clean_text for keyword in HELP_KEYWORDS) else None


def natural_spreadsheet_operation_command(text: str) -> str:
    source = first_spreadsheet_url(text)
    if not source:
        return ""
    normalized = normalized_text(text)
    if any(
        keyword in normalized
        for keyword in ("同步表格", "表格同步", "spreadsheet sync", "sheet sync")
    ):
        return f"/debug spreadsheet sync {source}"
    if any(
        keyword in normalized
        for keyword in ("重跑表格", "表格重跑", "spreadsheet rerun", "sheet rerun")
    ):
        return f"/debug spreadsheet rerun {source}"
    return ""


def natural_command_text(normalized: str) -> str:
    if not normalized:
        return ""
    spreadsheet_row_batch_command = natural_spreadsheet_row_batch_command(normalized)
    if spreadsheet_row_batch_command:
        return spreadsheet_row_batch_command
    if any(term in normalized for term in ("启动 worker", "启动worker", "启动后台进程")):
        return "/debug worker start"
    if any(term in normalized for term in ("停止 worker", "停止worker", "停止后台进程")):
        return "/debug worker stop"
    if any(term in normalized for term in ("worker", "后台进程", "队列")):
        return "/debug worker"
    if any(
        term in normalized
        for term in ("模型目录", "模型配置", "模型路由", "agent 拓扑", "agent拓扑")
    ):
        return "/debug models"
    if any(term in normalized for term in ("性能", "p95", "耗时", "延迟")):
        return "/debug performance"
    if any(term in normalized for term in ("观测总览", "观测摘要", "观测", "系统总览")):
        return "/debug observability"
    if any(term in normalized for term in ("产物保留", "产物清理", "产物状态", "artifact")):
        return "/debug artifact-retention"
    if any(term in normalized for term in ("样本列表", "样本清单", "case列表", "case 列表")):
        return "/debug cases"
    if any(term in normalized for term in ("机器人预检", "bot预检", "接入预检")):
        return "/debug preflight"
    if any(term in normalized for term in ("上线门禁", "真实上线", "go-live", "golive")):
        return "/debug go-live"
    if any(term in normalized for term in ("scope检查", "权限检查", "scope check")):
        return "/debug scope-check"
    if any(term in normalized for term in ("权限清单", "权限", "scope", "scopes")):
        return "/debug permissions"
    if any(term in normalized for term in ("表格连接", "飞书表格状态", "表格状态")):
        return "/debug sheet-status"
    if any(term in normalized for term in ("操作审计", "lark审计", "飞书审计")):
        return "/debug audits"
    if any(term in normalized for term in ("草稿列表", "badcase草稿", "当前草稿列表")):
        return "/debug drafts"
    if any(
        term in normalized
        for term in ("待确认命令", "待确认操作", "pending command", "pending commands")
    ):
        return "/debug pending"
    if any(term in normalized for term in ("写回审计", "写回状态", "表格写回")):
        return "/debug writebacks"
    if any(term in normalized for term in ("最近任务", "任务列表", "任务清单", "job列表")):
        return "/debug jobs"
    if any(term in normalized for term in ("批次列表", "批次清单", "最近批次", "batch列表")):
        return "/debug batches"
    if any(term in normalized for term in ("批次对比", "批次ab", "批次 a/b", "batch comparison")):
        return "/debug batch-comparison"
    if any(term in normalized for term in ("运维支持包", "支持包", "support bundle")):
        return "/debug support-bundle"
    if any(term in normalized for term in ("导出任务", "任务导出", "debugjob导出")):
        return "/debug export"
    if any(term in normalized for term in ("数据库备份", "db backup")):
        return "/debug database-backup"
    spreadsheet_sync_source = extract_target_after_keywords(
        normalized, ("同步表格", "表格同步", "spreadsheet sync", "sheet sync")
    )
    if spreadsheet_sync_source:
        return f"/debug spreadsheet sync {spreadsheet_sync_source}"
    spreadsheet_rerun_source = extract_target_after_keywords(
        normalized, ("重跑表格", "表格重跑", "spreadsheet rerun", "sheet rerun")
    )
    if spreadsheet_rerun_source:
        return f"/debug spreadsheet rerun {spreadsheet_rerun_source}"

    recommended_status_command = recommended_action_status_command(normalized)
    if recommended_status_command:
        return recommended_status_command
    recommended_verify_targets = extract_two_targets_after_keywords(
        normalized, ("验证推荐动作", "复验推荐动作", "recommended action verify")
    )
    if recommended_verify_targets[0]:
        return (
            "/debug recommended-actions verify "
            f"{recommended_verify_targets[0]} {recommended_verify_targets[1]}"
        )
    human_status_command = human_handoff_status_command(normalized)
    if human_status_command:
        return human_status_command
    strategy_followup_targets = extract_two_targets_after_keywords(
        normalized, ("创建策略跟进", "执行策略跟进", "提交策略跟进", "strategy followup job")
    )
    if strategy_followup_targets[0]:
        return (
            "/debug strategy-followups run "
            f"{strategy_followup_targets[0]} {strategy_followup_targets[1]}"
        )
    targeted_probe_targets = extract_two_targets_after_keywords(
        normalized, ("创建定向探针", "执行定向探针", "提交定向探针", "targeted probe job")
    )
    if targeted_probe_targets[0]:
        return f"/debug targeted-probes run {targeted_probe_targets[0]} {targeted_probe_targets[1]}"
    auto_closure_report_job_id = extract_target_after_keywords(
        normalized, ("自动闭环报告", "闭环报告", "auto closure report")
    )
    if auto_closure_report_job_id:
        return f"/debug auto-closure-report {auto_closure_report_job_id}"
    auto_closure_job_id = extract_target_after_keywords(
        normalized, ("自动闭环", "自动debug闭环", "auto closure")
    )
    if auto_closure_job_id:
        return f"/debug auto-closure {auto_closure_job_id}"

    case_id = extract_target_after_keywords(
        normalized,
        (
            "调试已导入样本",
            "运行已导入样本",
            "跑已导入样本",
            "调试 case",
            "运行 case",
            "跑 case",
            "case id",
            "case:",
            "debug case",
            "run case",
        ),
    )
    if case_id:
        return f"/debug run case {case_id}"
    report_job_id = extract_target_after_keywords(
        normalized, ("查看报告", "任务报告", "报告", "report")
    )
    if report_job_id:
        return f"/debug report {report_job_id}"
    evidence_job_id = extract_target_after_keywords(
        normalized, ("查看证据", "证据账本", "证据", "evidence")
    )
    if evidence_job_id:
        return f"/debug evidence {evidence_job_id}"
    stages_job_id = extract_target_after_keywords(
        normalized, ("运行阶段", "阶段", "run stages", "stages")
    )
    if stages_job_id:
        return f"/debug stages {stages_job_id}"
    recommended_actions_job_id = extract_target_after_keywords(
        normalized, ("推荐动作状态", "推荐动作", "recommended actions", "recommended")
    )
    if recommended_actions_job_id:
        return f"/debug recommended-actions {recommended_actions_job_id}"
    human_handoffs_job_id = extract_target_after_keywords(
        normalized, ("人工交接", "人类交接", "human handoffs", "handoffs")
    )
    if human_handoffs_job_id:
        return f"/debug human-handoffs {human_handoffs_job_id}"
    strategy_followups_job_id = extract_target_after_keywords(
        normalized, ("策略跟进", "跟进实验", "strategy followups", "strategy follow-ups")
    )
    if strategy_followups_job_id:
        return f"/debug strategy-followups {strategy_followups_job_id}"
    targeted_probes_job_id = extract_target_after_keywords(
        normalized, ("定向探针", "targeted probes", "探针")
    )
    if targeted_probes_job_id:
        return f"/debug targeted-probes {targeted_probes_job_id}"
    base_writeback_job_id = extract_target_after_keywords(
        normalized, ("base写回", "base 写回", "base writeback")
    )
    if base_writeback_job_id:
        return f"/debug base-writeback {base_writeback_job_id}"
    writeback_job_id = extract_target_after_keywords(
        normalized, ("创建写回确认", "写回任务", "写回 job", "writeback job")
    )
    if writeback_job_id:
        return f"/debug writeback {writeback_job_id}"
    if any(term in normalized for term in ("状态", "运行情况", "健康", "就绪", "status")):
        return "/debug status"
    if any(term in normalized for term in ("准入", "门禁", "pilot", "gate", "能不能上线")):
        return "/debug pilot-gate"
    for phrase, command in (
        ("暂停批次", "pause"),
        ("恢复批次", "resume"),
        ("取消批次", "cancel"),
        ("pause batch", "pause"),
        ("resume batch", "resume"),
        ("cancel batch", "cancel"),
    ):
        batch_id_for_action = extract_target_after_keywords(normalized, (phrase,))
        if batch_id_for_action:
            return f"/debug batch {command} {batch_id_for_action}"
    job_id = extract_target_after_keywords(normalized, ("查看任务", "任务", "job"))
    if job_id:
        return f"/debug job {job_id}"
    batch_id = extract_target_after_keywords(normalized, ("查看批次", "批次", "batch"))
    if batch_id:
        return f"/debug batch {batch_id}"
    return ""


def natural_spreadsheet_row_batch_command(normalized: str) -> str:
    source = first_spreadsheet_url(normalized)
    if not source:
        return ""
    row_ids = spreadsheet_row_ids_from_natural_text(normalized)
    sheet_id = sheet_id_from_spreadsheet_url(source)
    option_text = spreadsheet_rerun_option_text(normalized)
    if row_ids:
        return f"/debug spreadsheet rerun {source} {sheet_id} {','.join(row_ids)} {option_text}".strip()
    case_ids = spreadsheet_case_ids_from_natural_text(normalized)
    if len(case_ids) >= 2:
        return f"/debug spreadsheet rerun {source} {sheet_id} case:{','.join(case_ids)} {option_text}".strip()
    return ""


def spreadsheet_rerun_option_text(text: str) -> str:
    compact = normalized_text(text).replace(" ", "")
    options: list[str] = []
    if any(marker in compact for marker in ("返回报告", "生成报告", "报告", "结论")):
        options.append("--report")
        options.append("--controlled-probes")
    if any(marker in compact for marker in SPREADSHEET_RERUN_WRITEBACK_OPTION_MARKERS):
        options.append("--writeback")
    return " ".join(options)


def first_spreadsheet_url(text: str) -> str:
    match = SPREADSHEET_URL_PATTERN.search(text)
    return match.group(0).strip() if match else ""


def sheet_id_from_spreadsheet_url(source: str) -> str:
    clean_source = first_spreadsheet_url(source) or source
    parsed = urlparse(clean_source)
    sheet = parse_qs(parsed.query).get("sheet", [""])
    return sheet[0].strip()


def spreadsheet_row_ids_from_natural_text(text: str) -> list[str]:
    compact = text.replace(" ", "")
    first_rows_match = re.search(r"前(\d+)(?:行|个|条|个任务|条任务)", compact)
    if first_rows_match:
        count = int(first_rows_match.group(1))
        if count <= 0:
            return []
        return [str(row_id) for row_id in range(2, count + 2)]
    row_matches = re.findall(r"第(\d+)行", compact)
    if len(row_matches) > 1:
        return _unique_row_ids(row_matches)
    grouped_match = re.search(r"第((?:\d+[、,，和及与]*)+)\s*行", compact)
    if grouped_match:
        return _unique_row_ids(re.findall(r"\d+", grouped_match.group(1)))
    if row_matches:
        return _unique_row_ids(row_matches)
    return []


def spreadsheet_case_ids_from_natural_text(text: str) -> list[str]:
    text_without_links = re.sub(r"https?://[^\s，,。；;）)]+", " ", text)
    return _unique_case_ids(re.findall(r"\b[A-Z][A-Z0-9]{1,10}[-_]\d{1,8}\b", text_without_links))


def _unique_row_ids(row_ids: list[str]) -> list[str]:
    unique: list[str] = []
    for row_id in row_ids:
        normalized = str(int(row_id))
        if normalized not in unique:
            unique.append(normalized)
    return unique


def _unique_case_ids(case_ids: list[str]) -> list[str]:
    unique: list[str] = []
    for case_id in case_ids:
        normalized = case_id.strip()
        if normalized and normalized not in unique:
            unique.append(normalized)
    return unique


def is_badcase_intake_message(text: str) -> bool:
    normalized = normalized_text(strip_bot_mention_prefix(text))
    if has_lark_resource_link(normalized):
        return True
    return any(
        term in normalized
        for term in (
            "调试",
            "debug",
            "排查",
            "识别错",
            "识别错误",
            "badcase",
            "模型输出",
            "正确答案",
            "期望结果",
            "错误现象",
            "原始输入",
            "补充",
            "补充材料",
            "追加材料",
            "再补充",
        )
    )


def is_badcase_intake_guidance_request(text: str) -> bool:
    normalized = normalized_text(strip_bot_mention_prefix(text))
    compact = normalized.replace(" ", "")
    has_badcase_context = any(
        marker in compact
        for marker in (
            "badcase",
            "case",
            "识别错",
            "识别错误",
            "模型错",
            "模型错误",
            "调试",
            "debug",
        )
    )
    asks_how_to_submit = any(
        marker in compact
        for marker in (
            "怎么提",
            "怎么发",
            "怎么提交",
            "哪些信息",
            "什么信息",
            "要给你什么",
            "要给你哪些",
            "告诉我怎么",
        )
    )
    return has_badcase_context and asks_how_to_submit


def is_badcase_draft_followup_request(text: str) -> bool:
    normalized = normalized_text(strip_bot_mention_prefix(text)).strip(" ?？。!！")
    if normalized in {
        "然后呢",
        "下一步",
        "下一步呢",
        "接下来呢",
        "现在呢",
        "继续",
        "继续推进",
        "怎么提交",
        "怎么确认",
        "草稿呢",
        "当前草稿",
        "草稿状态",
    }:
        return True
    if "草稿" not in normalized and "badcase" not in normalized:
        return False
    if any(
        marker in normalized
        for marker in (
            "模型输出",
            "正确答案",
            "期望结果",
            "错误现象",
            "原始输入",
        )
    ):
        return False
    return any(
        term in normalized
        for term in (
            "已经记录",
            "记录为",
            "你不说",
            "刚才",
            "然后",
            "下一步",
            "怎么",
            "状态",
            "在哪",
        )
    )


def is_current_progress_request(text: str) -> bool:
    normalized = normalized_text(strip_bot_mention_prefix(text)).strip(" ?？。!！")
    normalized = re.sub(r"^(小d|xiaod|debug agent|debug-agent)[，,：:\\s]*", "", normalized)
    if normalized in {
        "现在跑到哪了",
        "跑到哪了",
        "当前进度",
        "任务进度",
        "当前任务进度",
        "最近任务进度",
        "现在进度",
    }:
        return True
    return any(
        marker in normalized
        for marker in (
            "跑到哪",
            "跑哪了",
            "任务进度",
            "当前任务",
            "现在还在跑",
            "还在跑吗",
            "执行到哪",
            "进展到哪",
        )
    )


def is_recent_tasks_request(text: str) -> bool:
    normalized = normalized_text(strip_bot_mention_prefix(text)).strip(" ?？。!！")
    normalized = re.sub(r"^(小d|xiaod|debug agent|debug-agent)[，,：:\s]*", "", normalized)
    compact = normalized.replace(" ", "")
    if compact in {
        "最近任务",
        "最近3个任务",
        "最近三个任务",
        "我的最近任务",
        "当前会话任务",
        "当前会话最近任务",
    }:
        return True
    return any(
        marker in compact
        for marker in (
            "最近3个任务",
            "最近三个任务",
            "我最近的任务",
            "当前会话任务",
            "刚才提交的任务",
        )
    )


def is_cancel_current_job_request(text: str) -> bool:
    compact = _current_job_control_text(text)
    if "草稿" in compact:
        return False
    return bool(
        re.search(r"(取消|终止)(当前|这个|最近)?(debug)?(任务|job)", compact)
        or re.search(r"(当前|这个|最近)?(debug)?(任务|job)(取消|终止)", compact)
    )


def is_pause_current_job_request(text: str) -> bool:
    compact = _current_job_control_text(text)
    if "草稿" in compact:
        return False
    return _mentions_job(compact) and any(marker in compact for marker in ("暂停", "先停"))


def is_resume_current_job_request(text: str) -> bool:
    compact = _current_job_control_text(text)
    if "草稿" in compact:
        return False
    return _mentions_job(compact) and any(marker in compact for marker in ("恢复", "继续执行"))


def _current_job_control_text(text: str) -> str:
    normalized = normalized_text(strip_bot_mention_prefix(text)).strip(" ?？。!！")
    normalized = re.sub(r"^(小d|xiaod|debug agent|debug-agent)[，,：:\s]*", "", normalized)
    return normalized.replace(" ", "")


def _mentions_job(compact: str) -> bool:
    return any(
        marker in compact
        for marker in ("当前任务", "这个任务", "最近任务", "debug任务", "任务", "job")
    )


def is_help_request(text: str) -> bool:
    normalized = normalized_text(strip_bot_mention_prefix(text))
    if normalized in {"/", "?", "？", "help", "/help", "帮助", "菜单", "开始"}:
        return True
    return any(keyword in normalized for keyword in HELP_KEYWORDS)


def has_lark_resource_link(text: str) -> bool:
    normalized = normalized_text(text)
    return any(marker in normalized for marker in LARK_RESOURCE_MARKERS)


def is_confirm_draft_request(text: str) -> bool:
    normalized = normalized_text(strip_bot_mention_prefix(text))
    return normalized in {
        "确认",
        "确认提交",
        "提交",
        "可以提交",
        "开始调试",
        "确认开始",
    }


def is_cancel_draft_request(text: str) -> bool:
    normalized = normalized_text(strip_bot_mention_prefix(text))
    if normalized in {
        "取消",
        "取消草稿",
        "不提交",
        "先不提交",
        "别提交",
        "放弃",
        "放弃草稿",
    }:
        return True
    compact = normalized.replace(" ", "")
    return "草稿" in compact and any(
        marker in compact for marker in ("取消", "放弃", "不提交", "别提交", "先别跑", "先不跑")
    )


def extract_target_after_keywords(normalized: str, keywords: tuple[str, ...]) -> str:
    for keyword in keywords:
        keyword_index = find_keyword_index(normalized, keyword)
        if keyword_index < 0:
            continue
        tail = normalized[keyword_index + len(keyword) :].strip(" ：:，,。")
        if not tail:
            continue
        target = tail.split()[0].strip(" ：:，,。?？")
        target = first_spreadsheet_url(target) or target
        if is_plausible_target_token(target):
            return target
    return ""


def extract_two_targets_after_keywords(
    normalized: str, keywords: tuple[str, ...]
) -> tuple[str, str]:
    for keyword in keywords:
        keyword_index = find_keyword_index(normalized, keyword)
        if keyword_index < 0:
            continue
        tail = normalized[keyword_index + len(keyword) :].strip(" ：:，,。")
        if not tail:
            continue
        tokens = [token.strip(" ：:，,。?？") for token in tail.split()]
        tokens = [token for token in tokens if token]
        if len(tokens) < 2:
            continue
        first, second = tokens[0], tokens[1]
        if is_plausible_target_token(first) and is_plausible_secondary_target_token(second):
            return first, second
    return "", ""


def find_keyword_index(normalized: str, keyword: str) -> int:
    start = 0
    while True:
        index = normalized.find(keyword, start)
        if index < 0:
            return -1
        if keyword_starts_at_token_boundary(normalized, index):
            return index
        start = index + 1


def keyword_starts_at_token_boundary(text: str, index: int) -> bool:
    if index <= 0:
        return True
    previous = text[index - 1]
    return not (previous.isascii() and (previous.isalnum() or previous in {"_", "-"}))


def recommended_action_status_command(normalized: str) -> str:
    for phrase, status in (
        ("标记推荐动作已应用", "applied"),
        ("推荐动作已应用", "applied"),
        ("应用推荐动作", "applied"),
        ("接受推荐动作", "accepted"),
        ("采纳推荐动作", "accepted"),
        ("拒绝推荐动作", "rejected"),
        ("驳回推荐动作", "rejected"),
    ):
        job_id, action_index = extract_two_targets_after_keywords(normalized, (phrase,))
        if job_id and action_index:
            return f"/debug recommended-actions status {job_id} {action_index} {status}"
    return ""


def human_handoff_status_command(normalized: str) -> str:
    for phrase, status in (
        ("人工交接已解决", "resolved"),
        ("人类交接已解决", "resolved"),
        ("解决人工交接", "resolved"),
        ("确认人工交接", "acknowledged"),
        ("人工交接处理中", "in_progress"),
        ("人工交接不处理", "wont_fix"),
    ):
        job_id, target_id = extract_two_targets_after_keywords(normalized, (phrase,))
        if job_id and target_id:
            return f"/debug human-handoffs status {job_id} {target_id} {status}"
    return ""


def is_plausible_target_token(target: str) -> bool:
    if not target or target.startswith("的"):
        return False
    if target.startswith(("http://", "https://")):
        return True
    if target in {
        "在哪",
        "在哪里",
        "哪里",
        "怎么",
        "怎么样",
        "如何",
        "呢",
        "吗",
        "状态",
        "报告",
        "证据",
    }:
        return False
    return any(char.isdigit() or char in {"-", "_"} for char in target)


def is_plausible_secondary_target_token(target: str) -> bool:
    if not target or target.startswith("的"):
        return False
    if target in {
        "在哪",
        "在哪里",
        "哪里",
        "怎么",
        "怎么样",
        "如何",
        "呢",
        "吗",
        "状态",
        "报告",
        "证据",
    }:
        return False
    return True


def has_command_prefix(normalized: str) -> bool:
    return any(normalized.startswith(prefix) for prefix in COMMAND_PREFIXES)


def strip_bot_mention_prefix(text: str) -> str:
    stripped = text.strip()
    lower = stripped.lower()
    for prefix in BOT_MENTION_PREFIXES:
        if lower.startswith(prefix):
            return stripped[len(prefix) :].lstrip(" ：:，,")
    return stripped


def normalized_text(text: str) -> str:
    return " ".join(text.strip().split()).lower()


def assistant_question_and_model(text: str) -> tuple[str, str]:
    stripped = text.strip()
    patterns = (
        r"(?i)\bmodel_id\s*=\s*([A-Za-z0-9_.:-]+)",
        r"(?i)\bmodel\s*=\s*([A-Za-z0-9_.:-]+)",
        r"用模型\s*([A-Za-z0-9_.:-]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, stripped)
        if not match:
            continue
        model_id = match.group(1).strip()
        question = (stripped[: match.start()] + stripped[match.end() :]).strip(" ，,。")
        return question or stripped, model_id
    return stripped, ""
