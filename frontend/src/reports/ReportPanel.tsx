import type {
  AutoDebugClosureResult,
  DebugReport,
  HumanHandoffStatus,
  HumanHandoffStatusValue,
  RecommendedActionStatusEvent,
  RecommendedActionStatusValue,
  RecommendedActionVerification,
  RecommendedActionVerificationResult
} from "../api/client";
import { MetricStrip } from "../ui/ProductPrimitives";

type ReportPanelProps = {
  report: DebugReport;
  recommendedActionStatusEvents?: RecommendedActionStatusEvent[];
  recommendedActionVerifications?: RecommendedActionVerification[];
  recommendedActionVerificationResults?: RecommendedActionVerificationResult[];
  humanHandoffStatuses?: HumanHandoffStatus[];
  onSelectEvidence?: (evidenceId: string) => void;
  onUpdateRecommendedActionStatus?: (actionIndex: number, status: RecommendedActionStatusValue) => void;
  onUpdateHumanHandoffStatus?: (targetId: string, status: HumanHandoffStatusValue) => void;
  onVerifyRecommendedAction?: (actionIndex: number) => void;
  onCreateStrategyFollowUp?: (stage: string) => void;
  onCreateTargetedProbe?: (targetId: string) => void;
  onCreateFinalAttributionFollowUp?: (targetId: string) => void;
  onCreateFinalAttributionRecovery?: (targetId: string) => void;
  autoDebugClosureResult?: AutoDebugClosureResult | null;
  autoDebugClosureMarkdown?: string;
  autoDebugClosureReportUrl?: string;
  onRunAutoDebugClosure?: () => void;
};

