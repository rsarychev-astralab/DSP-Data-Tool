from app.http_utils import encode_validation_errors, encode_validation_rows


def test_encode_validation_errors_roundtrip():
    errors = [f"Строка {i}: тест" for i in range(3)]
    encoded = encode_validation_errors(errors)
    assert encoded is not None
    assert len(encoded) > 0


def test_encode_empty_returns_none():
    assert encode_validation_errors([]) is None


def test_encode_validation_rows():
    assert encode_validation_rows([3, 5, 10]) == "3,5,10"
    assert encode_validation_rows([]) is None


def test_encode_validation_rows_truncates():
    rows = list(range(3, 3000))
    encoded = encode_validation_rows(rows)
    assert encoded is not None
    assert encoded.endswith(",...")
    encoded.encode("latin-1")


def test_encode_validation_rows_latin1_safe_for_otm_scale():
    rows = list(range(3, 3 + 800))
    encoded = encode_validation_rows(rows)
    assert encoded is not None
    encoded.encode("latin-1")
