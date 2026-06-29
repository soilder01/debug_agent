from typing import Literal

from debug_agent.cases.models import DebugCase
from debug_agent.experiments.planner import (
    plan_experiments,
    plan_strategy_escalation_follow_up_experiments,
    plan_targeted_escalation_follow_up_experiments,
)
from debug_agent.experiments.runner import ExperimentRunResult
from debug_agent.reports.action_queue import build_action_queue
from debug_agent.reports.generator import AgentTrace, DebugReport, generate_initial_report
from debug_agent.reports.composer import build_product_summary
from debug_agent.reports.run_view import build_debug_run_view
from debug_agent.storage.repository import (
    DebugJobRepository,
    RecommendedActionVerification,
    StrategyFollowUpJob,
    TargetedProbeJob,
)

MAX_TARGETED_PROBE_DEPTH = 3


def build_report_for_job(repository: DebugJobRepository, job_id: str) -> DebugReport | None:
    base_report = _build_base_report_for_job(repository, job_id)
    if base_report is None:
        return None
    _apply_meta_agent_enrichment(repository, job_id, base_report)
    verification_results = build_recommended_action_verification_results(
        repository,
        job_id,
        source_report=base_report,
    )
    report = _build_base_report_for_job(
        repository, job_id, verification_results=verification_results
    )
    if report is None:
        return None
    _apply_meta_agent_enrichment(repository, job_id, report)
    report.strategy_follow_up_results = build_strategy_follow_up_results(repository, job_id)
    report.targeted_probe_results = build_targeted_probe_results(repository, job_id)
    report.supplemental_contexts = _build_supplemental_contexts(repository, job_id)
    report.product_summary = build_product_summary(report=report)
    report.report_document_url = _published_report_document_url(repository, job_id)
    job = repository.get_job(job_id)
    case = repository.get_case(job.case_id) if job is not None else None
    if case is not None:
        report.follow_up_experiments = [
            *report.follow_up_experiments,
            *_build_strategy_escalation_follow_up_experiments(
                case=case,
                strategy_follow_up_results=report.strategy_follow_up_results,
            ),
            *_build_targeted_escalation_follow_up_experiments(
                case=case,
                targeted_probe_results=report.targeted_probe_results,
            ),
        ]
        report.human_handoff_requests = _build_human_handoff_requests(report.follow_up_experiments)
        report.human_handoff_statuses = [
            status.model_dump() for status in repository.list_human_handoff_statuses(job_id)
        ]
        report.final_attributions = _build_final_attributions(report.human_handoff_statuses)
        report.final_attribution_verification_results = (
            _build_final_attribution_verification_results(
                final_attributions=report.final_attributions,
                strategy_follow_up_results=report.strategy_follow_up_results,
            )
        )
        report.final_attribution_recovery_results = _build_final_attribution_recovery_results(
            final_attributions=report.final_attributions,
            strategy_follow_up_results=report.strategy_follow_up_results,
        )
        report.recommended_actions = [
            *report.recommended_actions,
            *_build_final_attribution_recommended_actions(report.final_attributions),
            *_build_final_attribution_verification_recovery_actions(
                report.final_attribution_verification_results
            ),
            *_build_final_attribution_recovery_closure_actions(
                report.final_attribution_recovery_results
            ),
            *_build_final_attribution_reinvestigation_actions(
                report.final_attribution_recovery_results
            ),
        ]
        report.follow_up_experiments = [
            *report.follow_up_experiments,
            *_build_final_attribution_follow_up_experiments(report.final_attributions),
            *_build_final_attribution_verification_recovery_follow_up_experiments(
                report.final_attribution_verification_results
            ),
            *_build_final_attribution_reinvestigation_follow_up_experiments(
                report.final_attribution_recovery_results
            ),
        ]
    report = _merge_recommended_action_statuses(repository, job_id, report)
    report.action_queue = build_action_queue(repository=repository, job_id=job_id, report=report)
    run_view = build_debug_run_view(repository=repository, job_id=job_id, report=report)
    if run_view is not None:
        report.run_view = run_view.model_dump(mode="json")
    return report


def _published_report_document_url(repository: DebugJobRepository, job_id: str) -> str:
    document = repository.get_lark_report_document(job_id)
    if document is None or document.status != "published":
        return ""
    return document.document_url


