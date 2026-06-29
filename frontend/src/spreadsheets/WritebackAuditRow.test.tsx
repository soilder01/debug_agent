import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { SpreadsheetWritebackAudit } from "../api/client";
import { WritebackAuditRow } from "./WritebackAuditRow";

function makeAudit(overrides: Partial<SpreadsheetWritebackAudit> = {}): SpreadsheetWritebackAudit {
  return {
    job_id: "job-failed-writeback-1",
    status: "failed",
    row_id: "7",
    report_url: "https://debug-agent.local/jobs/job-failed-writeback-1/report",
    fields: {
      错误原因: "model_weakness"
    },
    error_message: "permission denied",
    created_at: "2026-06-12T06:00:00+00:00",
    updated_at: "2026-06-12T06:00:01+00:00",
    ...overrides
  };
}

describe("WritebackAuditRow", () => {
  it("renders failed audit details and supports retry", async () => {
    const onOpenJob = vi.fn();
    const onRetry = vi.fn();
    const audit = makeAudit();

    render(<WritebackAuditRow audit={audit} onOpenJob={onOpenJob} onRetry={onRetry} />);

    expect(screen.getByRole("listitem")).toHaveClass("writeback-audit-row");
    expect(screen.getByText("失败")).toHaveClass("status-badge--critical");
    expect(screen.getByLabelText("审计行操作")).toHaveClass("action-row");
    expect(screen.getByText("job-failed-writeback-1：失败｜行 7｜permission denied")).toBeInTheDocument();
    expect(screen.getByText("可重试：是")).toBeInTheDocument();
    expect(screen.getByText("重试原因：上次写回失败：permission denied")).toBeInTheDocument();
    expect(screen.getByText("写回字段数：1")).toBeInTheDocument();
    expect(screen.getByText("写回字段：错误原因=model_weakness")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "打开任务 job-failed-writeback-1" }));
    await userEvent.click(screen.getByRole("button", { name: "重试写回 job-failed-writeback-1" }));

    expect(onOpenJob).toHaveBeenCalledWith("job-failed-writeback-1");
    expect(onRetry).toHaveBeenCalledWith(audit);
  });

  it("hides retry for succeeded audits and keeps the report link", () => {
    const audit = makeAudit({
      job_id: "job-succeeded-writeback-1",
      status: "succeeded",
      row_id: "9",
      error_message: "",
      report_url: "https://debug-agent.local/jobs/job-succeeded-writeback-1/report"
    });

    render(<WritebackAuditRow audit={audit} onOpenJob={vi.fn()} onRetry={vi.fn()} />);

    expect(screen.getByText("job-succeeded-writeback-1：成功｜行 9｜无错误")).toBeInTheDocument();
    expect(screen.getByText("可重试：否")).toBeInTheDocument();
    expect(screen.getByText("重试原因：已经写回成功")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "重试写回 job-succeeded-writeback-1" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "打开报告 job-succeeded-writeback-1" })).toHaveAttribute(
      "href",
      "https://debug-agent.local/jobs/job-succeeded-writeback-1/report"
    );
  });

  it("renders native writeback fields for audit rows", () => {
    const audit = makeAudit({
      fields: {
        错误原因: "结构化评分显示 video:segment:1 存在 segment_label_mismatch。",
        影响目标: "video:segment:1",
        结构化差异: "video:segment:1 segment_label_mismatch: expected=person_enters actual=person_leaves",
        证据产物: "video-case:baseline:0:input-snapshot",
        推荐操作:
          "model_capability/high：将 video 感知能力短板纳入模型能力归因。 - 单模态 ablation 已失败，优先归因 video 感知/定位/grounding 能力。"
      }
    });

    render(<WritebackAuditRow audit={audit} onOpenJob={vi.fn()} onRetry={vi.fn()} />);

    expect(screen.getByText("原生调试写回")).toBeInTheDocument();
    const nativeSummary = screen.getByLabelText("原生调试写回");
    expect(screen.getByText("影响目标：video:segment:1")).toBeInTheDocument();
    expect(screen.getByText("结构化差异：video:segment:1 segment_label_mismatch: expected=person_enters actual=person_leaves")).toBeInTheDocument();
    expect(screen.getByText("证据产物：video-case:baseline:0:input-snapshot")).toBeInTheDocument();
    expect(within(nativeSummary).getByText("推荐操作条目")).toBeInTheDocument();
    expect(within(nativeSummary).getByText("类别：model_capability")).toBeInTheDocument();
    expect(within(nativeSummary).getByText("优先级：high")).toBeInTheDocument();
    expect(within(nativeSummary).getByText("摘要：将 video 感知能力短板纳入模型能力归因。")).toBeInTheDocument();
    expect(screen.getByText("写回字段：影响目标=video:segment:1")).toBeInTheDocument();
  });
});
