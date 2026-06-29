from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from debug_agent.api.schemas import (
    ObservabilityEvidenceSummary,
    ObservabilityFinalAttributionRecoveryFeedbackSummary,
    ObservabilityFinalAttributionVerificationFeedbackSummary,
    ObservabilityHealthSummary,
    ObservabilityHumanHandoffFeedbackSummary,
    ObservabilityJobSummary,
    ObservabilityStrategyFeedbackSummary,
    ObservabilitySummaryResponse,
    ObservabilityTargetedProbeFeedbackSummary,
    ObservabilityUsageSummary,
    SpreadsheetWritebackAuditSummaryResponse,
    StrategyFollowUpJobWithOutcome,
    TargetedProbeJobWithOutcome,
    WorkerRuntimeStatus,
)
from debug_agent.reports.job_report import (
    MAX_TARGETED_PROBE_DEPTH,
    build_strategy_follow_up_results,
    build_targeted_probe_results,
)
from debug_agent.storage.repository import DebugJobRepository
from debug_agent.telemetry.performance import performance_summary


class ObservabilityController:
    def __init__(
        self,
        *,
        job_repository: DebugJobRepository,
        worker_status: Callable[[], WorkerRuntimeStatus],
        usage_budget_units: Callable[[], float],
        budget_enforcement_enabled: Callable[[], bool],
    ) -> None:
        self._job_repository = job_repository
        self._worker_status = worker_status
        self._usage_budget_units = usage_budget_units
        self._budget_enforcement_enabled = budget_enforcement_enabled

    def get_summary(self) -> ObservabilitySummaryResponse:
        job_counts = self._job_repository.count_jobs_by_status()
        writeback_counts = self._job_repository.count_spreadsheet_writeback_audits_by_status()
        worker_status = self._worker_status()
        evidence_summary = ObservabilityEvidenceSummary.model_validate(
            self._job_repository.summarize_evidence_quality()
        )
        usage_summary = self.build_usage_summary(
            self._job_repository.summarize_usage(),
            budget_units=self._usage_budget_units(),
            budget_enforcement_enabled=self._budget_enforcement_enabled(),
        )
        strategy_feedback_summary = self.build_strategy_feedback_summary()
        targeted_probe_feedback_summary = self.build_targeted_probe_feedback_summary()
        human_handoff_feedback_summary = self.build_human_handoff_feedback_summary()
        final_attribution_verification_feedback_summary = (
            self.build_final_attribution_verification_feedback_summary()
        )
        final_attribution_recovery_feedback_summary = (
            self.build_final_attribution_recovery_feedback_summary()
        )
        job_summary = ObservabilityJobSummary(
            by_status=job_counts,
            total_count=sum(job_counts.values()),
            pending_count=job_counts.get("created", 0),
            running_count=job_counts.get("running", 0),
            failed_count=job_counts.get("failed", 0),
            completed_count=job_counts.get("completed", 0),
        )
        writeback_summary = SpreadsheetWritebackAuditSummaryResponse(
            by_status=writeback_counts,
            total_count=sum(writeback_counts.values()),
        )
        return ObservabilitySummaryResponse(
            jobs=job_summary,
            worker=worker_status,
            writeback_audits=writeback_summary,
            evidence=evidence_summary,
            strategy_feedback=strategy_feedback_summary,
            targeted_probe_feedback=targeted_probe_feedback_summary,
            human_handoff_feedback=human_handoff_feedback_summary,
            final_attribution_verification_feedback=final_attribution_verification_feedback_summary,
            final_attribution_recovery_feedback=final_attribution_recovery_feedback_summary,
            health=self.build_observability_health(
                jobs=job_summary,
                worker=worker_status,
                writeback_audits=writeback_summary,
                evidence=evidence_summary,
                usage=usage_summary,
                strategy_feedback=strategy_feedback_summary,
                targeted_probe_feedback=targeted_probe_feedback_summary,
                human_handoff_feedback=human_handoff_feedback_summary,
                final_attribution_verification_feedback=final_attribution_verification_feedback_summary,
                final_attribution_recovery_feedback=final_attribution_recovery_feedback_summary,
            ),
            usage=usage_summary,
            performance=performance_summary(limit=20),
        )

    def build_usage_summary(
        self,
        raw_usage: dict[str, int | float],
        *,
        budget_units: float,
        budget_enforcement_enabled: bool,
    ) -> ObservabilityUsageSummary:
        estimated_cost_units = float(raw_usage["estimated_cost_units"])
        budget_status: Literal["not_configured", "within_budget", "over_budget"] = (
            "not_configured"
        )
        budget_utilization = 0.0
        if budget_units > 0:
            budget_utilization = round(estimated_cost_units / budget_units, 4)
            budget_status = (
                "over_budget" if estimated_cost_units > budget_units else "within_budget"
            )
        return ObservabilityUsageSummary(
            model_call_count=int(raw_usage["model_call_count"]),
            prompt_character_count=int(raw_usage["prompt_character_count"]),
            estimated_cost_units=estimated_cost_units,
            budget_units=budget_units,
            budget_status=budget_status,
            budget_utilization=budget_utilization,
            budget_enforcement_enabled=budget_enforcement_enabled,
        )

    def build_strategy_feedback_summary(self) -> ObservabilityStrategyFeedbackSummary:
        outcomes = [
            StrategyFollowUpJobWithOutcome.model_validate(follow_up)
            for source_job_id in {
                follow_up.source_job_id
                for follow_up in self._job_repository.list_all_strategy_follow_up_jobs()
            }
            for follow_up in build_strategy_follow_up_results(
                self._job_repository, source_job_id
            )
        ]
        return ObservabilityStrategyFeedbackSummary(
            total_follow_ups=len(outcomes),
            pending_count=sum(1 for item in outcomes if item.outcome == "pending"),
            passed_stop_condition_count=sum(
                1 for item in outcomes if item.outcome == "passed_stop_condition"
            ),
            needs_escalation_count=sum(
                1 for item in outcomes if item.outcome == "needs_escalation"
            ),
        )

    def build_targeted_probe_feedback_summary(self) -> ObservabilityTargetedProbeFeedbackSummary:
        outcomes = [
            TargetedProbeJobWithOutcome.model_validate(probe)
            for source_job_id in {
                probe.source_job_id for probe in self._job_repository.list_all_targeted_probe_jobs()
            }
            for probe in build_targeted_probe_results(self._job_repository, source_job_id)
        ]
        return ObservabilityTargetedProbeFeedbackSummary(
            total_probes=len(outcomes),
            pending_count=sum(1 for item in outcomes if item.outcome == "pending"),
            target_cleared_count=sum(1 for item in outcomes if item.outcome == "target_cleared"),
            target_still_failing_count=sum(
                1 for item in outcomes if item.outcome == "target_still_failing"
            ),
            inconclusive_count=sum(1 for item in outcomes if item.outcome == "inconclusive"),
            max_depth_reached_count=count_targeted_probe_max_depth_chains(outcomes),
        )

    def build_human_handoff_feedback_summary(self) -> ObservabilityHumanHandoffFeedbackSummary:
        statuses = self._job_repository.list_human_handoff_statuses()
        pending_count = sum(1 for item in statuses if item.status == "pending")
        acknowledged_count = sum(1 for item in statuses if item.status == "acknowledged")
        in_progress_count = sum(1 for item in statuses if item.status == "in_progress")
        resolved_count = sum(1 for item in statuses if item.status == "resolved")
        wont_fix_count = sum(1 for item in statuses if item.status == "wont_fix")
        return ObservabilityHumanHandoffFeedbackSummary(
            total_handoffs=len(statuses),
            pending_count=pending_count,
            acknowledged_count=acknowledged_count,
            in_progress_count=in_progress_count,
            resolved_count=resolved_count,
            wont_fix_count=wont_fix_count,
            open_count=pending_count + acknowledged_count + in_progress_count,
        )

    def build_final_attribution_verification_feedback_summary(
        self,
    ) -> ObservabilityFinalAttributionVerificationFeedbackSummary:
        outcomes = [
            StrategyFollowUpJobWithOutcome.model_validate(follow_up)
            for source_job_id in {
                follow_up.source_job_id
                for follow_up in self._job_repository.list_all_strategy_follow_up_jobs()
                if follow_up.stage.startswith("final_attribution:")
            }
            for follow_up in build_strategy_follow_up_results(
                self._job_repository, source_job_id
            )
            if str(follow_up.get("stage", "")).startswith("final_attribution:")
        ]
        return ObservabilityFinalAttributionVerificationFeedbackSummary(
            total_verifications=len(outcomes),
            pending_count=sum(1 for item in outcomes if item.outcome == "pending"),
            resolved_count=sum(1 for item in outcomes if item.outcome == "passed_stop_condition"),
            not_resolved_count=sum(1 for item in outcomes if item.outcome == "needs_escalation"),
            inconclusive_count=sum(1 for item in outcomes if item.outcome == "inconclusive"),
        )

    def build_final_attribution_recovery_feedback_summary(
        self,
    ) -> ObservabilityFinalAttributionRecoveryFeedbackSummary:
        outcomes = [
            StrategyFollowUpJobWithOutcome.model_validate(follow_up)
            for source_job_id in {
                follow_up.source_job_id
                for follow_up in self._job_repository.list_all_strategy_follow_up_jobs()
                if follow_up.stage.startswith("final_attribution_recovery:")
            }
            for follow_up in build_strategy_follow_up_results(
                self._job_repository, source_job_id
            )
            if str(follow_up.get("stage", "")).startswith("final_attribution_recovery:")
        ]
        return ObservabilityFinalAttributionRecoveryFeedbackSummary(
            total_recoveries=len(outcomes),
            pending_count=sum(1 for item in outcomes if item.outcome == "pending"),
            closed_count=sum(1 for item in outcomes if item.outcome == "passed_stop_condition"),
            reopen_count=sum(1 for item in outcomes if item.outcome == "needs_escalation"),
            inconclusive_count=sum(1 for item in outcomes if item.outcome == "inconclusive"),
        )

    def build_observability_health(
        self,
        *,
        jobs: ObservabilityJobSummary,
        worker: WorkerRuntimeStatus,
        writeback_audits: SpreadsheetWritebackAuditSummaryResponse,
        evidence: ObservabilityEvidenceSummary,
        usage: ObservabilityUsageSummary,
        strategy_feedback: ObservabilityStrategyFeedbackSummary,
        targeted_probe_feedback: ObservabilityTargetedProbeFeedbackSummary,
        human_handoff_feedback: ObservabilityHumanHandoffFeedbackSummary,
        final_attribution_verification_feedback: ObservabilityFinalAttributionVerificationFeedbackSummary,
        final_attribution_recovery_feedback: ObservabilityFinalAttributionRecoveryFeedbackSummary,
    ) -> ObservabilityHealthSummary:
        critical_reasons: list[str] = []
        degraded_reasons: list[str] = []
        if jobs.failed_count > 0:
            critical_reasons.append("failed jobs present")
        if worker.error_count > 0:
            critical_reasons.append("worker errors present")
        if writeback_audits.by_status.get("failed", 0) > 0:
            critical_reasons.append("failed spreadsheet writebacks present")
        if evidence.model_call_errors > 0:
            critical_reasons.append("model call errors present")
        if usage.budget_status == "over_budget":
            critical_reasons.append("usage budget exceeded")
        if jobs.pending_count > 0:
            degraded_reasons.append("pending jobs present")
        if jobs.running_count > 0:
            degraded_reasons.append("jobs currently running")
        if evidence.response_parse_errors > 0:
            degraded_reasons.append("response parse errors present")
        if writeback_audits.by_status.get("skipped", 0) > 0:
            degraded_reasons.append("skipped spreadsheet writebacks present")
        if strategy_feedback.needs_escalation_count > 0:
            degraded_reasons.append("strategy follow-ups need escalation")
        if targeted_probe_feedback.target_still_failing_count > 0:
            degraded_reasons.append("targeted probes still failing")
        if targeted_probe_feedback.max_depth_reached_count > 0:
            degraded_reasons.append("targeted probe guardrails reached")
        if human_handoff_feedback.open_count > 0:
            degraded_reasons.append("human handoffs still open")
        if final_attribution_verification_feedback.not_resolved_count > 0:
            degraded_reasons.append("final attribution verifications not resolved")
        if final_attribution_recovery_feedback.reopen_count > 0:
            degraded_reasons.append("final attribution recoveries reopened")
        if critical_reasons:
            reasons = critical_reasons + degraded_reasons
            return ObservabilityHealthSummary(
                level="critical", reasons=reasons, actions=observability_actions(reasons)
            )
        if degraded_reasons:
            return ObservabilityHealthSummary(
                level="degraded",
                reasons=degraded_reasons,
                actions=observability_actions(degraded_reasons),
            )
        return ObservabilityHealthSummary(level="healthy", reasons=[], actions=[])


