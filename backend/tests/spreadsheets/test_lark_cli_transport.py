import json
import subprocess

import pytest

from debug_agent.spreadsheets.lark import LarkCliError, LarkCliSheetsTransport
from debug_agent.telemetry.performance import performance_recorder


class RecordingCommandRunner:
    def __init__(self, output: dict[str, object] | list[dict[str, object]]) -> None:
        self.outputs = output if isinstance(output, list) else [output]
        self.calls: list[tuple[list[str], str | None]] = []

    def __call__(self, args: list[str], stdin: str | None = None) -> str:
        self.calls.append((args, stdin))
        return json.dumps(self.outputs.pop(0))


def test_lark_cli_transport_reads_rows_json_as_value_matrix() -> None:
    runner = RecordingCommandRunner(
        {
            "ok": True,
            "data": {
                "rows": [
                    {"row_number": 1, "values": {"A": "case_id", "B": "image_uri", "C": "avg_score"}},
                    {"row_number": 2, "values": {"A": "case-1", "B": "file://case-1.png", "C": 0.2}},
                ]
            },
        }
    )
    transport = LarkCliSheetsTransport(command_runner=runner, read_range="A1:C200")

    values = transport.read_values("spreadsheet-1", "sheet-1")

    assert values == [
        ["case_id", "image_uri", "avg_score"],
        ["case-1", "file://case-1.png", 0.2],
    ]
    assert runner.calls == [
        (
            [
                "lark-cli",
                "sheets",
                "+csv-get",
                "--spreadsheet-token",
                "spreadsheet-1",
                "--sheet-id",
                "sheet-1",
                "--range",
                "A1:C200",
                "--rows-json",
            ],
            None,
        )
    ]


def test_lark_cli_transport_records_read_timing() -> None:
    runner = RecordingCommandRunner({"ok": True, "data": {"rows": []}})
    transport = LarkCliSheetsTransport(command_runner=runner, read_range="A1:C200")
    performance_recorder.clear()
    try:
        assert transport.read_values("spreadsheet-1", "sheet-1") == []

        events = performance_recorder.events(component="lark_cli")
        assert len(events) == 1
        assert events[0].operation == "+csv-get"
        assert events[0].status == "succeeded"
        assert events[0].metadata["context"] == "+csv-get --spreadsheet-token spreadsheet-1 --sheet-id sheet-1 --range A1:C200"
    finally:
        performance_recorder.clear()


def test_lark_cli_transport_writes_fields_to_header_columns() -> None:
    runner = RecordingCommandRunner(
        [
            {
                "ok": True,
                "data": {
                    "rows": [
                        {
                            "row_number": 1,
                            "values": {
                                "A": "case_id",
                                "B": "错误原因",
                                "C": "评估问题反馈",
                                "D": "分析报告链接",
                            },
                        }
                    ]
                },
            },
            {"ok": True, "data": {}},
            {"ok": True, "data": {}},
        ]
    )
    transport = LarkCliSheetsTransport(command_runner=runner, read_range="A1:D200")

    written_fields = transport.update_row(
        spreadsheet_id="spreadsheet-1",
        sheet_id="sheet-1",
        row_id="7",
        fields={"错误原因": "模型无法稳定识别。", "分析报告链接": "http://localhost/reports/job-1"},
    )

    assert written_fields == {"错误原因": "模型无法稳定识别。", "分析报告链接": "http://localhost/reports/job-1"}
    assert runner.calls == [
        (
            [
                "lark-cli",
                "sheets",
                "+csv-get",
                "--spreadsheet-token",
                "spreadsheet-1",
                "--sheet-id",
                "sheet-1",
                "--range",
                "A1:D200",
                "--rows-json",
            ],
            None,
        ),
        (
            [
                "lark-cli",
                "sheets",
                "+cells-set",
                "--spreadsheet-token",
                "spreadsheet-1",
                "--sheet-id",
                "sheet-1",
                "--range",
                "B7",
                "--cells",
                "-",
            ],
            json.dumps([[{"value": "模型无法稳定识别。"}]], ensure_ascii=False),
        ),
        (
            [
                "lark-cli",
                "sheets",
                "+cells-set",
                "--spreadsheet-token",
                "spreadsheet-1",
                "--sheet-id",
                "sheet-1",
                "--range",
                "D7",
                "--cells",
                "-",
            ],
            json.dumps([[{"value": "http://localhost/reports/job-1"}]], ensure_ascii=False),
        ),
    ]