def _build_supplemental_contexts(
    repository: DebugJobRepository,
    job_id: str,
) -> list[dict[str, object]]:
    contexts: list[dict[str, object]] = []
    for stage in repository.list_debug_run_stages(job_id):
        if stage.stage != "supplemental_context":
            continue
        attachments = stage.input.get("attachments")
        output = stage.output
        contexts.append(
            {
                "text": str(stage.input.get("supplement_text", "")),
                "attachments": attachments if isinstance(attachments, list) else [],
                "actor": str(stage.input.get("actor", "")),
                "message_id": str(output.get("message_id", "")),
                "draft_id": str(output.get("draft_id", "")),
                "attachment_count": int(output.get("attachment_count", 0))
                if isinstance(output.get("attachment_count", 0), int | float)
                else 0,
                "created_at": stage.created_at,
            }
        )
    return contexts


def _apply_meta_agent_enrichment(
    repository: DebugJobRepository, job_id: str, report: DebugReport
) -> None:
    enrichment = _meta_agent_enrichment(repository, job_id)
    if not enrichment:
        return
    report.meta_agent_enrichment = enrichment
    root_cause_summary = enrichment.get("root_cause_summary")
    if isinstance(root_cause_summary, str) and root_cause_summary.strip():
        report.confidence_reasons.append(
            {
                "source": "report_root_cause_agent",
                "level": "medium",
                "summary": root_cause_summary,
            }
        )
    recommended_actions = enrichment.get("recommended_actions")
    if isinstance(recommended_actions, list):
        report.recommended_actions.extend(
            _action_item(item) for item in recommended_actions if isinstance(item, dict)
        )
    confidence_reasons = enrichment.get("confidence_reasons")
    if isinstance(confidence_reasons, list):
        report.confidence_reasons.extend(
            _string_dict(item) for item in confidence_reasons if isinstance(item, dict)
        )
    judge_notes = enrichment.get("judge_comparison_notes")
    if isinstance(judge_notes, list):
        report.judge_comparison_notes.extend(
            _judge_note_item(item) for item in judge_notes if isinstance(item, dict)
        )
    strategy_updates = enrichment.get("strategy_updates")
    if isinstance(strategy_updates, list):
        strategy_items = [
            _strategy_item(item) for item in strategy_updates if isinstance(item, dict)
        ]
        report.debug_strategy.extend(strategy_items)
        report.follow_up_experiments.extend(
            {
                "source": "debug_strategy",
                "stage": item.get("stage", "llm_strategy"),
                "planned_steps": item.get("planned_probe", ""),
                "summary": item.get("objective", ""),
            }
            for item in strategy_items
        )
    agent_traces = enrichment.get("agent_traces")
    if isinstance(agent_traces, list):
        report.agent_traces = _merge_agent_traces(
            report.agent_traces,
            [AgentTrace.model_validate(item) for item in agent_traces if isinstance(item, dict)],
        )


def _merge_agent_traces(
    existing: list[AgentTrace],
    incoming: list[AgentTrace],
) -> list[AgentTrace]:
    merged = list(existing)
    existing_keys = {
        (
            trace.agent_role,
            str(trace.input_summary.get("evidence_id", "")),
            trace.input_sha256,
        )
        for trace in merged
    }
    for trace in incoming:
        key = (
            trace.agent_role,
            str(trace.input_summary.get("evidence_id", "")),
            trace.input_sha256,
        )
        if key in existing_keys:
            continue
        merged.append(trace)
        existing_keys.add(key)
    return merged


def _meta_agent_enrichment(repository: DebugJobRepository, job_id: str) -> dict[str, object]:
    for stage in repository.list_debug_run_stages(job_id):
        if stage.stage != "attribution":
            continue
        enrichment = stage.output.get("meta_agent_enrichment")
        if isinstance(enrichment, dict):
            return enrichment
    return {}


def _strategy_item(item: dict[object, object]) -> dict[str, str]:
    normalized = _string_dict(item)
    normalized.setdefault("stage", "llm_strategy")
    normalized.setdefault("objective", normalized.get("summary", "LLM 生成的深挖策略"))
    normalized.setdefault("trigger", "meta_agent_enrichment")
    normalized.setdefault("planned_probe", normalized.get("planned_steps", ""))
    normalized.setdefault("stop_condition", "新增证据能支持或推翻当前 root cause。")
    normalized.setdefault("escalation", "证据不足时转人工复核或补充 targeted replay。")
    return normalized


