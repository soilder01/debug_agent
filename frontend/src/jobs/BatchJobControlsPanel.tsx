type BatchJobControlsPanelProps = {
  caseIds: string;
  onCaseIdsChange: (value: string) => void;
  onSubmit: () => void;
  onLoadJobs: (status?: string, sort?: string) => void;
  showHeading?: boolean;
};

export function BatchJobControlsPanel({
  caseIds,
  onCaseIdsChange,
  onSubmit,
  onLoadJobs,
  showHeading = true
}: BatchJobControlsPanelProps) {
  return (
    <div className="batch-job-command">
      {showHeading ? <h2>批量调试任务</h2> : null}
      <p className="batch-job-command__guide">
        不知道样本 ID？先去“数据导入”加载样本，或在“回写同步”按飞书行号重跑。
      </p>
      <label htmlFor="batch-case-ids">批量样本 ID</label>
      <p className="batch-job-command__hint">一行一个 case_id，例如 JSZN-096。也可以从已导入样本列表一键填充。</p>
      <textarea
        id="batch-case-ids"
        aria-label="批量样本 ID"
        value={caseIds}
        placeholder={"JSZN-096\nJSZN-049\nJSZN-008"}
        onChange={(event) => onCaseIdsChange(event.target.value)}
      />
      <p className="batch-job-command__hint">
        默认使用当前 Agent 模型路由；需要改模型时，到“操作监控”的 agent 机器人卡片里点“查看配置”。
      </p>
      <div className="batch-job-command__actions">
        <button type="button" onClick={onSubmit}>
          批量提交调试
        </button>
        <button type="button" onClick={() => onLoadJobs(undefined, undefined)}>
          查看历史任务
        </button>
        <button type="button" onClick={() => onLoadJobs("failed", undefined)}>
          查看失败任务
        </button>
        <button type="button" onClick={() => onLoadJobs(undefined, "created_at_desc")}>
          查看最新任务
        </button>
      </div>
    </div>
  );
}
