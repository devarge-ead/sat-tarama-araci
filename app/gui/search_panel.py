"""Search parameters panel and the Start/Cancel controls."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..core import searcher
from ..core.searcher import SEARCH_MODE_SIMILARITY, SEARCH_MODE_SUBSTRING

# Search fields in display order; keys used to persist user input.
SEARCH_FIELDS = [
    ("project_code", "Project Code"),
    ("project_name", "Project Name"),
    ("demanded_by", "Demanded By"),
    ("item", "Item"),
    ("cas_no", "CAS No"),
    ("sat_no", "SAT No"),
]


class SearchPanel(QWidget):
    """Compact form holding the five optional search parameters."""

    start_search_requested = Signal()
    cancel_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._edits: dict[str, QLineEdit] = {}

        # One row of equal-width fields, label above the input.
        fields_row = QHBoxLayout()
        fields_row.setSpacing(8)
        for field_key, label in SEARCH_FIELDS:
            field_box = QVBoxLayout()
            field_box.setSpacing(2)
            lbl = QLabel(label)
            edit = QLineEdit()
            edit.setPlaceholderText(label)
            self._edits[field_key] = edit
            field_box.addWidget(lbl)
            field_box.addWidget(edit)
            fields_row.addLayout(field_box, 1)

        # Search method selection: substring (default) or advanced similarity.
        self._substring_radio = QRadioButton("Substring Match")
        self._substring_radio.setChecked(True)
        self._similarity_radio = QRadioButton("Similarity Match")

        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self._substring_radio)
        self._mode_group.addButton(self._similarity_radio)

        self._threshold = QSpinBox()
        self._threshold.setRange(0, 100)
        self._threshold.setValue(80)
        self._threshold.setSuffix(" %")
        self._threshold.setEnabled(False)
        self._threshold_label = QLabel("Similarity Threshold:")

        method_row = QHBoxLayout()
        method_row.setSpacing(8)
        method_row.addWidget(self._substring_radio)
        method_row.addWidget(self._similarity_radio)
        method_row.addStretch()
        method_row.addWidget(self._threshold_label)
        method_row.addWidget(self._threshold)

        self._substring_radio.toggled.connect(self._on_method_toggled)

        self._start_btn = QPushButton("Start Search")
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setObjectName("ghostButton")
        self._cancel_btn.setEnabled(False)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        self._progress.setFixedHeight(16)

        self._start_btn.clicked.connect(self.start_search_requested.emit)
        self._cancel_btn.clicked.connect(self.cancel_requested.emit)

        button_row = QHBoxLayout()
        button_row.addWidget(self._start_btn)
        button_row.addWidget(self._cancel_btn)
        button_row.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addLayout(fields_row)
        layout.addLayout(method_row)
        layout.addWidget(self._progress)
        layout.addLayout(button_row)

    # ------------------------------------------------------------------ api
    def _on_method_toggled(self, checked: bool) -> None:
        """Enable/disable the threshold control for the similarity method."""
        self._threshold.setEnabled(self._similarity_radio.isChecked())
        self._threshold_label.setEnabled(self._similarity_radio.isChecked())

    def mode(self) -> str:
        """Return the selected search method key."""
        return SEARCH_MODE_SIMILARITY if self._similarity_radio.isChecked() \
            else SEARCH_MODE_SUBSTRING

    def similarity_threshold(self) -> float:
        """Return the similarity threshold percentage."""
        return float(self._threshold.value())

    def parameters(self) -> dict[str, str]:
        """Return the current values of every search field."""
        return {key: edit.text().strip() for key, edit in self._edits.items()}

    def set_parameters(self, values: dict[str, str]) -> None:
        for key, edit in self._edits.items():
            if key in values:
                edit.setText(values[key])

    def has_any_value(self) -> bool:
        return any(self.parameters().values())

    def set_running(self, running: bool) -> None:
        """Toggle the widget state while a search is in progress."""
        self._start_btn.setEnabled(not running)
        self._cancel_btn.setEnabled(running)
        for edit in self._edits.values():
            edit.setEnabled(not running)
        self._substring_radio.setEnabled(not running)
        self._similarity_radio.setEnabled(not running)
        if running:
            self._threshold.setEnabled(False)
            self._threshold_label.setEnabled(False)
        else:
            self._threshold.setEnabled(self._similarity_radio.isChecked())
            self._threshold_label.setEnabled(self._similarity_radio.isChecked())

    def set_progress(self, current: int, total: int) -> None:
        if total <= 0:
            self._progress.setRange(0, 0)
            self._progress.setValue(0)
            return
        self._progress.setRange(0, total)
        self._progress.setValue(current)

    def reset_progress(self) -> None:
        self._progress.setRange(0, 100)
        self._progress.setValue(0)