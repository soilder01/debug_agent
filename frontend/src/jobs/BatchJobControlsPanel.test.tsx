import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { BatchJobControlsPanel } from "./BatchJobControlsPanel";

describe("BatchJobControlsPanel", () => {
  it("renders batch controls and delegates actions", async () => {
    const onCaseIdsChange = vi.fn();
    const onSubmit = vi.fn();
    const onLoadJobs = vi.fn();

    render(
      <BatchJobControlsPanel
        caseIds="case-1"
        onCaseIdsChange={onCaseIdsChange}
        onSubmit={onSubmit}
        onLoadJobs={onLoadJobs}
      />
    );

    expect(screen.getByRole("heading", { name: "批量调试任务" })).toBeInTheDocument();
    expect(screen.getByText("不知道样本 ID？先去“数据导入”加载样本，或在“回写同步”按飞书行号重跑。")).toBeInTheDocument();
    expect(screen.getByText(/一行一个 case_id，例如 JSZN-096/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("批量样本 ID"), { target: { value: "case-1\ncase-2" } });

    await userEvent.click(screen.getByRole("button", { name: "批量提交调试" }));
    await userEvent.click(screen.getByRole("button", { name: "查看历史任务" }));
    await userEvent.click(screen.getByRole("button", { name: "查看失败任务" }));
    await userEvent.click(screen.getByRole("button", { name: "查看最新任务" }));

    expect(onCaseIdsChange).toHaveBeenCalledWith("case-1\ncase-2");
    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onLoadJobs).toHaveBeenNthCalledWith(1, undefined, undefined);
    expect(onLoadJobs).toHaveBeenNthCalledWith(2, "failed", undefined);
    expect(onLoadJobs).toHaveBeenNthCalledWith(3, undefined, "created_at_desc");
  });
});
