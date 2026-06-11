from collections.abc import Callable

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


def create_sqlite_session_factory(database_url: str) -> tuple[Callable[[], Session], Engine]:
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool if database_url.endswith(":memory:") else None,
    )
    return sessionmaker(bind=engine, expire_on_commit=False), engine


def create_sqlite_memory_session_factory() -> tuple[Callable[[], Session], Engine]:
    return create_sqlite_session_factory("sqlite+pysqlite:///:memory:")


def ensure_database_schema(engine: Engine) -> None:
    from debug_agent.storage.models import Base, EvidenceRow

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
    if "evidence" in inspector.get_table_names():
        evidence_columns = {column["name"] for column in inspector.get_columns("evidence")}
        missing_columns = [
            ("model_name", "VARCHAR(120)", "''"),
            ("model_provider", "VARCHAR(80)", "''"),
            ("model_id", "VARCHAR(160)", "''"),
            ("request_summary_json", "TEXT", "'{}'"),
            ("latency_ms", "INTEGER", "0"),
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
