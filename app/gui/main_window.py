"""Main application window wiring together the sidebar, search and results."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..core import searcher
from ..core.folder_tree import build_year_folder
from ..core.models import YearFolder
from ..storage import settings as settings_store
from ..storage.settings import YearConfig
from .batch_panel import BatchPanel
from .results_table import ResultsTable
from .search_panel import SearchPanel
from .sidebar import Sidebar

MIN_WIDTH = 1100
MIN_HEIGHT = 640


def icon_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "assets" / "app.ico"


class MainWindow(QMainWindow):
    """Top-level window of the SAT Tarama Aracı."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = settings_store.load()
        self._thread = None

        self.setWindowTitle("SAT Tarama Aracı")
        self.setMinimumSize(QSize(MIN_WIDTH, MIN_HEIGHT))

        self.sidebar = Sidebar()
        self.search_panel = SearchPanel()
        self.results_table = ResultsTable()
        self._rebuild_sidebar_from_settings()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_sidebar_widget())
        splitter.addWidget(self._build_right_widget())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([330, 780])

        self.setCentralWidget(splitter)
        self._build_status_bar()

        self._connect_signals()
        self._apply_restored_state()

    # ------------------------------------------------------------------ layout
    def _build_sidebar_widget(self) -> QWidget:
        title = QLabel("SAT Tarama Aracı")
        title.setObjectName("titleLabel")
        subtitle = QLabel("Search SAT requests inside archived Excel lists")
        subtitle.setObjectName("subtitleLabel")
        header = QVBoxLayout()
        header.setSpacing(2)
        header.addWidget(title)
        header.addWidget(subtitle)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addLayout(header)
        layout.addWidget(self.sidebar, 1)
        widget.setFixedWidth(330)
        return widget

    def _build_right_widget(self) -> QWidget:
        # Manual search tab: parameters + results table (existing layout).
        manual_tab = QWidget()
        layout = QVBoxLayout(manual_tab)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setSpacing(10)
        layout.addWidget(self.search_panel)
        layout.addWidget(self.results_table, 1)

        # Batch search tab: input file picker + grouped results.
        self.batch_panel = BatchPanel(lambda: self.sidebar.get_year_folders())
        batch_tab = QWidget()
        batch_layout = QVBoxLayout(batch_tab)
        batch_layout.setContentsMargins(10, 12, 10, 10)
        batch_layout.setSpacing(10)
        batch_layout.addWidget(self.batch_panel, 1)

        tabs = QTabWidget()
        tabs.addTab(manual_tab, "Manual Search")
        tabs.addTab(batch_tab, "Batch Search")

        widget = QWidget()
        outer = QVBoxLayout(widget)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(10)
        outer.addWidget(tabs, 1)
        return widget

    def _build_status_bar(self) -> None:
        bar = QStatusBar()
        self._status = QLabel("Ready")
        bar.addWidget(self._status)
        self.setStatusBar(bar)

    # ------------------------------------------------------------------ wiring
    def _connect_signals(self) -> None:
        self.sidebar.folders_changed.connect(self._persist_settings)
        self.search_panel.start_search_requested.connect(self._start_search)
        self.search_panel.cancel_requested.connect(self._cancel_search)

    # ---------------------------------------------------------------- settings
    def _rebuild_sidebar_from_settings(self) -> None:
        year_folders: list[YearFolder] = []
        for config in self._settings.years:
            folder = build_year_folder(Path(config.path))
            if folder is None or not folder.months:
                continue
            folder.checked = config.checked
            unchecked = set(config.unchecked_months)
            for month in folder.months:
                if month.number in unchecked:
                    month.checked = False
            year_folders.append(folder)
        self.sidebar.set_year_folders(year_folders)

    def _persist_settings(self) -> None:
        self._settings.years = self._make_year_configs()
        settings_store.save(self._settings)

    # ------------------------------------------------------------------ search
    def _start_search(self) -> None:
        parameters = self.search_panel.parameters()
        if not any(parameters.values()):
            QMessageBox.warning(
                self, "No Search Terms",
                "Please fill in at least one search parameter before searching.")
            return

        year_folders = self.sidebar.get_year_folders()
        selected = [
            folder for folder in year_folders
            if folder.checked and any(month.checked for month in folder.months)
        ]
        if not selected:
            QMessageBox.warning(
                self, "No Folders Selected",
                "Please select at least one year/month folder to search.")
            return

        criteria = searcher.build_criteria(parameters)
        self._persist_settings()

        self.results_table.clear()
        self.search_panel.set_running(True)
        self._status.setText("Searching...")

        self._thread = searcher.SearchThread(selected, criteria, self)
        self._thread.progress.connect(self._on_progress)
        self._thread.result_found.connect(self.results_table.add_result)
        self._thread.error.connect(self._on_scan_error)
        self._thread.finished_search.connect(self._on_search_done)
        self._thread.start()

    def _cancel_search(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            self._thread.cancel()
            self._status.setText("Cancelling...")

    # ------------------------------------------------------------- thread slots
    def _on_progress(self, current: int, total: int) -> None:
        self.search_panel.set_progress(current, total)

    def _on_scan_error(self, message: str) -> None:
        self._status.setText(f"Error: {message}")

    def _on_search_done(self, processed: int) -> None:
        self.search_panel.set_running(False)
        self.search_panel.reset_progress()
        self.results_table.fit_columns()
        count = len(self.results_table.results())
        self._status.setText(f"Finished scanning {processed} file(s) · {count} match(es)")
        if self._thread is not None:
            self._thread = None

    # ------------------------------------------------------------ window state
    def _apply_restored_state(self) -> None:
        self.setWindowState(Qt.WindowState.WindowMaximized)

    def _store_window_state(self) -> None:
        self._settings.window_geometry = {
            "x": self.x(),
            "y": self.y(),
            "width": self.width(),
            "height": self.height(),
        }

    # -------------------------------------------------------------- serializing
    def _make_year_configs(self) -> list[YearConfig]:
        configs: list[YearConfig] = []
        for folder in self.sidebar.get_year_folders():
            configs.append(YearConfig(
                path=str(folder.path),
                checked=folder.checked,
                unchecked_months=[m.number for m in folder.months if not m.checked],
            ))
        return configs

    def persist_now(self) -> None:
        """Persist the full current state (used when the window closes)."""
        self._settings.years = self._make_year_configs()
        # Search inputs are intentionally not persisted; they start empty.
        self._settings.last_search = {}
        self._store_window_state()
        settings_store.save(self._settings)

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        if self._thread is not None and self._thread.isRunning():
            self._thread.cancel()
            self._thread.wait(5000)
        self.batch_panel.cancel_search()
        self.persist_now()
        super().closeEvent(event)