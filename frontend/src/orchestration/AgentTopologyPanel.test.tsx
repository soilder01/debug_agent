import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AgentTopologyPanel } from "./AgentTopologyPanel";

afterEach(() => {
  cleanup();
});

describe("AgentTopologyPanel", () => {
  it("renders seven logical agent capabilities", () => {
    render(<AgentTopologyPanel />);

    expect(screen.getByRole("heading", { name: "Agent 拓扑" })).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(7);
    expect(screen.getByText("导入接入 Agent")).toBeInTheDocument();
    expect(screen.getByText("实验规划 Agent")).toBeInTheDocument();
    expect(screen.getByText("模型执行 Agent")).toBeInTheDocument();
    expect(screen.getByText("评分对比 Agent")).toBeInTheDocument();
    expect(screen.getByText("证据产物 Agent")).toBeInTheDocument();
    expect(screen.getByText("根因报告 Agent")).toBeInTheDocument();
    expect(screen.getByText("回写操作 Agent")).toBeInTheDocument();
  });

  it("renders distinct worker variants and tools for different agent responsibilities", () => {
    render(<AgentTopologyPanel />);

    expect(screen.getByLabelText("导入接入 Agent 工位")).toHaveAttribute("data-agent-variant", "loader");
    expect(screen.getByLabelText("实验规划 Agent 工位")).toHaveAttribute("data-agent-variant", "planner");
    expect(screen.getByLabelText("模型执行 Agent 工位")).toHaveAttribute("data-agent-variant", "operator");
    expect(screen.getByLabelText("评分对比 Agent 工位")).toHaveAttribute("data-agent-variant", "judge");
    expect(screen.getByLabelText("证据产物 Agent 工位")).toHaveAttribute("data-agent-variant", "archivist");
    expect(screen.getByLabelText("根因报告 Agent 工位")).toHaveAttribute("data-agent-variant", "analyst");
    expect(screen.getByLabelText("回写操作 Agent 工位")).toHaveAttribute("data-agent-variant", "dispatcher");
    expect(screen.getByText("导入搬运员")).toBeInTheDocument();
    expect(screen.getByText("路线规划师")).toBeInTheDocument();
    expect(screen.getByText("模型终端员")).toBeInTheDocument();
    expect(screen.getByText("评分裁判员")).toBeInTheDocument();
    expect(screen.getByText("证据档案员")).toBeInTheDocument();
    expect(screen.getByText("根因分析师")).toBeInTheDocument();
    expect(screen.getByText("写回调度员")).toBeInTheDocument();
  });

  it("marks the agents mapped to the running stage as working", () => {
    render(
      <AgentTopologyPanel
        runStages={[
          {
            attempt_count: 1,
            created_at: "2026-06-17T00:00:00Z",
            failure_reason: "",
            input: {},
            job_id: "job-1",
            output: {},
            retryable: true,
            stage: "targeted",
            status: "running",
            updated_at: "2026-06-17T00:01:00Z"
          }
        ]}
      />
    );

    expect(screen.getByLabelText("实验规划 Agent 工位")).toHaveAttribute("data-agent-state", "working");
    expect(screen.getByLabelText("模型执行 Agent 工位")).toHaveAttribute("data-agent-state", "working");
    expect(screen.getByLabelText("评分对比 Agent 工位")).toHaveAttribute("data-agent-state", "working");
    expect(screen.getByLabelText("证据产物 Agent 工位")).toHaveAttribute("data-agent-state", "working");
    expect(screen.getByLabelText("回写操作 Agent 工位")).toHaveAttribute("data-agent-state", "idle");
  });

  it("marks agents as completed after their stage completes", () => {
    render(
      <AgentTopologyPanel
        runStages={[
          {
            attempt_count: 1,
            created_at: "2026-06-17T00:00:00Z",
            failure_reason: "",
            input: {},
            job_id: "job-1",
            output: {},
            retryable: false,
            stage: "writeback",
            status: "completed",
            updated_at: "2026-06-17T00:01:00Z"
          }
        ]}
      />
    );

    expect(screen.getByLabelText("回写操作 Agent 工位")).toHaveAttribute("data-agent-state", "completed");
    expect(screen.getByText(/写回完成/)).toBeInTheDocument();
  });

  it("opens an agent configuration drawer with model and telemetry", async () => {
    render(
      <AgentTopologyPanel
        agentModelConfig={{
          roles: {
            model_runner: {
              provider: "ark",
              model_id: "seedpro-source",
              mode: "high",
              thinking: "disabled",
              locked: true
            },
            judge_comparator: {
              provider: "ark",
              model_id: "seed2-pro",
              thinking: "enabled",
              temperature: 0.2
            }
          }
        }}
        runStages={[
          {
            attempt_count: 1,
            created_at: "2026-06-17T00:00:00Z",
            failure_reason: "",
            input: {},
            job_id: "job-1",
            output: {
              downgrade_reason: "meta agent budget exceeded",
              meta_agent_enrichment: {
                telemetry: [
                  {
                    agent_role: "judge_comparator",
                    status: "completed",
                    model_id: "seed2-pro",
                    mode: "",
                    thinking: "enabled",
                    latency_ms: 321,
                    error_message: ""
                  }
                ]
              }
            },
            retryable: false,
            stage: "attribution",
            status: "completed",
            updated_at: "2026-06-17T00:01:00Z"
          }
        ]}
      />
    );

    await userEvent.click(screen.getByRole("button", { name: "打开评分对比 Agent配置" }));

    const drawer = screen.getByLabelText("Agent 配置抽屉");
    expect(drawer).toBeInTheDocument();
    expect(within(drawer).getByRole("heading", { name: "评分裁判员" })).toBeInTheDocument();
    expect(within(drawer).getByText("seed2-pro")).toBeInTheDocument();
    expect(within(drawer).getByText("enabled")).toBeInTheDocument();
    expect(within(drawer).getByText("321ms")).toBeInTheDocument();
    expect(within(drawer).getByText(/自动降级：meta agent budget exceeded/)).toBeInTheDocument();
  });

  it.each([
    ["导入接入 Agent", "导入搬运员"],
    ["实验规划 Agent", "路线规划师"],
    ["模型执行 Agent", "模型终端员"],
    ["评分对比 Agent", "评分裁判员"],
    ["证据产物 Agent", "证据档案员"],
    ["根因报告 Agent", "根因分析师"],
    ["回写操作 Agent", "写回调度员"]
  ])("opens the configuration drawer for %s", async (displayName, workerName) => {
    render(<AgentTopologyPanel />);

    const button = screen.getByRole("button", { name: `打开${displayName}配置` });
    await userEvent.click(button);

    expect(button).toHaveAttribute("aria-pressed", "true");
    const drawer = screen.getByLabelText("Agent 配置抽屉");
    expect(drawer).toBeInTheDocument();
    expect(within(drawer).getByRole("heading", { name: workerName })).toBeInTheDocument();
    expect(within(drawer).getByText(new RegExp(displayName))).toBeInTheDocument();
  });

  it("edits configurable agent model selection inside the robot drawer", async () => {
    const onAgentModelConfigChange = vi.fn();
    render(
      <AgentTopologyPanel
        agentModelConfig={{
          roles: {
            model_runner: {
              provider: "ark",
              model_id: "seedpro-source",
              thinking: "disabled",
              locked: true
            },
            report_root_cause: {
              provider: "ark",
              model_id: "seed2-pro",
              thinking: "enabled",
              temperature: 0.2
            }
          }
        }}
        modelCatalog={[
          {
            provider: "ark",
            model_id: "seed2-lite",
            label: "Seed2 Lite",
            description: "lite",
            modes: [],
            supports_thinking: true,
            supports_vision: false,
            supports_video: false,
            locked_for_roles: [],
            default_parameters: {},
            source: "local"
          },
          {
            provider: "ark",
            model_id: "seed2-pro",
            label: "Seed2 Pro",
            description: "pro",
            modes: [],
            supports_thinking: true,
            supports_vision: false,
            supports_video: false,
            locked_for_roles: [],
            default_parameters: {},
            source: "local"
          }
        ]}
        onAgentModelConfigChange={onAgentModelConfigChange}
      />
    );

    await userEvent.click(screen.getByRole("button", { name: "打开根因报告 Agent配置" }));
    const drawer = screen.getByLabelText("Agent 配置抽屉");
    await userEvent.selectOptions(within(drawer).getByLabelText("模型"), "seed2-lite");

    expect(onAgentModelConfigChange).toHaveBeenCalledWith(
      expect.objectContaining({
        roles: expect.objectContaining({
          report_root_cause: expect.objectContaining({ model_id: "seed2-lite" })
        })
      })
    );
  });
});
