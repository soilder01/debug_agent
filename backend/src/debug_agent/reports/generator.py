from pydantic import BaseModel, Field

from debug_agent.cases.models import DebugCase
from debug_agent.experiments.planner import ExperimentPlan
from debug_agent.experiments.runner import ExperimentEvidence, ExperimentRunResult
from debug_agent.reports.taxonomy import taxonomy_for_task_type


class ObservedFailure(BaseModel):
    type: str
    summary: str
    affected_box_ids: list[int]


class RootCause(BaseModel):
    label: str
    confidence: str
    evidence_summary: str


class ExperimentSummary(BaseModel):
    total_trials: int
    success_count: int
    failed_trial_count: int = 0
    success_rate: float = 0.0
    stability_label: str = "not_run"
    evidence_ids: list[str]
    artifact_ids: list[str] = Field(default_factory=list)
    image_artifact_ids: list[str]
    step_summaries: list[dict[str, object]] = Field(default_factory=list)


class DebugReport(BaseModel):
    job_id: str | None = None
    case_id: str
    status: str
    observed_failure: ObservedFailure
    planned_experiments: list[str]
    experiment_summary: ExperimentSummary | None = None
    root_cause: RootCause
    evidence_citations: list[dict[str, object]] = Field(default_factory=list)
    suggested_sheet_fields: dict[str, str]


