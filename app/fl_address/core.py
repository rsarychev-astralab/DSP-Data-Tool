from fastapi import HTTPException

from app.dadata.core import inn_checksum_ok
from app.fl_address.regions import REGIONS, address_for_region

NOTE = "Адрес по месту постановки на учёт в налоговой, не адрес проживания."


def lookup_fl_address(inn: str) -> dict[str, str]:
    digits = "".join(ch for ch in (inn or "") if ch.isdigit())
    if len(digits) == 10:
        raise HTTPException(
            status_code=400,
            detail=(
                "ИНН из 10 цифр — это юрлицо. "
                "Проверьте во вкладке «Проверка юридических лиц»."
            ),
        )
    if len(digits) != 12:
        raise HTTPException(
            status_code=400,
            detail="Для физлица нужен ИНН из 12 цифр",
        )
    if not inn_checksum_ok(digits):
        raise HTTPException(
            status_code=400,
            detail="Некорректная контрольная сумма ИНН",
        )

    code = digits[:2]
    region = REGIONS.get(code)
    if not region:
        raise HTTPException(
            status_code=422,
            detail=f"Неизвестный код региона {code}",
        )

    return {
        "inn": digits,
        "region_code": code,
        "region": region,
        "address": address_for_region(region),
        "note": NOTE,
    }
