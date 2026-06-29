import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { LarkBotBadcaseDraft, LarkBotBadcaseDraftConfirmResponse } from "../api/client";
import { LarkBotBadcaseDraftPanel } from "./LarkBotBadcaseDraftPanel";

function makeDraft(overrides: Partial<LarkBotBadcaseDraft> = {}): LarkBotBadcaseDraft {
  return {
    draft_id: "draft-1",
    actor: "ops-reviewer",
    open_id: "ou_1",
    chat_id: "oc_1",
    message_id: "om_1",
    status: "ready_for_confirmation",
    source_text: "原始输入：https://example.com/a.png",
    input_source: "https://example.com/a.png",
    model_output: '{"answer":"3"}',
    expected_output: '{"answer":"8"}',
    issue_summary: "把 8 识别成 3",
    task_type: "generic_json",
    scoring_standard: "Compare outputs",
    attachments: [],
    links: ["https://example.com/a.png"],
    missing_fields: [],
    submitted_case_id: "",
    submitted_job_id: "",
    error_message: "",
    created_at: "2026-06-23T00:00:00+00:00",
    updated_at: "2026-06-23T00:00:00+00:00",
    ...overrides
  };
}

const confirmation: LarkBotBadcaseDraftConfirmResponse = {
  draft: makeDraft({
    status: "submitted",
    submitted_case_id: "lark-draft-draft-1",
    submitted_job_id: "job-1"
  }),
  submitted_job: {
    job_id: "job-1",
    case_id: "lark-draft-draft-1",
    status: "created",
    attempt_count: 0,
    error_message: null,
    evidence_ids: []
  }
};

