"""Results table with the found rows and an export-to-CSV action."""

from __future__ import annotations

import csv
import os
import subprocess

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.models import ScanResult
from . import theme

COLUMNS = [
    "Period",
    "List Folder",
    "Excel File",
    "Created",
    "Modified",
    "Project Code",
    "Project Name",
    "Demanded By",
    "Item",
    "CAS No",
    "SAT No",
    "Similarity",
    "Excel Row",
]

PERIOD_COLUMN = 0

RESULT_ROLE = Qt.ItemDataRole.UserRole


class ResultsTable(QWidget):
    """Displays scan results and opens the source file on double-click."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._results: list[ScanResult] = []

        self._count_label = QLabel("0 result")
        self._count_label.setObjectName("subtitleLabel")
        self._export_btn = QPushButton("Export CSV")
        self._export_btn.setObjectName("secondaryButton")
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self._export_csv)

        header_row = QHBoxLayout()
        header_row.addWidget(QLabel("Search Results"))
        self._results_title = None
        header_row.addWidget(self._count_label)
        header_row.addStretch()
        header_row.addWidget(self._export_btn)

        self._table = QTableWidget(0, len(COLUMNS))
        self._table.setHorizontalHeaderLabels(COLUMNS)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.cellDoubleClicked.connect(self._open_row_file)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        header.setMinimumSectionSize(60)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # Give each column a sensible base width so titles fit comfortably.
        base_widths = {
            0: 90,   # Period
            1: 90,   # List Folder
            2: 150,  # Excel File
            3: 120,  # Created
            4: 120,  # Modified
            5: 110,  # Project Code
            6: 120,  # Project Name
            7: 100,  # Demanded By
            8: 140,  # Item
            9: 90,   # CAS No
            10: 110,  # SAT No
            11: 90,   # Similarity
            12: 80,   # Excel Row
        }
        for column in range(len(COLUMNS)):
            self._table.setColumnWidth(column, base_widths[column])

        # Sorting is enabled only after a scan finishes so that incoming
        # rows are not reshuffled while the table is being filled.
        self._table.setSortingEnabled(False)

        # Let the header height wrap when needed so no title is clipped.
        self._table.horizontalHeader().setMinimumHeight(34)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addLayout(header_row)
        layout.addWidget(self._table, 1)

    # ------------------------------------------------------------------ api
    def results(self) -> list[ScanResult]:
        return self._results

    def add_result(self, result: ScanResult) -> None:
        self._results.append(result)
        row = self._table.rowCount()
        self._table.insertRow(row)
        values = [
            result.period,
            result.list_folder,
            result.excel_file,
            result.created,
            result.modified,
            result.project_code,
            result.project_name,
            result.demanded_by,
            result.item,
            result.cas_no,
            result.sat_no,
            f"{result.similarity:g}%",
            str(result.row_number),
        ]
        for col, value in enumerate(values):
            cell = QTableWidgetItem(value)
            cell.setData(RESULT_ROLE, result.source_path)
            cell.setToolTip(value)
            self._table.setItem(row, col, cell)
        self._update_count()

    def fit_columns(self) -> None:
        """Resize columns to fit content, then sort by Period descending.

        Sorting is enabled after the scan so users can click any header to
        re-sort; during result insertion it stays disabled.
        """
        self._table.setSortingEnabled(False)
        self._table.resizeColumnsToContents()
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSortingEnabled(True)
        self._table.sortItems(
            PERIOD_COLUMN, Qt.SortOrder.DescendingOrder)

    def clear(self) -> None:
        self._table.setSortingEnabled(False)
        self._results.clear()
        self._table.setRowCount(0)
        self._update_count()

    def _update_count(self) -> None:
        count = len(self._results)
        self._count_label.setText(f"{count} result{'s' if count != 1 else ''}")
        self._export_btn.setEnabled(count > 0)

    # ------------------------------------------------------------- interactions
    def _open_row_file(self, row: int, _column: int) -> None:
        item = self._table.item(row, 0)
        if item is None:
            return
        path = item.data(RESULT_ROLE)
        if not path or not os.path.isfile(path):
            QMessageBox.warning(self, "Not Found",
                                "The source Excel file could not be located.")
            return
        try:
            if os.name == "nt":
                os.startfile(path)  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", path])
        except OSError as exc:
            QMessageBox.warning(self, "Open Failed", f"Could not open the file:\n{exc}")

    def _export_csv(self) -> None:
        target, _ = QFileDialog.getSaveFileName(
            self, "Export Results", "sat_tarama_results.csv",
            "CSV Files (*.csv)")
        if not target:
            return
        try:
            with open(target, "w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle)
                writer.writerow(COLUMNS)
                for result in self._results:
                    writer.writerow([
                        result.period, result.list_folder,
                        result.excel_file, result.created, result.modified,
                        result.project_code, result.project_name, result.demanded_by,
                        result.item, result.cas_no, result.sat_no,
                        f"{result.similarity:g}%", result.row_number,
                    ])
        except OSError as exc:
            QMessageBox.warning(self, "Export Failed", f"Could not write the file:\n{exc}")
            return
        QMessageBox.information(self, "Export Done",
                                f"Results exported to:\n{target}")