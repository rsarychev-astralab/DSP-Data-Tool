from io import BytesIO

import openpyxl

HEADERS = [
    "ERID", "Номер изначального договора", "Дата изначального договора",
    "Тип договора", "Предмет договора", "Вид деятельности",
    "Тип заказчика", "Заказчик", "ИНН заказчика или его аналог",
    "Рег.номер заказчика", "ОКСМ заказчика", "Тип исполнителя", "Исполнитель",
    "ИНН исполнителя или его аналог", "Рег.номер исполнителя", "ОКСМ исполнителя",
    "Включая НДС", "Показы", "Сумма",
]

CONTRACT_TYPES = {
    "intermediary", "посреднический", "посредническийдоговор",
    "additional", "дополнительноесоглашение", "допсоглашение",
    "original", "оказаниеуслуг", "оказанияуслуг", "договороказанияуслуг",
}
SUBJECT_TYPES = {
    "representation", "представительство", "distribution",
    "договорнараспространениерекламы", "distributionorganization",
    "договорнаорганизациюраспространениярекламы", "mediation", "посредничество",
    "other", "иное", "другое",
}
ACTIVITY_TYPES = {
    "conclude", "заключениедоговоров", "distribution",
    "действиявцеляхраспространениярекламы", "commercial",
    "коммерческоепредставительство", "other", "иное", "другое", "none", "нет",
}
PARTY_TYPES = {
    "legalperson", "individualentrepreneur", "physicalperson",
    "foreignphysicalperson", "foreignlegalperson", "юрлицо", "юридическоелицо",
    "ип", "физлицо", "иностранноефизлицо", "иностранноеюрлицо",
}
FOREIGN_TYPES = {"foreignphysicalperson", "foreignlegalperson", "иностранноефизлицо", "иностранноеюрлицо"}
RU_TYPES = {"legalperson", "individualentrepreneur", "physicalperson", "юрлицо", "юридическоелицо", "ип", "физлицо"}
VAT_VALUES = {"yes", "no"}


def norm(val):
    return "" if val is None else str(val).strip()


def norm_key(val):
    return norm(val).lower().replace(" ", "").replace(".", "")


def is_empty(val):
    return norm(val) == ""


def validate_row(row_num, values):
    errors = []
    v = [norm(x) for x in values[:19]]
    while len(v) < 19:
        v.append("")
    required = [0, 1, 2, 3, 4, 5, 6, 7, 11, 12, 16, 17, 18]
    for idx in required:
        if is_empty(v[idx]):
            errors.append(f"Строка {row_num}: обязательное поле «{HEADERS[idx]}»")
    return errors


def validate_workbook_bytes(data: bytes) -> list[str]:
    wb = openpyxl.load_workbook(BytesIO(data), data_only=True)
    ws = wb.active
    all_errors = []
    data_rows = 0
    for row_num in range(3, ws.max_row + 1):
        values = [ws.cell(row_num, c).value for c in range(1, 20)]
        if all(is_empty(x) for x in values):
            continue
        data_rows += 1
        all_errors.extend(validate_row(row_num, values))
    if data_rows == 0:
        all_errors.append("Нет строк данных")
    wb.close()
    return all_errors
