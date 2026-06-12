import pytest

from debug_agent.spreadsheets.lark import LarkSpreadsheetReference, parse_lark_spreadsheet_reference


def test_parse_lark_spreadsheet_reference_from_sheet_url() -> None:
    reference = parse_lark_spreadsheet_reference(
        "https://bytedance.larkoffice.com/sheets/N935sK3fzhGDiNtwT3LcRLDTnvb?sheet=wAKHdf"
    )

    assert reference == LarkSpreadsheetReference(
        spreadsheet_id="N935sK3fzhGDiNtwT3LcRLDTnvb",
        sheet_id="wAKHdf",
    )


def test_parse_lark_spreadsheet_reference_from_token_and_sheet_id() -> None:
    reference = parse_lark_spreadsheet_reference("N935sK3fzhGDiNtwT3LcRLDTnvb", sheet_id="wAKHdf")

    assert reference.spreadsheet_id == "N935sK3fzhGDiNtwT3LcRLDTnvb"
    assert reference.sheet_id == "wAKHdf"


def test_parse_lark_spreadsheet_reference_rejects_url_without_sheet_id() -> None:
    with pytest.raises(ValueError, match="sheet_id"):
        parse_lark_spreadsheet_reference("https://bytedance.larkoffice.com/sheets/N935sK3fzhGDiNtwT3LcRLDTnvb")


def test_parse_lark_spreadsheet_reference_rejects_non_sheet_url() -> None:
    with pytest.raises(ValueError, match="/sheets/"):
        parse_lark_spreadsheet_reference("https://bytedance.larkoffice.com/docx/ExampleToken?sheet=wAKHdf")
