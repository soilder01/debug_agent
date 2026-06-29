import type {
  AutoDebugClosureResult,
  DebugReport,
  ExperimentEvidence,
  HumanHandoffStatus,
  HumanHandoffStatusValue,
  LarkWriteConfirmation,
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
  humanHandoffStatuses?: HumanHandoffStatus[];
  writebackResult: SpreadsheetWritebackResult | null;
  writebackAudit: SpreadsheetWritebackAudit | null;
  writeConfirmation?: LarkWriteConfirmation | null;
  onSelectEvidence: (evidenceId: string) => void;
  onWriteReport: () => void;
  onPrepareWriteConfirmation?: () => void;
  onConfirmWriteReport?: () => void;
  onLoadWritebackAudit: () => void;
  onUpdateRecommendedActionStatus?: (actionIndex: number, status: RecommendedActionStatusValue) => void;
  onUpdateHumanHandoffStatus?: (targetId: string, status: HumanHandoffStatusValue) => void;
  onVerifyRecommendedAction?: (actionIndex: number) => void;
  onCreateStrategyFollowUp?: (stage: string) => void;
  onCreateTargetedProbe?: (targetId: string) => void;
  onCreateFinalAttributionFollowUp?: (targetId: string) => void;
  onCreateFinalAttributionRecovery?: (targetId: string) => void;
  onOpenStrategyFollowUp?: (jobId: string) => void;
  onOpenTargetedProbe?: (jobId: string) => void;
  autoDebugClosureResult?: AutoDebugClosureResult | null;
  autoDebugClosureMarkdown?: string;
  autoDebugClosureReportUrl?: string;
  onRunAutoDebugClosure?: () => void;
};

