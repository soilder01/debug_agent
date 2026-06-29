import json
import threading
from collections.abc import Callable
from datetime import datetime

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from debug_agent.cases.models import DebugCase
from debug_agent.experiments.runner import ExperimentEvidence
from debug_agent.storage.action_state_repository import ActionStateRepositoryMixin
from debug_agent.storage.lark_badcase_repository import LarkBadcaseRepositoryMixin
from debug_agent.storage.lark_pending_repository import LarkPendingRepositoryMixin
from debug_agent.storage.lark_writeback_repository import LarkWritebackRepositoryMixin
from debug_agent.storage.row_mappers import (
    _debug_batch_from_row,
    _debug_job_attempt_from_row,
    _debug_run_stage_from_row,
    _debug_run_stage_sort_key,
    _duration_ms,
    _duration_percentile,
    _judge_result_from_payload,
    _utc_now_iso,
)
from debug_agent.storage.schemas import (
    SpreadsheetRowMapping,
    SpreadsheetWritebackAudit as SpreadsheetWritebackAudit,
    LarkReportDocument as LarkReportDocument,
    LarkOperationAudit as LarkOperationAudit,
    LarkWriteConfirmation as LarkWriteConfirmation,
    LarkAuthSession as LarkAuthSession,
    LarkBotPendingCommand as LarkBotPendingCommand,
    XiaoDExecutionRun as XiaoDExecutionRun,
    XiaoDPendingDecision as XiaoDPendingDecision,
    XiaoDCommandAudit as XiaoDCommandAudit,
    LarkBotSetupAcknowledgement as LarkBotSetupAcknowledgement,
    LarkBotBadcaseDraft as LarkBotBadcaseDraft,
    LarkNotificationOutbox as LarkNotificationOutbox,
    RecommendedActionStatus as RecommendedActionStatus,
    RecommendedActionStatusEvent as RecommendedActionStatusEvent,
    RecommendedActionVerification as RecommendedActionVerification,
    StrategyFollowUpJob as StrategyFollowUpJob,
    TargetedProbeJob as TargetedProbeJob,
    HumanHandoffStatus as HumanHandoffStatus,
    DebugRunStage,
    DebugBatch,
    DebugJobAttempt,
)
from debug_agent.storage.models import (
    DebugBatchRow,
    DebugCaseRow,
    DebugJobRow,
    DebugJobAttemptRow,
    DebugRunStageRow,
    EvidenceRow,
    SpreadsheetRowMappingRow,
)


BATCH_TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


