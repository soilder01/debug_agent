import { useMemo, useRef, useState } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";

import { testAgentModelConnection, type AgentModelConfig, type DebugRunStage, type ModelCatalogOption } from "../api/client";

gsap.registerPlugin(useGSAP);

const agentRoles = [
  {
    roleId: "case_intake",
    displayName: "导入接入 Agent",
    workerName: "导入搬运员",
    technicalName: "Case Intake Agent",
    variant: "loader",
    toolGlyph: "箱",
    responsibility: "从文件、API 和飞书表格导入并标准化 debug 样本。",
    idleBehavior: "整理样本箱"
  },
  {
    roleId: "experiment_planner",
    displayName: "实验规划 Agent",
    workerName: "路线规划师",
    technicalName: "Experiment Planner Agent",
    variant: "planner",
    toolGlyph: "图",
    responsibility: "按任务类型路由样本，并生成有边界的实验计划。",
    idleBehavior: "擦拭路线板"
  },
  {
    roleId: "model_runner",
    displayName: "模型执行 Agent",
    workerName: "模型终端员",
    technicalName: "Model Runner Agent",
    variant: "operator",
    toolGlyph: "端",
    responsibility: "执行模型调用，并持久化请求、响应和证据。",
    idleBehavior: "校准模型终端"
  },
  {
    roleId: "judge_comparator",
    displayName: "评分对比 Agent",
    workerName: "评分裁判员",
    technicalName: "Judge Comparator Agent",
    variant: "judge",
    toolGlyph: "尺",
    responsibility: "评估模型输出，并产出结构化差异。",
    idleBehavior: "检查评分尺"
  },
  {
    roleId: "evidence_artifact",
    displayName: "证据产物 Agent",
    workerName: "证据档案员",
    technicalName: "Evidence Artifact Agent",
    variant: "archivist",
    toolGlyph: "档",
    responsibility: "生成输入、输出、裁剪和派生证据产物。",
    idleBehavior: "归档证据盒"
  },
  {
    roleId: "report_root_cause",
    displayName: "根因报告 Agent",
    workerName: "根因分析师",
    technicalName: "Report Root Cause Agent",
    variant: "analyst",
    toolGlyph: "因",
    responsibility: "推断根因标签，并生成可审计 debug 报告。",
    idleBehavior: "整理归因白板"
  },
  {
    roleId: "writeback_operator",
    displayName: "回写操作 Agent",
    workerName: "写回调度员",
    technicalName: "Writeback Operator Agent",
    variant: "dispatcher",
    toolGlyph: "飞",
    responsibility: "把结论写回业务系统，并保留审计记录。",
    idleBehavior: "待命写回台"
  }
];

type AgentRoleId = (typeof agentRoles)[number]["roleId"];
type AgentVisualState = "working" | "completed" | "idle";

type AgentTopologyPanelProps = {
  runStages?: DebugRunStage[];
  agentModelConfig?: AgentModelConfig | null;
  modelCatalog?: ModelCatalogOption[];
  onAgentModelConfigChange?: (value: AgentModelConfig) => void;
};

const stageAgentMap: Record<string, AgentRoleId[]> = {
  baseline: ["experiment_planner", "model_runner", "judge_comparator", "evidence_artifact"],
  targeted: ["experiment_planner", "model_runner", "judge_comparator", "evidence_artifact"],
  verification: ["model_runner", "judge_comparator", "evidence_artifact"],
  attribution: ["report_root_cause"],
  writeback: ["writeback_operator"]
};

const stageLabels: Record<string, string> = {
  baseline: "基线复测",
  targeted: "定向深挖",
  verification: "闭环验证",
  attribution: "最终归因",
  writeback: "写回"
};

function agentState(roleId: AgentRoleId, runStages: DebugRunStage[]): AgentVisualState {
  const relatedStages = runStages.filter((stage) => stageAgentMap[stage.stage]?.includes(roleId));
  if (relatedStages.some((stage) => stage.status === "running")) {
    return "working";
  }
  if (relatedStages.some((stage) => stage.status === "completed")) {
    return "completed";
  }
  return "idle";
}