def _action_item(item: dict[object, object]) -> dict[str, str]:
    normalized = _string_dict(item)
    normalized.setdefault("category", "meta_agent")
    normalized.setdefault("priority", "medium")
    normalized.setdefault("status", "pending")
    normalized.setdefault("summary", "LLM 生成的建议操作")
    normalized.setdefault("detail", normalized["summary"])
    return normalized


def _judge_note_item(item: dict[object, object]) -> dict[str, str]:
    normalized = _string_dict(item)
    normalized.setdefault("evidence_id", "")
    normalized.setdefault("target_id", "")
    normalized.setdefault("deterministic_reason", "")
    normalized.setdefault("llm_note", normalized.get("summary", "LLM 生成的辅助判分备注"))
    normalized.setdefault("risk", "medium")
    return normalized


def _string_dict(item: dict[object, object]) -> dict[str, str]:
    return {str(key): str(value) for key, value in item.items() if value is not None}


def _build_base_report_for_job(
    repository: DebugJobRepository,
    job_id: str,
    verification_results: list[dict[str, object]] | None = None,
) -> DebugReport | None:
    job = repository.get_job(job_id)
    if job is None:
        return None
    case = repository.get_case(job.case_id)
    if case is None:
        return None
    evidence = repository.list_evidence(job_id)
    plan = plan_experiments(case, baseline_trials=job.baseline_trials or None)
    run_result = ExperimentRunResult(
        case_id=case.case_id,
        total_trials=len(evidence),
        success_count=sum(1 for item in evidence if item.judge.score == 1),
        evidence=evidence,
    )
    return generate_initial_report(
        case=case,
        plan=plan,
        run_result=run_result,
        job_id=job_id,
        verification_results=verification_results,
    )


def build_recommended_action_verification_results(
    repository: DebugJobRepository,
    job_id: str,
    source_report: DebugReport | None = None,
) -> list[dict[str, object]]:
    resolved_source_report = source_report or _build_base_report_for_job(repository, job_id)
    return [
        _recommended_action_verification_result(
            repository=repository,
            job_id=job_id,
            verification=verification,
            source_report=resolved_source_report,
        )
        for verification in repository.list_recommended_action_verifications(job_id)
    ]


def build_strategy_follow_up_results(
    repository: DebugJobRepository, job_id: str
) -> list[dict[str, object]]:
    return [
        _strategy_follow_up_result(repository=repository, follow_up=follow_up)
        for follow_up in repository.list_strategy_follow_up_jobs(job_id)
    ]


def build_targeted_probe_results(
    repository: DebugJobRepository, job_id: str
) -> list[dict[str, object]]:
    return [
        _targeted_probe_result(repository=repository, probe=probe)
        for probe in repository.list_targeted_probe_jobs(job_id)
    ]


def _targeted_probe_result(
    *,
    repository: DebugJobRepository,
    probe: TargetedProbeJob,
) -> dict[str, object]:
    job = repository.get_job(probe.probe_job_id)
    if job is None or job.status != "completed":
        return {
            **probe.model_dump(),
            "outcome": "pending",
            "success_rate": 0.0,
            "summary": "Targeted probe job is not completed yet.",
            "escalation": "",
        }
    evidence = repository.list_evidence(probe.probe_job_id)
    if not evidence:
        return {
            **probe.model_dump(),
            "outcome": "inconclusive",
            "success_rate": 0.0,
            "summary": f"Targeted probe completed without evidence for {probe.target_id}.",
            "escalation": f"Re-run targeted probe with evidence capture enabled for {probe.target_id}.",
        }
    success_rate = sum(1 for item in evidence if item.judge.score == 1) / len(evidence)
    if success_rate >= 1.0:
        return {
            **probe.model_dump(),
            "outcome": "target_cleared",
            "success_rate": success_rate,
            "summary": f"Targeted probe passed for {probe.target_id}; localized failure did not reproduce.",
            "escalation": "",
        }
    return {
        **probe.model_dump(),
        "outcome": "target_still_failing",
        "success_rate": success_rate,
        "summary": f"Targeted probe still failed on {probe.target_id}; escalation is recommended.",
        "escalation": f"Run deeper localized replay or modality-specific probes for {probe.target_id}.",
    }


