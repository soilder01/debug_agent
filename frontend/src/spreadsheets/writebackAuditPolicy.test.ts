import { describe, expect, it } from "vitest";

import { canRetryWritebackAudit, writebackRetryReason } from "./writebackAuditPolicy";

describe("writebackAuditPolicy", () => {
  it("allows retry only for failed writeback audits", () => {
    expect(canRetryWritebackAudit("failed")).toBe(true);
    expect(canRetryWritebackAudit("succeeded")).toBe(false);
    expect(canRetryWritebackAudit("skipped")).toBe(false);
  });

  it("explains failed writebacks with the original error when available", () => {
    expect(writebackRetryReason("failed", "permission denied")).toBe("上次写回失败：permission denied");
    expect(writebackRetryReason("failed", "")).toBe("上次写回失败");
  });

  it("explains non-retryable writeback states", () => {
    expect(writebackRetryReason("succeeded", "")).toBe("已经写回成功");
    expect(writebackRetryReason("skipped", "missing report")).toBe("跳过原因：missing report");
    expect(writebackRetryReason("skipped", "")).toBe("缺少写回前置条件");
  });
});
