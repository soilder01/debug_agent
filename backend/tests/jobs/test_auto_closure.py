from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
import subprocess
from pathlib import Path

from debug_agent.api import routes
from debug_agent.main import app
from debug_agent.cases.models import DebugCase
from debug_agent.experiments.runner import ExperimentEvidence
from debug_agent.jobs.auto_closure import LocalVideoClipper, _final_attribution_candidates, run_auto_debug_closure
from debug_agent.jobs.service import DebugJobService
from debug_agent.judging.runner import JudgeResult
from debug_agent.reports.generator import DebugReport, ExperimentSummary, ObservedFailure, RootCause
from debug_agent.models.fake import FakeModelAdapter
from debug_agent.storage.database import create_sqlite_memory_session_factory, ensure_database_schema
from debug_agent.storage.repository import DebugJobRepository


@pytest.mark.asyncio
async def test_auto_debug_closure_runs_targeted_probe_stability_followup_and_verifications() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    ensure_database_schema(engine)
    repository = DebugJobRepository(session_factory)
    case = _video_case(f"auto-video-case-{uuid4()}")
    source_job_id = f"auto-video-job-{uuid4()}"
    repository.save_case(case)
    repository.create_job(source_job_id, case.case_id, baseline_trials=1)
    repository.save_evidence(
        job_id=source_job_id,
        case_id=case.case_id,
        evidence=[
            _failed_video_timestamp_evidence(source_job_id),
            *[
                ExperimentEvidence(
                    evidence_id=f"{source_job_id}:pass:{index}",
                    step_name="temporal_schema_check",
                    trial=index,
                    raw_output='{"video_action_segments":[]}',
                    judge=JudgeResult(score=1, reasons=[]),
                )
                for index in range(4)
            ],
        ],
    )
    repository.mark_completed(source_job_id)
    service = DebugJobService(
        repository,
        model_provider=lambda _: FakeModelAdapter(
            outputs=[
                """
                {
                  "video_action_segments": [
                    {
                      "subtask_label": "The right arm picks up the crab clamp and adjusts its position",
                      "start_s": 0.0,
                      "end_s": 23.0
                    }
                  ]
                }
                """
            ]
        ),
    )

    result = await run_auto_debug_closure(
        repository=repository,
        job_service=service,
        job_id=source_job_id,
        actor="auto-debug-agent",
    )

    assert result.source_job_id == source_job_id
    assert result.created_targeted_probe_jobs
    assert result.created_strategy_follow_up_jobs
    assert result.created_verification_jobs
    assert result.evidence_summaries
    source_summary = next(item for item in result.evidence_summaries if item["job_id"] == source_job_id)
    assert source_summary["evidence_id"] == f"{source_job_id}:failed"
    assert "timestamp_end_out_of_range" in source_summary["delta_reasons"]
    assert source_summary["raw_output_excerpt"] == '{"video_action_segments":[]}'
    assert any(item["job_id"] in result.created_targeted_probe_jobs for item in result.evidence_summaries)
    assert any(item["job_id"] in result.created_strategy_follow_up_jobs for item in result.evidence_summaries)
    assert any(item["job_id"] in result.created_verification_jobs for item in result.evidence_summaries)
    assert result.badcase_live_comparison["original_badcase"] == "原 badcase：0/1 通过，avg_score=0.0。"
    assert result.badcase_live_comparison["live_rerun"] == "Live 复测：4/5 通过，success_rate=80%。"
    assert result.badcase_live_comparison["decision"] == "model_instability"
    assert result.final_attribution_candidates[0]["category"] == "model_instability"
    assert result.writeback_status == "skipped_no_mapping"
    assert all(repository.get_job(job_id).status == "completed" for job_id in result.created_targeted_probe_jobs)
    assert all(repository.get_job(job_id).status == "completed" for job_id in result.created_strategy_follow_up_jobs)
    assert all(repository.get_job(job_id).status == "completed" for job_id in result.created_verification_jobs)


