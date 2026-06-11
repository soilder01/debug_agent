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
            error_message: null,
            evidence_ids: ["handwrite233:baseline_replay:0"]
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Submit debug job" }));

    expect(await screen.findByText("样本 ID：handwrite233")).toBeInTheDocument();
    expect(screen.getByText("Job ID：job-123")).toBeInTheDocument();
    expect(screen.getByText("状态：created")).toBeInTheDocument();
    expect(screen.getByText("尝试次数：0")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/cases/handwrite233/debug-jobs?auto_run=true", {
      method: "POST"
    });

    expect(await screen.findByText("状态：completed", {}, { timeout: 500 })).toBeInTheDocument();
    expect(screen.getByText("尝试次数：1")).toBeInTheDocument();
    expect(screen.getByText("证据数：1")).toBeInTheDocument();
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
            evidence_ids: []
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
    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-1");
    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-2");
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
            status: "running",
            attempt_count: 1,
            error_message: null,
            evidence_ids: []
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
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
      );

    render(<App />);
    await userEvent.type(screen.getByLabelText("Batch case ids"), "handwrite233 handwrite233");
    await userEvent.click(screen.getByRole("button", { name: "Submit batch jobs" }));
    await userEvent.click(await screen.findByRole("button", { name: "Start worker for batch" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/worker/start", { method: "POST" });
    expect(await screen.findByText("批量进度：0/2")).toBeInTheDocument();
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

  it("loads imported case summaries and can copy them into batch submission", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          cases: [
            {
              case_id: "case-list-1",
              image_uri: "file://case-list-1.png",
              avg_score: 0.2,
              debug_status: "pending",
              root_cause: "visual_recognition_failure"
            },
            {
              case_id: "case-list-2",
              image_uri: "file://case-list-2.png",
              avg_score: 1,
              debug_status: "",
              root_cause: ""
            }
          ]
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Load imported cases" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/cases");
    expect(await screen.findByText("已导入样本：2")).toBeInTheDocument();
    expect(screen.getByText("case-list-1｜avg_score 0.2｜pending｜visual_recognition_failure")).toBeInTheDocument();
    expect(screen.getByText("case-list-2｜avg_score 1｜未标记｜未归因")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Use imported cases for batch" }));

    expect(screen.getByLabelText("Batch case ids")).toHaveValue("case-list-1\ncase-list-2");
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

    expect(fetchMock).toHaveBeenCalledWith("/api/cases/case-list-1/debug-jobs?auto_run=true", {
      method: "POST"
    });
    expect(await screen.findByText("Job ID：job-case-detail-1")).toBeInTheDocument();
    expect(screen.getByText("样本 ID：case-list-1")).toBeInTheDocument();
    expect(screen.getByText("状态：created")).toBeInTheDocument();
  });
});