def _strategy_follow_up_result(
    *,
    repository: DebugJobRepository,
    follow_up: StrategyFollowUpJob,
) -> dict[str, object]:
    job = repository.get_job(follow_up.follow_up_job_id)
    if job is None or job.status != "completed":
        return {
            **follow_up.model_dump(),
            "outcome": "pending",
            "success_rate": 0.0,
            "summary": "Strategy follow-up job is not completed yet.",
            "escalation": "",
        }
    evidence = repository.list_evidence(follow_up.follow_up_job_id)
    success_rate = 0.0
    if evidence:
        success_rate = sum(1 for item in evidence if item.judge.score == 1) / len(evidence)
    if success_rate >= 1.0:
        return {
            **follow_up.model_dump(),
            "outcome": "passed_stop_condition",
            "success_rate": success_rate,
            "summary": "Strategy follow-up job passed all probes; stop condition is likely satisfied.",
            "escalation": "",
        }
    return {
        **follow_up.model_dump(),
        "outcome": "needs_escalation",
        "success_rate": success_rate,
        "summary": "Strategy follow-up job still failed; escalation is recommended.",
        "escalation": _strategy_escalation(follow_up.stage),
    }


def _strategy_escalation(stage: str) -> str:
    if stage == "ablation_expansion":
        return "Run single-modality capability probes before keeping cross-modal attribution."
    if stage == "verification_gate":
        return "Create another verification job after updating the recommended action."
    return "Collect additional targeted replay evidence before finalizing the root cause."


def _build_strategy_escalation_follow_up_experiments(
    *,
    case: DebugCase,
    strategy_follow_up_results: list[dict[str, object]],
) -> list[dict[str, str]]:
    base_step_names = {step.name for step in plan_experiments(case).steps}
    escalation_plan = plan_strategy_escalation_follow_up_experiments(
        case, strategy_follow_up_results
    )
    escalation_steps = [step for step in escalation_plan.steps if step.name not in base_step_names]
    return [
        {
            "source": "strategy_outcome",
            "stage": str(result.get("stage", "unknown")),
            "result": str(result.get("outcome", "unknown")),
            "planned_steps": step.name,
            "summary": (
                f"策略阶段 {result.get('stage')} 的 follow-up job {result.get('follow_up_job_id')} 未满足停止条件，"
                f"已生成升级 probing：{step.name}。"
            ),
        }
        for result, step in zip(
            [
                item
                for item in strategy_follow_up_results
                if item.get("outcome") == "needs_escalation"
            ],
            escalation_steps,
            strict=False,
        )
    ]


def _build_targeted_escalation_follow_up_experiments(
    *,
    case: DebugCase,
    targeted_probe_results: list[dict[str, object]],
) -> list[dict[str, str]]:
    base_step_names = {step.name for step in plan_experiments(case).steps}
    escalation_candidates, guardrails = _targeted_escalation_candidates(targeted_probe_results)
    escalation_plan = plan_targeted_escalation_follow_up_experiments(case, escalation_candidates)
    escalation_steps = [step for step in escalation_plan.steps if step.name not in base_step_names]
    escalation_follow_ups = [
        {
            "source": "targeted_probe_outcome",
            "target_id": str(result.get("target_id", "unknown")),
            "result": str(result.get("outcome", "unknown")),
            "parent_probe_job_id": str(result.get("probe_job_id", "")),
            "planned_steps": step.name,
            "summary": (
                f"Targeted probe job {result.get('probe_job_id')} for {result.get('target_id')} 未满足停止条件，"
                f"已生成升级 probing：{step.name}。"
            ),
        }
        for result, step in zip(
            escalation_candidates,
            escalation_steps,
            strict=False,
        )
    ]
    return [*escalation_follow_ups, *guardrails]


