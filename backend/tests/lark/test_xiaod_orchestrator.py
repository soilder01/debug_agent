import pytest

from debug_agent.lark.xiaod_orchestrator import (
    XiaoDConversationContext,
    XiaoDTurnRequest,
    assistant_question_and_model,
    command_text_for_backend,
    decide_xiaod_turn,
    first_spreadsheet_url,
    is_badcase_intake_message,
    is_badcase_draft_followup_request,
    is_cancel_current_job_request,
    sheet_id_from_spreadsheet_url,
    strip_bot_mention_prefix,
)


def test_xiaod_orchestrator_routes_draft_followup_before_assistant_chat() -> None:
    decision = decide_xiaod_turn(XiaoDTurnRequest(text="然后呢？"))

    assert decision.kind == "badcase_draft_followup"
    assert decision.reason == "latest_badcase_draft_status"
    assert is_badcase_draft_followup_request("你不说你已经记录为badcase 草稿了？")


def test_xiaod_orchestrator_routes_lark_sheet_link_to_badcase_draft() -> None:
    decision = decide_xiaod_turn(
        XiaoDTurnRequest(
            text="https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123",
        )
    )

    assert decision.kind == "save_badcase_draft"
    assert decision.reason == "badcase_intake"


def test_xiaod_orchestrator_does_not_parse_badcase_colon_as_case_command() -> None:
    decision = decide_xiaod_turn(
        XiaoDTurnRequest(
            text=(
                "@小D real-at-parser badcase:"
                "source:https://example.com/a-1.png; "
                "model_output: 3; expected: 8; issue: mistook 8 for 3"
            ),
        )
    )

    assert decision.kind == "save_badcase_draft"
    assert decision.reason == "badcase_intake"
    assert decision.backend_command == ""


def test_xiaod_orchestrator_routes_current_progress_query_before_backend_status() -> None:
    decision = decide_xiaod_turn(XiaoDTurnRequest(text="小D，现在跑到哪了？"))

    assert decision.kind == "query_current_progress"
    assert decision.reason == "current_debug_progress"
    assert command_text_for_backend("现在跑到哪了？") is None


def test_xiaod_orchestrator_routes_recent_tasks_query_before_global_jobs() -> None:
    decision = decide_xiaod_turn(XiaoDTurnRequest(text="小D，最近 3 个任务"))

    assert decision.kind == "query_recent_tasks"
    assert decision.reason == "recent_debug_tasks"
    assert command_text_for_backend("最近任务") is None


def test_xiaod_orchestrator_routes_current_job_control_before_draft_cancel() -> None:
    cancel_decision = decide_xiaod_turn(XiaoDTurnRequest(text="小D，取消当前任务"))
    pause_decision = decide_xiaod_turn(XiaoDTurnRequest(text="小D，暂停当前任务"))
    resume_decision = decide_xiaod_turn(XiaoDTurnRequest(text="小D，恢复当前任务"))

    assert cancel_decision.kind == "cancel_current_job"
    assert cancel_decision.reason == "current_debug_job_cancel"
    assert pause_decision.kind == "pause_current_job"
    assert pause_decision.reason == "current_debug_job_pause"
    assert resume_decision.kind == "resume_current_job"
    assert resume_decision.reason == "current_debug_job_resume"
    assert command_text_for_backend("取消当前任务") is None
    assert command_text_for_backend("暂停当前任务") is None
    assert command_text_for_backend("恢复当前任务") is None


def test_xiaod_orchestrator_treats_supplement_as_badcase_intake() -> None:
    decision = decide_xiaod_turn(XiaoDTurnRequest(text="补充材料：视频第 2 秒按钮闪了一下"))

    assert decision.kind == "save_badcase_draft"
    assert decision.reason == "badcase_intake"


