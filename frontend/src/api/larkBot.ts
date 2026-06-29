import { buildHttpErrorMessage } from "./http";
import type {
  ProductionReadiness,
  PilotGate,
  LarkOperationAuditListResponse,
  LarkBotPendingCommand,
  LarkBotPendingCommandListResponse,
  LarkBotBadcaseDraftListResponse,
  LarkBotBadcaseDraftConfirmResponse,
  LarkNotificationOutboxListResponse,
  LarkBotReplyPayload,
  LarkBotSetupAcknowledgement,
  LarkBotSetupAcknowledgementRequest,
  LarkBotPreflight,
  LarkBotGoLiveGate,
  LarkBotPermissionChecklist,
  LarkScopeCheckResponse,
  LarkAuthSession
} from "./types";

export async function fetchLarkOperationAudits(
  status?: string,
  limit?: number,
  offset?: number
): Promise<LarkOperationAuditListResponse> {
  const params = new URLSearchParams();
  if (status) {
    params.set("status", status);
  }
  if (limit !== undefined) {
    params.set("limit", String(limit));
  }
  if (offset !== undefined) {
    params.set("offset", String(offset));
  }
  const query = params.size > 0 ? `?${params.toString()}` : "";
  const response = await fetch(`/api/lark/operation-audits${query}`);
  if (!response.ok) {
    throw new Error(`加载 Lark 操作审计失败：${response.status}`);
  }
  return (await response.json()) as LarkOperationAuditListResponse;
}


export async function fetchLarkBotPendingCommands(
  status?: string,
  limit?: number,
  offset?: number
): Promise<LarkBotPendingCommandListResponse> {
  const params = new URLSearchParams();
  if (status) {
    params.set("status", status);
  }
  if (limit !== undefined) {
    params.set("limit", String(limit));
  }
  if (offset !== undefined) {
    params.set("offset", String(offset));
  }
  const query = params.size > 0 ? `?${params.toString()}` : "";
  const response = await fetch(`/api/lark/bot/commands/pending${query}`);
  if (!response.ok) {
    throw new Error(`加载机器人待确认命令失败：${response.status}`);
  }
  return (await response.json()) as LarkBotPendingCommandListResponse;
}


export async function confirmLarkBotPendingCommand(
  commandId: string,
  request: { actor?: string; note?: string } = {}
): Promise<LarkBotPendingCommand> {
  const response = await fetch(`/api/lark/bot/commands/pending/${encodeURIComponent(commandId)}/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request)
  });
  if (!response.ok) {
    throw new Error(await buildHttpErrorMessage("确认机器人命令失败", response));
  }
  return (await response.json()) as LarkBotPendingCommand;
}


export async function fetchLarkBotPendingCommandReplyPreview(commandId: string): Promise<LarkBotReplyPayload> {
  const response = await fetch(`/api/lark/bot/commands/pending/${encodeURIComponent(commandId)}/reply-preview`);
  if (!response.ok) {
    throw new Error(`加载机器人回复预览失败：${response.status}`);
  }
  return (await response.json()) as LarkBotReplyPayload;
}


export async function fetchLarkBotBadcaseDrafts(
  status?: string,
  limit?: number,
  offset?: number
): Promise<LarkBotBadcaseDraftListResponse> {
  const params = new URLSearchParams();
  if (status) {
    params.set("status", status);
  }
  if (limit !== undefined) {
    params.set("limit", String(limit));
  }
  if (offset !== undefined) {
    params.set("offset", String(offset));
  }
  const query = params.size > 0 ? `?${params.toString()}` : "";
  const response = await fetch(`/api/lark/bot/badcase-drafts${query}`);
  if (!response.ok) {
    throw new Error(`加载机器人 badcase 草稿失败：${response.status}`);
  }
  return (await response.json()) as LarkBotBadcaseDraftListResponse;
}


export async function fetchLarkBotNotificationOutbox(
  status?: string,
  limit?: number,
  offset?: number
): Promise<LarkNotificationOutboxListResponse> {
  const params = new URLSearchParams();
  if (status) {
    params.set("status", status);
  }
  if (limit !== undefined) {
    params.set("limit", String(limit));
  }
  if (offset !== undefined) {
    params.set("offset", String(offset));
  }
  const query = params.size > 0 ? `?${params.toString()}` : "";
  const response = await fetch(`/api/lark/bot/notification-outbox${query}`);
  if (!response.ok) {
    throw new Error(`加载飞书通知 Outbox 失败：${response.status}`);
  }
  return (await response.json()) as LarkNotificationOutboxListResponse;
}


export async function confirmLarkBotBadcaseDraft(
  draftId: string,
  request: { actor?: string; note?: string; create_job?: boolean } = {}
): Promise<LarkBotBadcaseDraftConfirmResponse> {
  const response = await fetch(`/api/lark/bot/badcase-drafts/${encodeURIComponent(draftId)}/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request)
  });
  if (!response.ok) {
    throw new Error(await buildHttpErrorMessage("确认机器人 badcase 草稿失败", response));
  }
  return (await response.json()) as LarkBotBadcaseDraftConfirmResponse;
}


