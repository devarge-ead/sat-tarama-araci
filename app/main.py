"""Application entry point for the SAT Tarama Aracı."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .gui import theme
from .gui.main_window import MainWindow, icon_path


def main() -> int:
    """Create the application, apply styling, and start the event loop."""
    app = QApplication(sys.argv)
    app.setApplicationName("SAT Tarama Aracı")
    app.setOrganizationName("SAT")

    icon = icon_path()
    if icon.is_file():
        app.setWindowIcon(QIcon(str(icon)))

    app.setStyleSheet(theme.style_sheet())

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())