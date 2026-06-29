import {
  describe,
  expect,
  it,
  vi,
  confirmLarkBotBadcaseDraft,
  completeLarkAuthSession,
  createLarkAuthSession,
  confirmLarkBotPendingCommand,
  fetchLarkBotBadcaseDrafts,
  fetchLarkBotNotificationOutbox,
  fetchLarkOperationAudits,
  fetchLarkBotPendingCommandReplyPreview,
  fetchLarkBotPendingCommands,
  fetchLarkBotGoLiveGate,
  fetchLarkBotPermissionChecklist,
  fetchLarkBotPreflight,
  acknowledgeLarkBotSetupItem,
  fetchLarkScopeCheck,
  fetchPilotGate,
  fetchProductionReadiness
} from "./client.test.setup";

describe("api client Lark operations", () => {
  it("loads Lark operation audits with filters and pagination", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          audits: [],
          total_count: 0
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    const result = await fetchLarkOperationAudits("failed", 50, 100);

    expect(result.total_count).toBe(0);
    expect(fetchMock).toHaveBeenCalledWith("/api/lark/operation-audits?status=failed&limit=50&offset=100");
  });


  it("loads and confirms Lark bot pending commands", async () => {
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
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ commands: [pendingCommand], total_count: 1 }), {
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
        new Response(
          JSON.stringify({
            command_id: "cmd-1",
            action_kind: "submit_case",
            status: "executed",
            target_type: "message",
            message_id: "om_1",
            chat_id: "oc_1",
            user_id: "ou_1",
            markdown: "## Debug Agent 已提交调试任务",
            idempotency_key: "debug-agent-bot-cmd-1-executed",
            delivery_args: ["im", "+messages-reply", "--message-id", "om_1", "--dry-run"]
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

    const list = await fetchLarkBotPendingCommands("pending", 50, 100);
    const confirmed = await confirmLarkBotPendingCommand("cmd-1", { actor: "ops-reviewer" });
    const replyPreview = await fetchLarkBotPendingCommandReplyPreview("cmd-1");

    expect(list.total_count).toBe(1);
    expect(confirmed.status).toBe("executed");
    expect(replyPreview.target_type).toBe("message");
    expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/lark/bot/commands/pending?status=pending&limit=50&offset=100");
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/lark/bot/commands/pending/cmd-1/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ actor: "ops-reviewer" })
    });
    expect(fetchMock).toHaveBeenNthCalledWith(3, "/api/lark/bot/commands/pending/cmd-1/reply-preview");
  });


  it("loads and confirms Lark bot badcase drafts", async () => {
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
            draft: { ...draft, status: "submitted", submitted_job_id: "job-1" },
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

    const list = await fetchLarkBotBadcaseDrafts("ready_for_confirmation", 50, 100);
    const confirmed = await confirmLarkBotBadcaseDraft("draft-1", {
      actor: "ops-reviewer",
      note: "Web 控制台确认",
      create_job: true
    });

    expect(list.total_count).toBe(1);
    expect(confirmed.draft.status).toBe("submitted");
    expect(confirmed.submitted_job?.job_id).toBe("job-1");
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/lark/bot/badcase-drafts?status=ready_for_confirmation&limit=50&offset=100"
    );
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/lark/bot/badcase-drafts/draft-1/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ actor: "ops-reviewer", note: "Web 控制台确认", create_job: true })
    });
  });


  it("loads Lark scope check requirements for a service", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          connector_mode: "cli",
          connector_identity: "bot",
          connector_profile: "debug-bot",
          auth_check_status: "not_verified",
          requirements: [],
          recent_missing_scopes: [],
          repair_steps: [],
          console_url: "https://open.larkoffice.com/app?lang=zh-CN"
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    const result = await fetchLarkScopeCheck("sheets", "csv-get");

    expect(result.connector_mode).toBe("cli");
    expect(fetchMock).toHaveBeenCalledWith("/api/lark/scopes/check?service=sheets&operation=csv-get");
  });


  it("loads Lark bot preflight", async () => {
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
              key: "copy_encrypt_key",
              title: "同步 Encrypt Key",
              owner: "lark_app_admin",
              required: true,
              status: "manual_check",
              detail: "configured=false",
              action: "配置 Encrypt Key。",
              evidence: "测试数据",
              acknowledgement: {
                acknowledgement_id: 1,
                item_key: "copy_encrypt_key",
                actor: "ops",
                evidence: "审批单",
                note: "已确认",
                created_at: "2026-06-23T00:00:00+00:00"
              }
            }
          ],
          checks: []
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    const result = await fetchLarkBotPreflight();

    expect(result.status).toBe("warning");
    expect(result.connector.identity).toBe("bot");
    expect(result.event_mode).toBe("webhook");
    expect(result.setup_package_url).toBe("/api/lark/bot/setup-package.zip");
    expect(result.required_bot_scopes).toContain("im:message:send_as_bot");
    expect(result.operator_required_items[0].title).toBe("同步 Encrypt Key");
    expect(fetchMock).toHaveBeenCalledWith("/api/lark/bot/preflight");
  });


  it("records Lark bot setup acknowledgement", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          acknowledgement_id: 3,
          item_key: "run_webhook_probe",
          actor: "ops",
          evidence: "probe-report.md",
          note: "已跑探针",
          created_at: "2026-06-23T00:00:00+00:00"
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    const result = await acknowledgeLarkBotSetupItem("run_webhook_probe", {
      actor: "ops",
      evidence: "probe-report.md",
      note: "已跑探针"
    });

    expect(result.acknowledgement_id).toBe(3);
    expect(fetchMock).toHaveBeenCalledWith("/api/lark/bot/setup-acknowledgements/run_webhook_probe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ actor: "ops", evidence: "probe-report.md", note: "已跑探针" })
    });
  });


  it("loads Lark bot go-live gate", async () => {
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
              key: "setup_items",
              label: "真实接入清单",
              status: "failed",
              detail: "未完成：订阅消息接收事件",
              action: "完成所有必需接入项后再进入真实 dogfood。"
            }
          ],
          export_urls: { setup_package: "/api/lark/bot/setup-package.zip" }
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    const result = await fetchLarkBotGoLiveGate();

    expect(result.allowed).toBe(false);
    expect(result.checks[0].key).toBe("setup_items");
    expect(fetchMock).toHaveBeenCalledWith("/api/lark/bot/go-live-gate");
  });


  it("loads Lark bot permission checklist", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          generated_at: "2026-06-23T00:00:00+00:00",
          status: "failed",
          event_mode: "long_connection",
          required_scopes: ["sheets:spreadsheet:readonly", "docs:document.media:download"],
          recommended_scopes: ["docx:document:readonly"],
          recent_missing_scopes: ["docs:document.media:download"],
          blocking_scopes: ["docs:document.media:download"],
          requirements: [
            {
              key: "sheet_media_download",
              title: "下载表格附件",
              category: "表格附件下载",
              permission_type: "oauth_scope",
              scope: "docs:document.media:download",
              phase: "required_now",
              risk_level: "read",
              operation: "api GET /drive/v1/medias/:file_token/download",
              required_for: "下载表格附件",
              repair_hint: "开通文档媒体下载权限",
              status: "needs_action",
              recent_missing: true,
              blocking: true,
              console_url: "https://open.larkoffice.com/app?lang=zh-CN"
            }
          ],
          admin_handoff_markdown: "# 小D Bot 飞书权限申请清单",
          console_url: "https://open.larkoffice.com/app?lang=zh-CN"
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    const result = await fetchLarkBotPermissionChecklist();

    expect(result.status).toBe("failed");
    expect(result.blocking_scopes).toContain("docs:document.media:download");
    expect(result.requirements[0].blocking).toBe(true);
    expect(fetchMock).toHaveBeenCalledWith("/api/lark/bot/permission-checklist");
  });


  it("loads production readiness status", async () => {
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
            report_base_url: "https://debug-agent.local",
            auto_writeback_enabled: false,
            queue_max_concurrency: 1,
            retry_max_attempts: 2,
            stale_running_job_seconds: 1800,
            require_trusted_actor: false,
            enable_fixture_fallback: false,
            usage_budget_units: 0,
            enforce_usage_budget: false,
            lark_configured: false,
            lark_connector_mode: "cli",
            lark_identity: "unknown",
            lark_profile: "",
            lark_event_mode: "webhook",
            lark_bot_verification_configured: false,
            lark_bot_encrypt_configured: false,
            worker_running: false,
            worker_completion_hook_enabled: false
          },
          paths: [],
          checks: [],
          export_urls: { readiness: "/api/operations/readiness" }
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    const result = await fetchProductionReadiness();

    expect(result.level).toBe("degraded");
    expect(result.config.environment).toBe("pilot");
    expect(fetchMock).toHaveBeenCalledWith("/api/operations/readiness");
  });


  it("loads pilot gate status", async () => {
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
          checks: [],
          comparison: {
            generated_at: "2026-06-22T00:00:00+00:00",
            batch_ids: ["batch-a"],
            items: [],
            best_batch_id: "batch-a",
            summary: "推荐 batch-a",
            export_url: "/api/debug-batches/comparison.csv?batch_ids=batch-a"
          },
          export_urls: { support_bundle: "/api/operations/support-bundle.zip" }
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    const result = await fetchPilotGate();

    expect(result.status).toBe("warning");
    expect(result.batch_evidence.best_batch_id).toBe("batch-a");
    expect(fetchMock).toHaveBeenCalledWith("/api/operations/pilot-gate");
  });


  it("creates and completes Lark auth sessions without token payloads", async () => {
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
      note: "need user auth",
      created_at: "2026-06-22T00:00:00+00:00",
      expires_at: "2026-06-22T00:30:00+00:00",
      completed_at: "",
      completed_by: ""
    };
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify(authSession), { status: 200, headers: { "Content-Type": "application/json" } })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ...authSession, status: "authorized", completed_by: "local-dev-operator" }), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        })
      );

    await createLarkAuthSession({
      identity: "user",
      profile: "debug-user",
      scopes: ["sheets:spreadsheet:readonly"],
      actor: "local-dev-operator",
      note: "need user auth"
    });
    await completeLarkAuthSession("auth-1", { actor: "local-dev-operator", note: "completed" });

    expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/lark/auth-sessions", {
      body: JSON.stringify({
        identity: "user",
        profile: "debug-user",
        scopes: ["sheets:spreadsheet:readonly"],
        redirect_url: "",
        actor: "local-dev-operator",
        note: "need user auth"
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/lark/auth-sessions/auth-1/complete", {
      body: JSON.stringify({ actor: "local-dev-operator", note: "completed" }),
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
  });


  it("fetches Lark notification outbox for observability", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          notifications: [
            {
              notification_id: "badcase-completion:draft-1:job-1",
              kind: "badcase_completion",
              dedupe_key: "draft-1:job-1",
              status: "failed",
              draft_id: "draft-1",
              job_id: "job-1",
              case_id: "case-1",
              job_status: "completed",
              progress_key: "",
              payload: { delivery_args: ["im", "+messages-reply"] },
              envelope: { notification_id: "badcase-completion:draft-1:job-1" },
              attempts: 2,
              last_error: "invalid message id",
              created_at: "2026-06-26T00:00:00+00:00",
              updated_at: "2026-06-26T00:01:00+00:00",
              sent_at: ""
            }
          ],
          total_count: 1
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    const response = await fetchLarkBotNotificationOutbox("failed", 20, 5);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/lark/bot/notification-outbox?status=failed&limit=20&offset=5"
    );
    expect(response.notifications[0].notification_id).toBe("badcase-completion:draft-1:job-1");
    expect(response.notifications[0].attempts).toBe(2);
    expect(response.notifications[0].last_error).toBe("invalid message id");
  });
});
