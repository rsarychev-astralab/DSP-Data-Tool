from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

import openpyxl

from app.engine.lookups import (
    ACTIVITY_TYPE,
    CONTRACT_TYPE,
    PARTY_TYPE,
    SUBJECT_TYPE,
)

if TYPE_CHECKING:
    from app.profiles.loader import PartnerProfile

HEADERS = [
    "ERID", "Номер изначального договора", "Дата изначального договора",
    "Тип договора", "Предмет договора", "Вид деятельности",
    "Тип заказчика", "Заказчик", "ИНН заказчика или его аналог",
    "Рег.номер заказчика", "ОКСМ заказчика", "Тип исполнителя", "Исполнитель",
    "ИНН исполнителя или его аналог", "Рег.номер исполнителя", "ОКСМ исполнителя",
    "Включая НДС", "Показы", "Сумма",
]

OUTPUT_FIELDS = [
    "erid", "contract_no", "contract_date", "contract_type", "contract_subject",
    "activity_type", "customer_type", "customer_name", "customer_inn",
    "customer_reg_no", "customer_oksm", "contractor_type", "contractor_name",
    "contractor_inn", "contractor_reg_no", "contractor_oksm",
    "vat_included", "impressions", "amount",
]

DEFAULT_REQUIRED_INDICES = {0, 1, 2, 3, 4, 5, 6, 7, 11, 12, 16, 17, 18}

ALLOWED_CONTRACT = set(CONTRACT_TYPE.values())
ALLOWED_SUBJECT = set(SUBJECT_TYPE.values())
ALLOWED_ACTIVITY = set(ACTIVITY_TYPE.values())
ALLOWED_PARTY = set(PARTY_TYPE.values())
ALLOWED_VAT = {"yes", "no"}

ENUM_CHECKS: dict[int, tuple[set[str], str]] = {
    3: (ALLOWED_CONTRACT, HEADERS[3]),
    4: (ALLOWED_SUBJECT, HEADERS[4]),
    5: (ALLOWED_ACTIVITY, HEADERS[5]),
    6: (ALLOWED_PARTY, HEADERS[6]),
    11: (ALLOWED_PARTY, HEADERS[11]),
    16: (ALLOWED_VAT, HEADERS[16]),
}


def norm(val):
    return "" if val is None else str(val).strip()


def is_empty(val):
    return norm(val) == ""


def required_field_indices(profile: PartnerProfile | None) -> set[int]:
    if profile is None:
        return set(DEFAULT_REQUIRED_INDICES)
    provided = set(profile.column_map) | set(profile.constants)
    optional = profile.optional_output_fields
    return {
        i
        for i, name in enumerate(OUTPUT_FIELDS)
        if name in provided and name not in optional
    }


def _check_enum(row_num: int, idx: int, value: str, allowed: set[str], label: str, errors: list[str]):
    if is_empty(value):
        return
    if value not in allowed:
        errors.append(
            f"Строка {row_num}: поле «{label}» — недопустимое значение «{value}»"
        )


def validate_row(row_num, values, required_indices: set[int]):
    errors = []
    v = [norm(x) for x in values[:19]]
    while len(v) < 19:
        v.append("")

    for idx in sorted(required_indices):
        if is_empty(v[idx]):
            errors.append(f"Строка {row_num}: обязательное поле «{HEADERS[idx]}»")

    for idx, (allowed, label) in ENUM_CHECKS.items():
        if not is_empty(v[idx]):
            _check_enum(row_num, idx, v[idx], allowed, label, errors)

    return errors


def validate_workbook_bytes(data: bytes, profile: PartnerProfile | None = None) -> list[str]:
    required_indices = required_field_indices(profile)
    wb = openpyxl.load_workbook(BytesIO(data), read_only=True, data_only=True)
    ws = wb.active
    all_errors = []
    data_rows = 0
    for row_num, row in enumerate(
        ws.iter_rows(min_row=3, max_col=19, values_only=True),
        start=3,
    ):
        values = list(row) if row else []
        if all(is_empty(x) for x in values):
            continue
        data_rows += 1
        all_errors.extend(validate_row(row_num, values, required_indices))
    if data_rows == 0:
        all_errors.append("Нет строк данных")
    wb.close()
    return all_errors
