from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import uuid4

from fastapi import HTTPException

from debug_agent.api.debug_batch_routes import (
    DebugBatchViewBuilder,
    submit_debug_batch_jobs,
    update_debug_batch_status,
)
from debug_agent.api.schemas import (
    AutoDebugClosureRequest,
    BatchDebugJobRequest,
    HumanHandoffStatusRequest,
    RecommendedActionStatusRequest,
    RecommendedActionVerificationRequest,
    SpreadsheetRerunRequest,
    SpreadsheetSyncRequest,
    StrategyFollowUpJobRequest,
    TargetedProbeJobRequest,
)
from debug_agent.api.writeback_routes import (
    JobReportBaseWritebackConfirmationRequest,
    JobReportWritebackConfirmationRequest,
)
from debug_agent.jobs.service import DebugJobService
from debug_agent.jobs.worker import AsyncJobWorker
from debug_agent.settings import DebugAgentSettings
from debug_agent.spreadsheets.lark import parse_lark_spreadsheet_reference
from debug_agent.storage.repository import DebugJobRepository, LarkBotPendingCommand


AsyncRunner = Callable[[Callable[[], Awaitable[object] | object]], object]


class LarkPendingCommandExecutionController:
    def __init__(
        self,
        *,
        settings: Callable[[], DebugAgentSettings],
        job_repository: Callable[[], DebugJobRepository],
        job_service: Callable[[], DebugJobService],
        job_worker: Callable[[], AsyncJobWorker],
        debug_batch_view_builder: Callable[[], DebugBatchViewBuilder],
        run_coroutine_from_sync: AsyncRunner,
        usage_budget_guard: Callable[[], None],
        new_artifact_group_id: Callable[[str], str],
        worker_runtime_status: Callable[[], object],
        sync_spreadsheet: Callable[[SpreadsheetSyncRequest], object],
        rerun_spreadsheet: Callable[[SpreadsheetRerunRequest], Awaitable[object]],
        run_spreadsheet_rerun_auto_closures: Callable[..., Awaitable[list[object]]],
        xiaod_spreadsheet_rerun_batch_id: Callable[[str], str],
        mark_xiaod_spreadsheet_rerun_batch_started: Callable[..., None],
        active_xiaod_spreadsheet_rerun_run_for_command: Callable[
            [LarkBotPendingCommand], object | None
        ],
        create_job_report_writeback_confirmation: Callable[..., object],
        create_job_report_base_writeback_confirmation: Callable[..., object],
        update_recommended_action_status: Callable[..., object],
        create_recommended_action_verification_job: Callable[..., object],
        update_human_handoff_status: Callable[..., object],
        create_strategy_follow_up_job: Callable[..., object],
        create_targeted_probe_job: Callable[..., object],
        run_job_auto_debug_closure: Callable[..., Awaitable[object]],
        run_job_auto_debug_closure_report: Callable[..., Awaitable[object]],
    ) -> None:
        self._settings = settings
        self._job_repository = job_repository
        self._job_service = job_service
        self._job_worker = job_worker
        self._debug_batch_view_builder = debug_batch_view_builder
        self._run_coroutine_from_sync = run_coroutine_from_sync
        self._usage_budget_guard = usage_budget_guard
        self._new_artifact_group_id = new_artifact_group_id
        self._worker_runtime_status = worker_runtime_status
        self._sync_spreadsheet = sync_spreadsheet
        self._rerun_spreadsheet = rerun_spreadsheet
        self._run_spreadsheet_rerun_auto_closures = run_spreadsheet_rerun_auto_closures
        self._xiaod_spreadsheet_rerun_batch_id = xiaod_spreadsheet_rerun_batch_id
        self._mark_xiaod_spreadsheet_rerun_batch_started = (
            mark_xiaod_spreadsheet_rerun_batch_started
        )
        self._active_xiaod_spreadsheet_rerun_run_for_command = (
            active_xiaod_spreadsheet_rerun_run_for_command
        )
        self._create_job_report_writeback_confirmation = create_job_report_writeback_confirmation
        self._create_job_report_base_writeback_confirmation = (
            create_job_report_base_writeback_confirmation
        )
        self._update_recommended_action_status = update_recommended_action_status
        self._create_recommended_action_verification_job = (
            create_recommended_action_verification_job
        )
        self._update_human_handoff_status = update_human_handoff_status
        self._create_strategy_follow_up_job = create_strategy_follow_up_job
        self._create_targeted_probe_job = create_targeted_probe_job
        self._run_job_auto_debug_closure = run_job_auto_debug_closure
        self._run_job_auto_debug_closure_report = run_job_auto_debug_closure_report

    def execute(self, command: LarkBotPendingCommand) -> dict[str, object]:
        if command.action_kind == "submit_case":
            return self._execute_submit_case(command)
        if command.action_kind == "submit_batch":
            return self._execute_submit_batch(command)
        if command.action_kind in {"batch_pause", "batch_resume", "batch_cancel"}:
            return self._execute_batch_status(command)
        if command.action_kind == "worker_start":
            self._job_worker().start()
            return {"worker": _model_dump_result(self._worker_runtime_status())}
        if command.action_kind == "worker_stop":
            self._run_coroutine_from_sync(self._job_worker().stop)
            return {"worker": _model_dump_result(self._worker_runtime_status())}
        if command.action_kind == "spreadsheet_sync":
            request = self.spreadsheet_sync_request_from_action(command.action)
            result = self._sync_spreadsheet(request)
            return {"spreadsheet_sync": _model_dump_result(result)}
        if command.action_kind == "spreadsheet_rerun":
            return self._execute_spreadsheet_rerun(command)
        if command.action_kind == "spreadsheet_writeback_confirmation":
            return self._execute_spreadsheet_writeback_confirmation(command)
        if command.action_kind == "base_writeback_confirmation":
            return self._execute_base_writeback_confirmation(command)
        if command.action_kind == "recommended_action_status_update":
            return self._execute_recommended_action_status_update(command)
        if command.action_kind == "recommended_action_verification":
            return self._execute_recommended_action_verification(command)
        if command.action_kind == "human_handoff_status_update":
            return self._execute_human_handoff_status_update(command)
        if command.action_kind == "strategy_followup_job":
            return self._execute_strategy_followup_job(command)
        if command.action_kind == "targeted_probe_job":
            return self._execute_targeted_probe_job(command)
        if command.action_kind == "auto_closure":
            return self._execute_auto_closure(command)
        if command.action_kind == "auto_closure_report":
            return self._execute_auto_closure_report(command)
        raise HTTPException(
            status_code=400, detail=f"Unsupported pending bot command: {command.action_kind}"
        )

    def spreadsheet_sync_request_from_action(
        self, action: dict[str, object]
    ) -> SpreadsheetSyncRequest:
        source = action_string(action, "source")
        sheet_id = action_string(action, "sheet_id")
        if not source:
            raise HTTPException(
                status_code=400, detail="Pending bot command missing spreadsheet source."
            )
        reference = parse_lark_spreadsheet_reference(source, sheet_id=sheet_id or None)
        return SpreadsheetSyncRequest(
            spreadsheet_url=source if source.startswith(("http://", "https://")) else "",
            spreadsheet_id=reference.spreadsheet_id,
            sheet_id=reference.sheet_id,
            create_jobs=True,
        )

    def spreadsheet_rerun_request_from_action(
        self, action: dict[str, object]
    ) -> SpreadsheetRerunRequest:
        source = action_string(action, "source")
        sheet_id = action_string(action, "sheet_id")
        if not source:
            raise HTTPException(
                status_code=400, detail="Pending bot command missing spreadsheet source."
            )
        reference = parse_lark_spreadsheet_reference(source, sheet_id=sheet_id or None)
        row_ids = self.spreadsheet_rerun_execution_row_ids(action)
        return SpreadsheetRerunRequest(
            spreadsheet_url=source if source.startswith(("http://", "https://")) else "",
            spreadsheet_id=reference.spreadsheet_id,
            sheet_id=reference.sheet_id,
            row_ids=row_ids,
            case_ids=action_string_list(action, "case_ids"),
            queue_priority="interactive",
            auto_closure=action_bool(action, "auto_closure") or action_bool(action, "report"),
            submit_controlled_probes=action_bool(action, "submit_controlled_probes"),
            writeback=action_bool(action, "writeback"),
        )

    def spreadsheet_rerun_execution_row_ids(self, action: dict[str, object]) -> list[str]:
        preflight = spreadsheet_rerun_preflight_from_action(action)
        if not preflight:
            return action_string_list(action, "row_ids")
        if preflight.get("status") != "ok":
            raise HTTPException(
                status_code=409,
                detail=f"Spreadsheet row preflight failed: {preflight.get('error') or 'unknown'}",
            )
        valid_row_ids = object_string_list(preflight, "valid_row_ids")
        if not valid_row_ids:
            raise HTTPException(
                status_code=409,
                detail="No valid spreadsheet rows after preflight.",
            )
        return valid_row_ids

    def record_spreadsheet_rerun_execution(
        self,
        *,
        command: LarkBotPendingCommand,
        execution_result: dict[str, object],
    ) -> None:
        result = payload_dict(execution_result.get("spreadsheet_rerun"))
        reports = payload_dict_list(result.get("auto_closure_reports"))
        row_results = self.spreadsheet_rerun_row_results(result=result, reports=reports)
        execution_result["row_results"] = row_results
        report_count = len(reports)
        execution_result["report_count"] = report_count
        writeback_requested = bool(execution_result.get("writeback_requested"))
        decision_pending = writeback_requested and report_count > 0
        execution_result["writeback_decision_status"] = (
            "pending"
            if decision_pending
            else "not_ready"
            if writeback_requested
            else "not_requested"
        )
        existing_run = self._active_xiaod_spreadsheet_rerun_run_for_command(command)
        existing_summary = (
            dict(getattr(existing_run, "summary", {}) or {})
            if existing_run is not None
            else {}
        )
        batch_id = spreadsheet_rerun_batch_id_from_result(result) or payload_string(
            existing_summary.get("batch_id")
        )
        job_ids = [
            payload_string(item.get("job_id"))
            for item in payload_dict_list(result.get("jobs"))
            if payload_string(item.get("job_id"))
        ] or object_string_list(existing_summary, "job_ids")
        stage = ""
        if not job_ids:
            stage = payload_string(existing_summary.get("stage")) or "batch_started"
        summary = {
            **existing_summary,
            "command_id": command.command_id,
            "message_id": command.message_id,
            "chat_id": command.chat_id,
            "open_id": command.open_id,
            "batch_id": batch_id,
            "job_ids": job_ids,
            "row_results": row_results,
            "report_requested": bool(execution_result.get("report_requested")),
            "report_count": report_count,
            "writeback_requested": writeback_requested,
            "writeback_decision_status": execution_result["writeback_decision_status"],
            "auto_closure_reports": reports,
        }
        if stage:
            summary["stage"] = stage
        else:
            summary.pop("stage", None)
        if existing_run is not None:
            run = self._job_repository().complete_xiaod_execution_run(
                str(getattr(existing_run, "run_id", "")),
                status="writeback_decision_pending" if decision_pending else "active",
                summary=summary,
            )
            if run is None:
                run = existing_run
        else:
            run = self._job_repository().create_xiaod_execution_run(
                run_id=str(uuid4()),
                tenant_key=command.tenant_key,
                chat_id=command.chat_id,
                open_id=command.open_id,
                command_id=command.command_id,
                batch_id=batch_id,
                job_id=job_ids[0] if job_ids else "",
                action_kind=command.action_kind,
                status="writeback_decision_pending" if decision_pending else "active",
                summary=summary,
            )
        execution_result["xiaod_run_id"] = run.run_id
        if decision_pending:
            self.create_spreadsheet_rerun_writeback_decision(
                command=command,
                run_id=run.run_id,
                row_results=row_results,
                reports=reports,
            )

    def create_spreadsheet_rerun_writeback_decision(
        self,
        *,
        command: LarkBotPendingCommand,
        run_id: str,
        row_results: list[dict[str, object]],
        reports: list[dict[str, object]],
    ) -> None:
        existing = self._job_repository().get_pending_xiaod_decision(
            tenant_key=command.tenant_key,
            chat_id=command.chat_id,
            open_id=command.open_id,
            decision_kind="spreadsheet_rerun_writeback_sync",
        )
        if existing is not None and existing.command_id == command.command_id:
            return
        decision = self._job_repository().create_xiaod_pending_decision(
            decision_id=str(uuid4()),
            tenant_key=command.tenant_key,
            chat_id=command.chat_id,
            open_id=command.open_id,
            decision_kind="spreadsheet_rerun_writeback_sync",
            command_id=command.command_id,
            run_id=run_id,
            payload={
                "row_results": row_results,
                "report_count": len(reports),
                "default": "no_sync",
            },
            note="Reports generated; waiting for explicit spreadsheet sync decision.",
            expires_at=(datetime.now(UTC) + timedelta(minutes=30)).isoformat(timespec="seconds"),
        )
        self._job_repository().save_xiaod_command_audit(
            tenant_key=command.tenant_key,
            chat_id=command.chat_id,
            open_id=command.open_id,
            command_id=command.command_id,
            run_id=run_id,
            decision_id=decision.decision_id,
            event_kind="spreadsheet_rerun_writeback_decision_created",
            status="pending",
            actor=command.open_id or command.actor,
            reason="reports_ready",
            payload={"row_results": row_results, "report_count": len(reports)},
        )

    def spreadsheet_rerun_row_results(
        self,
        *,
        result: dict[str, object],
        reports: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        imported_rows = payload_dict_list(result.get("imported_rows"))
        jobs = payload_dict_list(result.get("jobs"))
        reports_by_job_id = {
            payload_string(report.get("job_id")): report
            for report in reports
            if payload_string(report.get("job_id"))
        }
        row_results: list[dict[str, object]] = []
        for index, job in enumerate(jobs):
            imported_row = imported_rows[index] if index < len(imported_rows) else {}
            job_id = payload_string(job.get("job_id"))
            case_id = payload_string(job.get("case_id")) or payload_string(
                imported_row.get("case_id")
            )
            mapping = (
                self._job_repository().get_spreadsheet_row_mapping_by_job_id(job_id)
                if job_id
                else None
            )
            report = reports_by_job_id.get(job_id, {})
            row_results.append(
                {
                    "row_id": mapping.row_id
                    if mapping is not None
                    else payload_string(imported_row.get("sheet_row_id")),
                    "case_id": case_id,
                    "job_id": job_id,
                    "job_status": payload_string(job.get("status")) or "unknown",
                    "report_url": payload_string(report.get("report_artifact_url")),
                    "writeback_status": payload_string(report.get("writeback_status"))
                    or "not_ready",
                    "source_mapped": mapping is not None,
                    "spreadsheet_id": mapping.spreadsheet_id if mapping is not None else "",
                    "sheet_id": mapping.sheet_id if mapping is not None else "",
                }
            )
        return row_results

    def _execute_submit_case(self, command: LarkBotPendingCommand) -> dict[str, object]:
        case_id = action_string(command.action, "case_id")
        if not case_id:
            raise HTTPException(status_code=400, detail="Pending bot command missing case_id.")
        self._usage_budget_guard()
        submitted = self._job_service().submit_case_debug(
            case_id,
            baseline_trials=0,
            artifact_group_id="lark-bot",
        )
        return {"submitted_job": submitted.model_dump(mode="json")}

    def _execute_submit_batch(self, command: LarkBotPendingCommand) -> dict[str, object]:
        case_ids = action_string_list(command.action, "case_ids")
        if not case_ids:
            raise HTTPException(status_code=400, detail="Pending bot command missing case_ids.")
        batch_response = submit_debug_batch_jobs(
            request=BatchDebugJobRequest(
                case_ids=case_ids,
                baseline_trials=0,
                max_concurrency=self._settings().queue_max_concurrency,
                max_attempts=self._settings().retry_max_attempts,
            ),
            job_repository=self._job_repository(),
            job_service=self._job_service(),
            view_builder=self._debug_batch_view_builder(),
            raise_if_usage_budget_blocks_submission=self._usage_budget_guard,
            new_artifact_group_id=self._new_artifact_group_id,
        )
        return {"batch": batch_response.model_dump(mode="json")}

    def _execute_batch_status(self, command: LarkBotPendingCommand) -> dict[str, object]:
        batch_id = action_string(command.action, "batch_id")
        if not batch_id:
            raise HTTPException(status_code=400, detail="Pending bot command missing batch_id.")
        status_by_kind: dict[str, Literal["paused", "running", "cancelled"]] = {
            "batch_pause": "paused",
            "batch_resume": "running",
            "batch_cancel": "cancelled",
        }
        return {
            "batch": update_debug_batch_status(
                job_repository=self._job_repository(),
                view_builder=self._debug_batch_view_builder(),
                batch_id=batch_id,
                status=status_by_kind[command.action_kind],
            ).model_dump(mode="json")
        }

    def _execute_spreadsheet_rerun(self, command: LarkBotPendingCommand) -> dict[str, object]:
        request = self.spreadsheet_rerun_request_from_action(command.action)
        report_requested = request.auto_closure
        writeback_requested = request.writeback
        artifact_group_id = request.artifact_group_id or self._xiaod_spreadsheet_rerun_batch_id(
            request.sheet_id
        )
        self._mark_xiaod_spreadsheet_rerun_batch_started(
            command=command,
            batch_id=artifact_group_id,
        )
        execution_request = request.model_copy(
            update={
                "auto_run": False,
                "artifact_group_id": artifact_group_id,
            }
        )
        result = self._run_coroutine_from_sync(lambda: self._rerun_spreadsheet(execution_request))
        auto_closure_reports = []
        result = result.model_copy(update={"auto_closure_reports": auto_closure_reports})
        execution_result = {
            "spreadsheet_rerun": result.model_dump(mode="json"),
            "preflight": spreadsheet_rerun_preflight_from_action(command.action),
            "report_requested": report_requested,
            "writeback_requested": writeback_requested,
            "report_count": len(auto_closure_reports),
            "writeback_decision_status": "pending"
            if writeback_requested and auto_closure_reports
            else "not_ready"
            if writeback_requested
            else "not_requested",
        }
        self.record_spreadsheet_rerun_execution(
            command=command,
            execution_result=execution_result,
        )
        return execution_result

    def _execute_spreadsheet_writeback_confirmation(
        self, command: LarkBotPendingCommand
    ) -> dict[str, object]:
        job_id = action_string(command.action, "job_id")
        if not job_id:
            raise HTTPException(status_code=400, detail="Pending bot command missing job_id.")
        confirmation = self._create_job_report_writeback_confirmation(
            job_id,
            JobReportWritebackConfirmationRequest(
                actor=command.actor,
                note="Created from confirmed XiaoD pending command.",
            ),
        )
        return {"write_confirmation": confirmation.model_dump(mode="json")}

    def _execute_base_writeback_confirmation(
        self, command: LarkBotPendingCommand
    ) -> dict[str, object]:
        job_id = action_string(command.action, "job_id")
        if not job_id:
            raise HTTPException(status_code=400, detail="Pending bot command missing job_id.")
        confirmation = self._create_job_report_base_writeback_confirmation(
            job_id,
            JobReportBaseWritebackConfirmationRequest(
                actor=command.actor,
                note="Created from confirmed XiaoD pending command.",
            ),
        )
        return {"write_confirmation": confirmation.model_dump(mode="json")}

    def _execute_recommended_action_status_update(
        self, command: LarkBotPendingCommand
    ) -> dict[str, object]:
        job_id = action_string(command.action, "job_id")
        action_index = action_int(command.action, "action_index")
        status = action_string(command.action, "status")
        if not job_id or action_index is None or not status:
            raise HTTPException(
                status_code=400,
                detail="Pending bot command missing recommended action status parameters.",
            )
        result = self._update_recommended_action_status(
            job_id,
            action_index,
            RecommendedActionStatusRequest(
                status=status,
                actor=command.actor,
                note=confirmed_command_note(command.action),
            ),
        )
        return {"recommended_action_status": _model_dump_result(result)}

    def _execute_recommended_action_verification(
        self, command: LarkBotPendingCommand
    ) -> dict[str, object]:
        job_id = action_string(command.action, "job_id")
        action_index = action_int(command.action, "action_index")
        if not job_id or action_index is None:
            raise HTTPException(
                status_code=400,
                detail="Pending bot command missing recommended action verification parameters.",
            )
        result = self._create_recommended_action_verification_job(
            job_id,
            action_index,
            RecommendedActionVerificationRequest(
                actor=command.actor,
                note=confirmed_command_note(command.action),
            ),
        )
        return {"recommended_action_verification": _model_dump_result(result)}

    def _execute_human_handoff_status_update(
        self, command: LarkBotPendingCommand
    ) -> dict[str, object]:
        job_id = action_string(command.action, "job_id")
        target_id = action_string(command.action, "target_id")
        status = action_string(command.action, "status")
        if not job_id or not target_id or not status:
            raise HTTPException(
                status_code=400,
                detail="Pending bot command missing human handoff status parameters.",
            )
        result = self._update_human_handoff_status(
            job_id,
            target_id,
            HumanHandoffStatusRequest(
                status=status,
                actor=command.actor,
                note=confirmed_command_note(command.action),
            ),
        )
        return {"human_handoff_status": _model_dump_result(result)}

    def _execute_strategy_followup_job(self, command: LarkBotPendingCommand) -> dict[str, object]:
        job_id = action_string(command.action, "job_id")
        stage = action_string(command.action, "stage")
        if not job_id or not stage:
            raise HTTPException(
                status_code=400,
                detail="Pending bot command missing strategy follow-up parameters.",
            )
        result = self._create_strategy_follow_up_job(
            job_id,
            stage,
            StrategyFollowUpJobRequest(
                actor=command.actor,
                note=confirmed_command_note(command.action),
            ),
        )
        return {"strategy_followup": _model_dump_result(result)}

    def _execute_targeted_probe_job(self, command: LarkBotPendingCommand) -> dict[str, object]:
        job_id = action_string(command.action, "job_id")
        target_id = action_string(command.action, "target_id")
        if not job_id or not target_id:
            raise HTTPException(
                status_code=400,
                detail="Pending bot command missing targeted probe parameters.",
            )
        result = self._create_targeted_probe_job(
            job_id,
            target_id,
            TargetedProbeJobRequest(
                actor=command.actor,
                note=confirmed_command_note(command.action),
            ),
        )
        return {"targeted_probe": _model_dump_result(result)}

    def _execute_auto_closure(self, command: LarkBotPendingCommand) -> dict[str, object]:
        job_id = action_string(command.action, "job_id")
        if not job_id:
            raise HTTPException(status_code=400, detail="Pending bot command missing job_id.")
        result = self._run_coroutine_from_sync(
            lambda: self._run_job_auto_debug_closure(
                job_id,
                AutoDebugClosureRequest(
                    actor=command.actor,
                    note=confirmed_command_note(command.action),
                    writeback=action_bool(command.action, "writeback"),
                    report_url=action_string(command.action, "report_url"),
                    submit_controlled_probes=action_bool(
                        command.action, "submit_controlled_probes"
                    ),
                ),
            )
        )
        return {"auto_closure": _model_dump_result(result)}

    def _execute_auto_closure_report(self, command: LarkBotPendingCommand) -> dict[str, object]:
        job_id = action_string(command.action, "job_id")
        if not job_id:
            raise HTTPException(status_code=400, detail="Pending bot command missing job_id.")
        result = self._run_coroutine_from_sync(
            lambda: self._run_job_auto_debug_closure_report(
                job_id,
                AutoDebugClosureRequest(
                    actor=command.actor,
                    note=confirmed_command_note(command.action),
                    writeback=action_bool(command.action, "writeback"),
                    report_url=action_string(command.action, "report_url"),
                    submit_controlled_probes=action_bool(
                        command.action, "submit_controlled_probes"
                    ),
                ),
            )
        )
        return {"auto_closure_report": _model_dump_result(result)}


def spreadsheet_rerun_preflight_from_action(action: dict[str, object]) -> dict[str, object]:
    parameters = action.get("parameters")
    if not isinstance(parameters, dict):
        return {}
    preflight = parameters.get("preflight")
    return dict(preflight) if isinstance(preflight, dict) else {}


def spreadsheet_rerun_batch_id_from_result(result: dict[str, object]) -> str:
    batch = payload_dict(result.get("batch"))
    nested_batch = payload_dict(batch.get("batch"))
    batch_id = payload_string(nested_batch.get("batch_id")) or payload_string(batch.get("batch_id"))
    if batch_id:
        return batch_id
    jobs = payload_dict_list(result.get("jobs"))
    return payload_string(jobs[0].get("artifact_group_id")) if jobs else ""


def payload_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def payload_dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def payload_string(value: object) -> str:
    return value.strip() if isinstance(value, str) else str(value).strip() if value else ""


def confirmed_command_note(action: dict[str, object]) -> str:
    return action_string(action, "note") or "Created from confirmed XiaoD pending command."


def action_string(action: dict[str, object], key: str) -> str:
    parameters = action.get("parameters")
    if not isinstance(parameters, dict):
        return ""
    value = parameters.get(key)
    return value.strip() if isinstance(value, str) else str(value).strip() if value else ""


def action_string_list(action: dict[str, object], key: str) -> list[str]:
    parameters = action.get("parameters")
    if not isinstance(parameters, dict):
        return []
    value = parameters.get(key)
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def action_int(action: dict[str, object], key: str) -> int | None:
    parameters = action.get("parameters")
    if not isinstance(parameters, dict):
        return None
    value = parameters.get(key)
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def action_bool(action: dict[str, object], key: str) -> bool:
    parameters = action.get("parameters")
    if not isinstance(parameters, dict):
        return False
    value = parameters.get(key)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "on", "写回"}
    return False


def object_string_list(payload: dict[str, object], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _model_dump_result(value: object) -> dict[str, object]:
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(mode="json")
        return dumped if isinstance(dumped, dict) else {"value": dumped}
    if isinstance(value, dict):
        return value
    return {"value": str(value)}
