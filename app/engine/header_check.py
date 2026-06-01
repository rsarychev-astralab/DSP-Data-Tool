from dataclasses import dataclass

from app.engine.normalize import norm_key


@dataclass(frozen=True)
class ColumnHeaderRule:
    index: int
    patterns: tuple[str, ...]
    label: str | None = None


@dataclass(frozen=True)
class HeaderCheck:
    row: int
    columns: tuple[ColumnHeaderRule, ...]


def _header_cell_matches(cell_value, patterns: tuple[str, ...]) -> bool:
    header_norm = norm_key(cell_value)
    if not header_norm:
        return False
    for pattern in patterns:
        pattern_norm = norm_key(pattern)
        if not pattern_norm:
            continue
        if header_norm == pattern_norm or pattern_norm in header_norm or header_norm in pattern_norm:
            return True
    return False


def validate_source_headers(header_row: tuple, check: HeaderCheck) -> None:
    errors: list[str] = []
    for rule in check.columns:
        actual = header_row[rule.index] if rule.index < len(header_row) else None
        if not _header_cell_matches(actual, rule.patterns):
            expected = rule.label or " / ".join(rule.patterns)
            actual_text = "" if actual is None else str(actual).strip()
            if not actual_text:
                actual_text = "(пусто)"
            errors.append(
                f"колонка {rule.index + 1}: ожидали «{expected}», в файле «{actual_text}»"
            )

    if errors:
        details = "; ".join(errors)
        raise ValueError(
            "Формат выгрузки не совпадает с профилем — возможно, сместились колонки. "
            f"{details}"
        )


def read_header_row(ws, row_num: int, max_index: int) -> tuple:
    rows = list(
        ws.iter_rows(
            min_row=row_num,
            max_row=row_num,
            min_col=1,
            max_col=max_index + 1,
            values_only=True,
        )
    )
    if not rows:
        return tuple()
    row = rows[0]
    return tuple(row) if row else tuple()
