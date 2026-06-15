import os
from pathlib import Path

from pydantic import BaseModel, SecretStr

from debug_agent.spreadsheets.lark import LarkSpreadsheetReference, parse_lark_spreadsheet_reference

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


def _env_bool(key: str, *, default: bool) -> bool:
    value = os.environ.get(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class DebugAgentSettings(BaseModel):
    database_url: str = "sqlite+pysqlite:///:memory:"
    image_artifact_dir: Path = Path("artifacts/image-crops")
    report_base_url: str = "http://localhost:8000"
    auto_writeback_enabled: bool = False
    usage_budget_units: float = 0.0
    enforce_usage_budget: bool = False
    require_trusted_actor: bool = False

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
            report_base_url=os.environ.get(
                "DEBUG_AGENT_REPORT_BASE_URL",
                cls.model_fields["report_base_url"].default,
            ),
            auto_writeback_enabled=_env_bool("DEBUG_AGENT_AUTO_WRITEBACK_ENABLED", default=False),
            usage_budget_units=float(
                os.environ.get(
                    "DEBUG_AGENT_USAGE_BUDGET_UNITS",
                    str(cls.model_fields["usage_budget_units"].default),
                )
            ),
            enforce_usage_budget=_env_bool("DEBUG_AGENT_ENFORCE_USAGE_BUDGET", default=False),
            require_trusted_actor=_env_bool("DEBUG_AGENT_REQUIRE_TRUSTED_ACTOR", default=False),
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


class LarkSpreadsheetSettings(BaseModel):
    spreadsheet_url: str = ""
    sheet_id: str = ""
    lark_cli_timeout_seconds: int = 60
    reference: LarkSpreadsheetReference | None = None

    @classmethod
    def from_env(cls) -> "LarkSpreadsheetSettings":
        load_local_env()
        spreadsheet_url = os.environ.get("LARK_SPREADSHEET_URL", "")
        sheet_id = os.environ.get("LARK_SHEET_ID", "")
        lark_cli_timeout_seconds = int(
            os.environ.get(
                "LARK_CLI_TIMEOUT_SECONDS",
                str(cls.model_fields["lark_cli_timeout_seconds"].default),
            )
        )
        reference = None
        if spreadsheet_url:
            reference = parse_lark_spreadsheet_reference(spreadsheet_url, sheet_id=sheet_id or None)
        return cls(
            spreadsheet_url=spreadsheet_url,
            sheet_id=sheet_id,
            lark_cli_timeout_seconds=lark_cli_timeout_seconds,
            reference=reference,
        )
