import { App, describe, expect, it, render, screen, userEvent, vi } from "./App.test.setup";

describe("App Reports Workspace", () => {
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
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            row_id: "row-42",
            fields: {
              "错误原因": "模型无法稳定识别涂改后的最终答案。",
              "评估问题反馈": "复测稳定性：unstable",
              "分析报告链接": `${window.location.origin}/api/jobs/job-report-1/report`
            }
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-report-1",
            status: "succeeded",
            row_id: "row-42",
            report_url: `${window.location.origin}/api/jobs/job-report-1/report`,
            fields: {
              "错误原因": "模型无法稳定识别涂改后的最终答案。"
            },
            error_message: "",
            created_at: "2026-06-12T06:00:00+00:00",
            updated_at: "2026-06-12T06:00:01+00:00"
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "查看历史任务" }));
    await userEvent.click(await screen.findByRole("button", { name: "打开任务 job-report-1" }));
    await userEvent.click(screen.getByRole("button", { name: "加载任务报告" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-report-1/report");
    expect(await screen.findAllByText("样本 ID：handwrite233")).toHaveLength(2);
    expect(screen.getByText("类型：erasure_revision_failure/medium")).toBeInTheDocument();
    expect(screen.getByText("复测稳定性：unstable")).toBeInTheDocument();
    expect(screen.getByText("错误原因")).toBeInTheDocument();
    expect(screen.getByText("模型无法稳定识别涂改后的最终答案。")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "写回报告到表格" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-report-1/spreadsheet-writeback", {
      body: JSON.stringify({
        report_url: `${window.location.origin}/api/jobs/job-report-1/report`,
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
    expect(await screen.findByText("表格写回行：row-42")).toBeInTheDocument();
    expect(
      screen.getByText(`分析报告链接：${window.location.origin}/api/jobs/job-report-1/report`)
    ).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "加载审计预览" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-report-1/spreadsheet-writeback/audit");
    expect(await screen.findByText("写回审计状态：成功")).toBeInTheDocument();
    expect(screen.getByText("写回行：row-42")).toBeInTheDocument();
    expect(screen.getByText("更新时间：2026-06-12T06:00:01+00:00")).toBeInTheDocument();
  });


  it("creates a high-risk Lark write confirmation before confirmed writeback", async () => {
    const confirmation = {
      confirmation_id: "confirm-write-1",
      actor: "local-dev-operator",
      service: "sheets",
      operation: "+cells-set",
      resource_id: "sheets:testSpreadsheetToken123:testSheet123:row-42:job:job-confirm-1",
      resource_summary: "写回任务 job-confirm-1 到表格 testSpreadsheetToken123/testSheet123 行 row-42",
      risk_action: "sheets +cells-set",
      required_scopes: ["sheets:spreadsheet"],
      status: "pending",
      note: "人工确认前预检写回目标",
      created_at: "2026-06-22T00:00:00+00:00",
      expires_at: "2026-06-22T00:30:00+00:00",
      confirmed_at: "",
      confirmed_by: ""
    };
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            jobs: [
              {
                job_id: "job-confirm-1",
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
                evidence_error_counts: {}
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
            job_id: "job-confirm-1",
            case_id: "handwrite233",
            status: "needs_human_review",
            observed_failure: {
              type: "erasure_revision_failure",
              summary: "模型在涂改区域识别不稳定。",
              affected_box_ids: [1]
            },
            planned_experiments: ["baseline_replay"],
            experiment_summary: null,
            root_cause: {
              label: "erasure_revision_failure",
              confidence: "medium",
              evidence_summary: "当前样本低分。"
            },
            suggested_sheet_fields: {
              "错误原因": "模型无法稳定识别涂改后的最终答案。"
            }
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(confirmation), { status: 200, headers: { "Content-Type": "application/json" } })
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            ...confirmation,
            status: "confirmed",
            confirmed_at: "2026-06-22T00:01:00+00:00",
            confirmed_by: "local-dev-operator"
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            row_id: "row-42",
            fields: {
              "错误原因": "模型无法稳定识别涂改后的最终答案。",
              "分析报告链接": `${window.location.origin}/api/jobs/job-confirm-1/report`
            }
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "查看历史任务" }));
    await userEvent.click(await screen.findByRole("button", { name: "打开任务 job-confirm-1" }));
    await userEvent.click(screen.getByRole("button", { name: "加载任务报告" }));
    await userEvent.click(await screen.findByRole("button", { name: "生成高风险写回确认" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-confirm-1/spreadsheet-writeback/confirmation", {
      body: JSON.stringify({
        report_url: `${window.location.origin}/api/jobs/job-confirm-1/report`,
        spreadsheet_url: "https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123",
        spreadsheet_id: "testSpreadsheetToken123",
        sheet_id: "testSheet123",
        actor: "local-dev-operator",
        note: "人工确认前预检写回目标"
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
    expect(await screen.findByText("Lark 写回确认状态：待确认")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "确认并写回报告" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/lark/write-confirmations/confirm-write-1/confirm", {
      body: JSON.stringify({
        actor: "local-dev-operator",
        note: "确认写回报告到飞书表格"
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-confirm-1/spreadsheet-writeback", {
      body: JSON.stringify({
        report_url: `${window.location.origin}/api/jobs/job-confirm-1/report`,
        spreadsheet_url: "https://example.larkoffice.com/sheets/testSpreadsheetToken123?sheet=testSheet123",
        spreadsheet_id: "testSpreadsheetToken123",
        sheet_id: "testSheet123",
        require_confirmation: true,
        confirmation_id: "confirm-write-1",
        actor: "local-dev-operator",
        note: "已通过高风险写回确认"
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
    expect(await screen.findByText("表格写回行：row-42")).toBeInTheDocument();
  });


  it("runs auto debug closure from a persisted report and renders closure lineage", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            jobs: [
              {
                job_id: "job-auto-closure-1",
                case_id: "JSZN-131",
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
                evidence_ids: ["JSZN-131:baseline_replay:0"],
                evidence_error_counts: {
                  total_evidence: 5,
                  failed_judgements: 1,
                  response_parse_errors: 0,
                  model_call_errors: 0
                },
                spreadsheet_writeback_audit: null
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
            job_id: "job-auto-closure-1",
            case_id: "JSZN-131",
            status: "needs_human_review",
            observed_failure: {
              type: "video_timestamp_mismatch",
              summary: "视频时间窗评分发现 video:segment:3 存在时间边界偏差。",
              affected_box_ids: []
            },
            planned_experiments: ["baseline_replay"],
            experiment_summary: {
              total_trials: 5,
              success_count: 4,
              failed_trial_count: 1,
              success_rate: 0.8,
              stability_label: "unstable",
              evidence_ids: ["JSZN-131:baseline_replay:0"],
              image_artifact_ids: []
            },
            root_cause: {
              label: "video_timestamp_boundary_error",
              confidence: "high",
              evidence_summary: "视频时间边界定位失败。"
            },
            suggested_sheet_fields: {
              "错误原因": "视频时间边界定位失败"
            }
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            source_job_id: "job-auto-closure-1",
            closure: {
              source_job_id: "job-auto-closure-1",
              created_targeted_probe_jobs: ["job-targeted-probe-1"],
              created_strategy_follow_up_jobs: ["job-stability-follow-up-1"],
              created_verification_jobs: ["job-action-verify-1"],
              evidence_summaries: [],
              targeted_probe_outcomes: [],
              final_attribution_candidates: [
                {
                  category: "model_instability",
                  confidence: "high",
                  summary: "Live rerun passed 4/5 trials, so stability verification is required."
                }
              ],
              badcase_live_comparison: {
                original_badcase: "原 badcase：0/1 通过，avg_score=0.0。",
                live_rerun: "Live 复测：4/5 通过，success_rate=80%。",
                decision: "model_instability"
              },
              writeback_status: "succeeded"
            },
            markdown: "# JSZN-131 最终 Debug 报告\n\n## Evidence 明细\n",
            report_artifact_url: "/api/artifacts/files/JSZN-131_auto_closure_report.md"
          }),
          { status: 202, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "查看历史任务" }));
    await userEvent.click(await screen.findByRole("button", { name: "打开任务 job-auto-closure-1" }));
    await userEvent.click(screen.getByRole("button", { name: "加载任务报告" }));
    await userEvent.click(await screen.findByRole("button", { name: "运行自动闭环调试" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-auto-closure-1/auto-closure/report", {
      body: JSON.stringify({
        actor: "local-dev-operator",
        note: "auto close video badcase",
        writeback: true,
        report_url: `${window.location.origin}/api/jobs/job-auto-closure-1/report`,
        submit_controlled_probes: false
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
    expect(await screen.findByText("自动定向深挖任务：job-targeted-probe-1")).toBeInTheDocument();
    expect(screen.getByText("自动稳定性跟进任务：job-stability-follow-up-1")).toBeInTheDocument();
    expect(screen.getByText("自动闭环验证任务：job-action-verify-1")).toBeInTheDocument();
    expect(screen.getByText("闭环判断：model_instability")).toBeInTheDocument();
    expect(screen.getByText("自动写回状态：成功")).toBeInTheDocument();
    expect(screen.getByText("自动闭环 Markdown 报告")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "打开自动闭环 Markdown 报告" })).toHaveAttribute(
      "href",
      "/api/artifacts/files/JSZN-131_auto_closure_report.md"
    );
    expect(screen.getByText(/# JSZN-131 最终 Debug 报告/)).toBeInTheDocument();
  });


  it("updates recommended action status from a persisted report", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            jobs: [
              {
                job_id: "job-action-status-1",
                case_id: "case-action-status-1",
                status: "completed",
                attempt_count: 1,
                max_attempts: 2,
                remaining_attempts: 1,
                will_retry: false,
                retry_recommendation: "none",
                retry_recommendation_detail: {
                  code: "none",
                  label: "无需重试",
                  action: "查看报告",
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
                spreadsheet_writeback_audit: null,
                created_at: "2026-06-14T00:00:00+00:00",
                updated_at: "2026-06-14T00:00:01+00:00"
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
            job_id: "job-action-status-1",
            case_id: "case-action-status-1",
            status: "needs_human_review",
            observed_failure: {
              type: "cross_modal_alignment_failure",
              summary: "cross-modal compare failed",
              affected_box_ids: []
            },
            planned_experiments: ["modality_ablation_check"],
            experiment_summary: null,
            root_cause: {
              label: "cross_modal_alignment_failure",
              confidence: "high",
              evidence_summary: "cross-modal variant failed."
            },
            recommended_actions: [
              {
                category: "prompt",
                priority: "high",
                status: "pending",
                summary: "强化跨模态对比步骤。",
                detail: "要求模型先分别列出 image/text 证据，再输出冲突结论。"
              }
            ],
            suggested_sheet_fields: {
              "错误原因": "跨模态对齐问题"
            }
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            statuses: [],
            events: []
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-action-status-1",
            action_index: 0,
            status: "accepted",
            actor: "local-dev-operator",
            note: "",
            created_at: "2026-06-14T00:00:00+00:00",
            updated_at: "2026-06-14T00:00:02+00:00"
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            statuses: [
              {
                job_id: "job-action-status-1",
                action_index: 0,
                status: "accepted",
                actor: "local-dev-operator",
                note: "",
                created_at: "2026-06-14T00:00:00+00:00",
                updated_at: "2026-06-14T00:00:02+00:00"
              }
            ],
            events: [
              {
                event_id: 1,
                job_id: "job-action-status-1",
                action_index: 0,
                status: "accepted",
                actor: "local-dev-operator",
                note: "",
                created_at: "2026-06-14T00:00:02+00:00"
              }
            ]
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "查看历史任务" }));
    await userEvent.click(await screen.findByRole("button", { name: "打开任务 job-action-status-1" }));
    await userEvent.click(screen.getByRole("button", { name: "加载任务报告" }));
    await userEvent.click(await screen.findByRole("button", { name: "接受建议操作 1" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-action-status-1/recommended-actions/0/status", {
      body: JSON.stringify({
        status: "accepted",
        actor: "local-dev-operator",
        note: ""
      }),
      headers: { "Content-Type": "application/json" },
      method: "PATCH"
    });
    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-action-status-1/recommended-actions/statuses");
    expect(
      fetchMock.mock.calls.filter((call) => call[0] === "/api/jobs/job-action-status-1/recommended-actions/statuses")
    ).toHaveLength(2);
    expect(await screen.findByText("状态：已接受")).toBeInTheDocument();
    expect(await screen.findByText("建议操作状态事件")).toBeInTheDocument();
    expect(screen.getByText("操作 1：已接受")).toBeInTheDocument();
    expect(screen.getByText("操作者：local-dev-operator")).toBeInTheDocument();
  });


  it("updates human handoff status from a persisted report", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            jobs: [
              {
                job_id: "job-handoff-source",
                case_id: "case-handoff",
                status: "completed",
                attempt_count: 1,
                max_attempts: 2,
                remaining_attempts: 1,
                will_retry: false,
                retry_recommendation: "none",
                retry_recommendation_detail: {
                  code: "none",
                  label: "无需重试",
                  action: "查看报告",
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
                spreadsheet_writeback_audit: null,
                created_at: "2026-06-15T00:00:00+00:00",
                updated_at: "2026-06-15T00:00:01+00:00"
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
            job_id: "job-handoff-source",
            case_id: "case-handoff",
            status: "needs_human_review",
            observed_failure: {
              type: "cross_modal_alignment_failure",
              summary: "cross-modal compare failed",
              affected_box_ids: []
            },
            planned_experiments: ["modality_ablation_check"],
            experiment_summary: null,
            root_cause: {
              label: "cross_modal_alignment_failure",
              confidence: "high",
              evidence_summary: "cross-modal target failed."
            },
            human_handoff_requests: [
              {
                source: "targeted_probe_guardrail",
                target_id: "multimodal:conflict:1",
                priority: "high",
                reason: "max_targeted_probe_depth_reached",
                summary: "Targeted probe chain for multimodal:conflict:1 reached max depth 3.",
                recommended_owner: "human-debugger",
                next_action: "Review the full targeted probe chain and decide the final attribution."
              }
            ],
            suggested_sheet_fields: {
              "错误原因": "跨模态对齐问题"
            }
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            statuses: [
              {
                job_id: "job-handoff-source",
                target_id: "multimodal:conflict:1",
                status: "pending",
                actor: "",
                note: "",
                created_at: "2026-06-15T00:00:00+00:00",
                updated_at: "2026-06-15T00:00:00+00:00"
              }
            ]
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-handoff-source",
            target_id: "multimodal:conflict:1",
            status: "resolved",
            actor: "local-dev-operator",
            note: "",
            created_at: "2026-06-15T00:00:00+00:00",
            updated_at: "2026-06-15T00:00:02+00:00"
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "查看历史任务" }));
    await userEvent.click(await screen.findByRole("button", { name: "打开任务 job-handoff-source" }));
    await userEvent.click(screen.getByRole("button", { name: "加载任务报告" }));
    await userEvent.click(await screen.findByRole("button", { name: "完成接管 multimodal:conflict:1" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-handoff-source/human-handoffs/statuses");
    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-handoff-source/human-handoffs/multimodal%3Aconflict%3A1/status", {
      body: JSON.stringify({
        status: "resolved",
        actor: "local-dev-operator",
        note: ""
      }),
      headers: { "Content-Type": "application/json" },
      method: "PATCH"
    });
    expect(await screen.findByText("接管状态：已解决")).toBeInTheDocument();
  });


  it("creates a final attribution verification job from a persisted report", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            jobs: [
              {
                job_id: "job-final-attribution-source",
                case_id: "case-final-attribution",
                status: "completed",
                attempt_count: 1,
                max_attempts: 2,
                remaining_attempts: 1,
                will_retry: false,
                retry_recommendation: "none",
                retry_recommendation_detail: {
                  code: "none",
                  label: "无需重试",
                  action: "查看报告",
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
                spreadsheet_writeback_audit: null,
                created_at: "2026-06-15T00:00:00+00:00",
                updated_at: "2026-06-15T00:00:01+00:00"
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
            job_id: "job-final-attribution-source",
            case_id: "case-final-attribution",
            status: "needs_human_review",
            observed_failure: {
              type: "cross_modal_alignment_failure",
              summary: "cross-modal compare failed",
              affected_box_ids: []
            },
            planned_experiments: ["modality_ablation_check"],
            experiment_summary: null,
            root_cause: {
              label: "cross_modal_alignment_failure",
              confidence: "high",
              evidence_summary: "cross-modal target failed."
            },
            follow_up_experiments: [
              {
                source: "final_attribution",
                target_id: "multimodal:conflict:1",
                category: "prompt_issue",
                planned_steps: "final_attribution_prompt_verification",
                summary:
                  "Final attribution for multimodal:conflict:1 is prompt_issue; run final_attribution_prompt_verification to verify the recommended fix."
              }
            ],
            suggested_sheet_fields: {
              "错误原因": "跨模态对齐问题"
            }
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ follow_ups: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        })
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            source_job_id: "job-final-attribution-source",
            stage: "final_attribution:multimodal:conflict:1",
            planned_steps: "final_attribution_prompt_verification",
            follow_up_job_id: "job-final-verify-1",
            actor: "local-dev-operator",
            note: "",
            created_at: "2026-06-15T00:00:02+00:00",
            follow_up_job: {
              job_id: "job-final-verify-1",
              case_id: "case-final-attribution",
              status: "created"
            }
          }),
          { status: 202, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "查看历史任务" }));
    await userEvent.click(await screen.findByRole("button", { name: "打开任务 job-final-attribution-source" }));
    await userEvent.click(screen.getByRole("button", { name: "加载任务报告" }));
    await userEvent.click(
      await screen.findByRole("button", { name: "运行最终归因跟进 multimodal:conflict:1" })
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/jobs/job-final-attribution-source/final-attributions/multimodal%3Aconflict%3A1/verification-jobs",
      {
        body: JSON.stringify({
          actor: "local-dev-operator",
          note: ""
        }),
        headers: { "Content-Type": "application/json" },
        method: "POST"
      }
    );
    expect(await screen.findByText("任务 ID：job-final-verify-1")).toBeInTheDocument();
  });


  it("creates a final attribution recovery job from a persisted report", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            jobs: [
              {
                job_id: "job-final-recovery-source",
                case_id: "case-final-recovery",
                status: "completed",
                attempt_count: 1,
                max_attempts: 2,
                remaining_attempts: 1,
                will_retry: false,
                retry_recommendation: "none",
                retry_recommendation_detail: {
                  code: "none",
                  label: "无需重试",
                  action: "查看报告",
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
                spreadsheet_writeback_audit: null,
                created_at: "2026-06-15T00:00:00+00:00",
                updated_at: "2026-06-15T00:00:01+00:00"
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
            job_id: "job-final-recovery-source",
            case_id: "case-final-recovery",
            status: "needs_human_review",
            observed_failure: {
              type: "cross_modal_alignment_failure",
              summary: "cross-modal compare failed",
              affected_box_ids: []
            },
            planned_experiments: ["modality_ablation_check"],
            experiment_summary: null,
            root_cause: {
              label: "cross_modal_alignment_failure",
              confidence: "high",
              evidence_summary: "cross-modal target failed."
            },
            follow_up_experiments: [
              {
                source: "final_attribution_verification_outcome",
                target_id: "multimodal:conflict:1",
                category: "prompt_issue",
                result: "not_resolved",
                verification_job_id: "job-final-verify-1",
                planned_steps: "final_attribution_recovery_probe",
                summary:
                  "Final attribution verification for multimodal:conflict:1 is not_resolved; run final_attribution_recovery_probe to reassess the root cause before closure."
              }
            ],
            suggested_sheet_fields: {
              "错误原因": "跨模态对齐问题"
            }
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ follow_ups: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        })
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            source_job_id: "job-final-recovery-source",
            stage: "final_attribution_recovery:multimodal:conflict:1",
            planned_steps: "final_attribution_recovery_probe",
            follow_up_job_id: "job-final-recovery-1",
            actor: "local-dev-operator",
            note: "",
            created_at: "2026-06-15T00:00:03+00:00",
            follow_up_job: {
              job_id: "job-final-recovery-1",
              case_id: "case-final-recovery",
              status: "created"
            }
          }),
          { status: 202, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "查看历史任务" }));
    await userEvent.click(await screen.findByRole("button", { name: "打开任务 job-final-recovery-source" }));
    await userEvent.click(screen.getByRole("button", { name: "加载任务报告" }));
    await userEvent.click(
      await screen.findByRole("button", { name: "运行最终归因恢复 multimodal:conflict:1" })
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/jobs/job-final-recovery-source/final-attribution-recoveries/multimodal%3Aconflict%3A1/debug-jobs",
      {
        body: JSON.stringify({
          actor: "local-dev-operator",
          note: ""
        }),
        headers: { "Content-Type": "application/json" },
        method: "POST"
      }
    );
    expect(await screen.findByText("任务 ID：job-final-recovery-1")).toBeInTheDocument();
  });


  it("creates a verification debug job for an applied recommended action", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            jobs: [
              {
                job_id: "job-action-verify-source",
                case_id: "case-action-verify",
                status: "completed",
                attempt_count: 1,
                max_attempts: 2,
                remaining_attempts: 1,
                will_retry: false,
                retry_recommendation: "none",
                retry_recommendation_detail: {
                  code: "none",
                  label: "无需重试",
                  action: "查看报告",
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
                spreadsheet_writeback_audit: null,
                created_at: "2026-06-14T00:00:00+00:00",
                updated_at: "2026-06-14T00:00:01+00:00"
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
            job_id: "job-action-verify-source",
            case_id: "case-action-verify",
            status: "needs_human_review",
            observed_failure: {
              type: "cross_modal_alignment_failure",
              summary: "cross-modal compare failed",
              affected_box_ids: []
            },
            planned_experiments: ["modality_ablation_check"],
            experiment_summary: null,
            root_cause: {
              label: "cross_modal_alignment_failure",
              confidence: "high",
              evidence_summary: "cross-modal variant failed."
            },
            recommended_actions: [
              {
                category: "prompt",
                priority: "high",
                status: "applied",
                summary: "强化跨模态对比步骤。",
                detail: "要求模型先分别列出 image/text 证据，再输出冲突结论。"
              }
            ],
            suggested_sheet_fields: {
              错误原因: "跨模态对齐问题"
            }
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ statuses: [], events: [], verifications: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        })
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-action-verify-source",
            action_index: 0,
            verification_job_id: "job-action-verify-rerun",
            actor: "local-dev-operator",
            note: "",
            created_at: "2026-06-14T00:00:02+00:00",
            verification_job: {
              job_id: "job-action-verify-rerun",
              case_id: "case-action-verify",
              status: "created"
            }
          }),
          { status: 202, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            statuses: [],
            events: [],
            verifications: [
              {
                job_id: "job-action-verify-source",
                action_index: 0,
                verification_job_id: "job-action-verify-rerun",
                actor: "local-dev-operator",
                note: "",
                created_at: "2026-06-14T00:00:02+00:00"
              }
            ]
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "查看历史任务" }));
    await userEvent.click(await screen.findByRole("button", { name: "打开任务 job-action-verify-source" }));
    await userEvent.click(screen.getByRole("button", { name: "加载任务报告" }));
    await userEvent.click(await screen.findByRole("button", { name: "验证建议操作 1" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-action-verify-source/recommended-actions/0/verification-jobs", {
      body: JSON.stringify({
        actor: "local-dev-operator",
        note: ""
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
    expect(await screen.findByText("任务 ID：job-action-verify-rerun")).toBeInTheDocument();
    expect(await screen.findByText("建议操作验证任务")).toBeInTheDocument();
    expect(screen.getByText("操作 1 验证任务：job-action-verify-rerun")).toBeInTheDocument();
    expect(screen.getAllByText("样本 ID：case-action-verify").length).toBeGreaterThan(0);
  });


  it("creates strategy follow-up jobs from a persisted report", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            jobs: [
              {
                job_id: "job-strategy-source",
                case_id: "case-strategy-follow-up",
                status: "completed",
                attempt_count: 1,
                max_attempts: 2,
                remaining_attempts: 1,
                will_retry: false,
                retry_recommendation: "none",
                retry_recommendation_detail: {
                  code: "none",
                  label: "无需重试",
                  action: "查看报告",
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
                spreadsheet_writeback_audit: null,
                created_at: "2026-06-15T00:00:00+00:00",
                updated_at: "2026-06-15T00:00:01+00:00"
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
            job_id: "job-strategy-source",
            case_id: "case-strategy-follow-up",
            status: "needs_human_review",
            observed_failure: {
              type: "cross_modal_alignment_failure",
              summary: "cross-modal compare failed",
              affected_box_ids: []
            },
            planned_experiments: ["modality_ablation_check"],
            experiment_summary: null,
            root_cause: {
              label: "cross_modal_alignment_failure",
              confidence: "high",
              evidence_summary: "cross-modal variant failed."
            },
            recommended_actions: [
              {
                category: "prompt",
                priority: "high",
                status: "pending",
                summary: "保留推荐操作状态查询。",
                detail: "该测试需要加载状态接口后再创建 strategy follow-up。"
              }
            ],
            follow_up_experiments: [
              {
                source: "debug_strategy",
                stage: "ablation_expansion",
                planned_steps: "strategy_ablation_expansion_probe",
                summary: "策略阶段 ablation_expansion 已转为 follow-up experiment：strategy_ablation_expansion_probe。"
              }
            ],
            suggested_sheet_fields: {
              错误原因: "跨模态对齐问题"
            }
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ statuses: [], events: [], verifications: [], verification_results: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        })
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            follow_ups: [
              {
                source_job_id: "job-strategy-source",
                stage: "evidence_audit",
                planned_steps: "strategy_evidence_audit_probe",
                follow_up_job_id: "job-existing-strategy-follow-up",
                actor: "strategy-operator",
                note: "existing evidence audit",
                created_at: "2026-06-15T00:00:02+00:00",
                outcome: "passed_stop_condition",
                success_rate: 1,
                summary: "Strategy follow-up job passed all probes; stop condition is likely satisfied.",
                escalation: ""
              }
            ]
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            source_job_id: "job-strategy-source",
            stage: "ablation_expansion",
            planned_steps: "strategy_ablation_expansion_probe",
            follow_up_job_id: "job-strategy-follow-up",
            actor: "local-dev-operator",
            note: "",
            created_at: "2026-06-15T00:00:02+00:00",
            follow_up_job: {
              job_id: "job-strategy-follow-up",
              case_id: "case-strategy-follow-up",
              status: "created"
            }
          }),
          { status: 202, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "查看历史任务" }));
    await userEvent.click(await screen.findByRole("button", { name: "打开任务 job-strategy-source" }));
    await userEvent.click(screen.getByRole("button", { name: "加载任务报告" }));
    expect(await screen.findByText("策略执行历史记录")).toBeInTheDocument();
    expect(screen.getByText("任务：job-existing-strategy-follow-up")).toBeInTheDocument();
    expect(screen.getByText("执行结果：passed_stop_condition")).toBeInTheDocument();
    await userEvent.click(await screen.findByRole("button", { name: "运行策略跟进 ablation_expansion" }));

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/jobs/job-strategy-source/strategy-follow-ups/ablation_expansion/debug-jobs",
      {
        body: JSON.stringify({
          actor: "local-dev-operator",
          note: ""
        }),
        headers: { "Content-Type": "application/json" },
        method: "POST"
      }
    );
    expect(await screen.findByText("任务 ID：job-strategy-follow-up")).toBeInTheDocument();
  });


  it("creates targeted probe jobs from a persisted report", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            jobs: [
              {
                job_id: "job-targeted-source",
                case_id: "case-targeted-probe",
                status: "completed",
                attempt_count: 1,
                max_attempts: 2,
                remaining_attempts: 1,
                will_retry: false,
                retry_recommendation: "none",
                retry_recommendation_detail: {
                  code: "none",
                  label: "无需重试",
                  action: "查看报告",
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
                spreadsheet_writeback_audit: null,
                created_at: "2026-06-15T00:00:00+00:00",
                updated_at: "2026-06-15T00:00:01+00:00"
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
            job_id: "job-targeted-source",
            case_id: "case-targeted-probe",
            status: "needs_human_review",
            observed_failure: {
              type: "cross_modal_alignment_failure",
              summary: "cross-modal compare failed",
              affected_box_ids: []
            },
            planned_experiments: ["modality_ablation_check"],
            experiment_summary: null,
            root_cause: {
              label: "cross_modal_alignment_failure",
              confidence: "high",
              evidence_summary: "cross-modal target multimodal:conflict:1 failed."
            },
            recommended_actions: [],
            follow_up_experiments: [
              {
                source: "targeted_probe",
                target_id: "multimodal:conflict:1",
                planned_steps: "targeted_multimodal_conflict_probe",
                summary: "围绕目标 multimodal:conflict:1 生成 targeted probing：targeted_multimodal_conflict_probe。"
              }
            ],
            suggested_sheet_fields: {
              错误原因: "跨模态对齐问题"
            }
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ follow_ups: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ probes: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        })
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            source_job_id: "job-targeted-source",
            target_id: "multimodal:conflict:1",
            planned_steps: "targeted_multimodal_conflict_probe",
            probe_job_id: "job-targeted-probe",
            actor: "local-dev-operator",
            note: "",
            created_at: "2026-06-15T00:00:02+00:00",
            probe_job: {
              job_id: "job-targeted-probe",
              case_id: "case-targeted-probe",
              status: "created"
            }
          }),
          { status: 202, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "查看历史任务" }));
    await userEvent.click(await screen.findByRole("button", { name: "打开任务 job-targeted-source" }));
    await userEvent.click(screen.getByRole("button", { name: "加载任务报告" }));
    await userEvent.click(await screen.findByRole("button", { name: "运行定向深挖 multimodal:conflict:1" }));

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/jobs/job-targeted-source/targeted-probes/multimodal%3Aconflict%3A1/debug-jobs",
      {
        body: JSON.stringify({
          actor: "local-dev-operator",
          note: ""
        }),
        headers: { "Content-Type": "application/json" },
        method: "POST"
      }
    );
    expect(await screen.findByText("任务 ID：job-targeted-probe")).toBeInTheDocument();
  });
});
