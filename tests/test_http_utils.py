from app.http_utils import encode_validation_errors


def test_encode_validation_errors_roundtrip():
    errors = [f"Строка {i}: тест" for i in range(3)]
    encoded = encode_validation_errors(errors)
    assert encoded is not None
    assert len(encoded) > 0


def test_encode_empty_returns_none():
    assert encode_validation_errors([]) is None
