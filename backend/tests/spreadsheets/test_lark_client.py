from debug_agent.spreadsheets.lark import LarkSpreadsheetClient


class RecordingLarkSheetsTransport:
    def __init__(self, values: list[list[object]]) -> None:
        self.values = values
        self.read_spreadsheet_id = ""
        self.read_sheet_id = ""
        self.updated_rows: list[tuple[str, str, str, dict[str, str]]] = []

    def read_values(self, spreadsheet_id: str, sheet_id: str) -> list[list[object]]:
        self.read_spreadsheet_id = spreadsheet_id
        self.read_sheet_id = sheet_id
        return self.values

    def update_row(self, spreadsheet_id: str, sheet_id: str, row_id: str, fields: dict[str, str]) -> None:
        self.updated_rows.append((spreadsheet_id, sheet_id, row_id, fields))


class RowsJsonLarkSheetsTransport(RecordingLarkSheetsTransport):
    def __init__(self, rows_json: dict[str, object]) -> None:
        super().__init__([])
        self.rows_json = rows_json

    def read_rows_json(self, spreadsheet_id: str, sheet_id: str) -> dict[str, object]:
        self.read_spreadsheet_id = spreadsheet_id
        self.read_sheet_id = sheet_id
        return self.rows_json


def test_lark_spreadsheet_client_converts_header_values_to_source_rows() -> None:
    transport = RecordingLarkSheetsTransport(
        [
            ["case_id", "image_uri", "avg_score"],
            ["case-1", "file://case-1.png", 0.2],
            ["case-2", "file://case-2.png", 1.0],
        ]
    )
    client = LarkSpreadsheetClient(transport)

    rows = client.list_rows("spreadsheet-1", "sheet-1")

    assert transport.read_spreadsheet_id == "spreadsheet-1"
    assert transport.read_sheet_id == "sheet-1"
    assert len(rows) == 2
    assert rows[0].row_id == "2"
    assert rows[0].values == {"case_id": "case-1", "image_uri": "file://case-1.png", "avg_score": 0.2}
    assert rows[1].row_id == "3"
    assert rows[1].values["case_id"] == "case-2"


def test_lark_spreadsheet_client_skips_empty_rows() -> None:
    transport = RecordingLarkSheetsTransport(
        [
            ["case_id", "image_uri"],
            ["", ""],
            ["case-1", "file://case-1.png"],
        ]
    )
    client = LarkSpreadsheetClient(transport)

    rows = client.list_rows("spreadsheet-1", "sheet-1")

    assert [row.row_id for row in rows] == ["3"]
    assert rows[0].values["case_id"] == "case-1"


def test_lark_spreadsheet_client_preserves_source_columns_from_rows_json() -> None:
    transport = RowsJsonLarkSheetsTransport(
        {
            "rows": [
                {"row_number": 1, "values": {"A": "id", "J": "video"}},
                {"row_number": 2, "values": {"A": "JSZN-131", "J": "JSZN-131.mp4"}},
            ]
        }
    )
    client = LarkSpreadsheetClient(transport)

    rows = client.list_rows("spreadsheet-1", "sheet-1")

    assert transport.read_spreadsheet_id == "spreadsheet-1"
    assert rows[0].row_id == "2"
    assert rows[0].values["id"] == "JSZN-131"
    assert rows[0].values["video"] == "JSZN-131.mp4"
    assert rows[0].values["__field_columns"] == {"id": "A", "video": "J"}


def test_lark_spreadsheet_client_uses_first_non_empty_row_as_header() -> None:
    transport = RecordingLarkSheetsTransport(
        [
            ["", "", ""],
            ["", "", ""],
            ["case_id", "image_uri", "avg_score"],
            ["case-1", "file://case-1.png", 0.2],
        ]
    )
    client = LarkSpreadsheetClient(transport)

    rows = client.list_rows("spreadsheet-1", "sheet-1")

    assert len(rows) == 1
    assert rows[0].row_id == "4"
    assert rows[0].values == {"case_id": "case-1", "image_uri": "file://case-1.png", "avg_score": 0.2}


def test_lark_spreadsheet_client_forwards_writeback_fields() -> None:
    transport = RecordingLarkSheetsTransport([["case_id"], ["case-1"]])
    client = LarkSpreadsheetClient(transport)

    client.update_row(
        spreadsheet_id="spreadsheet-1",
        sheet_id="sheet-1",
        row_id="2",
        fields={"错误原因": "模型无法稳定识别。"},
    )

    assert transport.updated_rows == [
        ("spreadsheet-1", "sheet-1", "2", {"错误原因": "模型无法稳定识别。"})
    ]
