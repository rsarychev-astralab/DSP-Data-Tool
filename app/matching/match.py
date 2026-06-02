"""Метчинг строк шаблона DSP с «База договоров»."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

import openpyxl

from app.config import (
    CONTRACT_ATTRS_CANDIDATES,
    CONTRACT_ATTRS_SHEET,
    resolve_contract_attrs_path as _resolve_contract_attrs_path,
)
from app.engine.normalize import has_value
from app.engine.template import TEXT_NUMBER_FORMAT
from app.matching.keys import build_match_key
from app.validation.validate import is_empty

DATA_START_ROW = 3
OUTPUT_HEADERS = ["ERID", "ID в OTM", "ID в OZON", "ID в VK"]

# Заголовки листа OriginalContract в «База договоров.xlsx»
DB_HEADERS = {
    "contract_no": "Номер",
    "contract_date": "Дата",
    "contractor_name": "Исполнитель (Агент)",
    "customer_name": "Заказчик (Принципал)",
    "contract_type": "Тип договора",
    "contract_subject": "Сведения о предмете договора",
    "intermediary_type": "Тип посреднического договора",
    "inactive": "Неактуален",
    "id_otm": "ID в OTM",
    "id_ozon": "ID в OZON",
    "id_vk": "ID в VK",
}

# Колонки выгрузки шаблона (0-based в строке из 19 ячеек)
UPLOAD_COL = {
    "erid": 0,
    "contract_no": 1,
    "contract_date": 2,
    "contract_type": 3,
    "contract_subject": 4,
    "activity_type": 5,
    "customer_name": 7,
    "contractor_name": 12,
}


@dataclass(frozen=True)
class ContractEntry:
    id_otm: Any
    id_ozon: Any
    id_vk: Any


@dataclass(frozen=True)
class MatchResult:
    output_bytes: bytes
    output_filename: str
    rows_total: int
    rows_matched: int
    rows_unmatched: int


def resolve_contract_attrs_path() -> Path | None:
    return _resolve_contract_attrs_path()


def build_matched_filename(original_filename: str | None) -> str:
    if original_filename:
        stem = Path(original_filename).stem
        if stem.endswith("_matched"):
            return f"{stem}.xlsx"
        return f"{stem}_matched.xlsx"
    return "dsp_matched.xlsx"


def _cell(row: tuple, index: int) -> Any:
    return row[index] if index < len(row) else None


def _is_inactive(val) -> bool:
    if not has_value(val):
        return False
    return norm_key_inactive(str(val).strip().lower())


def norm_key_inactive(text: str) -> bool:
    return text in {"да", "yes", "true", "1", "y"}


def _header_columns(ws, titles: dict[str, str]) -> dict[str, int]:
    by_title: dict[str, int] = {}
    for col in range(1, (ws.max_column or 0) + 1):
        val = ws.cell(1, col).value
        if has_value(val):
            by_title[str(val).strip()] = col
    columns: dict[str, int] = {}
    missing = []
    for field, title in titles.items():
        if title in by_title:
            columns[field] = by_title[title]
        elif field not in ("id_otm", "id_ozon", "id_vk"):
            missing.append(title)
    for id_field, title in (
        ("id_otm", "ID в OTM"),
        ("id_ozon", "ID в OZON"),
        ("id_vk", "ID в VK"),
    ):
        if title in by_title:
            columns[id_field] = by_title[title]
    if missing:
        raise ValueError(
            "В справочнике договоров нет колонок: " + ", ".join(f"«{t}»" for t in missing)
        )
    return columns


def _format_id(val) -> str | None:
    if not has_value(val):
        return None
    if isinstance(val, float) and val == val and val == int(val):
        return str(int(val))
    if isinstance(val, int):
        return str(val)
    return str(val).strip()


def _load_contract_index(path: Path) -> dict[tuple[str, ...], ContractEntry]:
    """Load contract DB into match key index (first row wins on duplicate keys)."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        sheet_name = (
            CONTRACT_ATTRS_SHEET
            if CONTRACT_ATTRS_SHEET in wb.sheetnames
            else wb.sheetnames[0]
        )
        ws = wb[sheet_name]
        cols = _header_columns(ws, DB_HEADERS)
        index: dict[tuple[str, ...], ContractEntry] = {}

        def get_col(row_vals: list, field: str):
            col = cols[field]
            return row_vals[col - 1] if col - 1 < len(row_vals) else None

        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row:
                continue
            row_vals = list(row)
            if not has_value(get_col(row_vals, "contract_no")):
                continue
            if "inactive" in cols and _is_inactive(get_col(row_vals, "inactive")):
                continue

            key = build_match_key(
                contract_no=get_col(row_vals, "contract_no"),
                contract_date=get_col(row_vals, "contract_date"),
                customer_name=get_col(row_vals, "customer_name"),
                contractor_name=get_col(row_vals, "contractor_name"),
                contract_type=get_col(row_vals, "contract_type"),
                contract_subject=get_col(row_vals, "contract_subject"),
                intermediary_type=get_col(row_vals, "intermediary_type"),
                from_db=True,
            )
            if key in index:
                continue
            index[key] = ContractEntry(
                id_otm=_format_id(get_col(row_vals, "id_otm")) if "id_otm" in cols else None,
                id_ozon=_format_id(get_col(row_vals, "id_ozon")) if "id_ozon" in cols else None,
                id_vk=_format_id(get_col(row_vals, "id_vk")) if "id_vk" in cols else None,
            )
        return index
    finally:
        wb.close()


