from typing import Literal

from pydantic import BaseModel, Field


AgentRoleId = Literal[
    "case_intake",
    "experiment_planner",
    "model_runner",
    "judge_comparator",
    "evidence_artifact",
    "report_root_cause",
    "hypothesis_strategist",
    "probe_synthesizer",
    "causal_comparator",
    "writeback_operator",
]


DebugStageId = Literal[
    "case_intake",
    "baseline",
    "targeted",
    "verification",
    "hypothesis",
    "intervention",
    "causal_comparison",
    "attribution",
    "writeback",
]


class AgentRoleDefinition(BaseModel):
    role_id: AgentRoleId
    display_name: str
    worker_name: str
    responsibility: str
    default_model_tier: Literal["source_locked", "strong_reasoning", "lightweight", "rules"]
    locked: bool = False
    owned_stages: list[DebugStageId] = Field(default_factory=list)


class DebugStageDefinition(BaseModel):
    stage_id: DebugStageId
    display_name: str
    owner_roles: list[AgentRoleId]
    source_replay: bool = False


AGENT_ROLE_DEFINITIONS: tuple[AgentRoleDefinition, ...] = (
    AgentRoleDefinition(
        role_id="case_intake",
        display_name="Case Intake Agent",
        worker_name="导入搬运员",
        responsibility="Import and normalize debug cases from files, APIs, and spreadsheets.",
        default_model_tier="strong_reasoning",
        owned_stages=["case_intake"],
    ),
    AgentRoleDefinition(
        role_id="experiment_planner",
        display_name="Experiment Planner Agent",
        worker_name="路线规划师",
        responsibility="Route cases by task type and build bounded experiment plans.",
        default_model_tier="strong_reasoning",
        owned_stages=["baseline", "targeted", "attribution"],
    ),
    AgentRoleDefinition(
        role_id="model_runner",
        display_name="Model Runner Agent",
        worker_name="模型终端员",
        responsibility="Execute source-model replay calls and capture durable request and response evidence.",
        default_model_tier="source_locked",
        locked=True,
        owned_stages=["baseline", "targeted", "verification"],
    ),
    AgentRoleDefinition(
        role_id="judge_comparator",
        display_name="Judge Comparator Agent",
        worker_name="评分裁判员",
        responsibility="Score model outputs, compare deltas, and provide model-assisted comparison notes.",
        default_model_tier="strong_reasoning",
        owned_stages=["baseline", "targeted", "verification", "attribution"],
    ),
    AgentRoleDefinition(
        role_id="evidence_artifact",
        display_name="Evidence Artifact Agent",
        worker_name="证据档案员",
        responsibility="Create input, output, crop, and derived evidence artifacts.",
        default_model_tier="lightweight",
        owned_stages=["baseline", "targeted", "verification"],
    ),
    AgentRoleDefinition(
        role_id="report_root_cause",
        display_name="Report Root Cause Agent",
        worker_name="根因分析师",
        responsibility="Infer root cause labels and generate auditable debug reports.",
        default_model_tier="strong_reasoning",
        owned_stages=["attribution"],
    ),
    AgentRoleDefinition(
        role_id="hypothesis_strategist",
        display_name="Hypothesis Strategist Agent",
        worker_name="假设策略师",
        responsibility="Propose candidate root-cause hypotheses from report, evidence, and judge deltas.",
        default_model_tier="strong_reasoning",
        owned_stages=["hypothesis"],
    ),
    AgentRoleDefinition(
        role_id="probe_synthesizer",
        display_name="Probe Synthesizer Agent",
        worker_name="探针合成师",
        responsibility="Convert candidate hypotheses into bounded, controlled probe plans.",
        default_model_tier="strong_reasoning",
        owned_stages=["intervention"],
    ),
    AgentRoleDefinition(
        role_id="causal_comparator",
        display_name="Causal Comparator Agent",
        worker_name="因果比较员",
        responsibility="Compare baseline and intervention evidence to classify hypotheses as supported, rejected, or inconclusive.",
        default_model_tier="strong_reasoning",
        owned_stages=["causal_comparison"],
    ),
    AgentRoleDefinition(
        role_id="writeback_operator",
        display_name="Writeback Operator Agent",
        worker_name="写回调度员",
        responsibility="Write conclusions back to operator systems with audit records.",
        default_model_tier="lightweight",
        owned_stages=["writeback"],
    ),
)


DEBUG_STAGE_DEFINITIONS: tuple[DebugStageDefinition, ...] = (
    DebugStageDefinition(
        stage_id="case_intake", display_name="样本导入", owner_roles=["case_intake"]
    ),
    DebugStageDefinition(
        stage_id="baseline",
        display_name="基线复测",
        owner_roles=["experiment_planner", "model_runner", "judge_comparator", "evidence_artifact"],
        source_replay=True,
    ),
    DebugStageDefinition(
        stage_id="targeted",
        display_name="定向深挖",
        owner_roles=["experiment_planner", "model_runner", "judge_comparator", "evidence_artifact"],
        source_replay=True,
    ),
    DebugStageDefinition(
        stage_id="verification",
        display_name="闭环验证",
        owner_roles=["model_runner", "judge_comparator", "evidence_artifact"],
        source_replay=True,
    ),
    DebugStageDefinition(
        stage_id="hypothesis",
        display_name="候选假设",
        owner_roles=["hypothesis_strategist", "judge_comparator", "report_root_cause"],
    ),
    DebugStageDefinition(
        stage_id="intervention",
        display_name="受控干预",
        owner_roles=["probe_synthesizer", "model_runner", "judge_comparator", "evidence_artifact"],
        source_replay=True,
    ),
    DebugStageDefinition(
        stage_id="causal_comparison",
        display_name="因果比较",
        owner_roles=["causal_comparator", "judge_comparator", "report_root_cause"],
    ),
    DebugStageDefinition(
        stage_id="attribution",
        display_name="最终归因",
        owner_roles=[
            "experiment_planner",
            "hypothesis_strategist",
            "causal_comparator",
            "judge_comparator",
            "report_root_cause",
        ],
    ),
    DebugStageDefinition(
        stage_id="writeback", display_name="写回", owner_roles=["writeback_operator"]
    ),
)


def logical_agent_roles() -> list[AgentRoleDefinition]:
    return list(AGENT_ROLE_DEFINITIONS)


def debug_stage_definitions() -> list[DebugStageDefinition]:
    return list(DEBUG_STAGE_DEFINITIONS)


def agent_role_definition(role_id: str) -> AgentRoleDefinition | None:
    return next((role for role in AGENT_ROLE_DEFINITIONS if role.role_id == role_id), None)


def roles_for_stage(stage_id: str) -> list[AgentRoleId]:
    stage = next((item for item in DEBUG_STAGE_DEFINITIONS if item.stage_id == stage_id), None)
    return list(stage.owner_roles) if stage is not None else []


def is_source_replay_stage(stage_id: str) -> bool:
    stage = next((item for item in DEBUG_STAGE_DEFINITIONS if item.stage_id == stage_id), None)
    return bool(stage and stage.source_replay)


def role_for_experiment_step(step_name: str) -> AgentRoleId:
    del step_name
    return "model_runner"
