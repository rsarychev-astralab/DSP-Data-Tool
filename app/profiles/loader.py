from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from app.config import PROFILES_DIR

PROFILE_ALIASES: dict[str, str] = {}


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


def _load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


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

    markers = data.get("empty_markers") or []
    return PartnerProfile(
        id=data["id"],
        display_name=data.get("display_name", data["id"]),
        sheet=source.get("sheet", "Sheet1"),
        data_from_row=int(source.get("data_from_row", 2)),
        column_map={k: int(v) for k, v in column_map.items()},
        constants=data.get("constants") or {},
        amount_by_vat=data.get("amount_by_vat"),
        empty_markers=tuple(str(m).strip() for m in markers if str(m).strip()),
    )
