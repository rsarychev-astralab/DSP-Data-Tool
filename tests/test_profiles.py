from pathlib import Path

import pytest

from app.config import PROFILES_DIR
from app.profiles.loader import load_profile, resolve_profile_id


@pytest.mark.parametrize("profile_file", sorted(PROFILES_DIR.glob("*.yaml")))
def test_existing_profiles_load(profile_file: Path):
    partner_id = profile_file.stem
    profile = load_profile(partner_id)
    assert profile.column_map


def test_profile_aliases():
    assert resolve_profile_id("between_low") == "between"
    assert resolve_profile_id("target_rtb") == "targetrtb"
    assert load_profile("target_rtb").id == "targetrtb"
    assert load_profile("between_low").id == "between"


def test_umg_maps_sample_layout():
    profile = load_profile("umg")
    assert profile.column_map["impressions"] == 1
    assert profile.column_map["amount"] == 2
    assert profile.column_map["customer_inn"] == 6
    assert profile.column_map["contract_no"] == 11
    assert profile.column_map["vat_included"] == 17


def test_programmatica_has_sheet_fallback():
    profile = load_profile("programmatica")
    assert "astralab" in profile.sheet_candidates
    assert "result" in profile.sheet_candidates
    assert profile.column_map["customer_inn"] == 7
    assert profile.column_map["impressions"] == 15
