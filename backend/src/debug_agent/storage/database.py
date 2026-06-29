import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


def create_sqlite_session_factory(database_url: str) -> tuple[Callable[[], Session], Engine]:
    _ensure_sqlite_parent_dir(database_url)
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool if database_url.endswith(":memory:") else None,
    )
    return sessionmaker(bind=engine, expire_on_commit=False), engine


def create_sqlite_memory_session_factory() -> tuple[Callable[[], Session], Engine]:
    return create_sqlite_session_factory("sqlite+pysqlite:///:memory:")


def _ensure_sqlite_parent_dir(database_url: str) -> None:
    if database_url.endswith(":memory:") or not database_url.startswith("sqlite"):
        return
    if database_url.startswith("sqlite+pysqlite:///") and not database_url.startswith(
        "sqlite+pysqlite:////"
    ):
        raw_path = database_url.removeprefix("sqlite+pysqlite:///")
        if raw_path and not (len(raw_path) >= 2 and raw_path[1] == ":"):
            database_path = Path(raw_path)
            if database_path.parent != Path("."):
                database_path.parent.mkdir(parents=True, exist_ok=True)
            return
    if database_url.startswith("sqlite:///") and not database_url.startswith("sqlite:////"):
        raw_path = database_url.removeprefix("sqlite:///")
        if raw_path and not (len(raw_path) >= 2 and raw_path[1] == ":"):
            database_path = Path(raw_path)
            if database_path.parent != Path("."):
                database_path.parent.mkdir(parents=True, exist_ok=True)
            return
    parsed = urlparse(database_url)
    if parsed.scheme not in {"sqlite", "sqlite+pysqlite"}:
        return
    path_text = unquote(parsed.path)
    if not path_text:
        return
    if len(path_text) >= 3 and path_text[0] == "/" and path_text[2] == ":":
        path_text = path_text[1:]
    database_path = Path(path_text)
    if not database_path.is_absolute() and database_url.startswith("sqlite+pysqlite:///"):
        database_path = Path(database_url.removeprefix("sqlite+pysqlite:///"))
    if database_path.parent != Path("."):
        database_path.parent.mkdir(parents=True, exist_ok=True)


