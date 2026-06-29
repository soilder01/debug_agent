import json
import subprocess
from pathlib import Path
from typing import Protocol
from urllib.parse import unquote, urlparse

from pydantic import BaseModel, Field

from debug_agent.cases.models import DebugCase
from debug_agent.debug_closure import (
    DEFAULT_DEBUG_LOOP_POLICY,
    CausalComparisonResult,
    DebugHypothesis,
    DebugLoopPolicy,
    DebugProbeRunResult,
    HypothesisClosurePayload,
    build_controlled_probe_draft,
    compare_probe_outcome,
    current_iteration,
    intervention_requires_locked_model_runner,
    loop_budget_payload,
    next_iteration_hypotheses,
    normalize_hypotheses,
    run_non_runner_probe,
    run_hypothesis_strategy_agent,
    should_escalate_loop,
    submit_controlled_probe_job,
    synthesize_probe_plans,
)
from debug_agent.debug_closure.hypotheses import DebugProbePlan
from debug_agent.jobs.service import DebugJobService
from debug_agent.settings import ArkSettings
from debug_agent.reports.generator import DebugReport
from debug_agent.reports.job_report import build_report_for_job
from debug_agent.spreadsheets.writeback import (
    SpreadsheetWritebackClient,
    build_report_writeback_fields,
)
from debug_agent.storage.repository import DebugJobRepository


class AutoDebugClosureResult(BaseModel):
    source_job_id: str
    created_targeted_probe_jobs: list[str] = Field(default_factory=list)
    created_strategy_follow_up_jobs: list[str] = Field(default_factory=list)
    created_verification_jobs: list[str] = Field(default_factory=list)
    evidence_summaries: list[dict[str, object]] = Field(default_factory=list)
    targeted_probe_outcomes: list[dict[str, str]] = Field(default_factory=list)
    final_attribution_candidates: list[dict[str, str]] = Field(default_factory=list)
    badcase_live_comparison: dict[str, str] = Field(default_factory=dict)
    writeback_status: str = "not_requested"
    hypotheses: list[dict[str, object]] = Field(default_factory=list)
    probe_plans: list[dict[str, object]] = Field(default_factory=list)
    probe_results: list[dict[str, object]] = Field(default_factory=list)
    causal_comparisons: list[dict[str, object]] = Field(default_factory=list)
    verified_root_causes: list[dict[str, str]] = Field(default_factory=list)
    unverified_hypotheses: list[dict[str, str]] = Field(default_factory=list)
    fairness_lock: dict[str, object] = Field(default_factory=dict)
    debug_loop: dict[str, object] = Field(default_factory=dict)


class _HypothesisClosureBuildResult(BaseModel):
    payload: HypothesisClosurePayload
    strategy_agent_trace: dict[str, object] = Field(default_factory=dict)
    strategy_agent_error: str = ""


class VideoClipper(Protocol):
    def create_clip(self, *, source_uri: str, target_id: str, start_s: float, end_s: float) -> str:
        """Create a local video clip for a targeted probe and return its URI."""