def _targeted_escalation_candidates(
    targeted_probe_results: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    candidates: list[dict[str, object]] = []
    guardrails: list[dict[str, str]] = []
    for chain in _targeted_probe_chains(targeted_probe_results):
        latest = chain[-1]
        if latest.get("outcome") not in {"target_still_failing", "inconclusive"}:
            continue
        target_id = str(latest.get("target_id", "unknown"))
        if len(chain) >= MAX_TARGETED_PROBE_DEPTH:
            guardrails.append(
                {
                    "source": "targeted_probe_guardrail",
                    "target_id": target_id,
                    "result": str(latest.get("outcome", "unknown")),
                    "planned_steps": "",
                    "summary": (
                        f"Targeted probe chain for {target_id} reached max depth {MAX_TARGETED_PROBE_DEPTH}; "
                        "stop automatic escalation and require human review."
                    ),
                    "stop_condition": "max_targeted_probe_depth_reached",
                }
            )
            continue
        candidates.append(latest)
    return candidates, guardrails


def _targeted_probe_chains(
    targeted_probe_results: list[dict[str, object]],
) -> list[list[dict[str, object]]]:
    by_target: dict[str, list[dict[str, object]]] = {}
    for result in targeted_probe_results:
        target_id = str(result.get("target_id", "unknown"))
        by_target.setdefault(target_id, []).append(result)
    return [_order_targeted_probe_chain(items) for items in by_target.values()]


def _order_targeted_probe_chain(items: list[dict[str, object]]) -> list[dict[str, object]]:
    by_parent: dict[str, list[dict[str, object]]] = {}
    for item in items:
        parent = str(item.get("parent_probe_job_id", ""))
        by_parent.setdefault(parent, []).append(item)
    ordered: list[dict[str, object]] = []

    def visit(item: dict[str, object]) -> None:
        ordered.append(item)
        probe_job_id = str(item.get("probe_job_id", ""))
        for child in by_parent.get(probe_job_id, []):
            visit(child)

    for root in by_parent.get("", []):
        visit(root)
    for item in items:
        if item not in ordered:
            visit(item)
    return ordered


def _build_human_handoff_requests(
    follow_up_experiments: list[dict[str, str]],
) -> list[dict[str, str]]:
    return [
        {
            "source": "targeted_probe_guardrail",
            "target_id": follow_up.get("target_id", "unknown"),
            "priority": "high",
            "reason": follow_up.get("stop_condition", "targeted_probe_guardrail"),
            "summary": f"Targeted probe chain for {follow_up.get('target_id', 'unknown')} reached max depth {MAX_TARGETED_PROBE_DEPTH}.",
            "recommended_owner": "human-debugger",
            "next_action": (
                "Review the full targeted probe chain, inspect evidence artifacts, and decide whether to update prompt, "
                "evaluation assets, or model capability attribution."
            ),
        }
        for follow_up in follow_up_experiments
        if follow_up.get("source") == "targeted_probe_guardrail"
    ]


def _build_final_attributions(human_handoff_statuses: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "source": "human_handoff",
            "target_id": status.get("target_id", "unknown"),
            "category": _final_attribution_category(status.get("note", "")),
            "status": status.get("status", "unknown"),
            "actor": status.get("actor", ""),
            "summary": status.get("note", ""),
            "recommended_action": _final_attribution_recommended_action(status.get("note", "")),
        }
        for status in human_handoff_statuses
        if status.get("status") in {"resolved", "wont_fix"} and status.get("note", "").strip()
    ]


def _final_attribution_category(note: str) -> str:
    normalized = note.lower()
    if "prompt" in normalized:
        return "prompt_issue"
    if any(token in normalized for token in ["scoring", "golden", "expected", "evaluation asset"]):
        return "evaluation_asset_issue"
    if "data" in normalized or "sample" in normalized:
        return "data_issue"
    if "model" in normalized or "capability" in normalized:
        return "model_capability_gap"
    return "human_confirmed_root_cause"


def _final_attribution_recommended_action(note: str) -> str:
    category = _final_attribution_category(note)
    if category == "prompt_issue":
        return "Update prompt instructions and rerun verification before assigning model capability blame."
    if category == "evaluation_asset_issue":
        return "Fix evaluation assets and rerun the case before keeping model attribution."
    if category == "data_issue":
        return "Repair or quarantine the sample, then rerun debug verification."
    if category == "model_capability_gap":
        return "Keep model capability attribution and add targeted regression coverage."
    return "Record the confirmed root cause and rerun verification if the case remains business-critical."


def _build_final_attribution_recommended_actions(
    final_attributions: list[dict[str, str]],
) -> list[dict[str, str]]:
    return [
        {
            "category": _recommended_action_category_for_attribution(
                attribution.get("category", "")
            ),
            "priority": "high",
            "status": "pending",
            "summary": f"Apply final attribution fix for {attribution.get('target_id', 'unknown')}.",
            "detail": attribution.get("recommended_action", ""),
        }
        for attribution in final_attributions
        if attribution.get("recommended_action", "").strip()
    ]