export function DebugReportWorkspace({
  report,
  selectedEvidence,
  recommendedActionStatusEvents = [],
  recommendedActionVerifications = [],
  recommendedActionVerificationResults = [],
  strategyFollowUps = [],
  targetedProbes = [],
  humanHandoffStatuses = [],
  writebackResult,
  writebackAudit,
  writeConfirmation = null,
  onSelectEvidence,
  onWriteReport,
  onPrepareWriteConfirmation,
  onConfirmWriteReport,
  onLoadWritebackAudit,
  onUpdateRecommendedActionStatus,
  onUpdateHumanHandoffStatus,
  onVerifyRecommendedAction,
  onCreateStrategyFollowUp,
  onCreateTargetedProbe,
  onCreateFinalAttributionFollowUp,
  onCreateFinalAttributionRecovery,
  onOpenStrategyFollowUp,
  onOpenTargetedProbe,
  autoDebugClosureResult = null,
  autoDebugClosureMarkdown = "",
  autoDebugClosureReportUrl = "",
  onRunAutoDebugClosure
}: DebugReportWorkspaceProps) {
  return (
    <section aria-label="调试报告工作区" className="report-workspace">
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
        humanHandoffStatuses={humanHandoffStatuses}
        onSelectEvidence={onSelectEvidence}
        onUpdateRecommendedActionStatus={onUpdateRecommendedActionStatus}
        onUpdateHumanHandoffStatus={onUpdateHumanHandoffStatus}
        onVerifyRecommendedAction={onVerifyRecommendedAction}
        onCreateStrategyFollowUp={onCreateStrategyFollowUp}
        onCreateTargetedProbe={onCreateTargetedProbe}
        onCreateFinalAttributionFollowUp={onCreateFinalAttributionFollowUp}
        onCreateFinalAttributionRecovery={onCreateFinalAttributionRecovery}
        autoDebugClosureResult={autoDebugClosureResult}
        autoDebugClosureMarkdown={autoDebugClosureMarkdown}
        autoDebugClosureReportUrl={autoDebugClosureReportUrl}
        onRunAutoDebugClosure={onRunAutoDebugClosure}
      />
      {report.job_id ? (
        <SpreadsheetWritebackPanel
          writebackResult={writebackResult}
          writebackAudit={writebackAudit}
          writeConfirmation={writeConfirmation}
          onWriteReport={onWriteReport}
          onPrepareWriteConfirmation={onPrepareWriteConfirmation}
          onConfirmWriteReport={onConfirmWriteReport}
          onLoadAudit={onLoadWritebackAudit}
        />
      ) : null}
    </section>
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
    <section aria-label="策略执行历史记录" className="evidence-spine">
      <h2>策略执行历史记录</h2>
      <ul>
        {followUps.map((followUp) => (
          <li className="lineage-row" key={`${followUp.stage}:${followUp.follow_up_job_id}`}>
            <p>
              {followUp.stage}：{followUp.planned_steps}
            </p>
            <p>任务：{followUp.follow_up_job_id}</p>
            <p>执行结果：{followUp.outcome}</p>
            <p>成功率：{formatPercent(followUp.success_rate)}</p>
            <p>{followUp.summary}</p>
            {followUp.escalation ? <p>升级异常：{followUp.escalation}</p> : null}
            <p>操作者：{followUp.actor || "未知"}</p>
            {followUp.note ? <p>备注：{followUp.note}</p> : null}
            <p>时间：{followUp.created_at}</p>
            {onOpenStrategyFollowUp ? (
              <button
                type="button"
                aria-label={`打开策略跟进历史任务 ${followUp.follow_up_job_id}`}
                onClick={() => onOpenStrategyFollowUp(followUp.follow_up_job_id)}
              >
                打开历史任务 {followUp.follow_up_job_id}
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
    <section aria-label="定向探测任务历史记录" className="evidence-spine">
      <h2>定向探测任务历史记录</h2>
      <TargetedProbeEscalationChain probes={probes} />
      <ul>
        {probes.map((probe) => (
          <li className="lineage-row" key={`${probe.target_id}:${probe.probe_job_id}`}>
            <p>
              {probe.target_id}：{probe.planned_steps}
            </p>
            <p>任务：{probe.probe_job_id}</p>
            <p>执行结果：{probe.outcome ?? "处理中"}</p>
            <p>成功率：{formatPercent(probe.success_rate ?? 0)}</p>
            {probe.summary ? <p>{probe.summary}</p> : null}
            {probe.escalation ? <p>升级异常：{probe.escalation}</p> : null}
            <p>操作者：{probe.actor || "未知"}</p>
            {probe.note ? <p>备注：{probe.note}</p> : null}
            <p>时间：{probe.created_at}</p>
            {onOpenTargetedProbe ? (
              <button
                type="button"
                aria-label={`打开定向探测 ${probe.probe_job_id}`}
                onClick={() => onOpenTargetedProbe(probe.probe_job_id)}
              >
                打开定向探测 {probe.probe_job_id}
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
    <section aria-label="定向探测升级链">
      <h2>定向探测升级链</h2>
      {chains.map((chain) => (
        <div key={`${chain[0].target_id}:${chain.map((probe) => probe.probe_job_id).join(":")}`}>
          <p>
            链目标 {chain[0].target_id} 深度：{chain.length}
          </p>
          {chain.map((probe, index) => (
            <div key={probe.probe_job_id}>
              <p>
                执行步骤 {index + 1}：{probe.source}/{probe.probe_job_id}
              </p>
              {probe.parent_probe_job_id ? <p>父节点探测：{probe.parent_probe_job_id}</p> : null}
              {probe.trigger_outcome ? <p>触发结果：{probe.trigger_outcome}</p> : null}
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
    <section aria-label="可解释性分析">
      <h2>可解释性分析</h2>
      {firstTrace ? (
        <>
          <p>证据追踪：{firstTrace.evidence_id}</p>
          {firstTrace.next_probe ? <p>下一步探测：{firstTrace.next_probe}</p> : null}
        </>
      ) : null}
      {firstDiagnostic ? (
        <p>
          诊断覆盖情况：{firstDiagnostic.source}/{firstDiagnostic.status}/{firstDiagnostic.severity}
        </p>
      ) : null}
      {firstConfidenceReason ? (
        <p>
          置信度覆盖：{firstConfidenceReason.source}/{firstConfidenceReason.level}
        </p>
      ) : null}
      {firstAction ? (
        <p>
          操作覆盖情况：{firstAction.category}/{firstAction.priority}/{firstAction.status ?? "pending"}
        </p>
      ) : null}
      {firstVerification && firstVerificationResult ? (
        <p>
          验证覆盖情况：{firstVerification.verification_job_id}/{statusLabel(firstVerificationResult.result)}
        </p>
      ) : null}
    </section>
  );
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    accepted: "已接受",
    acknowledged: "已确认",
    applied: "已应用",
    closed: "已关闭",
    failed: "失败",
    in_progress: "进行中",
    pending: "待处理",
    rejected: "已拒绝",
    resolved: "已解决",
    skipped: "跳过",
    succeeded: "成功"
  };
  return labels[status] ?? status;
}
