from debug_agent.cases.models import DebugCase
from debug_agent.experiments.planner import (
    ExperimentPlan,
)
from debug_agent.experiments.runner import ExperimentEvidence, ExperimentRunResult
from debug_agent.reports.agent_traces import build_model_runner_agent_traces
from debug_agent.reports.followups import (
    _build_debug_strategy,
    _build_follow_up_experiments,
    _build_strategy_follow_up_experiments,
    _build_targeted_probe_follow_up_experiments,
)
from debug_agent.reports.citations import (
    _artifact_ids_from_run_result,
    _box_id_from_delta,
    _build_evidence_citations,
    _citation_context,
    with_citations,
)
from debug_agent.reports.recommended_actions import build_recommended_actions
from debug_agent.reports.root_cause_trace import (
    _build_root_cause_trace,
    _target_ids_from_evidence,
)
from debug_agent.reports.schemas import (
    AgentTrace,
    DebugReport,
    ExperimentSummary,
    ObservedFailure,
    RootCause,
)
from debug_agent.reports.taxonomy import taxonomy_for_task_type

__all__ = [
    "AgentTrace",
    "DebugReport",
    "ExperimentSummary",
    "ObservedFailure",
    "RootCause",
    "generate_initial_report",
]


def generate_initial_report(
    case: DebugCase,
    plan: ExperimentPlan,
    run_result: ExperimentRunResult | None = None,
    job_id: str | None = None,
    verification_results: list[dict[str, object]] | None = None,
) -> DebugReport:
    experiment_summary = None
    if run_result is not None:
        failed_trial_count = run_result.total_trials - run_result.success_count
        experiment_summary = ExperimentSummary(
            total_trials=run_result.total_trials,
            success_count=run_result.success_count,
            failed_trial_count=failed_trial_count,
            success_rate=_success_rate(run_result.success_count, run_result.total_trials),
            stability_label=_stability_label(
                run_result.success_count, failed_trial_count, run_result.total_trials
            ),
            evidence_ids=[evidence.evidence_id for evidence in run_result.evidence],
            artifact_ids=[
                artifact.artifact_id
                for evidence in run_result.evidence
                for artifact in evidence.artifacts
            ],
            artifact_evidence_links=_build_artifact_evidence_links(run_result.evidence),
            image_artifact_ids=[
                artifact.artifact_id
                for evidence in run_result.evidence
                for artifact in evidence.image_artifacts
            ],
            step_summaries=_build_step_summaries(run_result.evidence),
        )
    observed_failure, root_cause, suggested_sheet_fields = _infer_report_findings(
        case=case, run_result=run_result
    )
    root_cause_trace = _build_root_cause_trace(run_result)
    citation_context = _citation_context(run_result=run_result, root_cause_trace=root_cause_trace)
    debug_strategy = _build_debug_strategy(root_cause=root_cause, citation_context=citation_context)
    return DebugReport(
        job_id=job_id,
        case_id=case.case_id,
        status="needs_human_review",
        observed_failure=observed_failure,
        planned_experiments=[step.name for step in plan.steps],
        experiment_summary=experiment_summary,
        root_cause=root_cause,
        evidence_citations=_build_evidence_citations(run_result),
        root_cause_trace=root_cause_trace,
        recommended_actions=build_recommended_actions(
            root_cause, citation_context=citation_context
        ),
        verification_results=verification_results or [],
        evaluation_asset_diagnostics=_build_evaluation_asset_diagnostics(
            case=case,
            run_result=run_result,
            citation_context=citation_context,
        ),
        follow_up_experiments=[
            *_build_follow_up_experiments(case, verification_results or []),
            *_build_strategy_follow_up_experiments(case=case, debug_strategy=debug_strategy),
            *_build_targeted_probe_follow_up_experiments(
                case=case, root_cause_trace=root_cause_trace
            ),
        ],
        confidence_reasons=_build_confidence_reasons(
            run_result=run_result,
            root_cause_trace=root_cause_trace,
            verification_results=verification_results or [],
            citation_context=citation_context,
        ),
        debug_strategy=debug_strategy,
        agent_traces=build_model_runner_agent_traces(run_result),
        suggested_sheet_fields=suggested_sheet_fields,
    )


