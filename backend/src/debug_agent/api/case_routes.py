from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query

from debug_agent.api.schemas import DebugCaseListResponse, DebugCaseSummary
from debug_agent.artifacts.store import artifact_store
from debug_agent.cases.models import DebugCase
from debug_agent.experiments.planner import plan_experiments
from debug_agent.experiments.runner import run_experiments
from debug_agent.jobs.service import DebugJobService, SubmittedDebugJob
from debug_agent.models.fake import FakeModelAdapter
from debug_agent.reports.generator import DebugReport, generate_initial_report
from debug_agent.storage.repository import DebugJobRepository


class CaseRouteController:
    def __init__(
        self,
        *,
        job_repository: DebugJobRepository,
        job_service: DebugJobService,
        raise_if_usage_budget_blocks_submission: Callable[[], None],
        artifact_dir_for_job_id: Callable[[str], Path],
    ) -> None:
        self._job_repository = job_repository
        self._job_service = job_service
        self._raise_if_usage_budget_blocks_submission = (
            raise_if_usage_budget_blocks_submission
        )
        self._artifact_dir_for_job_id = artifact_dir_for_job_id

    def list_cases(
        self,
        *,
        has_regions: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> DebugCaseListResponse:
        total_count = self._job_repository.count_cases()
        filtered_count = self._job_repository.count_cases(has_regions=has_regions)
        cases = self._job_repository.list_cases(
            has_regions=has_regions, limit=limit, offset=offset
        )
        return DebugCaseListResponse(
            total_count=total_count,
            filtered_count=filtered_count,
            cases=[
                DebugCaseSummary(
                    case_id=case.case_id,
                    image_uri=case.image_uri,
                    avg_score=case.avg_score,
                    debug_status=case.human_notes.debug_status,
                    root_cause=case.human_notes.root_cause,
                    box_region_count=len(case.box_regions),
                )
                for case in cases
            ],
        )

    def get_case_detail(self, case_id: str) -> DebugCase:
        try:
            return self._job_service.load_case(case_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    async def debug_case(self, case_id: str) -> DebugReport:
        try:
            case = self._job_service.load_case(case_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        job_id = str(uuid4())
        self._job_repository.create_job(
            job_id=job_id, case_id=case.case_id, artifact_group_id="direct-debug"
        )
        self._job_repository.mark_running(job_id)
        plan = plan_experiments(case)
        adapter = FakeModelAdapter(
            outputs=[prediction.raw_output for prediction in case.predictions]
        )
        try:
            run_result = await run_experiments(
                case=case,
                plan=plan,
                adapter=adapter,
                image_artifact_dir=self._artifact_dir_for_job_id(job_id),
            )
            artifact_store.save_case_evidence(case.case_id, run_result.evidence)
            self._job_repository.save_evidence(
                job_id=job_id,
                case_id=case.case_id,
                evidence=run_result.evidence,
            )
            self._job_repository.mark_completed(job_id)
        except Exception as exc:
            self._job_repository.mark_failed(job_id, str(exc))
            raise
        return generate_initial_report(case, plan, run_result, job_id=job_id)

    async def submit_debug_job(
        self,
        *,
        case_id: str,
        auto_run: bool = False,
        baseline_trials: int = 0,
    ) -> SubmittedDebugJob:
        self._raise_if_usage_budget_blocks_submission()
        try:
            submitted = self._job_service.submit_case_debug(
                case_id,
                baseline_trials=baseline_trials,
                artifact_group_id="single",
            )
            if auto_run:
                await self._job_service.run_job(submitted.job_id)
            return submitted
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


def build_case_router(controller: CaseRouteController) -> APIRouter:
    router = APIRouter()

    @router.get("/cases")
    def list_cases(
        has_regions: bool = False, limit: int | None = None, offset: int = 0
    ) -> DebugCaseListResponse:
        return controller.list_cases(
            has_regions=has_regions, limit=limit, offset=offset
        )

    @router.get("/cases/{case_id}")
    def get_case_detail(case_id: str) -> DebugCase:
        return controller.get_case_detail(case_id)

    @router.post("/cases/{case_id}/debug")
    async def debug_case(case_id: str) -> DebugReport:
        return await controller.debug_case(case_id)

    @router.post("/cases/{case_id}/debug-jobs", status_code=202)
    async def submit_debug_job(
        case_id: str,
        auto_run: bool = False,
        baseline_trials: int = Query(default=0, ge=0, le=5),
    ) -> SubmittedDebugJob:
        return await controller.submit_debug_job(
            case_id=case_id,
            auto_run=auto_run,
            baseline_trials=baseline_trials,
        )

    return router
