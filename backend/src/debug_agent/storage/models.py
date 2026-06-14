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
    baseline_trials: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)
    updated_at: Mapped[str] = mapped_column(String(40), default="", server_default="")


class DebugCaseRow(Base):
    __tablename__ = "debug_cases"

    case_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    case_json: Mapped[str] = mapped_column(Text)
    box_region_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", index=True)


class SpreadsheetRowMappingRow(Base):
    __tablename__ = "spreadsheet_row_mappings"

    spreadsheet_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    sheet_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    row_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(120), index=True)
    job_id: Mapped[str] = mapped_column(String(80), default="", server_default="", index=True)
    created_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)
    updated_at: Mapped[str] = mapped_column(String(40), default="", server_default="")


class SpreadsheetWritebackAuditRow(Base):
    __tablename__ = "spreadsheet_writeback_audits"

    job_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    row_id: Mapped[str] = mapped_column(String(160), default="", server_default="")
    report_url: Mapped[str] = mapped_column(Text, default="", server_default="")
    fields_json: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")
    error_message: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)
    updated_at: Mapped[str] = mapped_column(String(40), default="", server_default="")


class RecommendedActionStatusRow(Base):
    __tablename__ = "recommended_action_statuses"

    job_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    action_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(40), default="pending", server_default="pending", index=True)
    actor: Mapped[str] = mapped_column(String(120), default="", server_default="")
    note: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)
    updated_at: Mapped[str] = mapped_column(String(40), default="", server_default="")


class RecommendedActionStatusEventRow(Base):
    __tablename__ = "recommended_action_status_events"

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(80), index=True)
    action_index: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    actor: Mapped[str] = mapped_column(String(120), default="", server_default="")
    note: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)


class RecommendedActionVerificationRow(Base):
    __tablename__ = "recommended_action_verifications"

    job_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    action_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    verification_job_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    actor: Mapped[str] = mapped_column(String(120), default="", server_default="")
    note: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[str] = mapped_column(String(40), default="", server_default="", index=True)


class EvidenceRow(Base):
    __tablename__ = "evidence"

    job_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    evidence_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(120), index=True)
    step_name: Mapped[str] = mapped_column(String(120), index=True)
    trial: Mapped[int] = mapped_column(Integer)
    model_name: Mapped[str] = mapped_column(String(120), default="", server_default="")
    model_provider: Mapped[str] = mapped_column(String(80), default="", server_default="")
    model_id: Mapped[str] = mapped_column(String(160), default="", server_default="")
    request_summary_json: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    response_parse_error: Mapped[str] = mapped_column(Text, default="", server_default="")
    model_call_error_type: Mapped[str] = mapped_column(String(120), default="", server_default="")
    model_call_error_message: Mapped[str] = mapped_column(Text, default="", server_default="")
    image_artifacts_json: Mapped[str] = mapped_column(Text, default="[]", server_default="[]")
    artifacts_json: Mapped[str] = mapped_column(Text, default="[]", server_default="[]")
    score: Mapped[int] = mapped_column(Integer)
    reasons_json: Mapped[str] = mapped_column(Text)
    raw_output: Mapped[str] = mapped_column(Text)