def test_xiaod_orchestrator_maps_existing_product_read_actions() -> None:
    decision = decide_xiaod_turn(XiaoDTurnRequest(text="查看 worker 状态"))

    assert decision.kind == "backend_command"
    assert decision.backend_command == "/debug worker"
    expectations = {
        "当前 worker 怎么样？": "/debug worker",
        "启动 worker": "/debug worker start",
        "模型路由现在怎么配的": "/debug models",
        "性能 P95 怎么样": "/debug performance",
        "机器人预检结果": "/debug preflight",
        "上线门禁怎么样": "/debug go-live",
        "Lark 权限清单": "/debug permissions",
        "最近操作审计": "/debug audits",
        "badcase草稿列表": "/debug drafts",
        "表格写回审计": "/debug writebacks",
        "查看报告 job-1": "/debug report job-1",
        "查看证据 job-1": "/debug evidence job-1",
        "运行阶段 job-1": "/debug stages job-1",
        "暂停批次 batch-1": "/debug batch pause batch-1",
        "@debug-agent /debug status": "/debug status",
        "@小D查看状态": "/debug status",
    }
    for message, command in expectations.items():
        assert command_text_for_backend(message) == command
    assert command_text_for_backend("这个任务的报告在哪里？") is None
    assert command_text_for_backend("任务报告在哪？") is None


def test_xiaod_orchestrator_does_not_treat_cancel_button_copy_as_job_cancel() -> None:
    assert is_cancel_current_job_request("取消当前任务")
    assert is_cancel_current_job_request("这个任务取消")
    assert not is_cancel_current_job_request("需要看到确认创建任务和取消按钮，不要点击确认。")


def test_xiaod_orchestrator_routes_live_card_validation_sheet_copy_to_rerun() -> None:
    message = (
        "task-card-live-test 处理这个表第2行："
        "https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123\n"
        "只做真实群卡片验收：需要看到确认创建任务和取消按钮，不要点击确认。"
    )

    decision = decide_xiaod_turn(XiaoDTurnRequest(text=message))

    assert decision.kind == "backend_command"
    assert decision.backend_command == (
        "/debug spreadsheet rerun "
        "https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123 "
        "testSheet123 2"
    )


def test_xiaod_orchestrator_maps_spreadsheet_report_writeback_targets() -> None:
    text = (
        "把这个表前10行 debug 任务跑完，返回报告并写回对应列："
        "https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123"
    )

    assert command_text_for_backend(text) == (
        "/debug spreadsheet rerun "
        "https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123 "
        "testSheet123 2,3,4,5,6,7,8,9,10,11 --report --controlled-probes --writeback"
    )


@pytest.mark.parametrize(
    "sync_phrase",
    [
        "询问是否同步到飞书表格",
        "询问是否同步到飞书",
        "询问是否同步对应位置",
        "询问是否同步相应位置",
        "询问是否同步",
    ],
)
def test_xiaod_orchestrator_maps_spreadsheet_report_sync_decision_targets(
    sync_phrase: str,
) -> None:
    text = (
        f"把这个表前10行 debug 任务跑完，返回报告并{sync_phrase}："
        "https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123"
    )

    assert command_text_for_backend(text) == (
        "/debug spreadsheet rerun "
        "https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123 "
        "testSheet123 2,3,4,5,6,7,8,9,10,11 --report --controlled-probes --writeback"
    )


def test_xiaod_orchestrator_explicit_sheet_rows_preempt_contextual_report_writeback() -> None:
    text = (
        "把这个表前10行debug任务跑完，返回报告，并在完成后询问是否写回/同步到飞书表格对应位置；"
        "https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123"
    )
    expected_command = (
        "/debug spreadsheet rerun "
        "https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123 "
        "testSheet123 2,3,4,5,6,7,8,9,10,11 --report --controlled-probes --writeback"
    )
    context = XiaoDConversationContext(
        latest_submitted_job_id="job-report",
        latest_submitted_job_status="completed",
    )

    decision = decide_xiaod_turn(XiaoDTurnRequest(text=text), context=context)

    assert command_text_for_backend(text) == expected_command
    assert decision.kind == "backend_command"
    assert decision.backend_command == expected_command
    assert decision.reason == "mapped_to_debug_agent_api"
    assert "job-report" not in decision.backend_command


