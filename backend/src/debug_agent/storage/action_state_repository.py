from __future__ import annotations

from sqlalchemy import select

from debug_agent.storage.models import (
    HumanHandoffStatusRow,
    RecommendedActionStatusEventRow,
    RecommendedActionStatusRow,
    RecommendedActionVerificationRow,
    StrategyFollowUpJobRow,
    TargetedProbeJobRow,
)
from debug_agent.storage.row_mappers import (
    _human_handoff_status_from_row,
    _recommended_action_status_event_from_row,
    _recommended_action_status_from_row,
    _recommended_action_verification_from_row,
    _strategy_follow_up_job_from_row,
    _targeted_probe_job_from_row,
    _utc_now_iso,
)
from debug_agent.storage.schemas import (
    HumanHandoffStatus,
    RecommendedActionStatus,
    RecommendedActionStatusEvent,
    RecommendedActionVerification,
    StrategyFollowUpJob,
    TargetedProbeJob,
)


class ActionStateRepositoryMixin:
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
                    query = query.where(
                        RecommendedActionStatusEventRow.action_index == action_index
                    )
                return [
                    _recommended_action_status_event_from_row(row) for row in session.scalars(query)
                ]

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
                    query = query.where(
                        RecommendedActionVerificationRow.action_index == action_index
                    )
                return [
                    _recommended_action_verification_from_row(row) for row in session.scalars(query)
                ]

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

    def list_strategy_follow_up_jobs(
        self, source_job_id: str, stage: str | None = None
    ) -> list[StrategyFollowUpJob]:
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
        source: str = "targeted_probe",
        parent_probe_job_id: str = "",
        trigger_outcome: str = "",
        actor: str = "",
        note: str = "",
    ) -> TargetedProbeJob:
        with self._lock:
            with self._session_factory() as session:
                now = _utc_now_iso()
                row = TargetedProbeJobRow(
                    source_job_id=source_job_id,
                    source=source,
                    target_id=target_id,
                    planned_steps=planned_steps,
                    probe_job_id=probe_job_id,
                    parent_probe_job_id=parent_probe_job_id,
                    trigger_outcome=trigger_outcome,
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

    def list_all_targeted_probe_jobs(self) -> list[TargetedProbeJob]:
        with self._lock:
            with self._session_factory() as session:
                rows = session.scalars(
                    select(TargetedProbeJobRow).order_by(
                        TargetedProbeJobRow.created_at,
                        TargetedProbeJobRow.source_job_id,
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

    def save_human_handoff_status(
        self,
        *,
        job_id: str,
        target_id: str,
        status: str,
        actor: str = "",
        note: str = "",
    ) -> HumanHandoffStatus:
        with self._lock:
            with self._session_factory() as session:
                now = _utc_now_iso()
                existing = session.get(HumanHandoffStatusRow, (job_id, target_id))
                created_at = existing.created_at if existing is not None else now
                row = HumanHandoffStatusRow(
                    job_id=job_id,
                    target_id=target_id,
                    status=status,
                    actor=actor,
                    note=note,
                    created_at=created_at,
                    updated_at=now,
                )
                session.merge(row)
                session.commit()
                return _human_handoff_status_from_row(row)

    def list_human_handoff_statuses(self, job_id: str | None = None) -> list[HumanHandoffStatus]:
        with self._lock:
            with self._session_factory() as session:
                query = select(HumanHandoffStatusRow).order_by(
                    HumanHandoffStatusRow.created_at,
                    HumanHandoffStatusRow.job_id,
                    HumanHandoffStatusRow.target_id,
                )
                if job_id is not None:
                    query = query.where(HumanHandoffStatusRow.job_id == job_id)
                return [_human_handoff_status_from_row(row) for row in session.scalars(query)]
