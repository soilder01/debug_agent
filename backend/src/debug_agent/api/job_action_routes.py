from __future__ import annotations

import json
from collections.abc import Callable

from fastapi import APIRouter, HTTPException

from debug_agent.api.schemas import (
    AutoDebugClosureReportResponse,
    AutoDebugClosureRequest,
    HumanHandoffStatusListResponse,
    HumanHandoffStatusRequest,
    RecommendedActionStatusListResponse,
    RecommendedActionStatusRequest,
    RecommendedActionVerificationRequest,
    RecommendedActionVerificationResponse,
    RecommendedActionVerificationResult,
    StrategyFollowUpJobListResponse,
    StrategyFollowUpJobRequest,
    StrategyFollowUpJobResponse,
    StrategyFollowUpJobWithOutcome,
    TargetedProbeJobListResponse,
    TargetedProbeJobRequest,
    TargetedProbeJobResponse,
    TargetedProbeJobWithOutcome,
)
from debug_agent.cases.models import DebugCase
from debug_agent.jobs.auto_closure import (
    AutoDebugClosureResult,
    LocalVideoClipper,
    run_auto_debug_closure,
)
from debug_agent.jobs.auto_closure_report import build_auto_closure_markdown_report
from debug_agent.jobs.service import DebugJobService
from debug_agent.reports.generator import DebugReport
from debug_agent.reports.job_report import (
    build_recommended_action_verification_results,
    build_report_for_job,
    build_strategy_follow_up_results,
    build_targeted_probe_results,
)
from debug_agent.spreadsheets.writeback import SpreadsheetWritebackClient
from debug_agent.storage.models import DebugJobRow
from debug_agent.storage.repository import (
    DebugJobRepository,
    HumanHandoffStatus,
    RecommendedActionStatus,
)
from debug_agent.telemetry.performance import measure_performance