def _success_rate(success_count: int, total_trials: int) -> float:
    if total_trials <= 0:
        return 0.0
    return success_count / total_trials


def _stability_label(success_count: int, failed_trial_count: int, total_trials: int) -> str:
    if total_trials <= 0:
        return "not_run"
    if success_count == total_trials:
        return "stable_success"
    if failed_trial_count == total_trials:
        return "stable_failure"
    return "unstable"


def _build_step_summaries(evidence: list[ExperimentEvidence]) -> list[dict[str, object]]:
    step_names: list[str] = []
    by_step: dict[str, list[ExperimentEvidence]] = {}
    for item in evidence:
        if item.step_name not in by_step:
            step_names.append(item.step_name)
            by_step[item.step_name] = []
        by_step[item.step_name].append(item)

    return [_build_step_summary(step_name, by_step[step_name]) for step_name in step_names]


def _build_artifact_evidence_links(evidence: list[ExperimentEvidence]) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    for item in evidence:
        for evidence_artifact in item.artifacts:
            links.append(
                {"artifact_id": evidence_artifact.artifact_id, "evidence_id": item.evidence_id}
            )
        for image_artifact in item.image_artifacts:
            links.append(
                {"artifact_id": image_artifact.artifact_id, "evidence_id": item.evidence_id}
            )
    return links


def _build_step_summary(step_name: str, evidence: list[ExperimentEvidence]) -> dict[str, object]:
    total_trials = len(evidence)
    success_count = sum(item.judge.score for item in evidence)
    failed_trial_count = total_trials - success_count
    summary: dict[str, object] = {
        "step_name": step_name,
        "total_trials": total_trials,
        "success_count": success_count,
        "failed_trial_count": failed_trial_count,
        "success_rate": _success_rate(success_count, total_trials),
        "delta_reasons": _step_delta_reasons(evidence),
        "target_ids": _step_target_ids(evidence),
        "evidence_ids": [item.evidence_id for item in evidence],
        "artifact_ids": [artifact.artifact_id for item in evidence for artifact in item.artifacts],
    }
    ablation_variants = _step_request_summary_strings(evidence, "ablation_variant")
    ablation_modalities = _step_request_summary_string_items(evidence, "ablation_modalities")
    if ablation_variants:
        summary["ablation_variants"] = ablation_variants
    if ablation_modalities:
        summary["ablation_modalities"] = ablation_modalities
    return summary


def _build_confidence_reasons(
    *,
    run_result: ExperimentRunResult | None,
    root_cause_trace: list[dict[str, object]],
    verification_results: list[dict[str, object]],
    citation_context: dict[str, str],
) -> list[dict[str, str]]:
    evidence_count = len(run_result.evidence) if run_result is not None else 0
    evidence_level = "high" if evidence_count >= 3 else "medium" if evidence_count > 0 else "low"
    reasons = [
        {
            "source": "evidence_count",
            "level": evidence_level,
            "summary": f"{evidence_count} 条 evidence 支撑当前判断。",
        }
    ]
    trace_variants = {
        str(trace.get("variant"))
        for trace in root_cause_trace
        if isinstance(trace.get("variant"), str) and str(trace.get("variant")).strip()
    }
    if "cross_modal_compare" in trace_variants:
        reasons.append(
            {
                "source": "ablation_pattern",
                "level": "high",
                "summary": "root cause trace 包含 cross_modal_compare 变体，支持跨模态归因。",
            }
        )
    elif trace_variants:
        reasons.append(
            {
                "source": "ablation_pattern",
                "level": "medium",
                "summary": f"root cause trace 包含 {', '.join(sorted(trace_variants))} 变体，支持当前归因。",
            }
        )
    verification_reason = _verification_confidence_reason(verification_results)
    reasons.append(verification_reason)
    return with_citations(reasons, citation_context)


