import pytest

from app.engine.header_check import (
    ColumnHeaderRule,
    HeaderCheck,
    validate_source_headers,
)
from app.profiles.loader import load_profile


def test_sape_profile_has_header_check():
    profile = load_profile("sape")
    assert profile.header_check is not None
    assert profile.header_check.row == 1


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
