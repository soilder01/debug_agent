from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import inspect, text

from debug_agent.storage.database import (
    create_sqlite_memory_session_factory,
    create_sqlite_session_factory,
    ensure_database_schema,
)


def test_create_sqlite_session_factory_creates_parent_directory_for_file_database() -> None:
    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        database_path = Path(temp_dir) / "runtime" / "debug-agent.db"

        _session_factory, engine = create_sqlite_session_factory(
            f"sqlite+pysqlite:///{database_path.as_posix()}"
        )

        try:
            assert database_path.parent.exists()
        finally:
            engine.dispose()


def test_ensure_database_schema_adds_lark_operation_audit_repair_columns() -> None:
    _session_factory, engine = create_sqlite_memory_session_factory()
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE lark_operation_audits (
                    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor VARCHAR(120) NOT NULL DEFAULT '',
                    connector_mode VARCHAR(40) NOT NULL DEFAULT 'cli',
                    identity VARCHAR(40) NOT NULL DEFAULT 'unknown',
                    profile VARCHAR(120) NOT NULL DEFAULT '',
                    service VARCHAR(80) NOT NULL DEFAULT '',
                    operation VARCHAR(120) NOT NULL DEFAULT '',
                    status VARCHAR(40) NOT NULL DEFAULT '',
                    context TEXT NOT NULL DEFAULT '',
                    error_type VARCHAR(120) NOT NULL DEFAULT '',
                    permission_scopes_json TEXT NOT NULL DEFAULT '[]',
                    risk_action VARCHAR(160) NOT NULL DEFAULT '',
                    duration_ms INTEGER NOT NULL DEFAULT 0,
                    created_at VARCHAR(40) NOT NULL DEFAULT ''
                )
                """
            )
        )

    ensure_database_schema(engine)

    columns = {column["name"] for column in inspect(engine).get_columns("lark_operation_audits")}
    assert "hint" in columns
    assert "console_url" in columns


def test_ensure_database_schema_adds_lark_badcase_progress_notification_columns() -> None:
    _session_factory, engine = create_sqlite_memory_session_factory()
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE lark_bot_badcase_drafts (
                    draft_id VARCHAR(80) PRIMARY KEY,
                    actor VARCHAR(120) NOT NULL DEFAULT '',
                    open_id VARCHAR(120) NOT NULL DEFAULT '',
                    chat_id VARCHAR(120) NOT NULL DEFAULT '',
                    message_id VARCHAR(120) NOT NULL DEFAULT '',
                    status VARCHAR(40) NOT NULL DEFAULT 'collecting',
                    source_text TEXT NOT NULL DEFAULT '',
                    input_source TEXT NOT NULL DEFAULT '',
                    model_output TEXT NOT NULL DEFAULT '',
                    expected_output TEXT NOT NULL DEFAULT '',
                    issue_summary TEXT NOT NULL DEFAULT '',
                    task_type VARCHAR(80) NOT NULL DEFAULT 'generic_json',
                    scoring_standard TEXT NOT NULL DEFAULT '',
                    attachments_json TEXT NOT NULL DEFAULT '[]',
                    links_json TEXT NOT NULL DEFAULT '[]',
                    missing_fields_json TEXT NOT NULL DEFAULT '[]',
                    submitted_case_id VARCHAR(120) NOT NULL DEFAULT '',
                    submitted_job_id VARCHAR(80) NOT NULL DEFAULT '',
                    error_message TEXT NOT NULL DEFAULT '',
                    created_at VARCHAR(40) NOT NULL DEFAULT '',
                    updated_at VARCHAR(40) NOT NULL DEFAULT ''
                )
                """
            )
        )

    ensure_database_schema(engine)

    columns = {column["name"] for column in inspect(engine).get_columns("lark_bot_badcase_drafts")}
    assert "progress_notified_keys_json" in columns
    assert "progress_panel_message_id" in columns


def test_ensure_database_schema_creates_lark_notification_outbox_table() -> None:
    _session_factory, engine = create_sqlite_memory_session_factory()

    ensure_database_schema(engine)

    inspector = inspect(engine)
    assert "lark_notification_outbox" in inspector.get_table_names()
    columns = {column["name"] for column in inspector.get_columns("lark_notification_outbox")}
    assert {
        "notification_id",
        "kind",
        "dedupe_key",
        "status",
        "attempts",
        "last_error",
        "envelope_json",
    }.issubset(columns)
