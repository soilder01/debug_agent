from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from typing import Any

from debug_agent.lark.progress_presenter import build_lark_progress_card
from debug_agent.settings import DebugAgentSettings
from debug_agent.storage.models import DebugJobRow
from debug_agent.storage.repository import DebugJobRepository, DebugRunStage


class LarkProgressController:
    def __init__(
        self,
        *,
        settings: Callable[[], DebugAgentSettings],
        job_repository: DebugJobRepository,
        report_url: Callable[[str], str],
    ) -> None:
        self._settings = settings
        self._job_repository = job_repository
        self._report_url = report_url

    def progress_state(self, *, job: DebugJobRow) -> dict[str, object] | None:
        stages = self._job_repository.list_debug_run_stages(job.job_id)
        stage_map = {stage.stage: stage for stage in stages}

        def with_runtime(progress: dict[str, object] | None) -> dict[str, object] | None:
            if progress is None:
                return None
            return progress_state_with_runtime(job=job, progress=progress, stages=stages)

        if job.status in {"created", "pending"}:
            return with_runtime(
                progress_state(
                    key="queued",
                    stage="queued",
                    title="Debug Agent 已排队",
                    summary="任务已进入队列，等待 worker 执行。",
                    detail="小D会继续跟进进度，完成后发最终报告卡片。",
                    percent=5,
                )
            )
        if job.status == "running":
            baseline_stage = stage_map.get("baseline")
            if baseline_stage is not None and baseline_stage.status == "completed":
                return with_runtime(
                    progress_state(
                        key="attribution-running",
                        stage="attribution",
                        title="正在归因和规划后续验证",
                        summary="基础复测已产生证据，正在运行 report_root_cause / experiment_planner / judge_comparator。",
                        detail="这一步会整理根因、推荐动作和后续闭环计划。",
                        percent=35,
                    )
                )
            return with_runtime(
                progress_state(
                    key="baseline-running",
                    stage="baseline",
                    title="正在执行基础复测",
                    summary="model_runner 正在复现 badcase 并生成 evidence ledger。",
                    detail="视频/多模态样本会比纯文本样本更慢。",
                    percent=20,
                )
            )
        if job.status == "completed":
            auto_stage = stage_map.get("auto_closure")
            if auto_stage is None and self._settings().auto_closure_enabled:
                return with_runtime(
                    progress_state(
                        key="auto-closure-starting",
                        stage="auto_closure",
                        title="正在进入自动闭环",
                        summary="基础 DebugJob 已完成，auto-debug-agent 正在启动 targeted probes 和 verification。",
                        detail="最终完成卡片会等 auto-closure 结束后再发。",
                        percent=45,
                    )
                )
            if auto_stage is not None and auto_stage.status == "running":
                return with_runtime(self.auto_closure_progress_state(job=job))
            if auto_stage is not None and auto_stage.status == "failed":
                return with_runtime(
                    progress_state(
                        key="auto-closure-failed",
                        stage="auto_closure",
                        title="自动闭环异常，正在准备报告",
                        summary="auto-closure 未能完整结束，小D会把失败原因和已有证据写入最终报告。",
                        detail=clip_text(auto_stage.failure_reason or "未记录失败原因", 240),
                        percent=95,
                        template="red",
                    )
                )
        return None

    def auto_closure_progress_state(self, *, job: DebugJobRow) -> dict[str, object]:
        stages = self._job_repository.list_debug_run_stages(job.job_id)
        hypothesis_stage = next(
            (stage for stage in reversed(stages) if stage.stage == "hypothesis"), None
        )
        targeted = self._job_repository.list_targeted_probe_jobs(job.job_id)
        strategy = self._job_repository.list_strategy_follow_up_jobs(job.job_id)
        verifications = self._job_repository.list_recommended_action_verifications(job.job_id)
        targeted_completed_count = self.completed_related_job_count(
            item.probe_job_id for item in targeted
        )
        strategy_completed_count = self.completed_related_job_count(
            item.follow_up_job_id for item in strategy
        )
        verification_completed_count = self.completed_related_job_count(
            item.verification_job_id for item in verifications
        )
        if targeted and targeted_completed_count < len(targeted):
            return progress_state(
                key=f"targeted-{len(targeted)}-{targeted_completed_count}",
                stage="targeted_probe",
                title="正在做定向复测",
                summary=f"auto-debug-agent 已创建 {len(targeted)} 个 targeted probe，完成 {targeted_completed_count} 个。",
                detail="小D正在复核失败片段，不会提前发最终结论。",
                percent=min(75, 45 + targeted_completed_count * 8),
            )
        if strategy and strategy_completed_count < len(strategy):
            return progress_state(
                key=f"strategy-{len(strategy)}-{strategy_completed_count}",
                stage="strategy_follow_up",
                title="正在做稳定性跟进",
                summary=f"已创建 {len(strategy)} 个 strategy follow-up，完成 {strategy_completed_count} 个。",
                detail="这一步用于验证根因是否稳定、是否还需要升级处理。",
                percent=min(85, 72 + strategy_completed_count * 5),
            )
        if verifications and verification_completed_count < len(verifications):
            return progress_state(
                key=f"verification-{len(verifications)}-{verification_completed_count}",
                stage="verification",
                title="正在验证推荐动作",
                summary=f"已创建 {len(verifications)} 个推荐动作验证任务，完成 {verification_completed_count} 个。",
                detail="最终通知会包含验证结果和下一步动作。",
                percent=min(95, 84 + verification_completed_count * 5),
            )
        if hypothesis_stage is not None:
            return hypothesis_progress_state(hypothesis_stage)
        if targeted or strategy or verifications:
            return progress_state(
                key=(
                    f"auto-closure-finalizing-{len(targeted)}-{len(strategy)}-{len(verifications)}"
                ),
                stage="auto_closure",
                title="正在汇总闭环结果",
                summary="复测/验证任务已完成，auto-debug-agent 正在汇总最终报告。",
                detail="小D即将发送最终完成卡片。",
                percent=96,
            )
        return progress_state(
            key="auto-closure-running",
            stage="auto_closure",
            title="正在自动闭环",
            summary="auto-debug-agent 正在整理复测计划和后续动作。",
            detail="这一步会自动决定是否创建 targeted probes、follow-up 或 verification。",
            percent=50,
        )

    def completed_related_job_count(self, job_ids: Iterable[object]) -> int:
        count = 0
        for job_id in job_ids:
            if not isinstance(job_id, str) or not job_id:
                continue
            job = self._job_repository.get_job(job_id)
            if job is not None and job.status == "completed":
                count += 1
        return count

    def progress_card_for_job(
        self,
        *,
        job: DebugJobRow,
        progress: dict[str, object],
        title: str,
    ) -> dict[str, object]:
        base_url = self._settings().report_base_url.rstrip("/")
        return build_lark_progress_card(
            title=title,
            template=str(progress.get("template", "blue")),
            job_id=job.job_id,
            job_url=f"{base_url}/xiaod/views/jobs/{job.job_id}",
            run_stages_url=f"{base_url}/xiaod/views/jobs/{job.job_id}/run-stages",
            report_url=self._report_url(job.job_id),
            progress=progress,
        )

    def stable_progress_idempotency_key(self, progress_key: str) -> str:
        digest = hashlib.sha256(progress_key.encode("utf-8")).hexdigest()[:24]
        return f"da-progress-{digest}"

    def stable_completion_idempotency_key(self, *, draft_id: str, job_id: str) -> str:
        raw_key = f"{draft_id}:{job_id}"
        digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:24]
        return f"da-done-{digest}"


