import type { DebugJobStatus, ExperimentEvidence, SubmittedDebugJob } from "../api/client";
import { EvidenceDetail } from "../evidence/EvidenceDetail";
import { JobStatusPanel } from "./JobStatusPanel";

type CurrentJobPanelProps = {
  job: DebugJobStatus | SubmittedDebugJob;
  selectedEvidence: ExperimentEvidence | null;
  onSelectEvidence: (evidenceId: string) => void;
  onLoadReport: () => void;
};

export function CurrentJobPanel({ job, selectedEvidence, onSelectEvidence, onLoadReport }: CurrentJobPanelProps) {
  return (
    <>
      <JobStatusPanel job={job} onSelectEvidence={onSelectEvidence} onLoadReport={onLoadReport} />
      <EvidenceDetail evidence={selectedEvidence} />
    </>
  );
}
