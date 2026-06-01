import base64
import json

MAX_VALIDATION_ERRORS_IN_HEADER = 40
_MAX_HEADER_BYTES = 6000


def encode_validation_errors(errors: list[str]) -> str | None:
    if not errors:
        return None
    trimmed = errors[:MAX_VALIDATION_ERRORS_IN_HEADER]
    payload = json.dumps(trimmed, ensure_ascii=False).encode("utf-8")
    while len(payload) > _MAX_HEADER_BYTES and len(trimmed) > 1:
        trimmed = trimmed[:-1]
        payload = json.dumps(trimmed, ensure_ascii=False).encode("utf-8")
    return base64.b64encode(payload).decode("ascii")
