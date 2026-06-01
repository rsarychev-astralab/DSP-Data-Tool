from io import BytesIO
from pathlib import Path

import openpyxl

from app.engine.lookups import TEMPLATE_COLUMNS
from app.engine.normalize import has_value


def load_template_headers(template_path: Path):
    tpl_wb = openpyxl.load_workbook(template_path, read_only=True, data_only=True)
    tpl_ws = tpl_wb["Sheet1"]
    headers = [tpl_ws.cell(1, c).value for c in range(1, 20)]
    descriptions = [tpl_ws.cell(2, c).value for c in range(1, 20)]
    tpl_wb.close()
    return headers, descriptions


def create_output_workbook(headers, descriptions):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    for col, value in enumerate(headers, 1):
        if has_value(value):
            ws.cell(1, col, value)
    for col, value in enumerate(descriptions, 1):
        if has_value(value):
            ws.cell(2, col, value)
    return wb, ws


def write_cell(ws, row, col, value):
    if has_value(value):
        ws.cell(row, col, value)


def write_records(ws, records, start_row=3):
    for i, record in enumerate(records):
        out_row = start_row + i
        for key, col in TEMPLATE_COLUMNS.items():
            write_cell(ws, out_row, col, record.get(key))


def workbook_to_bytes(wb) -> bytes:
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()