class LocalVideoClipper:
    def __init__(self, output_dir: Path, *, skip_missing_source: bool = False) -> None:
        self._output_dir = output_dir
        self._skip_missing_source = skip_missing_source

    def create_clip(self, *, source_uri: str, target_id: str, start_s: float, end_s: float) -> str:
        source_path = _local_path_from_file_uri(source_uri)
        if self._skip_missing_source and not source_path.exists():
            return source_uri
        self._output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self._output_dir / (
            f"{source_path.stem}_{_safe_case_fragment(target_id)}_{start_s:.1f}_{end_s:.1f}.mp4"
        )
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                f"{start_s:.1f}",
                "-to",
                f"{end_s:.1f}",
                "-i",
                str(source_path),
                "-vf",
                "scale='min(640,iw)':-2,fps=5",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "30",
                "-an",
                str(output_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return output_path.resolve().as_uri()


async def run_auto_debug_closure(
    *,
    repository: DebugJobRepository,
    job_service: DebugJobService,
    job_id: str,
    actor: str = "auto-debug-agent",
    writeback_client: SpreadsheetWritebackClient | None = None,
    video_clipper: VideoClipper | None = None,
    report_url: str = "",
    submit_controlled_probes: bool = False,
    execute_follow_up_jobs: bool = True,
    max_loop_iterations: int = DEFAULT_DEBUG_LOOP_POLICY.max_iterations,
) -> AutoDebugClosureResult:
    report = build_report_for_job(repository, job_id)
    if report is None:
        raise KeyError(f"Debug report not found for job: {job_id}")
    result = AutoDebugClosureResult(source_job_id=job_id)
    await _attach_hypothesis_closure(
        repository=repository,
        job_service=job_service,
        job_id=job_id,
        report=report,
        result=result,
        submit_controlled_probes=submit_controlled_probes,
        loop_policy=DebugLoopPolicy(max_iterations=max_loop_iterations),
    )
    targeted_probe_results = await _run_targeted_probes(
        repository=repository,
        job_service=job_service,
        job_id=job_id,
        report=report,
        actor=actor,
        video_clipper=video_clipper,
        execute_jobs=execute_follow_up_jobs,
    )
    result.created_targeted_probe_jobs = [item["probe_job_id"] for item in targeted_probe_results]
    result.targeted_probe_outcomes = targeted_probe_results
    result.created_strategy_follow_up_jobs = await _run_stability_follow_up(
        repository=repository,
        job_service=job_service,
        job_id=job_id,
        report=report,
        actor=actor,
        execute_jobs=execute_follow_up_jobs,
    )
    result.final_attribution_candidates = _final_attribution_candidates(report)
    result.badcase_live_comparison = _badcase_live_comparison(
        repository=repository,
        job_id=job_id,
        report=report,
        final_attribution_candidates=result.final_attribution_candidates,
    )
    result.created_verification_jobs = await _run_recommended_action_verifications(
        repository=repository,
        job_service=job_service,
        job_id=job_id,
        report=report,
        actor=actor,
        execute_jobs=execute_follow_up_jobs,
    )
    result.evidence_summaries = _evidence_summaries(
        repository=repository,
        job_ids=[
            job_id,
            *result.created_targeted_probe_jobs,
            *result.created_strategy_follow_up_jobs,
            *result.created_verification_jobs,
        ],
    )
    result.writeback_status = _writeback_if_possible(
        repository=repository,
        writeback_client=writeback_client,
        job_id=job_id,
        report=report,
        closure_result=result,
        report_url=report_url,
    )
    return result


async def _attach_hypothesis_closure(
    *,
    repository: DebugJobRepository,
    job_service: DebugJobService,
    job_id: str,
    report: DebugReport,
    result: AutoDebugClosureResult,
    submit_controlled_probes: bool,
    loop_policy: DebugLoopPolicy,
) -> None:
    try:
        build_result = await _build_hypothesis_closure(
            repository=repository,
            job_service=job_service,
            job_id=job_id,
            report=report,
            submit_controlled_probes=submit_controlled_probes,
            loop_policy=loop_policy,
        )
        payload = build_result.payload
    except Exception as exc:
        failure_payload = HypothesisClosurePayload(
            fairness_lock={"model_runner_config_ref": "locked_source"}
        )
        repository.save_debug_run_stage(
            job_id=job_id,
            stage="hypothesis",
            status="failed",
            input={"job_id": job_id, "report_job_id": report.job_id or ""},
            output={"hypothesis_closure": failure_payload.model_dump(mode="json")},
            failure_reason=str(exc),
            retryable=False,
        )
        result.fairness_lock = failure_payload.fairness_lock
        result.unverified_hypotheses = [
            {
                "hypothesis_id": "hypothesis_closure_failed",
                "status": "inconclusive",
                "summary": str(exc),
            }
        ]
        result.debug_loop = _debug_loop_failure_payload(job_id=job_id, error_message=str(exc))
        _save_debug_loop_stage(
            repository=repository,
            job_id=job_id,
            debug_loop=result.debug_loop,
        )
        return

    verified_root_causes = _verified_root_causes(payload.causal_comparisons)
    unverified_hypotheses = _unverified_hypotheses(payload.hypotheses)
    closure_output = payload.model_dump(mode="json")
    closure_output["verified_root_causes"] = verified_root_causes
    closure_output["unverified_hypotheses"] = unverified_hypotheses
    stage_output: dict[str, object] = {"hypothesis_closure": closure_output}
    if build_result.strategy_agent_trace:
        stage_output["strategy_agent_trace"] = build_result.strategy_agent_trace
    if build_result.strategy_agent_error:
        stage_output["strategy_agent_error"] = build_result.strategy_agent_error
    repository.save_debug_run_stage(
        job_id=job_id,
        stage="hypothesis",
        status="completed",
        input={"job_id": job_id, "report_job_id": report.job_id or ""},
        output=stage_output,
        failure_reason="",
        retryable=False,
    )
    result.hypotheses = [item.model_dump(mode="json") for item in payload.hypotheses]
    result.probe_plans = [item.model_dump(mode="json") for item in payload.probe_plans]
    result.probe_results = [item.model_dump(mode="json") for item in payload.probe_results]
    result.causal_comparisons = [
        item.model_dump(mode="json") for item in payload.causal_comparisons
    ]
    result.fairness_lock = payload.fairness_lock
    result.verified_root_causes = verified_root_causes
    result.unverified_hypotheses = unverified_hypotheses
    result.debug_loop = _debug_loop_payload(
        job_id=job_id,
        payload=payload,
        verified_root_causes=verified_root_causes,
        unverified_hypotheses=unverified_hypotheses,
        loop_policy=loop_policy,
    )
    _save_debug_loop_stage(
        repository=repository,
        job_id=job_id,
        debug_loop=result.debug_loop,
    )


async def _build_hypothesis_closure(
    *,
    repository: DebugJobRepository,
    job_service: DebugJobService,
    job_id: str,
    report: DebugReport,
    submit_controlled_probes: bool,
    loop_policy: DebugLoopPolicy,
) -> _HypothesisClosureBuildResult:
    previous_payload = _previous_hypothesis_closure_payload(repository=repository, job_id=job_id)
    agent_trace: dict[str, object] = {}
    agent_error = ""
    if previous_payload is None:
        agent_hypotheses, agent_trace, agent_error = await _strategy_agent_hypotheses(
            repository=repository,
            job_service=job_service,
            job_id=job_id,
            report=report,
        )
        hypotheses = normalize_hypotheses(
            [
                *agent_hypotheses,
                *_candidate_hypotheses_from_report(report),
            ]
        )
    else:
        hypotheses = normalize_hypotheses(previous_payload.hypotheses)
    probe_plans = _bounded_probe_plans(
        synthesize_probe_plans(hypotheses),
        loop_policy=loop_policy,
    )
    probe_results = _probe_results_for_plans(
        repository=repository,
        job_service=job_service,
        job_id=job_id,
        probe_plans=probe_plans,
        submit_controlled_probes=submit_controlled_probes,
    )
    baseline_success_rate = _report_success_rate(report)
    causal_comparisons = _causal_comparisons_for_probe_results(
        repository=repository,
        probe_plans=probe_plans,
        probe_results=probe_results,
        baseline_success_rate=baseline_success_rate,
    )
    payload = HypothesisClosurePayload(
        hypotheses=hypotheses,
        probe_plans=probe_plans,
        probe_results=probe_results,
        causal_comparisons=causal_comparisons,
        fairness_lock=_fairness_lock_payload(),
    )
    if submit_controlled_probes and should_escalate_loop(payload=payload, policy=loop_policy):
        hypotheses = normalize_hypotheses(
            [
                *hypotheses,
                *next_iteration_hypotheses(
                    current_iteration_value=current_iteration(payload),
                    evidence_ids=_report_evidence_ids(report),
                ),
            ]
        )
        probe_plans = _bounded_probe_plans(
            synthesize_probe_plans(hypotheses),
            loop_policy=loop_policy,
        )
        probe_results = _probe_results_for_plans(
            repository=repository,
            job_service=job_service,
            job_id=job_id,
            probe_plans=probe_plans,
            submit_controlled_probes=submit_controlled_probes,
        )
        causal_comparisons = _causal_comparisons_for_probe_results(
            repository=repository,
            probe_plans=probe_plans,
            probe_results=probe_results,
            baseline_success_rate=baseline_success_rate,
        )
        payload = HypothesisClosurePayload(
            hypotheses=hypotheses,
            probe_plans=probe_plans,
            probe_results=probe_results,
            causal_comparisons=causal_comparisons,
            fairness_lock=_fairness_lock_payload(),
        )
    return _HypothesisClosureBuildResult(
        payload=payload,
        strategy_agent_trace=agent_trace,
        strategy_agent_error=agent_error,
    )


def _previous_hypothesis_closure_payload(
    *,
    repository: DebugJobRepository,
    job_id: str,
) -> HypothesisClosurePayload | None:
    stage = next(
        (
            item
            for item in reversed(repository.list_debug_run_stages(job_id))
            if item.stage == "hypothesis"
        ),
        None,
    )
    if stage is None:
        return None
    payload = stage.output.get("hypothesis_closure")
    if not isinstance(payload, dict):
        return None
    try:
        return HypothesisClosurePayload.model_validate(payload)
    except Exception:
        return None


def _bounded_probe_plans(
    probe_plans: list[DebugProbePlan],
    *,
    loop_policy: DebugLoopPolicy,
) -> list[DebugProbePlan]:
    counts_by_iteration: dict[int, int] = {}
    selected: list[DebugProbePlan] = []
    for plan in probe_plans:
        count = counts_by_iteration.get(plan.iteration, 0)
        if count >= loop_policy.max_probe_plans_per_iteration:
            continue
        selected.append(plan)
        counts_by_iteration[plan.iteration] = count + 1
    return selected


def _fairness_lock_payload() -> dict[str, object]:
    return {
        "model_runner_config_ref": "locked_source",
        "source_replay_role": "model_runner",
    }


async def _strategy_agent_hypotheses(
    *,
    repository: DebugJobRepository,
    job_service: DebugJobService,
    job_id: str,
    report: DebugReport,
) -> tuple[list[DebugHypothesis], dict[str, object], str]:
    job = repository.get_job(job_id)
    if job is None:
        return [], {}, ""
    case = repository.get_case(job.case_id)
    if case is None:
        return [], {}, ""
    config = job_service.agent_model_config_for_artifact_group(job.artifact_group_id)
    if config is None or "hypothesis_strategist" not in config.roles:
        return [], {}, ""
    result = await run_hypothesis_strategy_agent(case=case, report=report, config=config)
    return (
        result.hypotheses,
        result.agent_trace.model_dump(mode="json"),
        result.error_message,
    )


def _candidate_hypotheses_from_report(report: DebugReport) -> list[DebugHypothesis]:
    evidence_ids = _report_evidence_ids(report)
    text = " ".join(
        [
            report.observed_failure.type,
            report.observed_failure.summary,
            report.root_cause.label,
            report.root_cause.evidence_summary,
        ]
    ).lower()
    hypotheses: list[DebugHypothesis] = []
    if any(marker in text for marker in ("prompt", "schema", "json", "mismatch", "output")):
        hypotheses.append(
            DebugHypothesis(
                hypothesis_id="h-prompt-constraint",
                category="prompt_constraint",
                claim="Prompt or schema constraints may be insufficient for the observed mismatch.",
                supporting_evidence_ids=evidence_ids,
                missing_evidence=["prompt_patch_probe"],
                confidence_before_probe="medium" if evidence_ids else "low",
            )
        )
    if any(marker in text for marker in ("score", "scoring", "judge", "mismatch", "output")):
        hypotheses.append(
            DebugHypothesis(
                hypothesis_id="h-scoring-strictness",
                category="scoring_strictness",
                claim="The strict scoring rubric may be over-penalizing partially correct output.",
                supporting_evidence_ids=evidence_ids,
                missing_evidence=["scoring_variant_probe"],
                confidence_before_probe="medium" if evidence_ids else "low",
            )
        )
    if report.experiment_summary is not None and report.experiment_summary.failed_trial_count > 0:
        hypotheses.append(
            DebugHypothesis(
                hypothesis_id="h-model-stability",
                category="model_stability",
                claim="Locked source-model reruns may reveal unstable omission of required details.",
                supporting_evidence_ids=evidence_ids,
                missing_evidence=["stability_rerun_probe"],
                confidence_before_probe="low",
            )
        )
    if any(marker in text for marker in ("golden", "reference", "answer", "expected", "output")):
        hypotheses.append(
            DebugHypothesis(
                hypothesis_id="h-golden-answer-ambiguity",
                category="golden_answer_ambiguity",
                claim="The reference answer may be narrower than acceptable semantic equivalents.",
                supporting_evidence_ids=evidence_ids,
                missing_evidence=["golden_equivalence_probe"],
                confidence_before_probe="low",
            )
        )
    return hypotheses


def _not_run_probe_result(*, job_id: str, plan: DebugProbePlan) -> DebugProbeRunResult:
    return DebugProbeRunResult(
        probe_id=plan.probe_id,
        hypothesis_id=plan.hypothesis_id,
        iteration=plan.iteration,
        status="not_run",
        source_job_id=job_id,
        model_runner_config_snapshot=(
            {"model_runner_config_ref": "locked_source"}
            if intervention_requires_locked_model_runner(plan.intervention_type)
            else {}
        ),
    )


def _probe_results_for_plans(
    *,
    repository: DebugJobRepository,
    job_service: DebugJobService,
    job_id: str,
    probe_plans: list[DebugProbePlan],
    submit_controlled_probes: bool,
) -> list[DebugProbeRunResult]:
    previous_results = _previous_hypothesis_probe_results(repository=repository, job_id=job_id)
    if not submit_controlled_probes:
        return [
            _existing_or_not_run_probe_result(
                repository=repository,
                job_id=job_id,
                plan=plan,
                previous_results=previous_results,
            )
            for plan in probe_plans
        ]
    job = repository.get_job(job_id)
    if job is None:
        return [
            _failed_probe_result(job_id=job_id, plan=plan, error_message="source job not found")
            for plan in probe_plans
        ]
    source_case = repository.get_case(job.case_id)
    if source_case is None:
        return [
            _failed_probe_result(job_id=job_id, plan=plan, error_message="source case not found")
            for plan in probe_plans
        ]
    agent_model_config = job_service.agent_model_config_for_artifact_group(job.artifact_group_id)
    ark_settings = _controlled_probe_ark_settings()
    source_evidence = repository.list_evidence(job_id)
    results: list[DebugProbeRunResult] = []
    for plan in probe_plans:
        existing = _existing_or_not_run_probe_result(
            repository=repository,
            job_id=job_id,
            plan=plan,
            previous_results=previous_results,
        )
        if not intervention_requires_locked_model_runner(plan.intervention_type):
            results.append(
                run_non_runner_probe(
                    source_job_id=job_id,
                    source_case=source_case,
                    plan=plan,
                    source_evidence=source_evidence,
                )
            )
            continue
        if existing.probe_job_id:
            results.append(existing)
            continue
        try:
            draft = build_controlled_probe_draft(
                source_case=source_case,
                source_job_id=job_id,
                plan=plan,
                agent_model_config=agent_model_config,
                ark_settings=ark_settings,
            )
            submitted = submit_controlled_probe_job(
                repository=repository,
                job_service=job_service,
                draft=draft,
                artifact_group_id=job.artifact_group_id,
            )
            results.append(submitted.probe_result)
        except Exception as exc:
            results.append(_failed_probe_result(job_id=job_id, plan=plan, error_message=str(exc)))
    return results


def _previous_hypothesis_probe_results(
    *,
    repository: DebugJobRepository,
    job_id: str,
) -> dict[str, DebugProbeRunResult]:
    stage = next(
        (
            item
            for item in reversed(repository.list_debug_run_stages(job_id))
            if item.stage == "hypothesis"
        ),
        None,
    )
    if stage is None:
        return {}
    payload = stage.output.get("hypothesis_closure")
    if not isinstance(payload, dict):
        return {}
    raw_results = payload.get("probe_results")
    if not isinstance(raw_results, list):
        return {}
    results: dict[str, DebugProbeRunResult] = {}
    for item in raw_results:
        if not isinstance(item, dict):
            continue
        try:
            result = DebugProbeRunResult.model_validate(item)
        except Exception:
            continue
        results[result.probe_id] = result
    return results


def _existing_or_not_run_probe_result(
    *,
    repository: DebugJobRepository,
    job_id: str,
    plan: DebugProbePlan,
    previous_results: dict[str, DebugProbeRunResult],
) -> DebugProbeRunResult:
    previous = previous_results.get(plan.probe_id)
    if previous is None:
        return _not_run_probe_result(job_id=job_id, plan=plan)
    if not previous.probe_job_id:
        return previous.model_copy(update={"iteration": plan.iteration})
    job = repository.get_job(previous.probe_job_id)
    if job is None:
        return previous.model_copy(
            update={
                "status": "failed",
                "error_message": f"probe job not found: {previous.probe_job_id}",
            }
        )
    evidence_ids = repository.list_evidence_ids(job.job_id)
    if job.status == "completed" and evidence_ids:
        return previous.model_copy(
            update={
                "status": "completed",
                "evidence_ids": evidence_ids,
                "error_message": "",
            }
        )
    if job.status == "completed":
        return previous.model_copy(
            update={
                "status": "inconclusive",
                "evidence_ids": [],
                "error_message": "probe job completed without evidence",
            }
        )
    if job.status == "failed":
        return previous.model_copy(
            update={
                "status": "failed",
                "evidence_ids": evidence_ids,
                "error_message": job.error_message or "probe job failed",
            }
        )
    if job.status == "running":
        return previous.model_copy(update={"status": "running", "evidence_ids": evidence_ids})
    return previous.model_copy(update={"status": "not_run", "evidence_ids": evidence_ids})


def _failed_probe_result(
    *,
    job_id: str,
    plan: DebugProbePlan,
    error_message: str,
) -> DebugProbeRunResult:
    return DebugProbeRunResult(
        probe_id=plan.probe_id,
        hypothesis_id=plan.hypothesis_id,
        iteration=plan.iteration,
        status="failed",
        source_job_id=job_id,
        error_message=error_message,
    )


def _probe_error_message(
    *,
    probe_results: list[DebugProbeRunResult],
    plan: DebugProbePlan,
) -> str:
    result = next((item for item in probe_results if item.probe_id == plan.probe_id), None)
    if result is not None and result.error_message:
        return result.error_message
    return "controlled probe not executed yet"


def _causal_comparisons_for_probe_results(
    *,
    repository: DebugJobRepository,
    probe_plans: list[DebugProbePlan],
    probe_results: list[DebugProbeRunResult],
    baseline_success_rate: float,
) -> list[CausalComparisonResult]:
    return [
        compare_probe_outcome(
            plan=plan,
            baseline_success_rate=baseline_success_rate,
            intervention_success_rate=_probe_success_rate(
                repository=repository,
                result=_probe_result_for_plan(probe_results=probe_results, plan=plan),
                fallback=baseline_success_rate,
            ),
            evidence_ids=_probe_evidence_ids(
                result=_probe_result_for_plan(probe_results=probe_results, plan=plan)
            ),
            error_message=_causal_probe_error_message(
                result=_probe_result_for_plan(probe_results=probe_results, plan=plan),
                plan=plan,
            ),
        )
        for plan in probe_plans
    ]


def _probe_result_for_plan(
    *,
    probe_results: list[DebugProbeRunResult],
    plan: DebugProbePlan,
) -> DebugProbeRunResult | None:
    return next((item for item in probe_results if item.probe_id == plan.probe_id), None)


def _probe_success_rate(
    *,
    repository: DebugJobRepository,
    result: DebugProbeRunResult | None,
    fallback: float,
) -> float:
    if result is not None and result.observed_success_rate is not None:
        return result.observed_success_rate
    if result is None or result.status != "completed" or not result.probe_job_id:
        return fallback
    evidence = repository.list_evidence(result.probe_job_id)
    if not evidence:
        return fallback
    success_count = sum(1 for item in evidence if item.judge.score > 0)
    return success_count / len(evidence)


def _probe_evidence_ids(*, result: DebugProbeRunResult | None) -> list[str]:
    return list(result.evidence_ids) if result is not None else []


def _causal_probe_error_message(
    *,
    result: DebugProbeRunResult | None,
    plan: DebugProbePlan,
) -> str:
    if result is None:
        return "controlled probe not executed yet"
    if result.error_message:
        return result.error_message
    if result.status == "completed" and result.evidence_ids:
        return ""
    if result.status == "running":
        return "controlled probe still running"
    if result.status == "not_run" and result.probe_job_id:
        return "controlled probe queued but not executed yet"
    if result.status == "not_run" and intervention_requires_locked_model_runner(
        plan.intervention_type
    ):
        return "controlled probe not executed yet"
    return ""


def _controlled_probe_ark_settings() -> ArkSettings:
    try:
        return ArkSettings.from_env()
    except RuntimeError:
        return ArkSettings(
            api_key="",
            video_model_id="locked_source",
            video_mode="high",
            video_disable_thinking=True,
            seed2_pro_model_id="seedpro",
            seed2_lite_model_id="lite",
        )


def _report_success_rate(report: DebugReport) -> float:
    if report.experiment_summary is None:
        return 0.0
    return report.experiment_summary.success_rate


def _report_evidence_ids(report: DebugReport) -> list[str]:
    if report.experiment_summary is None:
        return []
    return list(report.experiment_summary.evidence_ids)


def _verified_root_causes(comparisons: list[CausalComparisonResult]) -> list[dict[str, str]]:
    return [
        {
            "hypothesis_id": comparison.hypothesis_id,
            "probe_id": comparison.probe_id,
            "summary": comparison.evidence_summary,
        }
        for comparison in comparisons
        if comparison.verdict == "supported"
    ]


def _unverified_hypotheses(hypotheses: list[DebugHypothesis]) -> list[dict[str, str]]:
    return [
        {
            "hypothesis_id": hypothesis.hypothesis_id,
            "status": hypothesis.status,
            "summary": hypothesis.claim,
        }
        for hypothesis in hypotheses
        if hypothesis.status != "supported"
    ]


def _debug_loop_failure_payload(*, job_id: str, error_message: str) -> dict[str, object]:
    return {
        "current_iteration": 1,
        "decision": "failed",
        "next_action": "修复假设闭环异常后重新运行 auto-closure。",
        "stop_reason": error_message,
        "iterations": [
            {
                "iteration": 1,
                "source_job_id": job_id,
                "hypothesis_count": 0,
                "probe_plan_count": 0,
                "probe_result_count": 0,
                "completed_probe_count": 0,
                "pending_probe_count": 0,
                "causal_comparison_count": 0,
                "supported_count": 0,
                "decision": "failed",
                "next_action": "修复假设闭环异常后重新运行 auto-closure。",
                "stop_reason": error_message,
                "probe_results": [],
            }
        ],
    }


def _debug_loop_payload(
    *,
    job_id: str,
    payload: HypothesisClosurePayload,
    verified_root_causes: list[dict[str, str]],
    unverified_hypotheses: list[dict[str, str]],
    loop_policy: DebugLoopPolicy,
) -> dict[str, object]:
    current_iteration_value = current_iteration(payload)
    iteration_values = sorted(
        {
            1,
            *[item.iteration for item in payload.hypotheses],
            *[item.iteration for item in payload.probe_plans],
            *[item.iteration for item in payload.probe_results],
            *[item.iteration for item in payload.causal_comparisons],
        }
    )
    iterations = [
        _debug_loop_iteration_payload(
            job_id=job_id,
            payload=payload,
            iteration_value=iteration_value,
            current_iteration_value=current_iteration_value,
            verified_root_cause_count=len(verified_root_causes),
            loop_policy=loop_policy,
        )
        for iteration_value in iteration_values
    ]
    latest_iteration = iterations[-1] if iterations else {}
    decision = str(latest_iteration.get("decision", "no_hypothesis"))
    next_action = str(latest_iteration.get("next_action", ""))
    stop_reason = str(latest_iteration.get("stop_reason", ""))
    return {
        "current_iteration": current_iteration_value,
        "decision": decision,
        "next_action": next_action,
        "stop_reason": stop_reason,
        "iterations": iterations,
        "fairness_lock": payload.fairness_lock,
        "loop_budget": loop_budget_payload(loop_policy),
        "verified_root_causes": verified_root_causes,
        "unverified_hypotheses": unverified_hypotheses,
    }


def _debug_loop_iteration_payload(
    *,
    job_id: str,
    payload: HypothesisClosurePayload,
    iteration_value: int,
    current_iteration_value: int,
    verified_root_cause_count: int,
    loop_policy: DebugLoopPolicy,
) -> dict[str, object]:
    hypotheses = [item for item in payload.hypotheses if item.iteration == iteration_value]
    probe_plans = [item for item in payload.probe_plans if item.iteration == iteration_value]
    probe_results = [
        item.model_dump(mode="json")
        for item in payload.probe_results
        if item.iteration == iteration_value
    ]
    causal_comparisons = [
        item.model_dump(mode="json")
        for item in payload.causal_comparisons
        if item.iteration == iteration_value
    ]
    completed_probe_count = sum(
        1 for item in probe_results if str(item.get("status", "")) == "completed"
    )
    pending_probe_count = sum(
        1
        for item in probe_results
        if str(item.get("probe_job_id", "")).strip()
        and str(item.get("status", "")) not in {"completed", "failed", "inconclusive"}
    )
    supported_count = sum(
        1 for item in causal_comparisons if str(item.get("verdict", "")) == "supported"
    )
    decision, next_action, stop_reason = _debug_loop_decision(
        hypothesis_count=len(hypotheses),
        probe_plan_count=len(probe_plans),
        pending_probe_count=pending_probe_count,
        completed_probe_count=completed_probe_count,
        causal_comparison_count=len(causal_comparisons),
        supported_count=supported_count,
        verified_root_cause_count=verified_root_cause_count,
        iteration_value=iteration_value,
        max_loop_iterations=loop_policy.max_iterations,
    )
    if iteration_value < current_iteration_value and decision in {
        "continue_or_handoff",
        "stopped_evidence_exhausted",
    }:
        decision = "escalated_to_next_iteration"
        next_action = f"已升级到第 {iteration_value + 1} 轮补充证据。"
        stop_reason = "本轮没有 supported causal comparison。"
    return {
        "iteration": iteration_value,
        "source_job_id": job_id,
        "hypothesis_count": len(hypotheses),
        "probe_plan_count": len(probe_plans),
        "probe_result_count": len(probe_results),
        "completed_probe_count": completed_probe_count,
        "pending_probe_count": pending_probe_count,
        "causal_comparison_count": len(causal_comparisons),
        "supported_count": supported_count,
        "decision": decision,
        "next_action": next_action,
        "stop_reason": stop_reason,
        "probe_results": probe_results,
        "causal_comparisons": causal_comparisons,
    }


def _debug_loop_decision(
    *,
    hypothesis_count: int,
    probe_plan_count: int,
    pending_probe_count: int,
    completed_probe_count: int,
    causal_comparison_count: int,
    supported_count: int,
    verified_root_cause_count: int,
    iteration_value: int,
    max_loop_iterations: int,
) -> tuple[str, str, str]:
    if pending_probe_count:
        if verified_root_cause_count or supported_count:
            return (
                "waiting_for_probe_completion",
                "已有 supported comparison，但仍需等待 queued runner probe 完成后再收口。",
                "存在未完成的 controlled runner probe。",
            )
        return (
            "waiting_for_probe_completion",
            "等待 queued probe job 完成后回流证据并重新进行因果比较。",
            "",
        )
    if verified_root_cause_count or supported_count:
        return (
            "verified_root_cause_found",
            "查看已验证根因并决定是否同步报告。",
            "存在 supported probe comparison。",
        )
    if probe_plan_count and completed_probe_count == 0:
        return (
            "waiting_for_probe_submission",
            "显式开启 controlled probes 后提交 probe job。",
            "",
        )
    if causal_comparison_count:
        if iteration_value >= max_loop_iterations:
            return (
                "stopped_evidence_exhausted",
                "当前已达到深度探索预算；输出 inconclusive 结论并转人工复核。",
                "达到最大探索轮次后仍没有 supported causal comparison。",
            )
        return (
            "continue_or_handoff",
            "当前没有 verified root cause；继续补充 probe evidence 或转人工复核。",
            "没有 supported causal comparison。",
        )
    if hypothesis_count:
        return (
            "waiting_for_probe_submission",
            "提交受控 probe 以验证候选假设。",
            "",
        )
    return (
        "no_hypothesis",
        "补充失败样本证据后重新生成候选假设。",
        "没有生成候选假设。",
    )


def _save_debug_loop_stage(
    *,
    repository: DebugJobRepository,
    job_id: str,
    debug_loop: dict[str, object],
) -> None:
    decision = str(debug_loop.get("decision", ""))
    status = {
        "failed": "failed",
        "waiting_for_probe_completion": "waiting",
        "waiting_for_probe_submission": "waiting",
        "verified_root_cause_found": "completed",
        "continue_or_handoff": "completed",
        "stopped_evidence_exhausted": "completed",
        "escalated_to_next_iteration": "waiting",
        "no_hypothesis": "skipped",
    }.get(decision, "completed")
    repository.save_debug_run_stage(
        job_id=job_id,
        stage="debug_loop",
        status=status,
        input={"job_id": job_id, "current_iteration": debug_loop.get("current_iteration", 1)},
        output={"debug_loop": debug_loop},
        failure_reason=str(debug_loop.get("stop_reason", "")) if status == "failed" else "",
        retryable=status in {"waiting", "failed"},
    )


async def _run_targeted_probes(
    *,
    repository: DebugJobRepository,
    job_service: DebugJobService,
    job_id: str,
    report: DebugReport,
    actor: str,
    video_clipper: VideoClipper | None,
    execute_jobs: bool = True,
) -> list[dict[str, str]]:
    created_jobs: list[dict[str, str]] = []
    case_job = repository.get_job(job_id)
    if case_job is None:
        return created_jobs
    source_case = repository.get_case(case_job.case_id)
    if source_case is None:
        return created_jobs
    for target_id in _probe_target_ids(report):
        probe_case = _targeted_probe_case(
            repository=repository,
            source_job_id=job_id,
            source_case=source_case,
            target_id=target_id,
            video_clipper=video_clipper,
        )
        repository.save_case(probe_case)
        probe_job = job_service.submit_case_debug(
            probe_case.case_id,
            baseline_trials=1,
            artifact_group_id=case_job.artifact_group_id,
        )
        repository.save_targeted_probe_job(
            source_job_id=job_id,
            source="auto_targeted_probe",
            target_id=target_id,
            planned_steps=_planned_probe_step(target_id),
            probe_job_id=probe_job.job_id,
            actor=actor,
            note="auto-closure targeted probe for failing video segment",
        )
        if execute_jobs:
            await job_service.run_job(probe_job.job_id)
        created_jobs.append(
            _targeted_probe_outcome(
                repository=repository, probe_job_id=probe_job.job_id, target_id=target_id
            )
        )
    return created_jobs


def _targeted_probe_outcome(
    *,
    repository: DebugJobRepository,
    probe_job_id: str,
    target_id: str,
) -> dict[str, str]:
    evidence = repository.list_evidence(probe_job_id)
    if any(item.judge.score > 0 for item in evidence):
        outcome = "corrected_boundary"
        summary = f"Clipped targeted probe cleared {target_id}."
    elif evidence:
        outcome = "confirmed_boundary_failure"
        summary = f"Clipped targeted probe still failed {target_id}."
    else:
        outcome = "inconclusive"
        summary = f"Clipped targeted probe produced no evidence for {target_id}."
    return {
        "probe_job_id": probe_job_id,
        "target_id": target_id,
        "outcome": outcome,
        "summary": summary,
    }


def _targeted_probe_case(
    *,
    repository: DebugJobRepository,
    source_job_id: str,
    source_case: DebugCase,
    target_id: str,
    video_clipper: VideoClipper | None,
) -> DebugCase:
    probe_window = _probe_window_for_target(
        repository=repository, job_id=source_job_id, target_id=target_id
    )
    image_uri = source_case.image_uri
    if video_clipper is not None and probe_window is not None:
        image_uri = video_clipper.create_clip(
            source_uri=source_case.image_uri,
            target_id=target_id,
            start_s=float(probe_window["clip_start_s"]),
            end_s=float(probe_window["clip_end_s"]),
        )
    prompt = _targeted_probe_prompt(
        source_case=source_case, target_id=target_id, probe_window=probe_window
    )
    return source_case.model_copy(
        update={
            "case_id": f"{source_case.case_id}__auto_probe__{_safe_case_fragment(target_id)}",
            "image_uri": image_uri,
            "prompt": prompt,
        }
    )


def _probe_window_for_target(
    *,
    repository: DebugJobRepository,
    job_id: str,
    target_id: str,
) -> dict[str, float | str] | None:
    for evidence in repository.list_evidence(job_id):
        for delta in evidence.judge.deltas:
            if delta.get("target_id") != target_id:
                continue
            metadata = delta.get("metadata", {})
            if not isinstance(metadata, dict):
                continue
            expected_range = _expected_range(metadata)
            actual_value = _actual_value(metadata)
            if expected_range is None and actual_value is None:
                continue
            values = [
                value
                for value in [*(expected_range or ()), actual_value]
                if isinstance(value, int | float)
            ]
            if not values:
                continue
            clip_start_s = max(0.0, min(float(value) for value in values) - 5.0)
            clip_end_s = max(float(value) for value in values) + 5.0
            return {
                "clip_start_s": round(clip_start_s, 1),
                "clip_end_s": round(clip_end_s, 1),
                "field": str(metadata.get("field", "")),
                "expected": _format_expected_range(expected_range),
                "actual": _format_actual_value(actual_value),
            }
    return None


def _expected_range(metadata: dict[object, object]) -> tuple[float, float] | None:
    field = str(metadata.get("field", ""))
    raw_value = metadata.get(f"expected_{field}_range") if field else None
    if isinstance(raw_value, str) and "-" in raw_value:
        left, right = raw_value.split("-", 1)
        try:
            return float(left), float(right)
        except ValueError:
            return None
    return None


def _actual_value(metadata: dict[object, object]) -> float | None:
    field = str(metadata.get("field", ""))
    raw_value = metadata.get(f"actual_{field}") if field else None
    if isinstance(raw_value, int | float):
        return float(raw_value)
    return None


def _format_expected_range(value: tuple[float, float] | None) -> str:
    return f"{value[0]}-{value[1]}" if value is not None else "unknown"


def _format_actual_value(value: float | None) -> str:
    return str(value) if value is not None else "unknown"


def _targeted_probe_prompt(
    *,
    source_case: DebugCase,
    target_id: str,
    probe_window: dict[str, float | str] | None,
) -> str:
    lines = [
        source_case.prompt,
        "",
        f"定向深挖目标：{target_id}",
        "只针对这些失败点重新观察视频，不要重新发散做全量任务；输出仍必须符合原始任务 schema。",
        "参考答案约束：",
        json.dumps(source_case.expected_output, ensure_ascii=False, indent=2),
        "评分规则约束：",
        source_case.scoring_standard,
        "要求：逐条满足参考答案和评分规则；最终只输出原始任务要求的 JSON，不要输出解释文本。",
    ]
    if probe_window is not None:
        field = probe_window["field"]
        lines.extend(
            [
                f"局部视频窗口：{probe_window['clip_start_s']}-{probe_window['clip_end_s']}s。",
                f"上一轮失败点：期望 {field}：{probe_window['expected']}；实际 {field}：{probe_window['actual']}。",
                f"复核重点：判断 {target_id} 是否在期望 {field} 边界完成动作/释放目标物，并按评分规则修正该字段。",
            ]
        )
    return "\n".join(lines)


def _safe_case_fragment(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value).strip("_")


def _local_path_from_file_uri(uri: str) -> Path:
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        return Path(uri)
    if parsed.netloc:
        return Path(f"//{parsed.netloc}{unquote(parsed.path)}")
    path_text = unquote(parsed.path)
    if len(path_text) >= 3 and path_text[0] == "/" and path_text[2] == ":":
        path_text = path_text[1:]
    return Path(path_text)


async def _run_stability_follow_up(
    *,
    repository: DebugJobRepository,
    job_service: DebugJobService,
    job_id: str,
    report: DebugReport,
    actor: str,
    execute_jobs: bool = True,
) -> list[str]:
    summary = report.experiment_summary
    if summary is None or not (0 < summary.success_count < summary.total_trials):
        return []
    source_job = repository.get_job(job_id)
    if source_job is None:
        return []
    follow_up_job = job_service.submit_case_debug(
        source_job.case_id,
        baseline_trials=5,
        artifact_group_id=source_job.artifact_group_id,
    )
    repository.save_strategy_follow_up_job(
        source_job_id=job_id,
        stage="stability_verification",
        planned_steps="stability_verification_probe",
        follow_up_job_id=follow_up_job.job_id,
        actor=actor,
        note=f"auto-closure detected unstable live rerun {summary.success_count}/{summary.total_trials}",
    )
    if execute_jobs:
        await job_service.run_job(follow_up_job.job_id)
    return [follow_up_job.job_id]


async def _run_recommended_action_verifications(
    *,
    repository: DebugJobRepository,
    job_service: DebugJobService,
    job_id: str,
    report: DebugReport,
    actor: str,
    execute_jobs: bool = True,
) -> list[str]:
    source_job = repository.get_job(job_id)
    if source_job is None:
        return []
    source_case = repository.get_case(source_job.case_id)
    if source_case is None:
        return []
    verification_job_ids: list[str] = []
    for action_index, action in enumerate(report.recommended_actions):
        if action.get("priority") not in {"high", "critical"}:
            continue
        verification_case = _verification_case(
            source_case=source_case, action=action, action_index=action_index
        )
        repository.save_case(verification_case)
        verification_job = job_service.submit_case_debug(
            verification_case.case_id,
            baseline_trials=1,
            artifact_group_id=source_job.artifact_group_id,
        )
        repository.save_recommended_action_verification(
            job_id=job_id,
            action_index=action_index,
            verification_job_id=verification_job.job_id,
            actor=actor,
            note=f"auto-closure verification for {action.get('summary', '')}",
        )
        if execute_jobs:
            await job_service.run_job(verification_job.job_id)
        verification_job_ids.append(verification_job.job_id)
    return verification_job_ids


def _verification_case(
    *, source_case: DebugCase, action: dict[str, object], action_index: int
) -> DebugCase:
    return source_case.model_copy(
        update={
            "case_id": f"{source_case.case_id}__auto_verify__{action_index + 1}",
            "prompt": _verification_prompt(source_case=source_case, action=action),
        }
    )


def _verification_prompt(*, source_case: DebugCase, action: dict[str, object]) -> str:
    return "\n".join(
        [
            source_case.prompt,
            "",
            "闭环验证增强约束：",
            f"推荐动作：{action.get('summary', '')}",
            f"推荐动作细节：{action.get('detail', '')}",
            "参考答案约束：",
            json.dumps(source_case.expected_output, ensure_ascii=False, indent=2),
            "评分规则约束：",
            source_case.scoring_standard,
            "要求：逐条满足参考答案和评分规则；输出前自检 task 数量、时间窗、主体动作、关键词和 JSON schema；最终只输出原始任务要求的 JSON。",
        ]
    )


def _writeback_if_possible(
    *,
    repository: DebugJobRepository,
    writeback_client: SpreadsheetWritebackClient | None,
    job_id: str,
    report: DebugReport,
    closure_result: AutoDebugClosureResult,
    report_url: str,
) -> str:
    if writeback_client is None:
        return (
            "skipped_no_client"
            if repository.get_spreadsheet_row_mapping_by_job_id(job_id)
            else "skipped_no_mapping"
        )
    mapping = repository.get_spreadsheet_row_mapping_by_job_id(job_id)
    if mapping is None:
        return "skipped_no_mapping"
    resolved_report_url = report_url or f"local://jobs/{job_id}/report"
    fields = build_report_writeback_fields(report, report_url=resolved_report_url)
    fields.update(build_auto_closure_writeback_fields(closure_result))
    try:
        written_fields = writeback_client.update_row(
            spreadsheet_id=mapping.spreadsheet_id,
            sheet_id=mapping.sheet_id,
            row_id=mapping.row_id,
            fields=fields,
        )
    except Exception as exc:
        repository.save_spreadsheet_writeback_audit(
            job_id=job_id,
            status="failed",
            row_id=mapping.row_id,
            report_url=resolved_report_url,
            fields={},
            error_message=str(exc),
        )
        raise
    repository.save_spreadsheet_writeback_audit(
        job_id=job_id,
        status="succeeded",
        row_id=mapping.row_id,
        report_url=resolved_report_url,
        fields=written_fields or fields,
        error_message="",
    )
    return "succeeded"


def build_auto_closure_writeback_fields(result: AutoDebugClosureResult) -> dict[str, str]:
    evidence_lines = [
        f"定向深挖任务：{_joined_or_none(result.created_targeted_probe_jobs)}",
        f"稳定性跟进任务：{_joined_or_none(result.created_strategy_follow_up_jobs)}",
        f"闭环验证任务：{_joined_or_none(result.created_verification_jobs)}",
    ]
    attribution_lines = [
        f"{candidate['category']}/{candidate['confidence']}：{candidate['summary']}"
        for candidate in result.final_attribution_candidates
    ]
    return {
        "要点备注": _auto_closure_summary_line(result),
        "自动闭环状态": "已自动深挖",
        "自动闭环证据": "\n".join(evidence_lines),
        "原始Badcase与Live复测对比": _comparison_line(result.badcase_live_comparison),
        "最终归因候选": "\n".join(attribution_lines) if attribution_lines else "无",
    }


def _auto_closure_summary_line(result: AutoDebugClosureResult) -> str:
    live_rerun = (
        result.badcase_live_comparison.get("live_rerun", "").replace("Live 复测：", "").rstrip("。")
    )
    targeted_count = len(result.created_targeted_probe_jobs)
    verification_count = len(result.created_verification_jobs)
    if live_rerun:
        return f"自动 debug：Live 复测 {live_rerun}；定向深挖 {targeted_count} 个；闭环验证 {verification_count} 个。"
    return f"自动 debug：定向深挖 {targeted_count} 个；闭环验证 {verification_count} 个。"


def _joined_or_none(values: list[str]) -> str:
    return ", ".join(values) if values else "无"


def _evidence_summaries(
    *, repository: DebugJobRepository, job_ids: list[str]
) -> list[dict[str, object]]:
    summaries: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for job_id in job_ids:
        for evidence in repository.list_evidence(job_id):
            key = (job_id, evidence.evidence_id)
            if key in seen:
                continue
            seen.add(key)
            summaries.append(
                {
                    "job_id": job_id,
                    "evidence_id": evidence.evidence_id,
                    "step_name": evidence.step_name,
                    "trial": str(evidence.trial),
                    "judge_score": str(evidence.judge.score),
                    "delta_reasons": _delta_reasons(evidence.judge.deltas),
                    "raw_output_excerpt": _excerpt(evidence.raw_output, limit=1200),
                    "model_call_error": evidence.model_call_error_message,
                    "response_parse_error": evidence.response_parse_error,
                }
            )
    return summaries


def _delta_reasons(deltas: list[dict[str, object]]) -> list[str]:
    reasons: list[str] = []
    for delta in deltas:
        reason = str(delta.get("reason", ""))
        if reason and reason not in reasons:
            reasons.append(reason)
    return reasons


def _excerpt(value: str, *, limit: int) -> str:
    normalized = value.strip()
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit]}..."


