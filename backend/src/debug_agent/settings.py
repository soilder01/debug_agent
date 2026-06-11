import os
from pathlib import Path

from pydantic import BaseModel, SecretStr

_LOCAL_ENV_LOADED = False


def load_env_file(path: str | Path, override: bool = False) -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        normalized_value = value.strip().strip('"').strip("'")
        if override or key not in os.environ:
            os.environ[key] = normalized_value


def load_local_env() -> None:
    global _LOCAL_ENV_LOADED
    if _LOCAL_ENV_LOADED:
        return
    project_root = Path(__file__).resolve().parents[3]
    load_env_file(project_root / ".env")
    _LOCAL_ENV_LOADED = True


class DebugAgentSettings(BaseModel):
    database_url: str = "sqlite+pysqlite:///:memory:"
    image_artifact_dir: Path = Path("artifacts/image-crops")

    @classmethod
    def from_env(cls) -> "DebugAgentSettings":
        load_local_env()
        default_image_artifact_dir = cls.model_fields["image_artifact_dir"].default
        return cls(
            database_url=os.environ.get(
                "DEBUG_AGENT_DATABASE_URL",
                cls.model_fields["database_url"].default,
            ),
            image_artifact_dir=Path(
                os.environ.get(
                    "DEBUG_AGENT_IMAGE_ARTIFACT_DIR",
                    str(default_image_artifact_dir),
                )
            ),
        )


class ModelRuntimeSettings(BaseModel):
    provider: str = "fake"

    @classmethod
    def from_env(cls) -> "ModelRuntimeSettings":
        load_local_env()
        return cls(
            provider=os.environ.get(
                "DEBUG_AGENT_MODEL_PROVIDER",
                cls.model_fields["provider"].default,
            )
        )


class ArkSettings(BaseModel):
    api_key: SecretStr
    base_url: str = "https://ark-cn-beijing.bytedance.net/api/v3"
    content_tasks_url: str = "https://ark-cn-beijing.bytedance.net/api/v3/contents/generations/tasks"
    seed2_lite_model_id: str = "ep-20260609151048-sbfnk"
    seed2_pro_model_id: str = "ep-20260609191630-7gkjm"

    @classmethod
    def from_env(cls) -> "ArkSettings":
        load_local_env()
        api_key = os.environ.get("ARK_API_KEY", "")
        if not api_key:
            raise RuntimeError("ARK_API_KEY is required for live Ark model calls")
        return cls(
            api_key=SecretStr(api_key),
            base_url=os.environ.get("ARK_BASE_URL", cls.model_fields["base_url"].default),
            content_tasks_url=os.environ.get(
                "ARK_CONTENT_TASKS_URL", cls.model_fields["content_tasks_url"].default
            ),
            seed2_lite_model_id=os.environ.get(
                "ARK_SEED2_LITE_MODEL_ID", cls.model_fields["seed2_lite_model_id"].default
            ),
            seed2_pro_model_id=os.environ.get(
                "ARK_SEED2_PRO_MODEL_ID", cls.model_fields["seed2_pro_model_id"].default
            ),
        )
