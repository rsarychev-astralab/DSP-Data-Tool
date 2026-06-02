from app.profiles.loader import load_profile
from app.validation.validate import validate_row


def _full_row(**overrides):
    row = [""] * 19
    defaults = {
        0: "erid-1",
        1: "dog-1",
        2: "2025-01-01",
        3: "Original",
        4: "Distribution",
        5: "Distribution",
        6: "LegalPerson",
        7: "Customer LLC",
        8: "7700000000",
        11: "LegalPerson",
        12: "Contractor LLC",
        13: "7700000001",
        18: "1000",
    }
    defaults.update(overrides)
    for idx, val in defaults.items():
        row[idx] = val
    return row


def test_validate_row_requires_erid():
    errors = validate_row(3, [""] * 19, None)
    assert any("ERID" in e for e in errors)


def test_adriver_allows_empty_reg_no_for_ru():
    profile = load_profile("adriver")
    row = _full_row()
    errors = validate_row(3, row, profile)
    assert not any("Рег.номер" in e for e in errors)
    assert not any("ОКСМ" in e for e in errors)
    assert not any("НДС" in e for e in errors)
    assert not any("Показы" in e for e in errors)


def test_validate_row_accepts_normalized_contract_type():
    row = _full_row()
    row[16] = "yes"
    row[17] = "100"
    errors = validate_row(3, row, None)
    assert not any("недопустимое" in e and "Тип договора" in e for e in errors)


def test_validate_row_rejects_bad_contract_type():
    row = _full_row()
    row[3] = "NotARealType"
    row[16] = "yes"
    row[17] = "100"
    errors = validate_row(3, row, None)
    assert any("Тип договора" in e for e in errors)


def test_ru_party_requires_inn():
    profile = load_profile("adriver")
    row = _full_row()
    row[8] = ""
    errors = validate_row(3, row, profile)
    assert any("ИНН" in e and "заказчика" in e for e in errors)


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