@pytest.mark.asyncio
async def test_auto_debug_closure_uses_clipped_targeted_video_probe_case() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    ensure_database_schema(engine)
    repository = DebugJobRepository(session_factory)
    case = _video_case(f"clip-target-video-case-{uuid4()}")
    source_job_id = f"clip-target-video-job-{uuid4()}"
    repository.save_case(case)
    repository.create_job(source_job_id, case.case_id, baseline_trials=1)
    repository.save_evidence(
        job_id=source_job_id,
        case_id=case.case_id,
        evidence=[_failed_video_timestamp_evidence(source_job_id)],
    )
    repository.mark_completed(source_job_id)
    service = DebugJobService(
        repository,
        model_provider=lambda _: FakeModelAdapter(
            outputs=[
                (
                    '{"video_action_segments":[{"subtask_label":"The right arm picks up the crab clamp and adjusts its position",'
                    '"start_s":0.0,"end_s":23.0}]}'
                )
            ]
        ),
    )
    clipper = RecordingVideoClipper()

    result = await run_auto_debug_closure(
        repository=repository,
        job_service=service,
        job_id=source_job_id,
        actor="auto-debug-agent",
        video_clipper=clipper,
    )

    assert result.created_targeted_probe_jobs
    assert result.targeted_probe_outcomes
    assert result.targeted_probe_outcomes[0]["outcome"] == "corrected_boundary"
    assert result.targeted_probe_outcomes[0]["summary"] == "Clipped targeted probe cleared video:segment:1."
    probe_job = repository.get_job(result.created_targeted_probe_jobs[0])
    assert probe_job is not None
    targeted_case = repository.get_case(probe_job.case_id)
    assert targeted_case is not None
    assert targeted_case.case_id != case.case_id
    assert targeted_case.image_uri == "file:///tmp/video_segment_1_probe.mp4"
    assert "Targeted probe for video:segment:1" in targeted_case.prompt
    assert "expected end_s 22.0-24.0" in targeted_case.prompt
    assert "actual end_s 34.0" in targeted_case.prompt
    assert clipper.calls == [
        {
            "source_uri": "file:///tmp/jszn-131.mp4",
            "target_id": "video:segment:1",
            "start_s": 17.0,
            "end_s": 39.0,
        }
    ]


@pytest.mark.asyncio
async def test_auto_debug_closure_writes_chinese_closure_fields_and_audit() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    ensure_database_schema(engine)
    repository = DebugJobRepository(session_factory)
    case = _video_case(f"writeback-auto-video-case-{uuid4()}")
    source_job_id = f"writeback-auto-video-job-{uuid4()}"
    repository.save_case(case)
    repository.create_job(source_job_id, case.case_id, baseline_trials=1)
    repository.save_spreadsheet_row_mapping(
        spreadsheet_id="spreadsheet-1",
        sheet_id="sheet-1",
        row_id="row-131",
        case_id=case.case_id,
        job_id=source_job_id,
    )
    repository.save_evidence(
        job_id=source_job_id,
        case_id=case.case_id,
        evidence=[_failed_video_timestamp_evidence(source_job_id)],
    )
    repository.mark_completed(source_job_id)
    service = DebugJobService(
        repository,
        model_provider=lambda _: FakeModelAdapter(outputs=['{"video_action_segments":[]}']),
    )
    writeback_client = RecordingWritebackClient()

    result = await run_auto_debug_closure(
        repository=repository,
        job_service=service,
        job_id=source_job_id,
        actor="auto-debug-agent",
        writeback_client=writeback_client,
        report_url="https://debug-agent.local/jobs/writeback-auto-video-job/report",
    )

    assert result.writeback_status == "succeeded"
    assert writeback_client.fields["错误原因"].startswith("视频时间边界定位失败")
    assert writeback_client.fields["分析报告链接"] == "https://debug-agent.local/jobs/writeback-auto-video-job/report"
    assert writeback_client.fields["自动闭环状态"] == "已自动深挖"
    assert "Targeted Probe" in writeback_client.fields["自动闭环证据"]
    assert "最终归因候选" in writeback_client.fields
    audit = repository.get_spreadsheet_writeback_audit(source_job_id)
    assert audit is not None
    assert audit.status == "succeeded"
    assert audit.row_id == "row-131"
    assert audit.fields["自动闭环状态"] == "已自动深挖"


