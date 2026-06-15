import type {
  DebugReport,
  RecommendedActionStatusEvent,
  RecommendedActionStatusValue,
  RecommendedActionVerification,
  RecommendedActionVerificationResult
} from "../api/client";

type ReportPanelProps = {
  report: DebugReport;
  recommendedActionStatusEvents?: RecommendedActionStatusEvent[];
  recommendedActionVerifications?: RecommendedActionVerification[];
  recommendedActionVerificationResults?: RecommendedActionVerificationResult[];
  onSelectEvidence?: (evidenceId: string) => void;
  onUpdateRecommendedActionStatus?: (actionIndex: number, status: RecommendedActionStatusValue) => void;
  onVerifyRecommendedAction?: (actionIndex: number) => void;
  onCreateStrategyFollowUp?: (stage: string) => void;
};

export function ReportPanel({
  report,
  recommendedActionStatusEvents = [],
  recommendedActionVerifications = [],
  recommendedActionVerificationResults = [],
  onSelectEvidence,
  onUpdateRecommendedActionStatus,
  onVerifyRecommendedAction,
  onCreateStrategyFollowUp
}: ReportPanelProps) {
  const experimentSummary = report.experiment_summary;
  const artifactIds = experimentSummary?.artifact_ids?.length
    ? experimentSummary.artifact_ids
    : (experimentSummary?.image_artifact_ids ?? []);
  const artifactEvidenceIdByArtifactId = new Map(
    (experimentSummary?.artifact_evidence_links ?? []).map((link) => [link.artifact_id, link.evidence_id])
  );
  const failedTrialCount = experimentSummary?.failed_trial_count ?? 0;
  const evidenceCitations = report.evidence_citations ?? [];
  const stepSummaries = experimentSummary?.step_summaries ?? [];
  const ablationConclusion = report.suggested_sheet_fields["Ablation结论"];
  const rootCauseTrace = report.root_cause_trace ?? [];
  const recommendedActions = report.recommended_actions ?? [];
  const evaluationAssetDiagnostics = report.evaluation_asset_diagnostics ?? [];
  const confidenceReasons = report.confidence_reasons ?? [];
  const debugStrategy = report.debug_strategy ?? [];
  const followUpExperiments = report.follow_up_experiments ?? [];
  const verificationResultByJobId = new Map(
    recommendedActionVerificationResults.map((result) => [result.verification_job_id, result])
  );

  return (
    <section>
      <h2>Root Cause</h2>
      <p>类型：{report.root_cause.label}</p>
      <p>置信度：{report.root_cause.confidence}</p>
      <p>{report.root_cause.evidence_summary}</p>
      {experimentSummary ? (
        <>
          <h3>Replay Stability</h3>
          <p>复测稳定性：{experimentSummary.stability_label ?? "unknown"}</p>
          <p>复测通过率：{formatPercent(experimentSummary.success_rate ?? 0)}</p>
          <p>
            失败次数：{failedTrialCount}/{experimentSummary.total_trials}
          </p>
        </>
      ) : null}
      {stepSummaries.length > 0 ? (
        <>
          <h3>Experiment Trajectory</h3>
          <ul aria-label="Experiment step trajectory">
            {stepSummaries.map((step) => (
              <li key={step.step_name}>
                <p>步骤：{step.step_name}</p>
                <p>步骤通过率：{formatPercent(step.success_rate)}</p>
                <p>
                  步骤失败次数：{step.failed_trial_count}/{step.total_trials}
                </p>
                <p>Delta 类型：{step.delta_reasons.length > 0 ? step.delta_reasons.join(", ") : "无"}</p>
                <p>目标：{step.target_ids.length > 0 ? step.target_ids.join(", ") : "无"}</p>
                {step.ablation_variants?.length ? <p>Ablation：{step.ablation_variants.join(", ")}</p> : null}
                {step.ablation_modalities?.length ? <p>Ablation 模态：{step.ablation_modalities.join(", ")}</p> : null}
                <p>证据：{step.evidence_ids.join(", ")}</p>
                {onSelectEvidence && step.evidence_ids.length > 0 ? (
                  <ul aria-label={`${step.step_name} trajectory evidence`}>
                    {step.evidence_ids.map((evidenceId) => (
                      <li key={evidenceId}>
                        <button type="button" onClick={() => onSelectEvidence(evidenceId)}>
                          {evidenceId}
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : null}
                <p>产物：{step.artifact_ids.length > 0 ? step.artifact_ids.join(", ") : "无"}</p>
                {onSelectEvidence && step.artifact_ids.length > 0 && step.evidence_ids.length > 0 ? (
                  <ArtifactEvidenceButtons
                    artifactIds={step.artifact_ids}
                    evidenceId={step.evidence_ids[0]}
                    onSelectEvidence={onSelectEvidence}
                  />
                ) : null}
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {ablationConclusion ? (
        <section aria-label="Ablation diagnosis">
          <h3>Ablation Diagnosis</h3>
          <p>{ablationConclusion}</p>
        </section>
      ) : null}
      {evaluationAssetDiagnostics.length > 0 ? (
        <>
          <h3>Evaluation Asset Diagnostics</h3>
          <ul aria-label="Evaluation asset diagnostics">
            {evaluationAssetDiagnostics.map((diagnostic) => (
              <li key={`${diagnostic.source}:${diagnostic.status}:${diagnostic.summary}`}>
                <p>
                  {diagnostic.source}/{diagnostic.status}/{diagnostic.severity}
                </p>
                <p>{diagnostic.summary}</p>
                <p>建议：{diagnostic.recommendation}</p>
                <CitationCoverage
                  artifactIds={diagnostic.artifact_ids}
                  evidenceIds={diagnostic.evidence_ids}
                  traceRefs={diagnostic.trace_refs}
                />
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {rootCauseTrace.length > 0 ? (
        <>
          <h3>Root Cause Trace</h3>
          <ul aria-label="Root cause trace">
            {rootCauseTrace.map((trace) => (
              <li key={`${trace.evidence_id}:${trace.variant}`}>
                <p>步骤：{trace.step_name}</p>
                <p>变体：{trace.variant}</p>
                <p>模态：{trace.modalities.length > 0 ? trace.modalities.join(", ") : "无"}</p>
                <p>证据：{trace.evidence_id}</p>
                <p>Judge Score：{trace.judge_score}</p>
                <p>Delta：{trace.delta_reasons.length > 0 ? trace.delta_reasons.join(", ") : "无"}</p>
                <p>目标：{trace.target_ids.length > 0 ? trace.target_ids.join(", ") : "无"}</p>
                <p>产物：{trace.artifact_ids.length > 0 ? trace.artifact_ids.join(", ") : "无"}</p>
                {trace.hypothesis ? <p>假设：{trace.hypothesis}</p> : null}
                {trace.observation ? <p>观察：{trace.observation}</p> : null}
                {trace.conclusion ? <p>结论：{trace.conclusion}</p> : null}
                {trace.next_probe ? <p>下一步：{trace.next_probe}</p> : null}
                {onSelectEvidence && trace.artifact_ids.length > 0 ? (
                  <ArtifactEvidenceButtons
                    artifactIds={trace.artifact_ids}
                    evidenceId={trace.evidence_id}
                    onSelectEvidence={onSelectEvidence}
                  />
                ) : null}
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {recommendedActions.length > 0 ? (
        <>
          <h3>Recommended Actions</h3>
          <ul aria-label="Recommended actions">
            {recommendedActions.map((action, actionIndex) => (
              <li key={`${action.category}:${action.summary}`}>
                <p>
                  {action.category}/{action.priority}：{action.summary}
                </p>
                <p>状态：{action.status ?? "pending"}</p>
                <p>{action.detail}</p>
                <CitationCoverage
                  artifactIds={action.artifact_ids}
                  evidenceIds={action.evidence_ids}
                  traceRefs={action.trace_refs}
                />
                {onUpdateRecommendedActionStatus ? (
                  <p>
                    <button
                      type="button"
                      onClick={() => onUpdateRecommendedActionStatus(actionIndex, "accepted")}
                    >
                      Accept recommended action {actionIndex + 1}
                    </button>
                    <button
                      type="button"
                      onClick={() => onUpdateRecommendedActionStatus(actionIndex, "rejected")}
                    >
                      Reject recommended action {actionIndex + 1}
                    </button>
                    <button
                      type="button"
                      onClick={() => onUpdateRecommendedActionStatus(actionIndex, "applied")}
                    >
                      Mark recommended action {actionIndex + 1} applied
                    </button>
                  </p>
                ) : null}
                {onVerifyRecommendedAction && action.status === "applied" ? (
                  <p>
                    <button type="button" onClick={() => onVerifyRecommendedAction(actionIndex)}>
                      Verify recommended action {actionIndex + 1}
                    </button>
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {debugStrategy.length > 0 ? (
        <>
          <h3>Debug Strategy</h3>
          <ul aria-label="Debug strategy">
            {debugStrategy.map((strategy) => (
              <li key={`${strategy.stage}:${strategy.objective}`}>
                <p>
                  {strategy.stage}：{strategy.objective}
                </p>
                <p>触发：{strategy.trigger}</p>
                <p>探测：{strategy.planned_probe}</p>
                <p>停止条件：{strategy.stop_condition}</p>
                <p>升级：{strategy.escalation}</p>
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {followUpExperiments.length > 0 ? (
        <>
          <h3>Follow-up Experiments</h3>
          <ul aria-label="Follow-up experiments">
            {followUpExperiments.map((followUp) => (
              <li key={`${followUp.source}:${followUp.stage ?? followUp.verification_job_id ?? followUp.planned_steps}`}>
                <p>
                  {followUp.source}/{followUp.stage ?? followUp.result ?? "unknown"}：{followUp.planned_steps}
                </p>
                <p>{followUp.summary}</p>
                {onCreateStrategyFollowUp && isRunnableStrategyFollowUp(followUp.source) && followUp.stage ? (
                  <p>
                    <button type="button" onClick={() => onCreateStrategyFollowUp(followUp.stage!)}>
                      Run strategy follow-up {followUp.stage}
                    </button>
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {confidenceReasons.length > 0 ? (
        <>
          <h3>Confidence Reasons</h3>
          <ul aria-label="Confidence reasons">
            {confidenceReasons.map((reason) => (
              <li key={`${reason.source}:${reason.level}:${reason.summary}`}>
                {reason.source}/{reason.level}：{reason.summary}
                <CitationCoverage
                  artifactIds={reason.artifact_ids}
                  evidenceIds={reason.evidence_ids}
                  traceRefs={reason.trace_refs}
                />
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {recommendedActionStatusEvents.length > 0 ? (
        <>
          <h3>Recommended Action Status Events</h3>
          <ul aria-label="Recommended action status events">
            {recommendedActionStatusEvents.map((event) => (
              <li key={event.event_id}>
                <p>
                  操作 {event.action_index + 1}：{event.status}
                </p>
                <p>操作者：{event.actor || "unknown"}</p>
                {event.note ? <p>备注：{event.note}</p> : null}
                <p>时间：{event.created_at}</p>
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {recommendedActionVerifications.length > 0 ? (
        <>
          <h3>Recommended Action Verification Jobs</h3>
          <ul aria-label="Recommended action verification jobs">
            {recommendedActionVerifications.map((verification) => (
              <li key={`${verification.action_index}:${verification.verification_job_id}`}>
                <p>
                  操作 {verification.action_index + 1} 验证任务：{verification.verification_job_id}
                </p>
                <p>操作者：{verification.actor || "unknown"}</p>
                {verification.note ? <p>备注：{verification.note}</p> : null}
                <p>时间：{verification.created_at}</p>
                {verificationResultByJobId.has(verification.verification_job_id) ? (
                  <VerificationResultSummary result={verificationResultByJobId.get(verification.verification_job_id)!} />
                ) : null}
              </li>
            ))}
          </ul>
        </>
      ) : null}
      <h3>Evidence Artifacts</h3>
      <p>证据产物：{artifactIds.length}</p>
      {artifactIds.length > 0 ? (
        <ul>
          {artifactIds.map((artifactId) => {
            const evidenceId = artifactEvidenceIdByArtifactId.get(artifactId);
            return (
              <li key={artifactId}>
                {onSelectEvidence && evidenceId ? (
                  <button type="button" onClick={() => onSelectEvidence(evidenceId)}>
                    Open artifact {artifactId}
                  </button>
                ) : (
                  artifactId
                )}
              </li>
            );
          })}
        </ul>
      ) : null}
      {evidenceCitations.length > 0 ? (
        <>
          <h3>Evidence Citations</h3>
          <ul>
            {evidenceCitations.map((citation) => (
              <li key={`${citation.evidence_id}:${citation.box_id ?? "global"}:${citation.reason}`}>
                <p>引用证据：{citation.evidence_id}</p>
                <p>引用步骤：{citation.step_name}</p>
                <p>引用目标/区域：{citation.box_id ?? "global"}</p>
                <p>引用原因：{citation.reason}</p>
                {citation.artifact_ids.length > 0 ? <p>引用证据产物：{citation.artifact_ids.join(", ")}</p> : null}
                {onSelectEvidence && citation.artifact_ids.length > 0 ? (
                  <ArtifactEvidenceButtons
                    artifactIds={citation.artifact_ids}
                    evidenceId={citation.evidence_id}
                    onSelectEvidence={onSelectEvidence}
                  />
                ) : null}
              </li>
            ))}
          </ul>
        </>
      ) : null}
      <h3>建议回填</h3>
      <dl>
        {Object.entries(report.suggested_sheet_fields).map(([key, value]) => (
          <div key={key}>
            <dt>{key}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

type VerificationResultSummaryProps = {
  result: RecommendedActionVerificationResult;
};

function VerificationResultSummary({ result }: VerificationResultSummaryProps) {
  return (
    <>
      <p>验证结果：{result.result}</p>
      <p>
        验证通过率：{formatPercent(result.verification_success_rate)}｜原通过率：
        {formatPercent(result.source_success_rate)}
      </p>
      <p>{result.summary}</p>
    </>
  );
}

type CitationCoverageProps = {
  artifactIds?: string;
  evidenceIds?: string;
  traceRefs?: string;
};

function CitationCoverage({ artifactIds = "", evidenceIds = "", traceRefs = "" }: CitationCoverageProps) {
  return (
    <>
      {evidenceIds ? <p>引用证据：{evidenceIds}</p> : null}
      {artifactIds ? <p>引用产物：{artifactIds}</p> : null}
      {traceRefs ? <p>Trace：{traceRefs}</p> : null}
    </>
  );
}

function isRunnableStrategyFollowUp(source: string) {
  return source === "debug_strategy" || source === "strategy_outcome";
}

type ArtifactEvidenceButtonsProps = {
  artifactIds: string[];
  evidenceId: string;
  onSelectEvidence: (evidenceId: string) => void;
};

function ArtifactEvidenceButtons({
  artifactIds,
  evidenceId,
  onSelectEvidence
}: ArtifactEvidenceButtonsProps) {
  return (
    <ul aria-label={`${evidenceId} artifact evidence links`}>
      {artifactIds.map((artifactId) => (
        <li key={artifactId}>
          <button type="button" onClick={() => onSelectEvidence(evidenceId)}>
            Open artifact {artifactId}
          </button>
        </li>
      ))}
    </ul>
  );
}
