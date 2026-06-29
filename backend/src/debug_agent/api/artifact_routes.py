from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from debug_agent.api.operations_routes import (
    ArtifactRetentionCleanupRequest,
    ArtifactRetentionCleanupResponse,
    ArtifactRetentionFileSample,
    ArtifactRetentionStatus,
)
from debug_agent.settings import DebugAgentSettings


ARTIFACT_RETENTION_DELETE_CONFIRMATION = "DELETE_EXPIRED_ARTIFACTS"


class ArtifactRouteController:
    def __init__(
        self,
        *,
        settings: Callable[[], DebugAgentSettings],
        resolved_actor: Callable[[str], str],
    ) -> None:
        self._settings = settings
        self._resolved_actor = resolved_actor

    def get_artifact_image(self, filename: str) -> FileResponse:
        artifact_path = self.artifact_file_path(filename)
        if artifact_path is None or artifact_path.suffix != ".png":
            raise HTTPException(status_code=404, detail=f"Artifact image not found: {filename}")
        return FileResponse(artifact_path, media_type="image/png")

    def get_artifact_manifest(self, filename: str) -> FileResponse:
        artifact_path = self.artifact_file_path(filename)
        if artifact_path is None or artifact_path.suffix != ".json":
            raise HTTPException(
                status_code=404, detail=f"Artifact manifest not found: {filename}"
            )
        return FileResponse(artifact_path, media_type="application/json")

    def get_artifact_file(self, filename: str) -> FileResponse:
        artifact_path = self.artifact_file_path(filename)
        if artifact_path is None:
            raise HTTPException(status_code=404, detail=f"Artifact file not found: {filename}")
        return FileResponse(artifact_path, media_type=self.artifact_media_type(artifact_path))

    def build_retention_status(self, *, limit: int) -> ArtifactRetentionStatus:
        now = datetime.now(UTC)
        artifact_root = self._settings().image_artifact_dir.resolve()
        scan_root = self.artifact_retention_scan_root()
        retention_days = max(0, self._settings().artifact_retention_days)
        cutoff = now - timedelta(days=retention_days)
        total_file_count = 0
        total_size_bytes = 0
        eligible_size_bytes = 0
        oldest_modified_at: datetime | None = None
        newest_modified_at: datetime | None = None
        eligible_records: list[tuple[datetime, ArtifactRetentionFileSample]] = []

        if scan_root.exists():
            for path in scan_root.rglob("*"):
                try:
                    stat = path.stat()
                except OSError:
                    continue
                if not path.is_file():
                    continue
                modified_at = datetime.fromtimestamp(stat.st_mtime, UTC)
                age_days = round(max(0.0, (now - modified_at).total_seconds() / 86_400), 2)
                sample = ArtifactRetentionFileSample(
                    relative_path=self.artifact_relative_path(path, artifact_root=artifact_root),
                    size_bytes=stat.st_size,
                    modified_at=modified_at.isoformat(timespec="seconds"),
                    age_days=age_days,
                )
                total_file_count += 1
                total_size_bytes += stat.st_size
                oldest_modified_at = (
                    modified_at
                    if oldest_modified_at is None
                    else min(oldest_modified_at, modified_at)
                )
                newest_modified_at = (
                    modified_at
                    if newest_modified_at is None
                    else max(newest_modified_at, modified_at)
                )
                if modified_at < cutoff:
                    eligible_records.append((modified_at, sample))
                    eligible_size_bytes += stat.st_size

        eligible_records.sort(key=lambda record: record[0])
        eligible_file_count = len(eligible_records)
        action = (
            f"有 {eligible_file_count} 个运行产物文件超过 {retention_days} 天；当前接口仅干跑，不会删除文件。"
            if eligible_file_count
            else f"当前没有超过 {retention_days} 天保留期的运行产物文件。"
        )
        if not scan_root.exists():
            action = "运行产物目录还不存在；首次任务完成后会自动创建。"
        return ArtifactRetentionStatus(
            generated_at=now.isoformat(timespec="seconds"),
            artifact_root=str(artifact_root),
            scan_root=str(scan_root),
            retention_days=retention_days,
            total_file_count=total_file_count,
            total_size_bytes=total_size_bytes,
            eligible_file_count=eligible_file_count,
            eligible_size_bytes=eligible_size_bytes,
            oldest_modified_at=oldest_modified_at.isoformat(timespec="seconds")
            if oldest_modified_at
            else "",
            newest_modified_at=newest_modified_at.isoformat(timespec="seconds")
            if newest_modified_at
            else "",
            eligible_samples=[sample for _, sample in eligible_records[:limit]],
            action=action,
        )

    def cleanup_retention(
        self, request: ArtifactRetentionCleanupRequest
    ) -> ArtifactRetentionCleanupResponse:
        actor = self._resolved_actor(request.actor)
        candidates = self.artifact_retention_candidates(limit=request.limit)
        if not request.dry_run and request.confirmation != ARTIFACT_RETENTION_DELETE_CONFIRMATION:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Artifact cleanup requires "
                    f"confirmation={ARTIFACT_RETENTION_DELETE_CONFIRMATION}."
                ),
            )
        deleted_samples: list[ArtifactRetentionFileSample] = []
        deleted_size_bytes = 0
        if not request.dry_run:
            scan_root = self.artifact_retention_scan_root()
            for path, sample in candidates:
                resolved_path = path.resolve()
                if not resolved_path.is_file() or not resolved_path.is_relative_to(scan_root):
                    continue
                try:
                    resolved_path.unlink()
                except OSError:
                    continue
                deleted_samples.append(sample)
                deleted_size_bytes += sample.size_bytes
                self.prune_empty_artifact_dirs(resolved_path.parent, stop_at=scan_root)
        deleted_count = len(deleted_samples) if not request.dry_run else 0
        eligible_count = len(candidates)
        return ArtifactRetentionCleanupResponse(
            actor=actor,
            dry_run=request.dry_run,
            confirmation_required=not request.dry_run,
            confirmation_phrase=ARTIFACT_RETENTION_DELETE_CONFIRMATION,
            deleted_file_count=deleted_count,
            deleted_size_bytes=deleted_size_bytes,
            deleted_samples=deleted_samples,
            status_after=self.build_retention_status(limit=min(request.limit, 200)),
            message=(
                f"干跑完成：发现 {eligible_count} 个超过保留期的运行产物文件。"
                if request.dry_run
                else f"清理完成：删除 {deleted_count} 个超过保留期的运行产物文件。"
            ),
        )

    def artifact_file_path(self, filename: str) -> Path | None:
        if Path(filename).name != filename:
            return None
        if Path(filename).suffix.lower() not in {
            ".json",
            ".md",
            ".mp4",
            ".png",
            ".txt",
            ".webm",
            ".mov",
        }:
            return None
        artifact_dir = self._settings().image_artifact_dir.resolve()
        for artifact_path in artifact_dir.rglob(filename):
            resolved_path = artifact_path.resolve()
            if resolved_path.is_file() and resolved_path.is_relative_to(artifact_dir):
                return resolved_path
        return None

    def artifact_media_type(self, artifact_path: Path) -> str:
        if artifact_path.suffix == ".md":
            return "text/markdown"
        if artifact_path.suffix == ".txt":
            return "text/plain"
        if artifact_path.suffix == ".mp4":
            return "video/mp4"
        if artifact_path.suffix == ".webm":
            return "video/webm"
        if artifact_path.suffix == ".mov":
            return "video/quicktime"
        if artifact_path.suffix == ".json":
            return "application/json"
        return "application/octet-stream"

    def artifact_retention_candidates(
        self, *, limit: int
    ) -> list[tuple[Path, ArtifactRetentionFileSample]]:
        now = datetime.now(UTC)
        artifact_root = self._settings().image_artifact_dir.resolve()
        scan_root = self.artifact_retention_scan_root()
        retention_days = max(0, self._settings().artifact_retention_days)
        cutoff = now - timedelta(days=retention_days)
        candidates: list[tuple[datetime, Path, ArtifactRetentionFileSample]] = []
        if scan_root.exists():
            for path in scan_root.rglob("*"):
                try:
                    stat = path.stat()
                except OSError:
                    continue
                if not path.is_file():
                    continue
                modified_at = datetime.fromtimestamp(stat.st_mtime, UTC)
                if modified_at >= cutoff:
                    continue
                candidates.append(
                    (
                        modified_at,
                        path,
                        ArtifactRetentionFileSample(
                            relative_path=self.artifact_relative_path(
                                path, artifact_root=artifact_root
                            ),
                            size_bytes=stat.st_size,
                            modified_at=modified_at.isoformat(timespec="seconds"),
                            age_days=round(
                                max(0.0, (now - modified_at).total_seconds() / 86_400), 2
                            ),
                        ),
                    )
                )
        candidates.sort(key=lambda record: record[0])
        return [(path, sample) for _, path, sample in candidates[:limit]]

    def prune_empty_artifact_dirs(self, path: Path, *, stop_at: Path) -> None:
        resolved_stop = stop_at.resolve()
        current = path.resolve()
        while current != resolved_stop and current.is_relative_to(resolved_stop):
            try:
                if any(current.iterdir()):
                    return
                current.rmdir()
            except OSError:
                return
            current = current.parent

    def artifact_retention_scan_root(self) -> Path:
        return self._settings().image_artifact_dir.resolve() / "runs"

    def artifact_relative_path(self, path: Path, *, artifact_root: Path) -> str:
        try:
            return path.resolve().relative_to(artifact_root).as_posix()
        except ValueError:
            return path.name


def build_artifact_router(controller: ArtifactRouteController) -> APIRouter:
    router = APIRouter()

    @router.get("/artifacts/images/{filename}")
    def get_artifact_image(filename: str) -> FileResponse:
        return controller.get_artifact_image(filename)

    @router.get("/api/artifacts/files/{filename}")
    def get_api_artifact_file(filename: str) -> FileResponse:
        return controller.get_artifact_file(filename)

    @router.get("/artifacts/manifests/{filename}")
    def get_artifact_manifest(filename: str) -> FileResponse:
        return controller.get_artifact_manifest(filename)

    @router.get("/artifacts/files/{filename}")
    def get_artifact_file(filename: str) -> FileResponse:
        return controller.get_artifact_file(filename)

    return router