def _verification_confidence_reason(
    verification_results: list[dict[str, object]],
) -> dict[str, str]:
    result_values = {
        str(result.get("result"))
        for result in verification_results
        if isinstance(result.get("result"), str) and str(result.get("result")).strip()
    }
    if "regressed" in result_values:
        return {
            "source": "verification_outcome",
            "level": "low",
            "summary": "验证任务出现 regressed，降低当前推荐操作置信度。",
        }
    if "resolved" in result_values:
        return {
            "source": "verification_outcome",
            "level": "high",
            "summary": "验证任务出现 resolved，提升当前推荐操作置信度。",
        }
    if result_values:
        return {
            "source": "verification_outcome",
            "level": "medium",
            "summary": f"验证任务结果包含 {', '.join(sorted(result_values))}，需要结合证据继续判断。",
        }
    return {
        "source": "verification_outcome",
        "level": "neutral",
        "summary": "尚无验证任务结果参与置信度判断。",
    }


def _step_delta_reasons(evidence: list[ExperimentEvidence]) -> list[str]:
    return sorted(
        {
            str(delta["reason"])
            for item in evidence
            for delta in item.judge.deltas
            if isinstance(delta.get("reason"), str) and str(delta.get("reason")).strip()
        }
    )


def _ablation_alignment_issue(
    run_result: ExperimentRunResult,
) -> tuple[ObservedFailure, RootCause, dict[str, str]] | None:
    passed_variants = _ablation_variants_by_score(run_result.evidence, score=1)
    failed_variants = _ablation_variants_by_score(run_result.evidence, score=0)
    failed_single_variants = [
        variant
        for variant in failed_variants
        if variant in {"image_only", "text_only", "video_only", "audio_only"}
    ]
    if failed_single_variants:
        variant_summary = ", ".join(failed_single_variants)
        modality_summary = ", ".join(_modalities_from_ablation_variants(failed_single_variants))
        conclusion = (
            f"单模态变体 {variant_summary} 失败，优先检查 {modality_summary} 模态感知能力。"
        )
        return (
            ObservedFailure(
                type="single_modality_capability_gap",
                summary=f"单模态 ablation 失败：{conclusion}",
                affected_box_ids=[],
            ),
            RootCause(
                label="single_modality_capability_gap",
                confidence="high",
                evidence_summary=(
                    f"Ablation evidence shows single-modality variant {variant_summary} failed; "
                    f"prioritize {modality_summary} perception and grounding before cross-modal fusion."
                ),
            ),
            {
                "debug1状态": "待人工确认",
                "模型可做对次数": f"{run_result.success_count}次",
                "错误原因": f"单模态能力短板：{conclusion}",
                "Ablation结论": conclusion,
            },
        )
    single_modality_passes = [
        variant
        for variant in passed_variants
        if variant in {"image_only", "text_only", "video_only", "audio_only"}
    ]
    cross_modal_failures = [
        variant
        for variant in failed_variants
        if variant in {"cross_modal_compare", "conflict_grounding_check"}
    ]
    if len(single_modality_passes) < 2 or not cross_modal_failures:
        return None

    passed_summary = ", ".join(single_modality_passes)
    failed_summary = ", ".join(cross_modal_failures)
    conclusion = f"单模态变体 {passed_summary} 可通过，但跨模态变体 {failed_summary} 失败。"
    return (
        ObservedFailure(
            type="cross_modal_alignment_failure",
            summary=f"单模态变体可通过，但跨模态比较失败：{conclusion}",
            affected_box_ids=[],
        ),
        RootCause(
            label="cross_modal_alignment_failure",
            confidence="high",
            evidence_summary=(
                f"Ablation evidence shows single-modality variants {passed_summary} passed, "
                f"while cross-modal variants {failed_summary} failed; prioritize cross-modal alignment and fusion."
            ),
        ),
        {
            "debug1状态": "待人工确认",
            "模型可做对次数": f"{run_result.success_count}次",
            "错误原因": f"跨模态对齐问题：{conclusion}",
            "Ablation结论": conclusion,
        },
    )


