export type DebugReport = {
  case_id: string;
  status: string;
  observed_failure: {
    type: string;
    summary: string;
    affected_box_ids: number[];
  };
  planned_experiments: string[];
  experiment_summary: {
    total_trials: number;
    success_count: number;
    evidence_ids: string[];
  } | null;
  root_cause: {
    label: string;
    confidence: string;
    evidence_summary: string;
  };
  suggested_sheet_fields: Record<string, string>;
};

export async function debugFixtureCase(caseId: string): Promise<DebugReport> {
  const response = await fetch(`/api/cases/${caseId}/debug`, { method: "POST" });
  if (!response.ok) {
    throw new Error(`Failed to debug case ${caseId}: ${response.status}`);
  }
  return (await response.json()) as DebugReport;
}
