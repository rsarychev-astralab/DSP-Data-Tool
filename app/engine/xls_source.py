"""Чтение .xlsx через calamine (быстро), .xls через xlrd."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import xlrd
from python_calamine import CalamineWorkbook as _CalamineWorkbook


class XlsSheet:
    def __init__(self, sheet):
        self._sheet = sheet

    def iter_rows(
        self,
        min_row: int = 1,
        max_row: int | None = None,
        min_col: int = 1,
        max_col: int | None = None,
        values_only: bool = True,
    ):
        start_r = max(min_row - 1, 0)
        end_r = self._sheet.nrows if max_row is None else min(max_row, self._sheet.nrows)
        start_c = max(min_col - 1, 0)
        end_c = self._sheet.ncols if max_col is None else min(max_col, self._sheet.ncols)
        for r in range(start_r, end_r):
            yield tuple(self._sheet.cell_value(r, c) for c in range(start_c, end_c))


class XlsWorkbook:
    def __init__(self, path: Path | None = None, content: bytes | None = None):
        if content is not None:
            self._book = xlrd.open_workbook(file_contents=content)
        elif path is not None:
            self._book = xlrd.open_workbook(str(path))
        else:
            raise ValueError("path or content required")

    @property
    def sheetnames(self) -> list[str]:
        return self._book.sheet_names()

    def __getitem__(self, name: str) -> XlsSheet:
        return XlsSheet(self._book.sheet_by_name(name))

    def close(self):
        pass


class CalamineSheet:
    def __init__(self, rows: list[tuple]):
        self._rows = rows

    def iter_rows(
        self,
        min_row: int = 1,
        max_row: int | None = None,
        min_col: int = 1,
        max_col: int | None = None,
        values_only: bool = True,
    ):
        start_r = max(min_row - 1, 0)
        end_r = len(self._rows) if max_row is None else min(max_row, len(self._rows))
        start_c = max(min_col - 1, 0)
        for r in range(start_r, end_r):
            row = self._rows[r]
            end_c = len(row) if max_col is None else min(max_col, len(row))
            if start_c:
                row = row[start_c:end_c]
            elif end_c < len(row):
                row = row[:end_c]
            yield tuple(row)


class CalamineWorkbook:
    def __init__(self, *, path: Path | None = None, content: bytes | None = None):
        if content is not None:
            self._book = _CalamineWorkbook.from_filelike(BytesIO(content))
        elif path is not None:
            self._book = _CalamineWorkbook.from_path(str(path))
        else:
            raise ValueError("path or content required")
        self._cache: dict[str, CalamineSheet] = {}

    @property
    def sheetnames(self) -> list[str]:
        return self._book.sheet_names

    def __getitem__(self, name: str) -> CalamineSheet:
        if name not in self._cache:
            sheet = self._book.get_sheet_by_name(name)
            self._cache[name] = CalamineSheet(sheet.to_python(skip_empty_area=False))
        return self._cache[name]

    def close(self):
        pass


def is_xls_path(path: Path | str | None) -> bool:
    return bool(path) and str(path).lower().endswith(".xls")


def _is_xls_name(name: str) -> bool:
    lower = name.lower()
    return lower.endswith(".xls") and not lower.endswith(".xlsx") and not lower.endswith(".xlsm")


def open_source_workbook(source: BinaryIO | Path, *, filename: str | None = None):
    """Возвращает (workbook, is_xls). .xls — xlrd, .xlsx/.xlsm — calamine."""
    if isinstance(source, Path):
        if is_xls_path(source):
            return XlsWorkbook(path=source), True
        return CalamineWorkbook(path=source), False

    data = source.read()
    name = (filename or "").lower()
    if _is_xls_name(name):
        return XlsWorkbook(content=data), True
    return CalamineWorkbook(content=data), False