def _modalities_from_ablation_variants(variants: list[str]) -> list[str]:
    modality_by_variant = {
        "image_only": "image",
        "text_only": "text",
        "video_only": "video",
        "audio_only": "audio",
    }
    return [modality for variant in variants if (modality := modality_by_variant.get(variant))]


def _ablation_variants_by_score(evidence: list[ExperimentEvidence], *, score: int) -> list[str]:
    variants: list[str] = []
    for item in evidence:
        if item.judge.score != score:
            continue
        variant = item.request_summary.get("ablation_variant")
        if isinstance(variant, str) and variant.strip() and variant not in variants:
            variants.append(variant)
    return variants


def _step_target_ids(evidence: list[ExperimentEvidence]) -> list[str]:
    return sorted({target_id for item in evidence for target_id in _target_ids_from_evidence(item)})


def _step_request_summary_strings(evidence: list[ExperimentEvidence], key: str) -> list[str]:
    values: list[str] = []
    for item in evidence:
        value = item.request_summary.get(key)
        if isinstance(value, str) and value.strip() and value not in values:
            values.append(value)
    return values


def _step_request_summary_string_items(evidence: list[ExperimentEvidence], key: str) -> list[str]:
    values: list[str] = []
    for item in evidence:
        value = item.request_summary.get(key)
        if isinstance(value, str):
            candidates = [value]
        elif isinstance(value, list):
            candidates = [candidate for candidate in value if isinstance(candidate, str)]
        else:
            candidates = []
        for candidate in candidates:
            if candidate.strip() and candidate not in values:
                values.append(candidate)
    return values


