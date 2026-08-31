from __future__ import annotations

import re

from fastapi import HTTPException

from app.dadata.core import inn_checksum_ok
from app.fl_address.regions import REGIONS, address_for_region

NOTE = "Адрес по месту постановки на учёт в налоговой, не адрес проживания."
UL_INN_DETAIL = (
    "ИНН из 10 цифр — это юрлицо. "
    "Проверьте во вкладке «Проверка юридических лиц»."
)
NEED_12_DETAIL = "Для физлица нужен ИНН из 12 цифр"
BAD_CHECKSUM_DETAIL = "Некорректная контрольная сумма ИНН"

_INTEGER_TEXT_RE = re.compile(r"^\d+(?:\.0+)?$")


def inn_digits(value: object | None) -> str:
    if value is None or isinstance(value, bool):
        return ""
    if isinstance(value, float):
        if value != value:
            return ""
        if value.is_integer():
            return str(int(value))
        return "".join(ch for ch in str(value) if ch.isdigit())
    if isinstance(value, int):
        return str(value)

    text = str(value).strip()
    if not text:
        return ""
    compact = text.replace(" ", "").replace("\u00a0", "")
    if _INTEGER_TEXT_RE.fullmatch(compact.replace(",", ".")):
        return compact.replace(",", ".").split(".")[0]
    return "".join(ch for ch in text if ch.isdigit())


def resolve_fl_address(inn: object | None) -> dict[str, str]:
    digits = inn_digits(inn)
    empty = {
        "inn": "",
        "region_code": "",
        "region": "",
        "address": "",
        "note": NOTE,
        "error": "",
    }
    if not digits:
        return empty

    if len(digits) == 10:
        return {**empty, "inn": digits, "error": UL_INN_DETAIL}
    if len(digits) != 12:
        return {**empty, "inn": digits, "error": NEED_12_DETAIL}
    if not inn_checksum_ok(digits):
        return {**empty, "inn": digits, "error": BAD_CHECKSUM_DETAIL}

    code = digits[:2]
    region = REGIONS.get(code)
    if not region:
        return {
            **empty,
            "inn": digits,
            "region_code": code,
            "error": f"Неизвестный код региона {code}",
        }

    return {
        "inn": digits,
        "region_code": code,
        "region": region,
        "address": address_for_region(region),
        "note": NOTE,
        "error": "",
    }


def lookup_fl_address(inn: str) -> dict[str, str]:
    result = resolve_fl_address(inn)
    if result["error"]:
        status = 422 if result["error"].startswith("Неизвестный код региона") else 400
        raise HTTPException(status_code=status, detail=result["error"])
    if not result["inn"]:
        raise HTTPException(status_code=400, detail=NEED_12_DETAIL)
    return {
        "inn": result["inn"],
        "region_code": result["region_code"],
        "region": result["region"],
        "address": result["address"],
        "note": result["note"],
    }
