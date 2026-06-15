import type {
  DebugReport,
  ExperimentEvidence,
  RecommendedActionStatusEvent,
  RecommendedActionVerification,
  RecommendedActionVerificationResult,
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
  recommendedActionVerificationResults?: RecommendedActionVerificationResult[];
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
  recommendedActionVerificationResults = [],
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
      <ExplainabilityWorkspace
        recommendedActionVerificationResults={recommendedActionVerificationResults}
        recommendedActionVerifications={recommendedActionVerifications}
        report={report}
      />
      <ReportPanel
        report={report}
        recommendedActionStatusEvents={recommendedActionStatusEvents}
        recommendedActionVerifications={recommendedActionVerifications}
        recommendedActionVerificationResults={recommendedActionVerificationResults}
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

type ExplainabilityWorkspaceProps = {
  report: DebugReport;
  recommendedActionVerifications: RecommendedActionVerification[];
  recommendedActionVerificationResults: RecommendedActionVerificationResult[];
};

function ExplainabilityWorkspace({
  report,
  recommendedActionVerifications,
  recommendedActionVerificationResults
}: ExplainabilityWorkspaceProps) {
  const firstTrace = report.root_cause_trace?.[0];
  const firstDiagnostic = report.evaluation_asset_diagnostics?.[0];
  const firstConfidenceReason = report.confidence_reasons?.[0];
  const firstAction = report.recommended_actions?.[0];
  const verificationResultByJobId = new Map(
    recommendedActionVerificationResults.map((result) => [result.verification_job_id, result])
  );
  const firstVerification = recommendedActionVerifications[0];
  const firstVerificationResult = firstVerification
    ? verificationResultByJobId.get(firstVerification.verification_job_id)
    : undefined;

  if (!firstTrace && !firstDiagnostic && !firstConfidenceReason && !firstAction && !firstVerificationResult) {
    return null;
  }

  return (
    <section aria-label="Explainability workspace">
      <h2>Explainability Workspace</h2>
      {firstTrace ? (
        <>
          <p>Evidence spine：{firstTrace.evidence_id}</p>
          {firstTrace.next_probe ? <p>Next probe：{firstTrace.next_probe}</p> : null}
        </>
      ) : null}
      {firstDiagnostic ? (
        <p>
          Diagnostic coverage：{firstDiagnostic.source}/{firstDiagnostic.status}/{firstDiagnostic.severity}
        </p>
      ) : null}
      {firstConfidenceReason ? (
        <p>
          Confidence coverage：{firstConfidenceReason.source}/{firstConfidenceReason.level}
        </p>
      ) : null}
      {firstAction ? (
        <p>
          Action coverage：{firstAction.category}/{firstAction.priority}/{firstAction.status ?? "pending"}
        </p>
      ) : null}
      {firstVerification && firstVerificationResult ? (
        <p>
          Verification coverage：{firstVerification.verification_job_id}/{firstVerificationResult.result}
        </p>
      ) : null}
    </section>
  );
}
