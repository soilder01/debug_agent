from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class DebugJobRow(Base):
    __tablename__ = "debug_jobs"

    job_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(120), index=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class DebugCaseRow(Base):
    __tablename__ = "debug_cases"

    case_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    case_json: Mapped[str] = mapped_column(Text)


class EvidenceRow(Base):
    __tablename__ = "evidence"

    job_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    evidence_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(120), index=True)
    step_name: Mapped[str] = mapped_column(String(120), index=True)
    trial: Mapped[int] = mapped_column(Integer)
    score: Mapped[int] = mapped_column(Integer)
    reasons_json: Mapped[str] = mapped_column(Text)
    raw_output: Mapped[str] = mapped_column(Text)
