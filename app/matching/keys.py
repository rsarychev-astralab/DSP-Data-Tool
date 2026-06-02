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
_INN_SPLIT_RE = re.compile(r"\s*ИНН\s*:?\s*(\d[\d\s]*)$", re.IGNORECASE)


def split_party_name_inn(val) -> tuple[str, str]:
    """«ООО … ИНН: 7700000000» → (название, инн)."""
    if not has_value(val):
        return "", ""
    text = str(val).strip()
    match = _INN_SPLIT_RE.search(text)
    if not match:
        return text, ""
    inn = re.sub(r"\s+", "", match.group(1))
    name = text[: match.start()].strip()
    return name, inn


def strip_internal_contract_id_suffix(text: str) -> str:
    """«26/14 - 1993» → «26/14»: в базе после « - » часто внутренний id учётной системы."""
    if " - " not in text:
        return text
    prefix, suffix = text.rsplit(" - ", 1)
    if re.fullmatch(r"\d+", suffix.strip()):
        return prefix.strip()
    return text


def norm_contract_no(val) -> str:
    if not has_value(val):
        return ""
    if isinstance(val, float) and val == val and val == int(val):
        text = str(int(val))
    else:
        text = str(val).strip()
    return strip_internal_contract_id_suffix(text)


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


def norm_inn(val) -> str:
    if not has_value(val):
        return ""
    if isinstance(val, float) and val == val and val == int(val):
        return str(int(val))
    return re.sub(r"\s+", "", str(val).strip())


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
    """Вид деятельности в базе и в выгрузке после преобразования."""
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
    customer_inn,
    contractor_inn,
    contract_type,
    contract_subject,
    from_db: bool,
) -> tuple[str, str, str, str, str, str]:
    """Ключ метчинга: номер, дата, ИНН, тип и предмет договора."""
    return (
        norm_contract_no(contract_no),
        norm_match_date(contract_date),
        norm_inn(customer_inn),
        norm_inn(contractor_inn),
        norm_contract_type(contract_type, from_db=from_db),
        norm_contract_subject(contract_subject, from_db=from_db),
    )
