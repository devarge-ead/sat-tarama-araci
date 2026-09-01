"""Reading Excel files and exposing their raw rows as strings.

Supported formats:
    .xlsx, .xlsm  -> openpyxl
    .xls          -> xlrd
"""

from __future__ import annotations

import datetime
from pathlib import Path

from .folder_tree import EXCEL_EXTENSIONS


def _cell_to_str(value: object) -> str:
    """Convert an Excel cell value into a searchable string."""
    if value is None:
        return ""
    if isinstance(value, datetime.datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, datetime.date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    return str(value).strip()


def _rows_from_openpyxl(path: Path) -> list[list[str]]:
    import openpyxl

    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = workbook.worksheets[0]
        rows: list[list[str]] = []
        for row in sheet.iter_rows(values_only=True):
            rows.append([_cell_to_str(cell) for cell in row])
        return rows
    finally:
        workbook.close()


def _rows_from_xlrd(path: Path) -> list[list[str]]:
    import xlrd

    workbook = xlrd.open_workbook(path)
    sheet = workbook.sheet_by_index(0)
    rows: list[list[str]] = []
    for row_index in range(sheet.nrows):
        rows.append([_cell_to_str(sheet.cell_value(row_index, col_index))
                     for col_index in range(sheet.ncols)])
    return rows


def read_rows(path: Path) -> list[list[str]]:
    """Read a whole Excel file and return its rows as string lists."""
    extension = path.suffix.lower()
    if extension not in EXCEL_EXTENSIONS:
        raise ValueError(f"Unsupported Excel extension: {extension}")
    if extension == ".xls":
        return _rows_from_xlrd(path)
    return _rows_from_openpyxl(path)


def normalize_header(header: str) -> str:
    """Trim and lowercase a header string for case-insensitive matching."""
    return header.strip().lower()