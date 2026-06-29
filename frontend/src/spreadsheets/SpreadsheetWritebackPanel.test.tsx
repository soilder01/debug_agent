import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { LarkWriteConfirmation, SpreadsheetWritebackAudit, SpreadsheetWritebackResult } from "../api/client";
import { SpreadsheetWritebackPanel } from "./SpreadsheetWritebackPanel";

function makeResult(overrides: Partial<SpreadsheetWritebackResult> = {}): SpreadsheetWritebackResult {
  return {
    row_id: "row-42",
    fields: {
      错误原因: "model_weakness",
      分析报告链接: "https://debug-agent.local/report"
    },
    ...overrides
  };
}

function makeAudit(overrides: Partial<SpreadsheetWritebackAudit> = {}): SpreadsheetWritebackAudit {
  return {
    job_id: "job-1",
    status: "failed",
    row_id: "row-42",
    report_url: "https://debug-agent.local/report",
    fields: {},
    error_message: "permission denied",
    created_at: "2026-06-13T00:00:00+00:00",
    updated_at: "2026-06-13T00:00:01+00:00",
    ...overrides
  };
}

function makeConfirmation(overrides: Partial<LarkWriteConfirmation> = {}): LarkWriteConfirmation {
  return {
    confirmation_id: "confirm-1",
    actor: "qa-operator",
    service: "sheets",
    operation: "+cells-set",
    resource_id: "sheets:spreadsheet-1:sheet-1:row-42:job:job-1",
    resource_summary: "写回任务 job-1 到表格 spreadsheet-1/sheet-1 行 row-42",
    risk_action: "sheets +cells-set",
    required_scopes: ["sheets:spreadsheet"],
    status: "pending",
    note: "reviewed",
    created_at: "2026-06-22T00:00:00+00:00",
    expires_at: "2026-06-22T00:30:00+00:00",
    confirmed_at: "",
    confirmed_by: "",
    ...overrides
  };
}

