from io import BytesIO

import openpyxl

from app.validation.remarks import build_remarks_filename, build_validation_remarks_bytes
from app.validation.validate import ValidationResult


def test_build_remarks_filename():
    assert build_remarks_filename("genius_desk_apr_2026.xlsx") == (
        "genius_desk_apr_2026_log.xlsx"
    )


def test_build_validation_remarks_bytes_contains_all_errors():
    validation = ValidationResult(
        errors=[
            "Строка 8: поле «Вид деятельности» пустое",
            "Строка 9: поле «Вид деятельности» пустое",
            "Нет строк данных",
        ],
        row_numbers=[8, 9],
    )
    data = build_validation_remarks_bytes(
        validation,
        partner_name="Genius Desk",
        source_filename="source.xlsx",
    )
    wb = openpyxl.load_workbook(BytesIO(data), read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    assert rows[0] == ("DSP", "Genius Desk")
    assert rows[1] == ("Исходный файл", "source.xlsx")
    assert rows[2] == ("Всего замечаний", 3)
    assert rows[3] == ("Строка Excel", "Замечание")
    assert rows[4] == (8, "поле «Вид деятельности» пустое")
    assert rows[5] == (9, "поле «Вид деятельности» пустое")
    assert rows[6][0] is None or rows[6][0] == ""
    assert "Нет строк данных" in str(rows[6][1])
