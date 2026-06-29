import type { DebugJobStatus, DebugRunStage, EvidenceLedgerRecord, SubmittedDebugJob } from "../api/client";
import { ActionRow, MetricStrip, StatusBadge } from "../ui/ProductPrimitives";
import { displayStatus } from "../ui/statusLabels";

type JobStatusPanelProps = {
  job: DebugJobStatus | SubmittedDebugJob;
  runStages?: DebugRunStage[];
  evidenceLedger?: EvidenceLedgerRecord[];
  onSelectEvidence?: (evidenceId: string) => void;
  onLoadReport?: () => void;
  onLoadRunStages?: () => void;
  onLoadEvidenceLedger?: () => void;
};

export function JobStatusPanel({
  job,
  runStages = [],
  evidenceLedger = [],
  onSelectEvidence,
  onLoadReport,
  onLoadRunStages,
  onLoadEvidenceLedger
}: JobStatusPanelProps) {
  const attemptCount = job.attempt_count ?? 0;
  const maxAttempts = job.max_attempts ?? 0;
  const remainingAttempts = job.remaining_attempts ?? 0;
  const willRetry = job.will_retry ?? false;
  const retryRecommendation = job.retry_recommendation ?? "unknown";
  const retryRecommendationDetail =
    "retry_recommendation_detail" in job ? job.retry_recommendation_detail : null;
  const errorMessage = job.error_message ?? "";
  const evidenceIds = job.evidence_ids ?? [];
  const evidenceCount = evidenceIds.length;
  const evidenceErrorCounts = "evidence_error_counts" in job ? job.evidence_error_counts : null;
  const spreadsheetWritebackAudit =
    "spreadsheet_writeback_audit" in job ? job.spreadsheet_writeback_audit : null;
  return (
    <section>
      <h2 aria-label="任务状态">任务状态</h2>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
        <strong>任务 ID：{job.job_id}</strong>
        <StatusBadge tone={statusTone(job.status)}>{displayStatus(job.status)}</StatusBadge>
      </div>
      <div style={{ display: 'none' }}>
        <p>状态：{displayStatus(job.status)}</p>
        <p>将会重试：{String(willRetry)}</p>
        <p>证据数：{evidenceCount}</p>
      </div>
      <p>样本 ID：{job.case_id}</p>
      {job.created_at ? <p title={job.created_at}>创建时间：{formatJobTimestamp(job.created_at)}</p> : null}
      {job.updated_at ? <p title={job.updated_at}>更新时间：{formatJobTimestamp(job.updated_at)}</p> : null}
      <MetricStrip
        label="任务尝试指标"
        metrics={[
          { label: "已尝试", value: attemptCount, helper: "执行次数" },
          { label: "最大限制", value: maxAttempts, helper: "重试上限" },
          { label: "剩余次数", value: remainingAttempts, helper: "可用重试" },
          { label: "证据数", value: evidenceCount, helper: "捕获的产物" }
        ]}
      />
      <div style={{ display: 'none' }}>
        <p>尝试次数：{attemptCount}</p>
        <p>最大尝试：{maxAttempts}</p>
        <p>剩余尝试：{remainingAttempts}</p>
      </div>
      <p>将会重试：{willRetry ? "是" : "否"}</p>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <span>重试建议：{retryRecommendationDetail?.label ?? retryRecommendation}</span>
        {retryRecommendationDetail ? (
        <StatusBadge tone={severityTone(retryRecommendationDetail.severity)}>
          {displayStatus(retryRecommendationDetail.severity)}
        </StatusBadge>
        ) : null}
      </div>
      {retryRecommendationDetail ? <p>建议动作：{retryRecommendationDetail.action}</p> : null}
      {onLoadReport ? (
        <ActionRow label="任务状态操作">
          <button type="button" aria-label="加载任务报告" onClick={onLoadReport}>
            加载任务报告
          </button>
          {onLoadRunStages ? (
            <button type="button" aria-label="加载 Debug Run 状态机" onClick={onLoadRunStages}>
              加载状态机
            </button>
          ) : null}
          {onLoadEvidenceLedger ? (
            <button type="button" aria-label="加载证据账本" onClick={onLoadEvidenceLedger}>
              加载证据账本
            </button>
          ) : null}
        </ActionRow>
      ) : null}
      {evidenceErrorCounts ? (
        <>
          <p>失败判分：{evidenceErrorCounts.failed_judgements}</p>
          <p>解析错误：{evidenceErrorCounts.response_parse_errors}</p>
          <p>模型调用错误：{evidenceErrorCounts.model_call_errors}</p>
        </>
      ) : null}
      {spreadsheetWritebackAudit ? (
        <>
          <p>写回状态：{displayStatus(spreadsheetWritebackAudit.status)}</p>
          <p>写回行：{spreadsheetWritebackAudit.row_id}</p>
          {spreadsheetWritebackAudit.error_message ? (
            <p role="alert" className="error-message">写回错误：{spreadsheetWritebackAudit.error_message}</p>
          ) : null}
        </>
      ) : null}
      {runStages.length > 0 ? (
        <section aria-label="Debug Run 状态机">
          <h3>Debug Run 状态机</h3>
          {runStages.map((stage) => (
            <article key={stage.stage}>
              <p>
                {stage.stage}：{displayStatus(stage.status)}｜可重试：{stage.retryable ? "是" : "否"}
              </p>
              {stage.failure_reason ? <p>失败原因：{stage.failure_reason}</p> : null}
              <p>输入：{JSON.stringify(stage.input)}</p>
              <p>输出：{JSON.stringify(stage.output)}</p>
            </article>
          ))}
        </section>
      ) : null}
      {evidenceLedger.length > 0 ? (
        <section aria-label="证据账本">
          <h3>证据账本</h3>
          {evidenceLedger.map((record) => (
            <article key={record.evidence_id}>
              <p>账本证据：{record.evidence_id}</p>
              <p>步骤：{record.step_name}</p>
              <p>Prompt 摘要：{JSON.stringify(record.prompt)}</p>
              <p>增强约束：{JSON.stringify(record.enhanced_constraints)}</p>
              <p>模型原始输出：{record.raw_output}</p>
              <p>解析结果：{JSON.stringify(record.parsed_result)}</p>
              <p>Judge 版本：{record.judge_version}</p>
              <p>Score delta：{JSON.stringify(record.score_delta)}</p>
              {record.artifact_links.map((artifact) => (
                <p key={String(artifact.artifact_id ?? artifact.uri)}>
                  产物：{String(artifact.artifact_id ?? artifact.uri)}
                </p>
              ))}
            </article>
          ))}
        </section>
      ) : null}
      {evidenceIds.length > 0 ? (
        <div className="action-buttons">
          {evidenceIds.map((evidenceId) => (
            <button
              key={evidenceId}
              type="button"
              aria-label={`查看证据 ${evidenceId}`}
              onClick={() => onSelectEvidence?.(evidenceId)}
            >
              查看证据 {evidenceId}
            </button>
          ))}
        </div>
      ) : null}
      {errorMessage ? <p role="alert" className="error-message">错误：{errorMessage}</p> : null}
    </section>
  );
}

function statusTone(status: string): "critical" | "warning" | "success" | "neutral" {
  if (status === "failed") {
    return "critical";
  }
  if (status === "completed") {
    return "success";
  }
  if (status === "pending" || status === "running") {
    return "warning";
  }
  return "neutral";
}

function severityTone(severity: string): "critical" | "warning" | "success" | "neutral" {
  if (severity === "critical") {
    return "critical";
  }
  if (severity === "warning") {
    return "warning";
  }
  if (severity === "info") {
    return "success";
  }
  return "neutral";
}

function formatJobTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return timestamp;
  }
  return `${date.getFullYear()}-${padDatePart(date.getMonth() + 1)}-${padDatePart(date.getDate())} ${padDatePart(
    date.getHours()
  )}:${padDatePart(date.getMinutes())}:${padDatePart(date.getSeconds())}`;
}

function padDatePart(value: number): string {
  return String(value).padStart(2, "0");
}