def test_lark_cli_transport_reuses_header_cache_for_repeated_writebacks() -> None:
    runner = RecordingCommandRunner(
        [
            {
                "ok": True,
                "data": {
                    "rows": [
                        {
                            "row_number": 1,
                            "values": {
                                "A": "case_id",
                                "B": "错误原因",
                            },
                        }
                    ]
                },
            },
            {"ok": True, "data": {}},
            {"ok": True, "data": {}},
        ]
    )
    transport = LarkCliSheetsTransport(command_runner=runner, read_range="A1:B200")

    transport.update_row(
        spreadsheet_id="spreadsheet-1",
        sheet_id="sheet-1",
        row_id="2",
        fields={"错误原因": "第一次写回"},
    )
    transport.update_row(
        spreadsheet_id="spreadsheet-1",
        sheet_id="sheet-1",
        row_id="3",
        fields={"错误原因": "第二次写回"},
    )

    assert [call[0][2] for call in runner.calls] == ["+csv-get", "+cells-set", "+cells-set"]
    assert runner.calls[1][0][8] == "B2"
    assert runner.calls[2][0][8] == "B3"


def test_lark_cli_transport_matches_header_prefix_before_newline() -> None:
    runner = RecordingCommandRunner(
        [
            {
                "ok": True,
                "data": {
                    "rows": [
                        {
                            "row_number": 1,
                            "values": {
                                "R": "评估问题反馈\n（务必再三确认）",
                            },
                        }
                    ]
                },
            },
            {"ok": True, "data": {}},
        ]
    )
    transport = LarkCliSheetsTransport(command_runner=runner, read_range="A1:AC200")

    transport.update_row(
        spreadsheet_id="spreadsheet-1",
        sheet_id="sheet-1",
        row_id="2",
        fields={"评估问题反馈": "自动闭环完成。"},
    )

    assert runner.calls[1][0][8] == "R2"


def test_lark_cli_transport_skips_fields_missing_from_sheet_headers() -> None:
    runner = RecordingCommandRunner(
        [
            {
                "ok": True,
                "data": {
                    "rows": [
                        {
                            "row_number": 1,
                            "values": {
                                "A": "case_id",
                                "B": "错误原因",
                                "C": "评估问题反馈\n（务必再三确认）",
                            },
                        }
                    ]
                },
            },
            {"ok": True, "data": {}},
            {"ok": True, "data": {}},
        ]
    )
    transport = LarkCliSheetsTransport(command_runner=runner, read_range="A1:AC200")

    performance_recorder.clear()
    try:
        written_fields = transport.update_row(
            spreadsheet_id="spreadsheet-1",
            sheet_id="sheet-1",
            row_id="3",
            fields={
                "错误原因": "模型无法稳定识别。",
                "影响目标": "generic_json:root",
                "评估问题反馈": "自动闭环完成。",
            },
        )

        assert written_fields == {
            "错误原因": "模型无法稳定识别。",
            "评估问题反馈": "自动闭环完成。",
        }
        assert [call[0][8] for call in runner.calls[1:]] == ["B3", "C3"]

        resolution_events = performance_recorder.events(component="lark_writeback", operation="resolve_fields")
        assert resolution_events[-1].metadata["written_count"] == 2
        assert resolution_events[-1].metadata["missing_count"] == 1
    finally:
        performance_recorder.clear()


def test_lark_cli_transport_raises_when_all_writeback_headers_are_missing() -> None:
    runner = RecordingCommandRunner(
        {
            "ok": True,
            "data": {
                "rows": [
                    {"row_number": 1, "values": {"A": "case_id", "B": "错误原因"}}
                ]
            },
        }
    )
    transport = LarkCliSheetsTransport(command_runner=runner, read_range="A1:B200")

    with pytest.raises(LarkCliError, match="Spreadsheet headers not found for any writeback fields"):
        transport.update_row(
            spreadsheet_id="spreadsheet-1",
            sheet_id="sheet-1",
            row_id="3",
            fields={"影响目标": "generic_json:root"},
        )

    assert len(runner.calls) == 1


def test_lark_cli_transport_uses_first_non_empty_row_for_writeback_headers() -> None:
    runner = RecordingCommandRunner(
        [
            {
                "ok": True,
                "data": {
                    "rows": [
                        {"row_number": 1, "values": {"A": "", "B": ""}},
                        {"row_number": 2, "values": {"A": "", "B": ""}},
                        {"row_number": 3, "values": {"A": "case_id", "B": "错误原因"}},
                    ]
                },
            },
            {"ok": True, "data": {}},
        ]
    )
    transport = LarkCliSheetsTransport(command_runner=runner, read_range="A1:B200")

    transport.update_row(
        spreadsheet_id="spreadsheet-1",
        sheet_id="sheet-1",
        row_id="8",
        fields={"错误原因": "模型无法稳定识别。"},
    )

    assert runner.calls[1] == (
        [
            "lark-cli",
            "sheets",
            "+cells-set",
            "--spreadsheet-token",
            "spreadsheet-1",
            "--sheet-id",
            "sheet-1",
            "--range",
            "B8",
            "--cells",
            "-",
        ],
        json.dumps([[{"value": "模型无法稳定识别。"}]], ensure_ascii=False),
    )


