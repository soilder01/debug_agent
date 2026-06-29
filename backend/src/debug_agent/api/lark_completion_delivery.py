from __future__ import annotations

import json
from collections.abc import Callable
from typing import Literal
from urllib.parse import urlparse

from debug_agent.api.badcase_intake_parsers import _clip_text, _object_string
from debug_agent.api.lark_bot_routes import LarkBotBadcaseDraftCompletionNotification
from debug_agent.api.lark_completion_rendering import (
    _completion_card_root_cause,
    _debug_report_has_agent_traces,
    _is_lark_document_url,
    _lark_bot_action_queue_card_buttons,
    _lark_bot_action_queue_summary_line,
    _lark_bot_completion_report_summary_lines,
    _lark_bot_run_view_summary_lines,
    _lark_url_button,
    _markdown_dict_items,
)
from debug_agent.experiments.runner import ExperimentEvidence
from debug_agent.jobs.auto_closure import AutoDebugClosureResult
from debug_agent.jobs.auto_closure_report import build_auto_closure_markdown_report
from debug_agent.jobs.service import SubmittedDebugJob
from debug_agent.lark.bot import LarkBotReplyPayload, lark_bot_reply_cli_args
from debug_agent.lark.connector import LarkCliConnector, LarkCliError
from debug_agent.reports.generator import DebugReport
from debug_agent.reports.lark_docx_renderer import build_lark_docx_report_xml
from debug_agent.settings import DebugAgentSettings
from debug_agent.storage.models import DebugJobRow
from debug_agent.storage.repository import (
    DebugJobRepository,
    LarkBotBadcaseDraft,
    LarkReportDocument,
)