def _comparison_line(comparison: dict[str, str]) -> str:
    if not comparison:
        return "无"
    return "\n".join(
        value
        for value in [
            comparison.get("original_badcase", ""),
            comparison.get("live_rerun", ""),
            f"闭环判断：{comparison.get('decision', '')}" if comparison.get("decision") else "",
        ]
        if value
    )


def _probe_target_ids(report: DebugReport) -> list[str]:
    target_ids: list[str] = []
    for trace in report.root_cause_trace:
        trace_target_ids = trace.get("target_ids", [])
        if not isinstance(trace_target_ids, list):
            continue
        for value in trace_target_ids:
            if (
                isinstance(value, str)
                and value.startswith("video:segment:")
                and value not in target_ids
            ):
                target_ids.append(value)
    return target_ids[:3]


def _planned_probe_step(target_id: str) -> str:
    if target_id.startswith("video:segment:"):
        return "targeted_video_segment_probe"
    return "targeted_probe"


def _final_attribution_candidates(report: DebugReport) -> list[dict[str, str]]:
    summary = report.experiment_summary
    diagnostic_candidate = _diagnostic_attribution_candidate(report)
    if diagnostic_candidate is not None:
        return [diagnostic_candidate]
    if (
        report.root_cause.label == "video_timestamp_boundary_error"
        and summary
        and 0 < summary.success_count < summary.total_trials
    ):
        return [
            {
                "category": "model_instability",
                "confidence": "high",
                "summary": (
                    f"Live 复测通过 {summary.success_count}/{summary.total_trials} 次；"
                    "模型具备解题能力，但时间边界输出不稳定。"
                ),
            }
        ]
    if report.root_cause.label == "video_timestamp_boundary_error":
        return [
            {
                "category": "model_capability_gap",
                "confidence": "medium",
                "summary": "视频时间边界错误在现有证据中持续出现，暂按模型能力或评测资产高难问题处理。",
            }
        ]
    mapped_category = _mapped_attribution_category(
        report.root_cause.label, report.observed_failure.type
    )
    return [
        {
            "category": mapped_category,
            "confidence": report.root_cause.confidence,
            "summary": report.root_cause.evidence_summary,
        }
    ]


