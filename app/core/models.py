"""Data models describing the folder structure and scan results."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MonthFolder:
    """A month folder inside a year folder.

    The name follows the pattern ``AY_NO-AY_ADI`` or ``AY_NO- AY_ADI``.
    Only the leading number identifies the month.
    """

    path: Path
    number: int
    checked: bool = True


@dataclass
class YearFolder:
    """A year folder that contains up to 12 month folders."""

    path: Path
    name: str
    checked: bool = True
    months: list[MonthFolder] = field(default_factory=list)


@dataclass
class ScanResult:
    """A single matching row found during a search."""

    year_folder: str
    month_folder: str
    period: str
    list_folder: str
    excel_file: str
    created: str
    modified: str
    project_code: str
    project_name: str
    demanded_by: str
    item: str
    cas_no: str
    sat_no: str
    source_path: str = ""