class JobActionRouteController:
    def __init__(
        self,
        *,
        job_repository: DebugJobRepository,
        job_service: Callable[[], DebugJobService],
        spreadsheet_writeback_client: Callable[[], SpreadsheetWritebackClient | None],
        resolved_actor: Callable[[str], str],
        raise_if_usage_budget_blocks_submission: Callable[[], None],
        video_clipper_for_job: Callable[[str], LocalVideoClipper],
        save_auto_closure_run_stages: Callable[..., None],
        persist_auto_closure_markdown_report: Callable[..., str],
        original_cot_excerpt: Callable[[DebugCase], str],
        original_prediction: Callable[[DebugCase], str],
    ) -> None:
        self._job_repository = job_repository
        self._job_service = job_service
        self._spreadsheet_writeback_client = spreadsheet_writeback_client
        self._resolved_actor = resolved_actor
        self._raise_if_usage_budget_blocks_submission = raise_if_usage_budget_blocks_submission
        self._video_clipper_for_job = video_clipper_for_job
        self._save_auto_closure_run_stages = save_auto_closure_run_stages
        self._persist_auto_closure_markdown_report = persist_auto_closure_markdown_report
        self._original_cot_excerpt = original_cot_excerpt
        self._original_prediction = original_prediction

    def update_recommended_action_status(
        self,
        *,
        job_id: str,
        action_index: int,
        request: RecommendedActionStatusRequest,
    ) -> RecommendedActionStatus:
        report = self._require_report(job_id)
        if action_index < 0 or action_index >= len(report.recommended_actions):
            raise HTTPException(
                status_code=404, detail=f"Recommended action not found: {action_index}"
            )
        actor = self._resolved_actor(request.actor)
        return self._job_repository.save_recommended_action_status(
            job_id=job_id,
            action_index=action_index,
            status=request.status,
            actor=actor,
            note=request.note,
        )

    def create_recommended_action_verification_job(
        self,
        *,
        job_id: str,
        action_index: int,
        request: RecommendedActionVerificationRequest,
    ) -> RecommendedActionVerificationResponse:
        job, report = self._require_job_and_report(job_id)
        if action_index < 0 or action_index >= len(report.recommended_actions):
            raise HTTPException(
                status_code=404, detail=f"Recommended action not found: {action_index}"
            )
        actor = self._resolved_actor(request.actor)
        self._raise_if_usage_budget_blocks_submission()
        verification_job = self._job_service().submit_case_debug(
            job.case_id,
            baseline_trials=job.baseline_trials,
            artifact_group_id=job.artifact_group_id,
        )
        verification = self._job_repository.save_recommended_action_verification(
            job_id=job_id,
            action_index=action_index,
            verification_job_id=verification_job.job_id,
            actor=actor,
            note=request.note,
        )
        return RecommendedActionVerificationResponse(
            **verification.model_dump(),
            verification_job=verification_job,
        )

    def create_strategy_follow_up_job(
        self,
        *,
        job_id: str,
        stage: str,
        request: StrategyFollowUpJobRequest,
    ) -> StrategyFollowUpJobResponse:
        job, report = self._require_job_and_report(job_id)
        follow_up = _strategy_follow_up_from_report(report, stage)
        if follow_up is None:
            raise HTTPException(
                status_code=404, detail=f"Strategy follow-up stage not found: {stage}"
            )
        return self._create_strategy_job(
            job=job,
            job_id=job_id,
            stage=stage,
            planned_steps=str(follow_up.get("planned_steps", "")),
            request=request,
        )

    def create_final_attribution_verification_job(
        self,
        *,
        job_id: str,
        target_id: str,
        request: StrategyFollowUpJobRequest,
    ) -> StrategyFollowUpJobResponse:
        job, report = self._require_job_and_report(job_id)
        follow_up = _final_attribution_follow_up_from_report(report, target_id)
        if follow_up is None:
            raise HTTPException(
                status_code=404, detail=f"Final attribution follow-up not found: {target_id}"
            )
        return self._create_strategy_job(
            job=job,
            job_id=job_id,
            stage=f"final_attribution:{target_id}",
            planned_steps=str(follow_up.get("planned_steps", "")),
            request=request,
        )

    def create_final_attribution_recovery_job(
        self,
        *,
        job_id: str,
        target_id: str,
        request: StrategyFollowUpJobRequest,
    ) -> StrategyFollowUpJobResponse:
        job, report = self._require_job_and_report(job_id)
        follow_up = _final_attribution_recovery_follow_up_from_report(report, target_id)
        if follow_up is None:
            raise HTTPException(
                status_code=404,
                detail=f"Final attribution recovery follow-up not found: {target_id}",
            )
        return self._create_strategy_job(
            job=job,
            job_id=job_id,
            stage=f"final_attribution_recovery:{target_id}",
            planned_steps=str(follow_up.get("planned_steps", "")),
            request=request,
        )

    def create_final_attribution_reinvestigation_job(
        self,
        *,
        job_id: str,
        target_id: str,
        request: StrategyFollowUpJobRequest,
    ) -> StrategyFollowUpJobResponse:
        job, report = self._require_job_and_report(job_id)
        follow_up = _final_attribution_reinvestigation_follow_up_from_report(report, target_id)
        if follow_up is None:
            raise HTTPException(
                status_code=404,
                detail=f"Final attribution reinvestigation follow-up not found: {target_id}",
            )
        return self._create_strategy_job(
            job=job,
            job_id=job_id,
            stage=f"final_attribution_reinvestigation:{target_id}",
            planned_steps=str(follow_up.get("planned_steps", "")),
            request=request,
        )

    def list_strategy_follow_up_jobs(self, job_id: str) -> StrategyFollowUpJobListResponse:
        self._require_job(job_id)
        return StrategyFollowUpJobListResponse(
            follow_ups=[
                StrategyFollowUpJobWithOutcome.model_validate(follow_up)
                for follow_up in build_strategy_follow_up_results(self._job_repository, job_id)
            ]
        )

    def create_targeted_probe_job(
        self,
        *,
        job_id: str,
        target_id: str,
        request: TargetedProbeJobRequest,
    ) -> TargetedProbeJobResponse:
        job, report = self._require_job_and_report(job_id)
        follow_up = _targeted_probe_from_report(report, target_id)
        if follow_up is None:
            raise HTTPException(status_code=404, detail=f"Targeted probe not found: {target_id}")
        if follow_up.get("source") == "targeted_probe_guardrail":
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Targeted probe stopped by guardrail for {target_id}: "
                    f"{follow_up.get('stop_condition')}"
                ),
            )
        actor = self._resolved_actor(request.actor)
        self._raise_if_usage_budget_blocks_submission()
        probe_job = self._job_service().submit_case_debug(
            job.case_id,
            baseline_trials=job.baseline_trials,
            artifact_group_id=job.artifact_group_id,
        )
        lineage = self._job_repository.save_targeted_probe_job(
            source_job_id=job_id,
            target_id=target_id,
            planned_steps=str(follow_up.get("planned_steps", "")),
            probe_job_id=probe_job.job_id,
            source=str(follow_up.get("source", "targeted_probe")),
            parent_probe_job_id=str(follow_up.get("parent_probe_job_id", "")),
            trigger_outcome=str(follow_up.get("result", "")),
            actor=actor,
            note=request.note,
        )
        return TargetedProbeJobResponse(
            **lineage.model_dump(),
            probe_job=probe_job,
        )

    def list_targeted_probe_jobs(self, job_id: str) -> TargetedProbeJobListResponse:
        self._require_job(job_id)
        return TargetedProbeJobListResponse(
            probes=[
                TargetedProbeJobWithOutcome.model_validate(probe)
                for probe in build_targeted_probe_results(self._job_repository, job_id)
            ]
        )

    async def run_job_auto_debug_closure(
        self,
        *,
        job_id: str,
        request: AutoDebugClosureRequest,
    ) -> AutoDebugClosureResult:
        self._require_job(job_id)
        actor = self._resolved_actor(request.actor)
        self._raise_if_usage_budget_blocks_submission()
        with measure_performance(
            component="auto_closure",
            operation="run_auto_debug_closure",
            metadata={"job_id": job_id, "writeback": request.writeback},
        ):
            closure = await run_auto_debug_closure(
                repository=self._job_repository,
                job_service=self._job_service(),
                job_id=job_id,
                actor=actor,
                writeback_client=self._spreadsheet_writeback_client()
                if request.writeback
                else None,
                video_clipper=self._video_clipper_for_job(job_id),
                report_url=request.report_url,
                submit_controlled_probes=request.submit_controlled_probes,
            )
            self._save_auto_closure_run_stages(
                repository=self._job_repository,
                job_id=job_id,
                closure=closure,
            )
            return closure

    async def run_job_auto_debug_closure_report(
        self,
        *,
        job_id: str,
        request: AutoDebugClosureRequest,
    ) -> AutoDebugClosureReportResponse:
        job, report = self._require_job_and_report(job_id)
        case = self._job_repository.get_case(job.case_id)
        if case is None:
            raise HTTPException(status_code=404, detail=f"Debug case not found: {job.case_id}")
        actor = self._resolved_actor(request.actor)
        self._raise_if_usage_budget_blocks_submission()
        with measure_performance(
            component="auto_closure",
            operation="build_auto_closure_report",
            metadata={"job_id": job_id, "writeback": request.writeback},
        ):
            closure = await run_auto_debug_closure(
                repository=self._job_repository,
                job_service=self._job_service(),
                job_id=job_id,
                actor=actor,
                writeback_client=self._spreadsheet_writeback_client()
                if request.writeback
                else None,
                video_clipper=self._video_clipper_for_job(job_id),
                report_url=request.report_url,
                submit_controlled_probes=request.submit_controlled_probes,
            )
            markdown = build_auto_closure_markdown_report(
                report=report,
                closure=closure,
                original_prompt=case.prompt,
                original_cot_excerpt=self._original_cot_excerpt(case),
                original_prediction=self._original_prediction(case),
                reference_answer=json.dumps(case.expected_output, ensure_ascii=False, indent=2),
                scoring_ops=case.scoring_standard,
            )
            report_artifact_url = self._persist_auto_closure_markdown_report(
                job_id=job_id,
                case_id=case.case_id,
                markdown=markdown,
            )
            self._save_auto_closure_run_stages(
                repository=self._job_repository,
                job_id=job_id,
                closure=closure,
            )
        return AutoDebugClosureReportResponse(
            source_job_id=job_id,
            closure=closure,
            markdown=markdown,
            report_artifact_url=report_artifact_url,
        )

    def update_human_handoff_status(
        self,
        *,
        job_id: str,
        target_id: str,
        request: HumanHandoffStatusRequest,
    ) -> HumanHandoffStatus:
        report = self._require_report(job_id)
        if not any(item.get("target_id") == target_id for item in report.human_handoff_requests):
            raise HTTPException(
                status_code=404, detail=f"Human handoff target not found: {target_id}"
            )
        actor = self._resolved_actor(request.actor)
        return self._job_repository.save_human_handoff_status(
            job_id=job_id,
            target_id=target_id,
            status=request.status,
            actor=actor,
            note=request.note,
        )

    def list_human_handoff_statuses(self, job_id: str) -> HumanHandoffStatusListResponse:
        self._require_job(job_id)
        return HumanHandoffStatusListResponse(
            statuses=self._job_repository.list_human_handoff_statuses(job_id)
        )

    def list_recommended_action_statuses(self, job_id: str) -> RecommendedActionStatusListResponse:
        self._require_job(job_id)
        verifications = self._job_repository.list_recommended_action_verifications(job_id)
        return RecommendedActionStatusListResponse(
            statuses=self._job_repository.list_recommended_action_statuses(job_id),
            events=self._job_repository.list_recommended_action_status_events(job_id),
            verifications=verifications,
            verification_results=[
                RecommendedActionVerificationResult.model_validate(result)
                for result in build_recommended_action_verification_results(
                    self._job_repository, job_id
                )
            ],
        )

    def _create_strategy_job(
        self,
        *,
        job: DebugJobRow,
        job_id: str,
        stage: str,
        planned_steps: str,
        request: StrategyFollowUpJobRequest,
    ) -> StrategyFollowUpJobResponse:
        actor = self._resolved_actor(request.actor)
        self._raise_if_usage_budget_blocks_submission()
        follow_up_job = self._job_service().submit_case_debug(
            job.case_id,
            baseline_trials=job.baseline_trials,
            artifact_group_id=job.artifact_group_id,
        )
        lineage = self._job_repository.save_strategy_follow_up_job(
            source_job_id=job_id,
            stage=stage,
            planned_steps=planned_steps,
            follow_up_job_id=follow_up_job.job_id,
            actor=actor,
            note=request.note,
        )
        return StrategyFollowUpJobResponse(
            **lineage.model_dump(),
            follow_up_job=follow_up_job,
        )

    def _require_job(self, job_id: str) -> DebugJobRow:
        job = self._job_repository.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"Debug job not found: {job_id}")
        return job

    def _require_report(self, job_id: str) -> DebugReport:
        self._require_job(job_id)
        report = build_report_for_job(self._job_repository, job_id)
        if report is None:
            raise HTTPException(status_code=404, detail=f"Debug report not found for job: {job_id}")
        return report

    def _require_job_and_report(self, job_id: str) -> tuple[DebugJobRow, DebugReport]:
        job = self._require_job(job_id)
        report = build_report_for_job(self._job_repository, job_id)
        if report is None:
            raise HTTPException(status_code=404, detail=f"Debug report not found for job: {job_id}")
        return job, report


