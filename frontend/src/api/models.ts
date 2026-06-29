import { buildHttpErrorMessage } from "./http";
import type {
  ModelCatalogResponse,
  AgentModelConnectionTestRequest,
  AgentModelConnectionTestResponse
} from "./types";

export async function fetchAgentModelCatalog(live = false): Promise<ModelCatalogResponse> {
  const response = await fetch(`/api/agent-models${live ? "?live=true" : ""}`);
  if (!response.ok) {
    throw new Error(`加载 Agent 模型目录失败：${response.status}`);
  }
  return (await response.json()) as ModelCatalogResponse;
}


export async function testAgentModelConnection(
  request: AgentModelConnectionTestRequest
): Promise<AgentModelConnectionTestResponse> {
  const response = await fetch("/api/agent-models/test", {
    body: JSON.stringify(request),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(await buildHttpErrorMessage("测试 Agent 模型连接失败", response));
  }
  return (await response.json()) as AgentModelConnectionTestResponse;
}
