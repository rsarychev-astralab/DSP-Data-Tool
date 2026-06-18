from app.engine.transform import build_record
from app.profiles.loader import load_profile


def test_build_record_empty_activity_stays_empty():
    profile = load_profile("genius_desk")
    record = build_record(
        {
            "erid": "abc",
            "contract_no": "1",
            "contract_subject": "org-distribution",
            "activity_type": None,
        },
        profile,
    )
    assert "activity_type" not in record


def test_build_record_activity_from_source_is_normalized():
    profile = load_profile("genius_desk")
    record = build_record(
        {
            "erid": "abc",
            "activity_type": "distribution",
        },
        profile,
    )
    assert record["activity_type"] == "Distribution"
