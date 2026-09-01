from pathlib import Path
import os

from dotenv import load_dotenv

load_dotenv(override=True)

ROOT = Path(__file__).resolve().parents[1]
PROFILES_DIR = Path(__file__).resolve().parent / "profiles"
STATIC_DIR = ROOT / "static"

_TEMPLATE_NAME = "Шаблон загрузки данных от DSP (2).xlsx"
_TEMPLATE_CANDIDATES = [
    ROOT / "Шаблон" / _TEMPLATE_NAME,
    ROOT / _TEMPLATE_NAME,
]


def resolve_template_path() -> Path:
    for path in _TEMPLATE_CANDIDATES:
        if path.exists():
            return path
    return _TEMPLATE_CANDIDATES[0]


TEMPLATE_PATH = resolve_template_path()
SPRAVKA_DIR = ROOT / "Справка"
SPRAVKA_DSP_PATH = SPRAVKA_DIR / "DSP.xlsx"
SOURCE_DATA_DIR = Path(os.environ.get("SOURCE_DATA_DIR", str(ROOT / "Исходные данные")))

# Справочник атрибутов договоров из учётной системы (правила метчинга — в app.matching.match)
CONTRACT_ATTRS_CANDIDATES = [
    SPRAVKA_DIR / "База договоров.xlsx",
    SPRAVKA_DIR / "Договоры.xlsx",
    SPRAVKA_DIR / "Атрибуты договоров.xlsx",
    SPRAVKA_DIR / "contract_attributes.xlsx",
]
CONTRACT_ATTRS_SHEET = "OriginalContract"


def resolve_contract_attrs_path() -> Path | None:
    for path in CONTRACT_ATTRS_CANDIDATES:
        if path.exists():
            return path
    return None


def dadata_api_key() -> str:
    return os.environ.get("DADATA_API_KEY", "").strip()


def dadata_configured() -> bool:
    return bool(dadata_api_key())


def basic_auth_credentials() -> tuple[str, str]:
    user = os.environ.get("DSP_BASIC_USER", "").strip()
    password = os.environ.get("DSP_BASIC_PASSWORD", "")
    if not user or not password:
        return "", ""
    return user, password


def auth_configured() -> bool:
    return bool(basic_auth_credentials()[0])


def docs_enabled() -> bool:
    return os.environ.get("DSP_ENABLE_DOCS", "").strip().lower() in {"1", "true", "yes"}


def dadata_rate_limit_per_min() -> int:
    raw = os.environ.get("DADATA_RATE_LIMIT_PER_MIN", "60").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 60


def dadata_max_jobs() -> int:
    raw = os.environ.get("DADATA_MAX_JOBS", "2").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 2
