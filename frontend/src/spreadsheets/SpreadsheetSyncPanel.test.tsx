import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type {
  LarkAuthSession,
  LarkOperationAuditListResponse,
  LarkScopeCheckResponse,
  LarkSpreadsheetStatus,
  SpreadsheetSyncResponse,
  SpreadsheetWritebackAudit,
  SpreadsheetWritebackAuditCounts,
  SpreadsheetWritebackAuditListResponse,
  SpreadsheetWritebackResult
} from "../api/client";
import { SpreadsheetSyncPanel } from "./SpreadsheetSyncPanel";

afterEach(() => {
  vi.restoreAllMocks();
});

function makeLarkStatus(): LarkSpreadsheetStatus {
  return {
    configured: true,
    spreadsheet_id: "spreadsheet-1",
    sheet_id: "sheet-1",
    lark_cli_timeout_seconds: 60,
    connectivity_status: "ok",
    error_message: ""
  };
}

function makeSyncResult(): SpreadsheetSyncResponse {
  return {
    imported_case_ids: ["case-1"],
    imported_rows: [{ sheet_row_id: "7", case_id: "case-1" }],
    jobs: [{ job_id: "job-sheet-1", case_id: "case-1", status: "created" }],
    rejected_rows: []
  };
}

function makeAudit(): SpreadsheetWritebackAudit {
  return {
    job_id: "job-1",
    status: "failed",
    row_id: "7",
    report_url: "https://debug-agent.local/reports/job-1",
    fields: { 错误原因: "model_weakness" },
    error_message: "permission denied",
    created_at: "2026-06-12T06:00:00+00:00",
    updated_at: "2026-06-12T06:00:01+00:00"
  };
}

function makeLarkOperationAuditList(): LarkOperationAuditListResponse {
  return {
    audits: [
      {
        audit_id: 1,
        actor: "local-dev-operator",
        connector_mode: "cli",
        identity: "bot",
        profile: "debug-bot",
        service: "sheets",
        operation: "+csv-get",
        status: "failed",
        context: "+csv-get --spreadsheet-token sheet --sheet-id tab",
        error_type: "permission_denied",
        hint: "run lark-cli auth login",
        permission_scopes: ["sheets:spreadsheet:readonly"],
        console_url: "https://open.feishu.cn/app",
        risk_action: "",
        duration_ms: 12,
        created_at: "2026-06-22T00:00:00+00:00"
      }
    ],
    total_count: 2
  };
}

function makeLarkScopeCheck(): LarkScopeCheckResponse {
  return {
    connector_mode: "cli",
    connector_identity: "bot",
    connector_profile: "debug-bot",
    auth_check_status: "not_verified",
    recent_missing_scopes: ["sheets:spreadsheet:readonly"],
    console_url: "https://open.larkoffice.com/app?lang=zh-CN",
    repair_steps: ["确认应用至少具备这些 scope：sheets:spreadsheet:readonly。"],
    requirements: [
      {
        service: "sheets",
        operation: "+csv-get",
        required_scopes: ["sheets:spreadsheet:readonly"],
        risk_level: "read",
        identity: "bot",
        confirmation_required: false,
        repair_hint: "在飞书开放平台为应用开通电子表格读取权限。",
        console_url: "https://open.larkoffice.com/app?lang=zh-CN",
        status: "missing_recently",
        recent_missing_scopes: ["sheets:spreadsheet:readonly"],
        recent_failure_count: 1
      }
    ]
  };
}

function makeLarkAuthSession(): LarkAuthSession {
  return {
    auth_session_id: "auth-1",
    actor: "local-dev-operator",
    identity: "user",
    profile: "debug-user",
    scopes: ["sheets:spreadsheet:readonly"],
    state: "state-1",
    auth_url: "https://open.larkoffice.com/app?debug_agent_auth=1",
    redirect_url: "",
    status: "pending",
    note: "need user auth",
    created_at: "2026-06-22T00:00:00+00:00",
    expires_at: "2026-06-22T00:30:00+00:00",
    completed_at: "",
    completed_by: ""
  };
}

