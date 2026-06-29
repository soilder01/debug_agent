import type { SubmittedDebugJob } from "./debug";

export type LarkOperationAudit = {
  audit_id: number;
  actor: string;
  connector_mode: string;
  identity: string;
  profile: string;
  service: string;
  operation: string;
  status: string;
  context: string;
  error_type: string;
  hint: string;
  permission_scopes: string[];
  console_url: string;
  risk_action: string;
  duration_ms: number;
  created_at: string;
};

export type LarkOperationAuditListResponse = {
  audits: LarkOperationAudit[];
  total_count: number;
};

export type LarkBotPendingCommand = {
  command_id: string;
  actor: string;
  open_id: string;
  chat_id: string;
  message_id: string;
  tenant_key: string;
  identity: string;
  profile: string;
  command_text: string;
  action_kind: string;
  action: Record<string, unknown>;
  card: Record<string, unknown>;
  status: string;
  note: string;
  execution_result: Record<string, unknown>;
  error_message: string;
  created_at: string;
  expires_at: string;
  confirmed_at: string;
  confirmed_by: string;
  executed_at: string;
};

export type LarkBotPendingCommandListResponse = {
  commands: LarkBotPendingCommand[];
  total_count: number;
};

export type LarkBotBadcaseDraft = {
  draft_id: string;
  actor: string;
  open_id: string;
  chat_id: string;
  message_id: string;
  status: string;
  source_text: string;
  input_source: string;
  model_output: string;
  expected_output: string;
  issue_summary: string;
  task_type: string;
  scoring_standard: string;
  attachments: Array<Record<string, unknown>>;
  links: string[];
  missing_fields: string[];
  progress_notified_keys?: string[];
  progress_panel_message_id?: string;
  submitted_case_id: string;
  submitted_job_id: string;
  error_message: string;
  created_at: string;
  updated_at: string;
};

export type LarkBotBadcaseDraftListResponse = {
  drafts: LarkBotBadcaseDraft[];
  total_count: number;
};

export type LarkBotBadcaseDraftConfirmResponse = {
  draft: LarkBotBadcaseDraft;
  submitted_job: SubmittedDebugJob | null;
};

export type LarkNotificationOutbox = {
  notification_id: string;
  kind: string;
  dedupe_key: string;
  status: string;
  draft_id: string;
  job_id: string;
  case_id: string;
  job_status: string;
  progress_key: string;
  payload: Record<string, unknown>;
  envelope: Record<string, unknown>;
  attempts: number;
  last_error: string;
  created_at: string;
  updated_at: string;
  sent_at: string;
};

export type LarkNotificationOutboxListResponse = {
  notifications: LarkNotificationOutbox[];
  total_count: number;
};

export type LarkBotReplyPayload = {
  command_id: string;
  action_kind: string;
  status: string;
  target_type: "message" | "chat" | "user" | "none";
  message_id: string;
  chat_id: string;
  user_id: string;
  markdown: string;
  idempotency_key: string;
  delivery_args: string[];
};

export type LarkBotPreflightCheck = {
  key: string;
  label: string;
  status: "passed" | "warning" | "failed";
  detail: string;
  action: string;
};

export type LarkBotSetupAcknowledgement = {
  acknowledgement_id: number;
  item_key: string;
  actor: string;
  evidence: string;
  note: string;
  created_at: string;
};

export type LarkBotSetupAcknowledgementRequest = {
  actor: string;
  evidence: string;
  note?: string;
};

export type LarkBotSetupChecklistItem = {
  key: string;
  title: string;
  owner: "debug_agent_operator" | "lark_app_admin" | "workspace_admin" | "security_admin";
  required: boolean;
  status: "done" | "needs_action" | "manual_check";
  detail: string;
  action: string;
  evidence: string;
  acknowledgement?: LarkBotSetupAcknowledgement | null;
};

export type LarkBotPreflight = {
  generated_at: string;
  status: "passed" | "warning" | "failed";
  connector: {
    mode: "cli" | "openapi" | "fake";
    identity: "bot" | "user" | "unknown";
    profile: string;
    auth_status: string;
    token_status: string;
  };
  event_mode: "webhook" | "long_connection";
  event_endpoint_url: string;
  setup_package_url: string;
  required_bot_scopes: string[];
  pending_command_count: number;
  failed_command_count: number;
  recent_missing_scopes: string[];
  operator_required_items: LarkBotSetupChecklistItem[];
  checks: LarkBotPreflightCheck[];
};

export type LarkBotGoLiveGateCheck = {
  key: string;
  label: string;
  status: "passed" | "warning" | "failed";
  detail: string;
  action: string;
};

export type LarkBotGoLiveGate = {
  generated_at: string;
  status: "passed" | "warning" | "failed";
  allowed: boolean;
  decision: string;
  preflight: LarkBotPreflight;
  checks: LarkBotGoLiveGateCheck[];
  export_urls: Record<string, string>;
};

export type LarkBotPermissionRequirement = {
  key: string;
  title: string;
  category: string;
  permission_type: "event_subscription" | "oauth_scope";
  scope: string;
  phase: "required_now" | "recommended_next";
  risk_level: "event" | "read" | "write";
  operation: string;
  required_for: string;
  repair_hint: string;
  status: "manual_check" | "needs_action";
  recent_missing: boolean;
  blocking: boolean;
  console_url: string;
};

export type LarkBotPermissionChecklist = {
  generated_at: string;
  status: "passed" | "warning" | "failed";
  event_mode: "webhook" | "long_connection";
  required_scopes: string[];
  recommended_scopes: string[];
  recent_missing_scopes: string[];
  blocking_scopes: string[];
  requirements: LarkBotPermissionRequirement[];
  admin_handoff_markdown: string;
  console_url: string;
};

export type LarkScopeRequirementStatus = {
  service: string;
  operation: string;
  required_scopes: string[];
  risk_level: "read" | "write";
  identity: string;
  confirmation_required: boolean;
  repair_hint: string;
  console_url: string;
  status: "unknown" | "not_observed_missing" | "missing_recently";
  recent_missing_scopes: string[];
  recent_failure_count: number;
};

export type LarkScopeCheckResponse = {
  connector_mode: string;
  connector_identity: string;
  connector_profile: string;
  auth_check_status: "not_verified";
  requirements: LarkScopeRequirementStatus[];
  recent_missing_scopes: string[];
  repair_steps: string[];
  console_url: string;
};

export type LarkWriteConfirmation = {
  confirmation_id: string;
  actor: string;
  service: string;
  operation: string;
  resource_id: string;
  resource_summary: string;
  risk_action: string;
  required_scopes: string[];
  status: string;
  note: string;
  created_at: string;
  expires_at: string;
  confirmed_at: string;
  confirmed_by: string;
};

export type LarkAuthSession = {
  auth_session_id: string;
  actor: string;
  identity: string;
  profile: string;
  scopes: string[];
  state: string;
  auth_url: string;
  redirect_url: string;
  status: string;
  note: string;
  created_at: string;
  expires_at: string;
  completed_at: string;
  completed_by: string;
};

export type LarkSpreadsheetStatus = {
  configured: boolean;
  spreadsheet_id: string;
  sheet_id: string;
  lark_cli_timeout_seconds: number;
  connector_mode?: string;
  connector_identity?: string;
  connector_profile?: string;
  connector_auth_status?: string;
  connector_token_status?: string;
  connectivity_status: "not_checked" | "ok" | "failed";
  error_message: string;
  error_type?: string;
  permission_scopes?: string[];
  console_url?: string;
  risk_action?: string;
};