def _infer_report_findings(
    *,
    case: DebugCase,
    run_result: ExperimentRunResult | None,
) -> tuple[ObservedFailure, RootCause, dict[str, str]]:
    taxonomy = taxonomy_for_task_type(case.task_type)
    asset_issue = _evaluation_asset_issue(case=case, run_result=run_result)
    if asset_issue is not None:
        return asset_issue
    if run_result is not None:
        runtime_error = _first_runtime_error(run_result.evidence)
        if runtime_error is not None:
            existing_badcase_report = _existing_lark_badcase_report_from_runtime_error(
                case=case,
                run_result=run_result,
                runtime_error=runtime_error,
            )
            if existing_badcase_report is not None:
                return existing_badcase_report
            error_summary = f"{runtime_error.model_call_error_type}: {runtime_error.model_call_error_message}".strip()
            return (
                ObservedFailure(
                    type="model_call_error",
                    summary=f"模型调用失败，未能完成稳定复测：{error_summary}",
                    affected_box_ids=[],
                ),
                RootCause(
                    label="model_call_error",
                    confidence="high",
                    evidence_summary=f"Evidence {runtime_error.evidence_id} reported {error_summary}.",
                ),
                {
                    "debug1状态": "待人工确认",
                    "模型可做对次数": f"{run_result.success_count}次",
                    "错误原因": f"模型调用失败：{error_summary}",
                },
            )
        parse_error = _first_parse_error(run_result.evidence)
        if parse_error is not None:
            return (
                ObservedFailure(
                    type="parse_error",
                    summary="模型输出解析失败，无法形成可评分的结构化结果。",
                    affected_box_ids=[],
                ),
                RootCause(
                    label="parse_error",
                    confidence="high",
                    evidence_summary=f"Evidence {parse_error.evidence_id} 解析失败：{parse_error.response_parse_error}",
                ),
                {
                    "debug1状态": "待人工确认",
                    "模型可做对次数": f"{run_result.success_count}次",
                    "错误原因": f"模型输出解析失败：{parse_error.response_parse_error}",
                },
            )
        ablation_issue = _ablation_alignment_issue(run_result)
        if ablation_issue is not None:
            return ablation_issue
        structured_deltas = _structured_answer_deltas(run_result.evidence)
        if case.task_type == "video_detection":
            video_timestamp_issue = _video_timestamp_issue(
                deltas=structured_deltas,
                success_count=run_result.success_count,
                artifact_ids=_artifact_ids_from_run_result(run_result),
            )
            if video_timestamp_issue is not None:
                return video_timestamp_issue
        if structured_deltas:
            affected_box_ids = _affected_box_ids_from_deltas(structured_deltas)
            target_summary = _target_summary_from_deltas(structured_deltas, affected_box_ids)
            reason_labels = sorted(
                {str(delta.get("reason", "")) for delta in structured_deltas if delta.get("reason")}
            )
            reason_summary = ", ".join(reason_labels)
            sheet_fields = _native_structured_sheet_fields(
                deltas=structured_deltas,
                target_summary=target_summary,
                reason_summary=reason_summary,
                success_count=run_result.success_count,
                artifact_ids=_artifact_ids_from_run_result(run_result),
            )
            return (
                ObservedFailure(
                    type=taxonomy.structured_mismatch_label,
                    summary=f"结构化评分发现 {target_summary} 存在输出差异：{reason_summary}。",
                    affected_box_ids=affected_box_ids,
                ),
                RootCause(
                    label=taxonomy.structured_mismatch_label,
                    confidence="high",
                    evidence_summary=(
                        f"结构化评分差异指向 {target_summary}，原因：{reason_summary}；"
                        "需要对照评分规则和参考答案检查模型输出。"
                    ),
                ),
                sheet_fields,
            )
        if 0 < run_result.success_count < run_result.total_trials:
            return (
                ObservedFailure(
                    type="unstable_prediction",
                    summary="多次复测结果不稳定，模型在相同输入下未保持一致输出。",
                    affected_box_ids=[],
                ),
                RootCause(
                    label="unstable_prediction",
                    confidence="medium",
                    evidence_summary=(
                        f"同一输入复测通过 {run_result.success_count}/{run_result.total_trials} 次；"
                        "需要检查 prompt 敏感性和采样波动。"
                    ),
                ),
                {
                    "debug1状态": "待人工确认",
                    "模型可做对次数": f"{run_result.success_count}次",
                    "错误原因": (
                        f"同一样本复测不稳定：{run_result.success_count}/{run_result.total_trials} 次成功。"
                    ),
                },
            )
    return (
        ObservedFailure(
            type=taxonomy.fallback_failure_type,
            summary=taxonomy.fallback_summary,
            affected_box_ids=[1, 2],
        ),
        RootCause(
            label=taxonomy.fallback_root_cause_label,
            confidence="medium",
            evidence_summary=taxonomy.fallback_evidence_summary,
        ),
        {
            "debug1状态": "待人工确认",
            "模型可做对次数": "0次",
            "错误原因": taxonomy.fallback_sheet_reason,
        },
    )


def _evaluation_asset_issue(
    *,
    case: DebugCase,
    run_result: ExperimentRunResult | None,
) -> tuple[ObservedFailure, RootCause, dict[str, str]] | None:
    if not case.scoring_standard.strip():
        return _evaluation_asset_report(
            label="scoring_standard_issue",
            confidence="high",
            summary="评分标准缺失，当前 0/1 结论缺少可审计的判分依据。",
            feedback="评分标准缺失：请补充 exact match、可接受别字/格式、box_id 对齐等规则。",
        )
    if case.task_type == "handwriting_ocr" and not case.golden_answer.answers:
        return _evaluation_asset_report(
            label="golden_answer_issue",
            confidence="high",
            summary="标答为空，无法判断模型输出是否真正错误。",
            feedback="标答为空：请补充至少一个 box_id 与 student_answer。",
        )
    if (
        case.task_type != "handwriting_ocr"
        and not case.expected_output
        and not case.golden_answer.answers
    ):
        return _evaluation_asset_report(
            label="expected_output_issue",
            confidence="high",
            summary="期望输出为空，无法判断 task-native 模型输出是否真正错误。",
            feedback="期望输出为空：请补充 expected_output_json 作为通用任务的评分依据。",
        )
    if (
        run_result is not None
        and _has_response_parse_error(run_result.evidence)
        and not _prompt_requests_json(case.prompt)
    ):
        return _evaluation_asset_report(
            label="prompt_schema_issue",
            confidence="medium",
            summary="prompt 未明确 JSON 输出格式，且 evidence 中出现解析失败。",
            feedback='prompt 未明确 JSON/schema：请要求模型只输出 {"answers":[...]} 结构。',
        )
    return None


