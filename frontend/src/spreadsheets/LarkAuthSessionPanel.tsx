import type { LarkAuthSession } from "../api/client";

type LarkAuthSessionPanelProps = {
  authSession: LarkAuthSession | null;
  onCreateAuthSession: () => void;
  onCompleteAuthSession: () => void;
};

export function LarkAuthSessionPanel({
  authSession,
  onCreateAuthSession,
  onCompleteAuthSession
}: LarkAuthSessionPanelProps) {
  return (
    <section className="writeback-audit-list" aria-label="Lark 授权会话">
      <p>Lark 授权会话：{authSession ? authSessionStatusLabel(authSession.status) : "未创建"}</p>
      <div className="writeback-audit-filters">
        <button type="button" onClick={onCreateAuthSession}>
          创建 Lark 授权会话
        </button>
        <button type="button" onClick={onCompleteAuthSession} disabled={!authSession || authSession.status !== "pending"}>
          标记 Lark 授权完成
        </button>
      </div>
      {authSession ? (
        <>
          <p>
            授权身份：{identityLabel(authSession.identity)} / Profile {authSession.profile || "默认"}
          </p>
          <p>授权 scope：{authSession.scopes.join(", ") || "未声明"}</p>
          <p>授权 state：{authSession.state}</p>
          <p>过期时间：{authSession.expires_at}</p>
          {authSession.completed_at ? <p>完成时间：{authSession.completed_at}</p> : null}
          <a href={authSession.auth_url} target="_blank" rel="noreferrer">
            打开 Lark 授权入口
          </a>
        </>
      ) : (
        <p>创建会话后，按授权入口完成飞书授权，再回到这里标记完成。</p>
      )}
    </section>
  );
}

function authSessionStatusLabel(status: string): string {
  if (status === "authorized") {
    return "已授权";
  }
  if (status === "pending") {
    return "待授权";
  }
  if (status === "expired") {
    return "已过期";
  }
  return status || "未知";
}

function identityLabel(identity: string): string {
  if (identity === "bot") {
    return "应用";
  }
  if (identity === "user") {
    return "用户";
  }
  return "未知";
}