def build_job_action_router(controller: JobActionRouteController) -> APIRouter:
    router = APIRouter()

    @router.patch("/jobs/{job_id}/recommended-actions/{action_index}/status")
    def update_recommended_action_status(
        job_id: str,
        action_index: int,
        request: RecommendedActionStatusRequest,
    ) -> RecommendedActionStatus:
        return controller.update_recommended_action_status(
            job_id=job_id, action_index=action_index, request=request
        )

    @router.post(
        "/jobs/{job_id}/recommended-actions/{action_index}/verification-jobs",
        status_code=202,
    )
    def create_recommended_action_verification_job(
        job_id: str,
        action_index: int,
        request: RecommendedActionVerificationRequest,
    ) -> RecommendedActionVerificationResponse:
        return controller.create_recommended_action_verification_job(
            job_id=job_id, action_index=action_index, request=request
        )

    @router.post("/jobs/{job_id}/strategy-follow-ups/{stage}/debug-jobs", status_code=202)
    def create_strategy_follow_up_job(
        job_id: str,
        stage: str,
        request: StrategyFollowUpJobRequest,
    ) -> StrategyFollowUpJobResponse:
        return controller.create_strategy_follow_up_job(job_id=job_id, stage=stage, request=request)

    @router.post(
        "/jobs/{job_id}/final-attributions/{target_id}/verification-jobs",
        status_code=202,
    )
    def create_final_attribution_verification_job(
        job_id: str,
        target_id: str,
        request: StrategyFollowUpJobRequest,
    ) -> StrategyFollowUpJobResponse:
        return controller.create_final_attribution_verification_job(
            job_id=job_id, target_id=target_id, request=request
        )

    @router.post(
        "/jobs/{job_id}/final-attribution-recoveries/{target_id}/debug-jobs",
        status_code=202,
    )
    def create_final_attribution_recovery_job(
        job_id: str,
        target_id: str,
        request: StrategyFollowUpJobRequest,
    ) -> StrategyFollowUpJobResponse:
        return controller.create_final_attribution_recovery_job(
            job_id=job_id, target_id=target_id, request=request
        )

    @router.post(
        "/jobs/{job_id}/final-attribution-reinvestigations/{target_id}/debug-jobs",
        status_code=202,
    )
    def create_final_attribution_reinvestigation_job(
        job_id: str,
        target_id: str,
        request: StrategyFollowUpJobRequest,
    ) -> StrategyFollowUpJobResponse:
        return controller.create_final_attribution_reinvestigation_job(
            job_id=job_id, target_id=target_id, request=request
        )

    @router.get("/jobs/{job_id}/strategy-follow-ups")
    def list_strategy_follow_up_jobs(job_id: str) -> StrategyFollowUpJobListResponse:
        return controller.list_strategy_follow_up_jobs(job_id)

    @router.post("/jobs/{job_id}/targeted-probes/{target_id}/debug-jobs", status_code=202)
    def create_targeted_probe_job(
        job_id: str,
        target_id: str,
        request: TargetedProbeJobRequest,
    ) -> TargetedProbeJobResponse:
        return controller.create_targeted_probe_job(
            job_id=job_id, target_id=target_id, request=request
        )

    @router.get("/jobs/{job_id}/targeted-probes")
    def list_targeted_probe_jobs(job_id: str) -> TargetedProbeJobListResponse:
        return controller.list_targeted_probe_jobs(job_id)

    @router.post("/jobs/{job_id}/auto-closure", status_code=202)
    async def run_job_auto_debug_closure(
        job_id: str,
        request: AutoDebugClosureRequest,
    ) -> AutoDebugClosureResult:
        return await controller.run_job_auto_debug_closure(job_id=job_id, request=request)

    @router.post("/jobs/{job_id}/auto-closure/report", status_code=202)
    async def run_job_auto_debug_closure_report(
        job_id: str,
        request: AutoDebugClosureRequest,
    ) -> AutoDebugClosureReportResponse:
        return await controller.run_job_auto_debug_closure_report(job_id=job_id, request=request)

    @router.patch("/jobs/{job_id}/human-handoffs/{target_id}/status")
    def update_human_handoff_status(
        job_id: str,
        target_id: str,
        request: HumanHandoffStatusRequest,
    ) -> HumanHandoffStatus:
        return controller.update_human_handoff_status(
            job_id=job_id, target_id=target_id, request=request
        )

    @router.get("/jobs/{job_id}/human-handoffs/statuses")
    def list_human_handoff_statuses(job_id: str) -> HumanHandoffStatusListResponse:
        return controller.list_human_handoff_statuses(job_id)

    @router.get("/jobs/{job_id}/recommended-actions/statuses")
    def list_recommended_action_statuses(job_id: str) -> RecommendedActionStatusListResponse:
        return controller.list_recommended_action_statuses(job_id)

    return router


