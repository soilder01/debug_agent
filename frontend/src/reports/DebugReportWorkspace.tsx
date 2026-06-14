import type {
  DebugReport,
  ExperimentEvidence,
  RecommendedActionStatusEvent,
  RecommendedActionVerification,
  RecommendedActionStatusValue,
  SpreadsheetWritebackAudit,
  SpreadsheetWritebackResult
} from "../api/client";
import { CaseDetail } from "../cases/CaseDetail";
import { EvidenceDetail } from "../evidence/EvidenceDetail";
import { ExperimentTimeline } from "../experiments/ExperimentTimeline";
import { SpreadsheetWritebackPanel } from "../spreadsheets/SpreadsheetWritebackPanel";
import { ReportPanel } from "./ReportPanel";

type DebugReportWorkspaceProps = {
  report: DebugReport;
  selectedEvidence: ExperimentEvidence | null;
  recommendedActionStatusEvents?: RecommendedActionStatusEvent[];
  recommendedActionVerifications?: RecommendedActionVerification[];
  writebackResult: SpreadsheetWritebackResult | null;
  writebackAudit: SpreadsheetWritebackAudit | null;
  onSelectEvidence: (evidenceId: string) => void;
  onWriteReport: () => void;
  onLoadWritebackAudit: () => void;
  onUpdateRecommendedActionStatus?: (actionIndex: number, status: RecommendedActionStatusValue) => void;
  onVerifyRecommendedAction?: (actionIndex: number) => void;
};

export function DebugReportWorkspace({
  report,
  selectedEvidence,
  recommendedActionStatusEvents = [],
  recommendedActionVerifications = [],
  writebackResult,
  writebackAudit,
  onSelectEvidence,
  onWriteReport,
  onLoadWritebackAudit,
  onUpdateRecommendedActionStatus,
  onVerifyRecommendedAction
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
      <ReportPanel
        report={report}
        recommendedActionStatusEvents={recommendedActionStatusEvents}
        recommendedActionVerifications={recommendedActionVerifications}
        onSelectEvidence={onSelectEvidence}
        onUpdateRecommendedActionStatus={onUpdateRecommendedActionStatus}
        onVerifyRecommendedAction={onVerifyRecommendedAction}
      />
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