def test_xiaod_orchestrator_explicit_sheet_task_preempts_pending_no_sync_decision() -> None:
    text = (
        "请处理表格第3行 JSZN-096，完成 debug 后返回报告；"
        "默认不要写回飞书，完成后询问我是否同步。链接："
        "https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123"
    )
    context = XiaoDConversationContext(has_pending_writeback_decision=True)

    decision = decide_xiaod_turn(XiaoDTurnRequest(text=text), context=context)

    assert decision.kind == "backend_command"
    assert decision.reason == "mapped_to_debug_agent_api"
    assert decision.backend_command == (
        "/debug spreadsheet rerun "
        "https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123 "
        "testSheet123 3 --report --controlled-probes --writeback"
    )


def test_xiaod_orchestrator_trims_spreadsheet_url_at_sheet_query_boundary() -> None:
    text = (
        "处理这个表第2行："
        "https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123"
        "只做真实群卡片验收：需要看到确认创建任务和取消按钮"
    )

    assert first_spreadsheet_url(text) == (
        "https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123"
    )
    assert command_text_for_backend(text) == (
        "/debug spreadsheet rerun "
        "https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123 "
        "testSheet123 2"
    )


@pytest.mark.parametrize(
    "text",
    [
        (
            "处理这个表第2行："
            "[https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123]"
            "(https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123)"
        ),
        (
            "处理这个表第2行："
            "https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123]"
            "(https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123)"
        ),
    ],
)
def test_xiaod_orchestrator_cleans_markdown_spreadsheet_links(text: str) -> None:
    clean_url = "https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123"

    assert first_spreadsheet_url(text) == clean_url
    assert sheet_id_from_spreadsheet_url(text) == "testSheet123"
    assert command_text_for_backend(text) == (f"/debug spreadsheet rerun {clean_url} testSheet123 2")


def test_xiaod_orchestrator_cleans_keyword_spreadsheet_markdown_link_target() -> None:
    clean_url = "https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123"
    text = f"重跑表格 [{clean_url}]({clean_url})"

    assert command_text_for_backend(text) == f"/debug spreadsheet rerun {clean_url}"


def test_sheet_id_from_spreadsheet_url_ignores_markdown_link_trailer() -> None:
    polluted_url = (
        "https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123]"
        "(https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123)"
    )

    assert sheet_id_from_spreadsheet_url(polluted_url) == "testSheet123"


def test_xiaod_orchestrator_recognizes_badcase_intake_and_mentions() -> None:
    text = "\n".join(
        [
            "原始输入：https://example.com/a.png",
            '模型输出：{"answer":"3"}',
            '正确答案：{"answer":"8"}',
            "错误现象：把 8 识别成 3",
        ]
    )

    assert is_badcase_intake_message(text)
    assert is_badcase_intake_message("@小D 帮我调试这个识别错误")
    assert strip_bot_mention_prefix("@小D 帮我调试这个识别错误") == "帮我调试这个识别错误"


def test_xiaod_orchestrator_keeps_write_actions_behind_backend_command_gate() -> None:
    decision = decide_xiaod_turn(XiaoDTurnRequest(text="调试已导入样本 case-1"))

    assert decision.kind == "backend_command"
    assert decision.backend_command == "/debug run case case-1"


def test_xiaod_orchestrator_preserves_chat_model_override() -> None:
    decision = decide_xiaod_turn(XiaoDTurnRequest(text="model_id=ep-user 解释一下报告"))

    assert decision.kind == "assistant_chat"
    assert decision.assistant_question == "解释一下报告"
    assert decision.assistant_model_id == "ep-user"
    assert assistant_question_and_model("用模型 ep-pro 解释一下报告") == ("解释一下报告", "ep-pro")


def test_xiaod_orchestrator_uses_context_for_ambiguous_continue() -> None:
    running_context = XiaoDConversationContext(
        latest_submitted_job_id="job-running",
        latest_submitted_job_status="running",
    )
    decision = decide_xiaod_turn(XiaoDTurnRequest(text="继续"), context=running_context)

    assert decision.kind == "query_current_progress"
    assert decision.reason == "contextual_continue_current_job"

    ready_context = XiaoDConversationContext(has_ready_draft=True)
    ready_decision = decide_xiaod_turn(XiaoDTurnRequest(text="继续"), context=ready_context)

    assert ready_decision.kind == "badcase_draft_followup"
    assert ready_decision.reason == "contextual_continue_badcase_draft"


