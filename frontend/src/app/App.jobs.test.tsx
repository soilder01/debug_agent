import { App, describe, expect, it, openTab, render, screen, userEvent, vi } from "./App.test.setup";

describe("App Jobs Workspace", () => {
  it("guides users to select a case before submitting a single debug job", async () => {
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
    await userEvent.click(screen.getByRole("button", { name: "提交调试任务" }));

    expect(fetchMock).not.toHaveBeenCalled();
    expect(await screen.findByRole("alert")).toHaveTextContent("请先在数据导入或飞书同步结果中选择一个案件，再提交调试任务。");
    expect(screen.getByRole("heading", { name: "数据导入" })).toBeInTheDocument();
  });


  it("keeps the single-case shortcut from running without a selected case", async () => {
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
    await userEvent.click(screen.getByRole("button", { name: "提交调试任务" }));

    expect(fetchMock).not.toHaveBeenCalled();
    expect(await screen.findByRole("alert")).toHaveTextContent("请先在数据导入或飞书同步结果中选择一个案件");
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
    await userEvent.type(screen.getByLabelText("批量样本 ID"), "handwrite233\nmissing-case");
    await userEvent.click(screen.getByRole("button", { name: "批量提交调试" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/debug-jobs/batch", {
      body: JSON.stringify({ case_ids: ["handwrite233", "missing-case"], max_concurrency: 1 }),
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
    await userEvent.type(screen.getByLabelText("批量样本 ID"), "handwrite233 handwrite233");
    await userEvent.click(screen.getByRole("button", { name: "批量提交调试" }));

    expect(await screen.findByText("批量创建：2")).toBeInTheDocument();
    expect(screen.getByText("job-1：已创建")).toBeInTheDocument();
    expect(screen.getByText("job-2：已创建")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalledWith("/api/jobs/job-1");
    expect(fetchMock).not.toHaveBeenCalledWith("/api/jobs/job-2");
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
    await userEvent.click(screen.getByRole("button", { name: "查看历史任务" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs?limit=50");
    expect(await screen.findByText("队列任务：1")).toBeInTheDocument();
    expect(screen.getByText("总任务：5")).toBeInTheDocument();
    expect(screen.getByText("未加载：4")).toBeInTheDocument();
    expect(screen.getByText("job-history-1：失败")).toBeInTheDocument();
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
    expect(screen.getByText("job-history-1 级别：严重")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "打开任务 job-history-1" }));

    expect(screen.getByText("任务 ID：job-history-1")).toBeInTheDocument();
    expect(screen.getByText("建议动作：不要继续自动重试，转人工检查任务错误和证据链。")).toBeInTheDocument();

    await userEvent.click(
      screen.getByRole("button", { name: "查看任务 job-history-1 的证据 handwrite233:baseline_replay:0" })
    );

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-history-1/evidence/handwrite233%3Abaseline_replay%3A0");
    expect(await screen.findByText("证据 ID：handwrite233:baseline_replay:0")).toBeInTheDocument();
    expect(screen.getByText("模型 Provider：ark")).toBeInTheDocument();
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
    await userEvent.click(screen.getByRole("button", { name: "查看失败任务" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs?status=failed&limit=50");
    expect(await screen.findByText("失败任务：1")).toBeInTheDocument();
    expect(screen.getByText("总任务：3")).toBeInTheDocument();
    expect(screen.getByText("未加载：2")).toBeInTheDocument();
    expect(await screen.findByText("job-failed-1：失败")).toBeInTheDocument();
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
    await userEvent.click(screen.getByRole("button", { name: "查看最新任务" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs?limit=50&sort=created_at_desc");
    expect(await screen.findByText("最新任务：1")).toBeInTheDocument();
    expect(screen.getByText("job-newest-1：已完成")).toBeInTheDocument();
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
    await userEvent.click(screen.getByRole("button", { name: "查看历史任务" }));

    expect(await screen.findByText("未加载：1")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "加载更多调试任务" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs?limit=50");
    expect(fetchMock).toHaveBeenCalledWith("/api/jobs?limit=50&offset=1");
    expect(await screen.findByText("job-history-page-2：失败")).toBeInTheDocument();
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
            last_error: null,
            completion_hook_enabled: true,
            report_base_url: "https://debug-agent.local",
            auto_writeback_enabled: true
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
            last_error: null,
            completion_hook_enabled: true,
            report_base_url: "https://debug-agent.local",
            auto_writeback_enabled: true
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
            last_error: null,
            completion_hook_enabled: true,
            report_base_url: "https://debug-agent.local",
            auto_writeback_enabled: true
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await openTab("操作监控");
    await userEvent.click(screen.getByRole("button", { name: "启动后台进程" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/worker/start", { method: "POST" });
    expect(await screen.findByText("进程运行中：是")).toBeInTheDocument();
    expect(await screen.findByText("已处理任务：1", {}, { timeout: 500 })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "停止后台进程" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/worker/stop", { method: "POST" });
    expect(await screen.findByText("进程运行中：否")).toBeInTheDocument();
    expect(screen.getByText("进程错误：0")).toBeInTheDocument();
    expect(screen.getByText("自动回写配置：开启")).toBeInTheDocument();
    expect(screen.getByText("完成回调：开启")).toBeInTheDocument();
    expect(screen.getByText("报告基础 URL：https://debug-agent.local")).toBeInTheDocument();
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
    await userEvent.type(screen.getByLabelText("批量样本 ID"), "handwrite233 handwrite233");
    await userEvent.click(screen.getByRole("button", { name: "批量提交调试" }));
    await userEvent.click(await screen.findByRole("button", { name: "启动批量处理进程" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/worker/start", { method: "POST" });
    expect(await screen.findByText("批量进度：1/2", {}, { timeout: 500 })).toBeInTheDocument();
    expect(screen.getByText("后台进程运行中：是")).toBeInTheDocument();
    expect(await screen.findByText("后台进程已处理：1", {}, { timeout: 500 })).toBeInTheDocument();
  });
});