def count_targeted_probe_max_depth_chains(outcomes: list[TargetedProbeJobWithOutcome]) -> int:
    by_target: dict[tuple[str, str], list[TargetedProbeJobWithOutcome]] = {}
    for outcome in outcomes:
        by_target.setdefault((outcome.source_job_id, outcome.target_id), []).append(outcome)
    return sum(
        1
        for chain in by_target.values()
        if len(chain) >= MAX_TARGETED_PROBE_DEPTH
        and any(item.outcome in {"target_still_failing", "inconclusive"} for item in chain)
    )


def observability_actions(reasons: list[str]) -> list[str]:
    action_by_reason = {
        "failed jobs present": "Inspect failed jobs and open their evidence chain.",
        "worker errors present": "Check worker logs and restart the worker if the error persists.",
        "failed spreadsheet writebacks present": (
            "Retry failed spreadsheet writebacks after checking Lark permissions and sheet headers."
        ),
        "model call errors present": (
            "Check model endpoint health, timeout settings, and retry affected jobs."
        ),
        "usage budget exceeded": (
            "Pause new submissions or raise the usage budget before continuing."
        ),
        "pending jobs present": "Start or scale workers to drain the pending job backlog.",
        "jobs currently running": "Monitor running jobs for timeout or stuck execution.",
        "response parse errors present": (
            "Inspect prompts and parser assumptions for malformed model outputs."
        ),
        "skipped spreadsheet writebacks present": (
            "Check spreadsheet row mappings before retrying writeback."
        ),
        "strategy follow-ups need escalation": (
            "Open strategy follow-up history and run escalation probes."
        ),
        "targeted probes still failing": (
            "Open targeted probe history and escalate unresolved targets."
        ),
        "targeted probe guardrails reached": (
            "Review targeted probe guardrails and assign human investigation."
        ),
        "human handoffs still open": (
            "Review human handoff queue and drive open investigations to resolution."
        ),
        "final attribution verifications not resolved": (
            "Open final attribution verification results and rerun unresolved attribution fixes."
        ),
        "final attribution recoveries reopened": (
            "Open final attribution recovery results and reassign reopened attribution review."
        ),
    }
    actions: list[str] = []
    for reason in reasons:
        action = action_by_reason.get(reason)
        if action and action not in actions:
            actions.append(action)
    return actions
