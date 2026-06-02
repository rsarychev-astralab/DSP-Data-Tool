from app.engine.normalize import normalize_field, normalize_text


def test_normalize_text_whole_float_without_decimal():
    assert normalize_text(1.0) == "1"
    assert normalize_text(7700000000.0) == "7700000000"


def test_normalize_text_whole_number_strings():
    assert normalize_text("1.0") == "1"
    assert normalize_text("7700000001,0") == "7700000001"


def test_normalize_text_keeps_non_whole_and_text():
    assert normalize_text("12.34") == "12.34"
    assert normalize_text("dog-42") == "dog-42"
    assert normalize_text(12.5) == "12.5"


def test_normalize_field_contract_and_inn():
    assert normalize_field("contract_no", 1.0) == "1"
    assert normalize_field("customer_inn", 7700123456789.0) == "7700123456789"