def _diagnostic_attribution_candidate(report: DebugReport) -> dict[str, str] | None:
    for diagnostic in report.evaluation_asset_diagnostics:
        if diagnostic.get("status") != "fail":
            continue
        source = diagnostic.get("source", "")
        if source == "prompt":
            return {
                "category": "prompt_issue",
                "confidence": _confidence_from_severity(diagnostic.get("severity", "")),
                "summary": diagnostic.get("summary", "Prompt diagnostic failed."),
            }
        if source in {"scoring_standard", "scoring_ops", "evaluation_asset"}:
            return {
                "category": "scoring_asset_issue",
                "confidence": _confidence_from_severity(diagnostic.get("severity", "")),
                "summary": diagnostic.get("summary", "Scoring asset diagnostic failed."),
            }
    return None


def _mapped_attribution_category(root_label: str, failure_type: str) -> str:
    value = f"{root_label} {failure_type}".lower()
    if "prompt" in value:
        return "prompt_issue"
    if "scoring" in value or "evaluation_asset" in value or "judge" in value:
        return "scoring_asset_issue"
    if "golden" in value or "reference" in value or "answer_key" in value or "标答" in value:
        return "golden_answer_issue"
    if "data" in value or "download" in value or "corrupt" in value or "missing_media" in value:
        return "data_issue"
    if "model_capability" in value or "capability" in value:
        return "model_capability_gap"
    return root_label


