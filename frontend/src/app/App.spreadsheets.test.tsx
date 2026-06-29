import { App, describe, expect, fireEvent, it, openTab, render, screen, userEvent, vi } from "./App.test.setup";

describe("App Spreadsheet Workspace", () => {
  it("syncs spreadsheet rows through the configured backend client", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          imported_case_ids: ["synced-sheet-case-1"],
          imported_rows: [{ sheet_row_id: "sheet-row-7", case_id: "synced-sheet-case-1" }],
          rejected_rows: [],
          jobs: [{ job_id: "job-synced-sheet-1", case_id: "synced-sheet-case-1", status: "created" }]
        }),
        { status: 202, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);
    await openTab("回写同步");
    expect(screen.getByLabelText("表格 Token")).toHaveValue("testSpreadsheetToken123");
    expect(screen.getByLabelText("工作表 ID")).toHaveValue("testSheet123");
    fireEvent.change(screen.getByLabelText("表格 Token"), { target: { value: "spreadsheet-1" } });
    fireEvent.change(screen.getByLabelText("工作表 ID"), { target: { value: "sheet-1" } });
    await userEvent.click(screen.getByRole("button", { name: "同步表格行" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/spreadsheets/sync", {
      body: JSON.stringify({
        spreadsheet_url: "https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123",
        spreadsheet_id: "spreadsheet-1",
        sheet_id: "sheet-1",
        create_jobs: true,
        baseline_trials: 5
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
    expect(await screen.findByText("表格同步样本：1")).toBeInTheDocument();
    expect(screen.getByText("表格同步行：sheet-row-7:synced-sheet-case-1")).toBeInTheDocument();
    expect(screen.getByText("表格同步拒绝：无")).toBeInTheDocument();
    expect(screen.getByText("表格同步任务：1")).toBeInTheDocument();
  });


  it("checks Lark spreadsheet configuration and connectivity", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          configured: true,
          spreadsheet_id: "testSpreadsheetToken123",
          sheet_id: "testSheet123",
          lark_cli_timeout_seconds: 60,
          connectivity_status: "ok",
          error_message: ""
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);
    await openTab("回写同步");
    await userEvent.click(screen.getByRole("button", { name: "检查飞书连接" }));

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/spreadsheets/lark/status?check_connectivity=true&spreadsheet_url=https%3A%2F%2Fexample.larkoffice.com%2Fsheets%2FtestSpreadsheetToken123%3Fsheet%3DtestSheet123&spreadsheet_id=testSpreadsheetToken123&sheet_id=testSheet123"
    );
    expect(await screen.findByText("Lark 配置状态：已配置")).toBeInTheDocument();
    expect(screen.getByText("Lark 连接状态：正常")).toBeInTheDocument();
    expect(screen.getByText("Lark 表格：testSpreadsheetToken123 / testSheet123")).toBeInTheDocument();
    expect(screen.getByText("Lark CLI 超时：60s")).toBeInTheDocument();
  });


  it("loads spreadsheet writeback audit summary counts", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          by_status: {
            succeeded: 8,
            failed: 2,
            skipped: 3
          },
          total_count: 13
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);
    await openTab("回写同步");
    await userEvent.click(screen.getByRole("button", { name: "加载审计概览" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/spreadsheets/writeback/audits/summary");
    expect(await screen.findByText("审计总数：13")).toBeInTheDocument();
    expect(screen.getByText("写回成功：8")).toBeInTheDocument();
    expect(screen.getByText("写回失败：2")).toBeInTheDocument();
    expect(screen.getByText("写回跳过：3")).toBeInTheDocument();
  });


  it("drills down from writeback audit summary counts", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            by_status: {
              succeeded: 8,
              failed: 2,
              skipped: 3
            },
            total_count: 13
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            audits: [
              {
                job_id: "job-failed-writeback-1",
                status: "failed",
                row_id: "7",
                report_url: "https://debug-agent.local/jobs/job-failed-writeback-1/report",
                fields: {},
                error_message: "permission denied",
                created_at: "2026-06-12T06:00:00+00:00",
                updated_at: "2026-06-12T06:00:01+00:00"
              }
            ],
            total_count: 2
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await openTab("回写同步");
    await userEvent.click(screen.getByRole("button", { name: "加载审计概览" }));
    await userEvent.click(await screen.findByRole("button", { name: "查看失败审计" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/spreadsheets/writeback/audits?status=failed&limit=50");
    expect(await screen.findByText("审计记录总数：2")).toBeInTheDocument();
    expect(screen.getByText("job-failed-writeback-1：失败｜行 7｜permission denied")).toBeInTheDocument();
  });


  it("loads failed spreadsheet writeback audits for drilldown", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          audits: [
            {
              job_id: "job-failed-writeback-1",
              status: "failed",
              row_id: "7",
              report_url: "https://debug-agent.local/jobs/job-failed-writeback-1/report",
              fields: {},
              error_message: "permission denied",
              created_at: "2026-06-12T06:00:00+00:00",
              updated_at: "2026-06-12T06:00:01+00:00"
            }
          ],
          total_count: 3
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);
    await openTab("回写同步");
    await userEvent.click(screen.getByRole("button", { name: "加载失败审计" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/spreadsheets/writeback/audits?status=failed&limit=50");
    expect(await screen.findByText("审计记录总数：3")).toBeInTheDocument();
    expect(screen.getAllByText("当前筛选：失败").length).toBeGreaterThan(0);
    expect(screen.getByText("job-failed-writeback-1：失败｜行 7｜permission denied")).toBeInTheDocument();
  });


  it("shows retry eligibility for failed spreadsheet writeback audits", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          audits: [
            {
              job_id: "job-failed-writeback-1",
              status: "failed",
              row_id: "7",
              report_url: "https://debug-agent.local/jobs/job-failed-writeback-1/report",
              fields: {},
              error_message: "permission denied",
              created_at: "2026-06-12T06:00:00+00:00",
              updated_at: "2026-06-12T06:00:01+00:00"
            }
          ],
          total_count: 1
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);
    await openTab("回写同步");
    await userEvent.click(screen.getByRole("button", { name: "加载失败审计" }));

    expect(await screen.findByText("可重试：是")).toBeInTheDocument();
  });


  it("shows retry reason for failed spreadsheet writeback audits", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          audits: [
            {
              job_id: "job-failed-writeback-1",
              status: "failed",
              row_id: "7",
              report_url: "https://debug-agent.local/jobs/job-failed-writeback-1/report",
              fields: {},
              error_message: "permission denied",
              created_at: "2026-06-12T06:00:00+00:00",
              updated_at: "2026-06-12T06:00:01+00:00"
            }
          ],
          total_count: 1
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);
    await openTab("回写同步");
    await userEvent.click(screen.getByRole("button", { name: "加载失败审计" }));

    expect(await screen.findByText("重试原因：上次写回失败：permission denied")).toBeInTheDocument();
  });


  it("loads succeeded spreadsheet writeback audits for drilldown", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          audits: [
            {
              job_id: "job-succeeded-writeback-1",
              status: "succeeded",
              row_id: "9",
              report_url: "https://debug-agent.local/jobs/job-succeeded-writeback-1/report",
              fields: { 错误原因: "model_weakness" },
              error_message: "",
              created_at: "2026-06-12T06:00:00+00:00",
              updated_at: "2026-06-12T06:00:01+00:00"
            }
          ],
          total_count: 4
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);
    await openTab("回写同步");
    await userEvent.click(screen.getByRole("button", { name: "加载成功审计" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/spreadsheets/writeback/audits?status=succeeded&limit=50");
    expect(await screen.findByText("审计记录总数：4")).toBeInTheDocument();
    expect(screen.getByText("job-succeeded-writeback-1：成功｜行 9｜无错误")).toBeInTheDocument();
  });


  it("hides retry action for succeeded spreadsheet writeback audits", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          audits: [
            {
              job_id: "job-succeeded-writeback-1",
              status: "succeeded",
              row_id: "9",
              report_url: "https://debug-agent.local/jobs/job-succeeded-writeback-1/report",
              fields: { 错误原因: "model_weakness" },
              error_message: "",
              created_at: "2026-06-12T06:00:00+00:00",
              updated_at: "2026-06-12T06:00:01+00:00"
            }
          ],
          total_count: 1
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);
    await openTab("回写同步");
    await userEvent.click(screen.getByRole("button", { name: "加载成功审计" }));

    expect(await screen.findByText("job-succeeded-writeback-1：成功｜行 9｜无错误")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "重试写回 job-succeeded-writeback-1" })).not.toBeInTheDocument();
  });


  it("shows retry reason for succeeded spreadsheet writeback audits", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          audits: [
            {
              job_id: "job-succeeded-writeback-1",
              status: "succeeded",
              row_id: "9",
              report_url: "https://debug-agent.local/jobs/job-succeeded-writeback-1/report",
              fields: { 错误原因: "model_weakness" },
              error_message: "",
              created_at: "2026-06-12T06:00:00+00:00",
              updated_at: "2026-06-12T06:00:01+00:00"
            }
          ],
          total_count: 1
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);
    await openTab("回写同步");
    await userEvent.click(screen.getByRole("button", { name: "加载成功审计" }));

    expect(await screen.findByText("重试原因：已经写回成功")).toBeInTheDocument();
  });


  it("shows persisted fields for succeeded spreadsheet writeback audits", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          audits: [
            {
              job_id: "job-succeeded-writeback-1",
              status: "succeeded",
              row_id: "9",
              report_url: "https://debug-agent.local/jobs/job-succeeded-writeback-1/report",
              fields: {
                错误原因: "model_weakness",
                分析报告链接: "https://debug-agent.local/jobs/job-succeeded-writeback-1/report"
              },
              error_message: "",
              created_at: "2026-06-12T06:00:00+00:00",
              updated_at: "2026-06-12T06:00:01+00:00"
            }
          ],
          total_count: 1
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);
    await openTab("回写同步");
    await userEvent.click(screen.getByRole("button", { name: "加载成功审计" }));

    expect(await screen.findByText("写回字段：错误原因=model_weakness")).toBeInTheDocument();
    expect(
      screen.getByText("写回字段：分析报告链接=https://debug-agent.local/jobs/job-succeeded-writeback-1/report")
    ).toBeInTheDocument();
  });


  it("shows persisted field count for spreadsheet writeback audits", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          audits: [
            {
              job_id: "job-succeeded-writeback-1",
              status: "succeeded",
              row_id: "9",
              report_url: "https://debug-agent.local/jobs/job-succeeded-writeback-1/report",
              fields: {
                错误原因: "model_weakness",
                评估问题反馈: "prompt needs stricter rubric"
              },
              error_message: "",
              created_at: "2026-06-12T06:00:00+00:00",
              updated_at: "2026-06-12T06:00:01+00:00"
            }
          ],
          total_count: 1
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);
    await openTab("回写同步");
    await userEvent.click(screen.getByRole("button", { name: "加载成功审计" }));

    expect(await screen.findByText("写回字段数：2")).toBeInTheDocument();
  });


  it("opens a job from a spreadsheet writeback audit row", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            audits: [
              {
                job_id: "job-failed-writeback-1",
                status: "failed",
                row_id: "7",
                report_url: "https://debug-agent.local/jobs/job-failed-writeback-1/report",
                fields: {},
                error_message: "permission denied",
                created_at: "2026-06-12T06:00:00+00:00",
                updated_at: "2026-06-12T06:00:01+00:00"
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
            job_id: "job-failed-writeback-1",
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
            evidence_ids: [],
            evidence_error_counts: {
              total_evidence: 0,
              failed_judgements: 0,
              response_parse_errors: 0,
              model_call_errors: 0
            },
            spreadsheet_writeback_audit: {
              status: "failed",
              row_id: "7",
              report_url: "https://debug-agent.local/jobs/job-failed-writeback-1/report",
              error_message: "permission denied",
              updated_at: "2026-06-12T06:00:01+00:00"
            }
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await openTab("回写同步");
    await userEvent.click(screen.getByRole("button", { name: "加载失败审计" }));
    await userEvent.click(await screen.findByRole("button", { name: "打开任务 job-failed-writeback-1" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-failed-writeback-1");
    expect(await screen.findByText("任务 ID：job-failed-writeback-1")).toBeInTheDocument();
    expect(screen.getByText("写回状态：失败")).toBeInTheDocument();
    expect(screen.getByText("写回错误：permission denied")).toBeInTheDocument();
  });


  it("retries spreadsheet writeback from an audit row", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            audits: [
              {
                job_id: "job-failed-writeback-1",
                status: "failed",
                row_id: "7",
                report_url: "https://debug-agent.local/jobs/job-failed-writeback-1/report",
                fields: {},
                error_message: "permission denied",
                created_at: "2026-06-12T06:00:00+00:00",
                updated_at: "2026-06-12T06:00:01+00:00"
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
            row_id: "7",
            fields: {
              错误原因: "model_weakness",
              分析报告链接: "https://debug-agent.local/jobs/job-failed-writeback-1/report"
            }
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await openTab("回写同步");
    await userEvent.click(screen.getByRole("button", { name: "加载失败审计" }));
    await userEvent.click(await screen.findByRole("button", { name: "重试写回 job-failed-writeback-1" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-failed-writeback-1/spreadsheet-writeback", {
      body: JSON.stringify({
        report_url: `${window.location.origin}/api/jobs/job-failed-writeback-1/report`,
        spreadsheet_url: "https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123",
        spreadsheet_id: "testSpreadsheetToken123",
        sheet_id: "testSheet123",
        require_confirmation: false,
        confirmation_id: "",
        actor: "",
        note: ""
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
    expect(await screen.findByText("最近重试写回行：7")).toBeInTheDocument();
    expect(screen.getByText("错误原因：model_weakness")).toBeInTheDocument();
  });


  it("refreshes writeback audit list and summary after retrying an audit row", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            audits: [
              {
                job_id: "job-failed-writeback-1",
                status: "failed",
                row_id: "7",
                report_url: "https://debug-agent.local/jobs/job-failed-writeback-1/report",
                fields: {},
                error_message: "permission denied",
                created_at: "2026-06-12T06:00:00+00:00",
                updated_at: "2026-06-12T06:00:01+00:00"
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
            row_id: "7",
            fields: {
              错误原因: "model_weakness"
            }
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ audits: [], total_count: 0 }), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        })
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            by_status: {
              succeeded: 1,
              failed: 0,
              skipped: 0
            },
            total_count: 1
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await openTab("回写同步");
    await userEvent.click(screen.getByRole("button", { name: "加载失败审计" }));
    await userEvent.click(await screen.findByRole("button", { name: "重试写回 job-failed-writeback-1" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/spreadsheets/writeback/audits?status=failed&limit=50");
    expect(fetchMock).toHaveBeenCalledWith("/api/spreadsheets/writeback/audits/summary");
    expect(await screen.findByText("审计记录总数：0")).toBeInTheDocument();
    expect(screen.getByText("写回失败：0")).toBeInTheDocument();
    expect(screen.getByText("写回成功：1")).toBeInTheDocument();
  });


  it("shows report links in spreadsheet writeback audit rows", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          audits: [
            {
              job_id: "job-failed-writeback-1",
              status: "failed",
              row_id: "7",
              report_url: "https://debug-agent.local/jobs/job-failed-writeback-1/report",
              fields: {},
              error_message: "permission denied",
              created_at: "2026-06-12T06:00:00+00:00",
              updated_at: "2026-06-12T06:00:01+00:00"
            }
          ],
          total_count: 1
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);
    await openTab("回写同步");
    await userEvent.click(screen.getByRole("button", { name: "加载失败审计" }));

    const reportLink = await screen.findByRole("link", { name: "打开报告 job-failed-writeback-1" });
    expect(reportLink).toHaveAttribute("href", "https://debug-agent.local/jobs/job-failed-writeback-1/report");
  });


  it("loads all spreadsheet writeback audits without a status filter", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          audits: [
            {
              job_id: "job-succeeded-writeback-1",
              status: "succeeded",
              row_id: "9",
              report_url: "https://debug-agent.local/jobs/job-succeeded-writeback-1/report",
              fields: { 错误原因: "model_weakness" },
              error_message: "",
              created_at: "2026-06-12T06:00:00+00:00",
              updated_at: "2026-06-12T06:00:01+00:00"
            }
          ],
          total_count: 1
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);
    await openTab("回写同步");
    await userEvent.click(screen.getByRole("button", { name: "加载全部审计" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/spreadsheets/writeback/audits?limit=50");
    expect(await screen.findByText("job-succeeded-writeback-1：成功｜行 9｜无错误")).toBeInTheDocument();
    expect(screen.getAllByText("当前筛选：全部").length).toBeGreaterThan(0);
  });


  it("shows update timestamps in spreadsheet writeback audit rows", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          audits: [
            {
              job_id: "job-failed-writeback-1",
              status: "failed",
              row_id: "7",
              report_url: "https://debug-agent.local/jobs/job-failed-writeback-1/report",
              fields: {},
              error_message: "permission denied",
              created_at: "2026-06-12T06:00:00+00:00",
              updated_at: "2026-06-12T06:00:01+00:00"
            }
          ],
          total_count: 1
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);
    await openTab("回写同步");
    await userEvent.click(screen.getByRole("button", { name: "加载失败审计" }));

    expect(await screen.findByText("更新时间：2026-06-12T06:00:01+00:00")).toBeInTheDocument();
  });


  it("loads more spreadsheet writeback audits using the current status filter", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            audits: [
              {
                job_id: "job-failed-writeback-1",
                status: "failed",
                row_id: "7",
                report_url: "https://debug-agent.local/jobs/job-failed-writeback-1/report",
                fields: {},
                error_message: "permission denied",
                created_at: "2026-06-12T06:00:00+00:00",
                updated_at: "2026-06-12T06:00:01+00:00"
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
            audits: [
              {
                job_id: "job-failed-writeback-2",
                status: "failed",
                row_id: "8",
                report_url: "https://debug-agent.local/jobs/job-failed-writeback-2/report",
                fields: {},
                error_message: "sheet header not found",
                created_at: "2026-06-12T06:00:02+00:00",
                updated_at: "2026-06-12T06:00:03+00:00"
              }
            ],
            total_count: 2
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await openTab("回写同步");
    await userEvent.click(screen.getByRole("button", { name: "加载失败审计" }));
    await userEvent.click(await screen.findByRole("button", { name: "加载更多审计记录" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/spreadsheets/writeback/audits?status=failed&limit=50");
    expect(fetchMock).toHaveBeenCalledWith("/api/spreadsheets/writeback/audits?status=failed&limit=50&offset=1");
    expect(screen.getByText("job-failed-writeback-1：失败｜行 7｜permission denied")).toBeInTheDocument();
    expect(screen.getByText("job-failed-writeback-2：失败｜行 8｜sheet header not found")).toBeInTheDocument();
  });


  it("loads skipped spreadsheet writeback audits for drilldown", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          audits: [
            {
              job_id: "job-skipped-writeback-1",
              status: "skipped",
              row_id: "",
              report_url: "https://debug-agent.local/jobs/job-skipped-writeback-1/report",
              fields: {},
              error_message: "spreadsheet row mapping not found",
              created_at: "2026-06-12T06:00:00+00:00",
              updated_at: "2026-06-12T06:00:01+00:00"
            }
          ],
          total_count: 1
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);
    await openTab("回写同步");
    await userEvent.click(screen.getByRole("button", { name: "加载跳过审计" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/spreadsheets/writeback/audits?status=skipped&limit=50");
    expect(await screen.findByText("审计记录总数：1")).toBeInTheDocument();
    expect(
      screen.getByText("job-skipped-writeback-1：跳过｜行 无｜spreadsheet row mapping not found")
    ).toBeInTheDocument();
  });


  it("hides retry action for skipped spreadsheet writeback audits", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          audits: [
            {
              job_id: "job-skipped-writeback-1",
              status: "skipped",
              row_id: "",
              report_url: "https://debug-agent.local/jobs/job-skipped-writeback-1/report",
              fields: {},
              error_message: "spreadsheet row mapping not found",
              created_at: "2026-06-12T06:00:00+00:00",
              updated_at: "2026-06-12T06:00:01+00:00"
            }
          ],
          total_count: 1
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);
    await openTab("回写同步");
    await userEvent.click(screen.getByRole("button", { name: "加载跳过审计" }));

    expect(
      await screen.findByText("job-skipped-writeback-1：跳过｜行 无｜spreadsheet row mapping not found")
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "重试写回 job-skipped-writeback-1" })).not.toBeInTheDocument();
  });


  it("shows retry eligibility for skipped spreadsheet writeback audits", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          audits: [
            {
              job_id: "job-skipped-writeback-1",
              status: "skipped",
              row_id: "",
              report_url: "https://debug-agent.local/jobs/job-skipped-writeback-1/report",
              fields: {},
              error_message: "spreadsheet row mapping not found",
              created_at: "2026-06-12T06:00:00+00:00",
              updated_at: "2026-06-12T06:00:01+00:00"
            }
          ],
          total_count: 1
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);
    await openTab("回写同步");
    await userEvent.click(screen.getByRole("button", { name: "加载跳过审计" }));

    expect(await screen.findByText("可重试：否")).toBeInTheDocument();
  });


  it("shows retry reason for skipped spreadsheet writeback audits", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          audits: [
            {
              job_id: "job-skipped-writeback-1",
              status: "skipped",
              row_id: "",
              report_url: "https://debug-agent.local/jobs/job-skipped-writeback-1/report",
              fields: {},
              error_message: "spreadsheet row mapping not found",
              created_at: "2026-06-12T06:00:00+00:00",
              updated_at: "2026-06-12T06:00:01+00:00"
            }
          ],
          total_count: 1
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);
    await openTab("回写同步");
    await userEvent.click(screen.getByRole("button", { name: "加载跳过审计" }));

    expect(await screen.findByText("重试原因：跳过原因：spreadsheet row mapping not found")).toBeInTheDocument();
  });


  it("parses a Lark spreadsheet URL into sync identifiers", async () => {
    render(<App />);
    await openTab("回写同步");
    fireEvent.change(screen.getByLabelText("飞书表格链接"), {
      target: {
        value: "https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123"
      }
    });
    await userEvent.click(screen.getByRole("button", { name: "解析飞书表格链接" }));

    expect(screen.getByLabelText("表格 Token")).toHaveValue("testSpreadsheetToken123");
    expect(screen.getByLabelText("工作表 ID")).toHaveValue("testSheet123");
  });
});
