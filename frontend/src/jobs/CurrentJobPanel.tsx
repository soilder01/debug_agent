import type { DebugJobStatus, DebugRunStage, EvidenceLedgerRecord, ExperimentEvidence, SubmittedDebugJob } from "../api/client";
import { EvidenceDetail } from "../evidence/EvidenceDetail";
import { JobStatusPanel } from "./JobStatusPanel";

type CurrentJobPanelProps = {
  job: DebugJobStatus | SubmittedDebugJob;
  runStages?: DebugRunStage[];
  evidenceLedger?: EvidenceLedgerRecord[];
  selectedEvidence: ExperimentEvidence | null;
  onSelectEvidence: (evidenceId: string) => void;
  onLoadReport: () => void;
  onLoadRunStages?: () => void;
  onLoadEvidenceLedger?: () => void;
};

export function CurrentJobPanel({
  job,
  runStages = [],
  evidenceLedger = [],
  selectedEvidence,
  onSelectEvidence,
  onLoadReport,
  onLoadRunStages,
  onLoadEvidenceLedger
}: CurrentJobPanelProps) {
  return (
    <section aria-label="当前任务工作区" className="current-job-panel">
      <JobStatusPanel
        job={job}
        runStages={runStages}
        evidenceLedger={evidenceLedger}
        onSelectEvidence={onSelectEvidence}
        onLoadReport={onLoadReport}
        onLoadRunStages={onLoadRunStages}
        onLoadEvidenceLedger={onLoadEvidenceLedger}
      />
      <EvidenceDetail evidence={selectedEvidence} />
    </section>
  );
}