class DebugJobRepository(
    ActionStateRepositoryMixin,
    LarkBadcaseRepositoryMixin,
    LarkPendingRepositoryMixin,
    LarkWritebackRepositoryMixin,
):
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory
        self._lock = threading.RLock()

    def create_job(
        self,
        job_id: str,
        case_id: str,
        baseline_trials: int = 0,
        artifact_group_id: str = "single",
    ) -> None:
        with self._lock:
            with self._session_factory() as session:
                now = _utc_now_iso()
                session.add(
                    DebugJobRow(
                        job_id=job_id,
                        case_id=case_id,
                        status="created",
                        artifact_group_id=artifact_group_id,
                        baseline_trials=baseline_trials,
                        created_at=now,
                        updated_at=now,
                    )
                )
                session.merge(
                    DebugRunStageRow(
                        job_id=job_id,
                        stage="baseline",
                        status="pending",
                        input_json=json.dumps(
                            {"case_id": case_id, "baseline_trials": baseline_trials}
                        ),
                        output_json="{}",
                        failure_reason="",
                        retryable=True,
                        attempt_count=0,
                        created_at=now,
                        updated_at=now,
                    )
                )
                session.commit()

    def create_batch(
        self,
        *,
        batch_id: str,
        total_jobs: int,
        max_concurrency: int = 1,
        retry_policy: dict[str, object] | None = None,
    ) -> DebugBatch:
        with self._lock:
            with self._session_factory() as session:
                now = _utc_now_iso()
                row = DebugBatchRow(
                    batch_id=batch_id,
                    status="created",
                    total_jobs=total_jobs,
                    max_concurrency=max(1, max_concurrency),
                    retry_policy_json=json.dumps(retry_policy or {}),
                    created_at=now,
                    updated_at=now,
                    started_at="",
                    completed_at="",
                )
                session.add(row)
                session.commit()
                return _debug_batch_from_row(row)

    def get_batch(self, batch_id: str) -> DebugBatch | None:
        with self._lock:
            with self._session_factory() as session:
                row = session.get(DebugBatchRow, batch_id)
                return _debug_batch_from_row(row) if row is not None else None

    def list_batches(self, limit: int = 50, offset: int = 0) -> list[DebugBatch]:
        with self._lock:
            with self._session_factory() as session:
                rows = session.scalars(
                    select(DebugBatchRow)
                    .order_by(desc(DebugBatchRow.created_at), desc(DebugBatchRow.batch_id))
                    .offset(offset)
                    .limit(limit)
                )
                return [_debug_batch_from_row(row) for row in rows]

    def update_batch_status(self, batch_id: str, status: str) -> DebugBatch:
        with self._lock:
            with self._session_factory() as session:
                row = session.get(DebugBatchRow, batch_id)
                if row is None:
                    raise KeyError(f"Debug batch not found: {batch_id}")
                now = _utc_now_iso()
                row.status = status
                row.updated_at = now
                if status == "running" and not row.started_at:
                    row.started_at = now
                if status in BATCH_TERMINAL_STATUSES and not row.completed_at:
                    row.completed_at = now
                session.commit()
                return _debug_batch_from_row(row)

    def start_job_attempt(self, job_id: str) -> DebugJobAttempt:
        with self._lock:
            with self._session_factory() as session:
                job = session.get(DebugJobRow, job_id)
                if job is None:
                    raise KeyError(f"Debug job not found: {job_id}")
                now = _utc_now_iso()
                row = DebugJobAttemptRow(
                    job_id=job_id,
                    attempt_index=job.attempt_count,
                    batch_id=job.artifact_group_id,
                    status="running",
                    failure_type="",
                    failure_stage="",
                    error_message="",
                    retry_decision="",
                    started_at=now,
                    finished_at="",
                    duration_ms=0,
                )
                session.merge(row)
                batch = session.get(DebugBatchRow, job.artifact_group_id)
                if batch is not None and batch.status == "created":
                    batch.status = "running"
                    batch.started_at = batch.started_at or now
                    batch.updated_at = now
                session.commit()
                return _debug_job_attempt_from_row(row)

    def finish_job_attempt(
        self,
        *,
        job_id: str,
        attempt_index: int,
        status: str,
        failure_type: str = "",
        failure_stage: str = "",
        error_message: str = "",
        retry_decision: str = "",
    ) -> DebugJobAttempt:
        with self._lock:
            with self._session_factory() as session:
                row = session.get(
                    DebugJobAttemptRow, {"job_id": job_id, "attempt_index": attempt_index}
                )
                if row is None:
                    job = session.get(DebugJobRow, job_id)
                    if job is None:
                        raise KeyError(f"Debug job not found: {job_id}")
                    row = DebugJobAttemptRow(
                        job_id=job_id,
                        attempt_index=attempt_index,
                        batch_id=job.artifact_group_id,
                        started_at=_utc_now_iso(),
                    )
                finished_at = _utc_now_iso()
                row.status = status
                row.failure_type = failure_type
                row.failure_stage = failure_stage
                row.error_message = error_message
                row.retry_decision = retry_decision
                row.finished_at = finished_at
                row.duration_ms = _duration_ms(row.started_at, finished_at)
                session.merge(row)
                session.commit()
                return _debug_job_attempt_from_row(row)

    def list_job_attempts(
        self, job_id: str | None = None, batch_id: str | None = None
    ) -> list[DebugJobAttempt]:
        with self._lock:
            with self._session_factory() as session:
                query = select(DebugJobAttemptRow).order_by(
                    DebugJobAttemptRow.started_at,
                    DebugJobAttemptRow.job_id,
                    DebugJobAttemptRow.attempt_index,
                )
                if job_id is not None:
                    query = query.where(DebugJobAttemptRow.job_id == job_id)
                if batch_id is not None:
                    query = query.where(DebugJobAttemptRow.batch_id == batch_id)
                return [_debug_job_attempt_from_row(row) for row in session.scalars(query)]

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

    def list_cases(
        self, has_regions: bool = False, limit: int | None = None, offset: int = 0
    ) -> list[DebugCase]:
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
        self._set_status(job_id, "completed", update_baseline_stage=False)

    def mark_failed(self, job_id: str, error_message: str) -> None:
        with self._lock:
            with self._session_factory() as session:
                job = session.get(DebugJobRow, job_id)
                if job is None:
                    raise KeyError(f"Debug job not found: {job_id}")
                job.status = "failed"
                job.error_message = error_message
                job.updated_at = _utc_now_iso()
                self._merge_debug_run_stage_row(
                    session=session,
                    job_id=job_id,
                    stage="baseline",
                    status="failed",
                    input={"case_id": job.case_id, "baseline_trials": job.baseline_trials},
                    output={"job_status": "failed"},
                    failure_reason=error_message,
                    retryable=False,
                    attempt_count=job.attempt_count,
                )
                session.commit()

    def update_job_status(
        self, job_id: str, status: str, *, error_message: str = ""
    ) -> DebugJobRow:
        with self._lock:
            with self._session_factory() as session:
                job = session.get(DebugJobRow, job_id)
                if job is None:
                    raise KeyError(f"Debug job not found: {job_id}")
                job.status = status
                job.error_message = error_message
                job.updated_at = _utc_now_iso()
                self._merge_debug_run_stage_row(
                    session=session,
                    job_id=job_id,
                    stage="baseline",
                    status=status,
                    input={"case_id": job.case_id, "baseline_trials": job.baseline_trials},
                    output={"job_status": status},
                    failure_reason=error_message,
                    retryable=status not in {"completed", "cancelled", "failed"},
                    attempt_count=job.attempt_count,
                )
                session.commit()
                return job

    def release_for_retry(self, job_id: str, error_message: str) -> None:
        with self._lock:
            with self._session_factory() as session:
                job = session.get(DebugJobRow, job_id)
                if job is None:
                    raise KeyError(f"Debug job not found: {job_id}")
                job.status = "created"
                job.error_message = error_message
                job.updated_at = _utc_now_iso()
                self._merge_debug_run_stage_row(
                    session=session,
                    job_id=job_id,
                    stage="baseline",
                    status="failed",
                    input={"case_id": job.case_id, "baseline_trials": job.baseline_trials},
                    output={"job_status": "created"},
                    failure_reason=error_message,
                    retryable=True,
                    attempt_count=job.attempt_count,
                )
                session.commit()

    def save_debug_run_stage(
        self,
        *,
        job_id: str,
        stage: str,
        status: str,
        input: dict[str, object],
        output: dict[str, object],
        failure_reason: str,
        retryable: bool,
    ) -> DebugRunStage:
        with self._lock:
            with self._session_factory() as session:
                job = session.get(DebugJobRow, job_id)
                if job is None:
                    raise KeyError(f"Debug job not found: {job_id}")
                row = self._merge_debug_run_stage_row(
                    session=session,
                    job_id=job_id,
                    stage=stage,
                    status=status,
                    input=input,
                    output=output,
                    failure_reason=failure_reason,
                    retryable=retryable,
                    attempt_count=job.attempt_count,
                )
                session.commit()
                return _debug_run_stage_from_row(row)

    def list_debug_run_stages(self, job_id: str) -> list[DebugRunStage]:
        with self._lock:
            with self._session_factory() as session:
                rows = session.scalars(
                    select(DebugRunStageRow).where(DebugRunStageRow.job_id == job_id)
                )
                return sorted(
                    [_debug_run_stage_from_row(row) for row in rows],
                    key=lambda stage: _debug_run_stage_sort_key(stage.stage),
                )

    def get_job(self, job_id: str) -> DebugJobRow | None:
        with self._lock:
            with self._session_factory() as session:
                return session.get(DebugJobRow, job_id)

    def list_jobs(
        self,
        status: str | None = None,
        artifact_group_id: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        sort: str = "created_at_asc",
    ) -> list[DebugJobRow]:
        with self._lock:
            with self._session_factory() as session:
                if sort == "created_at_desc":
                    query = select(DebugJobRow).order_by(
                        desc(DebugJobRow.created_at), desc(DebugJobRow.job_id)
                    )
                else:
                    query = select(DebugJobRow).order_by(DebugJobRow.created_at, DebugJobRow.job_id)
                if status is not None:
                    query = query.where(DebugJobRow.status == status)
                if artifact_group_id is not None:
                    query = query.where(DebugJobRow.artifact_group_id == artifact_group_id)
                if offset > 0:
                    query = query.offset(offset)
                if limit is not None:
                    query = query.limit(limit)
                rows = session.scalars(query)
                return list(rows)

    def count_jobs(self, status: str | None = None, artifact_group_id: str | None = None) -> int:
        with self._lock:
            with self._session_factory() as session:
                query = select(func.count()).select_from(DebugJobRow)
                if status is not None:
                    query = query.where(DebugJobRow.status == status)
                if artifact_group_id is not None:
                    query = query.where(DebugJobRow.artifact_group_id == artifact_group_id)
                return session.scalar(query) or 0

    def count_jobs_by_status(self, artifact_group_id: str | None = None) -> dict[str, int]:
        with self._lock:
            with self._session_factory() as session:
                query = (
                    select(DebugJobRow.status, func.count())
                    .group_by(DebugJobRow.status)
                    .order_by(DebugJobRow.status)
                )
                if artifact_group_id is not None:
                    query = query.where(DebugJobRow.artifact_group_id == artifact_group_id)
                rows = session.execute(query)
                return {str(status): int(count) for status, count in rows}

    def failure_type_distribution(self, batch_id: str | None = None) -> dict[str, int]:
        with self._lock:
            with self._session_factory() as session:
                query = (
                    select(DebugJobAttemptRow.failure_type, func.count())
                    .where(DebugJobAttemptRow.failure_type != "")
                    .group_by(DebugJobAttemptRow.failure_type)
                    .order_by(DebugJobAttemptRow.failure_type)
                )
                if batch_id is not None:
                    query = query.where(DebugJobAttemptRow.batch_id == batch_id)
                return {
                    str(failure_type): int(count) for failure_type, count in session.execute(query)
                }

    def failure_stage_distribution(self, batch_id: str | None = None) -> dict[str, int]:
        with self._lock:
            with self._session_factory() as session:
                query = (
                    select(DebugJobAttemptRow.failure_stage, func.count())
                    .where(DebugJobAttemptRow.failure_stage != "")
                    .group_by(DebugJobAttemptRow.failure_stage)
                    .order_by(DebugJobAttemptRow.failure_stage)
                )
                if batch_id is not None:
                    query = query.where(DebugJobAttemptRow.batch_id == batch_id)
                return {str(stage): int(count) for stage, count in session.execute(query)}

    def attempt_metrics(self, batch_id: str | None = None) -> dict[str, int | float]:
        with self._lock:
            with self._session_factory() as session:
                query = select(DebugJobAttemptRow)
                if batch_id is not None:
                    query = query.where(DebugJobAttemptRow.batch_id == batch_id)
                rows = list(session.scalars(query))
                completed = sorted(row.duration_ms for row in rows if row.duration_ms > 0)
                completed_count = len([row for row in rows if row.status == "completed"])
                failed_count = len([row for row in rows if row.status == "failed"])
                terminal_count = completed_count + failed_count
                return {
                    "attempt_count": len(rows),
                    "completed_attempt_count": completed_count,
                    "failed_attempt_count": failed_count,
                    "terminal_attempt_count": terminal_count,
                    "total_duration_ms": sum(completed),
                    "average_duration_ms": round(sum(completed) / len(completed), 2)
                    if completed
                    else 0,
                    "p50_duration_ms": _duration_percentile(completed, 0.50),
                    "p95_duration_ms": _duration_percentile(completed, 0.95),
                    "max_duration_ms": max(completed) if completed else 0,
                    "retry_scheduled_count": len(
                        [row for row in rows if row.retry_decision == "retry_scheduled"]
                    ),
                    "success_rate": round(completed_count / terminal_count, 4)
                    if terminal_count
                    else 0,
                }

    def recover_stale_running_jobs(self, *, stale_before: str) -> list[str]:
        recovered_job_ids: list[str] = []
        with self._lock:
            with self._session_factory() as session:
                rows = session.scalars(
                    select(DebugJobRow)
                    .where(DebugJobRow.status == "running")
                    .where(DebugJobRow.updated_at < stale_before)
                    .order_by(DebugJobRow.updated_at, DebugJobRow.job_id)
                )
                for job in rows:
                    job.status = "created"
                    job.error_message = "Recovered stale running job after worker interruption."
                    job.updated_at = _utc_now_iso()
                    self._merge_debug_run_stage_row(
                        session=session,
                        job_id=job.job_id,
                        stage="queue_runtime",
                        status="recovered",
                        input={"stale_before": stale_before},
                        output={"job_status": "created"},
                        failure_reason="worker_interrupted",
                        retryable=True,
                        attempt_count=job.attempt_count,
                    )
                    recovered_job_ids.append(job.job_id)
                session.commit()
        return recovered_job_ids

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
                created_jobs = list(
                    session.scalars(
                        select(DebugJobRow)
                        .where(DebugJobRow.status == "created")
                        .order_by(DebugJobRow.created_at, DebugJobRow.job_id)
                    )
                )
                job = None
                for candidate in sorted(
                    created_jobs,
                    key=lambda item: self._queue_claim_sort_key(session=session, job=item),
                ):
                    batch = session.get(DebugBatchRow, candidate.artifact_group_id)
                    if batch is not None and batch.status in {
                        "paused",
                        "cancelled",
                        "completed",
                        "failed",
                    }:
                        continue
                    job = candidate
                    break
                if job is None:
                    return None
                job.status = "running"
                job.attempt_count += 1
                job.updated_at = _utc_now_iso()
                self._merge_debug_run_stage_row(
                    session=session,
                    job_id=job.job_id,
                    stage="baseline",
                    status="running",
                    input={"case_id": job.case_id, "baseline_trials": job.baseline_trials},
                    output={"job_status": "running"},
                    failure_reason="",
                    retryable=True,
                    attempt_count=job.attempt_count,
                )
                session.commit()
                return job

    def _queue_priority_rank(self, *, session: Session, job: DebugJobRow) -> int:
        batch = session.get(DebugBatchRow, job.artifact_group_id)
        if batch is None:
            return 10
        try:
            retry_policy = json.loads(batch.retry_policy_json or "{}")
        except json.JSONDecodeError:
            return 10
        if not isinstance(retry_policy, dict):
            return 10
        priority = str(retry_policy.get("queue_priority", "")).strip().lower()
        if priority in {"interactive", "xiaod", "user"}:
            return 0
        return 10

    def _queue_claim_sort_key(self, *, session: Session, job: DebugJobRow) -> tuple[int, float, str]:
        priority_rank = self._queue_priority_rank(session=session, job=job)
        created_at = self._queue_created_at_timestamp(job.created_at)
        if priority_rank == 0:
            created_at = -created_at
        return (priority_rank, created_at, job.job_id)

    @staticmethod
    def _queue_created_at_timestamp(value: str) -> float:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return 0.0

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
                            input_excerpt=item.input_excerpt,
                            latency_ms=item.latency_ms,
                            response_parse_error=item.response_parse_error,
                            model_call_error_type=item.model_call_error_type,
                            model_call_error_message=item.model_call_error_message,
                            image_artifacts_json=json.dumps(
                                [artifact.model_dump() for artifact in item.image_artifacts]
                            ),
                            artifacts_json=json.dumps(
                                [artifact.model_dump() for artifact in item.artifacts]
                            ),
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
                rows = list(
                    session.scalars(
                        select(EvidenceRow).order_by(EvidenceRow.job_id, EvidenceRow.evidence_id)
                    )
                )
                total_evidence = len(rows)
                average_latency_ms = (
                    round(sum(row.latency_ms for row in rows) / total_evidence, 2)
                    if total_evidence > 0
                    else 0
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
                rows = list(
                    session.scalars(
                        select(EvidenceRow).order_by(EvidenceRow.job_id, EvidenceRow.evidence_id)
                    )
                )
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
                    input_excerpt=row.input_excerpt,
                    latency_ms=row.latency_ms,
                    response_parse_error=row.response_parse_error,
                    model_call_error_type=row.model_call_error_type,
                    model_call_error_message=row.model_call_error_message,
                    image_artifacts=image_artifacts,
                    artifacts=artifacts,
                    raw_output=row.raw_output,
                    judge=_judge_result_from_payload(
                        score=row.score, evidence_id=evidence_id, payload=judge_payload
                    ),
                )

    def _set_status(self, job_id: str, status: str, update_baseline_stage: bool = True) -> None:
        with self._lock:
            with self._session_factory() as session:
                job = session.get(DebugJobRow, job_id)
                if job is None:
                    raise KeyError(f"Debug job not found: {job_id}")
                job.status = status
                if status == "running":
                    job.attempt_count += 1
                job.updated_at = _utc_now_iso()
                if update_baseline_stage:
                    self._merge_debug_run_stage_row(
                        session=session,
                        job_id=job_id,
                        stage="baseline",
                        status=status,
                        input={"case_id": job.case_id, "baseline_trials": job.baseline_trials},
                        output={"job_status": status},
                        failure_reason="",
                        retryable=status != "completed",
                        attempt_count=job.attempt_count,
                    )
                session.commit()

    def _merge_debug_run_stage_row(
        self,
        *,
        session: Session,
        job_id: str,
        stage: str,
        status: str,
        input: dict[str, object],
        output: dict[str, object],
        failure_reason: str,
        retryable: bool,
        attempt_count: int,
    ) -> DebugRunStageRow:
        existing = session.get(DebugRunStageRow, {"job_id": job_id, "stage": stage})
        now = _utc_now_iso()
        created_at = existing.created_at if existing is not None else now
        row = DebugRunStageRow(
            job_id=job_id,
            stage=stage,
            status=status,
            input_json=json.dumps(input),
            output_json=json.dumps(output),
            failure_reason=failure_reason,
            retryable=retryable,
            attempt_count=attempt_count,
            created_at=created_at,
            updated_at=now,
        )
        return session.merge(row)