describe("LarkBotBadcaseDraftPanel", () => {
  it("renders ready drafts and delegates confirmation", async () => {
    const onLoadStatus = vi.fn();
    const onLoadMore = vi.fn();
    const onConfirm = vi.fn();

    render(
      <LarkBotBadcaseDraftPanel
        drafts={[makeDraft()]}
        totalCount={2}
        activeStatus="ready_for_confirmation"
        lastConfirmation={confirmation}
        onLoadStatus={onLoadStatus}
        onLoadMore={onLoadMore}
        onConfirm={onConfirm}
      />
    );

    expect(screen.getByRole("region", { name: "飞书 badcase 草稿" })).toBeInTheDocument();
    expect(screen.getByText("badcase 草稿总数：2")).toBeInTheDocument();
    expect(screen.getByText("当前筛选：待确认")).toBeInTheDocument();
    expect(screen.getByText("把 8 识别成 3")).toBeInTheDocument();
    expect(screen.getAllByText("待确认")[0]).toBeInTheDocument();
    expect(screen.getByText(/提交人：ops-reviewer/)).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "badcase 草稿确认结果" })).toBeInTheDocument();
    expect(screen.getByText("任务编号：job-1")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "查看全部草稿" }));
    await userEvent.click(screen.getByRole("button", { name: "查看待补充草稿" }));
    await userEvent.click(screen.getByRole("button", { name: "查看已取消草稿" }));
    await userEvent.click(screen.getByRole("button", { name: "确认并创建 Debug 任务" }));
    await userEvent.click(screen.getByRole("button", { name: "加载更多 badcase 草稿" }));

    expect(onLoadStatus).toHaveBeenNthCalledWith(1, null);
    expect(onLoadStatus).toHaveBeenNthCalledWith(2, "needs_more_info");
    expect(onLoadStatus).toHaveBeenNthCalledWith(3, "cancelled");
    expect(onConfirm).toHaveBeenCalledWith("draft-1");
    expect(onLoadMore).toHaveBeenCalledTimes(1);
  });

  it("renders recognized link contexts", () => {
    render(
      <LarkBotBadcaseDraftPanel
        drafts={[
          makeDraft({
            attachments: [
              {
                type: "link_context",
                link_type: "lark_sheet",
                resource: "飞书电子表格",
                url: "https://example.larkoffice.com/sheets/shtcn123?sheet=tab-1",
                token: "shtcn123",
                sheet_id: "tab-1",
                status: "content_resolved",
                selected_row: "2",
                next_action: "下一步接入表格读取后，可选择样本行并映射字段。"
              }
            ]
          })
        ]}
        totalCount={1}
        activeStatus={null}
        lastConfirmation={null}
        onLoadStatus={vi.fn()}
        onLoadMore={vi.fn()}
        onConfirm={vi.fn()}
      />
    );

    expect(screen.getByRole("list", { name: "badcase 草稿 draft-1 链接上下文" })).toBeInTheDocument();
    expect(screen.getByText(/飞书电子表格：lark_sheet/)).toBeInTheDocument();
    expect(screen.getByText(/已读取并提取字段/)).toBeInTheDocument();
    expect(screen.getByText(/token=shtcn123/)).toBeInTheDocument();
    expect(screen.getByText(/sheet=tab-1/)).toBeInTheDocument();
    expect(screen.getByText(/row=2/)).toBeInTheDocument();
  });

  it("renders link context read failures", () => {
    render(
      <LarkBotBadcaseDraftPanel
        drafts={[
          makeDraft({
            status: "needs_more_info",
            attachments: [
              {
                type: "link_context",
                link_type: "lark_doc",
                resource: "飞书文档",
                url: "https://bytedance.larkoffice.com/docx/doc-token",
                status: "read_failed",
                error_type: "permission_denied",
                permission_scopes: ["docx:document:readonly"],
                next_action: "读取飞书资源失败；请检查机器人权限、资源访问权限或链接定位参数。"
              }
            ]
          })
        ]}
        totalCount={1}
        activeStatus={null}
        lastConfirmation={null}
        onLoadStatus={vi.fn()}
        onLoadMore={vi.fn()}
        onConfirm={vi.fn()}
      />
    );

    expect(screen.getByText(/飞书文档：lark_doc/)).toBeInTheDocument();
    expect(screen.getByText(/读取失败/)).toBeInTheDocument();
    expect(screen.getByText(/error=permission_denied/)).toBeInTheDocument();
    expect(screen.getByText(/missing_scope=docx:document:readonly/)).toBeInTheDocument();
  });

  it("renders media download failures from sheet attachments", () => {
    render(
      <LarkBotBadcaseDraftPanel
        drafts={[
          makeDraft({
            status: "needs_more_info",
            missing_fields: ["input_source"],
            attachments: [
              {
                type: "link_context",
                link_type: "lark_sheet",
                resource: "飞书电子表格",
                url: "https://example.larkoffice.com/sheets/shtcn123?sheet=tab-1",
                status: "download_failed",
                media_input: {
                  status: "download_failed",
                  attachment_token: "file-token-1",
                  permission_scopes: ["docs:document.media:download"]
                },
                next_action: "已识别到表格视频附件，但机器人没有下载权限。"
              }
            ]
          })
        ]}
        totalCount={1}
        activeStatus={null}
        lastConfirmation={null}
        onLoadStatus={vi.fn()}
        onLoadMore={vi.fn()}
        onConfirm={vi.fn()}
      />
    );

    expect(screen.getByText(/飞书电子表格：lark_sheet/)).toBeInTheDocument();
    expect(screen.getByText(/附件下载失败/)).toBeInTheDocument();
    expect(screen.getByText(/media=附件下载失败/)).toBeInTheDocument();
    expect(screen.getByText(/attachment=file-token-1/)).toBeInTheDocument();
    expect(screen.getByText(/missing_scope=docs:document.media:download/)).toBeInTheDocument();
  });

  it("renders missing fields and empty state", () => {
    const { rerender } = render(
      <LarkBotBadcaseDraftPanel
        drafts={[makeDraft({ status: "needs_more_info", missing_fields: ["model_output", "expected_output"] })]}
        totalCount={1}
        activeStatus="needs_more_info"
        lastConfirmation={null}
        onLoadStatus={vi.fn()}
        onLoadMore={vi.fn()}
        onConfirm={vi.fn()}
      />
    );

    expect(screen.getByText("待补充：模型输出、期望结果")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "确认并创建 Debug 任务" })).not.toBeInTheDocument();

    rerender(
      <LarkBotBadcaseDraftPanel
        drafts={[]}
        totalCount={0}
        activeStatus={null}
        lastConfirmation={null}
        onLoadStatus={vi.fn()}
        onLoadMore={vi.fn()}
        onConfirm={vi.fn()}
      />
    );

    expect(screen.getByText("当前筛选：全部")).toBeInTheDocument();
    expect(screen.getByText("暂无 badcase 草稿")).toBeInTheDocument();
  });

  it("labels cancelled drafts", () => {
    render(
      <LarkBotBadcaseDraftPanel
        drafts={[makeDraft({ status: "cancelled" })]}
        totalCount={1}
        activeStatus="cancelled"
        lastConfirmation={null}
        onLoadStatus={vi.fn()}
        onLoadMore={vi.fn()}
        onConfirm={vi.fn()}
      />
    );

    expect(screen.getByText("当前筛选：已取消")).toBeInTheDocument();
    expect(screen.getByText("已取消")).toBeInTheDocument();
  });
});