describe("SpreadsheetSyncPanel", () => {
  it("renders spreadsheet workspace sections and delegates actions", async () => {
    vi.spyOn(window, "matchMedia").mockReturnValue({ matches: true } as MediaQueryList);
    const audit = makeAudit();
    const summary: SpreadsheetWritebackAuditCounts = {
      by_status: { failed: 1, skipped: 2, succeeded: 3 },
      total_count: 6
    };
    const auditList: SpreadsheetWritebackAuditListResponse = {
      audits: [audit],
      total_count: 2
    };
    const writebackResult: SpreadsheetWritebackResult = {
      row_id: "7",
      fields: { 错误原因: "model_weakness" }
    };
    const onSyncSpreadsheet = vi.fn();
    const onRerunSpreadsheetRows = vi.fn();
    const onRerunAutoClosureChange = vi.fn();
    const onRerunWritebackChange = vi.fn();
    const onLoadWritebackAudits = vi.fn();
    const onLoadLarkOperationAudits = vi.fn();
    const onCheckLarkScopes = vi.fn();
    const onCreateLarkAuthSession = vi.fn();
    const onCompleteLarkAuthSession = vi.fn();
    const onOpenAuditJob = vi.fn();
    const onRetryAudit = vi.fn();
    const onLoadMoreWritebackAudits = vi.fn();
    const onLoadMoreLarkOperationAudits = vi.fn();

    render(
      <SpreadsheetSyncPanel
        spreadsheetUrl="https://example.larkoffice.com/sheets/spreadsheet-1?sheet=sheet-1"
        spreadsheetId="spreadsheet-1"
        sheetId="sheet-1"
        larkSpreadsheetStatus={makeLarkStatus()}
        syncResult={makeSyncResult()}
        writebackAuditSummary={summary}
        writebackAuditList={auditList}
        activeWritebackAuditStatus="failed"
        larkOperationAuditList={makeLarkOperationAuditList()}
        activeLarkOperationAuditStatus="failed"
        larkScopeCheck={makeLarkScopeCheck()}
        larkAuthSession={makeLarkAuthSession()}
        writebackResult={writebackResult}
        batchExportHref="/api/exports/debug-jobs.zip?job_ids=job-sheet-1"
        onSpreadsheetUrlChange={vi.fn()}
        onSpreadsheetIdChange={vi.fn()}
        onSheetIdChange={vi.fn()}
        onUseSpreadsheetUrl={vi.fn()}
        onCheckLarkStatus={vi.fn()}
        onSyncSpreadsheet={onSyncSpreadsheet}
        rerunRowIds="2,3"
        rerunAutoClosure={true}
        rerunWriteback={true}
        onRerunRowIdsChange={vi.fn()}
        onRerunAutoClosureChange={onRerunAutoClosureChange}
        onRerunWritebackChange={onRerunWritebackChange}
        onRerunSpreadsheetRows={onRerunSpreadsheetRows}
        onLoadWritebackAuditSummary={vi.fn()}
        onLoadWritebackAudits={onLoadWritebackAudits}
        onLoadLarkOperationAudits={onLoadLarkOperationAudits}
        onCheckLarkScopes={onCheckLarkScopes}
        onCreateLarkAuthSession={onCreateLarkAuthSession}
        onCompleteLarkAuthSession={onCompleteLarkAuthSession}
        onOpenAuditJob={onOpenAuditJob}
        onRetryAudit={onRetryAudit}
        onLoadMoreWritebackAudits={onLoadMoreWritebackAudits}
        onLoadMoreLarkOperationAudits={onLoadMoreLarkOperationAudits}
      />
    );

    expect(screen.getByRole("heading", { name: "飞书表格同步" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "飞书表格同步" })).toHaveClass("spreadsheet-operations");
    expect(screen.getByRole("region", { name: "回写同步操作舱" })).toHaveClass("writeback-command-center");
    expect(screen.getByRole("region", { name: "回写调度小队" })).toHaveAttribute("data-writeback-mood", "alert");
    expect(screen.getByText("审计警戒")).toBeInTheDocument();
    expect(screen.getByLabelText("调度小人-连接员")).toHaveAttribute("data-worker-expression", "smile");
    expect(screen.getByLabelText("调度小人-搬运员")).toHaveAttribute("data-worker-expression", "smile");
    expect(screen.getByLabelText("调度小人-审计员")).toHaveAttribute("data-worker-expression", "concern");
    expect(screen.getByText("连接")).toBeInTheDocument();
    expect(screen.getByText("同步")).toBeInTheDocument();
    expect(screen.getByText("重跑")).toBeInTheDocument();
    expect(screen.getByText("审计")).toBeInTheDocument();
    expect(screen.getByText("Lark 连接状态：正常")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "下载本次飞书任务包" })).toHaveAttribute(
      "href",
      "/api/exports/debug-jobs.zip?job_ids=job-sheet-1"
    );
    expect(screen.getByText("表格同步样本：1")).toBeInTheDocument();
    expect(screen.getByText("表格同步任务：1")).toBeInTheDocument();
    const auditDrawer = screen.getByRole("complementary", { name: "审计预览" });
    expect(auditDrawer).toHaveClass("writeback-audit-drawer");
    expect(within(auditDrawer).getByText("审计总数：6")).toBeInTheDocument();
    expect(within(auditDrawer).getAllByText("当前筛选：失败").length).toBeGreaterThan(0);
    expect(within(auditDrawer).getByText("最近重试写回行：7")).toBeInTheDocument();
    const operationDrawer = screen.getByRole("complementary", { name: "Lark 操作审计" });
    expect(operationDrawer).toHaveClass("writeback-audit-drawer");
    expect(within(operationDrawer).getByText("Lark 操作审计总数：2")).toBeInTheDocument();
    expect(within(operationDrawer).getByText("缺少权限：sheets:spreadsheet:readonly")).toBeInTheDocument();
    expect(screen.getByText("Lark 权限检查：未直接验证授权状态")).toBeInTheDocument();
    expect(screen.getByText("sheets +csv-get：最近失败审计显示缺失")).toBeInTheDocument();
    expect(screen.getByText("Lark 授权会话：待授权")).toBeInTheDocument();
    expect(screen.getByText("授权 scope：sheets:spreadsheet:readonly")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "同步表格行" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "启用自动闭环" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "写回重跑结果" }));
    fireEvent.click(screen.getByRole("button", { name: "重跑选中表格行" }));
    fireEvent.click(screen.getByRole("button", { name: "查看失败审计" }));
    fireEvent.click(screen.getByRole("button", { name: "查看 Lark 操作审计" }));
    fireEvent.click(screen.getByRole("button", { name: "查看失败 Lark 操作" }));
    fireEvent.click(screen.getByRole("button", { name: "检查 Lark 权限需求" }));
    fireEvent.click(screen.getByRole("button", { name: "创建 Lark 授权会话" }));
    fireEvent.click(screen.getByRole("button", { name: "标记 Lark 授权完成" }));
    fireEvent.click(within(operationDrawer).getByRole("button", { name: "加载更多 Lark 操作" }));
    fireEvent.click(within(operationDrawer).getByRole("button", { name: "关闭 Lark 操作审计" }));
    fireEvent.click(screen.getByRole("button", { name: "打开任务 job-1" }));
    fireEvent.click(screen.getByRole("button", { name: "重试写回 job-1" }));
    fireEvent.click(screen.getByRole("button", { name: "加载更多审计记录" }));
    fireEvent.click(screen.getByRole("button", { name: "关闭审计预览" }));

    expect(onSyncSpreadsheet).toHaveBeenCalledTimes(1);
    expect(onRerunAutoClosureChange).toHaveBeenCalledWith(false);
    expect(onRerunWritebackChange).toHaveBeenCalledWith(false);
    expect(onRerunSpreadsheetRows).toHaveBeenCalledTimes(1);
    expect(onLoadWritebackAudits).toHaveBeenCalledWith("failed");
    expect(onLoadLarkOperationAudits).toHaveBeenCalledWith(null);
    expect(onLoadLarkOperationAudits).toHaveBeenCalledWith("failed");
    expect(onCheckLarkScopes).toHaveBeenCalledTimes(1);
    expect(onCreateLarkAuthSession).toHaveBeenCalledTimes(1);
    expect(onCompleteLarkAuthSession).toHaveBeenCalledTimes(1);
    expect(onLoadMoreLarkOperationAudits).toHaveBeenCalledTimes(1);
    expect(onOpenAuditJob).toHaveBeenCalledWith("job-1");
    expect(onRetryAudit).toHaveBeenCalledWith(audit);
    expect(onLoadMoreWritebackAudits).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("complementary", { name: "审计预览" })).not.toBeInTheDocument();
    expect(screen.queryByRole("complementary", { name: "Lark 操作审计" })).not.toBeInTheDocument();
  });

  it("hides optional result areas before data has loaded", () => {
    vi.spyOn(window, "matchMedia").mockReturnValue({ matches: true } as MediaQueryList);
    render(
      <SpreadsheetSyncPanel
        spreadsheetUrl=""
        spreadsheetId=""
        sheetId=""
        larkSpreadsheetStatus={null}
        syncResult={null}
        writebackAuditSummary={null}
        writebackAuditList={null}
        activeWritebackAuditStatus={null}
        larkOperationAuditList={null}
        activeLarkOperationAuditStatus={null}
        larkScopeCheck={null}
        larkAuthSession={null}
        writebackResult={null}
        batchExportHref={undefined}
        onSpreadsheetUrlChange={vi.fn()}
        onSpreadsheetIdChange={vi.fn()}
        onSheetIdChange={vi.fn()}
        onUseSpreadsheetUrl={vi.fn()}
        onCheckLarkStatus={vi.fn()}
        onSyncSpreadsheet={vi.fn()}
        rerunRowIds=""
        rerunAutoClosure={true}
        rerunWriteback={true}
        onRerunRowIdsChange={vi.fn()}
        onRerunAutoClosureChange={vi.fn()}
        onRerunWritebackChange={vi.fn()}
        onRerunSpreadsheetRows={vi.fn()}
        onLoadWritebackAuditSummary={vi.fn()}
        onLoadWritebackAudits={vi.fn()}
        onLoadLarkOperationAudits={vi.fn()}
        onCheckLarkScopes={vi.fn()}
        onCreateLarkAuthSession={vi.fn()}
        onCompleteLarkAuthSession={vi.fn()}
        onOpenAuditJob={vi.fn()}
        onRetryAudit={vi.fn()}
        onLoadMoreWritebackAudits={vi.fn()}
        onLoadMoreLarkOperationAudits={vi.fn()}
      />
    );

    expect(screen.getByRole("heading", { name: "飞书表格同步" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "回写调度小队" })).toHaveAttribute("data-writeback-mood", "idle");
    expect(screen.getByText("巡逻待命")).toBeInTheDocument();
    expect(screen.getByLabelText("调度小人-连接员")).toHaveAttribute("data-worker-expression", "neutral");
    expect(screen.queryByText("Lark 连接状态：正常")).not.toBeInTheDocument();
    expect(screen.queryByText("表格同步样本：1")).not.toBeInTheDocument();
    expect(screen.queryByText("审计总数：6")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("飞书写回审计记录")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("审计预览")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Lark 操作审计")).not.toBeInTheDocument();
  });
});
