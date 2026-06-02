from io import BytesIO

import openpyxl

from app.engine.template import (
    AMOUNT_NUMBER_FORMAT,
    IMPRESSIONS_NUMBER_FORMAT,
    TEXT_NUMBER_FORMAT,
    create_output_workbook,
    write_cell,
    write_records,
)


def test_write_cell_text_format_for_inn():
    wb, ws = create_output_workbook([""] * 19, [""] * 19)
    write_cell(ws, 3, 9, "customer_inn", "7700123456789")
    cell = ws.cell(3, 9)
    assert cell.number_format == TEXT_NUMBER_FORMAT
    assert cell.value == "7700123456789"
    assert isinstance(cell.value, str)


def test_write_cell_numeric_format_for_impressions_and_amount():
    wb, ws = create_output_workbook([""] * 19, [""] * 19)
    write_cell(ws, 3, 18, "impressions", 1200)
    write_cell(ws, 3, 19, "amount", 1500.5)
    assert ws.cell(3, 18).number_format == IMPRESSIONS_NUMBER_FORMAT
    assert ws.cell(3, 18).value == 1200
    assert ws.cell(3, 19).number_format == AMOUNT_NUMBER_FORMAT
    assert ws.cell(3, 19).value == 1500.5


def test_write_records_mixed_formats():
    wb, ws = create_output_workbook([""] * 19, [""] * 19)
    write_records(ws, [{
        "erid": "abc",
        "contract_no": "001",
        "impressions": 10,
        "amount": 99.9,
    }])
    assert ws.cell(3, 1).number_format == TEXT_NUMBER_FORMAT
    assert ws.cell(3, 2).number_format == TEXT_NUMBER_FORMAT
    assert ws.cell(3, 18).number_format == IMPRESSIONS_NUMBER_FORMAT
    assert ws.cell(3, 19).number_format == AMOUNT_NUMBER_FORMAT


def test_output_workbook_bytes_preserve_text_format():
    from app.engine.template import workbook_to_bytes

    wb, ws = create_output_workbook([""] * 19, [""] * 19)
    write_cell(ws, 3, 1, "erid", "Lq7abc123")
    write_cell(ws, 3, 18, "impressions", 5)
    data = workbook_to_bytes(wb)
    out = openpyxl.load_workbook(BytesIO(data), data_only=False)
    cell = out.active.cell(3, 1)
    assert cell.number_format == TEXT_NUMBER_FORMAT
    assert out.active.cell(3, 18).number_format == IMPRESSIONS_NUMBER_FORMAT
    out.close()
