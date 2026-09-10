"""Batch Search tab: input file, threshold and grouped results."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core import batch_searcher
from ..core.batch_searcher import BatchMatch, BatchSearchThread, InputRow

COLUMNS = [
    "Row",
    "Input Item",
    "Input CAS No",
    "Matches",
    "Matched By",
    "Sim %",
    "Period",
    "List Folder",
    "Excel File",
    "Archive Item",
    "Archive CAS No",
    "Archive SAT No",
    "Archive Row",
]

SOURCE_ROLE = Qt.ItemDataRole.UserRole


class BatchPanel(QWidget):
    """Batch search controls plus a collapsible grouped results tree."""

    def __init__(self, year_provider, parent=None):
        super().__init__(parent)
        self._year_provider = year_provider  # callable returning year folders
        self._input_rows: list[InputRow] = []
        self._thread: BatchSearchThread | None = None

        self._file_edit = QLineEdit()
        self._file_edit.setPlaceholderText("Select an Excel file...")
        self._file_edit.setReadOnly(True)

        browse_btn = QPushButton("Browse...")
        browse_btn.setObjectName("secondaryButton")
        browse_btn.clicked.connect(self._browse_file)

        threshold_label = QLabel("Item Similarity Threshold:")
        self._threshold = QSpinBox()
        self._threshold.setRange(0, 100)
        self._threshold.setValue(80)
        self._threshold.setSuffix(" %")

        picker_row = QHBoxLayout()
        picker_row.setSpacing(8)
        picker_row.addWidget(self._file_edit, 1)
        picker_row.addWidget(browse_btn)
        picker_row.addWidget(threshold_label)
        picker_row.addWidget(self._threshold)

        self._start_btn = QPushButton("Start Batch Search")
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setObjectName("ghostButton")
        self._cancel_btn.setEnabled(False)
        self._start_btn.clicked.connect(self._start)
        self._cancel_btn.clicked.connect(self._cancel)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        self._progress.setFixedHeight(16)

        self._count_label = QLabel("0 result")
        self._count_label.setObjectName("subtitleLabel")
        button_row = QHBoxLayout()
        button_row.addWidget(self._start_btn)
        button_row.addWidget(self._cancel_btn)
        button_row.addStretch()
        button_row.addWidget(self._count_label)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(COLUMNS)
        self._tree.setAlternatingRowColors(True)
        self._tree.setExpandsOnDoubleClick(False)
        self._tree.itemDoubleClicked.connect(self._open_row_file)
        header = self._tree.header()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setMinimumSectionSize(60)
        widths = {0: 50, 1: 200, 2: 100, 3: 70, 4: 80, 5: 60, 6: 90,
                  7: 90, 8: 150, 9: 200, 10: 100, 11: 100, 12: 80}
        for column, width in widths.items():
            self._tree.setColumnWidth(column, width)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addLayout(picker_row)
        layout.addWidget(self._progress)
        layout.addLayout(button_row)
        layout.addWidget(self._tree, 1)

    # ------------------------------------------------------------------ inputs
    def _browse_file(self) -> None:
        target, _ = QFileDialog.getOpenFileName(
            self, "Select Excel File", "",
            "Excel Files (*.xlsx *.xlsm *.xls)")
        if not target:
            return
        try:
            rows = batch_searcher.read_input_rows(Path(target))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Read Failed",
                                f"Could not read the file:\n{exc}")
            return
        if not rows:
            QMessageBox.warning(
                self, "No Usable Columns",
                "No ITEM column was found in the first sheet of the file.")
            return
        self._file_edit.setText(target)
        self._input_rows = rows
        self._count_label.setText(f"{len(rows)} input row(s) loaded")

    # ------------------------------------------------------------------ search
    def _start(self) -> None:
        if not self._file_edit.text() or not self._input_rows:
            QMessageBox.warning(self, "No File", "Please select an Excel file first.")
            return
        year_folders = self._year_provider()
        selected = [f for f in year_folders
                    if f.checked and any(m.checked for m in f.months)]
        if not selected:
            QMessageBox.warning(self, "No Folders Selected",
                                "Please select at least one year/month folder.")
            return
        self._tree.clear()
        self._set_running(True)
        self._count_label.setText("Searching...")
        self._thread = BatchSearchThread(
            selected, self._input_rows, float(self._threshold.value()), self)
        self._thread.progress.connect(self._on_progress)
        self._thread.match_found.connect(self._on_match)
        self._thread.error.connect(self._on_error)
        self._thread.finished_search.connect(self._on_done)
        self._thread.start()

    def _cancel(self) -> None:
        self.cancel_search()

    def cancel_search(self) -> None:
        """Request cancellation of a running batch search (safe to call anytime)."""
        if self._thread is not None and self._thread.isRunning():
            self._thread.cancel()

    def _set_running(self, running: bool) -> None:
        self._start_btn.setEnabled(not running)
        self._cancel_btn.setEnabled(running)
        self._file_edit.setEnabled(not running)
        self._threshold.setEnabled(not running)

    # ------------------------------------------------------------------ slots
    def _on_progress(self, current: int, total: int) -> None:
        if total <= 0:
            self._progress.setRange(0, 0)
            return
        self._progress.setRange(0, total)
        self._progress.setValue(current)

    def _on_error(self, message: str) -> None:
        self._count_label.setText(f"Error: {message}")

    def _on_done(self, processed: int) -> None:
        self._set_running(False)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        # Sort each input row's matches by period, descending (YYYY-MM).
        for i in range(self._tree.topLevelItemCount()):
            parent = self._tree.topLevelItem(i)
            children = parent.takeChildren()
            children.sort(
                key=lambda child: child.text(6), reverse=True)
            parent.addChildren(children)
        # Auto-fit column widths, like double-clicking a header edge.
        for column in range(self._tree.columnCount()):
            self._tree.resizeColumnToContents(column)
        groups = self._tree.topLevelItemCount()
        matches = sum(self._tree.topLevelItem(i).childCount() for i in range(groups))
        self._count_label.setText(
            f"Finished scanning {processed} file(s) · {groups} input row(s) · {matches} match(es)")
        if self._thread is not None:
            self._thread = None

    def _on_match(self, match: BatchMatch) -> None:
        parent = self._group_item(match)
        child = QTreeWidgetItem([
            "", "", "", "", match.matched_by,
            f"{match.similarity:g}", match.period, match.list_folder,
            match.excel_file, match.item, match.cas_no, match.sat_no,
            str(match.row_number),
        ])
        child.setData(0, SOURCE_ROLE, match.source_path)
        child.setToolTip(9, match.item)
        parent.addChild(child)
        parent.setText(3, str(parent.childCount()))

    def _group_item(self, match: BatchMatch) -> QTreeWidgetItem:
        """Return (creating if needed) the group node for an input row."""
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            if int(item.text(0)) == match.input_index:
                return item
        entry = next((r for r in self._input_rows if r.index == match.input_index), None)
        item = QTreeWidgetItem([
            str(match.input_index),
            entry.item if entry else "",
            entry.cas_no if entry else "",
            "0", "", "", "", "", "", "", "", "", "", "", "",
        ])
        item.setToolTip(1, entry.item if entry else "")
        flags = item.flags()
        item.setFlags(flags & ~Qt.ItemFlag.ItemIsSelectable)
        self._tree.addTopLevelItem(item)
        return item

    def _open_row_file(self, item: QTreeWidgetItem, _column: int) -> None:
        path = item.data(0, SOURCE_ROLE)
        if not path:
            return
        if not os.path.isfile(path):
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