import subprocess
from pathlib import Path
from typing import Protocol
from urllib.parse import unquote, urlparse

from pydantic import BaseModel, Field

from debug_agent.cases.models import DebugCase
from debug_agent.jobs.service import DebugJobService
from debug_agent.reports.generator import DebugReport
from debug_agent.reports.job_report import build_report_for_job
from debug_agent.spreadsheets.writeback import SpreadsheetWritebackClient, build_report_writeback_fields
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
) -> AutoDebugClosureResult:
    report = build_report_for_job(repository, job_id)
    if report is None:
        raise KeyError(f"Debug report not found for job: {job_id}")
    result = AutoDebugClosureResult(source_job_id=job_id)
    targeted_probe_results = await _run_targeted_probes(
        repository=repository,
        job_service=job_service,
        job_id=job_id,
        report=report,
        actor=actor,
        video_clipper=video_clipper,
    )
    result.created_targeted_probe_jobs = [item["probe_job_id"] for item in targeted_probe_results]
    result.targeted_probe_outcomes = targeted_probe_results
    result.created_strategy_follow_up_jobs = await _run_stability_follow_up(
        repository=repository,
        job_service=job_service,
        job_id=job_id,
        report=report,
        actor=actor,
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


async def _run_targeted_probes(
    *,
    repository: DebugJobRepository,
    job_service: DebugJobService,
    job_id: str,
    report: DebugReport,
    actor: str,
    video_clipper: VideoClipper | None,
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
        probe_job = job_service.submit_case_debug(probe_case.case_id, baseline_trials=1)
        repository.save_targeted_probe_job(
            source_job_id=job_id,
            source="auto_targeted_probe",
            target_id=target_id,
            planned_steps=_planned_probe_step(target_id),
            probe_job_id=probe_job.job_id,
            actor=actor,
            note="auto-closure targeted probe for failing video segment",
        )
        await job_service.run_job(probe_job.job_id)
        created_jobs.append(_targeted_probe_outcome(repository=repository, probe_job_id=probe_job.job_id, target_id=target_id))
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
    probe_window = _probe_window_for_target(repository=repository, job_id=source_job_id, target_id=target_id)
    image_uri = source_case.image_uri
    if video_clipper is not None and probe_window is not None:
        image_uri = video_clipper.create_clip(
            source_uri=source_case.image_uri,
            target_id=target_id,
            start_s=float(probe_window["clip_start_s"]),
            end_s=float(probe_window["clip_end_s"]),
        )
    prompt = _targeted_probe_prompt(source_case=source_case, target_id=target_id, probe_window=probe_window)
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
            values = [value for value in [*(expected_range or ()), actual_value] if isinstance(value, int | float)]
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
        f"Targeted probe for {target_id}:",
        "Only inspect the provided local time window and explain the boundary decision before emitting JSON.",
        "Return the same video_action_segments schema as the original task.",
    ]
    if probe_window is not None:
        field = probe_window["field"]
        lines.extend(
            [
                f"Probe clip window: {probe_window['clip_start_s']}-{probe_window['clip_end_s']}s.",
                f"Previous failure: expected {field} {probe_window['expected']}, actual {field} {probe_window['actual']}.",
                f"Focus on whether {target_id} leaves/releases the target object at the expected {field} boundary.",
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
) -> list[str]:
    summary = report.experiment_summary
    if summary is None or not (0 < summary.success_count < summary.total_trials):
        return []
    source_job = repository.get_job(job_id)
    if source_job is None:
        return []
    follow_up_job = job_service.submit_case_debug(source_job.case_id, baseline_trials=5)
    repository.save_strategy_follow_up_job(
        source_job_id=job_id,
        stage="stability_verification",
        planned_steps="stability_verification_probe",
        follow_up_job_id=follow_up_job.job_id,
        actor=actor,
        note=f"auto-closure detected unstable live rerun {summary.success_count}/{summary.total_trials}",
    )
    await job_service.run_job(follow_up_job.job_id)
    return [follow_up_job.job_id]


async def _run_recommended_action_verifications(
    *,
    repository: DebugJobRepository,
    job_service: DebugJobService,
    job_id: str,
    report: DebugReport,
    actor: str,
) -> list[str]:
    source_job = repository.get_job(job_id)
    if source_job is None:
        return []
    verification_job_ids: list[str] = []
    for action_index, action in enumerate(report.recommended_actions):
        if action.get("priority") not in {"high", "critical"}:
            continue
        verification_job = job_service.submit_case_debug(source_job.case_id, baseline_trials=1)
        repository.save_recommended_action_verification(
            job_id=job_id,
            action_index=action_index,
            verification_job_id=verification_job.job_id,
            actor=actor,
            note=f"auto-closure verification for {action.get('summary', '')}",
        )
        await job_service.run_job(verification_job.job_id)
        verification_job_ids.append(verification_job.job_id)
    return verification_job_ids


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
        return "skipped_no_client" if repository.get_spreadsheet_row_mapping_by_job_id(job_id) else "skipped_no_mapping"
    mapping = repository.get_spreadsheet_row_mapping_by_job_id(job_id)
    if mapping is None:
        return "skipped_no_mapping"
    resolved_report_url = report_url or f"local://jobs/{job_id}/report"
    fields = build_report_writeback_fields(report, report_url=resolved_report_url)
    fields.update(_auto_closure_writeback_fields(closure_result))
    try:
        writeback_client.update_row(
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
        fields=fields,
        error_message="",
    )
    return "succeeded"


def _auto_closure_writeback_fields(result: AutoDebugClosureResult) -> dict[str, str]:
    evidence_lines = [
        f"Targeted Probe：{_joined_or_none(result.created_targeted_probe_jobs)}",
        f"稳定性 Follow-up：{_joined_or_none(result.created_strategy_follow_up_jobs)}",
        f"Verification Job：{_joined_or_none(result.created_verification_jobs)}",
    ]
    attribution_lines = [
        f"{candidate['category']}/{candidate['confidence']}：{candidate['summary']}"
        for candidate in result.final_attribution_candidates
    ]
    return {
        "自动闭环状态": "已自动深挖",
        "自动闭环证据": "\n".join(evidence_lines),
        "原始Badcase与Live复测对比": _comparison_line(result.badcase_live_comparison),
        "最终归因候选": "\n".join(attribution_lines) if attribution_lines else "无",
    }


def _joined_or_none(values: list[str]) -> str:
    return ", ".join(values) if values else "无"


def _evidence_summaries(*, repository: DebugJobRepository, job_ids: list[str]) -> list[dict[str, object]]:
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
            if isinstance(value, str) and value.startswith("video:segment:") and value not in target_ids:
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
    if report.root_cause.label == "video_timestamp_boundary_error" and summary and 0 < summary.success_count < summary.total_trials:
        return [
            {
                "category": "model_instability",
                "confidence": "high",
                "summary": (
                    f"Live rerun passed {summary.success_count}/{summary.total_trials} trials; "
                    "the model can solve the case but is not stable on temporal boundaries."
                ),
            }
        ]
    if report.root_cause.label == "video_timestamp_boundary_error":
        return [
            {
                "category": "model_capability_gap",
                "confidence": "medium",
                "summary": "Video timestamp boundary failures persisted across available evidence.",
            }
        ]
    mapped_category = _mapped_attribution_category(report.root_cause.label, report.observed_failure.type)
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
    original_success = sum(prediction.score for prediction in case.predictions) if case is not None else 0
    original_avg_score = case.avg_score if case is not None else 0.0
    summary = report.experiment_summary
    live_success = summary.success_count if summary is not None else 0
    live_total = summary.total_trials if summary is not None else 0
    live_rate = round((summary.success_rate if summary is not None else 0.0) * 100)
    decision = final_attribution_candidates[0]["category"] if final_attribution_candidates else report.root_cause.label
    return {
        "original_badcase": f"原 badcase：{original_success}/{original_total} 通过，avg_score={original_avg_score}。",
        "live_rerun": f"Live 复测：{live_success}/{live_total} 通过，success_rate={live_rate}%。",
        "decision": decision,
    }