def _read_upload_rows(data: bytes) -> list[dict[str, Any]]:
    wb = openpyxl.load_workbook(BytesIO(data), read_only=True, data_only=True)
    try:
        ws = wb.active
        header = ws.cell(1, 1).value
        if header and "ERID" not in str(header).upper():
            raise ValueError(
                "Файл не похож на шаблон загрузки DSP: в A1 ожидается заголовок ERID"
            )
        rows: list[dict[str, Any]] = []
        for row in ws.iter_rows(min_row=DATA_START_ROW, max_col=19, values_only=True):
            values = list(row) if row else []
            if all(is_empty(x) for x in values):
                continue
            rows.append({
                "erid": _cell(values, UPLOAD_COL["erid"]),
                "contract_no": _cell(values, UPLOAD_COL["contract_no"]),
                "contract_date": _cell(values, UPLOAD_COL["contract_date"]),
                "contract_type": _cell(values, UPLOAD_COL["contract_type"]),
                "contract_subject": _cell(values, UPLOAD_COL["contract_subject"]),
                "intermediary_type": _cell(values, UPLOAD_COL["activity_type"]),
                "customer_name": _cell(values, UPLOAD_COL["customer_name"]),
                "contractor_name": _cell(values, UPLOAD_COL["contractor_name"]),
            })
        if not rows:
            raise ValueError("В файле нет строк данных (ожидаются с 3-й строки)")
        return rows
    finally:
        wb.close()


def _write_output(rows: list[tuple]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    for col, title in enumerate(OUTPUT_HEADERS, 1):
        cell = ws.cell(1, col, title)
        cell.number_format = TEXT_NUMBER_FORMAT
    for i, (erid, id_otm, id_ozon, id_vk) in enumerate(rows, start=DATA_START_ROW):
        for col, val in enumerate((erid, id_otm, id_ozon, id_vk), 1):
            if val is None:
                continue
            cell = ws.cell(i, col, str(val))
            cell.number_format = TEXT_NUMBER_FORMAT
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


def _apply_matching(upload_bytes: bytes, attrs_path: Path) -> tuple[bytes, int, int, int]:
    index = _load_contract_index(attrs_path)
    upload_rows = _read_upload_rows(upload_bytes)
    output: list[tuple] = []
    matched = 0
    for row in upload_rows:
        key = build_match_key(
            contract_no=row["contract_no"],
            contract_date=row["contract_date"],
            customer_name=row["customer_name"],
            contractor_name=row["contractor_name"],
            contract_type=row["contract_type"],
            contract_subject=row["contract_subject"],
            intermediary_type=row["intermediary_type"],
            from_db=False,
        )
        entry = index.get(key)
        if entry:
            matched += 1
            output.append((
                _format_id(row["erid"]) or str(row["erid"]).strip(),
                entry.id_otm,
                entry.id_ozon,
                entry.id_vk,
            ))
        else:
            output.append((
                _format_id(row["erid"]) or str(row["erid"]).strip(),
                None,
                None,
                None,
            ))
    total = len(upload_rows)
    return _write_output(output), total, matched, total - matched


def match_workbook_bytes(
    upload_bytes: bytes,
    *,
    original_filename: str | None = None,
) -> MatchResult:
    attrs_path = resolve_contract_attrs_path()
    if attrs_path is None:
        expected = ", ".join(f"«{p.name}»" for p in CONTRACT_ATTRS_CANDIDATES)
        raise FileNotFoundError(
            "Не найден файл атрибутов договоров в папке «Справка». "
            f"Добавьте один из файлов: {expected}"
        )

    output_bytes, rows_total, rows_matched, rows_unmatched = _apply_matching(
        upload_bytes, attrs_path
    )
    return MatchResult(
        output_bytes=output_bytes,
        output_filename=build_matched_filename(original_filename),
        rows_total=rows_total,
        rows_matched=rows_matched,
        rows_unmatched=rows_unmatched,
    )
