"""Batch search: match rows of an input Excel file against the archive."""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from . import excel_reader, searcher
from .folder_tree import list_folder_excels, month_number_from_name
from .models import YearFolder

# Values that mean "no CAS number" and must be ignored during matching.
INVALID_CAS = {"", "na", "n/a", "n.a.", "-", "?"}


def is_valid_cas(value: str) -> bool:
    """Return True when the CAS value carries real data."""
    return value.strip().lower() not in INVALID_CAS


def item_similarity(a: str, b: str) -> float:
    """Advanced text similarity (0-100) combining sequence and token matching."""
    a = a.strip().lower()
    b = b.strip().lower()
    if not a or not b:
        return 0.0
    if a == b:
        return 100.0
    seq = difflib.SequenceMatcher(None, a, b).ratio() * 100.0
    token = difflib.SequenceMatcher(None, " ".join(sorted(a.split())),
                                    " ".join(sorted(b.split()))).ratio() * 100.0
    return max(seq, token)


@dataclass
class InputRow:
    """One row of the input Excel file used as a batch query."""

    index: int          # 1-based row number in the input file
    item: str
    cas_no: str


@dataclass
class BatchMatch:
    """A single archive match for an input row."""

    input_index: int
    period: str
    list_folder: str
    excel_file: str
    item: str
    cas_no: str
    sat_no: str
    similarity: float   # item similarity percentage (100.0 for CAS-only hits)
    matched_by: str     # "item", "cas" or "both"
    source_path: str


class BatchSearchThread(QThread):
    """Runs the batch scan in the background without blocking the UI."""

    progress = Signal(int, int)          # current file, total files
    match_found = Signal(object)         # BatchMatch
    error = Signal(str)
    finished_search = Signal(int)        # number of files scanned

    def __init__(self, year_folders: list[YearFolder], input_rows: list[InputRow],
                 threshold: float, parent=None):
        super().__init__(parent)
        self._year_folders = year_folders
        self._input_rows = input_rows
        self._threshold = threshold
        self._cancel_requested = False

    def cancel(self) -> None:
        self._cancel_requested = True

    def run(self) -> None:  # noqa: D102
        total_files = 0
        all_files: list[tuple[YearFolder, list[Path]]] = []
        for year in self._year_folders:
            if not year.checked:
                continue
            candidates = []
            for month in year.months:
                if not month.checked:
                    continue
                for list_folder in month.path.iterdir():
                    if list_folder.is_dir():
                        candidates.extend(list_folder_excels(list_folder))
            all_files.append((year, candidates))
            total_files += len(candidates)

        # CAS comparisons are only meaningful for rows with a real CAS value.
        cas_inputs = [r for r in self._input_rows if is_valid_cas(r.cas_no)]

        processed = 0
        for year, files in all_files:
            for file_path in files:
                if self._cancel_requested:
                    self.progress.emit(total_files, total_files)
                    self.finished_search.emit(processed)
                    return
                self.progress.emit(processed, total_files)
                try:
                    rows = excel_reader.read_rows(file_path)
                    if rows:
                        mapping, missing = searcher.map_columns(rows[0])
                        if "item" in mapping and not missing:
                            self._scan_file(
                                year, file_path, rows, mapping, cas_inputs)
                except Exception as exc:  # noqa: BLE001
                    self.error.emit(f"{file_path.name}: {exc}")
                processed += 1
        self.progress.emit(total_files, total_files)
        self.finished_search.emit(processed)

    def _scan_file(self, year: YearFolder, file_path: Path,
                   rows: list[list[str]], mapping: dict[str, int],
                   cas_inputs: list[InputRow]) -> None:
        month_name = file_path.parent.parent.name if file_path.parent.parent else ""
        month_num = month_number_from_name(month_name)
        period = f"{year.name}-{month_num:02d}" if month_num is not None else month_name
        cas_col = mapping.get("cas_no")
        sat_col = mapping.get("sat_no")
        item_col = mapping["item"]

        for data_row in rows[1:]:
            if not data_row:
                continue
            archive_item = data_row[item_col] if item_col < len(data_row) else ""
            archive_cas = (data_row[cas_col] if cas_col is not None
                           and cas_col < len(data_row) else "")
            archive_sat = (data_row[sat_col] if sat_col is not None
                           and sat_col < len(data_row) else "")

            for entry in self._input_rows:
                item_score = item_similarity(entry.item, archive_item)
                item_hit = bool(entry.item.strip()) and item_score >= self._threshold
                cas_hit = (entry in cas_inputs and is_valid_cas(archive_cas)
                           and entry.cas_no.strip().lower() in archive_cas.lower())
                if not (item_hit or cas_hit):
                    continue
                if item_hit and cas_hit:
                    matched_by = "both"
                elif item_hit:
                    matched_by = "item"
                else:
                    matched_by = "cas"
                    item_score = 100.0  # CAS hit without meaningful item score
                self.match_found.emit(BatchMatch(
                    input_index=entry.index,
                    period=period,
                    list_folder=file_path.parent.name,
                    excel_file=file_path.name,
                    item=archive_item,
                    cas_no=archive_cas,
                    sat_no=archive_sat or searcher.MISSING_VALUE,
                    similarity=round(item_score, 1),
                    matched_by=matched_by,
                    source_path=str(file_path),
                ))


def read_input_rows(path: Path) -> list[InputRow]:
    """Read ITEM and CAS NO columns from the chosen input Excel file."""
    rows = excel_reader.read_rows(path)
    if not rows:
        return []
    headers = [excel_reader.normalize_header(h) for h in rows[0]]
    item_col = next((i for i, h in enumerate(headers)
                     if h.startswith("item")), None)
    cas_col = next((i for i, h in enumerate(headers)
                    if h.startswith("cas no")), None)
    if item_col is None:
        return []
    result = []
    for position, row in enumerate(rows[1:], start=2):
        if not row:
            continue
        item = row[item_col] if item_col < len(row) else ""
        cas = row[cas_col] if cas_col is not None and cas_col < len(row) else ""
        if not item.strip() and not is_valid_cas(cas):
            continue
        result.append(InputRow(index=position, item=item, cas_no=cas))
    return result