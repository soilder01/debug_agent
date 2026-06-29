from debug_agent.storage.database import create_sqlite_memory_session_factory
from debug_agent.storage.models import Base
from debug_agent.storage.repository import DebugJobRepository


def test_repository_persists_lark_operation_audit_details() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)

    audit = repository.save_lark_operation_audit(
        actor="local-dev-operator",
        connector_mode="cli",
        identity="bot",
        profile="debug-bot",
        service="sheets",
        operation="+csv-get",
        status="failed",
        context="+csv-get --spreadsheet-token sheet --sheet-id tab",
        error_type="permission_denied",
        hint="run lark-cli auth login",
        permission_scopes=["sheets:spreadsheet:readonly"],
        console_url="https://open.feishu.cn/app",
        risk_action="",
        duration_ms=12,
    )

    assert audit.audit_id > 0
    assert audit.actor == "local-dev-operator"
    assert audit.connector_mode == "cli"
    assert audit.identity == "bot"
    assert audit.profile == "debug-bot"
    assert audit.service == "sheets"
    assert audit.operation == "+csv-get"
    assert audit.status == "failed"
    assert audit.error_type == "permission_denied"
    assert audit.hint == "run lark-cli auth login"
    assert audit.permission_scopes == ["sheets:spreadsheet:readonly"]
    assert audit.console_url == "https://open.feishu.cn/app"
    assert audit.duration_ms == 12
    assert audit.created_at


def test_repository_lists_lark_operation_audits_with_filter_and_pagination() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)
    for index, status in enumerate(["failed", "succeeded", "failed"], start=1):
        repository.save_lark_operation_audit(
            actor="local-dev-operator",
            connector_mode="cli",
            identity="bot",
            profile="debug-bot",
            service="sheets",
            operation="+csv-get",
            status=status,
            context=f"operation-{index}",
            error_type="permission_denied" if status == "failed" else "",
            permission_scopes=["scope"] if status == "failed" else [],
            duration_ms=index,
        )

    audits = repository.list_lark_operation_audits(status="failed", limit=1, offset=1)

    assert repository.count_lark_operation_audits() == 3
    assert repository.count_lark_operation_audits(status="failed") == 2
    assert len(audits) == 1
    assert audits[0].context == "operation-1"
    assert audits[0].status == "failed"


def test_repository_creates_and_completes_lark_auth_session() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    Base.metadata.create_all(engine)
    repository = DebugJobRepository(session_factory)

    auth_session = repository.create_lark_auth_session(
        auth_session_id="auth-1",
        actor="local-dev-operator",
        identity="user",
        profile="debug-user",
        scopes=["sheets:spreadsheet:readonly"],
        state="state-1",
        auth_url="https://open.larkoffice.com/app?debug_agent_auth=1",
        redirect_url="https://debug-agent.local/lark/callback",
        note="need user access",
        expires_at="2026-06-22T00:30:00+00:00",
    )

    assert auth_session.auth_session_id == "auth-1"
    assert auth_session.identity == "user"
    assert auth_session.profile == "debug-user"
    assert auth_session.scopes == ["sheets:spreadsheet:readonly"]
    assert auth_session.status == "pending"
    assert auth_session.completed_at == ""

    completed = repository.complete_lark_auth_session(
        "auth-1",
        actor="local-dev-operator",
        note="authorization completed",
    )

    assert completed is not None
    assert completed.status == "authorized"
    assert completed.completed_by == "local-dev-operator"
    assert completed.note == "authorization completed"
    assert completed.completed_at
