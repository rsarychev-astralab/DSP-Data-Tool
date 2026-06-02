from datetime import datetime
from io import BytesIO
from pathlib import Path

import openpyxl
import pytest

from app.matching.keys import build_match_key
from app.matching.match import OUTPUT_HEADERS, match_workbook_bytes


def _minimal_upload_bytes(**fields) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    for col, h in enumerate(
        [
            "ERID", "Номер изначального договора", "Дата изначального договора",
            "Тип договора", "Предмет договора", "Вид деятельности",
            "Тип заказчика", "Заказчик", "ИНН заказчика или его аналог",
            "Рег.номер заказчика", "ОКСМ заказчика", "Тип исполнителя", "Исполнитель",
            "ИНН исполнителя или его аналог", "Рег.номер исполнителя", "ОКСМ исполнителя",
            "Включая НДС", "Показы", "Сумма",
        ],
        1,
    ):
        ws.cell(1, col, h)
    row = [""] * 19
    row[0] = fields.get("erid", "erid-1")
    row[1] = fields.get("contract_no", "dog-1")
    row[2] = fields.get("contract_date", "2025-01-01")
    row[3] = fields.get("contract_type", "Original")
    row[4] = fields.get("contract_subject", "Distribution")
    row[5] = fields.get("activity_type", "")
    row[7] = fields.get("customer_name", "Customer")
    row[12] = fields.get("contractor_name", "Contractor")
    for col, val in enumerate(row, 1):
        if val != "":
            ws.cell(3, col, val)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _minimal_db_bytes() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "OriginalContract"
    headers = [
        "Номер", "Дата", "Ответственный", "Исполнитель (Агент)", "Заказчик (Принципал)",
        "Тип договора", "Сведения о предмете договора", "Тип посреднического договора",
        "Цена", "Включая НДС", "AdX", "Неактуален", "ID в OTM", "ID в OZON", "ID в VK",
    ]
    for col, h in enumerate(headers, 1):
        ws.cell(1, col, h)
    ws.append([
        "DOG-42", datetime(2025, 1, 1), "resp",
        "ООО «Исполнитель» ИНН: 7700000001",
        "ООО «Заказчик» ИНН: 7700000002",
        "Оказание услуг", "Распространение рекламы", "NA",
        100, "Нет", "Нет", "Нет", 999, 1001, 1002,
    ])
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_match_requires_contract_attrs(monkeypatch):
    monkeypatch.setattr("app.matching.match.resolve_contract_attrs_path", lambda: None)
    data = _minimal_upload_bytes()
    with pytest.raises(FileNotFoundError, match="атрибутов договоров"):
        match_workbook_bytes(data)


def test_match_finds_contract_and_outputs_ids(tmp_path, monkeypatch):
    db_path = tmp_path / "База договоров.xlsx"
    db_path.write_bytes(_minimal_db_bytes())
    monkeypatch.setattr("app.matching.match.resolve_contract_attrs_path", lambda: db_path)

    upload = _minimal_upload_bytes(
        contract_no="DOG-42",
        contract_date="2025-01-01",
        contract_type="Original",
        contract_subject="Distribution",
        activity_type="None",
        customer_name="ООО «Заказчик»",
        contractor_name="ООО «Исполнитель»",
    )
    result = match_workbook_bytes(upload, original_filename="out.xlsx")
    assert result.rows_total == 1
    assert result.rows_matched == 1
    assert result.rows_unmatched == 0

    out = openpyxl.load_workbook(BytesIO(result.output_bytes), data_only=True)
    ws = out.active
    assert [ws.cell(1, c).value for c in range(1, 5)] == OUTPUT_HEADERS
    assert ws.cell(3, 1).value == "erid-1"
    assert ws.cell(3, 2).value == "999"
    assert ws.cell(3, 3).value == "1001"
    assert ws.cell(3, 4).value == "1002"
    out.close()


def test_match_unmatched_row(tmp_path, monkeypatch):
    db_path = tmp_path / "База договоров.xlsx"
    db_path.write_bytes(_minimal_db_bytes())
    monkeypatch.setattr("app.matching.match.resolve_contract_attrs_path", lambda: db_path)

    upload = _minimal_upload_bytes(contract_no="UNKNOWN-999")
    result = match_workbook_bytes(upload)
    assert result.rows_matched == 0
    assert result.rows_unmatched == 1


def test_match_real_database_sample_row():
    db = Path("Справка/База договоров.xlsx")
    if not db.exists():
        pytest.skip("no contract database")
    upload = _minimal_upload_bytes(
        erid="test-erid",
        contract_no="TEST - 1991",
        contract_date="2022-08-03",
        contract_type="Original",
        contract_subject="Distribution",
        activity_type="None",
        customer_name='Акционерное общество "Вимм-Билль-Данн"',
        contractor_name="ООО «Нью Ченнел Плюс»",
    )
    result = match_workbook_bytes(upload)
    assert result.rows_matched == 1, f"unmatched={result.rows_unmatched}"
    out = openpyxl.load_workbook(BytesIO(result.output_bytes), data_only=True)
    assert out.active.cell(3, 2).value == "317"
    out.close()


def test_build_match_key_db_upload_symmetry():
    db_key = build_match_key(
        contract_no="TEST - 1991",
        contract_date=datetime(2022, 8, 3),
        customer_name='Акционерное общество "Вимм-Билль-Данн" ИНН: 7713085659',
        contractor_name="ООО «Нью Ченнел Плюс» ИНН: 7702848355",
        contract_type="Оказание услуг",
        contract_subject="Распространение рекламы",
        intermediary_type="NA",
        from_db=True,
    )
    up_key = build_match_key(
        contract_no="TEST - 1991",
        contract_date="2022-08-03",
        customer_name='Акционерное общество "Вимм-Билль-Данн"',
        contractor_name="ООО «Нью Ченнел Плюс»",
        contract_type="Original",
        contract_subject="Distribution",
        intermediary_type="None",
        from_db=False,
    )
    assert db_key == up_key