describe("SpreadsheetWritebackPanel", () => {
  it("renders writeback controls, result fields, and audit details", async () => {
    const onWriteReport = vi.fn();
    const onPrepareWriteConfirmation = vi.fn();
    const onConfirmWriteReport = vi.fn();
    const onLoadAudit = vi.fn();

    render(
      <SpreadsheetWritebackPanel
        writebackResult={makeResult()}
        writebackAudit={makeAudit()}
        writeConfirmation={makeConfirmation()}
        onWriteReport={onWriteReport}
        onPrepareWriteConfirmation={onPrepareWriteConfirmation}
        onConfirmWriteReport={onConfirmWriteReport}
        onLoadAudit={onLoadAudit}
      />
    );

    expect(screen.getByRole("heading", { name: "飞书写回" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "飞书写回" })).toHaveClass("writeback-panel");
    expect(screen.getByLabelText("飞书写回操作")).toHaveClass("action-row");
    expect(screen.getByText("失败")).toHaveClass("status-badge--critical");
    expect(screen.getByText("表格写回行：row-42")).toBeInTheDocument();
    expect(screen.getByText("错误原因：model_weakness")).toBeInTheDocument();
    expect(screen.getByText("分析报告链接：https://debug-agent.local/report")).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "写回审计预览" })).toHaveClass("writeback-audit-drawer");
    expect(screen.getByRole("region", { name: "Lark 写回确认单" })).toHaveClass("writeback-audit-list");
    expect(screen.getByText("Lark 写回确认状态：待确认")).toBeInTheDocument();
    expect(screen.getByText("风险操作：sheets +cells-set")).toBeInTheDocument();
    expect(screen.getByText("需要 scope：sheets:spreadsheet")).toBeInTheDocument();
    expect(screen.getByText("写回审计状态：失败")).toBeInTheDocument();
    expect(screen.getByText("写回行：row-42")).toBeInTheDocument();
    expect(screen.getByText("报告链接：https://debug-agent.local/report")).toBeInTheDocument();
    expect(screen.getByText("更新时间：2026-06-13T00:00:01+00:00")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("写回审计错误：permission denied");

    await userEvent.click(screen.getByRole("button", { name: "写回报告到表格" }));
    await userEvent.click(screen.getByRole("button", { name: "生成高风险写回确认" }));
    await userEvent.click(screen.getByRole("button", { name: "确认并写回报告" }));
    await userEvent.click(screen.getByRole("button", { name: "加载审计预览" }));
    await userEvent.click(screen.getByRole("button", { name: "关闭写回审计预览" }));

    expect(onWriteReport).toHaveBeenCalledTimes(1);
    expect(onPrepareWriteConfirmation).toHaveBeenCalledTimes(1);
    expect(onConfirmWriteReport).toHaveBeenCalledTimes(1);
    expect(onLoadAudit).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("complementary", { name: "写回审计预览" })).not.toBeInTheDocument();
  });

  it("hides optional result and audit details when absent", () => {
    render(
      <SpreadsheetWritebackPanel
        writebackResult={null}
        writebackAudit={null}
        writeConfirmation={null}
        onWriteReport={vi.fn()}
        onPrepareWriteConfirmation={vi.fn()}
        onConfirmWriteReport={vi.fn()}
        onLoadAudit={vi.fn()}
      />
    );

    expect(screen.queryByText(/表格写回行/)).not.toBeInTheDocument();
    expect(screen.queryByText(/写回审计状态/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Lark 写回确认状态/)).not.toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "确认并写回报告" })).toBeDisabled();
  });

  it("renders native writeback fields as structured debug summary", () => {
    render(
      <SpreadsheetWritebackPanel
        writebackResult={makeResult({
          fields: {
            错误原因: "结构化评分显示 multimodal:conflict:1 存在 conflict_actual_mismatch。",
            影响目标: "multimodal:conflict:1",
            结构化差异:
              "multimodal:conflict:1 conflict_actual_mismatch: expected=image and caption both describe a cat actual=image shows dog while caption says cat",
            证据产物: "multimodal-writeback:baseline:0:input-snapshot",
            推荐操作:
              "prompt/high：强化跨模态对比步骤。 - 要求模型先分别列出 image/text 证据，再输出冲突结论。",
            分析报告链接: "https://debug-agent.local/report"
          }
        })}
        writebackAudit={null}
        writeConfirmation={null}
        onWriteReport={vi.fn()}
        onPrepareWriteConfirmation={vi.fn()}
        onConfirmWriteReport={vi.fn()}
        onLoadAudit={vi.fn()}
      />
    );

    const nativeSummary = screen.getByLabelText("原生调试写回");
    expect(within(nativeSummary).getByText("原生调试写回")).toBeInTheDocument();
    expect(within(nativeSummary).getByText("影响目标：multimodal:conflict:1")).toBeInTheDocument();
    expect(within(nativeSummary).getByText(/结构化差异：multimodal:conflict:1 conflict_actual_mismatch/)).toBeInTheDocument();
    expect(within(nativeSummary).getByText("证据产物：multimodal-writeback:baseline:0:input-snapshot")).toBeInTheDocument();
    expect(
      within(nativeSummary).getByText(
        "推荐操作：prompt/high：强化跨模态对比步骤。 - 要求模型先分别列出 image/text 证据，再输出冲突结论。"
      )
    ).toBeInTheDocument();
    expect(within(nativeSummary).getByText("推荐操作条目")).toBeInTheDocument();
    expect(within(nativeSummary).getByText("类别：prompt")).toBeInTheDocument();
    expect(within(nativeSummary).getByText("优先级：high")).toBeInTheDocument();
    expect(within(nativeSummary).getByText("摘要：强化跨模态对比步骤。")).toBeInTheDocument();
    expect(within(nativeSummary).getByText("详情：要求模型先分别列出 image/text 证据，再输出冲突结论。")).toBeInTheDocument();
    expect(screen.getByText("错误原因：结构化评分显示 multimodal:conflict:1 存在 conflict_actual_mismatch。")).toBeInTheDocument();
  });
});
