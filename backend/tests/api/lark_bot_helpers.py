import base64
import hashlib
import json
import time
from uuid import uuid4

from Crypto.Cipher import AES
from debug_agent.api import routes
from debug_agent.reports.generator import DebugReport, ObservedFailure, RootCause
from debug_agent.spreadsheets.sync import SpreadsheetSourceRow


class RecordingBaseConnector:
    def __init__(self) -> None:
        self.args: list[str] = []
        self.payload: dict[str, str] = {}
        self.run_count = 0

    def run_json(self, args: list[str], stdin: str | None = None) -> dict[str, object]:
        self.run_count += 1
        self.args = list(args)
        payload_index = args.index("--json") + 1
        self.payload = json.loads(args[payload_index])
        return {"updated": True, "record": {"record_id": self.payload.get("record_id", "")}}


class RecordingDocsConnector:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], str | None]] = []

    def run_json(self, args: list[str], stdin: str | None = None) -> dict[str, object]:
        self.calls.append((list(args), stdin))
        return {
            "document": {
                "document_id": "doccn-debug-report",
                "url": "https://bytedance.larkoffice.com/docx/doccn-debug-report",
            }
        }


class RecordingWritebackClient:
    def __init__(self) -> None:
        self.spreadsheet_id = ""
        self.sheet_id = ""
        self.row_id = ""
        self.fields: dict[str, str] = {}
        self.update_count = 0

    def update_row(
        self,
        spreadsheet_id: str,
        sheet_id: str,
        row_id: str,
        fields: dict[str, str],
    ) -> dict[str, str]:
        self.update_count += 1
        self.spreadsheet_id = spreadsheet_id
        self.sheet_id = sheet_id
        self.row_id = row_id
        self.fields = fields
        return fields


class StaticSpreadsheetClient:
    def __init__(self, rows: list[SpreadsheetSourceRow]) -> None:
        self.rows = rows
        self.requested_spreadsheet_id = ""
        self.requested_sheet_id = ""

    def list_rows(self, spreadsheet_id: str, sheet_id: str) -> list[SpreadsheetSourceRow]:
        self.requested_spreadsheet_id = spreadsheet_id
        self.requested_sheet_id = sheet_id
        return self.rows


class RowsJsonSpreadsheetTransport:
    def __init__(self, rows_json: dict[str, object]) -> None:
        self.rows_json = rows_json

    def read_values(self, spreadsheet_id: str, sheet_id: str) -> list[list[object]]:
        raise AssertionError("rows-json path should be used for Lark spreadsheet rows")

    def read_rows_json(self, spreadsheet_id: str, sheet_id: str) -> dict[str, object]:
        return self.rows_json

    def update_row(
        self,
        spreadsheet_id: str,
        sheet_id: str,
        row_id: str,
        fields: dict[str, str],
    ) -> dict[str, str]:
        return fields


class DummyModelResult:
    def __init__(self, **values: object) -> None:
        self.values = values

    def model_dump(self, mode: str = "json") -> dict[str, object]:
        return self.values


def wait_pending_command_status(
    command_id: str,
    status: str,
    *,
    timeout_seconds: float = 3.0,
) -> object:
    deadline = time.monotonic() + timeout_seconds
    last = None
    while time.monotonic() < deadline:
        last = routes.job_repository.get_lark_bot_pending_command(command_id)
        if last is not None and last.status == status:
            return last
        time.sleep(0.02)
    assert last is not None
    assert last.status == status
    return last


def valid_spreadsheet_row_values(case_id: str, *, answer: str = "42") -> dict[str, object]:
    golden_answer = {"answers": [{"box_id": 1, "student_answer": answer}]}
    return {
        "case_id": case_id,
        "image_uri": f"file://{case_id}.png",
        "prompt": "Read the answer",
        "golden_answer_json": golden_answer,
        "scoring_standard": "exact match",
        "predictions_json": [
            {"trial": 1, "raw_output": json.dumps(golden_answer), "score": 1},
        ],
        "avg_score": 1.0,
    }


