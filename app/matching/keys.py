"""Нормализация полей для ключа метчинга договоров."""

from __future__ import annotations

import re
from datetime import date, datetime

from app.engine.lookups import ACTIVITY_TYPE, CONTRACT_TYPE, SUBJECT_TYPE
from app.engine.normalize import has_value, norm_key, normalize_date

# Русские подписи в «База договоров» → ключ (как norm_key от англ. кода шаблона)
CONTRACT_TYPE_RU = {
    "оказаниеуслуг": "original",
    "посредническийдоговор": "intermediary",
    "допсоглашение": "additional",
    "дополнительноесоглашение": "additional",
}

SUBJECT_TYPE_RU = {
    "распространениерекламы": "distribution",
    "посредничество": "mediation",
    "договорнаорганизациюраспространениярекламы": "distributionorganization",
    "представительство": "representation",
    "иное": "other",
    "другое": "other",
}

INTERMEDIARY_TYPE_RU = {
    "na": "",
    "нет": "",
    "н/д": "",
    "распространениерекламы": "distribution",
    "заключениедоговоров": "conclude",
    "коммерческоепредставительство": "commercial",
    "иное": "other",
}

_INN_SUFFIX_RE = re.compile(r"\s*ИНН\s*:?\s*[\d\s]+$", re.IGNORECASE)


def norm_contract_no(val) -> str:
    if not has_value(val):
        return ""
    if isinstance(val, float) and val == val and val == int(val):
        return str(int(val))
    return str(val).strip()


def norm_match_date(val) -> str:
    if not has_value(val):
        return ""
    if isinstance(val, datetime):
        return val.date().isoformat()
    if isinstance(val, date):
        return val.isoformat()
    parsed = normalize_date(val)
    return parsed or str(val).strip()


def norm_party_name(val) -> str:
    if not has_value(val):
        return ""
    text = str(val).strip()
    text = _INN_SUFFIX_RE.sub("", text).strip()
    return norm_key(text)


def _map_ru_or_code(val, ru_map: dict[str, str], code_map: dict[str, str]) -> str:
    if not has_value(val):
        return ""
    key = norm_key(val)
    if key in ru_map:
        return ru_map[key]
    code = code_map.get(key)
    if code:
        return norm_key(code)
    return key


def norm_contract_type(val, *, from_db: bool) -> str:
    if from_db:
        return _map_ru_or_code(val, CONTRACT_TYPE_RU, CONTRACT_TYPE)
    return _map_ru_or_code(val, CONTRACT_TYPE_RU, CONTRACT_TYPE)


def norm_contract_subject(val, *, from_db: bool) -> str:
    if from_db:
        return _map_ru_or_code(val, SUBJECT_TYPE_RU, SUBJECT_TYPE)
    return _map_ru_or_code(val, SUBJECT_TYPE_RU, SUBJECT_TYPE)


def norm_intermediary_type(val, *, from_db: bool) -> str:
    """Тип посреднического договора в базе; в выгрузке — колонка «Вид деятельности»."""
    if not has_value(val):
        return ""
    key = norm_key(val)
    if from_db:
        return INTERMEDIARY_TYPE_RU.get(key, key)
    mapped = _map_ru_or_code(val, INTERMEDIARY_TYPE_RU, ACTIVITY_TYPE)
    if mapped in ("none", "нет"):
        return ""
    return mapped


def build_match_key(
    *,
    contract_no,
    contract_date,
    customer_name,
    contractor_name,
    contract_type,
    contract_subject,
    intermediary_type,
    from_db: bool,
) -> tuple[str, ...]:
    return (
        norm_contract_no(contract_no),
        norm_match_date(contract_date),
        norm_party_name(customer_name),
        norm_party_name(contractor_name),
        norm_contract_type(contract_type, from_db=from_db),
        norm_contract_subject(contract_subject, from_db=from_db),
        norm_intermediary_type(intermediary_type, from_db=from_db),
    )
