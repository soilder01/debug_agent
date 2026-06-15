import json
import threading
from collections.abc import Callable
from datetime import UTC, datetime

from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from debug_agent.cases.models import DebugCase
from debug_agent.experiments.runner import ExperimentEvidence
from debug_agent.judging.runner import JudgeResult
from debug_agent.storage.models import (
    DebugCaseRow,
    DebugJobRow,
    EvidenceRow,
    RecommendedActionStatusEventRow,
    RecommendedActionStatusRow,
    RecommendedActionVerificationRow,
    SpreadsheetRowMappingRow,
    SpreadsheetWritebackAuditRow,
    StrategyFollowUpJobRow,
    TargetedProbeJobRow,
)


class SpreadsheetRowMapping(BaseModel):
    spreadsheet_id: str
    sheet_id: str
    row_id: str
    case_id: str
    job_id: str
    created_at: str
    updated_at: str


class SpreadsheetWritebackAudit(BaseModel):
    job_id: str
    status: str
    row_id: str
    report_url: str
    fields: dict[str, str]
    error_message: str
    created_at: str
    updated_at: str


class RecommendedActionStatus(BaseModel):
    job_id: str
    action_index: int
    status: str
    actor: str
    note: str
    created_at: str
    updated_at: str


class RecommendedActionStatusEvent(BaseModel):
    event_id: int
    job_id: str
    action_index: int
    status: str
    actor: str
    note: str
    created_at: str


class RecommendedActionVerification(BaseModel):
    job_id: str
    action_index: int
    verification_job_id: str
    actor: str
    note: str
    created_at: str


class StrategyFollowUpJob(BaseModel):
    source_job_id: str
    stage: str
    planned_steps: str
    follow_up_job_id: str
    actor: str
    note: str
    created_at: str


class TargetedProbeJob(BaseModel):
    source_job_id: str
    target_id: str
    planned_steps: str
    probe_job_id: str
    actor: str
    note: str
    created_at: str


