"""Central color palette and the application style sheet."""

from __future__ import annotations

PRIMARY = "#053c5a"
PRIMARY_LIGHT = "#0b6d9c"
PRIMARY_LIGHTER = "#0f86bd"
PRIMARY_PALE = "#e3f0f7"
PRIMARY_FADED = "#f3f9fc"
BACKGROUND = "#ffffff"
TEXT = "#1f2d3a"
TEXT_MUTED = "#6a7a87"
BORDER = "#d7e1e8"
DANGER = "#c44536"
SUCCESS = "#2e7d52"
DISABLED_TEXT = "#9aa8b2"

DESIGN_SIZE = 9


def style_sheet() -> str:
    """Return the application-wide Qt style sheet."""
    return f"""
    QMainWindow, QDialog {{
        background-color: {BACKGROUND};
    }}
    QWidget {{
        background-color: {BACKGROUND};
        color: {TEXT};
        font-size: {DESIGN_SIZE + 1}pt;
    }}
    QLabel {{
        color: {TEXT};
        font-size: {DESIGN_SIZE + 1}pt;
    }}
    QLabel#titleLabel {{
        font-size: 14pt;
        font-weight: 700;
        color: {PRIMARY};
    }}
    QLabel#subtitleLabel {{
        color: {TEXT_MUTED};
        font-size: 9pt;
    }}
    QLabel#sectionTitle {{
        font-size: 10pt;
        font-weight: 700;
        color: {PRIMARY};
        padding: 2px 0;
    }}
    QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox, QDateEdit {{
        background-color: {BACKGROUND};
        border: 1px solid {BORDER};
        border-radius: 4px;
        padding: 4px 6px;
        selection-background-color: {PRIMARY};
        selection-color: white;
    }}
    QLineEdit:focus, QComboBox:focus {{
        border: 1px solid {PRIMARY_LIGHTER};
    }}
    QLineEdit:disabled, QComboBox:disabled {{
        background-color: {PRIMARY_FADED};
        color: {DISABLED_TEXT};
    }}
    QPushButton {{
        background-color: {PRIMARY};
        color: white;
        border: none;
        border-radius: 4px;
        padding: 6px 14px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: {PRIMARY_LIGHT};
    }}
    QPushButton:pressed {{
        background-color: {PRIMARY_LIGHTER};
    }}
    QPushButton:disabled {{
        background-color: #9fb2bd;
        color: #eef3f6;
    }}
    QPushButton#secondaryButton {{
        background-color: {PRIMARY_PALE};
        color: {PRIMARY};
        border: 1px solid {PRIMARY_LIGHT};
    }}
    QPushButton#secondaryButton:hover {{
        background-color: {PRIMARY_FADED};
    }}
    QPushButton#ghostButton {{
        background-color: transparent;
        color: {PRIMARY};
        border: 1px solid {BORDER};
    }}
    QPushButton#ghostButton:hover {{
        background-color: {PRIMARY_PALE};
    }}
    QTreeWidget {{
        background-color: {BACKGROUND};
        border: 1px solid {BORDER};
        border-radius: 4px;
        outline: none;
    }}
    QTreeWidget::item {{
        padding: 3px 2px;
    }}
    QTreeWidget::item:selected {{
        background-color: {PRIMARY_PALE};
        color: {PRIMARY};
    }}
    QTreeWidget::item:hover {{
        background-color: {PRIMARY_FADED};
    }}
    QTreeWidget::branch:has-children {{
        border-image: none;
    }}
    QHeaderView::section {{
        background-color: {PRIMARY};
        color: white;
        border: none;
        padding: 6px 8px;
        font-weight: 600;
    }}
    QTableWidget {{
        background-color: {BACKGROUND};
        border: 1px solid {BORDER};
        border-radius: 4px;
        gridline-color: {BORDER};
        alternate-background-color: {PRIMARY_FADED};
        selection-background-color: {PRIMARY_PALE};
        selection-color: {PRIMARY};
    }}
    QTableWidget::item {{
        padding: 4px 6px;
    }}
    QProgressBar {{
        border: 1px solid {BORDER};
        border-radius: 4px;
        background-color: {PRIMARY_FADED};
        text-align: center;
        min-height: 12px;
    }}
    QProgressBar::chunk {{
        background-color: {PRIMARY_LIGHTER};
        border-radius: 3px;
    }}
    QStatusBar {{
        background-color: {PRIMARY_PALE};
        color: {TEXT_MUTED};
        border-top: 1px solid {BORDER};
    }}
    QGroupBox {{
        border: 1px solid {BORDER};
        border-radius: 6px;
        margin-top: 10px;
        padding-top: 6px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 8px;
        padding: 0 4px;
        color: {PRIMARY};
        font-weight: 600;
    }}
    QToolTip {{
        background-color: {PRIMARY};
        color: white;
        border: none;
        padding: 4px;
    }}
    QScrollBar:vertical, QScrollBar:horizontal {{
        background: {PRIMARY_FADED};
        border: 1px solid {BORDER};
        margin: 0;
    }}
    QScrollBar:vertical {{
        width: 14px;
    }}
    QScrollBar:horizontal {{
        height: 14px;
    }}
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
        background: {PRIMARY_LIGHT};
        border-radius: 6px;
        margin: 2px;
        min-height: 24px;
        min-width: 24px;
    }}
    QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{
        background: {PRIMARY_LIGHTER};
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{
        height: 0;
        width: 0;
    }}
    QScrollBar::add-page, QScrollBar::sub-page {{
        background: {PRIMARY_FADED};
    }}
    QCheckBox {{
        spacing: 5px;
    }}
    QCheckBox::indicator {{
        width: 14px;
        height: 14px;
    }}
    QRadioButton {{
        spacing: 6px;
        background-color: transparent;
        color: {TEXT};
    }}
    QRadioButton:focus {{
        outline: none;
    }}
    QRadioButton::indicator {{
        width: 15px;
        height: 15px;
        border: 1px solid {BORDER};
        border-radius: 8px;
        background-color: {BACKGROUND};
    }}
    QRadioButton::indicator:checked {{
        border: 1px solid {BORDER};
        background-color: qradialgradient(
            cx: 0.5, cy: 0.5,
            radius: 0.5,
            fx: 0.5, fy: 0.5,
            stop: 0.40 {PRIMARY},
            stop: 0.55 {BACKGROUND}
        );
    }}
    QRadioButton:disabled {{
        color: {DISABLED_TEXT};
    }}
    QRadioButton::indicator:disabled {{
        border: 1px solid {BORDER};
    }}
    QTabWidget::pane {{
        border: 1px solid {BORDER};
        border-radius: 4px;
        background: #ffffff;
        top: -1px;
    }}
    QTabBar::tab {{
        background: {PRIMARY_FADED};
        color: {PRIMARY};
        border: 1px solid {BORDER};
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        padding: 6px 20px;
        margin-right: 3px;
        font-weight: 600;
    }}
    QTabBar::tab:selected {{
        background: {PRIMARY};
        color: #ffffff;
    }}
    QTabBar::tab:hover:!selected {{
        background: {PRIMARY_LIGHTER};
    }}
    QTabWidget::pane > QWidget {{
        padding: 4px;
    }}
    """