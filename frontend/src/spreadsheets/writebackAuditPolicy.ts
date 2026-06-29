export function canRetryWritebackAudit(status: string): boolean {
  return status === "failed";
}

export function writebackRetryReason(status: string, errorMessage: string): string {
  if (status === "failed") {
    return errorMessage ? `上次写回失败：${errorMessage}` : "上次写回失败";
  }
  if (status === "succeeded") {
    return "已经写回成功";
  }
  if (status === "skipped") {
    return errorMessage ? `跳过原因：${errorMessage}` : "缺少写回前置条件";
  }
  return errorMessage ? `未知状态：${errorMessage}` : "未知写回状态";
}