def _recommended_action_category_for_attribution(category: str) -> str:
    if category == "prompt_issue":
        return "prompt_patch"
    if category == "evaluation_asset_issue":
        return "evaluation_asset_fix"
    if category == "data_issue":
        return "data_repair"
    if category == "model_capability_gap":
        return "regression_set"
    return "human_confirmed_action"


def _build_final_attribution_verification_recovery_actions(
    final_attribution_verification_results: list[dict[str, object]],
) -> list[dict[str, str]]:
    return [
        {
            "category": "attribution_recovery",
            "priority": "critical" if result.get("result") == "not_resolved" else "high",
            "status": "pending",
            "summary": f"Recover unresolved final attribution verification for {result.get('target_id', 'unknown')}.",
            "detail": (
                f"Final attribution verification job {result.get('verification_job_id', '')} "
                f"returned {result.get('result', 'unknown')}. Re-open the attribution, inspect verification "
                f"evidence, and run {_final_attribution_verification_recovery_step(str(result.get('result', '')))}."
            ),
        }
        for result in final_attribution_verification_results
        if result.get("result") in {"not_resolved", "inconclusive"}
    ]


def _build_final_attribution_recovery_closure_actions(
    final_attribution_recovery_results: list[dict[str, object]],
) -> list[dict[str, str]]:
    return [
        {
            "category": "attribution_closure",
            "priority": "high",
            "status": "pending",
            "summary": f"Close final attribution recovery for {result.get('target_id', 'unknown')}.",
            "detail": (
                f"Recovery job {result.get('recovery_job_id', '')} closed the attribution loop. "
                "Record closure and keep the resolved case in regression monitoring."
            ),
        }
        for result in final_attribution_recovery_results
        if result.get("result") == "closed"
    ]


def _build_final_attribution_reinvestigation_actions(
    final_attribution_recovery_results: list[dict[str, object]],
) -> list[dict[str, str]]:
    return [
        {
            "category": "attribution_reinvestigation",
            "priority": "critical",
            "status": "pending",
            "summary": f"Reinvestigate reopened final attribution recovery for {result.get('target_id', 'unknown')}.",
            "detail": (
                f"Recovery job {result.get('recovery_job_id', '')} returned {result.get('result', 'unknown')}. "
                "Rebuild the root-cause trace and run final_attribution_reinvestigation_probe."
            ),
        }
        for result in final_attribution_recovery_results
        if result.get("result") == "reopen"
    ]


def _build_final_attribution_follow_up_experiments(
    final_attributions: list[dict[str, str]],
) -> list[dict[str, str]]:
    return [
        {
            "source": "final_attribution",
            "target_id": attribution.get("target_id", "unknown"),
            "category": attribution.get("category", "unknown"),
            "planned_steps": _final_attribution_verification_step(attribution.get("category", "")),
            "summary": (
                f"Final attribution for {attribution.get('target_id', 'unknown')} is "
                f"{attribution.get('category', 'unknown')}; run "
                f"{_final_attribution_verification_step(attribution.get('category', ''))} "
                "to verify the recommended fix."
            ),
        }
        for attribution in final_attributions
    ]


def _build_final_attribution_verification_recovery_follow_up_experiments(
    final_attribution_verification_results: list[dict[str, object]],
) -> list[dict[str, str]]:
    return [
        {
            "source": "final_attribution_verification_outcome",
            "target_id": str(result.get("target_id", "unknown")),
            "category": str(result.get("category", "unknown")),
            "result": str(result.get("result", "unknown")),
            "verification_job_id": str(result.get("verification_job_id", "")),
            "planned_steps": _final_attribution_verification_recovery_step(
                str(result.get("result", ""))
            ),
            "summary": (
                f"Final attribution verification for {result.get('target_id', 'unknown')} is "
                f"{result.get('result', 'unknown')}; run "
                f"{_final_attribution_verification_recovery_step(str(result.get('result', '')))} "
                "to reassess the root cause before closure."
            ),
        }
        for result in final_attribution_verification_results
        if result.get("result") in {"not_resolved", "inconclusive"}
    ]


