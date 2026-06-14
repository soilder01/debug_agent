from pydantic import BaseModel


class AgentRole(BaseModel):
    role_id: str
    display_name: str
    responsibility: str


def logical_agent_roles() -> list[AgentRole]:
    return [
        AgentRole(
            role_id="case_intake",
            display_name="Case Intake Agent",
            responsibility="Import and normalize debug cases from files, APIs, and spreadsheets.",
        ),
        AgentRole(
            role_id="experiment_planner",
            display_name="Experiment Planner Agent",
            responsibility="Route cases by task type and build bounded experiment plans.",
        ),
        AgentRole(
            role_id="model_runner",
            display_name="Model Runner Agent",
            responsibility="Execute model calls and capture durable request and response evidence.",
        ),
        AgentRole(
            role_id="judge_comparator",
            display_name="Judge Comparator Agent",
            responsibility="Score model outputs and produce structured mismatch deltas.",
        ),
        AgentRole(
            role_id="evidence_artifact",
            display_name="Evidence Artifact Agent",
            responsibility="Create input, output, crop, and derived evidence artifacts.",
        ),
        AgentRole(
            role_id="report_root_cause",
            display_name="Report Root Cause Agent",
            responsibility="Infer root cause labels and generate auditable debug reports.",
        ),
        AgentRole(
            role_id="writeback_operator",
            display_name="Writeback Operator Agent",
            responsibility="Write conclusions back to operator systems with audit records.",
        ),
    ]
