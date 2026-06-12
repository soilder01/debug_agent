import { describe, expect, it } from "vitest";

import { canRetryWritebackAudit, writebackRetryReason } from "./writebackAuditPolicy";

describe("writebackAuditPolicy", () => {
  it("allows retry only for failed writeback audits", () => {
    expect(canRetryWritebackAudit("failed")).toBe(true);
    expect(canRetryWritebackAudit("succeeded")).toBe(false);
    expect(canRetryWritebackAudit("skipped")).toBe(false);
  });

  it("explains failed writebacks with the original error when available", () => {
    expect(writebackRetryReason("failed", "permission denied")).toBe("last writeback failed: permission denied");
    expect(writebackRetryReason("failed", "")).toBe("last writeback failed");
  });

  it("explains non-retryable writeback states", () => {
    expect(writebackRetryReason("succeeded", "")).toBe("already succeeded");
    expect(writebackRetryReason("skipped", "missing report")).toBe("missing report");
    expect(writebackRetryReason("skipped", "")).toBe("missing prerequisites");
  });
});
