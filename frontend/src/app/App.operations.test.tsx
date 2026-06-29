import { App, describe, expect, it, openTab, render, screen, userEvent, vi } from "./App.test.setup";

describe("App Operations Workspace", () => {
  it("renders the logical agent topology", async () => {
    render(<App />);

    await openTab("操作监控");
    expect(screen.getByRole("heading", { name: "Agent 拓扑" })).toBeInTheDocument();
    expect(screen.getByText("模型执行 Agent")).toBeInTheDocument();
    expect(screen.getByText("回写操作 Agent")).toBeInTheDocument();
  });


  it("loads observability summary for operational monitoring", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            jobs: {
              by_status: {
                created: 4,
                running: 1,
                completed: 12,
                failed: 2
              },
              total_count: 19,
              pending_count: 4,
              running_count: 1,
              failed_count: 2,
              completed_count: 12
            },
            worker: {
              running: true,
              processed_count: 18,
              error_count: 1,
              last_error: "hook failed",
              completion_hook_enabled: true,
              report_base_url: "https://debug-agent.local",
              auto_writeback_enabled: true
            },
            writeback_audits: {
              by_status: {
                succeeded: 10,
                failed: 2,
                skipped: 1
              },
              total_count: 13
            },
            evidence: {
              total_evidence: 42,
              failed_judgements: 11,
              response_parse_errors: 3,
              model_call_errors: 2,
              average_latency_ms: 88.5
            },
            usage: {
              model_call_count: 42,
              prompt_character_count: 12345,
              estimated_cost_units: 54.345,
              budget_units: 50,
              budget_status: "over_budget",
              budget_utilization: 1.0869,
              budget_enforcement_enabled: true
            },
            strategy_feedback: {
              total_follow_ups: 6,
              pending_count: 2,
              passed_stop_condition_count: 3,
              needs_escalation_count: 1
            },
            health: {
              level: "critical",
              reasons: ["failed jobs present", "failed spreadsheet writebacks present", "strategy follow-ups need escalation"],
              actions: [
                "Inspect failed jobs and open their evidence chain.",
                "Retry failed spreadsheet writebacks after checking Lark permissions and sheet headers.",
                "打开策略跟进历史任务 history and run escalation probes."
              ]
            }
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ jobs: [], total_count: 0 }), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        })
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
            running: true,
            processed_count: 18,
            error_count: 1,
            last_error: "hook failed",
            completion_hook_enabled: true,
            report_base_url: "https://debug-agent.local",
            auto_writeback_enabled: true
          }),
          { status: 202, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await openTab("操作监控");
    await userEvent.click(screen.getByRole("button", { name: "加载监控概览" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/observability/summary");
    expect(await screen.findByText("排队任务：4")).toBeInTheDocument();
    expect(screen.getByText("后台进程运行中：是")).toBeInTheDocument();
    expect(screen.getByText("回写失败：2")).toBeInTheDocument();
    expect(screen.getByText("证据解析错误：3")).toBeInTheDocument();
    expect(screen.getByText("预估消耗：54.345")).toBeInTheDocument();
    expect(screen.getByText("预算状态：超预算")).toBeInTheDocument();
    expect(screen.getByText("预算强制拦截：开启")).toBeInTheDocument();
    expect(screen.getByText("策略需升级：1")).toBeInTheDocument();
    expect(screen.getByText("健康状态：严重")).toBeInTheDocument();
    expect(screen.getByText("健康原因：存在失败任务")).toBeInTheDocument();
    expect(screen.getByText("健康原因：策略跟进需要升级处理")).toBeInTheDocument();
    expect(screen.getAllByText("建议操作：检查失败任务并打开对应证据链。").length).toBeGreaterThan(0);

    await userEvent.click(screen.getByRole("button", { name: "打开监控中的失败任务" }));
    await userEvent.click(screen.getByRole("button", { name: "打开监控中的失败回写" }));
    await userEvent.click(screen.getByRole("button", { name: "从监控概览启动后台进程" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs?status=failed&limit=50");
    expect(fetchMock).toHaveBeenCalledWith("/api/spreadsheets/writeback/audits?status=failed&limit=50");
    expect(fetchMock).toHaveBeenCalledWith("/api/worker/start", { method: "POST" });
  });


  it("loads production readiness status for operational monitoring", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          generated_at: "2026-06-22T00:00:00+00:00",
          level: "degraded",
          config: {
            environment: "pilot",
            database_url: "sqlite:///debug-agent.db",
            database_kind: "sqlite",
            database_path: "debug-agent.db",
            artifact_root: "backend/artifacts",
            artifact_retention_days: 30,
            report_base_url: "https://debug-agent.local",
            auto_writeback_enabled: true,
            queue_max_concurrency: 2,
            retry_max_attempts: 2,
            stale_running_job_seconds: 1800,
            require_trusted_actor: false,
            enable_fixture_fallback: false,
            usage_budget_units: 50,
            enforce_usage_budget: false,
            lark_configured: true,
            lark_connector_mode: "cli",
            lark_identity: "bot",
            lark_profile: "debug-bot",
            lark_event_mode: "webhook",
            lark_bot_verification_configured: true,
            lark_bot_encrypt_configured: true,
            worker_running: true,
            worker_completion_hook_enabled: true
          },
          paths: [
            {
              name: "artifact_root",
              label: "产物根目录",
              path: "backend/artifacts",
              exists: true,
              is_directory: true,
              writable: true
            }
          ],
          checks: [
            {
              key: "trusted_actor",
              label: "操作者约束",
              status: "warning",
              detail: "require_trusted_actor=false",
              action: "生产候选建议开启 DEBUG_AGENT_REQUIRE_TRUSTED_ACTOR。"
            }
          ],
          export_urls: {
            observability: "/api/observability/summary",
            readiness: "/api/operations/readiness",
            artifact_retention: "/api/operations/artifact-retention",
            operations_support_bundle: "/api/operations/support-bundle.zip"
          }
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);
    await openTab("操作监控");
    await userEvent.click(screen.getByRole("button", { name: "加载生产运行就绪" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/operations/readiness");
    expect(await screen.findByText("生产就绪状态：降级")).toBeInTheDocument();
    expect(screen.getByText("生产环境：pilot")).toBeInTheDocument();
    expect(screen.getByText("生产 Lark：已配置")).toBeInTheDocument();
    expect(screen.getByText("生产机器人事件模式：webhook 模式")).toBeInTheDocument();
    expect(screen.getByText(/生产检查：操作者约束\/需关注/)).toBeInTheDocument();
  });


  it("loads Lark bot preflight from operations", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          generated_at: "2026-06-23T00:00:00+00:00",
          status: "warning",
          connector: {
            mode: "cli",
            identity: "bot",
            profile: "debug-bot",
            auth_status: "unknown",
            token_status: "unknown"
          },
          event_mode: "webhook",
          event_endpoint_url: "https://debug-agent.example/api/lark/bot/events",
          setup_package_url: "/api/lark/bot/setup-package.zip",
          required_bot_scopes: ["im:message:send_as_bot"],
          pending_command_count: 1,
          failed_command_count: 0,
          recent_missing_scopes: [],
          operator_required_items: [
            {
              key: "grant_im_bot_scope",
              title: "开通机器人 IM 发送权限",
              owner: "lark_app_admin",
              required: true,
              status: "manual_check",
              detail: "required=im:message:send_as_bot",
              action: "在飞书开放平台开通 im:message:send_as_bot。",
              evidence: "测试数据"
            }
          ],
          checks: [
            {
              key: "im_scope_catalog",
              label: "IM 权限清单",
              status: "warning",
              detail: "required=im:message:send_as_bot; recent_missing=none",
              action: "在飞书开放平台开通 im:message:send_as_bot，并用真实群聊 dry-run/发送验证。"
            }
          ]
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);

    await openTab("操作监控");
    await userEvent.click(screen.getByRole("button", { name: "加载机器人上线预检" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/lark/bot/preflight");
    expect(await screen.findByText("机器人预检状态：需关注")).toBeInTheDocument();
    expect(screen.getByText("机器人事件模式：webhook 模式")).toBeInTheDocument();
    expect(screen.getByText("机器人预检身份：应用")).toBeInTheDocument();
    expect(screen.getByText("机器人接入交付包：/api/lark/bot/setup-package.zip")).toBeInTheDocument();
    expect(screen.getByText("机器人接入事项：开通机器人 IM 发送权限/需人工确认/飞书应用管理员")).toBeInTheDocument();
    expect(screen.getByText(/机器人预检项：IM 权限清单\/需关注/)).toBeInTheDocument();
  });


  it("loads Lark bot go-live gate from operations", async () => {
    const preflight = {
      generated_at: "2026-06-23T00:00:00+00:00",
      status: "failed",
      connector: {
        mode: "cli",
        identity: "unknown",
        profile: "",
        auth_status: "unknown",
        token_status: "unknown"
      },
      event_mode: "webhook",
      event_endpoint_url: "http://localhost:8000/api/lark/bot/events",
      setup_package_url: "/api/lark/bot/setup-package.zip",
      required_bot_scopes: ["im:message:send_as_bot"],
      pending_command_count: 0,
      failed_command_count: 0,
      recent_missing_scopes: [],
      operator_required_items: [],
      checks: []
    };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          generated_at: "2026-06-23T00:00:00+00:00",
          status: "failed",
          allowed: false,
          decision: "暂不允许进入真实飞书机器人 dogfood。",
          preflight,
          checks: [
            {
              key: "manual_acknowledgements",
              label: "人工确认记录",
              status: "failed",
              detail: "缺少确认：运行 webhook 探针",
              action: "用记录确认表单补齐管理员确认和证据。"
            }
          ],
          export_urls: { setup_package: "/api/lark/bot/setup-package.zip" }
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);

    await openTab("操作监控");
    await userEvent.click(screen.getByRole("button", { name: "加载机器人真实上线门禁" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/lark/bot/go-live-gate");
    expect(await screen.findByText("机器人真实上线门禁状态：阻塞")).toBeInTheDocument();
    expect(screen.getByText("机器人真实上线门禁结论：暂不允许")).toBeInTheDocument();
    expect(screen.getByText("机器人真实上线事件模式：webhook 模式")).toBeInTheDocument();
    expect(screen.getByText(/机器人真实上线检查：人工确认记录\/阻塞/)).toBeInTheDocument();
  });


  it("loads pilot gate status for operational monitoring", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          generated_at: "2026-06-22T00:00:00+00:00",
          status: "warning",
          thresholds: {
            min_completed_jobs: 20,
            min_success_rate: 0.8,
            max_p95_duration_ms: 12000,
            max_estimated_cost_units: 100,
            max_model_call_errors: 0,
            max_writeback_failed: 0,
            max_lark_operation_failures: 0
          },
          batch_evidence: {
            compared_batch_count: 2,
            completed_jobs: 18,
            best_batch_id: "batch-a",
            best_success_rate: 0.9,
            best_p95_duration_ms: 9000,
            best_estimated_cost_units: 12,
            best_quality_score: 88,
            best_efficiency_score: 77
          },
          checks: [
            {
              key: "scale_coverage",
              label: "真实样本覆盖",
              status: "failed",
              detail: "completed_jobs=18, required=20",
              action: "继续执行 operator-approved 真实批次。"
            }
          ],
          comparison: {
            generated_at: "2026-06-22T00:00:00+00:00",
            batch_ids: ["batch-a", "batch-b"],
            items: [],
            best_batch_id: "batch-a",
            summary: "推荐 batch-a",
            export_url: "/api/debug-batches/comparison.csv?batch_ids=batch-a,batch-b"
          },
          export_urls: {
            readiness: "/api/operations/readiness",
            batch_comparison_csv: "/api/debug-batches/comparison.csv?batch_ids=batch-a,batch-b",
            support_bundle: "/api/operations/support-bundle.zip"
          }
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    render(<App />);

    await openTab("操作监控");
    await userEvent.click(screen.getByRole("button", { name: "加载试点准入评估" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/operations/pilot-gate");
    expect(await screen.findByText("试点准入状态：需关注")).toBeInTheDocument();
    expect(screen.getByText("试点准入最佳批次：batch-a")).toBeInTheDocument();
    expect(screen.getByText(/试点检查：真实样本覆盖\/阻塞/)).toBeInTheDocument();
  });


  it("loads and confirms Lark bot pending commands from operations", async () => {
    const pendingCommand = {
      command_id: "cmd-1",
      actor: "ops-reviewer",
      open_id: "ou_1",
      chat_id: "oc_1",
      message_id: "om_1",
      tenant_key: "tenant-1",
      identity: "bot",
      profile: "debug-bot",
      command_text: "/debug run case handwrite233",
      action_kind: "submit_case",
      action: {},
      card: {},
      status: "pending",
      note: "",
      execution_result: {},
      error_message: "",
      created_at: "2026-06-23T00:00:00+00:00",
      expires_at: "2026-06-23T01:00:00+00:00",
      confirmed_at: "",
      confirmed_by: "",
      executed_at: ""
    };
    const replyPreview = {
      command_id: "cmd-1",
      action_kind: "submit_case",
      status: "executed",
      target_type: "message",
      message_id: "om_1",
      chat_id: "oc_1",
      user_id: "ou_1",
      markdown: "## Debug Agent 已提交调试任务\n\n- 任务：`job-1`",
      idempotency_key: "debug-agent-bot-cmd-1-executed",
      delivery_args: ["im", "+messages-reply", "--message-id", "om_1", "--dry-run"]
    };
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ commands: [pendingCommand], total_count: 1 }), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(replyPreview), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ...pendingCommand, status: "executed", confirmed_by: "ops-reviewer" }), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(replyPreview), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        })
      );

    render(<App />);

    await openTab("操作监控");
    await userEvent.click(screen.getByRole("button", { name: "加载机器人命令" }));

    expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/lark/bot/commands/pending?status=pending&limit=50");
    expect(await screen.findByText("机器人命令总数：1")).toBeInTheDocument();
    expect(screen.getByText("/debug run case handwrite233")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "预览机器人回复" }));
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/lark/bot/commands/pending/cmd-1/reply-preview");
    expect(await screen.findByRole("region", { name: "机器人回复预览" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "确认并执行机器人命令" }));

    expect(fetchMock).toHaveBeenNthCalledWith(3, "/api/lark/bot/commands/pending/cmd-1/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ actor: "local-dev-operator", note: "Web 控制台确认执行机器人命令" })
    });
    expect(fetchMock).toHaveBeenNthCalledWith(4, "/api/lark/bot/commands/pending/cmd-1/reply-preview");
    expect(await screen.findByText("确认人：ops-reviewer")).toBeInTheDocument();
  });


  it("loads and confirms Lark bot badcase drafts from operations", async () => {
    const draft = {
      draft_id: "draft-1",
      actor: "ops-reviewer",
      open_id: "ou_1",
      chat_id: "oc_1",
      message_id: "om_1",
      status: "ready_for_confirmation",
      source_text: "原始输入：https://example.com/a.png",
      input_source: "https://example.com/a.png",
      model_output: '{"answer":"3"}',
      expected_output: '{"answer":"8"}',
      issue_summary: "把 8 识别成 3",
      task_type: "generic_json",
      scoring_standard: "Compare outputs",
      attachments: [],
      links: ["https://example.com/a.png"],
      missing_fields: [],
      submitted_case_id: "",
      submitted_job_id: "",
      error_message: "",
      created_at: "2026-06-23T00:00:00+00:00",
      updated_at: "2026-06-23T00:00:00+00:00"
    };
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ drafts: [draft], total_count: 1 }), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        })
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            draft: {
              ...draft,
              status: "submitted",
              submitted_case_id: "lark-draft-draft-1",
              submitted_job_id: "job-1"
            },
            submitted_job: {
              job_id: "job-1",
              case_id: "lark-draft-draft-1",
              status: "created",
              attempt_count: 0,
              error_message: null,
              evidence_ids: []
            }
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);

    await openTab("操作监控");
    await userEvent.click(screen.getByRole("button", { name: "加载 badcase 草稿" }));

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/lark/bot/badcase-drafts?status=ready_for_confirmation&limit=50"
    );
    expect(await screen.findByText("badcase 草稿总数：1")).toBeInTheDocument();
    expect(screen.getByText("把 8 识别成 3")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "确认并创建 Debug 任务" }));

    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/lark/bot/badcase-drafts/draft-1/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ actor: "local-dev-operator", note: "Web 控制台确认提交 badcase 草稿", create_job: true })
    });
    expect(await screen.findByRole("region", { name: "badcase 草稿确认结果" })).toBeInTheDocument();
    expect(screen.getByText("任务编号：job-1")).toBeInTheDocument();
  });


  it("loads Lark operation audits from the connector status area", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
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
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            audits: [
              {
                audit_id: 1,
                actor: "local-dev-operator",
                connector_mode: "cli",
                identity: "bot",
                profile: "debug-bot",
                service: "sheets",
                operation: "+csv-get",
                status: "failed",
                context: "+csv-get --spreadsheet-token sheet --sheet-id tab",
                error_type: "permission_denied",
                hint: "run lark-cli auth login",
                permission_scopes: ["sheets:spreadsheet:readonly"],
                console_url: "https://open.feishu.cn/app",
                risk_action: "",
                duration_ms: 12,
                created_at: "2026-06-22T00:00:00+00:00"
              }
            ],
            total_count: 1
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await openTab("回写同步");
    await userEvent.click(screen.getByRole("button", { name: "检查飞书连接" }));
    await userEvent.click(await screen.findByRole("button", { name: "查看失败 Lark 操作" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/lark/operation-audits?status=failed&limit=50");
    expect(await screen.findByRole("complementary", { name: "Lark 操作审计" })).toBeInTheDocument();
    expect(screen.getByText("Lark 操作审计总数：1")).toBeInTheDocument();
    expect(screen.getByText("缺少权限：sheets:spreadsheet:readonly")).toBeInTheDocument();
  });


  it("loads Lark scope repair guidance from the connector status area", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
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
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            connector_mode: "cli",
            connector_identity: "bot",
            connector_profile: "debug-bot",
            auth_check_status: "not_verified",
            recent_missing_scopes: ["sheets:spreadsheet:readonly"],
            console_url: "https://open.larkoffice.com/app?lang=zh-CN",
            repair_steps: ["确认应用至少具备这些 scope：sheets:spreadsheet:readonly。"],
            requirements: [
              {
                service: "sheets",
                operation: "+csv-get",
                required_scopes: ["sheets:spreadsheet:readonly"],
                risk_level: "read",
                identity: "bot",
                confirmation_required: false,
                repair_hint: "在飞书开放平台为应用开通电子表格读取权限。",
                console_url: "https://open.larkoffice.com/app?lang=zh-CN",
                status: "missing_recently",
                recent_missing_scopes: ["sheets:spreadsheet:readonly"],
                recent_failure_count: 1
              }
            ]
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await openTab("回写同步");
    await userEvent.click(screen.getByRole("button", { name: "检查飞书连接" }));
    await userEvent.click(await screen.findByRole("button", { name: "检查 Lark 权限需求" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/lark/scopes/check?service=sheets");
    expect(await screen.findByRole("region", { name: "Lark 权限修复建议" })).toBeInTheDocument();
    expect(screen.getByText("最近缺少权限：sheets:spreadsheet:readonly")).toBeInTheDocument();
    expect(screen.getByText("sheets +csv-get：最近失败审计显示缺失")).toBeInTheDocument();
  });


  it("creates and completes Lark auth sessions from the connector status area", async () => {
    const authSession = {
      auth_session_id: "auth-1",
      actor: "local-dev-operator",
      identity: "user",
      profile: "debug-user",
      scopes: ["sheets:spreadsheet:readonly"],
      state: "state-1",
      auth_url: "https://open.larkoffice.com/app?debug_agent_auth=1",
      redirect_url: "",
      status: "pending",
      note: "飞书用户授权会话",
      created_at: "2026-06-22T00:00:00+00:00",
      expires_at: "2026-06-22T00:30:00+00:00",
      completed_at: "",
      completed_by: ""
    };
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            configured: true,
            spreadsheet_id: "testSpreadsheetToken123",
            sheet_id: "testSheet123",
            lark_cli_timeout_seconds: 60,
            connector_profile: "debug-user",
            connectivity_status: "ok",
            error_message: ""
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(authSession), { status: 200, headers: { "Content-Type": "application/json" } })
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            ...authSession,
            status: "authorized",
            completed_at: "2026-06-22T00:03:00+00:00",
            completed_by: "local-dev-operator"
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    render(<App />);
    await openTab("回写同步");
    await userEvent.click(screen.getByRole("button", { name: "检查飞书连接" }));
    await userEvent.click(await screen.findByRole("button", { name: "创建 Lark 授权会话" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/lark/auth-sessions", {
      body: JSON.stringify({
        identity: "user",
        profile: "debug-user",
        scopes: [],
        redirect_url: "",
        actor: "local-dev-operator",
        note: "飞书用户授权会话"
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
    expect(await screen.findByText("Lark 授权会话：待授权")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "打开 Lark 授权入口" })).toHaveAttribute(
      "href",
      "https://open.larkoffice.com/app?debug_agent_auth=1"
    );

    await userEvent.click(screen.getByRole("button", { name: "标记 Lark 授权完成" }));

    expect(fetchMock).toHaveBeenCalledWith("/api/lark/auth-sessions/auth-1/complete", {
      body: JSON.stringify({
        actor: "local-dev-operator",
        note: "已在飞书授权入口完成授权"
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
    expect(await screen.findByText("Lark 授权会话：已授权")).toBeInTheDocument();
  });
});