def progress_state(
    *,
    key: str,
    stage: str,
    title: str,
    summary: str,
    detail: str,
    percent: int,
    template: str = "blue",
) -> dict[str, object]:
    return {
        "key": key,
        "stage": stage,
        "title": title,
        "summary": summary,
        "detail": detail,
        "percent": max(0, min(100, percent)),
        "template": template,
    }


def progress_state_with_runtime(
    *,
    job: DebugJobRow,
    progress: dict[str, object],
    stages: list[DebugRunStage],
) -> dict[str, object]:
    enriched = dict(progress)
    stage_name = str(progress["stage"])
    stage = progress_debug_stage(stage_name=stage_name, stages=stages)
    enriched["stage_elapsed"] = progress_elapsed_label(stage=stage, job=job)
    enriched["completed_agents"] = progress_completed_agent_label(stages)
    enriched["next_step"] = progress_next_step(stage_name)
    return enriched


def progress_debug_stage(
    *,
    stage_name: str,
    stages: list[DebugRunStage],
) -> DebugRunStage | None:
    stage_map = {stage.stage: stage for stage in stages}
    if stage_name in stage_map:
        return stage_map[stage_name]
    alias = {
        "targeted_probe": "targeted",
        "strategy_follow_up": "verification",
        "verification": "verification",
    }.get(stage_name)
    if alias and alias in stage_map:
        return stage_map[alias]
    return stage_map.get("auto_closure")


def progress_elapsed_label(*, stage: DebugRunStage | None, job: DebugJobRow) -> str:
    started_at = stage.created_at if stage is not None and stage.created_at else job.created_at
    return duration_since(started_at)