def ensure_database_schema(engine: Engine) -> None:
    from debug_agent.storage.models import Base, DebugBatchRow, DebugJobAttemptRow, EvidenceRow

    inspector = inspect(engine)
    has_legacy_evidence_table = False
    if "evidence" in inspector.get_table_names():
        primary_key = inspector.get_pk_constraint("evidence").get("constrained_columns", [])
        has_legacy_evidence_table = primary_key == ["evidence_id"]

    if has_legacy_evidence_table:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE evidence RENAME TO evidence_legacy_global_pk"))
            Base.metadata.tables[EvidenceRow.__tablename__].create(bind=connection)
            connection.execute(
                text(
                    """
                    INSERT INTO evidence (
                        job_id,
                        evidence_id,
                        case_id,
                        step_name,
                        trial,
                        score,
                        reasons_json,
                        raw_output
                    )
                    SELECT
                        job_id,
                        evidence_id,
                        case_id,
                        step_name,
                        trial,
                        score,
                        reasons_json,
                        raw_output
                    FROM evidence_legacy_global_pk
                    """
                )
            )
            connection.execute(text("DROP TABLE evidence_legacy_global_pk"))

    Base.metadata.create_all(engine)

    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    with engine.begin() as connection:
        if "debug_batches" not in table_names:
            Base.metadata.tables[DebugBatchRow.__tablename__].create(bind=connection)
        if "debug_job_attempts" not in table_names:
            Base.metadata.tables[DebugJobAttemptRow.__tablename__].create(bind=connection)

    inspector = inspect(engine)
    if "debug_jobs" in inspector.get_table_names():
        debug_job_columns = {column["name"] for column in inspector.get_columns("debug_jobs")}
        missing_columns = [
            ("created_at", "VARCHAR(40)", "''"),
            ("updated_at", "VARCHAR(40)", "''"),
            ("baseline_trials", "INTEGER", "0"),
            ("artifact_group_id", "VARCHAR(120)", "'single'"),
        ]
        with engine.begin() as connection:
            for column_name, column_type, default_value in missing_columns:
                if column_name not in debug_job_columns:
                    connection.execute(
                        text(
                            f"ALTER TABLE debug_jobs ADD COLUMN {column_name} "
                            f"{column_type} NOT NULL DEFAULT {default_value}"
                        )
                    )
            now = _utc_now_iso()
            connection.execute(
                text(
                    """
                    UPDATE debug_jobs
                    SET
                        created_at = CASE WHEN created_at = '' THEN :now ELSE created_at END,
                        updated_at = CASE WHEN updated_at = '' THEN :now ELSE updated_at END
                    """
                ),
                {"now": now},
            )

    inspector = inspect(engine)
    if "evidence" in inspector.get_table_names():
        evidence_columns = {column["name"] for column in inspector.get_columns("evidence")}
        missing_columns = [
            ("model_name", "VARCHAR(120)", "''"),
            ("model_provider", "VARCHAR(80)", "''"),
            ("model_id", "VARCHAR(160)", "''"),
            ("request_summary_json", "TEXT", "'{}'"),
            ("input_excerpt", "TEXT", "''"),
            ("latency_ms", "INTEGER", "0"),
            ("response_parse_error", "TEXT", "''"),
            ("model_call_error_type", "VARCHAR(120)", "''"),
            ("model_call_error_message", "TEXT", "''"),
            ("image_artifacts_json", "TEXT", "'[]'"),
            ("artifacts_json", "TEXT", "'[]'"),
        ]
        with engine.begin() as connection:
            for column_name, column_type, default_value in missing_columns:
                if column_name not in evidence_columns:
                    connection.execute(
                        text(
                            f"ALTER TABLE evidence ADD COLUMN {column_name} "
                            f"{column_type} NOT NULL DEFAULT {default_value}"
                        )
                    )

    inspector = inspect(engine)
    if "debug_cases" in inspector.get_table_names():
        debug_case_columns = {column["name"] for column in inspector.get_columns("debug_cases")}
        if "box_region_count" not in debug_case_columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE debug_cases ADD COLUMN box_region_count INTEGER NOT NULL DEFAULT 0"
                    )
                )
                rows = connection.execute(
                    text("SELECT case_id, case_json FROM debug_cases")
                ).mappings()
                for row in rows:
                    connection.execute(
                        text(
                            "UPDATE debug_cases SET box_region_count = :box_region_count WHERE case_id = :case_id"
                        ),
                        {
                            "box_region_count": _count_box_regions(str(row["case_json"])),
                            "case_id": row["case_id"],
                        },
                    )

    inspector = inspect(engine)
    if "targeted_probe_jobs" in inspector.get_table_names():
        targeted_probe_columns = {
            column["name"] for column in inspector.get_columns("targeted_probe_jobs")
        }
        missing_columns = [
            ("source", "VARCHAR(80)", "'targeted_probe'"),
            ("parent_probe_job_id", "VARCHAR(80)", "''"),
            ("trigger_outcome", "VARCHAR(80)", "''"),
        ]
        with engine.begin() as connection:
            for column_name, column_type, default_value in missing_columns:
                if column_name not in targeted_probe_columns:
                    connection.execute(
                        text(
                            f"ALTER TABLE targeted_probe_jobs ADD COLUMN {column_name} "
                            f"{column_type} NOT NULL DEFAULT {default_value}"
                        )
                    )

    inspector = inspect(engine)
    if "lark_operation_audits" in inspector.get_table_names():
        lark_operation_columns = {
            column["name"] for column in inspector.get_columns("lark_operation_audits")
        }
        missing_columns = [
            ("hint", "TEXT", "''"),
            ("console_url", "TEXT", "''"),
        ]
        with engine.begin() as connection:
            for column_name, column_type, default_value in missing_columns:
                if column_name not in lark_operation_columns:
                    connection.execute(
                        text(
                            f"ALTER TABLE lark_operation_audits ADD COLUMN {column_name} "
                            f"{column_type} NOT NULL DEFAULT {default_value}"
                        )
                    )

    inspector = inspect(engine)
    if "lark_bot_pending_commands" in inspector.get_table_names():
        lark_bot_pending_columns = {
            column["name"] for column in inspector.get_columns("lark_bot_pending_commands")
        }
        missing_columns = [
            ("message_id", "VARCHAR(120)", "''"),
        ]
        with engine.begin() as connection:
            for column_name, column_type, default_value in missing_columns:
                if column_name not in lark_bot_pending_columns:
                    connection.execute(
                        text(
                            f"ALTER TABLE lark_bot_pending_commands ADD COLUMN {column_name} "
                            f"{column_type} NOT NULL DEFAULT {default_value}"
                        )
                    )

    inspector = inspect(engine)
    if "lark_bot_badcase_drafts" in inspector.get_table_names():
        lark_bot_badcase_columns = {
            column["name"] for column in inspector.get_columns("lark_bot_badcase_drafts")
        }
        missing_columns = [
            ("progress_notified_keys_json", "TEXT", "'[]'"),
            ("progress_panel_message_id", "VARCHAR(120)", "''"),
        ]
        with engine.begin() as connection:
            for column_name, column_type, default_value in missing_columns:
                if column_name not in lark_bot_badcase_columns:
                    connection.execute(
                        text(
                            f"ALTER TABLE lark_bot_badcase_drafts ADD COLUMN {column_name} "
                            f"{column_type} NOT NULL DEFAULT {default_value}"
                        )
                    )


def _count_box_regions(case_json: str) -> int:
    try:
        case_data = json.loads(case_json)
    except json.JSONDecodeError:
        return 0
    if not isinstance(case_data, dict):
        return 0
    box_regions = case_data.get("box_regions")
    if not isinstance(box_regions, list):
        return 0
    return len(box_regions)


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")
