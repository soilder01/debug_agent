import json

from debug_agent.spreadsheets.lark import LarkCliSheetsTransport


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

    transport.update_row(
        spreadsheet_id="spreadsheet-1",
        sheet_id="sheet-1",
        row_id="7",
        fields={"错误原因": "模型无法稳定识别。", "分析报告链接": "http://localhost/reports/job-1"},
    )

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