def _existing_lark_badcase_report_from_runtime_error(
    *,
    case: DebugCase,
    run_result: ExperimentRunResult,
    runtime_error: ExperimentEvidence,
) -> tuple[ObservedFailure, RootCause, dict[str, str]] | None:
    if case.human_notes.debug_status != "from_lark_badcase_draft":
        return None
    issue_summary = case.human_notes.root_cause.strip()
    if not issue_summary or not case.predictions or not case.expected_output:
        return None
    error_summary = (
        f"{runtime_error.model_call_error_type}: {runtime_error.model_call_error_message}".strip()
    )
    if _looks_like_video_timestamp_issue(issue_summary):
        return (
            ObservedFailure(
                type="video_timestamp_mismatch",
                summary=f"表格 badcase 已给出视频时间边界偏差：{_clip_summary(issue_summary)}",
                affected_box_ids=[],
            ),
            RootCause(
                label="video_timestamp_boundary_error",
                confidence="medium",
                evidence_summary=(
                    "source replay 模型调用失败，未产生新的复测输出；"
                    f"已基于表格提供的原始模型输出、期望输出和错误现象归因：{issue_summary}"
                ),
            ),
            {
                "debug1状态": "待人工确认",
                "模型可做对次数": f"{run_result.success_count}次",
                "错误原因": f"视频时间边界定位失败：{_clip_summary(issue_summary)}",
                "模型复测诊断": f"source replay 调用失败：{error_summary}",
            },
        )
    return (
        ObservedFailure(
            type="existing_badcase_mismatch",
            summary=f"表格 badcase 已给出模型输出与期望结果不一致：{_clip_summary(issue_summary)}",
            affected_box_ids=[],
        ),
        RootCause(
            label="output_mismatch",
            confidence="medium",
            evidence_summary=(
                "source replay 模型调用失败，未产生新的复测输出；"
                f"已基于表格提供的原始模型输出、期望输出和错误现象归因：{issue_summary}"
            ),
        ),
        {
            "debug1状态": "待人工确认",
            "模型可做对次数": f"{run_result.success_count}次",
            "错误原因": f"模型输出与期望结果不一致：{_clip_summary(issue_summary)}",
            "模型复测诊断": f"source replay 调用失败：{error_summary}",
        },
    )


def _looks_like_video_timestamp_issue(issue_summary: str) -> bool:
    normalized = issue_summary.lower()
    return any(
        token in normalized
        for token in (
            "evalopchecktimestamp",
            "timestamp",
            "start_s",
            "end_s",
            "时间",
            "视频",
            "clip",
        )
    )


def _clip_summary(value: str, limit: int = 240) -> str:
    normalized = " ".join(value.strip().split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3]}..."


def _build_evaluation_asset_diagnostics(
    *,
    case: DebugCase,
    run_result: ExperimentRunResult | None,
    citation_context: dict[str, str],
) -> list[dict[str, str]]:
    return with_citations(
        [
            _prompt_diagnostic(case=case, run_result=run_result),
            _golden_or_expected_output_diagnostic(case),
            _scoring_standard_diagnostic(case),
        ],
        citation_context,
    )


def _prompt_diagnostic(
    *,
    case: DebugCase,
    run_result: ExperimentRunResult | None,
) -> dict[str, str]:
    if (
        run_result is not None
        and _has_response_parse_error(run_result.evidence)
        and not _prompt_requests_json(case.prompt)
    ):
        return {
            "source": "prompt",
            "status": "warn",
            "severity": "medium",
            "summary": "Prompt 未明确要求 JSON/schema，且 evidence 出现解析失败。",
            "recommendation": "要求模型只输出可解析 JSON，并声明关键字段、类型和禁止额外文本。",
        }
    if _prompt_requests_json(case.prompt):
        return {
            "source": "prompt",
            "status": "pass",
            "severity": "info",
            "summary": "Prompt 已要求结构化 JSON 输出。",
            "recommendation": "保持 prompt 中明确的输出 schema、证据引用和约束条件。",
        }
    return {
        "source": "prompt",
        "status": "warn",
        "severity": "medium",
        "summary": "Prompt 未明确要求结构化 JSON 输出。",
        "recommendation": "补充 JSON/schema、关键字段和禁止额外文本等输出约束。",
    }


