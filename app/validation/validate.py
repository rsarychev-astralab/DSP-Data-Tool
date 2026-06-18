from __future__ import annotations

import re
from dataclasses import dataclass
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

# Индекс колонки → ключ поля в record / column_map
COL_FIELD = [
    "erid", "contract_no", "contract_date", "contract_type", "contract_subject",
    "activity_type", "customer_type", "customer_name", "customer_inn",
    "customer_reg_no", "customer_oksm", "contractor_type", "contractor_name",
    "contractor_inn", "contractor_reg_no", "contractor_oksm",
    "vat_included", "impressions", "amount",
]

CORE_REQUIRED = {
    "erid", "contract_no", "contract_date", "contract_type", "contract_subject",
    "activity_type", "customer_type", "customer_name",
    "contractor_type", "contractor_name",
}

ALLOWED_CONTRACT = set(CONTRACT_TYPE.values())
ALLOWED_SUBJECT = set(SUBJECT_TYPE.values())
ALLOWED_ACTIVITY = set(ACTIVITY_TYPE.values())
ALLOWED_PARTY = set(PARTY_TYPE.values())
ALLOWED_VAT = {"yes", "no"}

ENUM_BY_FIELD: dict[str, set[str]] = {
    "contract_type": ALLOWED_CONTRACT,
    "contract_subject": ALLOWED_SUBJECT,
    "activity_type": ALLOWED_ACTIVITY,
    "customer_type": ALLOWED_PARTY,
    "contractor_type": ALLOWED_PARTY,
    "vat_included": ALLOWED_VAT,
}

RU_PARTY = frozenset(
    {"legalperson", "individualentrepreneur", "physicalperson"}
)
FOREIGN_PARTY = frozenset(
    {"foreignphysicalperson", "foreignlegalperson"}
)


@dataclass(frozen=True)
class ValidationResult:
    errors: list[str]
    row_numbers: list[int]


def norm(val):
    return "" if val is None else str(val).strip()


def norm_key(val):
    return re.sub(r"[\s\.\-_«»\"']", "", norm(val).lower())


def is_empty(val):
    return norm(val) == ""


def _profile_fields(profile: PartnerProfile | None) -> set[str]:
    if profile is None:
        return set(COL_FIELD)
    return set(profile.column_map) | set(profile.constants)


def _optional_fields(profile: PartnerProfile | None) -> set[str]:
    if profile is None:
        return set()
    return set(profile.optional_output_fields)


def _field_active(profile: PartnerProfile | None, field: str) -> bool:
    return field in _profile_fields(profile)


def _field_label(field: str) -> str:
    return HEADERS[COL_FIELD.index(field)]


def _empty_field_error(row_num: int, field: str) -> str:
    return f"Строка {row_num}: поле «{_field_label(field)}» пустое"


def _is_required_scalar(profile: PartnerProfile | None, field: str) -> bool:
    if not _field_active(profile, field):
        return False
    if field in _optional_fields(profile):
        return False
    if field in CORE_REQUIRED:
        return True
    return field in {"amount", "impressions", "vat_included"}


def _check_enum(row_num: int, field: str, value: str, errors: list[str]):
    allowed = ENUM_BY_FIELD.get(field)
    if not allowed or is_empty(value):
        return
    if value not in allowed:
        idx = COL_FIELD.index(field)
        errors.append(
            f"Строка {row_num}: поле «{HEADERS[idx]}» — недопустимое значение «{value}»"
        )


def _check_number(row_num: int, field: str, value: str, errors: list[str], *, integer: bool):
    if is_empty(value):
        return
    try:
        num = float(value.replace(",", ".").replace(" ", ""))
    except ValueError:
        idx = COL_FIELD.index(field)
        errors.append(
            f"Строка {row_num}: поле «{HEADERS[idx]}» должно быть числом, получено «{value}»"
        )
        return
    if integer and (num < 0 or num != int(num)):
        idx = COL_FIELD.index(field)
        errors.append(
            f"Строка {row_num}: поле «{HEADERS[idx]}» должно быть целым числом ≥ 0"
        )


def _check_party(
    row_num: int,
    v: list[str],
    profile: PartnerProfile | None,
    errors: list[str],
    *,
    type_field: str,
    inn_field: str,
    reg_field: str,
    oksm_field: str,
    role: str,
):
    if not _field_active(profile, type_field):
        return

    type_idx = COL_FIELD.index(type_field)
    ptype = norm_key(v[type_idx])
    if not ptype:
        return

    inn = v[COL_FIELD.index(inn_field)] if _field_active(profile, inn_field) else ""
    reg = v[COL_FIELD.index(reg_field)] if _field_active(profile, reg_field) else ""
    oksm = v[COL_FIELD.index(oksm_field)] if _field_active(profile, oksm_field) else ""

    if ptype in RU_PARTY and _field_active(profile, inn_field) and is_empty(inn):
        errors.append(_empty_field_error(row_num, inn_field))
    if ptype in FOREIGN_PARTY:
        if _field_active(profile, oksm_field) and is_empty(oksm):
            errors.append(_empty_field_error(row_num, oksm_field))
        if _field_active(profile, inn_field) and _field_active(profile, reg_field):
            if is_empty(inn) and is_empty(reg):
                errors.append(
                    f"Строка {row_num}: поле «{_field_label(inn_field)}» или "
                    f"«{_field_label(reg_field)}» пустое"
                )


def validate_row(row_num: int, values, profile: PartnerProfile | None) -> list[str]:
    errors: list[str] = []
    v = [norm(x) for x in values[:19]]
    while len(v) < 19:
        v.append("")

    for field in COL_FIELD:
        if not _is_required_scalar(profile, field):
            continue
        idx = COL_FIELD.index(field)
        if is_empty(v[idx]):
            errors.append(_empty_field_error(row_num, field))

    for field in ENUM_BY_FIELD:
        if not _field_active(profile, field):
            continue
        idx = COL_FIELD.index(field)
        _check_enum(row_num, field, v[idx], errors)

    if _field_active(profile, "impressions"):
        _check_number(row_num, "impressions", v[17], errors, integer=True)
    if _field_active(profile, "amount"):
        _check_number(row_num, "amount", v[18], errors, integer=False)

    _check_party(
        row_num, v, profile, errors,
        type_field="customer_type",
        inn_field="customer_inn",
        reg_field="customer_reg_no",
        oksm_field="customer_oksm",
        role="заказчика",
    )
    _check_party(
        row_num, v, profile, errors,
        type_field="contractor_type",
        inn_field="contractor_inn",
        reg_field="contractor_reg_no",
        oksm_field="contractor_oksm",
        role="исполнителя",
    )

    return errors


def validate_workbook_bytes(
    data: bytes, profile: PartnerProfile | None = None
) -> ValidationResult:
    wb = openpyxl.load_workbook(BytesIO(data), read_only=True, data_only=True)
    ws = wb.active
    all_errors: list[str] = []
    problem_rows: list[int] = []
    data_rows = 0
    for row_num, row in enumerate(
        ws.iter_rows(min_row=3, max_col=19, values_only=True),
        start=3,
    ):
        values = list(row) if row else []
        if all(is_empty(x) for x in values):
            continue
        data_rows += 1
        row_errors = validate_row(row_num, values, profile)
        if row_errors:
            problem_rows.append(row_num)
            all_errors.extend(row_errors)
    if data_rows == 0:
        all_errors.append("Нет строк данных")
    wb.close()
    return ValidationResult(errors=all_errors, row_numbers=problem_rows)
