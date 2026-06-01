from pathlib import Path

import pytest

from app.config import PROFILES_DIR
from app.profiles.loader import load_profile


@pytest.mark.parametrize("profile_file", sorted(PROFILES_DIR.glob("*.yaml")))
def test_existing_profiles_load(profile_file: Path):
    partner_id = profile_file.stem
    profile = load_profile(partner_id)
    assert profile.column_map
