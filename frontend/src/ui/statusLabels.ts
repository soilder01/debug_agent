const STATUS_LABELS: Record<string, string> = {
  acknowledged: "已确认",
  closed: "已关闭",
  completed: "已完成",
  created: "已创建",
  critical: "严重",
  degraded: "降级",
  healthy: "健康",
  failed: "失败",
  ok: "正常",
  inconclusive: "结论不确定",
  in_progress: "处理中",
  info: "提示",
  not_configured: "未配置",
  not_resolved: "未解决",
  over_budget: "超预算",
  pending: "待处理",
  regressed: "回归失败",
  reopen: "重新开启",
  resolved: "已解决",
  running: "运行中",
  skipped: "已跳过",
  stopped: "已停止",
  succeeded: "已成功",
  success: "成功",
  warning: "警告",
  within_budget: "预算内",
  wont_fix: "不处理"
};

export function displayStatus(status: string | null | undefined): string {
  if (!status) {
    return "未声明";
  }
  return STATUS_LABELS[status] ?? status;
}

export function displayEnabled(value: boolean): string {
  return value ? "开启" : "关闭";
}
