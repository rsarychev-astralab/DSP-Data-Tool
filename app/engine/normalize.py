import re
from datetime import date, datetime

from app.engine.lookups import ACTIVITY_TYPE, CONTRACT_TYPE, PARTY_TYPE, SUBJECT_TYPE


def norm_key(val):
    return re.sub(r"[\s\.\-_«»\"']", "", str(val).strip().lower())


def has_value(val):
    if val is None:
        return False
    if isinstance(val, float) and val != val:
        return False
    text = str(val).strip()
    return text != "" and text != "--"


_WHOLE_NUMBER_TEXT = re.compile(r"^-?\d+[.,]\d+$")
_INTEGER_TEXT = re.compile(r"^-?\d+$")


def normalize_text(val):
    if not has_value(val):
        return None
    if isinstance(val, bool):
        return str(val)
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        if val != val:
            return None
        if val == int(val):
            return str(int(val))
        return str(val).strip()
    text = str(val).strip()
    if _INTEGER_TEXT.fullmatch(text):
        return text
    if _WHOLE_NUMBER_TEXT.fullmatch(text):
        num = _parse_number(text)
        if num is not None and num == int(num):
            return str(int(num))
    return text


def normalize_date(val):
    if not has_value(val):
        return None
    if isinstance(val, datetime):
        return val.date().isoformat()
    if isinstance(val, date):
        return val.isoformat()
    text = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return text


def normalize_lookup(val, mapping):
    if not has_value(val):
        return None
    return mapping.get(norm_key(val))


def normalize_vat(val):
    if val is True:
        return "yes"
    if val is False:
        return "no"
    if isinstance(val, (int, float)) and val == val:
        if val in (1, 1.0):
            return "yes"
        if val in (0, 0.0):
            return "no"
    if not has_value(val):
        return None
    key = norm_key(val)
    if key in {"yes", "да", "сндс", "ндсда", "22%", "20%", "18%", "10%", "true", "t", "1"} or "ндс" in key:
        return "yes"
    if key in {"no", "нет", "безндс", "false", "f", "0"}:
        return "no"
    return None


def _parse_number(val) -> float | None:
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val).replace(" ", "").replace(",", "."))
    except (TypeError, ValueError):
        return None


def normalize_impressions(val):
    if not has_value(val):
        return None
    num = _parse_number(val)
    if num is None or num < 0 or num != int(num):
        return None
    return int(num)


def normalize_amount(val):
    if not has_value(val):
        return None
    num = _parse_number(val)
    return num


def normalize_field(field_name, raw_value):
    if field_name == "contract_type":
        return normalize_lookup(raw_value, CONTRACT_TYPE)
    if field_name == "contract_subject":
        return normalize_lookup(raw_value, SUBJECT_TYPE)
    if field_name == "activity_type":
        return normalize_lookup(raw_value, ACTIVITY_TYPE)
    if field_name in ("customer_type", "contractor_type"):
        return normalize_lookup(raw_value, PARTY_TYPE)
    if field_name == "contract_date":
        return normalize_date(raw_value)
    if field_name == "vat_included":
        return normalize_vat(raw_value)
    if field_name == "impressions":
        return normalize_impressions(raw_value)
    if field_name == "amount":
        return normalize_amount(raw_value)
    return normalize_text(raw_value)
