import os
from pathlib import Path
from typing import Literal, cast

from pydantic import BaseModel, SecretStr

from debug_agent.spreadsheets.lark import LarkSpreadsheetReference, parse_lark_spreadsheet_reference

_LOCAL_ENV_LOADED = False
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_ARTIFACT_ROOT = _BACKEND_ROOT / "artifacts"


def _sqlite_database_url(path: Path) -> str:
    return f"sqlite+pysqlite:///{path.as_posix()}"


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
    environment: str = "local"
    database_url: str = _sqlite_database_url(_DEFAULT_ARTIFACT_ROOT / "debug-agent.db")
    image_artifact_dir: Path = _DEFAULT_ARTIFACT_ROOT
    report_base_url: str = "http://localhost:8000"
    auto_writeback_enabled: bool = False
    auto_closure_enabled: bool = True
    usage_budget_units: float = 0.0
    enforce_usage_budget: bool = False
    auto_downgrade_meta_agents: bool = False
    require_trusted_actor: bool = False
    enable_fixture_fallback: bool = False
    queue_max_concurrency: int = 1
    retry_max_attempts: int = 2
    retry_backoff_seconds: float = 0.0
    stale_running_job_seconds: int = 1800
    artifact_retention_days: int = 30
    lark_event_mode: Literal["webhook", "long_connection"] = "long_connection"
    lark_bot_verification_token: SecretStr | None = None
    lark_bot_encrypt_key: SecretStr | None = None
    lark_bot_action_token_secret: SecretStr | None = None
    lark_report_docs_enabled: bool = False
    lark_report_doc_identity: Literal["user", "bot"] = "user"
    lark_report_doc_profile: str = ""
    lark_report_doc_parent_token: str = ""
    lark_report_doc_parent_position: str = ""

    @classmethod
    def from_env(cls) -> "DebugAgentSettings":
        load_local_env()
        default_image_artifact_dir = cls.model_fields["image_artifact_dir"].default
        lark_event_mode = os.environ.get(
            "LARK_EVENT_MODE",
            cls.model_fields["lark_event_mode"].default,
        ).strip()
        if lark_event_mode not in {"webhook", "long_connection"}:
            lark_event_mode = cls.model_fields["lark_event_mode"].default
        normalized_lark_event_mode = cast(Literal["webhook", "long_connection"], lark_event_mode)
        lark_bot_verification_token = os.environ.get("LARK_BOT_VERIFICATION_TOKEN", "").strip()
        lark_bot_encrypt_key = os.environ.get("LARK_BOT_ENCRYPT_KEY", "").strip()
        lark_bot_action_token_secret = os.environ.get("LARK_BOT_ACTION_TOKEN_SECRET", "").strip()
        lark_report_doc_identity = os.environ.get(
            "LARK_REPORT_DOC_IDENTITY",
            cls.model_fields["lark_report_doc_identity"].default,
        ).strip()
        if lark_report_doc_identity not in {"user", "bot"}:
            lark_report_doc_identity = cls.model_fields["lark_report_doc_identity"].default
        return cls(
            environment=os.environ.get(
                "DEBUG_AGENT_ENVIRONMENT",
                cls.model_fields["environment"].default,
            ),
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
            auto_closure_enabled=_env_bool("DEBUG_AGENT_AUTO_CLOSURE_ENABLED", default=True),
            usage_budget_units=float(
                os.environ.get(
                    "DEBUG_AGENT_USAGE_BUDGET_UNITS",
                    str(cls.model_fields["usage_budget_units"].default),
                )
            ),
            enforce_usage_budget=_env_bool("DEBUG_AGENT_ENFORCE_USAGE_BUDGET", default=False),
            auto_downgrade_meta_agents=_env_bool(
                "DEBUG_AGENT_AUTO_DOWNGRADE_META_AGENTS", default=False
            ),
            require_trusted_actor=_env_bool("DEBUG_AGENT_REQUIRE_TRUSTED_ACTOR", default=False),
            enable_fixture_fallback=_env_bool("DEBUG_AGENT_ENABLE_FIXTURE_FALLBACK", default=False),
            queue_max_concurrency=int(
                os.environ.get(
                    "DEBUG_AGENT_QUEUE_MAX_CONCURRENCY",
                    str(cls.model_fields["queue_max_concurrency"].default),
                )
            ),
            retry_max_attempts=int(
                os.environ.get(
                    "DEBUG_AGENT_RETRY_MAX_ATTEMPTS",
                    str(cls.model_fields["retry_max_attempts"].default),
                )
            ),
            retry_backoff_seconds=float(
                os.environ.get(
                    "DEBUG_AGENT_RETRY_BACKOFF_SECONDS",
                    str(cls.model_fields["retry_backoff_seconds"].default),
                )
            ),
            stale_running_job_seconds=int(
                os.environ.get(
                    "DEBUG_AGENT_STALE_RUNNING_JOB_SECONDS",
                    str(cls.model_fields["stale_running_job_seconds"].default),
                )
            ),
            artifact_retention_days=int(
                os.environ.get(
                    "DEBUG_AGENT_ARTIFACT_RETENTION_DAYS",
                    str(cls.model_fields["artifact_retention_days"].default),
                )
            ),
            lark_event_mode=normalized_lark_event_mode,
            lark_bot_verification_token=(
                SecretStr(lark_bot_verification_token) if lark_bot_verification_token else None
            ),
            lark_bot_encrypt_key=SecretStr(lark_bot_encrypt_key) if lark_bot_encrypt_key else None,
            lark_bot_action_token_secret=(
                SecretStr(lark_bot_action_token_secret) if lark_bot_action_token_secret else None
            ),
            lark_report_docs_enabled=_env_bool("LARK_REPORT_DOCS_ENABLED", default=False),
            lark_report_doc_identity=cast(Literal["user", "bot"], lark_report_doc_identity),
            lark_report_doc_profile=os.environ.get("LARK_REPORT_DOC_PROFILE", "").strip(),
            lark_report_doc_parent_token=os.environ.get("LARK_REPORT_DOC_PARENT_TOKEN", ""),
            lark_report_doc_parent_position=os.environ.get("LARK_REPORT_DOC_PARENT_POSITION", ""),
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
    content_tasks_url: str = (
        "https://ark-cn-beijing.bytedance.net/api/v3/contents/generations/tasks"
    )
    seedance2_model_id: str = "ep-20260609151048-sbfnk"
    seed2_lite_model_id: str = "ep-20260609191630-7gkjm"
    seed2_pro_model_id: str = "ep-20260609191630-7gkjm"
    chat_model_id: str = "ep-20260609191630-7gkjm"
    video_model_id: str = "ep-20260609191630-7gkjm"
    video_mode: str = "high"
    video_disable_thinking: bool = True

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
            seedance2_model_id=os.environ.get(
                "ARK_SEEDANCE2_MODEL_ID",
                os.environ.get(
                    "ARK_CONTENT_TASK_MODEL_ID", cls.model_fields["seedance2_model_id"].default
                ),
            ),
            seed2_lite_model_id=os.environ.get(
                "ARK_SEED2_LITE_MODEL_ID", cls.model_fields["seed2_lite_model_id"].default
            ),
            seed2_pro_model_id=os.environ.get(
                "ARK_SEED2_PRO_MODEL_ID", cls.model_fields["seed2_pro_model_id"].default
            ),
            chat_model_id=os.environ.get(
                "ARK_CHAT_MODEL_ID",
                os.environ.get("ARK_SEED2_PRO_MODEL_ID", cls.model_fields["chat_model_id"].default),
            ),
            video_model_id=os.environ.get(
                "ARK_VIDEO_MODEL_ID", cls.model_fields["video_model_id"].default
            ),
            video_mode=os.environ.get("ARK_VIDEO_MODE", cls.model_fields["video_mode"].default),
            video_disable_thinking=_env_bool("ARK_VIDEO_DISABLE_THINKING", default=True),
        )


class LarkSpreadsheetSettings(BaseModel):
    spreadsheet_url: str = ""
    sheet_id: str = ""
    lark_cli_timeout_seconds: int = 60
    lark_cli_profile: str = ""
    lark_cli_identity: str = "unknown"
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
        lark_cli_identity = os.environ.get(
            "LARK_CLI_IDENTITY",
            str(cls.model_fields["lark_cli_identity"].default),
        ).strip()
        if lark_cli_identity not in {"bot", "user", "unknown"}:
            lark_cli_identity = "unknown"
        reference = None
        if spreadsheet_url:
            reference = parse_lark_spreadsheet_reference(spreadsheet_url, sheet_id=sheet_id or None)
        return cls(
            spreadsheet_url=spreadsheet_url,
            sheet_id=sheet_id,
            lark_cli_timeout_seconds=lark_cli_timeout_seconds,
            lark_cli_profile=os.environ.get(
                "LARK_CLI_PROFILE", cls.model_fields["lark_cli_profile"].default
            ),
            lark_cli_identity=lark_cli_identity,
            reference=reference,
        )
