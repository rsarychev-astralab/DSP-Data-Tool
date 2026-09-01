from typing import Any

from fastapi import HTTPException

_CHUNK = 1024 * 1024


async def read_upload_limited(file: Any, max_bytes: int) -> bytes:
    """Читает upload чанками и обрывает, если файл больше лимита."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            mb = max_bytes // (1024 * 1024)
            raise HTTPException(400, f"Файл больше {mb} МБ")
        chunks.append(chunk)
    return b"".join(chunks)
