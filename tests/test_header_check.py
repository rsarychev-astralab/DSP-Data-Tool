import pytest

from app.engine.header_check import (
    ColumnHeaderRule,
    HeaderCheck,
    validate_source_headers,
)
from app.profiles.loader import load_profile


@pytest.mark.parametrize(
    "partner_id,header_row",
    [
        ("sape", 1),
        ("buzzoola", 2),
        ("otm", 1),
        ("umg", 1),
        ("adriver", 1),
        ("adiamtech", 1),
        ("giraff", 1),
        ("targetrtb", 1),
        ("between", 1),
        ("plazkart", 1),
        ("programmatica", 1),
        ("genius_desk", 1),
        ("bidvol", 1),
    ],
)
def test_profiles_have_header_check(partner_id, header_row):
    profile = load_profile(partner_id)
    assert profile.header_check is not None
    assert profile.header_check.row == header_row


def test_validate_headers_passes_for_sape_layout():
    profile = load_profile("sape")
    header = (
        "ERID", "Исполнитель", "Тип исполнитель", "ИНН исполнителя",
        "Рег. номер исполнителя", "ОКСМ исполнителя", "Заказчик", "Тип заказчика",
        "ИНН заказчика", "Рег. номер заказчика", "ОКСМ заказчика",
        "ID изначального договора", "Номер изначального договора",
        "Дата изначального договора", "Тип договора", "Вид деятельности",
        "Вид договора", "Показы", "Доход, Руб", "НДС",
    )
    validate_source_headers(header, profile.header_check)


def test_validate_headers_fails_on_column_shift():
    check = HeaderCheck(
        row=1,
        columns=(
            ColumnHeaderRule(0, ("ERID",)),
            ColumnHeaderRule(14, ("Тип договора",)),
        ),
    )
    shifted = ("Показы",) + ("x",) * 13 + ("Тип договора",)
    with pytest.raises(ValueError, match="сместились"):
        validate_source_headers(shifted, check)


@pytest.mark.parametrize(
    "partner_id,filename",
    [
        ("sape", "sape.xlsx"),
        ("buzzoola", "buzzoola.xlsx"),
        ("otm", "OTM.xlsx"),
        ("umg", "UMG.xlsx"),
        ("adriver", "adriver.xlsx"),
        ("adiamtech", "adiamtech.xlsx"),
        ("plazkart", "plazkart.xlsx"),
        ("programmatica", "Programmatica.xlsx"),
        ("genius_desk", "Genius Desk.xlsx"),
        ("bidvol", "bidvol.xls"),
        ("giraff", "giraff.xlsx"),
        ("targetrtb", "targetrtb.xlsx"),
        ("between", "between.xlsx"),
    ],
)
def test_real_source_passes_header_check(partner_id, filename):
    from pathlib import Path

    from app.config import SOURCE_DATA_DIR
    from app.engine.header_check import read_header_row, validate_source_headers
    from app.engine.xls_source import open_source_workbook

    source = SOURCE_DATA_DIR / filename
    if not source.exists():
        pytest.skip(f"{filename} not present")
    profile = load_profile(partner_id)
    if profile.header_check is None:
        pytest.skip("no header_check")
    wb, _ = open_source_workbook(source, filename=source.name)
    try:
        candidates = profile.sheet_candidates or (profile.sheet,)
        sheet_name = next((name for name in candidates if name in wb.sheetnames), None)
        if sheet_name is None:
            pytest.fail(f"sheet {candidates} not in {wb.sheetnames}")
        ws = wb[sheet_name]
        max_index = max(rule.index for rule in profile.header_check.columns)
        header_row = read_header_row(ws, profile.header_check.row, max_index)
        validate_source_headers(header_row, profile.header_check)
    finally:
        wb.close()


def test_transform_sape_real_file_passes_header_check():
    from io import BytesIO
    from pathlib import Path

    from app.config import TEMPLATE_PATH
    from app.engine.transform import transform_source

    source = Path("Исходные данные/sape.xlsx")
    if not source.exists():
        pytest.skip("sape sample not present")
    profile = load_profile("sape")
    with source.open("rb") as f:
        result = transform_source(
            BytesIO(f.read()),
            profile,
            template_path=TEMPLATE_PATH,
            output_filename="test.xlsx",
        )
    assert result.rows_written > 0


def test_synthetic_headers_pass_for_new_profiles():
    for partner_id in ("giraff", "targetrtb", "between", "umg", "programmatica"):
        profile = load_profile(partner_id)
        assert profile.header_check is not None
        max_index = max(rule.index for rule in profile.header_check.columns)
        header = [""] * (max_index + 1)
        for rule in profile.header_check.columns:
            header[rule.index] = rule.patterns[0]
        validate_source_headers(tuple(header), profile.header_check)


def test_plazkart_maps_vat_from_with_vat_amount_column():
    profile = load_profile("plazkart")
    assert "impressions" not in profile.column_map
    assert "vat_included" not in profile.column_map
    assert profile.constants.get("vat_included") == "yes"
    assert profile.column_map["amount"] == 13


def test_adriver_has_no_impressions_or_vat_source():
    profile = load_profile("adriver")
    assert "impressions" not in profile.column_map
    assert "vat_included" not in profile.column_map
    assert "vat_included" not in profile.constants