def generate_initial_report(
    case: DebugCase,
    plan: ExperimentPlan,
    run_result: ExperimentRunResult | None = None,
    job_id: str | None = None,
) -> DebugReport:
    experiment_summary = None
    if run_result is not None:
        failed_trial_count = run_result.total_trials - run_result.success_count
        experiment_summary = ExperimentSummary(
            total_trials=run_result.total_trials,
            success_count=run_result.success_count,
            failed_trial_count=failed_trial_count,
            success_rate=_success_rate(run_result.success_count, run_result.total_trials),
            stability_label=_stability_label(run_result.success_count, failed_trial_count, run_result.total_trials),
            evidence_ids=[evidence.evidence_id for evidence in run_result.evidence],
            artifact_ids=[
                artifact.artifact_id
                for evidence in run_result.evidence
                for artifact in evidence.artifacts
            ],
            image_artifact_ids=[
                artifact.artifact_id
                for evidence in run_result.evidence
                for artifact in evidence.image_artifacts
            ],
            step_summaries=_build_step_summaries(run_result.evidence),
        )
    observed_failure, root_cause, suggested_sheet_fields = _infer_report_findings(case=case, run_result=run_result)
    return DebugReport(
        job_id=job_id,
        case_id=case.case_id,
        status="needs_human_review",
        observed_failure=observed_failure,
        planned_experiments=[step.name for step in plan.steps],
        experiment_summary=experiment_summary,
        root_cause=root_cause,
        evidence_citations=_build_evidence_citations(run_result),
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


def _build_step_summary(step_name: str, evidence: list[ExperimentEvidence]) -> dict[str, object]:
    total_trials = len(evidence)
    success_count = sum(item.judge.score for item in evidence)
    failed_trial_count = total_trials - success_count
    return {
        "step_name": step_name,
        "total_trials": total_trials,
        "success_count": success_count,
        "failed_trial_count": failed_trial_count,
        "success_rate": _success_rate(success_count, total_trials),
        "delta_reasons": _step_delta_reasons(evidence),
        "target_ids": _step_target_ids(evidence),
        "evidence_ids": [item.evidence_id for item in evidence],
        "artifact_ids": [
            artifact.artifact_id
            for item in evidence
            for artifact in item.artifacts
        ],
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


def _step_target_ids(evidence: list[ExperimentEvidence]) -> list[str]:
    return sorted(
        {
            str(delta["target_id"])
            for item in evidence
            for delta in item.judge.deltas
            if isinstance(delta.get("target_id"), str) and str(delta.get("target_id")).strip()
        }
    )


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
        structured_deltas = _structured_answer_deltas(run_result.evidence)
        if structured_deltas:
            affected_box_ids = _affected_box_ids_from_deltas(structured_deltas)
            target_summary = _target_summary_from_deltas(structured_deltas, affected_box_ids)
            reason_labels = sorted({str(delta.get("reason", "")) for delta in structured_deltas if delta.get("reason")})
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
                        f"Structured judge deltas cite {target_summary} with reasons {reason_summary}; "
                        "compare predicted answers against the scoring standard and golden answer."
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
                        f"Replay success ratio is {run_result.success_count}/{run_result.total_trials}; "
                        "inspect prompt sensitivity and sampling variance."
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
    if case.task_type != "handwriting_ocr" and not case.expected_output and not case.golden_answer.answers:
        return _evaluation_asset_report(
            label="expected_output_issue",
            confidence="high",
            summary="期望输出为空，无法判断 task-native 模型输出是否真正错误。",
            feedback="期望输出为空：请补充 expected_output_json 作为通用任务的评分依据。",
        )
    if run_result is not None and _has_response_parse_error(run_result.evidence) and not _prompt_requests_json(case.prompt):
        return _evaluation_asset_report(
            label="prompt_schema_issue",
            confidence="medium",
            summary="prompt 未明确 JSON 输出格式，且 evidence 中出现解析失败。",
            feedback="prompt 未明确 JSON/schema：请要求模型只输出 {\"answers\":[...]} 结构。",
        )
    return None


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


def _target_summary_from_deltas(deltas: list[dict[str, object]], affected_box_ids: list[int]) -> str:
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


def _artifact_ids_from_run_result(run_result: ExperimentRunResult) -> list[str]:
    artifact_ids = [
        artifact.artifact_id
        for evidence in run_result.evidence
        for artifact in evidence.artifacts
    ]
    if artifact_ids:
        return artifact_ids
    return [
        artifact.artifact_id
        for evidence in run_result.evidence
        for artifact in evidence.image_artifacts
    ]


def _build_evidence_citations(run_result: ExperimentRunResult | None) -> list[dict[str, object]]:
    if run_result is None:
        return []
    citations: list[dict[str, object]] = []
    for item in run_result.evidence:
        artifact_ids = _citation_artifact_ids(item)
        for delta in item.judge.deltas:
            box_id = _box_id_from_delta(delta)
            reason = delta.get("reason", "")
            citations.append(
                {
                    "evidence_id": item.evidence_id,
                    "step_name": item.step_name,
                    "box_id": box_id if isinstance(box_id, int) else None,
                    "reason": str(reason),
                    "artifact_ids": artifact_ids,
                }
            )
        if item.model_call_error_type:
            citations.append(
                {
                    "evidence_id": item.evidence_id,
                    "step_name": item.step_name,
                    "box_id": None,
                    "reason": item.model_call_error_type,
                    "artifact_ids": artifact_ids,
                }
            )
        if item.response_parse_error:
            citations.append(
                {
                    "evidence_id": item.evidence_id,
                    "step_name": item.step_name,
                    "box_id": None,
                    "reason": "response_parse_error",
                    "artifact_ids": artifact_ids,
                }
            )
    return citations


def _citation_artifact_ids(item: ExperimentEvidence) -> list[str]:
    artifact_ids = [artifact.artifact_id for artifact in item.artifacts]
    if artifact_ids:
        return artifact_ids
    return [artifact.artifact_id for artifact in item.image_artifacts]


def _box_id_from_delta(delta: dict[str, object]) -> int | None:
    legacy_box_id = delta.get("box_id")
    if isinstance(legacy_box_id, int):
        return legacy_box_id
    metadata = delta.get("metadata")
    if isinstance(metadata, dict):
        metadata_box_id = metadata.get("box_id")
        if isinstance(metadata_box_id, int):
            return metadata_box_id
    target_id = delta.get("target_id")
    if isinstance(target_id, str) and target_id.startswith("box:"):
        box_id_text = target_id.removeprefix("box:")
        if box_id_text.isdigit():
            return int(box_id_text)
    return None