def _confidence_from_severity(severity: str) -> str:
    if severity in {"critical", "high"}:
        return "high"
    if severity == "medium":
        return "medium"
    return "low"


def _badcase_live_comparison(
    *,
    repository: DebugJobRepository,
    job_id: str,
    report: DebugReport,
    final_attribution_candidates: list[dict[str, str]],
) -> dict[str, str]:
    job = repository.get_job(job_id)
    case = repository.get_case(job.case_id) if job is not None else None
    original_total = len(case.predictions) if case is not None else 0
    original_success = (
        sum(prediction.score for prediction in case.predictions) if case is not None else 0
    )
    original_avg_score = case.avg_score if case is not None else 0.0
    summary = report.experiment_summary
    live_success = summary.success_count if summary is not None else 0
    live_total = summary.total_trials if summary is not None else 0
    live_rate = round((summary.success_rate if summary is not None else 0.0) * 100)
    decision = (
        final_attribution_candidates[0]["category"]
        if final_attribution_candidates
        else report.root_cause.label
    )
    return {
        "original_badcase": f"原 badcase：{original_success}/{original_total} 通过，avg_score={original_avg_score}。",
        "live_rerun": f"Live 复测：{live_success}/{live_total} 通过，success_rate={live_rate}%。",
        "decision": decision,
    }