def _golden_or_expected_output_diagnostic(case: DebugCase) -> dict[str, str]:
    if case.task_type == "handwriting_ocr":
        answer_count = len(case.golden_answer.answers)
        if answer_count == 0:
            return {
                "source": "golden_answer",
                "status": "fail",
                "severity": "high",
                "summary": "标答为空，无法判断模型输出是否真正错误。",
                "recommendation": "补充至少一个 box_id 与 student_answer。",
            }
        return {
            "source": "golden_answer",
            "status": "pass",
            "severity": "info",
            "summary": f"标答包含 {answer_count} 个 answer 项。",
            "recommendation": "继续确保 golden answer 覆盖关键目标、区域或结构化字段。",
        }
    if not case.expected_output and not case.golden_answer.answers:
        return {
            "source": "expected_output",
            "status": "fail",
            "severity": "high",
            "summary": "期望输出为空，无法判断 task-native 模型输出是否真正错误。",
            "recommendation": "补充 expected_output_json 作为通用任务的评分依据。",
        }
    return {
        "source": "expected_output",
        "status": "pass",
        "severity": "info",
        "summary": "通用任务期望输出已配置。",
        "recommendation": "继续确保 expected_output 覆盖关键目标、结构化字段和可接受差异。",
    }


def _scoring_standard_diagnostic(case: DebugCase) -> dict[str, str]:
    if not case.scoring_standard.strip():
        return {
            "source": "scoring_standard",
            "status": "fail",
            "severity": "high",
            "summary": "评分标准缺失，当前 0/1 结论缺少可审计的判分依据。",
            "recommendation": "补充 exact match、可接受别字/格式、box_id 对齐等评分规则。",
        }
    return {
        "source": "scoring_standard",
        "status": "pass",
        "severity": "info",
        "summary": "评分标准已配置。",
        "recommendation": "继续确保评分标准覆盖 exact match、容错规则和结构化字段对齐。",
    }


def _evaluation_asset_report(
    *,
    label: str,
    confidence: str,
    summary: str,
    feedback: str,
) -> tuple[ObservedFailure, RootCause, dict[str, str]]:
    return (
        ObservedFailure(
            type="evaluation_asset_issue",
            summary=summary,
            affected_box_ids=[],
        ),
        RootCause(
            label=label,
            confidence=confidence,
            evidence_summary=feedback,
        ),
        {
            "debug1状态": "待人工确认",
            "模型可做对次数": "0次",
            "错误原因": f"评测资产问题：{feedback}",
        },
    )


def _first_runtime_error(evidence: list[ExperimentEvidence]) -> ExperimentEvidence | None:
    for item in evidence:
        if item.model_call_error_type:
            return item
    return None


def _first_parse_error(evidence: list[ExperimentEvidence]) -> ExperimentEvidence | None:
    for item in evidence:
        if item.response_parse_error:
            return item
    return None


def _has_response_parse_error(evidence: list[ExperimentEvidence]) -> bool:
    return any(item.response_parse_error for item in evidence)


def _prompt_requests_json(prompt: str) -> bool:
    normalized = prompt.lower()
    return "json" in normalized or "schema" in normalized


def _structured_answer_deltas(evidence: list[ExperimentEvidence]) -> list[dict[str, object]]:
    deltas: list[dict[str, object]] = []
    for item in evidence:
        deltas.extend(item.judge.deltas)
    return deltas


def _affected_box_ids_from_deltas(deltas: list[dict[str, object]]) -> list[int]:
    box_ids: set[int] = set()
    for delta in deltas:
        box_id = _box_id_from_delta(delta)
        if box_id is not None:
            box_ids.add(box_id)
    return sorted(box_ids)