def _strategy_follow_up_from_report(report: DebugReport, stage: str) -> dict[str, str] | None:
    for follow_up in report.follow_up_experiments:
        if follow_up.get("source") == "strategy_outcome" and follow_up.get("stage") == stage:
            return follow_up
    for follow_up in report.follow_up_experiments:
        if follow_up.get("source") == "debug_strategy" and follow_up.get("stage") == stage:
            return follow_up
    return None


def _final_attribution_follow_up_from_report(
    report: DebugReport, target_id: str
) -> dict[str, str] | None:
    for follow_up in report.follow_up_experiments:
        if (
            follow_up.get("source") == "final_attribution"
            and follow_up.get("target_id") == target_id
        ):
            return follow_up
    return None


def _final_attribution_recovery_follow_up_from_report(
    report: DebugReport, target_id: str
) -> dict[str, str] | None:
    for follow_up in report.follow_up_experiments:
        if (
            follow_up.get("source") == "final_attribution_verification_outcome"
            and follow_up.get("target_id") == target_id
        ):
            return follow_up
    return None


def _final_attribution_reinvestigation_follow_up_from_report(
    report: DebugReport, target_id: str
) -> dict[str, str] | None:
    for follow_up in report.follow_up_experiments:
        if (
            follow_up.get("source") == "final_attribution_recovery_outcome"
            and follow_up.get("target_id") == target_id
        ):
            return follow_up
    return None


def _targeted_probe_from_report(report: DebugReport, target_id: str) -> dict[str, str] | None:
    for follow_up in report.follow_up_experiments:
        if (
            follow_up.get("source") == "targeted_probe_guardrail"
            and follow_up.get("target_id") == target_id
        ):
            return follow_up
    for follow_up in report.follow_up_experiments:
        if (
            follow_up.get("source") == "targeted_probe_outcome"
            and follow_up.get("target_id") == target_id
        ):
            return follow_up
    for follow_up in report.follow_up_experiments:
        if follow_up.get("source") == "targeted_probe" and follow_up.get("target_id") == target_id:
            return follow_up
    return None
