from sqlalchemy import inspect

from debug_agent.storage.database import create_sqlite_memory_session_factory, ensure_database_schema
from debug_agent.storage.repository import DebugJobRepository, LarkBotPendingCommand


def test_ensure_database_schema_creates_xiaod_execution_lifecycle_tables() -> None:
    _session_factory, engine = create_sqlite_memory_session_factory()

    ensure_database_schema(engine)

    table_names = set(inspect(engine).get_table_names())
    assert {
        "xiaod_execution_runs",
        "xiaod_pending_decisions",
        "xiaod_command_audits",
    }.issubset(table_names)


def test_xiaod_active_state_is_isolated_by_tenant_chat_and_user() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    ensure_database_schema(engine)
    repository = DebugJobRepository(session_factory)

    repository.create_xiaod_execution_run(
        run_id="run-user-a",
        tenant_key="tenant-1",
        chat_id="chat-1",
        open_id="ou_a",
        command_id="cmd-user-a",
        batch_id="batch-user-a",
        action_kind="spreadsheet_rerun",
        status="running",
        summary={"title": "user a run"},
    )
    repository.create_xiaod_execution_run(
        run_id="run-user-b",
        tenant_key="tenant-1",
        chat_id="chat-1",
        open_id="ou_b",
        command_id="cmd-user-b",
        batch_id="batch-user-b",
        action_kind="spreadsheet_rerun",
        status="running",
        summary={"title": "user b run"},
    )
    repository.create_xiaod_execution_run(
        run_id="run-other-tenant",
        tenant_key="tenant-2",
        chat_id="chat-1",
        open_id="ou_a",
        command_id="cmd-other-tenant",
        status="running",
    )
    repository.create_xiaod_pending_decision(
        decision_id="decision-user-a",
        tenant_key="tenant-1",
        chat_id="chat-1",
        open_id="ou_a",
        decision_kind="retain_or_delete_unexecuted_command",
        command_id="cmd-user-a",
        payload={"summary": "user a pending command"},
    )
    repository.create_xiaod_pending_decision(
        decision_id="decision-user-b",
        tenant_key="tenant-1",
        chat_id="chat-1",
        open_id="ou_b",
        decision_kind="retain_or_delete_unexecuted_command",
        command_id="cmd-user-b",
        payload={"summary": "user b pending command"},
    )
    _create_pending_command(repository, command_id="cmd-user-a", open_id="ou_a")
    _create_pending_command(repository, command_id="cmd-user-b", open_id="ou_b")

    assert (
        repository.get_active_xiaod_execution_run(
            tenant_key="tenant-1",
            chat_id="chat-1",
            open_id="ou_a",
        ).run_id
        == "run-user-a"
    )
    assert (
        repository.get_active_xiaod_execution_run(
            tenant_key="tenant-1",
            chat_id="chat-1",
            open_id="ou_b",
        ).run_id
        == "run-user-b"
    )
    assert (
        repository.get_active_xiaod_execution_run(
            tenant_key="tenant-2",
            chat_id="chat-1",
            open_id="ou_a",
        ).run_id
        == "run-other-tenant"
    )
    assert (
        repository.get_pending_xiaod_decision(
            tenant_key="tenant-1",
            chat_id="chat-1",
            open_id="ou_a",
        ).decision_id
        == "decision-user-a"
    )
    assert (
        repository.get_pending_xiaod_decision(
            tenant_key="tenant-1",
            chat_id="chat-1",
            open_id="ou_b",
        ).decision_id
        == "decision-user-b"
    )
    assert (
        repository.get_active_lark_bot_pending_command_for_user(
            tenant_key="tenant-1",
            chat_id="chat-1",
            open_id="ou_a",
        ).command_id
        == "cmd-user-a"
    )
    assert (
        repository.get_active_lark_bot_pending_command_for_user(
            tenant_key="tenant-1",
            chat_id="chat-1",
            open_id="ou_b",
        ).command_id
        == "cmd-user-b"
    )


def test_xiaod_default_delete_marks_command_terminal_and_records_audit() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    ensure_database_schema(engine)
    repository = DebugJobRepository(session_factory)
    _create_pending_command(repository, command_id="cmd-default-delete", open_id="ou_a")

    deleted = repository.default_delete_lark_bot_pending_command(
        "cmd-default-delete",
        actor="xiaod-cleanup",
        note="retain/delete decision timed out",
    )

    assert deleted is not None
    assert deleted.status == "default_deleted"
    assert (
        repository.get_active_lark_bot_pending_command_for_user(
            tenant_key="tenant-1",
            chat_id="chat-1",
            open_id="ou_a",
        )
        is None
    )
    audits = repository.list_xiaod_command_audits(command_id="cmd-default-delete")
    assert len(audits) == 1
    assert audits[0].event_kind == "command_default_deleted"
    assert audits[0].status == "default_deleted"
    assert audits[0].actor == "xiaod-cleanup"
    assert audits[0].reason == "retain/delete decision timed out"
    assert audits[0].payload["action_kind"] == "spreadsheet_rerun"


def test_xiaod_retain_keeps_command_queryable_without_active_reminder() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    ensure_database_schema(engine)
    repository = DebugJobRepository(session_factory)
    _create_pending_command(repository, command_id="cmd-retain", open_id="ou_a")

    retained = repository.retain_lark_bot_pending_command(
        "cmd-retain",
        actor="ou_a",
        note="user chose to handle later",
    )

    assert retained is not None
    assert retained.status == "retained"
    assert repository.get_lark_bot_pending_command("cmd-retain").status == "retained"
    assert (
        repository.get_active_lark_bot_pending_command_for_user(
            tenant_key="tenant-1",
            chat_id="chat-1",
            open_id="ou_a",
        )
        is None
    )
    audits = repository.list_xiaod_command_audits(command_id="cmd-retain")
    assert [audit.status for audit in audits] == ["retained"]
    assert audits[0].event_kind == "command_retained"


def test_xiaod_delete_marks_command_deleted_and_records_audit() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    ensure_database_schema(engine)
    repository = DebugJobRepository(session_factory)
    _create_pending_command(repository, command_id="cmd-delete", open_id="ou_a")

    deleted = repository.delete_lark_bot_pending_command(
        "cmd-delete",
        actor="ou_a",
        note="user chose delete",
    )

    assert deleted is not None
    assert deleted.status == "deleted"
    assert repository.get_lark_bot_pending_command("cmd-delete").status == "deleted"
    audits = repository.list_xiaod_command_audits(command_id="cmd-delete")
    assert [audit.event_kind for audit in audits] == ["command_deleted"]
    assert audits[0].status == "deleted"


def _create_pending_command(
    repository: DebugJobRepository,
    *,
    command_id: str,
    open_id: str,
) -> LarkBotPendingCommand:
    return repository.create_lark_bot_pending_command(
        command_id=command_id,
        actor=open_id,
        open_id=open_id,
        chat_id="chat-1",
        message_id=f"message-{command_id}",
        tenant_key="tenant-1",
        identity="bot",
        profile="debug-bot",
        command_text="/debug spreadsheet rerun",
        action_kind="spreadsheet_rerun",
        action={"kind": "spreadsheet_rerun"},
        card={"title": "spreadsheet rerun"},
        note="Created from XiaoD test.",
        expires_at="2026-06-27T00:30:00+00:00",
    )
