import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { ProductionReadiness } from "../api/client";
import { ProductionReadinessPanel } from "./ProductionReadinessPanel";

function makeReadiness(): ProductionReadiness {
  return {
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
      artifact_retention_cleanup: "/api/operations/artifact-retention/cleanup",
      database_backup: "/api/operations/database-backup.zip",
      operations_support_bundle: "/api/operations/support-bundle.zip",
      lark_bot_preflight: "/api/lark/bot/preflight",
      lark_bot_go_live_gate: "/api/lark/bot/go-live-gate",
      lark_bot_permission_checklist: "/api/lark/bot/permission-checklist",
      lark_bot_setup_package: "/api/lark/bot/setup-package.zip"
    }
  };
}

describe("ProductionReadinessPanel", () => {
  it("renders runtime configuration, checks, and export URLs", () => {
    render(<ProductionReadinessPanel readiness={makeReadiness()} />);

    expect(screen.getByRole("heading", { name: "生产运行就绪" })).toBeInTheDocument();
    expect(screen.getByText("降级")).toHaveClass("status-badge--warning");
    expect(screen.getByLabelText("生产配置摘要")).toHaveClass("metric-strip");
    expect(screen.getByText("生产就绪状态：降级")).toBeInTheDocument();
    expect(screen.getByText("生产环境：pilot")).toBeInTheDocument();
    expect(screen.getByText("生产 Lark：已配置")).toBeInTheDocument();
    expect(screen.getByText("生产机器人事件模式：webhook 模式")).toBeInTheDocument();
    expect(screen.getByText("生产机器人回调 Token：已配置")).toBeInTheDocument();
    expect(screen.getByText("生产机器人 Encrypt Key：已配置")).toBeInTheDocument();
    expect(screen.getByText("产物根目录：backend/artifacts / 可写")).toBeInTheDocument();
    expect(screen.getByText(/操作者约束：需关注/)).toBeInTheDocument();
    expect(screen.getByText("运行就绪：/api/operations/readiness")).toBeInTheDocument();
    expect(screen.getByText("产物保留干跑：/api/operations/artifact-retention")).toBeInTheDocument();
    expect(screen.getByText("产物清理执行：/api/operations/artifact-retention/cleanup")).toBeInTheDocument();
    expect(screen.getByText("数据库备份包：/api/operations/database-backup.zip")).toBeInTheDocument();
    expect(screen.getByText("运维支持包：/api/operations/support-bundle.zip")).toBeInTheDocument();
    expect(screen.getByText("机器人上线预检：/api/lark/bot/preflight")).toBeInTheDocument();
    expect(screen.getByText("机器人真实上线门禁：/api/lark/bot/go-live-gate")).toBeInTheDocument();
    expect(screen.getByText("机器人权限清单：/api/lark/bot/permission-checklist")).toBeInTheDocument();
    expect(screen.getByText("机器人接入交付包：/api/lark/bot/setup-package.zip")).toBeInTheDocument();
  });
});
