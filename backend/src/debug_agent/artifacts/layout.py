from pathlib import Path


DEFAULT_ARTIFACT_GROUP = "single"


def job_artifact_dir(artifact_root: Path, *, artifact_group_id: str, job_id: str) -> Path:
    return artifact_root / "runs" / safe_path_fragment(artifact_group_id or DEFAULT_ARTIFACT_GROUP) / safe_path_fragment(job_id)


def safe_path_fragment(value: str) -> str:
    return "".join(character if character.isalnum() or character in {"-", "_"} else "_" for character in value)
