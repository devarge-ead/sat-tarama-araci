"""Left sidebar showing the year/month folder tree with checkboxes."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QStyle,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.folder_tree import build_year_folder
from ..core.models import YearFolder

# User roles used to remember what an item represents.
YEAR_INDEX_ROLE = Qt.ItemDataRole.UserRole
MONTH_ROLE = Qt.ItemDataRole.UserRole + 1


class Sidebar(QWidget):
    """A tree of year folders with per-month checkboxes."""

    folders_changed = Signal()  # emitted whenever the folder set changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self._year_folders: list[YearFolder] = []
        self._block = False

        title = QLabel("Archive Folders")
        title.setObjectName("sectionTitle")

        self._update_all = QPushButton("Select All")
        self._update_all.setObjectName("ghostButton")
        self._clear_all = QPushButton("Clear All")
        self._clear_all.setObjectName("ghostButton")
        header_row = QHBoxLayout()
        header_row.addWidget(title)
        header_row.addStretch()
        header_row.addWidget(self._update_all)
        header_row.addWidget(self._clear_all)

        # Management buttons, placed prominently at the top with icons.
        self._add_btn = QPushButton("Add Folder")
        self._add_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder))
        self._edit_btn = QPushButton("Edit")
        self._edit_btn.setObjectName("secondaryButton")
        self._edit_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        self._remove_btn = QPushButton("Remove")
        self._remove_btn.setObjectName("ghostButton")
        self._remove_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))

        self._update_all.clicked.connect(self._select_all)
        self._clear_all.clicked.connect(self._clear_all_folders)
        self._add_btn.clicked.connect(self._add_folder)
        self._edit_btn.clicked.connect(self._edit_folder)
        self._remove_btn.clicked.connect(self._remove_folder)

        buttons = QHBoxLayout()
        buttons.addWidget(self._add_btn, 1)
        buttons.addWidget(self._edit_btn, 1)
        buttons.addWidget(self._remove_btn, 1)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setAnimated(True)
        self._tree.itemChanged.connect(self._on_item_changed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addLayout(header_row)
        layout.addLayout(buttons)
        layout.addWidget(self._tree, 1)
# ------------------------------------------------------------------ model
    def set_year_folders(self, folders: list[YearFolder]) -> None:
        self._year_folders = folders
        self._rebuild()

    def get_year_folders(self) -> list[YearFolder]:
        """Return the current folders with their live checked states."""
        return self._year_folders

    def _rebuild(self) -> None:
        self._block = True
        self._tree.clear()
        for index, folder in enumerate(self._year_folders):
            year_item = QTreeWidgetItem([folder.name])
            year_item.setFlags(year_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            year_item.setData(0, YEAR_INDEX_ROLE, index)
            year_item.setCheckState(0, self._checkbox_state(folder.checked, folder.months))
            year_item.setToolTip(0, str(folder.path))
            for month in folder.months:
                month_item = QTreeWidgetItem([f"{month.number:02d}"])
                month_item.setFlags(month_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                month_item.setData(0, YEAR_INDEX_ROLE, index)
                month_item.setData(0, MONTH_ROLE, month.number)
                month_item.setCheckState(0,
                    Qt.CheckState.Checked if month.checked else Qt.CheckState.Unchecked)
                month_item.setToolTip(0, str(month.path))
                year_item.addChild(month_item)
            year_item.setExpanded(True)
            self._tree.addTopLevelItem(year_item)
        self._block = False

    @staticmethod
    def _checkbox_state(year_checked: bool, months: list) -> Qt.CheckState:
        checked = sum(1 for m in months if m.checked)
        if checked == len(months) and len(months) > 0:
            return Qt.CheckState.Checked
        if checked == 0:
            return Qt.CheckState.Unchecked
        return Qt.CheckState.PartiallyChecked

    # ------------------------------------------------------------ interactions
    def _on_item_changed(self, item: QTreeWidgetItem, _column: int) -> None:
        if self._block:
            return
        index = item.data(0, YEAR_INDEX_ROLE)
        if index is None:
            return
        folder = self._year_folders[index]
        month_number = item.data(0, MONTH_ROLE)
        state = item.checkState(0)

        # Update only the affected checkboxes in place so the tree keeps its
        # current expansion/collapse state (no full rebuild is required).
        self._block = True
        try:
            if month_number is None:
                # A year checkbox toggled: apply the state to all months.
                checked = state == Qt.CheckState.Checked
                folder.checked = checked
                for month in folder.months:
                    month.checked = checked
                item.setCheckState(
                    0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
                for row in range(item.childCount()):
                    item.child(row).setCheckState(
                        0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            else:
                month = next(
                    (m for m in folder.months if m.number == month_number), None)
                if month is not None:
                    month.checked = state == Qt.CheckState.Checked
                    folder.checked = any(m.checked for m in folder.months)
                    parent = item.parent()
                    if parent is not None:
                        parent.setCheckState(
                            0, self._checkbox_state(folder.checked, folder.months))
        finally:
            self._block = False
        self.folders_changed.emit()

    def _select_all(self) -> None:
        self._apply_all(True)

    def _clear_all_folders(self) -> None:
        self._apply_all(False)

    def _apply_all(self, checked: bool) -> None:
        for folder in self._year_folders:
            folder.checked = checked
            for month in folder.months:
                month.checked = checked
        self._rebuild()
        self.folders_changed.emit()

    # ---------------------------------------------------------- folder editing
    def _add_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select a Year Folder")
        if not selected:
            return
        path = Path(selected)
        if any(folder.path == path for folder in self._year_folders):
            QMessageBox.information(self, "Already Added", "This folder is already added.")
            return
        folder = build_year_folder(path)
        if folder is None or not folder.months:
            QMessageBox.warning(
                self,
                "No Months Found",
                "No month folders (matching AY_NO-AY_ADI) were found in the selected folder.",
            )
            return
        if any(existing.name == folder.name for existing in self._year_folders):
            QMessageBox.warning(
                self, "Duplicate Year",
                f"A folder for year {folder.name} is already added.")
            return
        self._year_folders.append(folder)
        self._rebuild()
        self.folders_changed.emit()

    def _edit_folder(self) -> None:
        item = self._tree.currentItem()
        index = item.data(0, YEAR_INDEX_ROLE) if item else None
        if index is None or item.data(0, MONTH_ROLE) is not None:
            self._show_no_year_selected()
            return
        selected = QFileDialog.getExistingDirectory(
            self, "Select the new Year Folder", str(self._year_folders[index].path))
        if not selected:
            return
        path = Path(selected)
        if any(folder.path == path and folder is not self._year_folders[index]
               for folder in self._year_folders):
            QMessageBox.information(self, "Already Added", "This folder is already added.")
            return
        new_folder = build_year_folder(path)
        if new_folder is None or not new_folder.months:
            QMessageBox.warning(
                self, "No Months Found",
                "No month folders were found in the selected folder.")
            return
        new_folder.checked = self._year_folders[index].checked
        if any(existing.name == new_folder.name
               for existing in self._year_folders if existing is not self._year_folders[index]):
            QMessageBox.warning(
                self, "Duplicate Year",
                f"A folder for year {new_folder.name} is already added.")
            return
        self._year_folders[index] = new_folder
        self._rebuild()
        self.folders_changed.emit()

    def _remove_folder(self) -> None:
        item = self._tree.currentItem()
        index = item.data(0, YEAR_INDEX_ROLE) if item else None
        if index is None:
            self._show_no_year_selected()
            return
        self._year_folders.pop(index)
        self._rebuild()
        self.folders_changed.emit()

    def _show_no_year_selected(self) -> None:
        QMessageBox.information(self, "Select a Year", "Please select a year folder first.")