def create_spreadsheet_rerun_writeback_decision_fixture() -> tuple[str, str, str, str, str]:
    unique = uuid4().hex[:12]
    command_id = f"cmd-sync-{unique}"
    run_id = f"run-sync-{unique}"
    job_id = f"job-sync-{unique}"
    batch_id = f"batch-sync-{unique}"
    actor = f"ou_sync_{unique}"
    chat_id = f"oc_sync_{unique}"
    report_url = f"/api/artifacts/files/{job_id}_auto_closure_report.md"
    row_results = [
        {
            "row_id": "row-1",
            "case_id": "handwrite233",
            "job_id": job_id,
            "job_status": "completed",
            "report_url": report_url,
            "writeback_status": "sync_decision_pending",
            "source_mapped": True,
            "spreadsheet_id": "spreadsheet-sync",
            "sheet_id": "sheet-sync",
        }
    ]
    reports = [
        {
            "job_id": job_id,
            "case_id": "handwrite233",
            "report_artifact_url": report_url,
            "writeback_status": "sync_decision_pending",
        }
    ]
    routes.job_repository.create_job(
        job_id=job_id,
        case_id="handwrite233",
        artifact_group_id=batch_id,
    )
    routes.job_repository.mark_completed(job_id)
    routes.job_repository.create_lark_bot_pending_command(
        command_id=command_id,
        actor=actor,
        open_id=actor,
        chat_id=chat_id,
        message_id=f"om_sync_{unique}",
        tenant_key="tenant-sync",
        identity="bot",
        profile="debug-bot",
        command_text="/debug spreadsheet rerun --report --writeback",
        action_kind="spreadsheet_rerun",
        action={
            "kind": "spreadsheet_rerun",
            "parameters": {"report": True, "auto_closure": True, "writeback": True},
        },
        card={"title": "表格批处理报告同步确认"},
        note="Created by test fixture.",
        expires_at="2026-06-27T00:30:00+00:00",
    )
    routes.job_repository.complete_lark_bot_pending_command(
        command_id,
        status="executed",
        execution_result={"writeback_decision_status": "pending"},
    )
    routes.job_repository.create_xiaod_execution_run(
        run_id=run_id,
        tenant_key="tenant-sync",
        chat_id=chat_id,
        open_id=actor,
        command_id=command_id,
        batch_id=batch_id,
        job_id=job_id,
        action_kind="spreadsheet_rerun",
        status="writeback_decision_pending",
        summary={
            "command_id": command_id,
            "batch_id": batch_id,
            "job_ids": [job_id],
            "row_results": row_results,
            "report_requested": True,
            "report_count": 1,
            "writeback_requested": True,
            "writeback_decision_status": "pending",
            "auto_closure_reports": reports,
        },
    )
    routes.job_repository.create_xiaod_pending_decision(
        decision_id=f"decision-sync-{unique}",
        tenant_key="tenant-sync",
        chat_id=chat_id,
        open_id=actor,
        decision_kind="spreadsheet_rerun_writeback_sync",
        command_id=command_id,
        run_id=run_id,
        payload={"row_results": row_results, "report_count": 1, "default": "no_sync"},
        note="Reports generated; waiting for explicit spreadsheet sync decision.",
        expires_at="2026-06-27T00:30:00+00:00",
    )
    return command_id, run_id, job_id, actor, chat_id


def mark_auto_closure_completed(job_id: str) -> None:
    routes.job_repository.save_debug_run_stage(
        job_id=job_id,
        stage="auto_closure",
        status="completed",
        input={"source_job_id": job_id},
        output={"source_job_id": job_id},
        failure_reason="",
        retryable=True,
    )


def spreadsheet_rerun_writeback_action_payload(
    *,
    action: str,
    command_id: str,
    actor: str,
) -> dict[str, object]:
    return {
        "header": {"event_type": "card.action.trigger"},
        "event": {
            "operator": {"open_id": actor},
            "action": {
                "value": {
                    "action": action,
                    "command_id": command_id,
                }
            },
        },
    }


def completed_debug_report(*, job_id: str) -> DebugReport:
    return DebugReport(
        job_id=job_id,
        case_id="handwrite233",
        status="needs_human_review",
        observed_failure=ObservedFailure(
            type="wrong_answer",
            summary="把 8 识别成 3",
            affected_box_ids=[],
        ),
        planned_experiments=["baseline", "targeted"],
        experiment_summary=None,
        root_cause=RootCause(
            label="model_call_error",
            confidence="high",
            evidence_summary="模型调用失败，未能完成稳定复测。",
        ),
        recommended_actions=[{"priority": "P0", "summary": "先修复模型调用链路后重跑该 badcase。"}],
        suggested_sheet_fields={
            "错误原因": "model_call_error",
            "评估问题反馈": "模型调用失败，未能完成稳定复测。",
        },
    )


def encrypt_lark_event_payload(payload: dict[str, object], encrypt_key: str) -> str:
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    padding_size = AES.block_size - (len(raw) % AES.block_size)
    padded = raw + bytes([padding_size]) * padding_size
    key = hashlib.sha256(encrypt_key.encode("utf-8")).digest()
    iv = b"0123456789abcdef"
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return base64.b64encode(iv + cipher.encrypt(padded)).decode("ascii")