@pytest.mark.parametrize("text", ["task5-marker 继续执行", "dogfood-123继续执行"])
def test_xiaod_orchestrator_recognizes_prefixed_pending_continue(text: str) -> None:
    context = XiaoDConversationContext(has_pending_command=True)

    decision = decide_xiaod_turn(XiaoDTurnRequest(text=text), context=context)

    assert decision.kind == "continue_pending_command"
    assert decision.reason == "contextual_continue_pending_command"


def test_xiaod_orchestrator_routes_writeback_decision_text_with_context() -> None:
    context = XiaoDConversationContext(has_pending_writeback_decision=True)

    skip_decision = decide_xiaod_turn(XiaoDTurnRequest(text="不同步"), context=context)
    sync_decision = decide_xiaod_turn(XiaoDTurnRequest(text="同步到飞书表格"), context=context)
    sync_to_lark_decision = decide_xiaod_turn(XiaoDTurnRequest(text="同步到飞书"), context=context)
    sync_position_decision = decide_xiaod_turn(
        XiaoDTurnRequest(text="同步对应位置"),
        context=context,
    )

    assert skip_decision.kind == "skip_writeback_decision"
    assert skip_decision.reason == "contextual_skip_writeback_decision"
    assert sync_decision.kind == "sync_writeback_decision"
    assert sync_decision.reason == "contextual_sync_writeback_decision"
    assert sync_to_lark_decision.kind == "sync_writeback_decision"
    assert sync_position_decision.kind == "sync_writeback_decision"


@pytest.mark.parametrize(
    "text",
    [
        "marker xxx 不同步",
        "dogfood-random 不写回",
        "验收前缀 不要同步",
        "task5-marker 先不同步",
        "dogfood-random skip sync",
        "dogfood-random no sync",
    ],
)
def test_xiaod_orchestrator_routes_prefixed_no_sync_to_writeback_skip(
    text: str,
) -> None:
    context = XiaoDConversationContext(has_pending_writeback_decision=True)

    decision = decide_xiaod_turn(XiaoDTurnRequest(text=text), context=context)

    assert decision.kind == "skip_writeback_decision"
    assert decision.reason == "contextual_skip_writeback_decision"
    assert decision.backend_command == ""


def test_xiaod_orchestrator_routes_contextual_report_request_to_latest_job() -> None:
    context = XiaoDConversationContext(
        latest_submitted_job_id="job-report",
        latest_submitted_job_status="completed",
    )
    decision = decide_xiaod_turn(XiaoDTurnRequest(text="报告呢？"), context=context)

    assert decision.kind == "backend_command"
    assert decision.backend_command == "/debug report job-report"
    assert decision.reason == "contextual_latest_job_report"


def test_xiaod_orchestrator_clarifies_ambiguous_report_without_context() -> None:
    decision = decide_xiaod_turn(
        XiaoDTurnRequest(text="报告呢？"),
        context=XiaoDConversationContext(),
    )

    assert decision.kind == "clarify_intent"
    assert decision.reason == "missing_context_for_report"


def test_xiaod_orchestrator_routes_contextual_pause_without_job_keyword() -> None:
    context = XiaoDConversationContext(
        latest_submitted_job_id="job-running",
        latest_submitted_job_status="running",
    )
    decision = decide_xiaod_turn(XiaoDTurnRequest(text="先别跑了"), context=context)

    assert decision.kind == "pause_current_job"
    assert decision.reason == "contextual_debug_job_pause"


def test_xiaod_orchestrator_routes_result_confidence_question_with_context() -> None:
    context = XiaoDConversationContext(
        latest_submitted_job_id="job-report",
        latest_submitted_job_status="completed",
    )
    decision = decide_xiaod_turn(XiaoDTurnRequest(text="这个结论靠谱吗？"), context=context)

    assert decision.kind == "backend_command"
    assert decision.backend_command == "/debug report job-report"
    assert decision.reason == "contextual_result_explanation"
