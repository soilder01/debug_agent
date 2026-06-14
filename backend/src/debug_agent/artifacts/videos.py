import json
from pathlib import Path


def materialize_video_segment_manifest(
    *,
    artifact_id: str,
    source_uri: str,
    metadata: dict[str, object],
    output_dir: Path,
) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / video_segment_manifest_filename(artifact_id)
    manifest = _video_segment_manifest(
        artifact_id=artifact_id,
        source_uri=source_uri,
        metadata=metadata,
    )
    output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path.resolve().as_uri()


def materialize_multimodal_conflict_manifest(
    *,
    artifact_id: str,
    source_uri: str,
    metadata: dict[str, object],
    output_dir: Path,
) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / multimodal_conflict_manifest_filename(artifact_id)
    manifest = _multimodal_conflict_manifest(
        artifact_id=artifact_id,
        source_uri=source_uri,
        metadata=metadata,
    )
    output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path.resolve().as_uri()


def video_segment_manifest_filename(artifact_id: str) -> str:
    return f"{_safe_artifact_filename(artifact_id)}.json"


def multimodal_conflict_manifest_filename(artifact_id: str) -> str:
    return f"{_safe_artifact_filename(artifact_id)}.json"


def _video_segment_manifest(
    *,
    artifact_id: str,
    source_uri: str,
    metadata: dict[str, object],
) -> dict[str, object]:
    segment = _segment_payload(metadata)
    return {
        "artifact_id": artifact_id,
        "manifest_type": "video_segment_delta",
        "source_uri": source_uri,
        "target_id": metadata.get("target_id", ""),
        "reason": metadata.get("reason", ""),
        "start_ms": segment.get("start_ms", 0),
        "end_ms": segment.get("end_ms", 0),
        "expected_label": metadata.get("expected"),
        "actual_label": metadata.get("actual"),
        "expected_segment": metadata.get("expected_segment"),
        "actual_segment": metadata.get("actual_segment"),
    }


def _multimodal_conflict_manifest(
    *,
    artifact_id: str,
    source_uri: str,
    metadata: dict[str, object],
) -> dict[str, object]:
    return {
        "artifact_id": artifact_id,
        "manifest_type": "multimodal_conflict_delta",
        "source_uri": source_uri,
        "target_id": metadata.get("target_id", ""),
        "reason": metadata.get("reason", ""),
        "expected": metadata.get("expected"),
        "actual": metadata.get("actual"),
        "expected_conflict_type": metadata.get("expected_conflict_type"),
        "actual_conflict_type": metadata.get("actual_conflict_type"),
        "expected_modalities": metadata.get("expected_modalities"),
        "actual_modalities": metadata.get("actual_modalities"),
    }


def _segment_payload(metadata: dict[str, object]) -> dict[str, object]:
    actual_segment = metadata.get("actual_segment")
    if isinstance(actual_segment, dict):
        return actual_segment
    expected_segment = metadata.get("expected_segment")
    if isinstance(expected_segment, dict):
        return expected_segment
    return {}


def _safe_artifact_filename(artifact_id: str) -> str:
    return "".join(character if character.isalnum() or character in {"-", "_"} else "_" for character in artifact_id)
