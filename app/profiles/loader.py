from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from app.config import PROFILES_DIR
from app.engine.header_check import ColumnHeaderRule, HeaderCheck
from app.engine.lookups import TEMPLATE_COLUMNS

PROFILE_ALIASES: dict[str, str] = {
    "between_low": "between",
    "target_rtb": "targetrtb",
}


@dataclass
class PartnerProfile:
    id: str
    display_name: str
    sheet: str
    data_from_row: int
    column_map: dict[str, int]
    constants: dict[str, Any]
    amount_by_vat: dict[str, Any] | None = None
    # Значения-заглушки во входе → пусто (skip), напр. UNKNOWN у buzzoola
    empty_markers: tuple[str, ...] = ()
    header_check: HeaderCheck | None = None
    # Поля из column_map, которые могут оставаться пустыми в шаблоне
    optional_output_fields: frozenset[str] = frozenset()


def _load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _parse_header_check(raw: dict | None) -> HeaderCheck | None:
    if not raw:
        return None
    row = int(raw.get("row", 1))
    columns_raw = raw.get("columns") or {}
    rules: list[ColumnHeaderRule] = []
    for key, patterns in columns_raw.items():
        idx = int(key)
        if isinstance(patterns, str):
            pattern_list = (patterns,)
        else:
            pattern_list = tuple(str(p).strip() for p in patterns if str(p).strip())
        if not pattern_list:
            raise ValueError(f"header_check.columns[{key}]: patterns required")
        rules.append(ColumnHeaderRule(index=idx, patterns=pattern_list))
    if not rules:
        return None
    rules.sort(key=lambda r: r.index)
    return HeaderCheck(row=row, columns=tuple(rules))


def resolve_profile_id(partner_id: str) -> str:
    return PROFILE_ALIASES.get(partner_id, partner_id)


def has_transform_profile(partner_id: str) -> bool:
    profile_id = resolve_profile_id(partner_id)
    path = PROFILES_DIR / f"{profile_id}.yaml"
    return path.exists()


def load_profile(partner_id: str) -> PartnerProfile:
    profile_id = resolve_profile_id(partner_id)
    path = PROFILES_DIR / f"{profile_id}.yaml"
    if not path.exists():
        raise KeyError(f"Unknown partner: {partner_id}")

    data = _load_yaml(path)
    source = data.get("source", {})
    column_map = data.get("column_map", {})
    if not column_map:
        raise ValueError(f"Profile {profile_id}: column_map is required")

    unknown = set(column_map) - set(TEMPLATE_COLUMNS)
    if unknown:
        raise ValueError(
            f"Profile {profile_id}: unknown column_map keys: {', '.join(sorted(unknown))}"
        )

    markers = data.get("empty_markers") or []
    header_check = _parse_header_check(data.get("header_check"))
    optional_raw = data.get("optional_output_fields") or []
    optional_output_fields = frozenset(
        str(name).strip() for name in optional_raw if str(name).strip()
    )
    unknown_optional = optional_output_fields - set(TEMPLATE_COLUMNS)
    if unknown_optional:
        raise ValueError(
            f"Profile {profile_id}: unknown optional_output_fields: "
            f"{', '.join(sorted(unknown_optional))}"
        )

    return PartnerProfile(
        id=data["id"],
        display_name=data.get("display_name", data["id"]),
        sheet=source.get("sheet", "Sheet1"),
        data_from_row=int(source.get("data_from_row", 2)),
        column_map={k: int(v) for k, v in column_map.items()},
        constants=data.get("constants") or {},
        amount_by_vat=data.get("amount_by_vat"),
        empty_markers=tuple(str(m).strip() for m in markers if str(m).strip()),
        header_check=header_check,
        optional_output_fields=optional_output_fields,
    )
