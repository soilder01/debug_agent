from __future__ import annotations

import csv
import io
import json
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Literal
from urllib.parse import unquote, urlparse

from fastapi import HTTPException
from fastapi.responses import Response

from debug_agent.api.report_export import build_html_report
from debug_agent.api.schemas import DebugJobStatus, EvidenceLedgerRecord
from debug_agent.experiments.runner import ExperimentEvidence
from debug_agent.reports.job_report import build_report_for_job
from debug_agent.settings import DebugAgentSettings
from debug_agent.storage.models import DebugJobRow
from debug_agent.storage.repository import DebugJobRepository
from debug_agent.telemetry.performance import performance_summary


class DebugJobExportController:
    def __init__(
        self,
        *,
        settings: Callable[[], DebugAgentSettings],
        job_repository: DebugJobRepository,
        build_job_status: Callable[[DebugJobRow], DebugJobStatus],
        evidence_ledger_record: Callable[..., EvidenceLedgerRecord],
        artifact_file_path: Callable[[str], Path | None],
    ) -> None:
        self._settings = settings
        self._job_repository = job_repository
        self._build_job_status = build_job_status
        self._evidence_ledger_record = evidence_ledger_record
        self._artifact_file_path = artifact_file_path

    def export_debug_jobs(
        self,
        *,
        job_ids: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
        sort: Literal["created_at_asc", "created_at_desc"] = "created_at_desc",
    ) -> Response:
        jobs = self.resolve_export_jobs(
            job_ids=job_ids, status=status, limit=limit, offset=offset, sort=sort
        )
        if job_ids and not jobs:
            raise HTTPException(status_code=404, detail="No debug jobs found for export.")
        archive = self.build_debug_job_export_archive(jobs)
        return Response(
            content=archive,
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="debug-agent-export.zip"'},
        )

    def resolve_export_jobs(
        self,
        *,
        job_ids: str | None,
        status: str | None,
        limit: int,
        offset: int,
        sort: Literal["created_at_asc", "created_at_desc"],
    ) -> list[DebugJobRow]:
        if job_ids:
            jobs: list[DebugJobRow] = []
            for raw_job_id in job_ids.split(","):
                job_id = raw_job_id.strip()
                if not job_id:
                    continue
                job = self._job_repository.get_job(job_id)
                if job is None:
                    raise HTTPException(status_code=404, detail=f"Debug job not found: {job_id}")
                jobs.append(job)
            return jobs
        return self._job_repository.list_jobs(
            status=status, limit=limit, offset=offset, sort=sort
        )

    def build_debug_job_export_archive(self, jobs: list[DebugJobRow]) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            manifest = {
                "export_type": "debug_jobs",
                "job_count": len(jobs),
                "job_ids": [job.job_id for job in jobs],
                "contents": [
                    "summary.csv",
                    "manifest.json",
                    "jobs/*.json",
                    "reports/*.json",
                    "run_stages/*.json",
                    "evidence/*.json",
                    "evidence_ledgers/*.json",
                    "writeback_audits/*.json",
                    "performance_summary.json",
                    "artifacts/*",
                ],
            }
            archive.writestr("manifest.json", _json_bytes(manifest))
            archive.writestr("summary.csv", self.summary_csv(jobs).encode("utf-8-sig"))
            archive.writestr(
                "performance_summary.json", _json_bytes(performance_summary(limit=200))
            )
            for job in jobs:
                safe_job_id = _safe_export_filename(job.job_id)
                archive.writestr(
                    f"jobs/{safe_job_id}.json",
                    _json_bytes(self._build_job_status(job).model_dump(mode="json")),
                )
                report = build_report_for_job(self._job_repository, job.job_id)
                if report is not None:
                    archive.writestr(
                        f"reports/{safe_job_id}.json",
                        _json_bytes(report.model_dump(mode="json")),
                    )
                archive.writestr(
                    f"html_reports/{safe_job_id}.html", build_html_report(job=job, report=report)
                )
                run_stages = [
                    stage.model_dump(mode="json")
                    for stage in self._job_repository.list_debug_run_stages(job.job_id)
                ]
                archive.writestr(
                    f"run_stages/{safe_job_id}.json", _json_bytes({"stages": run_stages})
                )
                evidence = [
                    item.model_dump(mode="json")
                    for item in self._job_repository.list_evidence(job.job_id)
                ]
                archive.writestr(
                    f"evidence/{safe_job_id}.json", _json_bytes({"evidence": evidence})
                )
                self.write_job_artifact_files(archive=archive, job_id=job.job_id)
                ledger = [
                    self._evidence_ledger_record(job_id=job.job_id, evidence=item).model_dump(
                        mode="json"
                    )
                    for item in self._job_repository.list_evidence(job.job_id)
                ]
                archive.writestr(
                    f"evidence_ledgers/{safe_job_id}.json", _json_bytes({"records": ledger})
                )
                audit = self._job_repository.get_spreadsheet_writeback_audit(job.job_id)
                if audit is not None:
                    archive.writestr(
                        f"writeback_audits/{safe_job_id}.json",
                        _json_bytes(audit.model_dump(mode="json")),
                    )
        return buffer.getvalue()

    def write_job_artifact_files(self, *, archive: zipfile.ZipFile, job_id: str) -> None:
        artifact_dir = self._settings().image_artifact_dir.resolve()
        safe_job_id = _safe_export_filename(job_id)
        written_paths: set[Path] = set()
        for evidence in self._job_repository.list_evidence(job_id):
            for artifact_path in self.artifact_paths_from_evidence(evidence):
                resolved_path = artifact_path.resolve()
                if resolved_path in written_paths or not resolved_path.is_file():
                    continue
                if not resolved_path.is_relative_to(artifact_dir):
                    continue
                relative_path = resolved_path.relative_to(artifact_dir)
                archive.write(resolved_path, f"artifacts/{safe_job_id}/{relative_path.as_posix()}")
                written_paths.add(resolved_path)

    def artifact_paths_from_evidence(self, evidence: ExperimentEvidence) -> list[Path]:
        paths: list[Path] = []
        for artifact in evidence.artifacts:
            for reference in (artifact.derived_uri, artifact.preview_url):
                if not reference:
                    continue
                artifact_path = self.artifact_path_from_reference(reference)
                if artifact_path is not None:
                    paths.append(artifact_path)
        for image_artifact in evidence.image_artifacts:
            for reference in (image_artifact.derived_image_uri, image_artifact.preview_image_url):
                if not reference:
                    continue
                artifact_path = self.artifact_path_from_reference(reference)
                if artifact_path is not None:
                    paths.append(artifact_path)
        return paths

    def artifact_path_from_reference(self, reference: str) -> Path | None:
        parsed = urlparse(reference)
        if parsed.scheme == "file":
            path_text = unquote(parsed.path)
            if len(path_text) >= 3 and path_text[0] == "/" and path_text[2] == ":":
                path_text = path_text[1:]
            return Path(path_text)
        for prefix in (
            "/api/artifacts/files/",
            "/artifacts/files/",
            "/api/artifacts/images/",
            "/artifacts/images/",
            "/api/artifacts/manifests/",
            "/artifacts/manifests/",
        ):
            if reference.startswith(prefix):
                return self._artifact_file_path(unquote(reference.removeprefix(prefix)))
        return None

    def summary_csv(self, jobs: list[DebugJobRow]) -> str:
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "job_id",
                "case_id",
                "status",
                "created_at",
                "updated_at",
                "attempt_count",
                "evidence_count",
                "error_message",
                "writeback_status",
                "writeback_row_id",
            ],
        )
        writer.writeheader()
        for job in jobs:
            audit = self._job_repository.get_spreadsheet_writeback_audit(job.job_id)
            writer.writerow(
                {
                    "job_id": job.job_id,
                    "case_id": job.case_id,
                    "status": job.status,
                    "created_at": job.created_at,
                    "updated_at": job.updated_at,
                    "attempt_count": job.attempt_count,
                    "evidence_count": len(self._job_repository.list_evidence_ids(job.job_id)),
                    "error_message": job.error_message or "",
                    "writeback_status": audit.status if audit is not None else "",
                    "writeback_row_id": audit.row_id if audit is not None else "",
                }
            )
        return output.getvalue()


def _safe_export_filename(value: str) -> str:
    return "".join(
        character if character.isalnum() or character in {"-", "_"} else "_" for character in value
    )


def _json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
