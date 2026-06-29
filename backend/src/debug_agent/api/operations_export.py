from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import Response

from debug_agent.api.lark_bot_setup_routes import LarkBotSetupAcknowledgementListResponse
from debug_agent.api.operations_routes import (
    ArtifactRetentionStatus,
    PilotGateResponse,
    ProductionReadinessResponse,
)
from debug_agent.api.schemas import (
    LarkOperationAuditListResponse,
    ObservabilitySummaryResponse,
    SpreadsheetWritebackAuditListResponse,
    WorkerRuntimeStatus,
)
from debug_agent.settings import DebugAgentSettings
from debug_agent.storage.repository import DebugJobRepository
from debug_agent.telemetry.performance import performance_summary


class OperationsExportController:
    def __init__(
        self,
        *,
        settings: Callable[[], DebugAgentSettings],
        job_repository: DebugJobRepository,
        readiness: Callable[[], ProductionReadinessResponse],
        observability_summary: Callable[[], ObservabilitySummaryResponse],
        worker_status: Callable[[], WorkerRuntimeStatus],
        artifact_retention: Callable[[int], ArtifactRetentionStatus],
        pilot_gate: Callable[[], PilotGateResponse],
        lark_bot_preflight: Callable[[], object],
        lark_bot_go_live_gate: Callable[[], object],
        lark_bot_permission_checklist: Callable[[], object],
        sqlite_database_path: Callable[[str], Path | None],
        database_kind: Callable[[str], str],
        redacted_database_url: Callable[[str], str],
    ) -> None:
        self._settings = settings
        self._job_repository = job_repository
        self._readiness = readiness
        self._observability_summary = observability_summary
        self._worker_status = worker_status
        self._artifact_retention = artifact_retention
        self._pilot_gate = pilot_gate
        self._lark_bot_preflight = lark_bot_preflight
        self._lark_bot_go_live_gate = lark_bot_go_live_gate
        self._lark_bot_permission_checklist = lark_bot_permission_checklist
        self._sqlite_database_path = sqlite_database_path
        self._database_kind = database_kind
        self._redacted_database_url = redacted_database_url

    def export_support_bundle(self, *, audit_limit: int = 100) -> Response:
        archive = self.build_support_bundle_archive(audit_limit=audit_limit)
        return Response(
            content=archive,
            media_type="application/zip",
            headers={
                "Content-Disposition": 'attachment; filename="debug-agent-operations-support-bundle.zip"'
            },
        )

    def export_database_backup(self) -> Response:
        archive = self.build_database_backup_archive()
        return Response(
            content=archive,
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="debug-agent-database-backup.zip"'},
        )

    def build_support_bundle_archive(self, *, audit_limit: int) -> bytes:
        entries: dict[str, object] = {
            "readiness.json": self._readiness().model_dump(mode="json"),
            "observability_summary.json": self._observability_summary().model_dump(mode="json"),
            "performance_summary.json": performance_summary(limit=200),
            "worker_status.json": self._worker_status().model_dump(mode="json"),
            "artifact_retention.json": self._artifact_retention(50).model_dump(mode="json"),
            "pilot_gate.json": self._pilot_gate().model_dump(mode="json"),
            "lark_bot_preflight.json": self._lark_bot_preflight().model_dump(mode="json"),
            "lark_bot_go_live_gate.json": self._lark_bot_go_live_gate().model_dump(mode="json"),
            "lark_bot_permission_checklist.json": self._lark_bot_permission_checklist().model_dump(
                mode="json"
            ),
            "lark_bot_setup_acknowledgements.json": LarkBotSetupAcknowledgementListResponse(
                acknowledgements=self._job_repository.list_lark_bot_setup_acknowledgements(
                    limit=audit_limit
                )
            ).model_dump(mode="json"),
            "lark_operation_audits.json": LarkOperationAuditListResponse(
                audits=self._job_repository.list_lark_operation_audits(
                    limit=audit_limit, offset=0
                ),
                total_count=self._job_repository.count_lark_operation_audits(),
            ).model_dump(mode="json"),
            "spreadsheet_writeback_audits.json": SpreadsheetWritebackAuditListResponse(
                audits=self._job_repository.list_spreadsheet_writeback_audits(
                    limit=audit_limit, offset=0
                ),
                total_count=self._job_repository.count_spreadsheet_writeback_audits(),
            ).model_dump(mode="json"),
        }
        manifest = {
            "export_type": "operations_support_bundle",
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "audit_limit": audit_limit,
            "contents": ["manifest.json", "README.txt", *entries.keys()],
            "redaction": "Runtime config is redacted; credentials, API keys, app secrets, auth codes, and tokens are not included.",
        }
        readme = (
            "Debug Agent 生产运维支持包\n"
            "\n"
            "用途：用于生产候选或试点现场排障，集中导出脱敏运行状态、性能指标、Worker 状态、"
            "Lark 操作审计和写回审计。\n"
            "安全：该包不包含 API key、App Secret、auth code、user token 或明文模型凭据。\n"
        )
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", _json_bytes(manifest))
            archive.writestr("README.txt", readme.encode("utf-8"))
            for filename, payload in entries.items():
                archive.writestr(filename, _json_bytes(payload))
        return buffer.getvalue()

    def build_database_backup_archive(self) -> bytes:
        database_url = self._settings().database_url
        database_path = self._sqlite_database_path(database_url)
        if database_path is None:
            raise HTTPException(
                status_code=400,
                detail="Database backup endpoint only supports SQLite database URLs.",
            )
        resolved_database_path = database_path.resolve()
        if not resolved_database_path.is_file():
            raise HTTPException(
                status_code=404, detail=f"SQLite database file not found: {database_path}"
            )
        backup_files = [resolved_database_path]
        for suffix in ("-wal", "-shm"):
            sidecar = Path(f"{resolved_database_path}{suffix}")
            if sidecar.is_file():
                backup_files.append(sidecar)
        manifest = {
            "export_type": "database_backup",
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "database_kind": self._database_kind(database_url),
            "database_url": self._redacted_database_url(database_url),
            "database_path": str(resolved_database_path),
            "file_count": len(backup_files),
            "files": [
                {
                    "name": path.name,
                    "size_bytes": path.stat().st_size,
                }
                for path in backup_files
            ],
            "warning": "This backup may contain case data, reports, audit logs, and operational state. Store it in an approved secure location.",
        }
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", _json_bytes(manifest))
            for path in backup_files:
                archive.write(path, f"database/{path.name}")
        return buffer.getvalue()


def _json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
