import shutil
from pathlib import Path
from urllib.parse import unquote, urlparse


def materialize_local_file_snapshot(*, source_uri: str, output_dir: Path | None, artifact_id: str) -> str:
    if output_dir is None:
        return ""
    try:
        source_path = _path_from_file_uri(source_uri)
    except ValueError:
        return ""
    if not source_path.is_file():
        return ""

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / _snapshot_filename(artifact_id, source_path.suffix)
    if source_path.resolve() != output_path.resolve():
        shutil.copy2(source_path, output_path)
    return output_path.resolve().as_uri()


def _snapshot_filename(artifact_id: str, suffix: str) -> str:
    normalized_suffix = suffix if suffix.startswith(".") else ""
    return f"{_safe_artifact_filename(artifact_id)}{normalized_suffix}"


def _path_from_file_uri(uri: str) -> Path:
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        raise ValueError(f"Only file:// URIs can be materialized: {uri}")
    path_text = unquote(parsed.path)
    if len(path_text) >= 3 and path_text[0] == "/" and path_text[2] == ":":
        path_text = path_text[1:]
    return Path(path_text)


def _safe_artifact_filename(artifact_id: str) -> str:
    return "".join(character if character.isalnum() or character in {"-", "_"} else "_" for character in artifact_id)
