from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from fastapi import APIRouter, HTTPException

from debug_agent.api.schemas import (
    ActionQueueItemResponse,
    ActionQueueResponse,
    DebugJobListResponse,
    DebugJobStatus,
    DebugRunStageListResponse,
    DebugRunStageResponse,
    EvidenceLedgerRecord,
    EvidenceLedgerResponse,
    WorkerRuntimeStatus,
)
from debug_agent.experiments.runner import ExperimentEvidence
from debug_agent.jobs.service import DebugJobService, SubmittedDebugJob
from debug_agent.jobs.worker import AsyncJobWorker
from debug_agent.reports.action_queue import summarize_action_queue
from debug_agent.reports.generator import DebugReport
from debug_agent.reports.job_report import build_report_for_job
from debug_agent.reports.run_view import DebugRunView, build_debug_run_view
from debug_agent.storage.models import DebugJobRow
from debug_agent.storage.repository import DebugJobRepository, SpreadsheetWritebackAudit
from debug_agent.telemetry.performance import measure_performance


class JobReadRouteController:
    def __init__(
        self,
        *,
        job_repository: DebugJobRepository,
        job_service: DebugJobService,
        job_worker: Callable[[], AsyncJobWorker],
        build_worker_runtime_status: Callable[[], WorkerRuntimeStatus],
        build_job_status: Callable[[DebugJobRow], DebugJobStatus],
        evidence_ledger_record: Callable[..., EvidenceLedgerRecord],
    ) -> None:
        self._job_repository = job_repository
        self._job_service = job_service
        self._job_worker = job_worker
        self._build_worker_runtime_status = build_worker_runtime_status
        self._build_job_status = build_job_status
        self._evidence_ledger_record = evidence_ledger_record

    async def run_next_job(self) -> SubmittedDebugJob | None:
        return await self._job_service.run_next_job()

    def list_jobs(
        self,
        *,
        status: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        sort: Literal["created_at_asc", "created_at_desc"] = "created_at_asc",
    ) -> DebugJobListResponse:
        return DebugJobListResponse(
            jobs=[
                self._build_job_status(job)
                for job in self._job_repository.list_jobs(
                    status=status, limit=limit, offset=offset, sort=sort
                )
            ],
            total_count=self._job_repository.count_jobs(status=status),
        )

    def get_job_evidence(self, job_id: str, evidence_id: str) -> ExperimentEvidence:
        evidence = self._job_repository.get_evidence(job_id, evidence_id)
        if evidence is None:
            raise HTTPException(status_code=404, detail=f"Evidence not found: {evidence_id}")
        return evidence

    def get_worker_status(self) -> WorkerRuntimeStatus:
        return self._build_worker_runtime_status()

    async def start_worker(self) -> WorkerRuntimeStatus:
        self._job_worker().start()
        return self._build_worker_runtime_status()

    async def stop_worker(self) -> WorkerRuntimeStatus:
        await self._job_worker().stop()
        return self._build_worker_runtime_status()

    def get_job_spreadsheet_writeback_audit(self, job_id: str) -> SpreadsheetWritebackAudit:
        audit = self._job_repository.get_spreadsheet_writeback_audit(job_id)
        if audit is None:
            raise HTTPException(
                status_code=404,
                detail=f"Spreadsheet writeback audit not found for job: {job_id}",
            )
        return audit

    def get_job_action_queue(self, job_id: str) -> ActionQueueResponse:
        if self._job_repository.get_job(job_id) is None:
            raise HTTPException(status_code=404, detail=f"Debug job not found: {job_id}")
        report = build_report_for_job(self._job_repository, job_id)
        if report is None:
            raise HTTPException(status_code=404, detail=f"Debug report not found for job: {job_id}")
        return ActionQueueResponse(
            job_id=job_id,
            summary=summarize_action_queue(report.action_queue),
            items=[ActionQueueItemResponse.model_validate(item) for item in report.action_queue],
        )

    def get_job_run_view(self, job_id: str) -> DebugRunView:
        if self._job_repository.get_job(job_id) is None:
            raise HTTPException(status_code=404, detail=f"Debug job not found: {job_id}")
        report = build_report_for_job(self._job_repository, job_id)
        if report is None:
            raise HTTPException(status_code=404, detail=f"Debug report not found for job: {job_id}")
        run_view = build_debug_run_view(
            repository=self._job_repository, job_id=job_id, report=report
        )
        if run_view is None:
            raise HTTPException(
                status_code=404, detail=f"Debug run view not found for job: {job_id}"
            )
        return run_view

    def get_job_status(self, job_id: str) -> DebugJobStatus:
        job = self._job_repository.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"Debug job not found: {job_id}")
        return self._build_job_status(job)

    def get_job_run_stages(self, job_id: str) -> DebugRunStageListResponse:
        if self._job_repository.get_job(job_id) is None:
            raise HTTPException(status_code=404, detail=f"Debug job not found: {job_id}")
        return DebugRunStageListResponse(
            stages=[
                DebugRunStageResponse.model_validate(stage.model_dump())
                for stage in self._job_repository.list_debug_run_stages(job_id)
            ]
        )

    def get_job_evidence_ledger(self, job_id: str) -> EvidenceLedgerResponse:
        if self._job_repository.get_job(job_id) is None:
            raise HTTPException(status_code=404, detail=f"Debug job not found: {job_id}")
        return EvidenceLedgerResponse(
            records=[
                self._evidence_ledger_record(job_id=job_id, evidence=evidence)
                for evidence in self._job_repository.list_evidence(job_id)
            ]
        )

    def get_job_report(self, job_id: str) -> DebugReport:
        with measure_performance(
            component="report", operation="build_job_report", metadata={"job_id": job_id}
        ):
            report = build_report_for_job(self._job_repository, job_id)
        if report is None:
            raise HTTPException(status_code=404, detail=f"Debug report not found for job: {job_id}")
        return report


