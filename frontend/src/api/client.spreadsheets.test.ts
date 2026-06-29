import {
  describe,
  expect,
  it,
  vi,
  confirmLarkWriteConfirmation,
  createJobReportWritebackConfirmation,
  fetchLarkSpreadsheetStatus,
  rerunSpreadsheetRows,
  syncSpreadsheetRows,
  writeJobReportToSpreadsheet
} from "./client.test.setup";

describe("api client spreadsheets", () => {
  it("passes visible spreadsheet URL through status and sync requests", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            configured: true,
            spreadsheet_id: "sheet-token",
            sheet_id: "tab-id",
            lark_cli_timeout_seconds: 60,
            connectivity_status: "ok",
            error_message: ""
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            imported_case_ids: [],
            imported_rows: [],
            jobs: [],
            rejected_rows: []
          }),
          { status: 202, headers: { "Content-Type": "application/json" } }
        )
      );

    await fetchLarkSpreadsheetStatus(true, {
      spreadsheetUrl: "https://example.larkoffice.com/sheets/sheet-token?sheet=tab-id",
      spreadsheetId: "sheet-token",
      sheetId: "tab-id"
    });
    await syncSpreadsheetRows("sheet-token", "tab-id", true, 5, "https://example.larkoffice.com/sheets/sheet-token?sheet=tab-id");

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/spreadsheets/lark/status?check_connectivity=true&spreadsheet_url=https%3A%2F%2Fexample.larkoffice.com%2Fsheets%2Fsheet-token%3Fsheet%3Dtab-id&spreadsheet_id=sheet-token&sheet_id=tab-id"
    );
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/spreadsheets/sync", {
      body: JSON.stringify({
        spreadsheet_url: "https://example.larkoffice.com/sheets/sheet-token?sheet=tab-id",
        spreadsheet_id: "sheet-token",
        sheet_id: "tab-id",
        create_jobs: true,
        baseline_trials: 5
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
  });


  it("creates and confirms Lark write confirmations", async () => {
    const confirmation = {
      confirmation_id: "confirm-1",
      actor: "local-dev-operator",
      service: "sheets",
      operation: "+cells-set",
      resource_id: "resource",
      resource_summary: "写回任务 job-1",
      risk_action: "sheets +cells-set",
      required_scopes: ["sheets:spreadsheet"],
      status: "pending",
      note: "",
      created_at: "2026-06-22T00:00:00+00:00",
      expires_at: "2026-06-22T00:30:00+00:00",
      confirmed_at: "",
      confirmed_by: ""
    };
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify(confirmation), { status: 200, headers: { "Content-Type": "application/json" } })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ...confirmation, status: "confirmed", confirmed_by: "local-dev-operator" }), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        })
      );

    await createJobReportWritebackConfirmation("job-1", {
      reportUrl: "https://debug-agent.local/report",
      spreadsheetUrl: "https://example.larkoffice.com/sheets/sheet?sheet=tab",
      spreadsheetId: "sheet",
      sheetId: "tab",
      actor: "local-dev-operator",
      note: "reviewed"
    });
    await confirmLarkWriteConfirmation("confirm-1", { actor: "local-dev-operator", note: "confirmed" });

    expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/jobs/job-1/spreadsheet-writeback/confirmation", {
      body: JSON.stringify({
        report_url: "https://debug-agent.local/report",
        spreadsheet_url: "https://example.larkoffice.com/sheets/sheet?sheet=tab",
        spreadsheet_id: "sheet",
        sheet_id: "tab",
        actor: "local-dev-operator",
        note: "reviewed"
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/lark/write-confirmations/confirm-1/confirm", {
      body: JSON.stringify({ actor: "local-dev-operator", note: "confirmed" }),
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
  });


  it("sends optional write confirmation fields when writing a report", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ row_id: "7", fields: {} }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      })
    );

    await writeJobReportToSpreadsheet("job-1", "https://debug-agent.local/report", {
      spreadsheetUrl: "https://example.larkoffice.com/sheets/sheet?sheet=tab",
      spreadsheetId: "sheet",
      sheetId: "tab",
      requireConfirmation: true,
      confirmationId: "confirm-1",
      actor: "local-dev-operator",
      note: "confirmed"
    });

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-1/spreadsheet-writeback", {
      body: JSON.stringify({
        report_url: "https://debug-agent.local/report",
        spreadsheet_url: "https://example.larkoffice.com/sheets/sheet?sheet=tab",
        spreadsheet_id: "sheet",
        sheet_id: "tab",
        require_confirmation: true,
        confirmation_id: "confirm-1",
        actor: "local-dev-operator",
        note: "confirmed"
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
  });


  it("surfaces spreadsheet sync backend error details", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Lark spreadsheet operation failed: lark-cli" }), {
        status: 502,
        headers: { "Content-Type": "application/json" }
      })
    );

    await expect(syncSpreadsheetRows("sheet-token", "tab-id")).rejects.toThrow(
      "同步飞书表格行失败: 502 - Lark spreadsheet operation failed: lark-cli"
    );
  });


  it("reruns selected spreadsheet rows with auto run enabled", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          imported_case_ids: ["JSZN-131"],
          imported_rows: [{ sheet_row_id: "2", case_id: "JSZN-131" }],
          rejected_rows: [],
          skipped_row_ids: ["3"],
          jobs: [{ job_id: "job-131", case_id: "JSZN-131", status: "completed" }],
          auto_closure_reports: [
            {
              job_id: "job-131",
              case_id: "JSZN-131",
              closure: {
                source_job_id: "job-131",
                created_targeted_probe_jobs: ["job-probe-131"],
                created_strategy_follow_up_jobs: [],
                created_verification_jobs: ["job-verify-131"],
                evidence_summaries: [],
                targeted_probe_outcomes: [],
                final_attribution_candidates: [],
                badcase_live_comparison: {
                  original_badcase: "原 badcase：0/1 通过，avg_score=0.0。",
                  live_rerun: "Live 复测：0/1 通过，success_rate=0%。",
                  decision: "model_capability_gap"
                },
                writeback_status: "succeeded"
              },
              report_artifact_url: "/api/artifacts/files/JSZN-131_auto_closure_report.md",
              writeback_status: "succeeded"
            }
          ]
        }),
        { status: 202, headers: { "Content-Type": "application/json" } }
      )
    );

    const response = await rerunSpreadsheetRows({
      spreadsheetId: "sheet-token",
      sheetId: "tab-id",
      spreadsheetUrl: "https://example.larkoffice.com/sheets/sheet-token?sheet=tab-id",
      rowIds: ["2"],
      baselineTrials: 3,
      autoRun: true,
      autoClosure: true,
      submitControlledProbes: true,
      writeback: true
    });

    expect(fetchMock).toHaveBeenCalledWith("/api/spreadsheets/rerun", {
      body: JSON.stringify({
        spreadsheet_url: "https://example.larkoffice.com/sheets/sheet-token?sheet=tab-id",
        spreadsheet_id: "sheet-token",
        sheet_id: "tab-id",
        row_ids: ["2"],
        baseline_trials: 3,
        auto_run: true,
        auto_closure: true,
        submit_controlled_probes: true,
        writeback: true
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
    expect(response.imported_case_ids).toEqual(["JSZN-131"]);
    expect(response.skipped_row_ids).toEqual(["3"]);
    expect(response.jobs[0].status).toBe("completed");
    expect(response.auto_closure_reports[0].report_artifact_url).toBe(
      "/api/artifacts/files/JSZN-131_auto_closure_report.md"
    );
  });
});
