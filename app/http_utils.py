import base64
import json

MAX_VALIDATION_ERRORS_IN_HEADER = 40
_MAX_HEADER_BYTES = 6000
_MAX_VALIDATION_ROWS_CHARS = 4000


def encode_validation_errors(errors: list[str]) -> str | None:
    if not errors:
        return None
    trimmed = errors[:MAX_VALIDATION_ERRORS_IN_HEADER]
    payload = json.dumps(trimmed, ensure_ascii=False).encode("utf-8")
    while len(payload) > _MAX_HEADER_BYTES and len(trimmed) > 1:
        trimmed = trimmed[:-1]
        payload = json.dumps(trimmed, ensure_ascii=False).encode("utf-8")
    return base64.b64encode(payload).decode("ascii")


def encode_validation_rows(row_numbers: list[int]) -> str | None:
    if not row_numbers:
        return None
    parts: list[str] = []
    for row in row_numbers:
        candidate = ",".join(parts + [str(row)]) if parts else str(row)
        if len(candidate) > _MAX_VALIDATION_ROWS_CHARS:
            break
        parts.append(str(row))
    if not parts:
        return str(row_numbers[0])
    # Только ASCII: иначе Starlette падает с 500 (заголовки — latin-1).
    suffix = ",..." if len(parts) < len(row_numbers) else ""
    return ",".join(parts) + suffix
