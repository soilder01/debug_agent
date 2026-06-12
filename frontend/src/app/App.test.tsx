import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("App", () => {
  it("submits a single-case debug job and renders the created job state", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-123",
            case_id: "handwrite233",
            status: "created",
            attempt_count: 0,
            error_message: null,
            evidence_ids: []
          }),
          { status: 202, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-123",
            case_id: "handwrite233",
            status: "completed",
            attempt_count: 1,
            max_attempts: 2,
            remaining_attempts: 1,
            will_retry: false,
            retry_recommendation: "no_retry_needed",
            retry_recommendation_detail: {
              code: "no_retry_needed",
              label: "无需重试",
              action: "任务已完成，直接查看证据链和结论。",
              severity: "info"
            },
            error_message: null,
            evidence_ids: ["handwrite233:baseline_replay:0"],
            evidence_error_counts: {
              total_evidence: 1,
              failed_judgements: 1,
              response_parse_errors: 0,
              model_call_errors: 0
            }
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Submit debug job" }));

    expect(await screen.findByText("样本 ID：handwrite233")).toBeInTheDocument();
    expect(screen.getByText("Job ID：job-123")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/cases/handwrite233/debug-jobs?auto_run=true&baseline_trials=5", {
      method: "POST"
    });

    expect(await screen.findByText("状态：completed", {}, { timeout: 500 })).toBeInTheDocument();
    expect(screen.getByText("尝试次数：1")).toBeInTheDocument();
    expect(screen.getByText("最大尝试：2")).toBeInTheDocument();
    expect(screen.getByText("剩余尝试：1")).toBeInTheDocument();
    expect(screen.getByText("将会重试：false")).toBeInTheDocument();
    expect(screen.getByText("重试建议：无需重试")).toBeInTheDocument();
    expect(screen.getByText("建议动作：任务已完成，直接查看证据链和结论。")).toBeInTheDocument();
    expect(screen.getByText("证据数：1")).toBeInTheDocument();
    expect(screen.getByText("失败判分：1")).toBeInTheDocument();
    expect(screen.getByText("解析错误：0")).toBeInTheDocument();
    expect(screen.getByText("模型调用错误：0")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-123");
  });

  it("opens persisted evidence detail from a completed job", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-123",
            case_id: "handwrite233",
            status: "created",
            attempt_count: 0,
            error_message: null,
            evidence_ids: []
          }),
          { status: 202, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-123",
            case_id: "handwrite233",
            status: "completed",
            attempt_count: 1,
            error_message: null,
            evidence_ids: ["handwrite233:baseline_replay:0"]
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            evidence_id: "handwrite233:baseline_replay:0",
            step_name: "baseline_replay",
            trial: 0,
            model_name: "fake",
            model_provider: "fake",
            model_id: "fake",
            request_summary: {
              prompt_length: 22,
              has_image: false,
              image_uri_scheme: ""
            },
            latency_ms: 12,
            response_parse_error: "Expecting value: line 1 column 1 (char 0)",
            model_call_error_type: "TimeoutError",
            model_call_error_message: "model request timed out",
            raw_output: "{\"answers\":[]}",
            judge: {
              score: 0,
              reasons: ["box 1 student_answer_mismatch"]
            }
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Submit debug job" }));
    await screen.findByText("状态：completed", {}, { timeout: 500 });
    await userEvent.click(screen.getByRole("button", { name: "View evidence handwrite233:baseline_replay:0" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-123/evidence/handwrite233%3Abaseline_replay%3A0");
    expect(await screen.findByText("证据 ID：handwrite233:baseline_replay:0")).toBeInTheDocument();
    expect(screen.getByText("模型名称：fake")).toBeInTheDocument();
    expect(screen.getByText("模型 Provider：fake")).toBeInTheDocument();
    expect(screen.getByText("模型 ID：fake")).toBeInTheDocument();
    expect(screen.getByText("调用耗时：12ms")).toBeInTheDocument();
    expect(screen.getByText("Prompt 长度：22")).toBeInTheDocument();
    expect(screen.getByText("包含图片：false")).toBeInTheDocument();
    expect(screen.getByText("图片 URI Scheme：无")).toBeInTheDocument();
    expect(screen.getByText("解析错误：Expecting value: line 1 column 1 (char 0)")).toBeInTheDocument();
    expect(screen.getByText("模型调用错误类型：TimeoutError")).toBeInTheDocument();
    expect(screen.getByText("模型调用错误信息：model request timed out")).toBeInTheDocument();
    expect(screen.getByText("box 1 student_answer_mismatch")).toBeInTheDocument();
  });

  it("submits batch debug jobs and renders the batch summary", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          jobs: [{ job_id: "job-123", case_id: "handwrite233", status: "created" }],
          rejected_case_ids: ["missing-case"]
        }),
        { status: 202, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);
    await userEvent.type(screen.getByLabelText("Batch case ids"), "handwrite233\nmissing-case");
    await userEvent.click(screen.getByRole("button", { name: "Submit batch jobs" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/debug-jobs/batch", {
      body: JSON.stringify({ case_ids: ["handwrite233", "missing-case"] }),
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
    expect(await screen.findByText("批量创建：1")).toBeInTheDocument();
    expect(screen.getByText("拒绝：missing-case")).toBeInTheDocument();
  });

  it("polls and renders statuses for batch debug jobs", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            jobs: [
              { job_id: "job-1", case_id: "handwrite233", status: "created" },
              { job_id: "job-2", case_id: "handwrite233", status: "created" }
            ],
            rejected_case_ids: []
          }),
          { status: 202, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-1",
            case_id: "handwrite233",
            status: "completed",
            attempt_count: 1,
            error_message: null,
            evidence_ids: ["handwrite233:baseline_replay:0"]
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-2",
            case_id: "handwrite233",
            status: "failed",
            attempt_count: 2,
            error_message: "fixture failed",
            evidence_ids: [],
            retry_recommendation_detail: {
              code: "retry_budget_exhausted",
              label: "重试预算已耗尽",
              action: "不要继续自动重试，转人工检查任务错误和证据链。",
              severity: "critical"
            }
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await userEvent.type(screen.getByLabelText("Batch case ids"), "handwrite233 handwrite233");
    await userEvent.click(screen.getByRole("button", { name: "Submit batch jobs" }));

    expect(await screen.findByText("批量创建：2")).toBeInTheDocument();
    expect(screen.getByText("job-1：created")).toBeInTheDocument();
    expect(screen.getByText("job-2：created")).toBeInTheDocument();
    expect(await screen.findByText("job-1：completed", {}, { timeout: 500 })).toBeInTheDocument();
    expect(await screen.findByText("job-2：failed", {}, { timeout: 500 })).toBeInTheDocument();
    expect(screen.getByText("job-2 错误：fixture failed")).toBeInTheDocument();
    expect(screen.getByText("job-2 建议：重试预算已耗尽")).toBeInTheDocument();
    expect(screen.getByText("job-2 级别：critical")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-1");
    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-2");
  });

  it("loads persisted debug jobs into the batch triage list", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            jobs: [
              {
                job_id: "job-history-1",
                case_id: "handwrite233",
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
                evidence_ids: ["handwrite233:baseline_replay:0"],
                evidence_error_counts: {
                  total_evidence: 0,
                  failed_judgements: 0,
                  response_parse_errors: 0,
                  model_call_errors: 0
                }
              }
            ],
            total_count: 5
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            evidence_id: "handwrite233:baseline_replay:0",
            step_name: "baseline_replay",
            trial: 0,
            model_name: "ark-seed2-lite",
            model_provider: "ark",
            model_id: "ep-20260609151048-sbfnk",
            request_summary: {
              prompt_length: 22,
              has_image: true,
              image_uri_scheme: "file"
            },
            latency_ms: 35,
            response_parse_error: "",
            model_call_error_type: "",
            model_call_error_message: "",
            raw_output: "{\"answers\":[]}",
            judge: {
              score: 0,
              reasons: ["box 1 student_answer_mismatch"]
            }
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Load debug jobs" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs?limit=50");
    expect(await screen.findByText("队列任务：1")).toBeInTheDocument();
    expect(screen.getByText("总任务：5")).toBeInTheDocument();
    expect(screen.getByText("未加载：4")).toBeInTheDocument();
    expect(screen.getByText("job-history-1：failed")).toBeInTheDocument();
    expect(screen.getByText("job-history-1 创建：2026-06-11 10:00:01")).toHaveAttribute(
      "title",
      "2026-06-11T10:00:01"
    );
    expect(screen.getByText("job-history-1 更新：2026-06-11 10:00:02")).toHaveAttribute(
      "title",
      "2026-06-11T10:00:02"
    );
    expect(screen.getByText("job-history-1 错误：fixture failed")).toBeInTheDocument();
    expect(screen.getByText("job-history-1 建议：重试预算已耗尽")).toBeInTheDocument();
    expect(screen.getByText("job-history-1 级别：critical")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Open job job-history-1" }));

    expect(screen.getByText("Job ID：job-history-1")).toBeInTheDocument();
    expect(screen.getByText("建议动作：不要继续自动重试，转人工检查任务错误和证据链。")).toBeInTheDocument();

    await userEvent.click(
      screen.getByRole("button", { name: "Open evidence handwrite233:baseline_replay:0 for job job-history-1" })
    );

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-history-1/evidence/handwrite233%3Abaseline_replay%3A0");
    expect(await screen.findByText("证据 ID：handwrite233:baseline_replay:0")).toBeInTheDocument();
    expect(screen.getByText("模型 Provider：ark")).toBeInTheDocument();
  });

  it("loads and renders a persisted report for an opened job", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            jobs: [
              {
                job_id: "job-report-1",
                case_id: "handwrite233",
                status: "completed",
                created_at: "2026-06-11T10:00:01",
                updated_at: "2026-06-11T10:00:02",
                attempt_count: 1,
                max_attempts: 2,
                remaining_attempts: 1,
                will_retry: false,
                retry_recommendation: "no_retry_needed",
                retry_recommendation_detail: {
                  code: "no_retry_needed",
                  label: "无需重试",
                  action: "任务已完成，直接查看证据链和结论。",
                  severity: "info"
                },
                error_message: null,
                evidence_ids: ["handwrite233:baseline_replay:0"],
                evidence_error_counts: {
                  total_evidence: 1,
                  failed_judgements: 1,
                  response_parse_errors: 0,
                  model_call_errors: 0
                }
              }
            ],
            total_count: 1
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-report-1",
            case_id: "handwrite233",
            status: "needs_human_review",
            observed_failure: {
              type: "erasure_revision_failure",
              summary: "模型在涂改区域识别不稳定。",
              affected_box_ids: [1]
            },
            planned_experiments: ["baseline_replay"],
            experiment_summary: {
              total_trials: 5,
              success_count: 2,
              failed_trial_count: 3,
              success_rate: 0.4,
              stability_label: "unstable",
              evidence_ids: ["handwrite233:baseline_replay:0"],
              image_artifact_ids: []
            },
            root_cause: {
              label: "erasure_revision_failure",
              confidence: "medium",
              evidence_summary: "当前样本低分且人工备注指向涂改区域识别失败。"
            },
            suggested_sheet_fields: {
              "debug1状态": "待人工确认",
              "错误原因": "模型无法稳定识别涂改后的最终答案。"
            }
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Load debug jobs" }));
    await userEvent.click(await screen.findByRole("button", { name: "Open job job-report-1" }));
    await userEvent.click(screen.getByRole("button", { name: "Load persisted report" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-report-1/report");
    expect(await screen.findAllByText("样本 ID：handwrite233")).toHaveLength(2);
    expect(screen.getByText("类型：erasure_revision_failure")).toBeInTheDocument();
    expect(screen.getByText("复测稳定性：unstable")).toBeInTheDocument();
    expect(screen.getByText("错误原因")).toBeInTheDocument();
    expect(screen.getByText("模型无法稳定识别涂改后的最终答案。")).toBeInTheDocument();
  });

  it("loads failed debug jobs with a status filter", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          jobs: [
            {
              job_id: "job-failed-1",
              case_id: "handwrite233",
              status: "failed",
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
            }
          ],
          total_count: 3
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Load failed jobs" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs?status=failed&limit=50");
    expect(await screen.findByText("失败任务：1")).toBeInTheDocument();
    expect(screen.getByText("总任务：3")).toBeInTheDocument();
    expect(screen.getByText("未加载：2")).toBeInTheDocument();
    expect(await screen.findByText("job-failed-1：failed")).toBeInTheDocument();
    expect(screen.getByText("job-failed-1 建议：重试预算已耗尽")).toBeInTheDocument();
  });

  it("loads newest debug jobs first", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          jobs: [
            {
              job_id: "job-newest-1",
              case_id: "handwrite233",
              status: "completed",
              created_at: "2026-06-11T10:00:02",
              updated_at: "2026-06-11T10:00:02",
              attempt_count: 0,
              max_attempts: 2,
              remaining_attempts: 2,
              will_retry: false,
              retry_recommendation: "retry_budget_exhausted",
              retry_recommendation_detail: {
                code: "retry_budget_exhausted",
                label: "重试预算已耗尽",
                action: "不要继续自动重试，转人工检查任务错误和证据链。",
                severity: "critical"
              },
              error_message: null,
              evidence_ids: [],
              evidence_error_counts: {
                total_evidence: 0,
                failed_judgements: 0,
                response_parse_errors: 0,
                model_call_errors: 0
              }
            }
          ],
          total_count: 1
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Load newest debug jobs" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs?limit=50&sort=created_at_desc");
    expect(await screen.findByText("最新任务：1")).toBeInTheDocument();
    expect(screen.getByText("job-newest-1：completed")).toBeInTheDocument();
  });

  it("loads more debug jobs after the first page", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            jobs: [
              {
                job_id: "job-history-page-1",
                case_id: "handwrite233",
                status: "completed",
                attempt_count: 0,
                max_attempts: 2,
                remaining_attempts: 2,
                will_retry: false,
                retry_recommendation: "retry_budget_exhausted",
                retry_recommendation_detail: {
                  code: "retry_budget_exhausted",
                  label: "重试预算已耗尽",
                  action: "不要继续自动重试，转人工检查任务错误和证据链。",
                  severity: "critical"
                },
                error_message: null,
                evidence_ids: [],
                evidence_error_counts: {
                  total_evidence: 0,
                  failed_judgements: 0,
                  response_parse_errors: 0,
                  model_call_errors: 0
                }
              }
            ],
            total_count: 2
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            jobs: [
              {
                job_id: "job-history-page-2",
                case_id: "handwrite233",
                status: "failed",
                attempt_count: 1,
                max_attempts: 2,
                remaining_attempts: 1,
                will_retry: true,
                retry_recommendation: "retry_model_call_error",
                retry_recommendation_detail: {
                  code: "retry_model_call_error",
                  label: "模型调用错误，建议重试",
                  action: "重新排队该任务。",
                  severity: "warning"
                },
                error_message: "transient error",
                evidence_ids: [],
                evidence_error_counts: {
                  total_evidence: 0,
                  failed_judgements: 0,
                  response_parse_errors: 0,
                  model_call_errors: 0
                }
              }
            ],
            total_count: 2
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Load debug jobs" }));

    expect(await screen.findByText("未加载：1")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Load more debug jobs" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs?limit=50");
    expect(fetchMock).toHaveBeenCalledWith("/api/jobs?limit=50&offset=1");
    expect(await screen.findByText("job-history-page-2：failed")).toBeInTheDocument();
    expect(screen.getByText("队列任务：2")).toBeInTheDocument();
    expect(screen.getByText("未加载：0")).toBeInTheDocument();
  });

  it("starts, polls, and stops the worker from the UI", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            running: true,
            processed_count: 0,
            error_count: 0,
            last_error: null
          }),
          { status: 202, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            running: true,
            processed_count: 1,
            error_count: 0,
            last_error: null
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            running: false,
            processed_count: 1,
            error_count: 0,
            last_error: null
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Start worker" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/worker/start", { method: "POST" });
    expect(await screen.findByText("Worker running：true")).toBeInTheDocument();
    expect(await screen.findByText("Worker processed：1", {}, { timeout: 500 })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Stop worker" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/worker/stop", { method: "POST" });
    expect(await screen.findByText("Worker running：false")).toBeInTheDocument();
    expect(screen.getByText("Worker errors：0")).toBeInTheDocument();
  });

  it("starts the worker from the batch section and renders batch progress", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url === "/api/debug-jobs/batch") {
        return Promise.resolve(
          new Response(
          JSON.stringify({
            jobs: [
              { job_id: "job-1", case_id: "handwrite233", status: "created" },
              { job_id: "job-2", case_id: "handwrite233", status: "created" }
            ],
            rejected_case_ids: []
          }),
          { status: 202, headers: { "Content-Type": "application/json" } }
        )
        );
      }
      if (url === "/api/worker/start") {
        return Promise.resolve(
          new Response(
          JSON.stringify({
            running: true,
            processed_count: 0,
            error_count: 0,
            last_error: null
          }),
          { status: 202, headers: { "Content-Type": "application/json" } }
        )
        );
      }
      if (url === "/api/jobs/job-1") {
        return Promise.resolve(
          new Response(
          JSON.stringify({
            job_id: "job-1",
            case_id: "handwrite233",
            status: "completed",
            attempt_count: 1,
            error_message: null,
            evidence_ids: ["handwrite233:baseline_replay:0"]
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
        );
      }
      if (url === "/api/jobs/job-2") {
        return Promise.resolve(
          new Response(
          JSON.stringify({
            job_id: "job-2",
            case_id: "handwrite233",
            status: "running",
            attempt_count: 1,
            error_message: null,
            evidence_ids: []
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
        );
      }
      if (url === "/api/worker/status") {
        return Promise.resolve(
          new Response(
          JSON.stringify({
            running: true,
            processed_count: 1,
            error_count: 0,
            last_error: null
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
        );
      }
      throw new Error(`Unexpected fetch: ${url}`);
    });

    render(<App />);
    await userEvent.type(screen.getByLabelText("Batch case ids"), "handwrite233 handwrite233");
    await userEvent.click(screen.getByRole("button", { name: "Submit batch jobs" }));
    await userEvent.click(await screen.findByRole("button", { name: "Start worker for batch" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/worker/start", { method: "POST" });
    expect(await screen.findByText("批量进度：1/2", {}, { timeout: 500 })).toBeInTheDocument();
    expect(screen.getByText("Worker running：true")).toBeInTheDocument();
    expect(await screen.findByText("Worker processed：1", {}, { timeout: 500 })).toBeInTheDocument();
  });

  it("imports JSONL cases and renders created jobs in the batch area", async () => {
    const jsonl = "{\"case_id\":\"imported-jsonl-1\"}";
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          imported_case_ids: ["imported-jsonl-1"],
          jobs: [{ job_id: "job-imported-1", case_id: "imported-jsonl-1", status: "created" }],
          rejected_lines: []
        }),
        { status: 202, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);
    fireEvent.change(screen.getByLabelText("JSONL cases"), { target: { value: jsonl } });
    await userEvent.click(screen.getByRole("button", { name: "Import JSONL cases" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/imports/jsonl", {
      body: JSON.stringify({ jsonl, create_jobs: true }),
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
    expect(await screen.findByText("导入样本：1")).toBeInTheDocument();
    expect(screen.getByText("导入拒绝：无")).toBeInTheDocument();
    expect(screen.getByText("批量创建：1")).toBeInTheDocument();
    expect(screen.getByText("job-imported-1：created")).toBeInTheDocument();
  });

  it("imports CSV cases and renders created jobs in the batch area", async () => {
    const csvText = "case_id,image_uri,prompt,golden_answer_json,scoring_standard,predictions_json,avg_score\n";
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          imported_case_ids: ["csv-import-1"],
          jobs: [{ job_id: "job-csv-1", case_id: "csv-import-1", status: "created" }],
          rejected_rows: []
        }),
        { status: 202, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);
    fireEvent.change(screen.getByLabelText("CSV cases"), { target: { value: csvText } });
    await userEvent.click(screen.getByRole("button", { name: "Import CSV cases" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/imports/csv", {
      body: JSON.stringify({ csv_text: csvText, create_jobs: true }),
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
    expect(await screen.findByText("CSV 导入样本：1")).toBeInTheDocument();
    expect(screen.getByText("CSV 导入拒绝：无")).toBeInTheDocument();
    expect(screen.getByText("批量创建：1")).toBeInTheDocument();
    expect(screen.getByText("job-csv-1：created")).toBeInTheDocument();
  });

  it("imports spreadsheet rows JSON and renders row sync results", async () => {
    const rows = [
      {
        sheet_row_id: "sheet-row-1",
        case_id: "spreadsheet-row-1",
        image_uri: "file://spreadsheet-row-1.png",
        prompt: "Read the answer",
        golden_answer_json: { answers: [{ box_id: 1, student_answer: "42" }] },
        scoring_standard: "exact match",
        predictions_json: [{ trial: 1, raw_output: "{\"answers\":[{\"box_id\":1,\"student_answer\":\"42\"}]}", score: 1 }],
        avg_score: 1
      }
    ];
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          imported_case_ids: ["spreadsheet-row-1"],
          imported_rows: [{ sheet_row_id: "sheet-row-1", case_id: "spreadsheet-row-1" }],
          jobs: [{ job_id: "job-spreadsheet-1", case_id: "spreadsheet-row-1", status: "created" }],
          rejected_rows: []
        }),
        { status: 202, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);
    fireEvent.change(screen.getByLabelText("Spreadsheet rows JSON"), { target: { value: JSON.stringify(rows) } });
    await userEvent.click(screen.getByRole("button", { name: "Import spreadsheet rows JSON" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/imports/spreadsheet-rows", {
      body: JSON.stringify({ rows, create_jobs: true }),
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
    expect(await screen.findByText("Spreadsheet 导入样本：1")).toBeInTheDocument();
    expect(screen.getByText("Spreadsheet 导入行：sheet-row-1:spreadsheet-row-1")).toBeInTheDocument();
    expect(screen.getByText("Spreadsheet 导入拒绝：无")).toBeInTheDocument();
    expect(screen.getByText("批量创建：1")).toBeInTheDocument();
    expect(screen.getByText("job-spreadsheet-1：created")).toBeInTheDocument();
  });

  it("loads imported case summaries and can copy them into batch submission", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            total_count: 5,
            filtered_count: 5,
            cases: [
              {
                case_id: "case-list-1",
                image_uri: "file://case-list-1.png",
                avg_score: 0.2,
                debug_status: "pending",
                root_cause: "visual_recognition_failure",
                box_region_count: 2
              },
              {
                case_id: "case-list-2",
                image_uri: "file://case-list-2.png",
                avg_score: 1,
                debug_status: "",
                root_cause: "",
                box_region_count: 0
              }
            ]
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            total_count: 5,
            filtered_count: 1,
            cases: [
              {
                case_id: "case-list-1",
                image_uri: "file://case-list-1.png",
                avg_score: 0.2,
                debug_status: "pending",
                root_cause: "visual_recognition_failure",
                box_region_count: 2
              }
            ]
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Load imported cases" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/cases?limit=50");
    expect(await screen.findByText("已导入样本：5")).toBeInTheDocument();
    expect(screen.getByText("已显示样本：2/5")).toBeInTheDocument();
    expect(screen.getByText("未加载样本：3")).toBeInTheDocument();
    expect(screen.getByText("case-list-1｜avg_score 0.2｜regions 2｜pending｜visual_recognition_failure")).toBeInTheDocument();
    expect(screen.getByText("case-list-2｜avg_score 1｜regions 0｜未标记｜未归因")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Only cases with regions" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/cases?has_regions=true&limit=50");
    expect(await screen.findByText("已显示样本：1/1")).toBeInTheDocument();
    expect(screen.getByText("未加载样本：0")).toBeInTheDocument();
    expect(screen.getByText("case-list-1｜avg_score 0.2｜regions 2｜pending｜visual_recognition_failure")).toBeInTheDocument();
    expect(screen.queryByText("case-list-2｜avg_score 1｜regions 0｜未标记｜未归因")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Use imported cases for batch" }));

    expect(screen.getByLabelText("Batch case ids")).toHaveValue("case-list-1");
  });

  it("loads more imported case summaries after the first page", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            total_count: 3,
            cases: [
              {
                case_id: "case-list-page-1",
                image_uri: "file://case-list-page-1.png",
                avg_score: 0.2,
                debug_status: "pending",
                root_cause: "visual_recognition_failure",
                box_region_count: 0
              },
              {
                case_id: "case-list-page-2",
                image_uri: "file://case-list-page-2.png",
                avg_score: 0.4,
                debug_status: "",
                root_cause: "",
                box_region_count: 0
              }
            ]
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            total_count: 3,
            cases: [
              {
                case_id: "case-list-page-3",
                image_uri: "file://case-list-page-3.png",
                avg_score: 1,
                debug_status: "done",
                root_cause: "no_issue",
                box_region_count: 1
              }
            ]
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Load imported cases" }));

    expect(await screen.findByText("未加载样本：1")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Load more imported cases" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/cases?limit=50");
    expect(fetchMock).toHaveBeenCalledWith("/api/cases?limit=50&offset=2");
    expect(await screen.findByText("case-list-page-3｜avg_score 1｜regions 1｜done｜no_issue")).toBeInTheDocument();
    expect(screen.getByText("已显示样本：3/3")).toBeInTheDocument();
    expect(screen.getByText("未加载样本：0")).toBeInTheDocument();
  });

  it("loads and renders imported case detail from the case list", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            cases: [
              {
                case_id: "case-list-1",
                image_uri: "file://case-list-1.png",
                avg_score: 0.2,
                debug_status: "pending",
                root_cause: "visual_recognition_failure"
              }
            ]
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            case_id: "case-list-1",
            image_uri: "file://case-list-1.png",
            prompt: "Read the handwritten answer",
            golden_answer: { answers: [{ box_id: 1, student_answer: "42" }] },
            scoring_standard: "exact match",
            predictions: [{ trial: 1, raw_output: "{\"answers\":[]}", score: 0 }],
            avg_score: 0.2,
            box_regions: [
              {
                box_id: 1,
                x: 12,
                y: 34,
                width: 56,
                height: 78,
                unit: "pixel",
                label: "answer-1"
              }
            ],
            human_notes: {
              debug_status: "pending",
              root_cause: "visual_recognition_failure"
            }
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Load imported cases" }));
    await userEvent.click(await screen.findByRole("button", { name: "View case detail case-list-1" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/cases/case-list-1");
    expect(await screen.findByText("样本详情：case-list-1")).toBeInTheDocument();
    expect(screen.getByText("图片：file://case-list-1.png")).toBeInTheDocument();
    expect(screen.getByText("Prompt：Read the handwritten answer")).toBeInTheDocument();
    expect(screen.getByText("评分标准：exact match")).toBeInTheDocument();
    expect(screen.getByText("标答 1：42")).toBeInTheDocument();
    expect(screen.getByText("区域 1：x=12, y=34, width=56, height=78, unit=pixel, label=answer-1")).toBeInTheDocument();
    expect(screen.getByText("预测 trial 1：score 0")).toBeInTheDocument();
    expect(screen.getByText("人工状态：pending")).toBeInTheDocument();
    expect(screen.getByText("人工根因：visual_recognition_failure")).toBeInTheDocument();
  });

  it("creates a debug job from the selected case detail", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            cases: [
              {
                case_id: "case-list-1",
                image_uri: "file://case-list-1.png",
                avg_score: 0.2,
                debug_status: "pending",
                root_cause: "visual_recognition_failure"
              }
            ]
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            case_id: "case-list-1",
            image_uri: "file://case-list-1.png",
            prompt: "Read the handwritten answer",
            golden_answer: { answers: [{ box_id: 1, student_answer: "42" }] },
            scoring_standard: "exact match",
            predictions: [{ trial: 1, raw_output: "{\"answers\":[]}", score: 0 }],
            avg_score: 0.2,
            human_notes: {
              debug_status: "pending",
              root_cause: "visual_recognition_failure"
            }
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-case-detail-1",
            case_id: "case-list-1",
            status: "created",
            attempt_count: 0,
            error_message: null,
            evidence_ids: []
          }),
          { status: 202, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Load imported cases" }));
    await userEvent.click(await screen.findByRole("button", { name: "View case detail case-list-1" }));
    await userEvent.click(await screen.findByRole("button", { name: "Create debug job for case-list-1" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/cases/case-list-1/debug-jobs?auto_run=true&baseline_trials=5", {
      method: "POST"
    });
    expect(await screen.findByText("Job ID：job-case-detail-1")).toBeInTheDocument();
    expect(screen.getByText("样本 ID：case-list-1")).toBeInTheDocument();
    expect(screen.getByText("状态：created")).toBeInTheDocument();
  });
});