def _build_final_attribution_reinvestigation_follow_up_experiments(
    final_attribution_recovery_results: list[dict[str, object]],
) -> list[dict[str, str]]:
    return [
        {
            "source": "final_attribution_recovery_outcome",
            "target_id": str(result.get("target_id", "unknown")),
            "category": str(result.get("category", "unknown")),
            "result": str(result.get("result", "unknown")),
            "recovery_job_id": str(result.get("recovery_job_id", "")),
            "planned_steps": "final_attribution_reinvestigation_probe",
            "summary": (
                f"Final attribution recovery for {result.get('target_id', 'unknown')} is "
                f"{result.get('result', 'unknown')}; run final_attribution_reinvestigation_probe "
                "to rebuild the root-cause trace."
            ),
        }
        for result in final_attribution_recovery_results
        if result.get("result") == "reopen"
    ]


def _final_attribution_verification_recovery_step(result: str) -> str:
    if result == "inconclusive":
        return "final_attribution_evidence_audit"
    return "final_attribution_recovery_probe"


def _final_attribution_verification_step(category: str) -> str:
    if category == "prompt_issue":
        return "final_attribution_prompt_verification"
    if category == "evaluation_asset_issue":
        return "final_attribution_asset_verification"
    if category == "data_issue":
        return "final_attribution_data_verification"
    if category == "model_capability_gap":
        return "final_attribution_regression_set"
    return "final_attribution_human_confirmed_verification"


def _build_final_attribution_verification_results(
    *,
    final_attributions: list[dict[str, str]],
    strategy_follow_up_results: list[dict[str, object]],
) -> list[dict[str, object]]:
    category_by_target = {
        attribution.get("target_id", ""): attribution.get("category", "unknown")
        for attribution in final_attributions
    }
    results: list[dict[str, object]] = []
    for follow_up in strategy_follow_up_results:
        stage = str(follow_up.get("stage", ""))
        if not stage.startswith("final_attribution:"):
            continue
        target_id = stage.removeprefix("final_attribution:")
        result = _final_attribution_verification_result(str(follow_up.get("outcome", "pending")))
        raw_success_rate = follow_up.get("success_rate", 0.0)
        success_rate = raw_success_rate if isinstance(raw_success_rate, int | float) else 0.0
        results.append(
            {
                "source": "final_attribution",
                "target_id": target_id,
                "category": category_by_target.get(target_id, "unknown"),
                "verification_job_id": str(follow_up.get("follow_up_job_id", "")),
                "result": result,
                "success_rate": float(success_rate),
                "summary": _final_attribution_verification_summary(
                    target_id=target_id,
                    result=result,
                ),
            }
        )
    return results


def _build_final_attribution_recovery_results(
    *,
    final_attributions: list[dict[str, str]],
    strategy_follow_up_results: list[dict[str, object]],
) -> list[dict[str, object]]:
    category_by_target = {
        attribution.get("target_id", ""): attribution.get("category", "unknown")
        for attribution in final_attributions
    }
    results: list[dict[str, object]] = []
    for follow_up in strategy_follow_up_results:
        stage = str(follow_up.get("stage", ""))
        if not stage.startswith("final_attribution_recovery:"):
            continue
        target_id = stage.removeprefix("final_attribution_recovery:")
        result = _final_attribution_recovery_result(str(follow_up.get("outcome", "pending")))
        raw_success_rate = follow_up.get("success_rate", 0.0)
        success_rate = raw_success_rate if isinstance(raw_success_rate, int | float) else 0.0
        results.append(
            {
                "source": "final_attribution_recovery",
                "target_id": target_id,
                "category": category_by_target.get(target_id, "unknown"),
                "recovery_job_id": str(follow_up.get("follow_up_job_id", "")),
                "result": result,
                "success_rate": float(success_rate),
                "summary": _final_attribution_recovery_summary(
                    target_id=target_id,
                    result=result,
                ),
            }
        )
    return results


def _final_attribution_verification_result(outcome: str) -> str:
    if outcome == "passed_stop_condition":
        return "resolved"
    if outcome == "needs_escalation":
        return "not_resolved"
    if outcome == "inconclusive":
        return "inconclusive"
    return "pending"


def _final_attribution_recovery_result(outcome: str) -> str:
    if outcome == "passed_stop_condition":
        return "closed"
    if outcome == "needs_escalation":
        return "reopen"
    if outcome == "inconclusive":
        return "inconclusive"
    return "pending"


