"""Application-wide Qt stylesheets for dark and light themes.

Provides ready-to-apply stylesheets that give the translator application a
consistent look in either dark or light mode.
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

_DARK_THEME_QSS = """
    QMainWindow {
        background-color: #2b2b2b;
        color: #ffffff;
    }
    QWidget {
        background-color: #2b2b2b;
        color: #ffffff;
    }
    QTextEdit {
        background-color: #3a3a3a;
        color: #ffffff;
        border: 1px solid #555555;
    }
    QLineEdit {
        background-color: #3a3a3a;
        color: #ffffff;
        border: 1px solid #555555;
        padding: 2px;
    }
    QListWidget {
        background-color: #3a3a3a;
        color: #ffffff;
        border: 1px solid #555555;
        selection-background-color: #4a90e2;
        selection-color: #ffffff;
    }
    QListWidget::item {
        padding: 5px;
        border-bottom: 1px solid #555555;
        background-color: #3a3a3a;
    }
    QListWidget::item:alternate {
        background-color: #404040;
    }
    QListWidget::item:selected {
        background-color: #4a90e2 !important;
        color: #ffffff !important;
    }
    QListWidget::item:hover {
        background-color: #4a4a4a;
    }
    QListWidget::item:selected:hover {
        background-color: #5aa0f2 !important;
        color: #ffffff !important;
    }
    QGroupBox {
        color: #ffffff;
        border: 2px solid #555555;
        border-radius: 5px;
        margin-top: 1ex;
        font-weight: bold;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px 0 5px;
    }
    QPushButton {
        background-color: #4a4a4a;
        color: #ffffff;
        border: 1px solid #666666;
        padding: 5px 10px;
        border-radius: 3px;
    }
    QPushButton:hover {
        background-color: #5a5a5a;
    }
    QPushButton:pressed {
        background-color: #3a3a3a;
    }
    QCheckBox {
        color: #ffffff;
    }
    QLabel {
        color: #ffffff;
    }
    QStatusBar {
        background-color: #2b2b2b;
        color: #ffffff;
    }
    QMenuBar {
        background-color: #2b2b2b;
        color: #ffffff;
    }
    QMenuBar::item:selected {
        background-color: #4a4a4a;
    }
    QMenu {
        background-color: #3a3a3a;
        color: #ffffff;
        border: 1px solid #555555;
    }
    QMenu::item:selected {
        background-color: #4a4a4a;
    }
    QScrollArea {
        background-color: #3a3a3a;
        border: 1px solid #555555;
    }
"""

_LIGHT_THEME_QSS = """
    QMainWindow {
        background-color: #ffffff;
        color: #000000;
    }
    QWidget {
        background-color: #ffffff;
        color: #000000;
    }
    QTextEdit {
        background-color: #ffffff;
        color: #000000;
        border: 1px solid #cccccc;
    }
    QLineEdit {
        background-color: #ffffff;
        color: #000000;
        border: 1px solid #cccccc;
        padding: 2px;
    }
    QListWidget {
        background-color: #ffffff;
        color: #000000;
        border: 1px solid #cccccc;
        selection-background-color: #0078d4;
        selection-color: #ffffff;
    }
    QListWidget::item {
        padding: 5px;
        border-bottom: 1px solid #eeeeee;
        color: #000000;
        background-color: #ffffff;
    }
    QListWidget::item:alternate {
        background-color: #f8f8f8;
    }
    QListWidget::item:selected {
        background-color: #0078d4 !important;
        color: #ffffff !important;
    }
    QListWidget::item:hover {
        background-color: #f0f0f0;
        color: #000000;
    }
    QListWidget::item:selected:hover {
        background-color: #106ebe !important;
        color: #ffffff !important;
    }
    QGroupBox {
        color: #000000;
        border: 2px solid #cccccc;
        border-radius: 5px;
        margin-top: 1ex;
        font-weight: bold;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px 0 5px;
    }
    QPushButton {
        background-color: #f0f0f0;
        color: #000000;
        border: 1px solid #cccccc;
        padding: 5px 10px;
        border-radius: 3px;
    }
    QPushButton:hover {
        background-color: #e0e0e0;
    }
    QPushButton:pressed {
        background-color: #d0d0d0;
    }
    QCheckBox {
        color: #000000;
    }
    QLabel {
        color: #000000;
    }
"""


def apply_app_theme(widget: QWidget, *, dark_mode: bool) -> None:
    """Apply the dark or light stylesheet to the given widget.

    Args:
        widget: The top-level widget (usually QMainWindow) to style.
        dark_mode: If True, apply the dark theme; otherwise light.
    """
    widget.setStyleSheet(_DARK_THEME_QSS if dark_mode else _LIGHT_THEME_QSS)


def theme_stylesheet(*, dark_mode: bool) -> str:
    """Return the raw stylesheet string for the requested theme.

    Args:
        dark_mode: If True, return the dark stylesheet; otherwise light.

    Returns:
        The complete QSS stylesheet as a string.
    """
    return _DARK_THEME_QSS if dark_mode else _LIGHT_THEME_QSS


__all__ = ["apply_app_theme", "theme_stylesheet"]