def test_lark_cli_transport_subprocess_runner_uses_timeout(monkeypatch) -> None:
    captured_timeout = 0

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        nonlocal captured_timeout
        captured_timeout = int(kwargs["timeout"])
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "data": {
                        "rows": [
                            {"row_number": 1, "values": {"A": "case_id"}},
                            {"row_number": 2, "values": {"A": "case-1"}},
                        ]
                    },
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    transport = LarkCliSheetsTransport()

    assert transport.read_values("spreadsheet-1", "sheet-1") == [["case_id"], ["case-1"]]
    assert captured_timeout == 60


def test_lark_cli_transport_uses_configured_timeout(monkeypatch) -> None:
    captured_timeout = 0

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        nonlocal captured_timeout
        captured_timeout = int(kwargs["timeout"])
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=json.dumps({"ok": True, "data": {"rows": []}}),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    transport = LarkCliSheetsTransport(timeout_seconds=7)

    assert transport.read_values("spreadsheet-1", "sheet-1") == []
    assert captured_timeout == 7


def test_lark_cli_transport_resolves_windows_cmd_shim(monkeypatch) -> None:
    captured_command = ""

    def fake_which(command: str) -> str | None:
        if command == "lark-cli.cmd":
            return "C:/Users/Admin/AppData/Roaming/npm/lark-cli.cmd"
        return None

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        nonlocal captured_command
        captured_command = str(args[0][0])
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=json.dumps({"ok": True, "data": {"rows": []}}), stderr="")

    monkeypatch.setattr("debug_agent.lark.connector.shutil.which", fake_which)
    monkeypatch.setattr(subprocess, "run", fake_run)
    transport = LarkCliSheetsTransport()

    assert transport.read_values("spreadsheet-1", "sheet-1") == []
    assert captured_command.endswith("lark-cli.cmd")


def test_lark_cli_transport_maps_subprocess_timeout(monkeypatch) -> None:
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd=args, timeout=kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", fake_run)
    transport = LarkCliSheetsTransport()

    with pytest.raises(LarkCliError, match="timed out after 60 seconds"):
        transport.read_values("spreadsheet-1", "sheet-1")


def test_lark_cli_transport_maps_missing_executable(monkeypatch) -> None:
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("lark-cli")

    monkeypatch.setattr("debug_agent.lark.connector.shutil.which", lambda _command: None)
    monkeypatch.setattr(subprocess, "run", fake_run)
    transport = LarkCliSheetsTransport()

    with pytest.raises(LarkCliError, match="lark-cli executable was not found"):
        transport.read_values("spreadsheet-1", "sheet-1")


def test_lark_cli_transport_nonzero_error_includes_safe_command_context(monkeypatch) -> None:
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="permission denied")

    monkeypatch.setattr(subprocess, "run", fake_run)
    transport = LarkCliSheetsTransport()

    with pytest.raises(LarkCliError) as exc_info:
        transport.read_values("spreadsheet-1", "sheet-1")

    message = str(exc_info.value)
    assert "+csv-get" in message
    assert "--spreadsheet-token spreadsheet-1" in message
    assert "--sheet-id sheet-1" in message
    assert "--range A1:Z500" in message
    assert "permission denied" in message


def test_lark_cli_transport_write_error_excludes_stdin_payload(monkeypatch) -> None:
    responses = [
        subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "data": {
                        "rows": [
                            {"row_number": 1, "values": {"A": "case_id", "B": "错误原因"}}
                        ]
                    },
                }
            ),
            stderr="",
        ),
        subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="write failed"),
    ]

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return responses.pop(0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    transport = LarkCliSheetsTransport()

    with pytest.raises(LarkCliError) as exc_info:
        transport.update_row(
            spreadsheet_id="spreadsheet-1",
            sheet_id="sheet-1",
            row_id="7",
            fields={"错误原因": "sensitive report detail"},
        )

    message = str(exc_info.value)
    assert "+cells-set" in message
    assert "--range B7" in message
    assert "write failed" in message
    assert "sensitive report detail" not in message