def _target_summary_from_deltas(
    deltas: list[dict[str, object]], affected_box_ids: list[int]
) -> str:
    if affected_box_ids:
        return ", ".join(f"box {box_id}" for box_id in affected_box_ids)
    target_ids = sorted(
        {
            str(delta["target_id"])
            for delta in deltas
            if isinstance(delta.get("target_id"), str) and str(delta.get("target_id")).strip()
        }
    )
    return ", ".join(target_ids) if target_ids else "global target"


def _native_structured_sheet_fields(
    *,
    deltas: list[dict[str, object]],
    target_summary: str,
    reason_summary: str,
    success_count: int,
    artifact_ids: list[str],
) -> dict[str, str]:
    fields = {
        "debug1状态": "待人工确认",
        "模型可做对次数": f"{success_count}次",
        "错误原因": f"结构化评分显示 {target_summary} 存在 {reason_summary}。",
        "影响目标": target_summary,
        "结构化差异": _delta_summary(deltas),
    }
    if artifact_ids:
        fields["证据产物"] = ", ".join(artifact_ids)
    return fields


def _video_timestamp_issue(
    *,
    deltas: list[dict[str, object]],
    success_count: int,
    artifact_ids: list[str],
) -> tuple[ObservedFailure, RootCause, dict[str, str]] | None:
    timestamp_deltas = [
        delta for delta in deltas if str(delta.get("reason", "")).startswith("timestamp_")
    ]
    if not timestamp_deltas:
        return None
    target_summary = _target_summary_from_deltas(timestamp_deltas, [])
    delta_lines = [_video_timestamp_delta_line(delta) for delta in timestamp_deltas]
    first_line = delta_lines[0]
    fields = {
        "debug1状态": "待人工确认",
        "模型可做对次数": f"{success_count}次",
        "错误原因": f"视频时间边界定位失败：{first_line}。",
        "影响目标": target_summary,
        "结构化差异": "\n".join(delta_lines),
    }
    if artifact_ids:
        fields["证据产物"] = ", ".join(artifact_ids)
    return (
        ObservedFailure(
            type="video_timestamp_mismatch",
            summary=f"视频时间窗评分发现 {target_summary} 存在时间边界偏差。",
            affected_box_ids=[],
        ),
        RootCause(
            label="video_timestamp_boundary_error",
            confidence="high",
            evidence_summary=f"视频时间边界定位失败：{'; '.join(delta_lines)}。",
        ),
        fields,
    )


def _video_timestamp_delta_line(delta: dict[str, object]) -> str:
    target_id = str(delta.get("target_id") or "video:segment:unknown")
    metadata = delta.get("metadata")
    if not isinstance(metadata, dict):
        return f"{target_id} 时间边界异常"
    field = str(metadata.get("field") or "timestamp")
    expected_range = (
        str(metadata.get("expected_start_s_range") or "")
        if field == "start_s"
        else str(metadata.get("expected_end_s_range") or "")
    )
    actual = metadata.get("actual_end_s") if field == "end_s" else metadata.get("actual_start_s")
    delta_seconds = metadata.get("delta_seconds")
    actual_text = f"{float(actual):.1f}s" if isinstance(actual, int | float) else "未知"
    delta_text = (
        f"{float(delta_seconds):.1f}s" if isinstance(delta_seconds, int | float) else "未知"
    )
    return (
        f"{target_id} {field} 超出期望窗口 {expected_range}s，实际 {actual_text}，偏差 {delta_text}"
    )


def _delta_summary(deltas: list[dict[str, object]]) -> str:
    summaries: list[str] = []
    for delta in deltas:
        target_id = str(delta.get("target_id") or "global target")
        reason = str(delta.get("reason") or "mismatch")
        expected = _sheet_value(delta.get("expected"))
        actual = _sheet_value(delta.get("actual"))
        summaries.append(f"{target_id} {reason}: expected={expected} actual={actual}")
    return "; ".join(summaries)


def _sheet_value(value: object) -> str:
    if value is None:
        return "None"
    return str(value)
