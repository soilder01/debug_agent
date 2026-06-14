const agentRoles = [
  {
    roleId: "case_intake",
    displayName: "Case Intake Agent",
    responsibility: "Import and normalize debug cases from files, APIs, and spreadsheets."
  },
  {
    roleId: "experiment_planner",
    displayName: "Experiment Planner Agent",
    responsibility: "Route cases by task type and build bounded experiment plans."
  },
  {
    roleId: "model_runner",
    displayName: "Model Runner Agent",
    responsibility: "Execute model calls and capture durable request and response evidence."
  },
  {
    roleId: "judge_comparator",
    displayName: "Judge Comparator Agent",
    responsibility: "Score model outputs and produce structured mismatch deltas."
  },
  {
    roleId: "evidence_artifact",
    displayName: "Evidence Artifact Agent",
    responsibility: "Create input, output, crop, and derived evidence artifacts."
  },
  {
    roleId: "report_root_cause",
    displayName: "Report Root Cause Agent",
    responsibility: "Infer root cause labels and generate auditable debug reports."
  },
  {
    roleId: "writeback_operator",
    displayName: "Writeback Operator Agent",
    responsibility: "Write conclusions back to operator systems with audit records."
  }
];

export function AgentTopologyPanel() {
  return (
    <section>
      <h2>Agent Topology</h2>
      <ul>
        {agentRoles.map((role) => (
          <li key={role.roleId}>
            <h3>{role.displayName}</h3>
            <p>{role.responsibility}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
