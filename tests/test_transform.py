from pathlib import Path

import pytest

from app.config import TEMPLATE_PATH
from app.engine.transform import build_record, transform_source
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


def test_buzzoola_maps_address_columns():
    profile = load_profile("buzzoola")
    assert profile.column_map["customer_address"] == 26
    assert profile.column_map["contractor_address"] == 21
    record = build_record(
        {
            "erid": "2VfnxxpZ3Yd",
            "customer_address": "129085, г. Москва, ул. Годовикова, д. 9, стр. 10.",
            "contractor_address": "197110, город Санкт-Петербург, Константиновский пр-кт, д. 11",
        },
        profile,
    )
    assert record["customer_address"] == "129085, г. Москва, ул. Годовикова, д. 9, стр. 10."
    assert record["contractor_address"].startswith("197110")


def test_transform_buzzoola_writes_addresses():
    source = Path("Исходные данные/buzzoola.xlsx")
    if not source.exists():
        pytest.skip("buzzoola sample not present")
    profile = load_profile("buzzoola")
    result = transform_source(
        source,
        profile,
        template_path=TEMPLATE_PATH,
        output_filename="buzzoola.xlsx",
        source_filename=source.name,
    )
    assert result.rows_written > 0
    with_customer = sum(1 for rec in result.records if rec.get("customer_address"))
    with_contractor = sum(1 for rec in result.records if rec.get("contractor_address"))
    assert with_customer > 0
    assert with_contractor > 0
