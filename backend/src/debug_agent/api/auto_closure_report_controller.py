from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path

from fastapi import HTTPException

from debug_agent.api.schemas import SpreadsheetRerunAutoClosureReport
from debug_agent.assistant.debug_lessons import build_debug_lesson_from_report
from debug_agent.assistant.knowledge_base import DebugLesson
from debug_agent.cases.models import DebugCase
from debug_agent.jobs.auto_closure import (
    AutoDebugClosureResult,
    LocalVideoClipper,
    run_auto_debug_closure,
)
from debug_agent.jobs.auto_closure_report import build_auto_closure_markdown_report
from debug_agent.jobs.service import DebugJobService, SubmittedDebugJob
from debug_agent.reports.generator import DebugReport
from debug_agent.storage.repository import DebugJobRepository


class AutoClosureReportController:
    def __init__(
        self,
        *,
        job_repository: Callable[[], DebugJobRepository],
        job_service: Callable[[], DebugJobService],
        build_report: Callable[[str], DebugReport | None],
        artifact_dir_for_job_id: Callable[[str], Path],
        video_clipper_for_job: Callable[[str], LocalVideoClipper],
        original_cot_excerpt: Callable[[DebugCase], str],
        original_prediction: Callable[[DebugCase], str],
        record_debug_lesson: Callable[[DebugLesson], object] | None = None,
    ) -> None:
        self._job_repository = job_repository
        self._job_service = job_service
        self._build_report = build_report
        self._artifact_dir_for_job_id = artifact_dir_for_job_id
        self._video_clipper_for_job = video_clipper_for_job
        self._original_cot_excerpt = original_cot_excerpt
        self._original_prediction = original_prediction
        self._record_debug_lesson = record_debug_lesson

    def persist_markdown_report(self, *, job_id: str, case_id: str, markdown: str) -> str:
        report_dir = self._artifact_dir_for_job_id(job_id) / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        filename = self._auto_closure_report_filename(case_id=case_id, job_id=job_id)
        output_path = report_dir / filename
        output_path.write_text(markdown, encoding="utf-8")
        return f"/api/artifacts/files/{filename}"

    async def run_spreadsheet_rerun_auto_closures(
        self,
        *,
        jobs: list[SubmittedDebugJob],
        writeback_requested: bool,
        submit_controlled_probes: bool = False,
        execute_follow_up_jobs: bool = True,
    ) -> list[SpreadsheetRerunAutoClosureReport]:
        reports: list[SpreadsheetRerunAutoClosureReport] = []
        for job in jobs:
            if job.status != "completed":
                continue
            reports.append(
                await self.run_report_for_completed_job(
                    job.job_id,
                    writeback_requested=writeback_requested,
                    submit_controlled_probes=submit_controlled_probes,
                    execute_follow_up_jobs=execute_follow_up_jobs,
                )
            )
        return reports

    async def run_report_for_completed_job(
        self,
        job_id: str,
        *,
        writeback_requested: bool,
        submit_controlled_probes: bool = False,
        execute_follow_up_jobs: bool = True,
    ) -> SpreadsheetRerunAutoClosureReport:
        repository = self._job_repository()
        job = repository.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"Debug job not found: {job_id}")
        report = self._build_report(job_id)
        if report is None:
            raise HTTPException(status_code=404, detail=f"Debug report not found for job: {job_id}")
        case = repository.get_case(job.case_id)
        if case is None:
            raise HTTPException(status_code=404, detail=f"Debug case not found: {job.case_id}")
        closure = await run_auto_debug_closure(
            repository=repository,
            job_service=self._job_service(),
            job_id=job_id,
            actor="spreadsheet-rerun-agent",
            writeback_client=None,
            video_clipper=self._video_clipper_for_job(job_id),
            report_url="",
            submit_controlled_probes=submit_controlled_probes,
            execute_follow_up_jobs=execute_follow_up_jobs,
        )
        markdown = self._build_markdown(report=report, closure=closure, case=case)
        report_artifact_url = self.persist_markdown_report(
            job_id=job_id,
            case_id=case.case_id,
            markdown=markdown,
        )
        self.save_run_stages(repository=repository, job_id=job_id, closure=closure)
        closure.writeback_status = (
            "sync_decision_pending" if writeback_requested else "not_requested"
        )
        repository.save_debug_run_stage(
            job_id=job_id,
            stage="writeback",
            status="pending" if writeback_requested else "skipped",
            input={"requested": writeback_requested, "report_url": report_artifact_url},
            output={
                "writeback_status": closure.writeback_status,
                "report_url": report_artifact_url,
            },
            failure_reason="",
            retryable=writeback_requested,
        )
        markdown = self._build_markdown(report=report, closure=closure, case=case)
        report_artifact_url = self.persist_markdown_report(
            job_id=job_id,
            case_id=case.case_id,
            markdown=markdown,
        )
        self.record_debug_lesson(
            report=report,
            closure=closure,
            report_artifact_url=report_artifact_url,
        )
        return SpreadsheetRerunAutoClosureReport(
            job_id=job_id,
            case_id=case.case_id,
            closure=closure,
            report_artifact_url=report_artifact_url,
            writeback_status=closure.writeback_status,
        )

    def save_run_stages(
        self,
        *,
        repository: DebugJobRepository,
        job_id: str,
        closure: AutoDebugClosureResult,
    ) -> None:
        existing_attribution_output = self.debug_run_stage_output(
            repository=repository,
            job_id=job_id,
            stage_name="attribution",
        )
        attribution_output: dict[str, object] = {
            "final_attribution_candidates": closure.final_attribution_candidates,
            "badcase_live_comparison": closure.badcase_live_comparison,
        }
        if isinstance(existing_attribution_output.get("meta_agent_enrichment"), dict):
            attribution_output["meta_agent_enrichment"] = existing_attribution_output[
                "meta_agent_enrichment"
            ]
        if "downgrade_reason" in existing_attribution_output:
            attribution_output["downgrade_reason"] = existing_attribution_output["downgrade_reason"]
        self.save_status_stage(
            repository=repository,
            job_id=job_id,
            status="completed",
            output=closure.model_dump(mode="json"),
            failure_reason="",
        )
        repository.save_debug_run_stage(
            job_id=job_id,
            stage="targeted",
            status="completed" if closure.created_targeted_probe_jobs else "skipped",
            input={"source_job_id": job_id},
            output={
                "created_jobs": closure.created_targeted_probe_jobs,
                "outcomes": closure.targeted_probe_outcomes,
            },
            failure_reason="",
            retryable=True,
        )
        repository.save_debug_run_stage(
            job_id=job_id,
            stage="verification",
            status="completed" if closure.created_verification_jobs else "skipped",
            input={"source_job_id": job_id},
            output={"created_jobs": closure.created_verification_jobs},
            failure_reason="",
            retryable=True,
        )
        repository.save_debug_run_stage(
            job_id=job_id,
            stage="attribution",
            status="completed" if closure.final_attribution_candidates else "skipped",
            input={"source_job_id": job_id},
            output=attribution_output,
            failure_reason="",
            retryable=True,
        )

    @staticmethod
    def debug_run_stage_output(
        *,
        repository: DebugJobRepository,
        job_id: str,
        stage_name: str,
    ) -> dict[str, object]:
        for stage in repository.list_debug_run_stages(job_id):
            if stage.stage == stage_name and isinstance(stage.output, dict):
                return dict(stage.output)
        return {}

    @staticmethod
    def save_status_stage(
        *,
        repository: DebugJobRepository,
        job_id: str,
        status: str,
        output: dict[str, object],
        failure_reason: str,
    ) -> None:
        repository.save_debug_run_stage(
            job_id=job_id,
            stage="auto_closure",
            status=status,
            input={"source_job_id": job_id},
            output=output,
            failure_reason=failure_reason,
            retryable=True,
        )

    def _build_markdown(
        self,
        *,
        report: DebugReport,
        closure: AutoDebugClosureResult,
        case: DebugCase,
    ) -> str:
        return build_auto_closure_markdown_report(
            report=report,
            closure=closure,
            original_prompt=case.prompt,
            original_cot_excerpt=self._original_cot_excerpt(case),
            original_prediction=self._original_prediction(case),
            reference_answer=json.dumps(case.expected_output, ensure_ascii=False, indent=2),
            scoring_ops=case.scoring_standard,
        )

    def record_debug_lesson(
        self,
        *,
        report: DebugReport,
        closure: AutoDebugClosureResult,
        report_artifact_url: str,
    ) -> None:
        if self._record_debug_lesson is None:
            return
        lesson = build_debug_lesson_from_report(
            report=report,
            closure=closure,
            source_uri=report_artifact_url,
            approved=False,
        )
        try:
            self._record_debug_lesson(lesson)
        except Exception:
            return

    @classmethod
    def _auto_closure_report_filename(cls, *, case_id: str, job_id: str) -> str:
        digest = hashlib.sha1(f"{case_id}:{job_id}".encode("utf-8")).hexdigest()[:12]
        safe_case = cls._safe_artifact_filename(case_id)[:48].strip("_") or "case"
        safe_job = cls._safe_artifact_filename(job_id)[:24].strip("_") or "job"
        return f"{safe_case}_{safe_job}_{digest}_auto_closure_report.md"

    @staticmethod
    def _safe_artifact_filename(value: str) -> str:
        return "".join(
            character if character.isalnum() or character in {"-", "_"} else "_"
            for character in value
        )
