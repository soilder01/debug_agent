import { App, describe, expect, fireEvent, it, openTab, render, screen, userEvent, vi } from "./App.test.setup";

describe("App Imports Workspace", () => {
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
    await openTab("数据导入");
    fireEvent.change(screen.getByLabelText("JSONL 案件数据"), { target: { value: jsonl } });
    await userEvent.click(screen.getByRole("button", { name: "导入 JSONL 案件" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/imports/jsonl", {
      body: JSON.stringify({ jsonl, create_jobs: true }),
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
    expect(await screen.findByText("导入样本：1")).toBeInTheDocument();
    expect(screen.getByText("导入拒绝：无")).toBeInTheDocument();
    expect(screen.getByText("批量创建：1")).toBeInTheDocument();
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
    await openTab("数据导入");
    fireEvent.change(screen.getByLabelText("CSV 案件数据"), { target: { value: csvText } });
    await userEvent.click(screen.getByRole("button", { name: "导入 CSV 案件" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/imports/csv", {
      body: JSON.stringify({ csv_text: csvText, create_jobs: true }),
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
    expect(await screen.findByText("CSV 导入样本：1")).toBeInTheDocument();
    expect(screen.getByText("CSV 导入拒绝：无")).toBeInTheDocument();
    expect(screen.getByText("批量创建：1")).toBeInTheDocument();
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
    await openTab("数据导入");
    fireEvent.change(screen.getByRole("textbox", { name: "飞书行 JSON" }), { target: { value: JSON.stringify(rows) } });
    await userEvent.click(screen.getByRole("button", { name: "导入飞书行 JSON" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/imports/spreadsheet-rows", {
      body: JSON.stringify({ rows, create_jobs: true }),
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
    expect(await screen.findByText("表格导入样本：1")).toBeInTheDocument();
    expect(screen.getByText("表格导入行：sheet-row-1:spreadsheet-row-1")).toBeInTheDocument();
    expect(screen.getByText("表格导入拒绝：无")).toBeInTheDocument();
    expect(screen.getByText("批量创建：1")).toBeInTheDocument();
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
    await openTab("数据导入");
    await userEvent.click(screen.getByRole("button", { name: "加载导入样本" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/cases?limit=50");
    expect(await screen.findByText("已导入样本：5")).toBeInTheDocument();
    expect(screen.getByText("已显示样本：2/5")).toBeInTheDocument();
    expect(screen.getByText("未加载样本：3")).toBeInTheDocument();
    expect(screen.getByText("case-list-1｜平均分 0.2｜区域 2｜pending｜visual_recognition_failure")).toBeInTheDocument();
    expect(screen.getByText("case-list-2｜平均分 1｜区域 0｜未标记｜未归因")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "只看有区域的样本" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/cases?has_regions=true&limit=50");
    expect(await screen.findByText("已显示样本：1/1")).toBeInTheDocument();
    expect(screen.getByText("未加载样本：0")).toBeInTheDocument();
    expect(screen.getByText("case-list-1｜平均分 0.2｜区域 2｜pending｜visual_recognition_failure")).toBeInTheDocument();
    expect(screen.queryByText("case-list-2｜平均分 1｜区域 0｜未标记｜未归因")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "用导入样本创建批次" }));

    expect(screen.getByLabelText("批量样本 ID")).toHaveValue("case-list-1");
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
    await openTab("数据导入");
    await userEvent.click(screen.getByRole("button", { name: "加载导入样本" }));

    expect(await screen.findByText("未加载样本：1")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "加载更多导入样本" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/cases?limit=50");
    expect(fetchMock).toHaveBeenCalledWith("/api/cases?limit=50&offset=2");
    expect(await screen.findByText("case-list-page-3｜平均分 1｜区域 1｜done｜no_issue")).toBeInTheDocument();
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
    await openTab("数据导入");
    await userEvent.click(screen.getByRole("button", { name: "加载导入样本" }));
    await userEvent.click(await screen.findByRole("button", { name: "查看样本详情 case-list-1" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/cases/case-list-1");
    expect(await screen.findByText("样本详情：case-list-1")).toBeInTheDocument();
    expect(screen.getByText("图片：file://case-list-1.png")).toBeInTheDocument();
    expect(screen.getByText("Prompt：Read the handwritten answer")).toBeInTheDocument();
    expect(screen.getByText("评分标准：exact match")).toBeInTheDocument();
    expect(screen.getByText("标答 1：42")).toBeInTheDocument();
    expect(screen.getByText("区域 1：x=12, y=34, width=56, height=78, unit=pixel, label=answer-1")).toBeInTheDocument();
    expect(screen.getByText("预测轮次 1：得分 0")).toBeInTheDocument();
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
    await openTab("数据导入");
    await userEvent.click(screen.getByRole("button", { name: "加载导入样本" }));
    await userEvent.click(await screen.findByRole("button", { name: "查看样本详情 case-list-1" }));
    await userEvent.click(await screen.findByRole("button", { name: "为 case-list-1 创建调试任务" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/cases/case-list-1/debug-jobs?auto_run=true&baseline_trials=5", {
      method: "POST"
    });
    expect(await screen.findByText("任务 ID：job-case-detail-1")).toBeInTheDocument();
    expect(screen.getByText("样本 ID：case-list-1")).toBeInTheDocument();
    expect(screen.getByText("状态：已创建")).toBeInTheDocument();
  });
});