def test_final_attribution_candidates_cover_debug_taxonomy() -> None:
    assert _final_attribution_candidates(
        _report(root_label="video_timestamp_boundary_error", success_count=4, total_trials=5)
    )[0]["category"] == "model_instability"
    assert _final_attribution_candidates(
        _report(root_label="video_timestamp_boundary_error", success_count=0, total_trials=5)
    )[0]["category"] == "model_capability_gap"
    assert _final_attribution_candidates(
        _report(
            root_label="prompt_instruction_gap",
            diagnostics=[{"source": "prompt", "status": "fail", "severity": "high", "summary": "prompt 缺少时序边界要求"}],
        )
    )[0]["category"] == "prompt_issue"
    assert _final_attribution_candidates(
        _report(
            root_label="scoring_standard_issue",
            diagnostics=[{"source": "scoring_standard", "status": "fail", "severity": "high", "summary": "check_timestamp 规则过窄"}],
        )
    )[0]["category"] == "scoring_asset_issue"
    assert _final_attribution_candidates(_report(root_label="golden_answer_issue"))[0]["category"] == "golden_answer_issue"
    assert _final_attribution_candidates(_report(root_label="data_issue"))[0]["category"] == "data_issue"


def test_local_video_clipper_creates_ffmpeg_clip(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(args: list[str], check: bool, capture_output: bool, text: bool) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        assert check is True
        assert capture_output is True
        assert text is True
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    clipper = LocalVideoClipper(output_dir=Path("artifacts/targeted-video-probes"))

    uri = clipper.create_clip(
        source_uri="file:///D:/videos/JSZN-131.mp4",
        target_id="video:segment:1",
        start_s=17.0,
        end_s=39.0,
    )

    assert uri.endswith("JSZN-131_video_segment_1_17.0_39.0.mp4")
    assert calls == [
        [
            "ffmpeg",
            "-y",
            "-ss",
            "17.0",
            "-to",
            "39.0",
            "-i",
            "D:\\videos\\JSZN-131.mp4",
            "-vf",
            "scale='min(640,iw)':-2,fps=5",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "30",
            "-an",
            str(Path("artifacts/targeted-video-probes") / "JSZN-131_video_segment_1_17.0_39.0.mp4"),
        ]
    ]


def test_auto_debug_closure_api_runs_closure_for_completed_job() -> None:
    client = TestClient(app)
    case = _video_case(f"api-auto-video-case-{uuid4()}")
    source_job_id = f"api-auto-video-job-{uuid4()}"
    routes.job_repository.save_case(case)
    routes.job_repository.create_job(source_job_id, case.case_id, baseline_trials=1)
    routes.job_repository.save_evidence(
        job_id=source_job_id,
        case_id=case.case_id,
        evidence=[
            _failed_video_timestamp_evidence(source_job_id),
            ExperimentEvidence(
                evidence_id=f"{source_job_id}:pass",
                step_name="temporal_schema_check",
                trial=1,
                raw_output='{"video_action_segments":[]}',
                judge=JudgeResult(score=1, reasons=[]),
            ),
        ],
    )
    routes.job_repository.mark_completed(source_job_id)

    response = client.post(
        f"/jobs/{source_job_id}/auto-closure",
        json={"actor": "api-auto-debugger", "note": "close this video badcase"},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["source_job_id"] == source_job_id
    assert body["created_targeted_probe_jobs"]
    assert body["created_strategy_follow_up_jobs"]
    assert body["created_verification_jobs"]
    assert body["final_attribution_candidates"][0]["category"] == "model_instability"


def test_auto_debug_closure_report_api_returns_chinese_markdown_from_real_closure() -> None:
    client = TestClient(app)
    case = _video_case(f"api-auto-report-video-case-{uuid4()}")
    source_job_id = f"api-auto-report-video-job-{uuid4()}"
    routes.job_repository.save_case(case)
    routes.job_repository.create_job(source_job_id, case.case_id, baseline_trials=1)
    routes.job_repository.save_evidence(
        job_id=source_job_id,
        case_id=case.case_id,
        evidence=[_failed_video_timestamp_evidence(source_job_id)],
    )
    routes.job_repository.mark_completed(source_job_id)

    response = client.post(
        f"/jobs/{source_job_id}/auto-closure/report",
        json={"actor": "api-auto-debugger", "note": "generate trusted markdown report"},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["source_job_id"] == source_job_id
    assert body["markdown"].startswith(f"# {case.case_id} 最终 Debug 报告")
    assert "## 原始 Badcase 证据" in body["markdown"]
    assert "## 自动深挖链路" in body["markdown"]
    assert "## Evidence 明细" in body["markdown"]
    assert "原模型预测" in body["markdown"]
    assert "参考答案" in body["markdown"]
    assert "评分规则" in body["markdown"]
    assert '{"video_action_segments"' in body["markdown"]
    assert body["report_artifact_url"].startswith("/api/artifacts/files/")
    artifact_response = client.get(body["report_artifact_url"])
    assert artifact_response.status_code == 200
    assert artifact_response.text.replace("\r\n", "\n") == body["markdown"]
    assert body["closure"]["source_job_id"] == source_job_id
    assert body["closure"]["created_targeted_probe_jobs"]


class RecordingWritebackClient:
    def __init__(self) -> None:
        self.fields: dict[str, str] = {}

    def update_row(self, spreadsheet_id: str, sheet_id: str, row_id: str, fields: dict[str, str]) -> None:
        self.fields = fields


class RecordingVideoClipper:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create_clip(self, *, source_uri: str, target_id: str, start_s: float, end_s: float) -> str:
        self.calls.append(
            {
                "source_uri": source_uri,
                "target_id": target_id,
                "start_s": start_s,
                "end_s": end_s,
            }
        )
        return "file:///tmp/video_segment_1_probe.mp4"


def _video_case(case_id: str) -> DebugCase:
    return DebugCase.model_validate(
        {
            "case_id": case_id,
            "task_type": "video_detection",
            "image_uri": "file:///tmp/jszn-131.mp4",
            "prompt": "Return video_action_segments JSON.",
            "golden_answer": {"answers": []},
            "expected_output": {
                "temporal_segments": [
                    {
                        "target_id": "video:segment:1",
                        "start_ms": 100,
                        "end_ms": 24000,
                        "label": "The right arm picks up the crab clamp and adjusts its position",
                    }
                ]
            },
            "scoring_standard": """
            [
              {
                "op_name": "check_timestamp",
                "grids": [
                  {
                    "start_s": {"type": "range", "min": 0.0, "max": 1.0},
                    "end_s": {"type": "range", "min": 22.0, "max": 24.0}
                  }
                ]
              }
            ]
            """,
            "predictions": [
                {
                    "trial": 0,
                    "raw_output": (
                        "{\"video_action_segments\":[{\"subtask_label\":\"The right arm picks up the crab clamp and adjusts its position\","
                        "\"start_s\":0.0,\"end_s\":34.0}]}"
                    ),
                    "score": 0,
                }
            ],
            "avg_score": 0.0,
        }
    )


def _failed_video_timestamp_evidence(job_id: str) -> ExperimentEvidence:
    return ExperimentEvidence(
        evidence_id=f"{job_id}:failed",
        step_name="baseline_replay",
        trial=0,
        raw_output='{"video_action_segments":[]}',
        judge=JudgeResult(
            score=0,
            reasons=["video:segment:1 timestamp_end_out_of_range"],
            deltas=[
                {
                    "target_id": "video:segment:1",
                    "expected": "22.0-24.0s",
                    "actual": "34.0s",
                    "reason": "timestamp_end_out_of_range",
                    "metadata": {
                        "field": "end_s",
                        "expected_end_s_range": "22.0-24.0",
                        "actual_end_s": 34.0,
                        "delta_seconds": 10.0,
                    },
                }
            ],
        ),
    )


def _report(
    *,
    root_label: str,
    success_count: int = 0,
    total_trials: int = 1,
    diagnostics: list[dict[str, str]] | None = None,
) -> DebugReport:
    return DebugReport(
        job_id="job-taxonomy",
        case_id="case-taxonomy",
        status="needs_human_review",
        observed_failure=ObservedFailure(type=root_label, summary=f"{root_label} summary", affected_box_ids=[]),
        planned_experiments=["baseline_replay"],
        experiment_summary=ExperimentSummary(
            total_trials=total_trials,
            success_count=success_count,
            failed_trial_count=total_trials - success_count,
            success_rate=success_count / total_trials,
            stability_label="unstable" if 0 < success_count < total_trials else "stable_failure",
            evidence_ids=["e-taxonomy"],
            image_artifact_ids=[],
        ),
        root_cause=RootCause(label=root_label, confidence="high", evidence_summary=f"{root_label} evidence"),
        evaluation_asset_diagnostics=diagnostics or [],
        suggested_sheet_fields={"错误原因": f"{root_label} 中文结论"},
    )
