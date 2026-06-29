from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import HTTPException

from debug_agent.lark.bot import LarkBotCommandAction


class XiaoDActionSummaryReader:
    def __init__(
        self,
        *,
        report_base_url: Callable[[], str],
        http_exception_detail_text: Callable[[object], str],
        operations_readiness: Callable[[], Any],
        pilot_gate: Callable[[], Any],
        observability_summary: Callable[[], Any],
        artifact_retention_status: Callable[[int], Any],
        list_cases: Callable[[int], Any],
        worker_runtime_status: Callable[[], Any],
        count_jobs: Callable[[str], int],
        performance_summary: Callable[[], Any],
        model_catalog: Callable[[], Any],
        lark_preflight: Callable[[], Any],
        lark_go_live_gate: Callable[[], Any],
        lark_permission_checklist: Callable[[], Any],
        lark_scope_check: Callable[[], Any],
        lark_spreadsheet_status: Callable[[], Any],
        lark_operation_audits: Callable[[int], list[Any]],
        badcase_drafts: Callable[[int], list[Any]],
        pending_commands: Callable[[int], list[Any]],
        writeback_audit_summary: Callable[[], Any],
        list_jobs: Callable[[int, str], Any],
        get_job_status: Callable[[str], Any],
        get_job_report: Callable[[str], Any],
        get_job_evidence_ledger: Callable[[str], Any],
        get_job_run_stages: Callable[[str], Any],
        recommended_action_statuses: Callable[[str], Any],
        human_handoff_statuses: Callable[[str], Any],
        strategy_followups: Callable[[str], Any],
        targeted_probes: Callable[[str], Any],
        debug_batches: Callable[[int], Any],
        debug_batch_comparison: Callable[[int], Any],
        debug_batch: Callable[[str], Any],
    ) -> None:
        self._report_base_url = report_base_url
        self._http_exception_detail_text = http_exception_detail_text
        self._operations_readiness = operations_readiness
        self._pilot_gate = pilot_gate
        self._observability_summary = observability_summary
        self._artifact_retention_status = artifact_retention_status
        self._list_cases = list_cases
        self._worker_runtime_status = worker_runtime_status
        self._count_jobs = count_jobs
        self._performance_summary = performance_summary
        self._model_catalog = model_catalog
        self._lark_preflight = lark_preflight
        self._lark_go_live_gate = lark_go_live_gate
        self._lark_permission_checklist = lark_permission_checklist
        self._lark_scope_check = lark_scope_check
        self._lark_spreadsheet_status = lark_spreadsheet_status
        self._lark_operation_audits = lark_operation_audits
        self._badcase_drafts = badcase_drafts
        self._pending_commands = pending_commands
        self._writeback_audit_summary = writeback_audit_summary
        self._list_jobs = list_jobs
        self._get_job_status = get_job_status
        self._get_job_report = get_job_report
        self._get_job_evidence_ledger = get_job_evidence_ledger
        self._get_job_run_stages = get_job_run_stages
        self._recommended_action_statuses = recommended_action_statuses
        self._human_handoff_statuses = human_handoff_statuses
        self._strategy_followups = strategy_followups
        self._targeted_probes = targeted_probes
        self._debug_batches = debug_batches
        self._debug_batch_comparison = debug_batch_comparison
        self._debug_batch = debug_batch

    def read(self, *, action: LarkBotCommandAction) -> list[str]:
        try:
            return self.read_unchecked(action=action)
        except HTTPException as exc:
            return ["", f"读取结果失败：{self._http_exception_detail_text(exc.detail)}"]
        except Exception as exc:
            return ["", f"读取结果失败：{str(exc)[:300]}"]

    def read_unchecked(self, *, action: LarkBotCommandAction) -> list[str]:
        kind = action.kind
        if kind == "readiness":
            data = self._operations_readiness()
            warnings = [check for check in data.checks if check.status in {"warning", "critical"}]
            return ["", f"运行就绪：`{data.level}`，需关注/严重项 {len(warnings)} 个。"]
        if kind == "pilot_gate":
            data = self._pilot_gate()
            return ["", f"试点门禁：`{data.status}`。"]
        if kind == "observability_summary":
            data = self._observability_summary()
            return [
                "",
                "观测总览："
                f"健康 `{data.health.level}`，任务总数 {data.jobs.total_count}，"
                f"待处理 {data.jobs.pending_count}，运行中 {data.jobs.running_count}，失败 {data.jobs.failed_count}。",
            ]
        if kind == "artifact_retention":
            data = self._artifact_retention_status(5)
            return [
                "",
                "产物保留："
                f"文件 {data.total_file_count} 个，约 {data.total_size_bytes} bytes；"
                f"可清理 {data.eligible_file_count} 个，约 {data.eligible_size_bytes} bytes。",
            ]
        if kind == "case_list":
            data = self._list_cases(10)
            latest = data.cases[0].case_id if data.cases else "暂无"
            return [
                "",
                f"样本列表：总数 {data.total_count}，当前返回 {len(data.cases)} 条；首条 `{latest}`。",
            ]
        if kind == "worker_status":
            data = self._worker_runtime_status()
            worker_state = "running" if data.running else "stopped"
            pending_count = self._count_jobs("pending")
            return [
                "",
                f"Worker：`{worker_state}`，运行中 {data.active_count}，待处理 {pending_count}。",
            ]
        if kind == "performance_summary":
            data = self._performance_summary()
            return ["", f"性能事件总数：`{data.total_count}`，聚合项 {len(data.aggregates)} 个。"]
        if kind == "model_catalog":
            data = self._model_catalog()
            return [
                "",
                f"模型目录：可选模型 {len(data.runtime.catalog)} 个；`model_runner` 保持 source replay 锁定。",
            ]
        if kind == "lark_preflight":
            data = self._lark_preflight()
            blocking = [check for check in data.checks if check.status in {"blocked", "critical"}]
            return ["", f"机器人预检：阻塞项 {len(blocking)} 个，事件模式 `{data.event_mode}`。"]
        if kind == "lark_go_live_gate":
            data = self._lark_go_live_gate()
            return ["", f"机器人真实上线门禁：`{data.status}`。"]
        if kind == "lark_permission_checklist":
            data = self._lark_permission_checklist()
            return ["", f"Lark 权限清单：机器人必需权限 {len(data.required_scopes)} 项。"]
        if kind == "lark_scope_check":
            data = self._lark_scope_check()
            return [
                "",
                "Lark Scope 检查："
                f"需求 {len(data.requirements)} 项，近期缺失 scope {len(data.recent_missing_scopes)} 个。",
            ]
        if kind == "lark_spreadsheet_status":
            data = self._lark_spreadsheet_status()
            configured = "configured" if data.configured else "not_configured"
            return [
                "",
                f"飞书表格连接：`{configured}`，connector `{data.connector_mode}/{data.connector_identity}/{data.connector_profile or 'default'}`。",
            ]
        if kind == "lark_operation_audits":
            audits = self._lark_operation_audits(10)
            return ["", f"Lark 操作审计：最近 {len(audits)} 条。"]
        if kind == "badcase_drafts":
            drafts = self._badcase_drafts(10)
            return ["", f"飞书 badcase 草稿：最近 {len(drafts)} 条。"]
        if kind == "pending_commands":
            commands = self._pending_commands(10)
            pending_count = sum(1 for command in commands if command.status == "pending")
            return [
                "",
                f"待确认机器人命令：最近 {len(commands)} 条，其中 pending {pending_count} 条。",
            ]
        if kind == "writeback_audits":
            data = self._writeback_audit_summary()
            return [
                "",
                "表格写回审计："
                f"成功 {data.by_status.get('succeeded', 0)}，失败 {data.by_status.get('failed', 0)}，"
                f"跳过 {data.by_status.get('skipped', 0)}。",
            ]
        if kind == "debug_jobs_export":
            return [
                "",
                f"DebugJob 导出包：{self._report_base_url().rstrip('/')}/api/exports/debug-jobs.zip",
            ]
        if kind == "support_bundle":
            return [
                "",
                f"运维支持包：{self._report_base_url().rstrip('/')}/api/operations/support-bundle.zip",
            ]
        if kind == "database_backup":
            return [
                "",
                "数据库备份包包含 case、报告、审计和运行状态数据；请只在受控环境下载。",
                f"链接：{self._report_base_url().rstrip('/')}/api/operations/database-backup.zip",
            ]
        if kind == "job_list":
            data = self._list_jobs(10, "created_at_desc")
            latest = data.jobs[0].job_id if data.jobs else "暂无"
            return [
                "",
                f"任务列表：总数 {data.total_count}，最近返回 {len(data.jobs)} 条；最新任务 `{latest}`。",
            ]
        job_id = str(action.parameters.get("job_id", ""))
        if kind == "job_status":
            data = self._get_job_status(job_id)
            return ["", f"任务状态：`{data.status}`。"]
        if kind == "job_report":
            data = self._get_job_report(job_id)
            return [
                "",
                f"任务报告：根因 `{data.root_cause.label}`，置信度 `{data.root_cause.confidence}`。",
            ]
        if kind == "job_evidence":
            data = self._get_job_evidence_ledger(job_id)
            return ["", f"证据账本：记录 {len(data.records)} 条。"]
        if kind == "job_run_stages":
            data = self._get_job_run_stages(job_id)
            return ["", f"运行阶段：{len(data.stages)} 个阶段。"]
        if kind == "recommended_action_statuses":
            data = self._recommended_action_statuses(job_id)
            return [
                "",
                "推荐动作状态："
                f"状态 {len(data.statuses)} 条，事件 {len(data.events)} 条，验证 {len(data.verifications)} 个。",
            ]
        if kind == "human_handoff_statuses":
            data = self._human_handoff_statuses(job_id)
            return ["", f"人工交接状态：记录 {len(data.statuses)} 条。"]
        if kind == "strategy_followups":
            data = self._strategy_followups(job_id)
            return ["", f"策略跟进任务：记录 {len(data.follow_ups)} 条。"]
        if kind == "targeted_probes":
            data = self._targeted_probes(job_id)
            return ["", f"定向探针任务：记录 {len(data.probes)} 条。"]
        batch_id = str(action.parameters.get("batch_id", ""))
        if kind == "batch_list":
            data = self._debug_batches(10)
            latest = data.batches[0].batch.batch_id if data.batches else "暂无"
            return ["", f"批次列表：最近 {len(data.batches)} 条；最新批次 `{latest}`。"]
        if kind == "batch_comparison":
            data = self._debug_batch_comparison(2)
            return [
                "",
                f"批次对比：参与 {len(data.items)} 个批次，最佳批次 `{data.best_batch_id or '暂无'}`。",
            ]
        if kind == "batch_status":
            data = self._debug_batch(batch_id)
            return ["", f"批次状态：`{data.batch.status}`。"]
        return []