export function ReportPanel({
  report,
  recommendedActionStatusEvents = [],
  recommendedActionVerifications = [],
  recommendedActionVerificationResults = [],
  humanHandoffStatuses = [],
  onSelectEvidence,
  onUpdateRecommendedActionStatus,
  onUpdateHumanHandoffStatus,
  onVerifyRecommendedAction,
  onCreateStrategyFollowUp,
  onCreateTargetedProbe,
  onCreateFinalAttributionFollowUp,
  onCreateFinalAttributionRecovery,
  autoDebugClosureResult = null,
  autoDebugClosureMarkdown = "",
  autoDebugClosureReportUrl = "",
  onRunAutoDebugClosure
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
  const runView = report.run_view;
  const debugLoop = runView?.debug_loop;
  const hypothesisClosure = runView?.hypothesis_closure;
  const hypothesisFairnessLock = textValue(hypothesisClosure?.fairness_lock?.model_runner_config_ref);
  const hypothesisClosureCounts = hypothesisClosure
    ? `候选假设：${hypothesisClosure.hypothesis_count}｜Probe 计划：${hypothesisClosure.probe_plan_count}｜因果比较：${hypothesisClosure.causal_comparison_count}｜已验证根因：${hypothesisClosure.verified_root_cause_count}`
    : "";
  const actionQueue = runView?.action_queue.items ?? report.action_queue ?? [];
  const evaluationAssetDiagnostics = report.evaluation_asset_diagnostics ?? [];
  const confidenceReasons = report.confidence_reasons ?? [];
  const debugStrategy = report.debug_strategy ?? [];
  const judgeComparisonNotes = report.judge_comparison_notes ?? [];
  const followUpExperiments = report.follow_up_experiments ?? [];
  const productSummary = report.product_summary;
  const rootCauseLabel = productSummary?.root_cause_label ?? `${report.root_cause.label}/${report.root_cause.confidence}`;
  const confidenceExplanation = productSummary?.confidence_explanation ?? report.root_cause.confidence;
  const metaAgentTelemetry = metaTelemetry(report.meta_agent_enrichment);
  const humanHandoffRequests = report.human_handoff_requests ?? [];
  const finalAttributions = report.final_attributions ?? [];
  const finalAttributionVerificationResults = report.final_attribution_verification_results ?? [];
  const finalAttributionRecoveryResults = report.final_attribution_recovery_results ?? [];
  const verificationResultByJobId = new Map(
    recommendedActionVerificationResults.map((result) => [result.verification_job_id, result])
  );
  const resolvedHumanHandoffStatuses = humanHandoffStatuses.length > 0 ? humanHandoffStatuses : (report.human_handoff_statuses ?? []);
  const humanHandoffStatusByTargetId = new Map(resolvedHumanHandoffStatuses.map((status) => [status.target_id, status]));

  return (
    <section aria-label="根因分析" className="root-cause-panel">
      <h2>根因分析</h2>
      <MetricStrip
        label="根因指标"
        metrics={[
          { label: "置信度", value: confidenceExplanation, helper: rootCauseLabel },
          { label: "失败次数", value: failedTrialCount, helper: "复测失败数" },
          { label: "证据产物", value: artifactIds.length, helper: "关键证据" },
          { label: "建议操作", value: recommendedActions.length, helper: "后续建议" }
        ]}
      />
      <p>类型：{rootCauseLabel}</p>
      <p>置信度：{confidenceExplanation}</p>
      <p>{productSummary?.failure_summary ?? report.root_cause.evidence_summary}</p>
      {productSummary?.evidence_source ? <p>证据来源：{productSummary.evidence_source}</p> : null}
      {productSummary?.next_action ? <p>下一步：{productSummary.next_action}</p> : null}
      {metaAgentTelemetry.length > 0 ? (
        <section aria-label="Meta Agent 执行记录">
          <h3>Meta Agent 执行记录</h3>
          <ul className="evidence-spine">
            {metaAgentTelemetry.map((item) => (
              <li className="lineage-row" key={`${item.agent_role}:${item.model_id}:${item.status}`}>
                <p>
                  {item.agent_role}/{item.status}：{item.model_id || item.model_name || "未记录模型"}
                </p>
                <p>
                  thinking={item.thinking || "未声明"} · mode={item.mode || "默认"} · latency={item.latency_ms ?? 0}ms
                </p>
                {item.error_message ? <p>fallback：{item.error_message}</p> : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {runView ? (
        <section aria-label="DebugRunView" className="evidence-spine">
          <h3>DebugRunView</h3>
          <p>统一状态：{runView.summary.headline}</p>
          <p>当前阶段：{runView.summary.current_phase}</p>
          <p>下一步：{runView.summary.next_step}</p>
          <p>
            自动闭环：{runView.auto_closure.status_label}｜{runView.auto_closure.summary}
          </p>
          <p>
            写回：{runView.writeback.status_label}｜{runView.writeback.row_id || "无"}
          </p>
          {debugLoop ? (
            <>
              <p>
                循环探索：第 {debugLoop.current_iteration} 轮｜{debugLoop.decision}
              </p>
              <p>循环下一步：{debugLoop.next_action || "无"}</p>
              <p>循环摘要：{debugLoop.summary}</p>
              {debugLoop.iterations.length > 0 ? (
                <ul aria-label="Debug Loop Iterations">
                  {debugLoop.iterations.map((iteration, index) => (
                    <li className="lineage-row" key={`${textValue(iteration.iteration)}:${index}`}>
                      循环轮次：第 {textValue(iteration.iteration)} 轮 / {textValue(iteration.decision)} / pending=
                      {textValue(iteration.pending_probe_count)} / completed={textValue(iteration.completed_probe_count)} /
                      supported={textValue(iteration.supported_comparison_count)}
                    </li>
                  ))}
                </ul>
              ) : null}
            </>
          ) : null}
          {hypothesisClosure ? (
            <>
              <p>
                假设闭环：{hypothesisClosure.status_label}｜{hypothesisClosure.summary}
              </p>
              <p>{hypothesisClosureCounts}</p>
              {hypothesisFairnessLock ? <p>公平性锁：{hypothesisFairnessLock}</p> : null}
              {hypothesisClosure.hypotheses.length > 0 ? (
                <ul aria-label="Hypothesis Matrix">
                  {hypothesisClosure.hypotheses.map((hypothesis, index) => (
                    <li className="lineage-row" key={`${textValue(hypothesis.hypothesis_id)}:${index}`}>
                      {textValue(hypothesis.hypothesis_id)} / {textValue(hypothesis.category)} /{" "}
                      {textValue(hypothesis.status)}：{textValue(hypothesis.claim)}
                    </li>
                  ))}
                </ul>
              ) : null}
              {hypothesisClosure.probe_plans.length > 0 ? (
                <ul aria-label="Probe Plans">
                  {hypothesisClosure.probe_plans.map((plan, index) => (
                    <li className="lineage-row" key={`${textValue(plan.probe_id)}:${index}`}>
                      {textValue(plan.probe_id)} / {textValue(plan.intervention_type)} /{" "}
                      {textValue(plan.model_runner_config_ref)}
                    </li>
                  ))}
                </ul>
              ) : null}
              {hypothesisClosure.causal_comparisons.length > 0 ? (
                <ul aria-label="Causal Comparisons">
                  {hypothesisClosure.causal_comparisons.map((comparison, index) => (
                    <li className="lineage-row" key={`${textValue(comparison.probe_id)}:${index}`}>
                      {textValue(comparison.probe_id)}：{textValue(comparison.verdict)}｜delta=
                      {textValue(comparison.delta)}
                    </li>
                  ))}
                </ul>
              ) : null}
              {hypothesisClosure.probe_results.length > 0 ? (
                <ul aria-label="Probe Results">
                  {hypothesisClosure.probe_results.map((result, index) => (
                    <li className="lineage-row" key={`${textValue(result.probe_id)}:${index}`}>
                      Probe 结果：{textValue(result.probe_id)} / {textValue(result.status)} /{" "}
                      {textValue(result.probe_job_id)}
                      {arrayText(result.evidence_ids) ? <p>Probe evidence：{arrayText(result.evidence_ids)}</p> : null}
                    </li>
                  ))}
                </ul>
              ) : null}
              {hypothesisClosure.verified_root_causes.length > 0 ? (
                <ul aria-label="Verified Root Causes">
                  {hypothesisClosure.verified_root_causes.map((item, index) => (
                    <li className="lineage-row" key={`${textValue(item.hypothesis_id)}:${index}`}>
                      已验证根因：{textValue(item.hypothesis_id)} / {textValue(item.probe_id)}：
                      {textValue(item.summary)}
                    </li>
                  ))}
                </ul>
              ) : null}
            </>
          ) : null}
          {runView.timeline.length > 0 ? (
            <ul aria-label="DebugRunView timeline">
              {runView.timeline.map((item) => (
                <li className="lineage-row" key={item.key}>
                  {item.key}：{item.status_label}｜{item.summary}
                </li>
              ))}
            </ul>
          ) : null}
          {runView.agent_traces.length > 0 ? (
            <ul aria-label="DebugRunView agent traces">
              {runView.agent_traces.map((trace, index) => (
                <li className="lineage-row" key={`${trace.agent_role}:${index}`}>
                  {trace.agent_role}：{String(trace.reasoning_summary ?? "未记录推理摘要")}
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      ) : null}
      <section aria-label="自动闭环调试">
        <h3>自动闭环调试</h3>
        {onRunAutoDebugClosure ? (
          <button type="button" aria-label="运行自动闭环调试" onClick={onRunAutoDebugClosure}>
            运行自动闭环调试
          </button>
        ) : null}
        {autoDebugClosureResult ? (
          <>
            <p>自动闭环源任务：{autoDebugClosureResult.source_job_id}</p>
            <p>自动定向深挖任务：{autoDebugClosureResult.created_targeted_probe_jobs.join(", ") || "无"}</p>
            <p>自动稳定性跟进任务：{autoDebugClosureResult.created_strategy_follow_up_jobs.join(", ") || "无"}</p>
            <p>自动闭环验证任务：{autoDebugClosureResult.created_verification_jobs.join(", ") || "无"}</p>
            <p>原始 badcase：{autoDebugClosureResult.badcase_live_comparison.original_badcase}</p>
            <p>Live 复测对比：{autoDebugClosureResult.badcase_live_comparison.live_rerun}</p>
            <p>闭环判断：{autoDebugClosureResult.badcase_live_comparison.decision}</p>
            <p>自动写回状态：{displayStatus(autoDebugClosureResult.writeback_status)}</p>
            <ul aria-label="自动最终归因候选">
              {autoDebugClosureResult.final_attribution_candidates.map((candidate) => (
                <li key={`${candidate.category}:${candidate.summary}`}>
                  {candidate.category}/{candidate.confidence}：{candidate.summary}
                </li>
              ))}
            </ul>
            {autoDebugClosureResult.targeted_probe_outcomes.length > 0 ? (
              <>
                <h4>定向深挖结果</h4>
                <ul aria-label="自动定向深挖结果" className="evidence-spine">
                  {autoDebugClosureResult.targeted_probe_outcomes.map((outcome) => (
                    <li className="lineage-row" key={`${outcome.probe_job_id}:${outcome.target_id}`}>
                      {outcome.target_id}/{outcome.outcome}：{outcome.summary}
                    </li>
                  ))}
                </ul>
              </>
            ) : null}
            {autoDebugClosureResult.evidence_summaries.length > 0 ? (
              <>
                <h4>自动闭环证据摘要</h4>
                <ul aria-label="自动闭环证据摘要" className="evidence-spine">
                  {autoDebugClosureResult.evidence_summaries.map((evidence) => (
                    <li className="lineage-row" key={`${evidence.job_id}:${evidence.evidence_id}`}>
                      <p>
                        证据 {evidence.evidence_id} / {evidence.step_name} / 得分={evidence.judge_score}
                      </p>
                      <p>任务：{evidence.job_id}</p>
                      <p>轮次：{evidence.trial}</p>
                      <p>缺失/偏差：{evidence.delta_reasons.join(", ") || "无"}</p>
                      {evidence.model_call_error ? <p>模型调用错误：{evidence.model_call_error}</p> : null}
                      {evidence.response_parse_error ? <p>解析错误：{evidence.response_parse_error}</p> : null}
                      <p>原始输出：{evidence.raw_output_excerpt}</p>
                    </li>
                  ))}
                </ul>
              </>
            ) : null}
            {autoDebugClosureMarkdown ? (
              <section aria-label="自动闭环 Markdown 报告">
                <h4>自动闭环 Markdown 报告</h4>
                {autoDebugClosureReportUrl ? (
                  <p>
                    <a href={autoDebugClosureReportUrl} target="_blank" rel="noreferrer">
                      打开自动闭环 Markdown 报告
                    </a>
                  </p>
                ) : null}
                <pre>{autoDebugClosureMarkdown}</pre>
              </section>
            ) : null}
          </>
        ) : null}
      </section>
      {experimentSummary ? (
        <>
          <h3>复测稳定性</h3>
          <p>复测稳定性：{experimentSummary.stability_label ?? "未知"}</p>
          <p>复测通过率：{formatPercent(experimentSummary.success_rate ?? 0)}</p>
          <p>
            失败次数：{failedTrialCount}/{experimentSummary.total_trials}
          </p>
        </>
      ) : null}
      {stepSummaries.length > 0 ? (
        <>
          <h3>实验轨迹</h3>
          <ul aria-label="实验步骤轨迹">
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
                  <ul aria-label={`${step.step_name} 轨迹证据`}>
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
      {judgeComparisonNotes.length > 0 ? (
        <section aria-label="Judge Comparator 辅助备注">
          <h3>Judge Comparator 辅助备注</h3>
          <ul className="evidence-spine">
            {judgeComparisonNotes.map((note) => (
              <li className="lineage-row" key={`${note.evidence_id}:${note.target_id}:${note.risk}`}>
                <p>证据：{note.evidence_id || "未指定"}</p>
                <p>目标：{note.target_id || "global"}</p>
                <p>规则原因：{note.deterministic_reason || "无"}</p>
                <p>模型辅助备注：{note.llm_note}</p>
                <p>风险：{note.risk}</p>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {ablationConclusion ? (
        <section aria-label="消融诊断">
          <h3>消融诊断</h3>
          <p>{ablationConclusion}</p>
        </section>
      ) : null}
      {evaluationAssetDiagnostics.length > 0 ? (
        <>
          <h3>评估资产诊断</h3>
          <ul aria-label="评估资产诊断" className="evidence-spine">
            {evaluationAssetDiagnostics.map((diagnostic) => (
              <li className="lineage-row" key={`${diagnostic.source}:${diagnostic.status}:${diagnostic.summary}`}>
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
          <h3>根因追踪</h3>
          <ul aria-label="根因追踪" className="evidence-spine">
            {rootCauseTrace.map((trace) => (
              <li className="lineage-row" key={`${trace.evidence_id}:${trace.variant}`}>
                <p>步骤：{trace.step_name}</p>
                <p>变体：{trace.variant}</p>
                <p>模态：{trace.modalities.length > 0 ? trace.modalities.join(", ") : "无"}</p>
                <p>证据：{trace.evidence_id}</p>
                <p>判分得分：{trace.judge_score}</p>
                <p>缺失/偏差：{trace.delta_reasons.length > 0 ? trace.delta_reasons.join(", ") : "无"}</p>
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
      {actionQueue.length > 0 ? (
        <>
          <h3>Action Queue</h3>
          <ul aria-label="Action Queue" className="action-console">
            {actionQueue.map((item) => {
              const actionIndex = actionQueueRecommendedIndex(item.id);
              return (
                <li className="lineage-row" key={item.id}>
                  <p>{`${item.priority} / ${item.state_label}：${item.title}`}</p>
                  {item.detail ? <p>{item.detail}</p> : null}
                  <p>负责人：{item.owner}</p>
                  <p>状态：{displayStatus(item.status)}</p>
                  <p>来源：{item.source} / {item.source_ref}</p>
                  {item.verification_job_id ? (
                    <p>
                      验证任务：{item.verification_job_id} / {item.verification_result || "pending"}
                    </p>
                  ) : null}
                  <p>
                    写回：{item.writeback_status}
                    {item.writeback_row_id ? ` / ${item.writeback_row_id}` : ""}
                  </p>
                  {item.verification_summary ? <p>验证摘要：{item.verification_summary}</p> : null}
                  {item.next_operation ? <p>下一步：{item.next_operation}</p> : null}
                  <CitationCoverage
                    artifactIds={item.artifact_ids}
                    evidenceIds={item.evidence_ids}
                    traceRefs={item.trace_refs}
                  />
                  {actionIndex !== null && onUpdateRecommendedActionStatus ? (
                    <p className="action-buttons">
                      <button
                        type="button"
                        aria-label={`接受 Action Queue 动作 ${actionIndex + 1}`}
                        onClick={() => onUpdateRecommendedActionStatus(actionIndex, "accepted")}
                      >
                        接受动作 {actionIndex + 1}
                      </button>
                      <button
                        type="button"
                        aria-label={`转人工处理 Action Queue 动作 ${actionIndex + 1}`}
                        onClick={() => onUpdateRecommendedActionStatus(actionIndex, "rejected")}
                      >
                        转人工 {actionIndex + 1}
                      </button>
                    </p>
                  ) : null}
                  {actionIndex !== null && onVerifyRecommendedAction && item.available_operations.includes("verify") ? (
                    <p>
                      <button
                        type="button"
                        aria-label={`验证 Action Queue 动作 ${actionIndex + 1}`}
                        onClick={() => onVerifyRecommendedAction(actionIndex)}
                      >
                        验证动作 {actionIndex + 1}
                      </button>
                    </p>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </>
      ) : null}
      {recommendedActions.length > 0 ? (
        <>
          <h3>建议操作</h3>
          <ul aria-label="建议操作" className="action-console">
            {recommendedActions.map((action, actionIndex) => (
              <li className="lineage-row" key={`${action.category}:${action.summary}`}>
                <p>
                  {action.category}/{action.priority}：{action.summary}
                </p>
                <p>状态：{displayStatus(action.status ?? "pending")}</p>
                <p>{action.detail}</p>
                <CitationCoverage
                  artifactIds={action.artifact_ids}
                  evidenceIds={action.evidence_ids}
                  traceRefs={action.trace_refs}
                />
                {onUpdateRecommendedActionStatus ? (
                  <p className="action-buttons">
                    <button
                      type="button"
                      aria-label={`接受建议操作 ${actionIndex + 1}`}
                      onClick={() => onUpdateRecommendedActionStatus(actionIndex, "accepted")}
                    >
                      接受建议操作 {actionIndex + 1}
                    </button>
                    <button
                      type="button"
                      aria-label={`拒绝建议操作 ${actionIndex + 1}`}
                      onClick={() => onUpdateRecommendedActionStatus(actionIndex, "rejected")}
                    >
                      拒绝建议操作 {actionIndex + 1}
                    </button>
                    <button
                      type="button"
                      aria-label={`标记建议操作 ${actionIndex + 1} 已应用`}
                      onClick={() => onUpdateRecommendedActionStatus(actionIndex, "applied")}
                    >
                      标记已应用 {actionIndex + 1}
                    </button>
                  </p>
                ) : null}
                {onVerifyRecommendedAction && action.status === "applied" ? (
                  <p>
                    <button
                      type="button"
                      aria-label={`验证建议操作 ${actionIndex + 1}`}
                      onClick={() => onVerifyRecommendedAction(actionIndex)}
                    >
                      验证建议操作 {actionIndex + 1}
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
          <h3>调试策略</h3>
          <ul aria-label="调试策略" className="evidence-spine">
            {debugStrategy.map((strategy) => (
              <li className="lineage-row" key={`${strategy.stage}:${strategy.objective}`}>
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
          <h3>跟进实验</h3>
          <ul aria-label="跟进实验" className="evidence-spine">
            {followUpExperiments.map((followUp) => (
              <li
                className="lineage-row"
                key={`${followUp.source}:${followUp.stage ?? followUp.verification_job_id ?? followUp.planned_steps}`}
              >
                <p>
                  {followUp.source}/{followUp.stage ?? followUp.result ?? "unknown"}：{followUp.planned_steps}
                </p>
                <p>{followUp.summary}</p>
                {followUp.stop_condition ? <p>停止条件：{followUp.stop_condition}</p> : null}
                {onCreateStrategyFollowUp && isRunnableStrategyFollowUp(followUp.source) && followUp.stage ? (
                  <p>
                    <button
                      type="button"
                      aria-label={`运行策略跟进 ${followUp.stage}`}
                      onClick={() => onCreateStrategyFollowUp(followUp.stage!)}
                    >
                      运行策略跟进 {followUp.stage}
                    </button>
                  </p>
                ) : null}
                {onCreateTargetedProbe && isRunnableTargetedProbeFollowUp(followUp.source) && followUp.target_id ? (
                  <p>
                    <button
                      type="button"
                      aria-label={`运行定向深挖 ${followUp.target_id}`}
                      onClick={() => onCreateTargetedProbe(followUp.target_id!)}
                    >
                      运行定向深挖 {followUp.target_id}
                    </button>
                  </p>
                ) : null}
                {onCreateFinalAttributionFollowUp && followUp.source === "final_attribution" && followUp.target_id ? (
                  <p>
                    <button
                      type="button"
                      aria-label={`运行最终归因跟进 ${followUp.target_id}`}
                      onClick={() => onCreateFinalAttributionFollowUp(followUp.target_id!)}
                    >
                      运行最终归因跟进 {followUp.target_id}
                    </button>
                  </p>
                ) : null}
                {onCreateFinalAttributionRecovery &&
                followUp.source === "final_attribution_verification_outcome" &&
                followUp.target_id ? (
                  <p>
                    <button
                      type="button"
                      aria-label={`运行最终归因恢复 ${followUp.target_id}`}
                      onClick={() => onCreateFinalAttributionRecovery(followUp.target_id!)}
                    >
                      运行最终归因恢复 {followUp.target_id}
                    </button>
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {humanHandoffRequests.length > 0 ? (
        <>
          <h3>人工接管请求</h3>
          <ul aria-label="人工接管请求" className="action-console">
            {humanHandoffRequests.map((request) => (
              <li className="lineage-row" key={`${request.source}:${request.target_id}:${request.reason}`}>
                <p>接管目标：{request.target_id}</p>
                <p>接管优先级：{request.priority}</p>
                <p>接管理由：{request.reason}</p>
                <p>接管状态：{displayStatus(humanHandoffStatusByTargetId.get(request.target_id)?.status ?? "pending")}</p>
                <p>接管处理人：{humanHandoffStatusByTargetId.get(request.target_id)?.actor || "未分配"}</p>
                <p>接管备注：{humanHandoffStatusByTargetId.get(request.target_id)?.note || "无"}</p>
                <p>{request.summary}</p>
                <p>建议负责人：{request.recommended_owner}</p>
                <p>下一步动作：{request.next_action}</p>
                {onUpdateHumanHandoffStatus ? (
                  <p>
                    <button
                      type="button"
                      aria-label={`确认接管 ${request.target_id}`}
                      onClick={() => onUpdateHumanHandoffStatus(request.target_id, "acknowledged")}
                    >
                      确认接管 {request.target_id}
                    </button>
                    <button
                      type="button"
                      aria-label={`开始接管 ${request.target_id}`}
                      onClick={() => onUpdateHumanHandoffStatus(request.target_id, "in_progress")}
                    >
                      开始接管 {request.target_id}
                    </button>
                    <button
                      type="button"
                      aria-label={`完成接管 ${request.target_id}`}
                      onClick={() => onUpdateHumanHandoffStatus(request.target_id, "resolved")}
                    >
                      完成接管 {request.target_id}
                    </button>
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {finalAttributions.length > 0 ? (
        <>
          <h3>最终归因</h3>
          <ul aria-label="最终归因" className="evidence-spine">
            {finalAttributions.map((attribution) => (
              <li className="lineage-row" key={`${attribution.source}:${attribution.target_id}:${attribution.category}`}>
                <p>归因目标：{attribution.target_id}</p>
                <p>归因类别：{attribution.category}</p>
                <p>归因状态：{displayStatus(attribution.status)}</p>
                <p>归因操作者：{attribution.actor || "未知"}</p>
                <p>{attribution.summary}</p>
                <p>归因建议：{attribution.recommended_action}</p>
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {finalAttributionVerificationResults.length > 0 ? (
        <>
          <h3>最终归因验证结果</h3>
          <ul aria-label="最终归因验证结果" className="evidence-spine">
            {finalAttributionVerificationResults.map((result) => (
              <li className="lineage-row" key={`${result.target_id}:${result.verification_job_id}`}>
                <p>归因验证目标：{result.target_id}</p>
                <p>归因验证类别：{result.category}</p>
                <p>归因验证结果：{displayStatus(result.result)}</p>
                <p>归因验证任务：{result.verification_job_id}</p>
                <p>归因验证通过率：{formatPercent(result.success_rate)}</p>
                <p>{result.summary}</p>
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {confidenceReasons.length > 0 ? (
        <>
          <h3>置信度理由</h3>
          <ul aria-label="置信度理由" className="evidence-spine">
            {confidenceReasons.map((reason) => (
              <li className="lineage-row" key={`${reason.source}:${reason.level}:${reason.summary}`}>
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
          <h3>建议操作状态事件</h3>
          <ul aria-label="建议操作状态事件" className="evidence-spine">
            {recommendedActionStatusEvents.map((event) => (
              <li className="lineage-row" key={event.event_id}>
                <p>
                  操作 {event.action_index + 1}：{displayStatus(event.status)}
                </p>
                <p>操作者：{event.actor || "未知"}</p>
                {event.note ? <p>备注：{event.note}</p> : null}
                <p>时间：{event.created_at}</p>
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {recommendedActionVerifications.length > 0 ? (
        <>
          <h3>建议操作验证任务</h3>
          <ul aria-label="建议操作验证任务" className="evidence-spine">
            {recommendedActionVerifications.map((verification) => (
              <li className="lineage-row" key={`${verification.action_index}:${verification.verification_job_id}`}>
                <p>
                  操作 {verification.action_index + 1} 验证任务：{verification.verification_job_id}
                </p>
                <p>操作者：{verification.actor || "未知"}</p>
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
      {finalAttributionRecoveryResults.length > 0 ? (
        <>
          <h3>最终归因恢复结果</h3>
          <ul aria-label="最终归因恢复结果" className="evidence-spine">
            {finalAttributionRecoveryResults.map((result) => (
              <li className="lineage-row" key={`${result.target_id}:${result.recovery_job_id}`}>
                <p>归因恢复目标：{result.target_id}</p>
                <p>归因恢复类别：{result.category}</p>
                <p>归因恢复结果：{displayStatus(result.result)}</p>
                <p>归因恢复任务：{result.recovery_job_id}</p>
                <p>归因恢复通过率：{formatPercent(result.success_rate)}</p>
                <p>{result.summary}</p>
              </li>
            ))}
          </ul>
        </>
      ) : null}
      <h3>证据产物</h3>
      <p>证据产物：{artifactIds.length}</p>
      {artifactIds.length > 0 ? (
        <ul aria-label="证据产物列表" className="evidence-spine">
          {artifactIds.map((artifactId) => {
            const evidenceId = artifactEvidenceIdByArtifactId.get(artifactId);
            return (
              <li className="lineage-row" key={artifactId}>
                {onSelectEvidence && evidenceId ? (
                  <button type="button" aria-label={`打开证据产物 ${artifactId}`} onClick={() => onSelectEvidence(evidenceId)}>
                    打开证据产物 {artifactId}
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
          <h3>证据引用</h3>
          <ul className="evidence-spine">
            {evidenceCitations.map((citation) => (
              <li className="lineage-row" key={`${citation.evidence_id}:${citation.box_id ?? "global"}:${citation.reason}`}>
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

function displayStatus(status: string): string {
  const labels: Record<string, string> = {
    accepted: "已接受",
    acknowledged: "已确认",
    applied: "已应用",
    failed: "失败",
    in_progress: "进行中",
    pending: "待处理",
    rejected: "已拒绝",
    resolved: "已解决",
    closed: "已关闭",
    skipped: "跳过",
    succeeded: "成功"
  };
  return labels[status] ?? status;
}

function actionQueueRecommendedIndex(itemId: string) {
  if (!itemId.startsWith("recommended:")) {
    return null;
  }
  const rawIndex = Number.parseInt(itemId.slice("recommended:".length), 10);
  return Number.isNaN(rawIndex) ? null : rawIndex;
}

type MetaAgentTelemetry = {
  agent_role: string;
  status: string;
  model_id: string;
  model_name: string;
  mode: string;
  thinking: string;
  latency_ms: number;
  error_message: string;
};

function metaTelemetry(enrichment?: Record<string, unknown>): MetaAgentTelemetry[] {
  const telemetry = enrichment?.telemetry;
  if (!Array.isArray(telemetry)) {
    return [];
  }
  return telemetry.filter(isRecord).map((item) => ({
    agent_role: stringValue(item.agent_role),
    status: stringValue(item.status),
    model_id: stringValue(item.model_id),
    model_name: stringValue(item.model_name),
    mode: stringValue(item.mode),
    thinking: stringValue(item.thinking),
    latency_ms: numberValue(item.latency_ms),
    error_message: stringValue(item.error_message)
  }));
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringValue(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function textValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "";
  }
  return String(value);
}

function arrayText(value: unknown): string {
  return Array.isArray(value) ? value.map((item) => String(item)).join(", ") : "";
}

function numberValue(value: unknown): number {
  return typeof value === "number" ? value : 0;
}

type VerificationResultSummaryProps = {
  result: RecommendedActionVerificationResult;
};

function VerificationResultSummary({ result }: VerificationResultSummaryProps) {
  return (
    <>
      <p>验证结果：{displayStatus(result.result)}</p>
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

function isRunnableTargetedProbeFollowUp(source: string) {
  return source === "targeted_probe" || source === "targeted_probe_outcome";
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
    <ul aria-label={`${evidenceId} 证据产物链接`}>
      {artifactIds.map((artifactId) => (
        <li key={artifactId}>
          <button type="button" onClick={() => onSelectEvidence(evidenceId)}>
            打开证据产物 {artifactId}
          </button>
        </li>
      ))}
    </ul>
  );
}