def build_job_read_router(controller: JobReadRouteController) -> APIRouter:
    router = APIRouter()

    @router.post("/jobs/run-next")
    async def run_next_job() -> SubmittedDebugJob | None:
        return await controller.run_next_job()

    @router.get("/jobs")
    def list_jobs(
        status: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        sort: Literal["created_at_asc", "created_at_desc"] = "created_at_asc",
    ) -> DebugJobListResponse:
        return controller.list_jobs(status=status, limit=limit, offset=offset, sort=sort)

    @router.get("/jobs/{job_id}/evidence/{evidence_id:path}")
    def get_job_evidence(job_id: str, evidence_id: str) -> ExperimentEvidence:
        return controller.get_job_evidence(job_id, evidence_id)

    @router.get("/worker/status")
    def get_worker_status() -> WorkerRuntimeStatus:
        return controller.get_worker_status()

    @router.post("/worker/start", status_code=202)
    async def start_worker() -> WorkerRuntimeStatus:
        return await controller.start_worker()

    @router.post("/worker/stop")
    async def stop_worker() -> WorkerRuntimeStatus:
        return await controller.stop_worker()

    @router.get("/jobs/{job_id}/spreadsheet-writeback/audit")
    def get_job_spreadsheet_writeback_audit(job_id: str) -> SpreadsheetWritebackAudit:
        return controller.get_job_spreadsheet_writeback_audit(job_id)

    @router.get("/jobs/{job_id}/action-queue")
    def get_job_action_queue(job_id: str) -> ActionQueueResponse:
        return controller.get_job_action_queue(job_id)

    @router.get("/jobs/{job_id}/run-view")
    def get_job_run_view(job_id: str) -> DebugRunView:
        return controller.get_job_run_view(job_id)

    @router.get("/jobs/{job_id}")
    def get_job_status(job_id: str) -> DebugJobStatus:
        return controller.get_job_status(job_id)

    @router.get("/jobs/{job_id}/run-stages")
    def get_job_run_stages(job_id: str) -> DebugRunStageListResponse:
        return controller.get_job_run_stages(job_id)

    @router.get("/jobs/{job_id}/evidence-ledger")
    def get_job_evidence_ledger(job_id: str) -> EvidenceLedgerResponse:
        return controller.get_job_evidence_ledger(job_id)

    @router.get("/jobs/{job_id}/report")
    def get_job_report(job_id: str) -> DebugReport:
        return controller.get_job_report(job_id)

    return router
