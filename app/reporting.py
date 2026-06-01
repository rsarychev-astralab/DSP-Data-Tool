"""Отчётный период и имена выходных файлов."""

MONTH_SLUG: dict[int, str] = {
    1: "январь",
    2: "февраль",
    3: "март",
    4: "апрель",
    5: "май",
    6: "июнь",
    7: "июль",
    8: "август",
    9: "сентябрь",
    10: "окябрь",
    11: "ноябрь",
    12: "декабрь",
}

MONTH_LABEL: dict[int, str] = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь",
}


def validate_report_period(month: int, year: int) -> None:
    if month not in MONTH_SLUG:
        raise ValueError(f"Некорректный месяц: {month}")
    if year < 2020 or year > 2035:
        raise ValueError(f"Некорректный год: {year}")


def build_output_filename(partner_id: str, month: int, year: int) -> str:
    validate_report_period(month, year)
    slug = MONTH_SLUG[month]
    return f"{partner_id}_{slug}_{year}.xlsx"
