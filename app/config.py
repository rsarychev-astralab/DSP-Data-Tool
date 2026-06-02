from pathlib import Path

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
SOURCE_DATA_DIR = ROOT / "Исходные данные"

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
