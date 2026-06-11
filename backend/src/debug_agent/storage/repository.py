import json
import threading
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from debug_agent.cases.models import DebugCase
from debug_agent.experiments.runner import ExperimentEvidence
from debug_agent.storage.models import DebugCaseRow, DebugJobRow, EvidenceRow


class DebugJobRepository:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory
        self._lock = threading.RLock()

    def create_job(self, job_id: str, case_id: str) -> None:
        with self._lock:
            with self._session_factory() as session:
                session.add(DebugJobRow(job_id=job_id, case_id=case_id, status="created"))
                session.commit()

    def save_case(self, case: DebugCase) -> None:
        with self._lock:
            with self._session_factory() as session:
                session.merge(DebugCaseRow(case_id=case.case_id, case_json=case.model_dump_json()))
                session.commit()

    def get_case(self, case_id: str) -> DebugCase | None:
        with self._lock:
            with self._session_factory() as session:
                row = session.get(DebugCaseRow, case_id)
                if row is None:
                    return None
                return DebugCase.model_validate_json(row.case_json)

    def list_cases(self) -> list[DebugCase]:
        with self._lock:
            with self._session_factory() as session:
                rows = session.scalars(select(DebugCaseRow).order_by(DebugCaseRow.case_id))
                return [DebugCase.model_validate_json(row.case_json) for row in rows]

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
                session.commit()

    def release_for_retry(self, job_id: str, error_message: str) -> None:
        with self._lock:
            with self._session_factory() as session:
                job = session.get(DebugJobRow, job_id)
                if job is None:
                    raise KeyError(f"Debug job not found: {job_id}")
                job.status = "created"
                job.error_message = error_message
                session.commit()

    def get_job(self, job_id: str) -> DebugJobRow | None:
        with self._lock:
            with self._session_factory() as session:
                return session.get(DebugJobRow, job_id)

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
                            score=item.judge.score,
                            reasons_json=json.dumps(item.judge.reasons),
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

    def _set_status(self, job_id: str, status: str) -> None:
        with self._lock:
            with self._session_factory() as session:
                job = session.get(DebugJobRow, job_id)
                if job is None:
                    raise KeyError(f"Debug job not found: {job_id}")
                job.status = status
                session.commit()
