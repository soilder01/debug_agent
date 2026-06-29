from __future__ import annotations

from debug_agent.experiments.runner import ExperimentEvidence, ExperimentRunResult


def with_citations(
    items: dict[str, str] | list[dict[str, str]],
    citation_context: dict[str, str],
) -> list[dict[str, str]]:
    normalized_items = [items] if isinstance(items, dict) else items
    return [{**item, **citation_context} for item in normalized_items]


def _artifact_ids_from_run_result(run_result: ExperimentRunResult) -> list[str]:
    artifact_ids = [
        artifact.artifact_id for evidence in run_result.evidence for artifact in evidence.artifacts
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


def _citation_context(
    *,
    run_result: ExperimentRunResult | None,
    root_cause_trace: list[dict[str, object]],
) -> dict[str, str]:
    evidence_ids = (
        [evidence.evidence_id for evidence in run_result.evidence] if run_result is not None else []
    )
    trace_refs = [
        f"{trace.get('step_name')}:{trace.get('variant')}"
        for trace in root_cause_trace
        if isinstance(trace.get("step_name"), str) and isinstance(trace.get("variant"), str)
    ]
    return {
        "evidence_ids": ", ".join(evidence_ids),
        "artifact_ids": ", ".join(_artifact_ids_from_run_result(run_result))
        if run_result is not None
        else "",
        "trace_refs": ", ".join(trace_refs),
    }


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
