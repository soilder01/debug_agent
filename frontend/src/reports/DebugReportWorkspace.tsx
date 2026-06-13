import type { DebugReport, ExperimentEvidence, SpreadsheetWritebackAudit, SpreadsheetWritebackResult } from "../api/client";
import { CaseDetail } from "../cases/CaseDetail";
import { EvidenceDetail } from "../evidence/EvidenceDetail";
import { ExperimentTimeline } from "../experiments/ExperimentTimeline";
import { SpreadsheetWritebackPanel } from "../spreadsheets/SpreadsheetWritebackPanel";
import { ReportPanel } from "./ReportPanel";

type DebugReportWorkspaceProps = {
  report: DebugReport;
  selectedEvidence: ExperimentEvidence | null;
  writebackResult: SpreadsheetWritebackResult | null;
  writebackAudit: SpreadsheetWritebackAudit | null;
  onSelectEvidence: (evidenceId: string) => void;
  onWriteReport: () => void;
  onLoadWritebackAudit: () => void;
};

export function DebugReportWorkspace({
  report,
  selectedEvidence,
  writebackResult,
  writebackAudit,
  onSelectEvidence,
  onWriteReport,
  onLoadWritebackAudit
}: DebugReportWorkspaceProps) {
  return (
    <>
      <CaseDetail jobId={report.job_id} caseId={report.case_id} status={report.status} />
      <ExperimentTimeline
        experiments={report.planned_experiments}
        summary={report.experiment_summary}
        onSelectEvidence={onSelectEvidence}
      />
      <EvidenceDetail evidence={selectedEvidence} />
      <ReportPanel report={report} />
      {report.job_id ? (
        <SpreadsheetWritebackPanel
          writebackResult={writebackResult}
          writebackAudit={writebackAudit}
          onWriteReport={onWriteReport}
          onLoadAudit={onLoadWritebackAudit}
        />
      ) : null}
    </>
  );
}