function agentStatusLabel(roleId: AgentRoleId, runStages: DebugRunStage[], state: AgentVisualState) {
  const relatedStages = runStages.filter((stage) => stageAgentMap[stage.stage]?.includes(roleId));
  const runningStage = relatedStages.find((stage) => stage.status === "running");
  if (runningStage) {
    return `${stageLabels[runningStage.stage] ?? runningStage.stage}工作中`;
  }
  const completedStage = [...relatedStages].reverse().find((stage) => stage.status === "completed");
  if (completedStage) {
    return `${stageLabels[completedStage.stage] ?? completedStage.stage}完成`;
  }
  if (state === "idle") {
    return "待命中";
  }
  return "状态同步中";
}

export function AgentTopologyPanel({
  runStages = [],
  agentModelConfig = null,
  modelCatalog = [],
  onAgentModelConfigChange
}: AgentTopologyPanelProps) {
  const topologyRef = useRef<HTMLElement | null>(null);
  const [selectedRoleId, setSelectedRoleId] = useState<AgentRoleId | null>(null);
  const [customModelDraft, setCustomModelDraft] = useState({
    provider: "ark" as "ark" | "api",
    base_url: "",
    api_key: "",
    model_id: ""
  });
  const [customModelStatus, setCustomModelStatus] = useState("");
  const stateSignature = useMemo(
    () => runStages.map((stage) => `${stage.stage}:${stage.status}:${stage.updated_at}`).join("|"),
    [runStages]
  );
  const selectedRole = agentRoles.find((role) => role.roleId === selectedRoleId) ?? null;
  const selectedModel = selectedRole ? agentModelConfig?.roles[selectedRole.roleId] ?? null : null;
  const selectedTelemetry = selectedRole ? latestTelemetryForRole(selectedRole.roleId, runStages) : null;
  const selectedFailures = selectedRole ? fallbackCountForRole(selectedRole.roleId, runStages) : 0;
  const selectedDowngradeReason = selectedRole ? downgradeReasonForRole(selectedRole.roleId, runStages) : "";
  const selectedLocked = selectedRole ? selectedRole.roleId === "model_runner" || Boolean(selectedModel?.locked) : false;
  const selectedCatalogOptions =
    selectedModel?.model_id && !modelCatalog.some((model) => model.model_id === selectedModel.model_id)
      ? [
          {
            provider: selectedModel.provider || "ark",
            model_id: selectedModel.model_id,
            label: `当前自定义：${selectedModel.model_id}`,
            description: selectedModel.base_url || "当前配置中的自定义模型",
            modes: [],
            supports_thinking: true,
            supports_vision: false,
            supports_video: false,
            locked_for_roles: [],
            default_parameters: {},
            source: "custom"
          },
          ...modelCatalog
        ]
      : modelCatalog;

  function updateRole(roleId: string, patch: Record<string, unknown>) {
    if (!agentModelConfig || !onAgentModelConfigChange) {
      return;
    }
    onAgentModelConfigChange({
      roles: {
        ...agentModelConfig.roles,
        [roleId]: {
          ...agentModelConfig.roles[roleId],
          ...patch
        }
      }
    });
  }

  async function testAndUseCustomModel(roleId: string) {
    setCustomModelStatus("正在测试连接...");
    try {
      const result = await testAgentModelConnection(customModelDraft);
      setCustomModelStatus(result.message);
      if (result.ok) {
        updateRole(roleId, {
          provider: customModelDraft.provider,
          model_id: customModelDraft.model_id,
          base_url: customModelDraft.base_url,
          credential_ref: result.credential_ref
        });
      }
    } catch (caught) {
      setCustomModelStatus(caught instanceof Error ? caught.message : "模型连接测试失败");
    }
  }

  useGSAP(
    () => {
      const scope = topologyRef.current;
      if (!scope || window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
        return;
      }

      const idleBodies = scope.querySelectorAll('[data-agent-state="idle"] .agent-worker__body');
      if (idleBodies.length > 0) {
        gsap.to(idleBodies, {
          y: -3,
          duration: 1.8,
          ease: "sine.inOut",
          repeat: -1,
          yoyo: true,
          stagger: 0.12
        });
      }

      const workingTools = scope.querySelectorAll('[data-agent-state="working"] .agent-worker__tool');
      if (workingTools.length > 0) {
        gsap.to(workingTools, {
          rotate: 18,
          transformOrigin: "50% 100%",
          duration: 0.26,
          ease: "power1.inOut",
          repeat: -1,
          yoyo: true
        });
      }

      const workingSparks = scope.querySelectorAll('[data-agent-state="working"] .agent-worker__spark');
      if (workingSparks.length > 0) {
        gsap.to(workingSparks, {
          opacity: 1,
          scale: 1.3,
          duration: 0.5,
          ease: "power2.out",
          repeat: -1,
          yoyo: true,
          stagger: 0.08
        });
      }

      const completedBadges = scope.querySelectorAll('[data-agent-state="completed"] .agent-worker__badge');
      if (completedBadges.length > 0) {
        gsap.to(completedBadges, {
          scale: 1.08,
          duration: 1.2,
          ease: "sine.inOut",
          repeat: -1,
          yoyo: true
        });
      }
    },
    { dependencies: [stateSignature], scope: topologyRef, revertOnUpdate: true }
  );

  return (
    <section ref={topologyRef} className="agent-topology" aria-label="Agent 拓扑">
      <h2>Agent 拓扑</h2>
      <p className="agent-topology__summary">
        状态来自 Debug Run 状态机；谁负责当前阶段，谁进入工作动画，其余 agent 保持待机行为。
      </p>
      <ul className="agent-topology__grid">
        {agentRoles.map((role) => {
          const state = agentState(role.roleId, runStages);
          const statusLabel = agentStatusLabel(role.roleId, runStages, state);
          return (
          <li
            key={role.roleId}
            aria-label={`${role.displayName} 工位`}
            className="agent-workstation"
            data-agent-id={role.roleId}
            data-agent-state={state}
            data-agent-variant={role.variant}
          >
            <button
              type="button"
              className="agent-workstation__open"
              aria-label={`打开${role.displayName}配置`}
              aria-pressed={selectedRoleId === role.roleId}
              onClick={() => setSelectedRoleId(role.roleId)}
            >
              查看配置
            </button>
            <div className="agent-worker" aria-hidden="true">
              <div className="agent-worker__antenna" />
              <div className="agent-worker__hat">
                <span className="agent-worker__hat-mark">{role.toolGlyph}</span>
              </div>
              <div className="agent-worker__head">
                <span className="agent-worker__eye" />
                <span className="agent-worker__eye" />
              </div>
              <div className="agent-worker__body">
                <span className="agent-worker__badge">{state === "completed" ? "OK" : role.roleId.slice(0, 2).toUpperCase()}</span>
                <span className="agent-worker__tool" />
              </div>
              <span className="agent-worker__prop">{role.toolGlyph}</span>
              <span className="agent-worker__spark" />
              <span className="agent-worker__spark" />
            </div>
            <div className="agent-workstation__copy">
              <p className="agent-workstation__worker-name">{role.workerName}</p>
              <h3>{role.displayName}</h3>
              <p>{role.responsibility}</p>
              <p className="agent-workstation__state">
                {statusLabel} · {state === "idle" ? role.idleBehavior : "执行真实 evidence 链路"}
              </p>
            </div>
          </li>
          );
        })}
      </ul>
      {selectedRole ? (
        <aside className="agent-config-drawer" aria-label="Agent 配置抽屉">
          <div className="agent-config-drawer__header">
            <div>
              <p className="agent-config-drawer__eyebrow">Agent 配置</p>
              <h3>{selectedRole.workerName}</h3>
              <p>{selectedRole.displayName} · {selectedRole.technicalName}</p>
            </div>
            <button type="button" onClick={() => setSelectedRoleId(null)}>
              关闭
            </button>
          </div>
          <div className="agent-config-drawer__role-switcher" aria-label="Agent 配置角色切换">
            {agentRoles.map((role) => (
              <button
                key={role.roleId}
                type="button"
                aria-pressed={selectedRoleId === role.roleId}
                onClick={() => setSelectedRoleId(role.roleId)}
              >
                {role.workerName}
              </button>
            ))}
          </div>
          <dl>
            <div>
              <dt>模型</dt>
              <dd>{selectedModel?.model_id || selectedTelemetry?.model_id || "未配置"}</dd>
            </div>
            <div>
              <dt>Thinking</dt>
              <dd>{selectedModel?.thinking || selectedTelemetry?.thinking || "未声明"}</dd>
            </div>
            <div>
              <dt>参数</dt>
              <dd>
                mode={selectedModel?.mode || selectedTelemetry?.mode || "默认"} · temp=
                {selectedModel?.temperature ?? "默认"} · top_p={selectedModel?.top_p ?? "默认"} · max_tokens=
                {selectedModel?.max_tokens ?? "默认"}
              </dd>
            </div>
            <div>
              <dt>锁定</dt>
              <dd>{selectedModel?.locked || selectedRole.roleId === "model_runner" ? "公平复测锁定，不允许修改" : "可配置"}</dd>
            </div>
            <div>
              <dt>最近耗时</dt>
              <dd>{selectedTelemetry?.latency_ms ?? 0}ms</dd>
            </div>
            <div>
              <dt>失败/降级次数</dt>
              <dd>{selectedFailures}</dd>
            </div>
          </dl>
          {selectedTelemetry?.error_message ? <p>最近 fallback：{selectedTelemetry.error_message}</p> : null}
          {selectedDowngradeReason ? <p>自动降级：{selectedDowngradeReason}</p> : null}
          <section className="agent-config-editor" aria-label={`${selectedRole.displayName}模型编辑`}>
            <h4>模型选择</h4>
            <p>
              默认配置会自动生效；只有在这里修改后，后续批量 debug 才会带上覆盖配置。原始复测的模型终端员保持公平锁定。
            </p>
            {agentModelConfig ? (
              <>
                <label>
                  模型
                  <select
                    value={selectedModel?.model_id ?? ""}
                    disabled={selectedLocked}
                    onChange={(event) => {
                      const selected = selectedCatalogOptions.find((model) => model.model_id === event.target.value);
                      updateRole(selectedRole.roleId, {
                        provider: selected?.provider ?? selectedModel?.provider ?? "ark",
                        model_id: event.target.value
                      });
                    }}
                  >
                    {selectedCatalogOptions.map((model) => (
                      <option key={`${model.provider}:${model.model_id}`} value={model.model_id}>
                        {model.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Thinking
                  <select
                    value={selectedModel?.thinking ?? "disabled"}
                    disabled={selectedLocked}
                    onChange={(event) => updateRole(selectedRole.roleId, { thinking: event.target.value })}
                  >
                    <option value="disabled">no-thinking</option>
                    <option value="enabled">thinking</option>
                  </select>
                </label>
                <div className="agent-config-editor__params">
                  <label>
                      模式 Mode
                    <input
                      value={selectedModel?.mode ?? ""}
                      disabled={selectedLocked}
                      placeholder="high"
                      onChange={(event) => updateRole(selectedRole.roleId, { mode: event.target.value })}
                    />
                  </label>
                  <label>
                    温度 Temp
                    <input
                      type="number"
                      min="0"
                      max="2"
                      step="0.1"
                      value={selectedModel?.temperature ?? ""}
                      disabled={selectedLocked}
                      onChange={(event) =>
                        updateRole(selectedRole.roleId, {
                          temperature: event.target.value === "" ? null : Number(event.target.value)
                        })
                      }
                    />
                  </label>
                  <label>
                    Top P
                    <input
                      type="number"
                      min="0"
                      max="1"
                      step="0.05"
                      value={selectedModel?.top_p ?? ""}
                      disabled={selectedLocked}
                      onChange={(event) =>
                        updateRole(selectedRole.roleId, {
                          top_p: event.target.value === "" ? null : Number(event.target.value)
                        })
                      }
                    />
                  </label>
                  <label>
                    最大 Token
                    <input
                      type="number"
                      min="1"
                      max="32768"
                      step="1"
                      value={selectedModel?.max_tokens ?? ""}
                      disabled={selectedLocked}
                      onChange={(event) =>
                        updateRole(selectedRole.roleId, {
                          max_tokens: event.target.value === "" ? null : Number(event.target.value)
                        })
                      }
                    />
                  </label>
                </div>
                {!selectedLocked ? (
                  <div className="agent-config-editor__custom">
                    <h4>添加自定义兼容模型</h4>
                    <p>用于测试 Ark/OpenAI 兼容的 `/models` 接口；API key 只参与本次测试，不写入任务配置。</p>
                    <label>
                      供应商 Provider
                      <select
                        value={customModelDraft.provider}
                        onChange={(event) =>
                          setCustomModelDraft((current) => ({
                            ...current,
                            provider: event.target.value as "ark" | "api"
                          }))
                        }
                      >
                        <option value="ark">Ark</option>
                        <option value="api">OpenAI-compatible API</option>
                      </select>
                    </label>
                    <label>
                      Base URL
                      <input
                        value={customModelDraft.base_url}
                        placeholder="https://ark.cn-beijing.volces.com/api/v3"
                        onChange={(event) =>
                          setCustomModelDraft((current) => ({ ...current, base_url: event.target.value }))
                        }
                      />
                    </label>
                    <label>
                      API Key
                      <input
                        type="password"
                        value={customModelDraft.api_key}
                        placeholder="仅用于测试，不会持久化"
                        onChange={(event) =>
                          setCustomModelDraft((current) => ({ ...current, api_key: event.target.value }))
                        }
                      />
                    </label>
                    <label>
                      Model ID
                      <input
                        value={customModelDraft.model_id}
                        placeholder="ep-..."
                        onChange={(event) =>
                          setCustomModelDraft((current) => ({ ...current, model_id: event.target.value }))
                        }
                      />
                    </label>
                    <button type="button" onClick={() => void testAndUseCustomModel(selectedRole.roleId)}>
                      测试并加入当前 Agent
                    </button>
                    {customModelStatus ? <p>{customModelStatus}</p> : null}
                  </div>
                ) : null}
              </>
            ) : (
              <p>默认配置加载中；未修改时使用后端默认模型路由。</p>
            )}
          </section>
        </aside>
      ) : null}
    </section>
  );
}

type AgentTelemetry = {
  agent_role: string;
  model_id: string;
  mode: string;
  thinking: string;
  latency_ms: number;
  status: string;
  error_message: string;
};

function latestTelemetryForRole(roleId: string, runStages: DebugRunStage[]): AgentTelemetry | null {
  const telemetry = telemetryFromStages(runStages).filter((item) => item.agent_role === roleId);
  return telemetry.length > 0 ? telemetry[telemetry.length - 1] : null;
}

function fallbackCountForRole(roleId: string, runStages: DebugRunStage[]): number {
  return telemetryFromStages(runStages).filter(
    (item) => item.agent_role === roleId && (item.status === "fallback" || Boolean(item.error_message))
  ).length;
}

function downgradeReasonForRole(roleId: string, runStages: DebugRunStage[]): string {
  if (roleId === "model_runner") {
    return "";
  }
  for (const stage of [...runStages].reverse()) {
    const reason = stage.output.downgrade_reason ?? stage.input.downgrade_reason;
    if (typeof reason === "string" && reason) {
      return reason;
    }
  }
  return "";
}

function telemetryFromStages(runStages: DebugRunStage[]): AgentTelemetry[] {
  const rows: AgentTelemetry[] = [];
  for (const stage of runStages) {
    const enrichment = recordValue(stage.output.meta_agent_enrichment);
    const telemetry = enrichment ? enrichment.telemetry : undefined;
    if (!Array.isArray(telemetry)) {
      continue;
    }
    for (const item of telemetry) {
      const row = recordValue(item);
      if (!row) {
        continue;
      }
      rows.push({
        agent_role: stringValue(row.agent_role),
        model_id: stringValue(row.model_id),
        mode: stringValue(row.mode),
        thinking: stringValue(row.thinking),
        latency_ms: numberValue(row.latency_ms),
        status: stringValue(row.status),
        error_message: stringValue(row.error_message)
      });
    }
  }
  return rows;
}

function recordValue(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? value as Record<string, unknown> : null;
}

function stringValue(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function numberValue(value: unknown): number {
  return typeof value === "number" ? value : 0;
}