def _final_attribution_verification_summary(*, target_id: str, result: str) -> str:
    if result == "resolved":
        return f"Final attribution verification for {target_id} resolved the issue."
    if result == "not_resolved":
        return f"Final attribution verification for {target_id} did not resolve the issue."
    if result == "inconclusive":
        return f"Final attribution verification for {target_id} is inconclusive."
    return f"Final attribution verification for {target_id} is still pending."


def _final_attribution_recovery_summary(*, target_id: str, result: str) -> str:
    if result == "closed":
        return f"Final attribution recovery for {target_id} closed the attribution loop."
    if result == "reopen":
        return (
            f"Final attribution recovery for {target_id} still failed; reopen attribution review."
        )
    if result == "inconclusive":
        return f"Final attribution recovery for {target_id} is inconclusive."
    return f"Final attribution recovery for {target_id} is still pending."


def _recommended_action_verification_result(
    *,
    repository: DebugJobRepository,
    job_id: str,
    verification: RecommendedActionVerification,
    source_report: DebugReport | None,
) -> dict[str, object]:
    source_success_rate = _report_success_rate(source_report)
    source_root_cause = source_report.root_cause.label if source_report is not None else ""
    verification_job = repository.get_job(verification.verification_job_id)
    if verification_job is None or verification_job.status != "completed":
        return {
            "job_id": job_id,
            "action_index": verification.action_index,
            "verification_job_id": verification.verification_job_id,
            "result": "pending",
            "source_success_rate": source_success_rate,
            "verification_success_rate": 0.0,
            "source_root_cause": source_root_cause,
            "verification_root_cause": "",
            "summary": "验证任务尚未完成，等待复测结果后再判断推荐操作是否生效。",
        }
    verification_report = _build_base_report_for_job(repository, verification.verification_job_id)
    verification_success_rate = _report_success_rate(verification_report)
    verification_root_cause = (
        verification_report.root_cause.label if verification_report is not None else ""
    )
    result = _classify_verification_result(
        source_success_rate=source_success_rate,
        verification_success_rate=verification_success_rate,
        has_verification_report=verification_report is not None,
    )
    return {
        "job_id": job_id,
        "action_index": verification.action_index,
        "verification_job_id": verification.verification_job_id,
        "result": result,
        "source_success_rate": source_success_rate,
        "verification_success_rate": verification_success_rate,
        "source_root_cause": source_root_cause,
        "verification_root_cause": verification_root_cause,
        "summary": _verification_result_summary(
            result=result,
            source_success_rate=source_success_rate,
            verification_success_rate=verification_success_rate,
        ),
    }


def _report_success_rate(report: DebugReport | None) -> float:
    if report is None or report.experiment_summary is None:
        return 0.0
    return report.experiment_summary.success_rate


def _classify_verification_result(
    *,
    source_success_rate: float,
    verification_success_rate: float,
    has_verification_report: bool,
) -> Literal["resolved", "not_resolved", "regressed", "inconclusive"]:
    if not has_verification_report:
        return "inconclusive"
    if verification_success_rate < source_success_rate:
        return "regressed"
    if verification_success_rate >= 1.0 and verification_success_rate > source_success_rate:
        return "resolved"
    if verification_success_rate <= source_success_rate:
        return "not_resolved"
    return "inconclusive"


def _verification_result_summary(
    *,
    result: str,
    source_success_rate: float,
    verification_success_rate: float,
) -> str:
    source_percent = round(source_success_rate * 100)
    verification_percent = round(verification_success_rate * 100)
    if result == "resolved":
        return f"验证任务通过率 {verification_percent}%，高于原任务 {source_percent}%，推荐操作可能已修复该问题。"
    if result == "regressed":
        return f"验证任务通过率 {verification_percent}%，低于原任务 {source_percent}%，推荐操作可能引入回归。"
    if result == "not_resolved":
        return f"验证任务通过率 {verification_percent}%，未高于原任务 {source_percent}%，推荐操作尚未证明有效。"
    return "验证任务结果不足以判断推荐操作是否生效。"


def _merge_recommended_action_statuses(
    repository: DebugJobRepository,
    job_id: str,
    report: DebugReport,
) -> DebugReport:
    statuses = {
        item.action_index: item.status
        for item in repository.list_recommended_action_statuses(job_id)
    }
    if not statuses or not report.recommended_actions:
        return report
    report.recommended_actions = [
        {**action, "status": statuses.get(index, action.get("status", "pending"))}
        for index, action in enumerate(report.recommended_actions)
    ]
    return report
