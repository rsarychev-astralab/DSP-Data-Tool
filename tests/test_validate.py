from app.profiles.loader import load_profile
from app.validation.validate import required_field_indices, validate_row


def test_validate_row_requires_erid():
    errors = validate_row(3, [""] * 19, required_field_indices(None))
    assert any("ERID" in e for e in errors)


def test_adriver_profile_skips_vat_and_impressions():
    profile = load_profile("adriver")
    required = required_field_indices(profile)
    assert 16 not in required
    assert 17 not in required
    assert 18 in required


def test_validate_row_accepts_normalized_contract_type():
    row = [""] * 19
    row[0] = "erid-1"
    row[1] = "dog-1"
    row[2] = "2025-01-01"
    row[3] = "Original"
    row[4] = "Distribution"
    row[5] = "Distribution"
    row[6] = "LegalPerson"
    row[7] = "Customer"
    row[11] = "LegalPerson"
    row[12] = "Contractor"
    row[16] = "yes"
    row[17] = "100"
    row[18] = "1000"
    errors = validate_row(3, row, required_field_indices(None))
    assert not any("Тип договора" in e and "недопустимое" in e for e in errors)


def test_validate_row_rejects_bad_contract_type():
    row = [""] * 19
    row[0] = "erid-1"
    row[1] = "dog-1"
    row[2] = "2025-01-01"
    row[3] = "NotARealType"
    row[4] = "Distribution"
    row[5] = "Distribution"
    row[6] = "LegalPerson"
    row[7] = "Customer"
    row[11] = "LegalPerson"
    row[12] = "Contractor"
    row[16] = "yes"
    row[17] = "100"
    row[18] = "1000"
    errors = validate_row(3, row, required_field_indices(None))
    assert any("Тип договора" in e for e in errors)


def test_adriver_workbook_validation_minimal_errors():
    from io import BytesIO
    from pathlib import Path

    from app.config import TEMPLATE_PATH
    from app.engine.transform import transform_source
    from app.validation.validate import validate_workbook_bytes

    source = Path("Исходные данные/adriver.xlsx")
    if not source.exists():
        return
    profile = load_profile("adriver")
    with source.open("rb") as f:
        result = transform_source(
            BytesIO(f.read()), profile, template_path=TEMPLATE_PATH
        )
    errors = validate_workbook_bytes(result.output_bytes, profile)
    assert len(errors) == 0, errors[:5]
