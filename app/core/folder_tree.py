"""Parsing of the year -> month -> list folder -> Excel files tree."""

from __future__ import annotations

import re
from pathlib import Path

from .models import MonthFolder, YearFolder

EXCEL_EXTENSIONS = (".xlsx", ".xlsm", ".xls")

# Matches the leading month number in a folder name such as "04-Nisan" or "04- Nisan".
_MONTH_RE = re.compile(r"^\s*(\d{1,2})")


def month_number_from_name(name: str) -> int | None:
    """Return the month number (1-12) encoded in a folder name, or None."""
    match = _MONTH_RE.match(name)
    if not match:
        return None
    number = int(match.group(1))
    if 1 <= number <= 12:
        return number
    return None


def build_year_folder(path: Path) -> YearFolder | None:
    """Build a YearFolder from a directory, scanning its month folders.

    Returns None when the given path is not an existing directory.
    """
    if not path.exists() or not path.is_dir():
        return None

    folder = YearFolder(path=path, name=year_from_name(path.name))
    # Sort months by their number so they are displayed in order.
    entries = []
    for child in path.iterdir():
        if child.is_dir():
            number = month_number_from_name(child.name)
            if number is not None:
                entries.append((number, child))
    for number, child in sorted(entries, key=lambda item: item[0]):
        folder.months.append(MonthFolder(path=child, number=number))
    return folder


def year_from_name(name: str) -> str:
    """Return the year encoded in the first 4 characters of a folder name.

    Falls back to the raw name when the first 4 characters are not digits.
    """
    prefix = name.strip()[:4]
    return prefix if prefix.isdigit() else name


def list_folder_excels(list_folder: Path) -> list[Path]:
    """Return direct Excel files inside a list folder.

    Nested subfolders inside the list folder are intentionally ignored.
    """
    if not list_folder.is_dir():
        return []
    result = []
    for item in list_folder.iterdir():
        if item.is_file() and item.suffix.lower() in EXCEL_EXTENSIONS:
            result.append(item)
    return sorted(result)


def scan(list_folder: Path) -> list[Path]:
    """Alias kept for readability when scanning a single list folder."""
    return list_folder_excels(list_folder)