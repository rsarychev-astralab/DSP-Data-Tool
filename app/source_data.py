from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.config import SOURCE_DATA_DIR
from app.profiles.loader import resolve_profile_id

ALLOWED_EXTENSIONS = {".xlsx", ".xlsm", ".xls"}
MAX_SOURCE_BYTES = 50 * 1024 * 1024


@dataclass(frozen=True)
class SavedSourceFile:
    partner_id: str
    display_name: str
    filename: str
    path: Path
    replaced: bool


def _pick_extension(original_filename: str) -> str:
    ext = Path(original_filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Нужен файл .xlsx, .xlsm или .xls")
    return ext


def build_source_filename(partner_id: str, original_filename: str) -> str:
    base = resolve_profile_id(partner_id)
    ext = _pick_extension(original_filename)
    return f"{base}{ext}"


def save_source_file(
    partner_id: str,
    display_name: str,
    content: bytes,
    original_filename: str,
) -> SavedSourceFile:
    if len(content) > MAX_SOURCE_BYTES:
        raise ValueError("Файл больше 50 МБ")

    SOURCE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    filename = build_source_filename(partner_id, original_filename)
    target = (SOURCE_DATA_DIR / filename).resolve()
    root = SOURCE_DATA_DIR.resolve()
    if root not in target.parents and target != root:
        raise ValueError("Недопустимый путь сохранения")

    replaced = target.exists()
    if replaced:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        stem = target.stem
        backup_name = f"{stem}_{stamp}{target.suffix}"
        target.rename(SOURCE_DATA_DIR / backup_name)

    target.write_bytes(content)
    return SavedSourceFile(
        partner_id=partner_id,
        display_name=display_name,
        filename=target.name,
        path=target,
        replaced=replaced,
    )