class LarkCompletionDeliveryController:
    def __init__(
        self,
        *,
        settings: Callable[[], DebugAgentSettings],
        job_repository: Callable[[], DebugJobRepository],
        build_report: Callable[[str], DebugReport | None],
        build_targeted_probe_results: Callable[[str], list[dict[str, object]]],
        report_document_connector: Callable[[str], LarkCliConnector],
        report_doc_identity: Callable[[], Literal["bot", "user", "unknown"]],
        reply_target_type: Callable[
            [LarkBotBadcaseDraft], Literal["message", "chat", "user", "none"]
        ],
        stable_completion_idempotency_key: Callable[[str, str], str],
        spreadsheet_writeback_target: Callable[[str], tuple[str, str, str] | None],
        base_writeback_target: Callable[[str], tuple[str, str, str] | None],
        badcase_action_url: Callable[[LarkBotBadcaseDraft, str], str],
        should_auto_close_completed_job: Callable[[SubmittedDebugJob], bool],
        original_cot_excerpt: Callable[[object], str],
        original_prediction: Callable[[object], str],
    ) -> None:
        self._settings = settings
        self._job_repository = job_repository
        self._build_report = build_report
        self._build_targeted_probe_results = build_targeted_probe_results
        self._report_document_connector = report_document_connector
        self._report_doc_identity = report_doc_identity
        self._reply_target_type = reply_target_type
        self._stable_completion_idempotency_key = stable_completion_idempotency_key
        self._spreadsheet_writeback_target = spreadsheet_writeback_target
        self._base_writeback_target = base_writeback_target
        self._badcase_action_url = badcase_action_url
        self._should_auto_close_completed_job = should_auto_close_completed_job
        self._original_cot_excerpt = original_cot_excerpt
        self._original_prediction = original_prediction

    def completion_notification_for_draft(
        self, *, draft: LarkBotBadcaseDraft, job: DebugJobRow
    ) -> LarkBotBadcaseDraftCompletionNotification:
        base_url = self._settings().report_base_url.rstrip("/")
        job_url = f"{base_url}/xiaod/views/jobs/{job.job_id}"
        internal_report_url = self.internal_job_report_url(job.job_id)
        report_document = self.ensure_lark_report_document_for_job(
            job,
            actor=draft.open_id or draft.actor,
            internal_report_url=internal_report_url,
        )
        report_url = (
            report_document.document_url
            if report_document is not None
            and report_document.status == "published"
            and report_document.document_url
            else internal_report_url
        )
        markdown = self.completion_markdown(
            draft=draft,
            job=job,
            job_url=job_url,
            report_url=report_url,
            internal_report_url=internal_report_url,
            report_document=report_document,
        )
        payload = LarkBotReplyPayload(
            command_id=f"badcase-{draft.draft_id}",
            action_kind="badcase_completion",
            status="completed",
            target_type=self._reply_target_type(draft),
            message_id=draft.message_id,
            chat_id=draft.chat_id,
            user_id=draft.open_id,
            markdown=markdown,
            message_type="interactive",
            content=self.completion_card(
                draft=draft,
                job=job,
                job_url=job_url,
                report_url=report_url,
                internal_report_url=internal_report_url,
                report_document=report_document,
                markdown=markdown,
            ),
            idempotency_key=self._stable_completion_idempotency_key(
                draft.draft_id,
                job.job_id,
            ),
        )
        payload = payload.model_copy(
            update={
                "delivery_args": lark_bot_reply_cli_args(payload, identity="bot", dry_run=False)
            }
        )
        return LarkBotBadcaseDraftCompletionNotification(
            notification_id=f"badcase-completion:{draft.draft_id}:{job.job_id}",
            kind="badcase_completion",
            draft_id=draft.draft_id,
            draft=draft,
            payload=payload,
            dedupe_key=f"{draft.draft_id}:{job.job_id}",
            job_id=job.job_id,
            case_id=job.case_id,
            job_status=job.status,
            job_url=job_url,
            report_url=report_url,
        )

    def internal_job_report_url(self, job_id: str) -> str:
        return f"{self._settings().report_base_url.rstrip('/')}/xiaod/views/jobs/{job_id}/report"

    def canonical_report_url_for_job(self, *, job: DebugJobRow, actor: str = "") -> str:
        internal_report_url = self.internal_job_report_url(job.job_id)
        report_document = self.ensure_lark_report_document_for_job(
            job,
            actor=actor,
            internal_report_url=internal_report_url,
        )
        if (
            report_document is not None
            and report_document.status == "published"
            and report_document.document_url
        ):
            return report_document.document_url
        return internal_report_url

    def ensure_lark_report_document_for_job(
        self,
        job: DebugJobRow,
        *,
        actor: str,
        internal_report_url: str,
    ) -> LarkReportDocument | None:
        repository = self._job_repository()
        existing = repository.get_lark_report_document(job.job_id)
        if existing is not None:
            return existing
        if not self._settings().lark_report_docs_enabled:
            return None
        report = self._build_report(job.job_id)
        if report is None:
            return repository.save_lark_report_document(
                job_id=job.job_id,
                status="failed",
                document_url="",
                document_token="",
                internal_report_url=internal_report_url,
                error_message="debug report could not be rebuilt",
            )
        try:
            data = self._report_document_connector(actor).run_json(
                self.report_document_create_args(),
                stdin=self.report_document_content(
                    job=job,
                    report=report,
                    internal_report_url=internal_report_url,
                ),
            )
            document_url = self.document_url_from_create_response(data)
            if not document_url:
                raise LarkCliError(
                    "lark-cli docs +create returned no document URL",
                    error_type="invalid_json",
                )
            document_token = self.document_token_from_create_response(
                data, document_url=document_url
            )
            return repository.save_lark_report_document(
                job_id=job.job_id,
                status="published",
                document_url=document_url,
                document_token=document_token,
                internal_report_url=internal_report_url,
            )
        except (FileNotFoundError, LarkCliError) as exc:
            return repository.save_lark_report_document(
                job_id=job.job_id,
                status="failed",
                document_url="",
                document_token="",
                internal_report_url=internal_report_url,
                error_message=_clip_text(str(exc), 500),
            )

    def report_document_create_args(self) -> list[str]:
        settings = self._settings()
        args = [
            "docs",
            "+create",
            "--api-version",
            "v2",
            "--doc-format",
            "xml",
            "--content",
            "-",
            "--format",
            "json",
            "--as",
            self._report_doc_identity(),
        ]
        if settings.lark_report_doc_parent_token:
            args.extend(["--parent-token", settings.lark_report_doc_parent_token])
        elif settings.lark_report_doc_parent_position:
            args.extend(["--parent-position", settings.lark_report_doc_parent_position])
        return args

    def document_url_from_create_response(self, data: dict[str, object]) -> str:
        document = data.get("document")
        if isinstance(document, dict):
            url = _object_string(document, "url")
            if url:
                return url
        return _object_string(data, "url") or _object_string(data, "document_url")

    def document_token_from_create_response(
        self,
        data: dict[str, object],
        *,
        document_url: str,
    ) -> str:
        document = data.get("document")
        if isinstance(document, dict):
            for key in ("document_id", "token", "document_token"):
                value = _object_string(document, key)
                if value:
                    return value
        parsed = urlparse(document_url)
        parts = [part for part in parsed.path.split("/") if part]
        return parts[-1] if parts else ""

    def completion_markdown(
        self,
        *,
        draft: LarkBotBadcaseDraft,
        job: DebugJobRow,
        job_url: str,
        report_url: str,
        internal_report_url: str,
        report_document: LarkReportDocument | None,
    ) -> str:
        report = self._build_report(job.job_id)
        quality = self.completion_quality(job=job, report=report)
        lines = [
            quality["title"],
            "",
            f"- 草稿编号：`{draft.draft_id}`",
            f"- 样本追踪号：`{job.case_id}`",
            f"- 任务编号：`{job.job_id}`",
            f"- 错误现象：{draft.issue_summary or '未填写'}",
        ]
        if report is not None:
            lines.extend(_lark_bot_completion_report_summary_lines(report))
        lines.extend(
            [
                f"- 证据记录：{quality['evidence_count']} 条",
                f"- 模型调用错误：{quality['model_call_errors']} 个",
                f"- 输出解析错误：{quality['response_parse_errors']} 个",
                f"- 多 Agent 协同：{quality['meta_agent_roles'] or '未发现 meta-agent 产物'}",
                f"- 后续闭环产物：{quality['autonomous_loop']}",
            ]
        )
        if report is not None and _debug_report_has_agent_traces(report):
            lines.append("- Agent 输入与推理摘要：已写入完整报告")
        lines.extend(self.completion_product_lines(job=job))
        if quality["status"] != "passed":
            lines.extend(["", *[f"- 需要处理：{item}" for item in quality["actions"]]])
        lines.extend(self.completion_writeback_lines(draft=draft, job=job))
        lines.extend(
            [
                f"- 查看任务：{job_url}",
                f"- 查看云文档报告：{report_url}"
                if _is_lark_document_url(report_url)
                else f"- 查看报告：{report_url}",
            ]
        )
        if report_url != internal_report_url:
            lines.append(f"- 报告详情页：{internal_report_url}")
        elif report_document is not None and report_document.status == "failed":
            lines.append(
                f"- 云文档报告：生成失败，已回退报告详情页；原因 `{report_document.error_message}`。"
            )
        lines.extend(
            [
                "",
                "我已把完整分析结果生成到报告里；聊天里只保留摘要和链接。",
            ]
        )
        return "\n".join(lines)

    def completion_card(
        self,
        *,
        draft: LarkBotBadcaseDraft,
        job: DebugJobRow,
        job_url: str,
        report_url: str,
        internal_report_url: str,
        report_document: LarkReportDocument | None,
        markdown: str,
    ) -> dict[str, object]:
        report = self._build_report(job.job_id)
        quality = self.completion_quality(job=job, report=report)
        title = str(quality["title"]).removeprefix("## ").strip()
        template = "green" if quality["status"] == "passed" else "red"
        actions = self.completion_card_actions(
            draft=draft,
            job=job,
            report=report,
            job_url=job_url,
            report_url=report_url,
            internal_report_url=internal_report_url,
        )
        summary_lines = [
            f"**样本追踪号**：`{job.case_id}`",
            f"**任务编号**：`{job.job_id}`",
            f"**根因判断**：{_completion_card_root_cause(report)}",
            f"**证据记录**：{quality['evidence_count']} 条",
            f"**多 Agent 协同**：{quality['meta_agent_roles'] or '未发现 meta-agent 产物'}",
            f"**Auto-closure**：{self.completion_auto_closure_status(job_id=job.job_id)}",
        ]
        summary_lines.extend(_lark_bot_run_view_summary_lines(report))
        if report is not None and report.recommended_actions:
            first_action = report.recommended_actions[0]
            summary = str(first_action.get("summary", "")).strip()
            priority = str(first_action.get("priority", "")).strip()
            if summary:
                prefix = f"{priority} / " if priority else ""
                summary_lines.append(f"**推荐动作**：{_clip_text(prefix + summary, 180)}")
        action_queue_line = _lark_bot_action_queue_summary_line(report)
        if action_queue_line:
            summary_lines.append(action_queue_line)
        if _is_lark_document_url(report_url):
            summary_lines.append("**报告**：已生成飞书云文档。")
        elif report_document is not None and report_document.status == "failed":
            summary_lines.append("**报告**：云文档生成失败，已回退报告详情页。")
        else:
            summary_lines.append("**报告**：已生成报告详情页。")
        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": template,
                "title": {"tag": "plain_text", "content": title},
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": "\n".join(summary_lines),
                },
                {
                    "tag": "action",
                    "actions": actions,
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "完整文字摘要保留在消息 fallback 中，报告内包含 run stages、evidence ledger 和 Agent 输入摘要。",
                        }
                    ],
                },
            ],
        }

    def completion_card_actions(
        self,
        *,
        draft: LarkBotBadcaseDraft,
        job: DebugJobRow,
        report: DebugReport | None,
        job_url: str,
        report_url: str,
        internal_report_url: str,
    ) -> list[dict[str, object]]:
        base_url = self._settings().report_base_url.rstrip("/")
        report_label = "打开云文档报告" if _is_lark_document_url(report_url) else "打开报告"
        actions: list[dict[str, object]] = [
            _lark_url_button(report_label, report_url, style="primary"),
            _lark_url_button("打开任务", job_url),
            _lark_url_button(
                "打开证据",
                f"{base_url}/xiaod/views/jobs/{job.job_id}/evidence-ledger",
            ),
        ]
        actions.append(
            _lark_url_button(
                "验证推荐动作",
                f"{base_url}/xiaod/views/jobs/{job.job_id}/recommended-actions",
            )
        )
        actions.extend(_lark_bot_action_queue_card_buttons(job=job, report=report))
        spreadsheet_writeback_url = (
            self._badcase_action_url(draft, "writeback_spreadsheet")
            if self._spreadsheet_writeback_target(job.job_id) is not None
            else ""
        )
        base_writeback_url = (
            self._badcase_action_url(draft, "writeback_base")
            if self._base_writeback_target(job.job_id) is not None
            else ""
        )
        writeback_url = spreadsheet_writeback_url or base_writeback_url or job_url
        writeback_label = (
            "确认表格写回"
            if spreadsheet_writeback_url
            else "确认 Base 写回"
            if base_writeback_url
            else "查看写回状态"
        )
        actions.append(_lark_url_button(writeback_label, writeback_url))
        actions.append(
            _lark_url_button(
                "人工复核",
                f"{base_url}/xiaod/views/jobs/{job.job_id}/human-handoffs",
            )
        )
        if report_url != internal_report_url:
            actions.append(_lark_url_button("报告详情页", internal_report_url))
        actions.append(_lark_url_button("打开操作台", base_url))
        return actions[:12]

    def completion_product_lines(self, *, job: DebugJobRow) -> list[str]:
        return [
            "- 完整报告包含：run stages、evidence ledger、Agent 输入与推理摘要、推荐动作和 follow-up experiments。",
            f"- Auto-closure：{self.completion_auto_closure_status(job_id=job.job_id)}",
            "- 前端可继续查看证据、报告、推荐动作、写回审计和闭环任务。",
        ]

    def completion_auto_closure_status(self, *, job_id: str) -> str:
        stages = [stage.stage for stage in self._job_repository().list_debug_run_stages(job_id)]
        if any(stage in {"auto_closure", "targeted", "verification"} for stage in stages):
            return f"已发现闭环执行阶段 `{', '.join(stages)}`。"
        return "未自动执行；可在前端或用 `/debug auto-closure <job_id>` 显式触发后续复测/验证。"

    def completion_notification_ready(self, *, job: DebugJobRow) -> bool:
        if not self._settings().auto_closure_enabled:
            return True
        submitted = SubmittedDebugJob(
            job_id=job.job_id,
            case_id=job.case_id,
            status=job.status,
            artifact_group_id=job.artifact_group_id,
        )
        if not self._should_auto_close_completed_job(submitted):
            auto_closure_stage = self.debug_run_stage_by_name(job.job_id, "auto_closure")
            return auto_closure_stage is None or auto_closure_stage.status in {
                "completed",
                "failed",
                "skipped",
            }
        auto_closure_stage = self.debug_run_stage_by_name(job.job_id, "auto_closure")
        return auto_closure_stage is not None and auto_closure_stage.status in {
            "completed",
            "failed",
            "skipped",
        }

    def debug_run_stage_by_name(self, job_id: str, stage_name: str):
        for stage in self._job_repository().list_debug_run_stages(job_id):
            if stage.stage == stage_name:
                return stage
        return None

    def completion_quality(
        self,
        *,
        job: DebugJobRow,
        report: DebugReport | None,
    ) -> dict[str, object]:
        evidence = self._job_repository().list_evidence(job.job_id)
        model_call_errors = sum(1 for item in evidence if item.model_call_error_type)
        response_parse_errors = sum(1 for item in evidence if item.response_parse_error)
        meta_agent_roles = self.completion_meta_agent_roles(job_id=job.job_id, report=report)
        autonomous_loop = self.completion_autonomous_loop_summary(job_id=job.job_id, report=report)
        actions: list[str] = []
        if model_call_errors:
            actions.append("模型调用失败，需检查 Ark endpoint、输入 URI 和权限。")
        if response_parse_errors:
            actions.append(
                "模型输出未被 parser 接受，需检查输出格式/解析器；这次不能算完整有效 debug。"
            )
        if not meta_agent_roles:
            actions.append(
                "未发现 report_root_cause / experiment_planner / judge_comparator 等 meta-agent 协同产物。"
            )
        if autonomous_loop == "未产生 follow-up / recommended actions":
            actions.append(
                "未产生 follow-up experiments、targeted probes 或 recommended actions，自主闭环不足。"
            )
        status = "passed" if not actions else "needs_attention"
        return {
            "status": status,
            "title": "## Debug Agent 调试完成"
            if status == "passed"
            else "## Debug Agent 调试未通过，需要处理",
            "evidence_count": len(evidence),
            "model_call_errors": model_call_errors,
            "response_parse_errors": response_parse_errors,
            "meta_agent_roles": ", ".join(meta_agent_roles),
            "autonomous_loop": autonomous_loop,
            "actions": actions,
        }

    def completion_meta_agent_roles(self, *, job_id: str, report: DebugReport | None) -> list[str]:
        roles: list[str] = []
        if report is not None:
            enrichment = getattr(report, "meta_agent_enrichment", {})
            if isinstance(enrichment, dict):
                roles.extend(_roles_from_meta_agent_enrichment(enrichment))
        for stage in self._job_repository().list_debug_run_stages(job_id):
            enrichment = stage.output.get("meta_agent_enrichment")
            if isinstance(enrichment, dict):
                roles.extend(_roles_from_meta_agent_enrichment(enrichment))
        deduped: list[str] = []
        for role in roles:
            if role and role not in deduped:
                deduped.append(role)
        return deduped

    def completion_autonomous_loop_summary(self, *, job_id: str, report: DebugReport | None) -> str:
        stages = [stage.stage for stage in self._job_repository().list_debug_run_stages(job_id)]
        follow_ups = getattr(report, "follow_up_experiments", []) if report is not None else []
        recommended = getattr(report, "recommended_actions", []) if report is not None else []
        follow_up_count = len(follow_ups) if isinstance(follow_ups, list) else 0
        recommended_count = len(recommended) if isinstance(recommended, list) else 0
        if follow_up_count or recommended_count:
            return f"follow-up {follow_up_count} 个，recommended actions {recommended_count} 个"
        if any(
            stage in {"targeted", "verification", "attribution", "auto_closure"} for stage in stages
        ):
            return f"已有阶段：{', '.join(stages)}"
        return "未产生 follow-up / recommended actions"

    def report_document_content(
        self,
        *,
        job: DebugJobRow,
        report: DebugReport,
        internal_report_url: str,
    ) -> str:
        closure = self.report_auto_closure_snapshot(job=job, report=report)
        case = self._job_repository().get_case(job.case_id)
        if case is not None:
            source_markdown = build_auto_closure_markdown_report(
                report=report,
                closure=closure,
                original_prompt=case.prompt,
                original_cot_excerpt=self._original_cot_excerpt(case),
                original_prediction=self._original_prediction(case),
                reference_answer=json.dumps(case.expected_output, ensure_ascii=False, indent=2),
                scoring_ops=case.scoring_standard,
            )
            return build_lark_docx_report_xml(
                case_id=report.case_id, source_markdown=source_markdown
            )
        lines = [
            f"# Debug Agent 调试报告 - {report.case_id}",
            "",
            "## 任务信息",
            "",
            f"- 任务编号：`{job.job_id}`",
            f"- 样本追踪号：`{report.case_id}`",
            f"- 任务状态：`{job.status}`",
            f"- 报告详情页：{internal_report_url}",
            "",
            "## 根因判断",
            "",
            f"- 根因标签：`{report.root_cause.label}`",
            f"- 置信度：`{report.root_cause.confidence}`",
            f"- 证据摘要：{report.root_cause.evidence_summary}",
            "",
            "## 错误现象",
            "",
            f"- 类型：`{report.observed_failure.type}`",
            f"- 摘要：{report.observed_failure.summary}",
        ]
        if report.observed_failure.affected_box_ids:
            affected = ", ".join(str(item) for item in report.observed_failure.affected_box_ids)
            lines.append(f"- 受影响区域：{affected}")
        if report.experiment_summary is not None:
            summary = report.experiment_summary
            lines.extend(
                [
                    "",
                    "## 实验摘要",
                    "",
                    f"- 总试次：{summary.total_trials}",
                    f"- 成功试次：{summary.success_count}",
                    f"- 失败试次：{summary.failed_trial_count}",
                    f"- 成功率：{summary.success_rate:.2%}",
                    f"- 稳定性：`{summary.stability_label}`",
                ]
            )
            if summary.step_summaries:
                lines.extend(["", "### 关键实验步骤", ""])
                for step in summary.step_summaries[:20]:
                    step_name = str(step.get("step_name", "unknown"))
                    success_rate = step.get("success_rate", "")
                    lines.append(f"- `{step_name}`：success_rate={success_rate}")
        if report.evidence_citations:
            lines.extend(["", "## 证据引用", ""])
            for citation in report.evidence_citations[:20]:
                evidence_id = str(citation.get("evidence_id", ""))
                summary = str(citation.get("summary", citation.get("reason", "")))
                lines.append(f"- `{evidence_id}`：{summary}")
        if report.recommended_actions:
            lines.extend(["", "## 推荐动作", ""])
            for index, action in enumerate(report.recommended_actions):
                priority = str(action.get("priority", f"P{index}"))
                action_summary = str(action.get("summary", action))
                status = str(action.get("status", "pending"))
                lines.append(f"- `{index}` / `{priority}` / `{status}`：{action_summary}")
        if report.verification_results:
            lines.extend(["", "## 验证结果", ""])
            lines.extend(_markdown_dict_items(report.verification_results))
        if report.strategy_follow_up_results:
            lines.extend(["", "## 策略跟进结果", ""])
            lines.extend(_markdown_dict_items(report.strategy_follow_up_results))
        if report.targeted_probe_results:
            lines.extend(["", "## 定向探针结果", ""])
            lines.extend(_markdown_dict_items(report.targeted_probe_results))
        if report.human_handoff_requests:
            lines.extend(["", "## 人工交接", ""])
            lines.extend(_markdown_dict_items(report.human_handoff_requests))
        if report.final_attributions:
            lines.extend(["", "## 最终归因", ""])
            lines.extend(_markdown_dict_items(report.final_attributions))
        lines.extend(
            [
                "",
                "## 写回字段",
                "",
                f"- 错误原因：{report.suggested_sheet_fields.get('错误原因', report.root_cause.label)}",
                f"- 评估问题反馈：{report.suggested_sheet_fields.get('评估问题反馈', report.root_cause.evidence_summary)}",
            ]
        )
        return build_lark_docx_report_xml(case_id=report.case_id, source_markdown="\n".join(lines))

    def report_auto_closure_snapshot(
        self,
        *,
        job: DebugJobRow,
        report: DebugReport,
    ) -> AutoDebugClosureResult:
        repository = self._job_repository()
        targeted_probe_results = self._build_targeted_probe_results(job.job_id)
        created_targeted_probe_jobs = [
            str(item.get("probe_job_id", ""))
            for item in targeted_probe_results
            if str(item.get("probe_job_id", "")).strip()
        ]
        created_strategy_follow_up_jobs = [
            item.follow_up_job_id
            for item in repository.list_strategy_follow_up_jobs(job.job_id)
            if item.follow_up_job_id
        ]
        created_verification_jobs = [
            item.verification_job_id
            for item in repository.list_recommended_action_verifications(job.job_id)
            if item.verification_job_id
        ]
        final_attribution_candidates = self.report_final_attribution_candidates(report)
        return AutoDebugClosureResult(
            source_job_id=job.job_id,
            created_targeted_probe_jobs=created_targeted_probe_jobs,
            created_strategy_follow_up_jobs=created_strategy_follow_up_jobs,
            created_verification_jobs=created_verification_jobs,
            evidence_summaries=self.report_evidence_summaries(
                [
                    job.job_id,
                    *created_targeted_probe_jobs,
                    *created_strategy_follow_up_jobs,
                    *created_verification_jobs,
                ]
            ),
            targeted_probe_outcomes=[
                {
                    "probe_job_id": str(item.get("probe_job_id", "")),
                    "target_id": str(item.get("target_id", "")),
                    "outcome": str(item.get("outcome", "")),
                    "summary": str(item.get("summary", "")),
                }
                for item in targeted_probe_results
            ],
            final_attribution_candidates=final_attribution_candidates,
            badcase_live_comparison=self.report_badcase_live_comparison(
                job=job,
                report=report,
                final_attribution_candidates=final_attribution_candidates,
            ),
            writeback_status=self.report_writeback_status(job.job_id),
        )

    def report_evidence_summaries(self, job_ids: list[str]) -> list[dict[str, object]]:
        summaries: list[dict[str, object]] = []
        seen: set[tuple[str, str]] = set()
        for job_id in job_ids:
            for evidence in self._job_repository().list_evidence(job_id):
                key = (job_id, evidence.evidence_id)
                if key in seen:
                    continue
                seen.add(key)
                summaries.append(
                    {
                        "job_id": job_id,
                        "evidence_id": evidence.evidence_id,
                        "step_name": evidence.step_name,
                        "trial": str(evidence.trial),
                        "judge_score": str(evidence.judge.score),
                        "delta_reasons": self.report_delta_reasons(evidence),
                        "raw_output_excerpt": _clip_text(evidence.raw_output.strip(), 1200),
                        "model_call_error": evidence.model_call_error_message,
                        "response_parse_error": evidence.response_parse_error,
                    }
                )
        return summaries

    def report_delta_reasons(self, evidence: ExperimentEvidence) -> list[str]:
        reasons: list[str] = []
        for delta in evidence.judge.deltas:
            reason = str(delta.get("reason", ""))
            if reason and reason not in reasons:
                reasons.append(reason)
        return reasons

    def report_final_attribution_candidates(self, report: DebugReport) -> list[dict[str, str]]:
        if report.final_attributions:
            return [
                {
                    "category": str(item.get("category", "human_confirmed_root_cause")),
                    "confidence": str(item.get("confidence", report.root_cause.confidence)),
                    "summary": str(item.get("summary", item.get("recommended_action", ""))),
                }
                for item in report.final_attributions
            ]
        summary = report.experiment_summary
        if report.root_cause.label == "video_timestamp_boundary_error" and summary is not None:
            if 0 < summary.success_count < summary.total_trials:
                return [
                    {
                        "category": "model_instability",
                        "confidence": "high",
                        "summary": (
                            f"Live 复测通过 {summary.success_count}/{summary.total_trials} 次；"
                            "模型具备解题能力，但时间边界输出不稳定或原始约束触发不足。"
                        ),
                    }
                ]
            return [
                {
                    "category": "model_capability_or_asset_gap",
                    "confidence": "medium",
                    "summary": "视频时间边界错误在现有证据中持续出现，需要继续区分模型能力、prompt 约束和评分资产问题。",
                }
            ]
        return [
            {
                "category": report.root_cause.label,
                "confidence": report.root_cause.confidence,
                "summary": report.root_cause.evidence_summary,
            }
        ]

    def report_badcase_live_comparison(
        self,
        *,
        job: DebugJobRow,
        report: DebugReport,
        final_attribution_candidates: list[dict[str, str]],
    ) -> dict[str, str]:
        case = self._job_repository().get_case(job.case_id)
        original_total = len(case.predictions) if case is not None else 0
        original_success = (
            sum(prediction.score for prediction in case.predictions) if case is not None else 0
        )
        original_avg_score = case.avg_score if case is not None else 0.0
        summary = report.experiment_summary
        live_success = summary.success_count if summary is not None else 0
        live_total = summary.total_trials if summary is not None else 0
        live_rate = round((summary.success_rate if summary is not None else 0.0) * 100)
        decision = (
            final_attribution_candidates[0]["category"]
            if final_attribution_candidates
            else report.root_cause.label
        )
        return {
            "original_badcase": f"原 badcase：{original_success}/{original_total} 通过，avg_score={original_avg_score}。",
            "live_rerun": f"Live 复测：{live_success}/{live_total} 通过，success_rate={live_rate}%。",
            "decision": decision,
        }

    def report_writeback_status(self, job_id: str) -> str:
        audit = self._job_repository().get_spreadsheet_writeback_audit(job_id)
        if audit is not None:
            return audit.status
        return "not_requested"

    def completion_writeback_lines(
        self,
        *,
        draft: LarkBotBadcaseDraft,
        job: DebugJobRow,
    ) -> list[str]:
        base_target = self._base_writeback_target(job.job_id)
        if base_target is not None:
            audit = self._job_repository().get_spreadsheet_writeback_audit(job.job_id)
            base_token, table_id, record_id = base_target
            if audit is not None and audit.status == "succeeded" and audit.row_id == record_id:
                return [f"- Base 写回：已写回记录 `{record_id}`。"]
            writeback_url = self._badcase_action_url(draft, "writeback_base")
            if not writeback_url:
                return ["- Base 写回：已定位来源记录，需在 Debug Agent 操作台确认写回。"]
            return [
                f"- Base 写回：待确认，目标 `{base_token}/{table_id}` 记录 `{record_id}`。",
                f"- Base 写回确认：{writeback_url}",
            ]

        target = self._spreadsheet_writeback_target(job.job_id)
        if target is None:
            return []
        audit = self._job_repository().get_spreadsheet_writeback_audit(job.job_id)
        if audit is not None and audit.status == "succeeded":
            return [f"- 表格写回：已写回原表格行 `{audit.row_id}`。"]
        writeback_url = self._badcase_action_url(draft, "writeback_spreadsheet")
        if not writeback_url:
            return ["- 表格写回：已定位来源表格行，需在 Debug Agent 操作台确认写回。"]
        spreadsheet_id, sheet_id, row_id = target
        return [
            f"- 表格写回：待确认，目标 `{spreadsheet_id}/{sheet_id}` 行 `{row_id}`。",
            f"- 写回确认：{writeback_url}",
        ]


def _roles_from_meta_agent_enrichment(enrichment: dict[str, object]) -> list[str]:
    roles: list[str] = []
    agent_roles = enrichment.get("agent_roles")
    if isinstance(agent_roles, list):
        roles.extend(str(role) for role in agent_roles if str(role))
    telemetry = enrichment.get("telemetry")
    if isinstance(telemetry, list):
        for item in telemetry:
            if isinstance(item, dict):
                role = str(item.get("role_id") or item.get("agent_role") or "")
                if role:
                    roles.append(role)
    return roles
