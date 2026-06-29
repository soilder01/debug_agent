import type { LarkScopeCheckResponse, LarkScopeRequirementStatus } from "../api/client";

type LarkScopeRepairPanelProps = {
  scopeCheck: LarkScopeCheckResponse;
};

export function LarkScopeRepairPanel({ scopeCheck }: LarkScopeRepairPanelProps) {
  return (
    <section className="writeback-audit-list" aria-label="Lark 权限修复建议">
      <p>Lark 权限检查：{scopeCheck.auth_check_status === "not_verified" ? "未直接验证授权状态" : scopeCheck.auth_check_status}</p>
      <p>
        Connector：{scopeCheck.connector_mode} / 身份 {connectorIdentityLabel(scopeCheck.connector_identity)} / Profile{" "}
        {scopeCheck.connector_profile || "默认"}
      </p>
      {scopeCheck.recent_missing_scopes.length ? (
        <p>最近缺少权限：{scopeCheck.recent_missing_scopes.join(", ")}</p>
      ) : (
        <p>最近失败审计未发现缺失权限。</p>
      )}
      <ul aria-label="Lark 操作权限需求">
        {scopeCheck.requirements.map((requirement) => (
          <li className="writeback-audit-list__item" key={`${requirement.service}:${requirement.operation}`}>
            <p>
              {requirement.service} {requirement.operation}：{scopeRequirementStatusLabel(requirement)}
            </p>
            <p>需要 scope：{requirement.required_scopes.join(", ")}</p>
            <p>风险级别：{requirement.risk_level === "write" ? "写入" : "读取"}</p>
            {requirement.confirmation_required ? <p>执行写入前需要风险确认。</p> : null}
            {requirement.recent_missing_scopes.length ? (
              <p>最近缺失：{requirement.recent_missing_scopes.join(", ")}</p>
            ) : null}
            <p>修复建议：{requirement.repair_hint}</p>
          </li>
        ))}
      </ul>
      <ol aria-label="Lark 权限修复步骤">
        {scopeCheck.repair_steps.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
    </section>
  );
}

function connectorIdentityLabel(identity: string): string {
  if (identity === "bot") {
    return "应用";
  }
  if (identity === "user") {
    return "用户";
  }
  return "未知";
}

function scopeRequirementStatusLabel(requirement: LarkScopeRequirementStatus): string {
  if (requirement.status === "missing_recently") {
    return "最近失败审计显示缺失";
  }
  if (requirement.status === "not_observed_missing") {
    return "最近未发现缺失";
  }
  return "未验证";
}
