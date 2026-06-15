import type {
  DebugReport,
  ExperimentEvidence,
  RecommendedActionStatusEvent,
  RecommendedActionVerification,
  RecommendedActionVerificationResult,
  RecommendedActionStatusValue,
  SpreadsheetWritebackAudit,
  SpreadsheetWritebackResult,
  StrategyFollowUpJob,
  TargetedProbeJob
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
  strategyFollowUps?: StrategyFollowUpJob[];
  targetedProbes?: TargetedProbeJob[];
  writebackResult: SpreadsheetWritebackResult | null;
  writebackAudit: SpreadsheetWritebackAudit | null;
  onSelectEvidence: (evidenceId: string) => void;
  onWriteReport: () => void;
  onLoadWritebackAudit: () => void;
  onUpdateRecommendedActionStatus?: (actionIndex: number, status: RecommendedActionStatusValue) => void;
  onVerifyRecommendedAction?: (actionIndex: number) => void;
  onCreateStrategyFollowUp?: (stage: string) => void;
  onCreateTargetedProbe?: (targetId: string) => void;
  onOpenStrategyFollowUp?: (jobId: string) => void;
  onOpenTargetedProbe?: (jobId: string) => void;
};

export function DebugReportWorkspace({
  report,
  selectedEvidence,
  recommendedActionStatusEvents = [],
  recommendedActionVerifications = [],
  recommendedActionVerificationResults = [],
  strategyFollowUps = [],
  targetedProbes = [],
  writebackResult,
  writebackAudit,
  onSelectEvidence,
  onWriteReport,
  onLoadWritebackAudit,
  onUpdateRecommendedActionStatus,
  onVerifyRecommendedAction,
  onCreateStrategyFollowUp,
  onCreateTargetedProbe,
  onOpenStrategyFollowUp,
  onOpenTargetedProbe
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
      <StrategyFollowUpHistory followUps={strategyFollowUps} onOpenStrategyFollowUp={onOpenStrategyFollowUp} />
      <TargetedProbeHistory probes={targetedProbes} onOpenTargetedProbe={onOpenTargetedProbe} />
      <ReportPanel
        report={report}
        recommendedActionStatusEvents={recommendedActionStatusEvents}
        recommendedActionVerifications={recommendedActionVerifications}
        recommendedActionVerificationResults={recommendedActionVerificationResults}
        onSelectEvidence={onSelectEvidence}
        onUpdateRecommendedActionStatus={onUpdateRecommendedActionStatus}
        onVerifyRecommendedAction={onVerifyRecommendedAction}
        onCreateStrategyFollowUp={onCreateStrategyFollowUp}
        onCreateTargetedProbe={onCreateTargetedProbe}
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

type StrategyFollowUpHistoryProps = {
  followUps: StrategyFollowUpJob[];
  onOpenStrategyFollowUp?: (jobId: string) => void;
};

function StrategyFollowUpHistory({ followUps, onOpenStrategyFollowUp }: StrategyFollowUpHistoryProps) {
  if (followUps.length === 0) {
    return null;
  }

  return (
    <section aria-label="Strategy follow-up job history">
      <h2>Strategy Follow-Up Job History</h2>
      <ul>
        {followUps.map((followUp) => (
          <li key={`${followUp.stage}:${followUp.follow_up_job_id}`}>
            <p>
              {followUp.stage}：{followUp.planned_steps}
            </p>
            <p>任务：{followUp.follow_up_job_id}</p>
            <p>Outcome：{followUp.outcome}</p>
            <p>Success Rate：{formatPercent(followUp.success_rate)}</p>
            <p>{followUp.summary}</p>
            {followUp.escalation ? <p>Escalation：{followUp.escalation}</p> : null}
            <p>操作者：{followUp.actor || "unknown"}</p>
            {followUp.note ? <p>备注：{followUp.note}</p> : null}
            <p>时间：{followUp.created_at}</p>
            {onOpenStrategyFollowUp ? (
              <button type="button" onClick={() => onOpenStrategyFollowUp(followUp.follow_up_job_id)}>
                Open strategy follow-up {followUp.follow_up_job_id}
              </button>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}

type TargetedProbeHistoryProps = {
  probes: TargetedProbeJob[];
  onOpenTargetedProbe?: (jobId: string) => void;
};

function TargetedProbeHistory({ probes, onOpenTargetedProbe }: TargetedProbeHistoryProps) {
  if (probes.length === 0) {
    return null;
  }

  return (
    <section aria-label="Targeted probe job history">
      <h2>Targeted Probe Job History</h2>
      <TargetedProbeEscalationChain probes={probes} />
      <ul>
        {probes.map((probe) => (
          <li key={`${probe.target_id}:${probe.probe_job_id}`}>
            <p>
              {probe.target_id}：{probe.planned_steps}
            </p>
            <p>任务：{probe.probe_job_id}</p>
            <p>Outcome：{probe.outcome ?? "pending"}</p>
            <p>Success Rate：{formatPercent(probe.success_rate ?? 0)}</p>
            {probe.summary ? <p>{probe.summary}</p> : null}
            {probe.escalation ? <p>Escalation：{probe.escalation}</p> : null}
            <p>操作者：{probe.actor || "unknown"}</p>
            {probe.note ? <p>备注：{probe.note}</p> : null}
            <p>时间：{probe.created_at}</p>
            {onOpenTargetedProbe ? (
              <button type="button" onClick={() => onOpenTargetedProbe(probe.probe_job_id)}>
                Open targeted probe {probe.probe_job_id}
              </button>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}

type TargetedProbeEscalationChainProps = {
  probes: TargetedProbeJob[];
};

function TargetedProbeEscalationChain({ probes }: TargetedProbeEscalationChainProps) {
  const chains = buildTargetedProbeChains(probes);
  if (chains.length === 0) {
    return null;
  }

  return (
    <section aria-label="Targeted probe escalation chain">
      <h2>Targeted Probe Escalation Chain</h2>
      {chains.map((chain) => (
        <div key={`${chain[0].target_id}:${chain.map((probe) => probe.probe_job_id).join(":")}`}>
          <p>
            Chain target {chain[0].target_id} depth：{chain.length}
          </p>
          {chain.map((probe, index) => (
            <div key={probe.probe_job_id}>
              <p>
                Chain step {index + 1}：{probe.source}/{probe.probe_job_id}
              </p>
              {probe.parent_probe_job_id ? <p>Parent probe：{probe.parent_probe_job_id}</p> : null}
              {probe.trigger_outcome ? <p>Trigger outcome：{probe.trigger_outcome}</p> : null}
            </div>
          ))}
        </div>
      ))}
    </section>
  );
}

function buildTargetedProbeChains(probes: TargetedProbeJob[]) {
  const byTarget = new Map<string, TargetedProbeJob[]>();
  for (const probe of probes) {
    byTarget.set(probe.target_id, [...(byTarget.get(probe.target_id) ?? []), probe]);
  }

  return [...byTarget.values()]
    .map((items) => orderProbeChain(items))
    .filter((items) => items.length > 1 || items.some((probe) => probe.parent_probe_job_id));
}

function orderProbeChain(probes: TargetedProbeJob[]) {
  const byParent = new Map<string, TargetedProbeJob[]>();
  for (const probe of probes) {
    byParent.set(probe.parent_probe_job_id, [...(byParent.get(probe.parent_probe_job_id) ?? []), probe]);
  }
  const ordered: TargetedProbeJob[] = [];
  const visit = (probe: TargetedProbeJob) => {
    ordered.push(probe);
    for (const child of byParent.get(probe.probe_job_id) ?? []) {
      visit(child);
    }
  };
  for (const root of byParent.get("") ?? []) {
    visit(root);
  }
  for (const probe of probes) {
    if (!ordered.includes(probe)) {
      visit(probe);
    }
  }
  return ordered;
}

function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`;
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