export async function fetchLarkBotPreflight(): Promise<LarkBotPreflight> {
  const response = await fetch("/api/lark/bot/preflight");
  if (!response.ok) {
    throw new Error(`加载机器人上线预检失败：${response.status}`);
  }
  return (await response.json()) as LarkBotPreflight;
}


export async function acknowledgeLarkBotSetupItem(
  itemKey: string,
  request: LarkBotSetupAcknowledgementRequest
): Promise<LarkBotSetupAcknowledgement> {
  const response = await fetch(`/api/lark/bot/setup-acknowledgements/${encodeURIComponent(itemKey)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request)
  });
  if (!response.ok) {
    throw new Error(`记录机器人接入确认失败：${response.status}`);
  }
  return (await response.json()) as LarkBotSetupAcknowledgement;
}


export async function fetchLarkBotGoLiveGate(): Promise<LarkBotGoLiveGate> {
  const response = await fetch("/api/lark/bot/go-live-gate");
  if (!response.ok) {
    throw new Error(`加载机器人真实上线门禁失败：${response.status}`);
  }
  return (await response.json()) as LarkBotGoLiveGate;
}


export async function fetchLarkBotPermissionChecklist(): Promise<LarkBotPermissionChecklist> {
  const response = await fetch("/api/lark/bot/permission-checklist");
  if (!response.ok) {
    throw new Error(`加载机器人权限清单失败：${response.status}`);
  }
  return (await response.json()) as LarkBotPermissionChecklist;
}


export async function fetchLarkScopeCheck(service?: string, operation?: string): Promise<LarkScopeCheckResponse> {
  const params = new URLSearchParams();
  if (service) {
    params.set("service", service);
  }
  if (operation) {
    params.set("operation", operation);
  }
  const query = params.size > 0 ? `?${params.toString()}` : "";
  const response = await fetch(`/api/lark/scopes/check${query}`);
  if (!response.ok) {
    throw new Error(`检查 Lark 权限需求失败：${response.status}`);
  }
  return (await response.json()) as LarkScopeCheckResponse;
}


export async function fetchProductionReadiness(): Promise<ProductionReadiness> {
  const response = await fetch("/api/operations/readiness");
  if (!response.ok) {
    throw new Error(`加载生产运行就绪状态失败：${response.status}`);
  }
  return (await response.json()) as ProductionReadiness;
}


export async function fetchPilotGate(): Promise<PilotGate> {
  const response = await fetch("/api/operations/pilot-gate");
  if (!response.ok) {
    throw new Error(`加载试点准入评估失败：${response.status}`);
  }
  return (await response.json()) as PilotGate;
}


export async function createLarkAuthSession(request: {
  identity?: "bot" | "user";
  profile?: string;
  scopes?: string[];
  redirectUrl?: string;
  actor?: string;
  note?: string;
}): Promise<LarkAuthSession> {
  const response = await fetch("/api/lark/auth-sessions", {
    body: JSON.stringify({
      identity: request.identity ?? "user",
      profile: request.profile ?? "",
      scopes: request.scopes ?? [],
      redirect_url: request.redirectUrl ?? "",
      actor: request.actor ?? "",
      note: request.note ?? ""
    }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`创建 Lark 授权会话失败：${response.status}`);
  }
  return (await response.json()) as LarkAuthSession;
}


export async function completeLarkAuthSession(
  authSessionId: string,
  request: { actor?: string; note?: string } = {}
): Promise<LarkAuthSession> {
  const response = await fetch(`/api/lark/auth-sessions/${encodeURIComponent(authSessionId)}/complete`, {
    body: JSON.stringify({
      actor: request.actor ?? "",
      note: request.note ?? ""
    }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`完成 Lark 授权会话失败：${response.status}`);
  }
  return (await response.json()) as LarkAuthSession;
}
