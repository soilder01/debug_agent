import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { DebugJobStatus } from "../api/client";
import { JobStatusPanel } from "./JobStatusPanel";

afterEach(() => {
  cleanup();
});

describe("JobStatusPanel", () => {
  it("renders formatted audit timestamps while preserving raw values", () => {
    const job = {
      job_id: "job-detail-1",
      case_id: "case-1",
      status: "failed",
      created_at: "2026-06-11T10:00:01",
      updated_at: "2026-06-11T10:00:02",
      attempt_count: 2,
      max_attempts: 2,
      remaining_attempts: 0,
      will_retry: false,
      retry_recommendation: "retry_budget_exhausted",
      retry_recommendation_detail: {
        code: "retry_budget_exhausted",
        label: "重试预算已耗尽",
        action: "不要继续自动重试，转人工检查任务错误和证据链。",
        severity: "critical"
      },
      error_message: "fixture failed",
      evidence_ids: [],
      evidence_error_counts: {
        total_evidence: 0,
        failed_judgements: 0,
        response_parse_errors: 0,
        model_call_errors: 0
      }
    } satisfies DebugJobStatus;

    render(<JobStatusPanel job={job} />);

    expect(screen.getByText("创建时间：2026-06-11 10:00:01")).toHaveAttribute("title", "2026-06-11T10:00:01");
    expect(screen.getByText("更新时间：2026-06-11 10:00:02")).toHaveAttribute("title", "2026-06-11T10:00:02");
  });
});