class DebugJobRepository:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory
        self._lock = threading.RLock()

    def create_job(self, job_id: str, case_id: str, baseline_trials: int = 0) -> None:
        with self._lock:
            with self._session_factory() as session:
                now = _utc_now_iso()
                session.add(
                    DebugJobRow(
                        job_id=job_id,
                        case_id=case_id,
                        status="created",
                        baseline_trials=baseline_trials,
                        created_at=now,
                        updated_at=now,
                    )
                )
                session.commit()

    def save_case(self, case: DebugCase) -> None:
        with self._lock:
            with self._session_factory() as session:
                session.merge(
                    DebugCaseRow(
                        case_id=case.case_id,
                        case_json=case.model_dump_json(),
                        box_region_count=len(case.box_regions),
                    )
                )
                session.commit()

    def get_case(self, case_id: str) -> DebugCase | None:
        with self._lock:
            with self._session_factory() as session:
                row = session.get(DebugCaseRow, case_id)
                if row is None:
                    return None
                return DebugCase.model_validate_json(row.case_json)

    def save_spreadsheet_row_mapping(
        self,
        *,
        spreadsheet_id: str,
        sheet_id: str,
        row_id: str,
        case_id: str,
        job_id: str = "",
    ) -> None:
        with self._lock:
            with self._session_factory() as session:
                now = _utc_now_iso()
                existing = session.get(
                    SpreadsheetRowMappingRow,
                    {
                        "spreadsheet_id": spreadsheet_id,
                        "sheet_id": sheet_id,
                        "row_id": row_id,
                    },
                )
                created_at = existing.created_at if existing is not None else now
                session.merge(
                    SpreadsheetRowMappingRow(
                        spreadsheet_id=spreadsheet_id,
                        sheet_id=sheet_id,
                        row_id=row_id,
                        case_id=case_id,
                        job_id=job_id,
                        created_at=created_at,
                        updated_at=now,
                    )
                )
                session.commit()

    def get_spreadsheet_row_mapping(
        self,
        *,
        spreadsheet_id: str,
        sheet_id: str,
        row_id: str,
    ) -> SpreadsheetRowMapping | None:
        with self._lock:
            with self._session_factory() as session:
                row = session.get(
                    SpreadsheetRowMappingRow,
                    {
                        "spreadsheet_id": spreadsheet_id,
                        "sheet_id": sheet_id,
                        "row_id": row_id,
                    },
                )
                if row is None:
                    return None
                return SpreadsheetRowMapping(
                    spreadsheet_id=row.spreadsheet_id,
                    sheet_id=row.sheet_id,
                    row_id=row.row_id,
                    case_id=row.case_id,
                    job_id=row.job_id,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )

    def get_spreadsheet_row_mapping_by_job_id(self, job_id: str) -> SpreadsheetRowMapping | None:
        with self._lock:
            with self._session_factory() as session:
                row = session.scalars(
                    select(SpreadsheetRowMappingRow)
                    .where(SpreadsheetRowMappingRow.job_id == job_id)
                    .order_by(SpreadsheetRowMappingRow.updated_at.desc())
                    .limit(1)
                ).first()
                if row is None:
                    return None
                return SpreadsheetRowMapping(
                    spreadsheet_id=row.spreadsheet_id,
                    sheet_id=row.sheet_id,
                    row_id=row.row_id,
                    case_id=row.case_id,
                    job_id=row.job_id,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )

    def save_spreadsheet_writeback_audit(
        self,
        *,
        job_id: str,
        status: str,
        row_id: str,
        report_url: str,
        fields: dict[str, str],
        error_message: str,
    ) -> None:
        with self._lock:
            with self._session_factory() as session:
                now = _utc_now_iso()
                existing = session.get(SpreadsheetWritebackAuditRow, job_id)
                created_at = existing.created_at if existing is not None else now
                session.merge(
                    SpreadsheetWritebackAuditRow(
                        job_id=job_id,
                        status=status,
                        row_id=row_id,
                        report_url=report_url,
                        fields_json=json.dumps(fields, ensure_ascii=False),
                        error_message=error_message,
                        created_at=created_at,
                        updated_at=now,
                    )
                )
                session.commit()

    def get_spreadsheet_writeback_audit(self, job_id: str) -> SpreadsheetWritebackAudit | None:
        with self._lock:
            with self._session_factory() as session:
                row = session.get(SpreadsheetWritebackAuditRow, job_id)
                if row is None:
                    return None
                return _spreadsheet_writeback_audit_from_row(row)

    def count_spreadsheet_writeback_audits_by_status(self) -> dict[str, int]:
        with self._lock:
            with self._session_factory() as session:
                rows = session.execute(
                    select(SpreadsheetWritebackAuditRow.status, func.count())
                    .group_by(SpreadsheetWritebackAuditRow.status)
                    .order_by(SpreadsheetWritebackAuditRow.status)
                )
                return {str(status): int(count) for status, count in rows}

    def list_spreadsheet_writeback_audits(
        self,
        status: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[SpreadsheetWritebackAudit]:
        with self._lock:
            with self._session_factory() as session:
                query = select(SpreadsheetWritebackAuditRow).order_by(
                    desc(SpreadsheetWritebackAuditRow.updated_at),
                    desc(SpreadsheetWritebackAuditRow.job_id),
                )
                if status is not None:
                    query = query.where(SpreadsheetWritebackAuditRow.status == status)
                if offset > 0:
                    query = query.offset(offset)
                if limit is not None:
                    query = query.limit(limit)
                return [_spreadsheet_writeback_audit_from_row(row) for row in session.scalars(query)]

    def count_spreadsheet_writeback_audits(self, status: str | None = None) -> int:
        with self._lock:
            with self._session_factory() as session:
                query = select(func.count()).select_from(SpreadsheetWritebackAuditRow)
                if status is not None:
                    query = query.where(SpreadsheetWritebackAuditRow.status == status)
                return session.scalar(query) or 0

    def save_recommended_action_status(
        self,
        *,
        job_id: str,
        action_index: int,
        status: str,
        actor: str = "",
        note: str = "",
    ) -> RecommendedActionStatus:
        with self._lock:
            with self._session_factory() as session:
                now = _utc_now_iso()
                existing = session.get(RecommendedActionStatusRow, (job_id, action_index))
                created_at = existing.created_at if existing is not None else now
                row = RecommendedActionStatusRow(
                    job_id=job_id,
                    action_index=action_index,
                    status=status,
                    actor=actor,
                    note=note,
                    created_at=created_at,
                    updated_at=now,
                )
                session.merge(row)
                session.add(
                    RecommendedActionStatusEventRow(
                        job_id=job_id,
                        action_index=action_index,
                        status=status,
                        actor=actor,
                        note=note,
                        created_at=now,
                    )
                )
                session.commit()
                return RecommendedActionStatus(
                    job_id=job_id,
                    action_index=action_index,
                    status=status,
                    actor=actor,
                    note=note,
                    created_at=created_at,
                    updated_at=now,
                )

    def list_recommended_action_statuses(self, job_id: str) -> list[RecommendedActionStatus]:
        with self._lock:
            with self._session_factory() as session:
                rows = session.scalars(
                    select(RecommendedActionStatusRow)
                    .where(RecommendedActionStatusRow.job_id == job_id)
                    .order_by(RecommendedActionStatusRow.action_index)
                )
                return [_recommended_action_status_from_row(row) for row in rows]

    def list_recommended_action_status_events(
        self,
        job_id: str,
        action_index: int | None = None,
    ) -> list[RecommendedActionStatusEvent]:
        with self._lock:
            with self._session_factory() as session:
                query = (
                    select(RecommendedActionStatusEventRow)
                    .where(RecommendedActionStatusEventRow.job_id == job_id)
                    .order_by(
                        RecommendedActionStatusEventRow.created_at,
                        RecommendedActionStatusEventRow.event_id,
                    )
                )
                if action_index is not None:
                    query = query.where(RecommendedActionStatusEventRow.action_index == action_index)
                return [_recommended_action_status_event_from_row(row) for row in session.scalars(query)]

    def save_recommended_action_verification(
        self,
        *,
        job_id: str,
        action_index: int,
        verification_job_id: str,
        actor: str = "",
        note: str = "",
    ) -> RecommendedActionVerification:
        with self._lock:
            with self._session_factory() as session:
                now = _utc_now_iso()
                row = RecommendedActionVerificationRow(
                    job_id=job_id,
                    action_index=action_index,
                    verification_job_id=verification_job_id,
                    actor=actor,
                    note=note,
                    created_at=now,
                )
                session.add(row)
                session.commit()
                return _recommended_action_verification_from_row(row)

    def list_recommended_action_verifications(
        self,
        job_id: str,
        action_index: int | None = None,
    ) -> list[RecommendedActionVerification]:
        with self._lock:
            with self._session_factory() as session:
                query = (
                    select(RecommendedActionVerificationRow)
                    .where(RecommendedActionVerificationRow.job_id == job_id)
                    .order_by(
                        RecommendedActionVerificationRow.created_at,
                        RecommendedActionVerificationRow.verification_job_id,
                    )
                )
                if action_index is not None:
                    query = query.where(RecommendedActionVerificationRow.action_index == action_index)
                return [_recommended_action_verification_from_row(row) for row in session.scalars(query)]

    def save_strategy_follow_up_job(
        self,
        *,
        source_job_id: str,
        stage: str,
        planned_steps: str,
        follow_up_job_id: str,
        actor: str = "",
        note: str = "",
    ) -> StrategyFollowUpJob:
        with self._lock:
            with self._session_factory() as session:
                now = _utc_now_iso()
                row = StrategyFollowUpJobRow(
                    source_job_id=source_job_id,
                    stage=stage,
                    planned_steps=planned_steps,
                    follow_up_job_id=follow_up_job_id,
                    actor=actor,
                    note=note,
                    created_at=now,
                )
                session.add(row)
                session.commit()
                return _strategy_follow_up_job_from_row(row)

    def list_strategy_follow_up_jobs(self, source_job_id: str, stage: str | None = None) -> list[StrategyFollowUpJob]:
        with self._lock:
            with self._session_factory() as session:
                query = (
                    select(StrategyFollowUpJobRow)
                    .where(StrategyFollowUpJobRow.source_job_id == source_job_id)
                    .order_by(
                        StrategyFollowUpJobRow.created_at,
                        StrategyFollowUpJobRow.follow_up_job_id,
                    )
                )
                if stage is not None:
                    query = query.where(StrategyFollowUpJobRow.stage == stage)
                return [_strategy_follow_up_job_from_row(row) for row in session.scalars(query)]

    def list_all_strategy_follow_up_jobs(self) -> list[StrategyFollowUpJob]:
        with self._lock:
            with self._session_factory() as session:
                rows = session.scalars(
                    select(StrategyFollowUpJobRow).order_by(
                        StrategyFollowUpJobRow.created_at,
                        StrategyFollowUpJobRow.source_job_id,
                        StrategyFollowUpJobRow.follow_up_job_id,
                    )
                )
                return [_strategy_follow_up_job_from_row(row) for row in rows]

    def list_strategy_follow_up_sources(self, follow_up_job_id: str) -> list[StrategyFollowUpJob]:
        with self._lock:
            with self._session_factory() as session:
                rows = session.scalars(
                    select(StrategyFollowUpJobRow)
                    .where(StrategyFollowUpJobRow.follow_up_job_id == follow_up_job_id)
                    .order_by(
                        StrategyFollowUpJobRow.created_at,
                        StrategyFollowUpJobRow.source_job_id,
                    )
                )
                return [_strategy_follow_up_job_from_row(row) for row in rows]

    def save_targeted_probe_job(
        self,
        *,
        source_job_id: str,
        target_id: str,
        planned_steps: str,
        probe_job_id: str,
        actor: str = "",
        note: str = "",
    ) -> TargetedProbeJob:
        with self._lock:
            with self._session_factory() as session:
                now = _utc_now_iso()
                row = TargetedProbeJobRow(
                    source_job_id=source_job_id,
                    target_id=target_id,
                    planned_steps=planned_steps,
                    probe_job_id=probe_job_id,
                    actor=actor,
                    note=note,
                    created_at=now,
                )
                session.add(row)
                session.commit()
                return _targeted_probe_job_from_row(row)

    def list_targeted_probe_jobs(self, source_job_id: str) -> list[TargetedProbeJob]:
        with self._lock:
            with self._session_factory() as session:
                rows = session.scalars(
                    select(TargetedProbeJobRow)
                    .where(TargetedProbeJobRow.source_job_id == source_job_id)
                    .order_by(
                        TargetedProbeJobRow.created_at,
                        TargetedProbeJobRow.probe_job_id,
                    )
                )
                return [_targeted_probe_job_from_row(row) for row in rows]

    def list_targeted_probe_sources(self, probe_job_id: str) -> list[TargetedProbeJob]:
        with self._lock:
            with self._session_factory() as session:
                rows = session.scalars(
                    select(TargetedProbeJobRow)
                    .where(TargetedProbeJobRow.probe_job_id == probe_job_id)
                    .order_by(
                        TargetedProbeJobRow.created_at,
                        TargetedProbeJobRow.source_job_id,
                    )
                )
                return [_targeted_probe_job_from_row(row) for row in rows]

    def list_cases(self, has_regions: bool = False, limit: int | None = None, offset: int = 0) -> list[DebugCase]:
        with self._lock:
            with self._session_factory() as session:
                query = select(DebugCaseRow).order_by(DebugCaseRow.case_id)
                if has_regions:
                    query = query.where(DebugCaseRow.box_region_count > 0)
                if offset > 0:
                    query = query.offset(offset)
                if limit is not None:
                    query = query.limit(limit)
                rows = session.scalars(query)
                return [DebugCase.model_validate_json(row.case_json) for row in rows]

    def count_cases(self, has_regions: bool = False) -> int:
        with self._lock:
            with self._session_factory() as session:
                query = select(func.count()).select_from(DebugCaseRow)
                if has_regions:
                    query = query.where(DebugCaseRow.box_region_count > 0)
                return session.scalar(query) or 0

    def mark_running(self, job_id: str) -> None:
        self._set_status(job_id, "running")

    def mark_completed(self, job_id: str) -> None:
        self._set_status(job_id, "completed")

    def mark_failed(self, job_id: str, error_message: str) -> None:
        with self._lock:
            with self._session_factory() as session:
                job = session.get(DebugJobRow, job_id)
                if job is None:
                    raise KeyError(f"Debug job not found: {job_id}")
                job.status = "failed"
                job.error_message = error_message
                job.updated_at = _utc_now_iso()
                session.commit()

    def release_for_retry(self, job_id: str, error_message: str) -> None:
        with self._lock:
            with self._session_factory() as session:
                job = session.get(DebugJobRow, job_id)
                if job is None:
                    raise KeyError(f"Debug job not found: {job_id}")
                job.status = "created"
                job.error_message = error_message
                job.updated_at = _utc_now_iso()
                session.commit()

    def get_job(self, job_id: str) -> DebugJobRow | None:
        with self._lock:
            with self._session_factory() as session:
                return session.get(DebugJobRow, job_id)

    def list_jobs(
        self,
        status: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        sort: str = "created_at_asc",
    ) -> list[DebugJobRow]:
        with self._lock:
            with self._session_factory() as session:
                if sort == "created_at_desc":
                    query = select(DebugJobRow).order_by(desc(DebugJobRow.created_at), desc(DebugJobRow.job_id))
                else:
                    query = select(DebugJobRow).order_by(DebugJobRow.created_at, DebugJobRow.job_id)
                if status is not None:
                    query = query.where(DebugJobRow.status == status)
                if offset > 0:
                    query = query.offset(offset)
                if limit is not None:
                    query = query.limit(limit)
                rows = session.scalars(query)
                return list(rows)

    def count_jobs(self, status: str | None = None) -> int:
        with self._lock:
            with self._session_factory() as session:
                query = select(func.count()).select_from(DebugJobRow)
                if status is not None:
                    query = query.where(DebugJobRow.status == status)
                return session.scalar(query) or 0

    def count_jobs_by_status(self) -> dict[str, int]:
        with self._lock:
            with self._session_factory() as session:
                rows = session.execute(
                    select(DebugJobRow.status, func.count()).group_by(DebugJobRow.status).order_by(DebugJobRow.status)
                )
                return {str(status): int(count) for status, count in rows}

    def get_next_created_job(self) -> DebugJobRow | None:
        with self._lock:
            with self._session_factory() as session:
                return session.scalars(
                    select(DebugJobRow)
                    .where(DebugJobRow.status == "created")
                    .order_by(DebugJobRow.job_id)
                    .limit(1)
                ).first()

    def claim_next_created_job(self) -> DebugJobRow | None:
        with self._lock:
            with self._session_factory() as session:
                job = session.scalars(
                    select(DebugJobRow)
                    .where(DebugJobRow.status == "created")
                    .order_by(DebugJobRow.job_id)
                    .limit(1)
                ).first()
                if job is None:
                    return None
                job.status = "running"
                job.attempt_count += 1
                job.updated_at = _utc_now_iso()
                session.commit()
                return job

    def save_evidence(
        self,
        job_id: str,
        case_id: str,
        evidence: list[ExperimentEvidence],
    ) -> None:
        with self._lock:
            with self._session_factory() as session:
                for item in evidence:
                    session.merge(
                        EvidenceRow(
                            evidence_id=item.evidence_id,
                            job_id=job_id,
                            case_id=case_id,
                            step_name=item.step_name,
                            trial=item.trial,
                            model_name=item.model_name,
                            model_provider=item.model_provider,
                            model_id=item.model_id,
                            request_summary_json=json.dumps(item.request_summary),
                            latency_ms=item.latency_ms,
                            response_parse_error=item.response_parse_error,
                            model_call_error_type=item.model_call_error_type,
                            model_call_error_message=item.model_call_error_message,
                            image_artifacts_json=json.dumps(
                                [artifact.model_dump() for artifact in item.image_artifacts]
                            ),
                            artifacts_json=json.dumps([artifact.model_dump() for artifact in item.artifacts]),
                            score=item.judge.score,
                            reasons_json=json.dumps(item.judge.model_dump()),
                            raw_output=item.raw_output,
                        )
                    )
                session.commit()

    def list_evidence_ids(self, job_id: str) -> list[str]:
        with self._lock:
            with self._session_factory() as session:
                rows = session.scalars(
                    select(EvidenceRow.evidence_id)
                    .where(EvidenceRow.job_id == job_id)
                    .order_by(EvidenceRow.evidence_id)
                )
                return list(rows)

    def list_evidence(self, job_id: str) -> list[ExperimentEvidence]:
        evidence: list[ExperimentEvidence] = []
        for evidence_id in self.list_evidence_ids(job_id):
            item = self.get_evidence(job_id, evidence_id)
            if item is not None:
                evidence.append(item)
        return evidence

    def count_evidence_errors(self, job_id: str) -> dict[str, int]:
        with self._lock:
            with self._session_factory() as session:
                rows = list(
                    session.scalars(
                        select(EvidenceRow)
                        .where(EvidenceRow.job_id == job_id)
                        .order_by(EvidenceRow.evidence_id)
                    )
                )
                return {
                    "total_evidence": len(rows),
                    "failed_judgements": sum(1 for row in rows if row.score == 0),
                    "response_parse_errors": sum(1 for row in rows if row.response_parse_error),
                    "model_call_errors": sum(1 for row in rows if row.model_call_error_type),
                }

    def summarize_evidence_quality(self) -> dict[str, int | float]:
        with self._lock:
            with self._session_factory() as session:
                rows = list(session.scalars(select(EvidenceRow).order_by(EvidenceRow.job_id, EvidenceRow.evidence_id)))
                total_evidence = len(rows)
                average_latency_ms = (
                    round(sum(row.latency_ms for row in rows) / total_evidence, 2) if total_evidence > 0 else 0
                )
                return {
                    "total_evidence": total_evidence,
                    "failed_judgements": sum(1 for row in rows if row.score == 0),
                    "response_parse_errors": sum(1 for row in rows if row.response_parse_error),
                    "model_call_errors": sum(1 for row in rows if row.model_call_error_type),
                    "average_latency_ms": average_latency_ms,
                }

    def summarize_usage(self) -> dict[str, int | float]:
        with self._lock:
            with self._session_factory() as session:
                rows = list(session.scalars(select(EvidenceRow).order_by(EvidenceRow.job_id, EvidenceRow.evidence_id)))
                prompt_character_count = 0
                for row in rows:
                    request_summary = json.loads(row.request_summary_json)
                    if isinstance(request_summary, dict):
                        prompt_length = request_summary.get("prompt_length", 0)
                        if isinstance(prompt_length, int | float):
                            prompt_character_count += int(prompt_length)
                return {
                    "model_call_count": len(rows),
                    "prompt_character_count": prompt_character_count,
                    "estimated_cost_units": round(len(rows) + prompt_character_count / 1000, 4),
                }

    def get_evidence(self, job_id: str, evidence_id: str) -> ExperimentEvidence | None:
        with self._lock:
            with self._session_factory() as session:
                row = session.get(EvidenceRow, (job_id, evidence_id))
                if row is None:
                    return None
                judge_payload = json.loads(row.reasons_json)
                request_summary = json.loads(row.request_summary_json)
                if not isinstance(request_summary, dict):
                    raise ValueError(f"Evidence request summary must be an object: {evidence_id}")
                image_artifacts = json.loads(row.image_artifacts_json)
                if not isinstance(image_artifacts, list):
                    raise ValueError(f"Evidence image artifacts must be a list: {evidence_id}")
                artifacts = json.loads(row.artifacts_json)
                if not isinstance(artifacts, list):
                    raise ValueError(f"Evidence artifacts must be a list: {evidence_id}")
                return ExperimentEvidence(
                    evidence_id=row.evidence_id,
                    step_name=row.step_name,
                    trial=row.trial,
                    model_name=row.model_name,
                    model_provider=row.model_provider,
                    model_id=row.model_id,
                    request_summary=request_summary,
                    latency_ms=row.latency_ms,
                    response_parse_error=row.response_parse_error,
                    model_call_error_type=row.model_call_error_type,
                    model_call_error_message=row.model_call_error_message,
                    image_artifacts=image_artifacts,
                    artifacts=artifacts,
                    raw_output=row.raw_output,
                    judge=_judge_result_from_payload(score=row.score, evidence_id=evidence_id, payload=judge_payload),
                )

    def _set_status(self, job_id: str, status: str) -> None:
        with self._lock:
            with self._session_factory() as session:
                job = session.get(DebugJobRow, job_id)
                if job is None:
                    raise KeyError(f"Debug job not found: {job_id}")
                job.status = status
                job.updated_at = _utc_now_iso()
                session.commit()


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def _judge_result_from_payload(*, score: int, evidence_id: str, payload: object) -> JudgeResult:
    if isinstance(payload, list):
        return JudgeResult(score=score, reasons=[str(reason) for reason in payload])
    if not isinstance(payload, dict):
        raise ValueError(f"Evidence judge payload must be an object or reasons list: {evidence_id}")
    payload_with_score = dict(payload)
    payload_with_score["score"] = score
    return JudgeResult.model_validate(payload_with_score)


def _spreadsheet_writeback_audit_from_row(row: SpreadsheetWritebackAuditRow) -> SpreadsheetWritebackAudit:
    fields = json.loads(row.fields_json)
    if not isinstance(fields, dict):
        raise ValueError(f"Spreadsheet writeback fields must be an object: {row.job_id}")
    return SpreadsheetWritebackAudit(
        job_id=row.job_id,
        status=row.status,
        row_id=row.row_id,
        report_url=row.report_url,
        fields={str(key): str(value) for key, value in fields.items()},
        error_message=row.error_message,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _recommended_action_status_from_row(row: RecommendedActionStatusRow) -> RecommendedActionStatus:
    return RecommendedActionStatus(
        job_id=row.job_id,
        action_index=row.action_index,
        status=row.status,
        actor=row.actor,
        note=row.note,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _recommended_action_status_event_from_row(row: RecommendedActionStatusEventRow) -> RecommendedActionStatusEvent:
    return RecommendedActionStatusEvent(
        event_id=row.event_id,
        job_id=row.job_id,
        action_index=row.action_index,
        status=row.status,
        actor=row.actor,
        note=row.note,
        created_at=row.created_at,
    )


def _recommended_action_verification_from_row(row: RecommendedActionVerificationRow) -> RecommendedActionVerification:
    return RecommendedActionVerification(
        job_id=row.job_id,
        action_index=row.action_index,
        verification_job_id=row.verification_job_id,
        actor=row.actor,
        note=row.note,
        created_at=row.created_at,
    )


def _strategy_follow_up_job_from_row(row: StrategyFollowUpJobRow) -> StrategyFollowUpJob:
    return StrategyFollowUpJob(
        source_job_id=row.source_job_id,
        stage=row.stage,
        planned_steps=row.planned_steps,
        follow_up_job_id=row.follow_up_job_id,
        actor=row.actor,
        note=row.note,
        created_at=row.created_at,
    )


def _targeted_probe_job_from_row(row: TargetedProbeJobRow) -> TargetedProbeJob:
    return TargetedProbeJob(
        source_job_id=row.source_job_id,
        target_id=row.target_id,
        planned_steps=row.planned_steps,
        probe_job_id=row.probe_job_id,
        actor=row.actor,
        note=row.note,
        created_at=row.created_at,
    )
