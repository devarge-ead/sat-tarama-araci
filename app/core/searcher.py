"""Column mapping, matching logic and the background search worker."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from . import excel_reader
from .folder_tree import list_folder_excels, month_number_from_name
from .models import ScanResult, YearFolder
from .similarity import item_similarity

SEARCH_MODE_SUBSTRING = "substring"
SEARCH_MODE_SIMILARITY = "similarity"

# Map each search field to a set of header prefixes (already lowercase).
HEADER_PREFIXES = {
    "project_code": ("project code",),
    "project_name": ("project name",),
    "demanded_by": ("name",),
    "item": ("item", "demand topic"),
    "cas_no": ("cas no",),
    "sat_no": ("sat no",),
}

# Columns every file must provide besides the optional SAT No.
REQUIRED_FIELDS = ("project_code", "project_name", "demanded_by", "item")

# Display value used when a local column for a field is absent.
MISSING_VALUE = "\u2014"  # em dash


def build_criteria(parameters: dict[str, str]) -> dict[str, str]:
    """Keep only the non-empty search parameters as matching criteria."""
    return {field: value for field, value in parameters.items() if value.strip()}
def map_columns(headers: list[str]) -> tuple[dict[str, int], set[str]]:
    """Map header positions to search fields.

    Returns (column_index_map, missing_required_fields).
    """
    mapping: dict[str, int] = {}
    found = {field: False for field in HEADER_PREFIXES}
    for index, header in enumerate(headers):
        normalized = excel_reader.normalize_header(header)
        if not normalized:
            continue
        for field, prefixes in HEADER_PREFIXES.items():
            if found[field]:
                continue
            if any(normalized.startswith(prefix) for prefix in prefixes):
                mapping[field] = index
                found[field] = True

    missing_required = {field for field in REQUIRED_FIELDS if not found[field]}
    return mapping, missing_required


def _match(row: list[str], mapping: dict[str, int], criteria: dict[str, str]) -> bool:
    """Return True when the row satisfies every criterion (substring)."""
    for field, search_value in criteria.items():
        column = mapping.get(field)
        if column is None:
            return False
        cell_value = row[column] if column < len(row) else ""
        if search_value.strip().lower() not in cell_value.lower():
            return False
    return True


# Fields matched by substring even in similarity mode: they are identifiers/codes
# where fuzzy similarity is unreliable, mirroring how batch search handles CAS.
IDENTIFIER_FIELDS = ("project_code", "cas_no", "sat_no")


def _similarity_match(row: list[str], mapping: dict[str, int],
                      criteria: dict[str, str], threshold: float,
                      similarity) -> tuple[bool, float]:
    """Similarity-based match.

    Returns (matched, score). Free-text fields (project_name, demanded_by,
    item) match when the search term is a substring of the value (score 100)
    or when the fuzzy similarity reaches the threshold; identifier fields are
    matched by substring. Every criterion must pass (AND).
    """
    scores: list[float] = []
    for field, search_value in criteria.items():
        column = mapping.get(field)
        if column is None:
            return False, 0.0
        cell_value = row[column] if column < len(row) else ""
        if field in IDENTIFIER_FIELDS:
            result = search_value.strip().lower() in cell_value.lower()
            score = 100.0 if result else 0.0
        else:
            # A substring hit is a guaranteed match (score 100); otherwise a
            # fuzzy hit passes only when its similarity reaches the threshold.
            # This keeps similarity a superset of the substring results.
            if search_value.strip().lower() in cell_value.lower():
                score = 100.0
                result = True
            else:
                score = similarity(search_value, cell_value)
                result = score >= threshold
        if not result:
            return False, 0.0
        scores.append(score)
    return True, round(min(scores), 1)


def _format_timestamp(path: Path, timestamp: float) -> str:
    import datetime

    return datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")


def _get(row: list[str], mapping: dict[str, int], field: str) -> str:
    """Read a field value from a row, using the em dash when the column is absent."""
    column = mapping.get(field)
    if column is None:
        return MISSING_VALUE
    if column >= len(row):
        return ""
    return row[column]
class SearchThread(QThread):
    """Runs a search in the background without blocking the UI."""

    progress = Signal(int, int)          # current file, total files
    result_found = Signal(object)        # ScanResult
    error = Signal(str)
    finished_search = Signal(int)        # number of files scanned

    def __init__(self, year_folders: list[YearFolder], criteria: dict[str, str],
                 mode: str = SEARCH_MODE_SUBSTRING, similarity_threshold: float = 80.0,
                 parent=None):
        super().__init__(parent)
        self._year_folders = year_folders
        self._criteria = criteria
        self._mode = mode
        self._threshold = similarity_threshold
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
                    if not rows:
                        processed += 1
                        continue
                    mapping, missing_required = map_columns(rows[0])
                    if missing_required:
                        processed += 1
                        continue
                    month_name = file_path.parent.parent.name if file_path.parent.parent else ""
                    month_num = month_number_from_name(month_name)
                    period = f"{year.name}-{month_num:02d}" if month_num is not None else month_name
                    list_folder_name = file_path.parent.name
                    for data_row_number, data_row in enumerate(rows[1:], start=2):
                        if not data_row:
                            continue
                        if self._mode == SEARCH_MODE_SIMILARITY:
                            matched, similarity_score = _similarity_match(
                                data_row, mapping, self._criteria, self._threshold,
                                item_similarity)
                        else:
                            matched = _match(data_row, mapping, self._criteria)
                            similarity_score = 100.0
                        if not matched:
                            continue
                        created = _format_timestamp(file_path, file_path.stat().st_ctime)
                        modified = _format_timestamp(file_path, file_path.stat().st_mtime)
                        result = ScanResult(
                            year_folder=year.name,
                            month_folder=month_name,
                            period=period,
                            list_folder=list_folder_name,
                            excel_file=file_path.name,
                            created=created,
                            modified=modified,
                            project_code=_get(data_row, mapping, "project_code"),
                            project_name=_get(data_row, mapping, "project_name"),
                            demanded_by=_get(data_row, mapping, "demanded_by"),
                            item=_get(data_row, mapping, "item"),
                            cas_no=_get(data_row, mapping, "cas_no"),
                            sat_no=_get(data_row, mapping, "sat_no"),
                            similarity=similarity_score,
                            source_path=str(file_path),
                            row_number=data_row_number,
                        )
                        self.result_found.emit(result)
                except Exception as exc:  # noqa: BLE001 - a bad file must not stop the scan
                    self.error.emit(f"{file_path.name}: {exc}")
                processed += 1
        self.progress.emit(total_files, total_files)
        self.finished_search.emit(processed)