def duration_since(started_at: str) -> str:
    if not started_at:
        return "未知"
    try:
        started = datetime.fromisoformat(started_at)
    except ValueError:
        return "未知"
    if started.tzinfo is None:
        started = started.replace(tzinfo=UTC)
    seconds = max(0, int((datetime.now(UTC) - started).total_seconds()))
    if seconds < 60:
        return "不到 1 分钟"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} 分钟"
    hours = minutes // 60
    remaining_minutes = minutes % 60
    if remaining_minutes == 0:
        return f"{hours} 小时"
    return f"{hours} 小时 {remaining_minutes} 分钟"


def progress_completed_agent_label(stages: list[DebugRunStage]) -> str:
    agents: list[str] = []
    for stage in stages:
        if stage.status != "completed":
            continue
        for agent in progress_agents_for_stage(stage.stage):
            if agent not in agents:
                agents.append(agent)
    return "、".join(agents) if agents else "暂无"


def progress_agents_for_stage(stage_name: str) -> list[str]:
    return {
        "baseline": ["model_runner"],
        "attribution": ["report_root_cause", "experiment_planner", "judge_comparator"],
        "hypothesis": ["hypothesis_strategist", "probe_synthesizer", "causal_comparator"],
        "intervention": ["probe_synthesizer", "model_runner", "judge_comparator"],
        "causal_comparison": ["causal_comparator"],
        "targeted": ["auto-debug-agent", "model_runner"],
        "verification": ["auto-debug-agent", "judge_comparator"],
        "auto_closure": ["auto-debug-agent"],
        "writeback": ["writeback_operator"],
    }.get(stage_name, [])


def progress_next_step(stage_name: str) -> str:
    return {
        "queued": "等待 worker 领取任务并启动基础复测。",
        "baseline": "基础复测完成后进入根因归因和后续验证规划。",
        "attribution": "归因规划完成后进入 auto-closure 定向复测/验证。",
        "hypothesis": "候选假设生成后进入受控 probe 或因果比较汇总。",
        "intervention": "等待 locked model_runner 完成受控干预复测。",
        "causal_comparison": "等待因果比较完成后再汇总最终报告。",
        "auto_closure": "等待 auto-debug-agent 创建或汇总后续复测与验证结果。",
        "targeted_probe": "等待定向复测完成，再判断是否进入稳定性跟进或推荐动作验证。",
        "strategy_follow_up": "等待稳定性跟进完成，判断是否需要升级或人工复核。",
        "verification": "等待推荐动作验证完成，然后汇总最终报告卡片。",
    }.get(stage_name, "继续等待 Debug Agent 更新运行阶段。")


def hypothesis_progress_state(stage: DebugRunStage) -> dict[str, object]:
    payload = stage.output.get("hypothesis_closure")
    closure = payload if isinstance(payload, dict) else {}
    hypothesis_count = payload_count(closure, "hypotheses")
    probe_plan_count = payload_count(closure, "probe_plans")
    comparison_count = payload_count(closure, "causal_comparisons")
    if stage.status == "failed":
        return progress_state(
            key="hypothesis-failed",
            stage="hypothesis",
            title="候选根因假设生成异常",
            summary="hypothesis closure 失败，当前不会把候选解释提升为已验证根因。",
            detail=clip_text(stage.failure_reason or "未记录失败原因", 240),
            percent=58,
            template="red",
        )
    fairness_ref = payload_fairness_ref(closure)
    fairness_text = f"公平性锁 {fairness_ref}" if fairness_ref else "公平性锁未记录"
    return progress_state(
        key=f"hypothesis-{hypothesis_count}-{probe_plan_count}-{comparison_count}",
        stage="hypothesis",
        title="正在生成候选根因假设",
        summary=(
            f"已生成候选假设 {hypothesis_count} 个、Probe 计划 {probe_plan_count} 个、"
            f"因果比较 {comparison_count} 个。"
        ),
        detail=f"{fairness_text}；受控 probe 尚未执行前不会提升为已验证根因。",
        percent=58,
    )


def payload_count(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    return len(value) if isinstance(value, list) else 0


def payload_fairness_ref(payload: dict[str, Any]) -> str:
    fairness_lock = payload.get("fairness_lock")
    if not isinstance(fairness_lock, dict):
        return ""
    value = fairness_lock.get("model_runner_config_ref", "")
    return value if isinstance(value, str) else ""


def clip_text(value: str, max_length: int) -> str:
    return value if len(value) <= max_length else f"{value[:max_length]}..."
