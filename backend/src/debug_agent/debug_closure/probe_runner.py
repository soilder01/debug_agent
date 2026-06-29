from __future__ import annotations

import json

from pydantic import BaseModel

from debug_agent.cases.models import DebugCase
from debug_agent.debug_closure.hypotheses import DebugProbePlan, DebugProbeRunResult
from debug_agent.debug_closure.probe_library import intervention_requires_locked_model_runner
from debug_agent.jobs.service import DebugJobService
from debug_agent.models.config import AgentModelConfig, sanitize_agent_model_config
from debug_agent.settings import ArkSettings
from debug_agent.storage.repository import DebugJobRepository


class ControlledProbeDraft(BaseModel):
    plan: DebugProbePlan
    derived_case: DebugCase
    probe_result: DebugProbeRunResult
    should_submit_debug_job: bool


def build_controlled_probe_draft(
    *,
    source_case: DebugCase,
    source_job_id: str,
    plan: DebugProbePlan,
    agent_model_config: AgentModelConfig | None = None,
    ark_settings: ArkSettings | None = None,
) -> ControlledProbeDraft:
    should_submit = intervention_requires_locked_model_runner(plan.intervention_type)
    derived_case = _derive_probe_case(source_case=source_case, plan=plan)
    return ControlledProbeDraft(
        plan=plan,
        derived_case=derived_case,
        should_submit_debug_job=should_submit,
        probe_result=DebugProbeRunResult(
            probe_id=plan.probe_id,
            hypothesis_id=plan.hypothesis_id,
            iteration=plan.iteration,
            status="not_run",
            source_job_id=source_job_id,
            model_runner_config_snapshot=(
                _locked_model_runner_snapshot(
                    agent_model_config=agent_model_config,
                    ark_settings=ark_settings,
                )
                if should_submit
                else {}
            ),
        ),
    )


def submit_controlled_probe_job(
    *,
    repository: DebugJobRepository,
    job_service: DebugJobService,
    draft: ControlledProbeDraft,
    artifact_group_id: str,
) -> ControlledProbeDraft:
    if not draft.should_submit_debug_job:
        return draft
    repository.save_case(draft.derived_case)
    submitted = job_service.submit_case_debug(
        draft.derived_case.case_id,
        baseline_trials=draft.plan.trials,
        artifact_group_id=artifact_group_id,
    )
    return draft.model_copy(
        update={
            "probe_result": draft.probe_result.model_copy(
                update={
                    "probe_job_id": submitted.job_id,
                    "status": "not_run",
                }
            )
        }
    )


def _derive_probe_case(*, source_case: DebugCase, plan: DebugProbePlan) -> DebugCase:
    return source_case.model_copy(
        update={
            "case_id": f"{source_case.case_id}__hypothesis_probe__{_safe_case_fragment(plan.probe_id)}",
            "prompt": _probe_prompt(source_case=source_case, plan=plan),
        }
    )


def _probe_prompt(*, source_case: DebugCase, plan: DebugProbePlan) -> str:
    if plan.intervention_type not in {
        "prompt_patch",
        "stability_rerun",
        "input_localization",
        "schema_constraint",
    }:
        return source_case.prompt

    lines = [
        source_case.prompt,
        "",
        "## 受控假设验证",
        f"- hypothesis_id: {plan.hypothesis_id}",
        f"- probe_id: {plan.probe_id}",
        f"- intervention_type: {plan.intervention_type}",
        "- 公平性约束：不得改变 model_id、mode、thinking、媒体输入或评分标准。",
        "- 成功标准：",
        json.dumps(plan.success_criteria, ensure_ascii=False, indent=2),
    ]
    prompt_patch = plan.intervention_payload.get("prompt_patch")
    if isinstance(prompt_patch, str) and prompt_patch.strip():
        lines.extend(["", "## Prompt Patch", prompt_patch.strip()])
    elif plan.intervention_type == "schema_constraint":
        lines.extend(
            ["", "## Schema Constraint", "按原输出 schema 补充 checklist 约束，禁止改变任务语义。"]
        )
    elif plan.intervention_type == "input_localization":
        lines.extend(["", "## Input Localization", "只收窄观察证据范围，禁止改变被测模型配置。"])
    elif plan.intervention_type == "stability_rerun":
        lines.extend(
            ["", "## Stability Rerun", "保持原 prompt、原媒体和原评分标准，重复执行稳定性复测。"]
        )
    return "\n".join(lines)


def _locked_model_runner_snapshot(
    *,
    agent_model_config: AgentModelConfig | None,
    ark_settings: ArkSettings | None,
) -> dict[str, object]:
    sanitized = sanitize_agent_model_config(agent_model_config, ark_settings=ark_settings)
    return sanitized.roles["model_runner"].model_dump(mode="json")


def _safe_case_fragment(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value).strip("_")
