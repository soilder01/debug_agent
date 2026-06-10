from collections.abc import Callable

from sqlalchemy import create_engine
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
