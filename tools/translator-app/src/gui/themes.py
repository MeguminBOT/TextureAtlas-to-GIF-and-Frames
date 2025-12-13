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
    QPushButton:disabled {
        background-color: #3a3a3a;
        color: #777777;
        border: 1px solid #4a4a4a;
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
    QComboBox {
        background-color: #454545;
        color: #ffffff;
        border: 1px solid #666666;
        padding: 4px 8px;
        border-radius: 3px;
        min-height: 20px;
    }
    QComboBox:hover {
        background-color: #505050;
        border: 1px solid #777777;
    }
    QComboBox:disabled {
        background-color: #3a3a3a;
        color: #777777;
        border: 1px solid #4a4a4a;
    }
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: right center;
        width: 20px;
        border-left: 1px solid #555555;
        background-color: #505050;
    }
    QComboBox QAbstractItemView {
        background-color: #3a3a3a;
        color: #ffffff;
        selection-background-color: #4a90e2;
        selection-color: #ffffff;
        border: 1px solid #555555;
    }
    QScrollBar:vertical {
        background-color: #2b2b2b;
        width: 12px;
        margin: 0;
        border: none;
    }
    QScrollBar::handle:vertical {
        background-color: #5a5a5a;
        min-height: 30px;
        border-radius: 5px;
        margin: 2px;
    }
    QScrollBar::handle:vertical:hover {
        background-color: #6a6a6a;
    }
    QScrollBar::handle:vertical:pressed {
        background-color: #7a7a7a;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0;
        background: none;
    }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: none;
    }
    QScrollBar:horizontal {
        background-color: #2b2b2b;
        height: 12px;
        margin: 0;
        border: none;
    }
    QScrollBar::handle:horizontal {
        background-color: #5a5a5a;
        min-width: 30px;
        border-radius: 5px;
        margin: 2px;
    }
    QScrollBar::handle:horizontal:hover {
        background-color: #6a6a6a;
    }
    QScrollBar::handle:horizontal:pressed {
        background-color: #7a7a7a;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0;
        background: none;
    }
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
        background: none;
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
    QPushButton:disabled {
        background-color: #e8e8e8;
        color: #a0a0a0;
        border: 1px solid #d0d0d0;
    }
    QCheckBox {
        color: #000000;
    }
    QLabel {
        color: #000000;
    }
    QComboBox {
        background-color: #f8f8f8;
        color: #000000;
        border: 1px solid #b0b0b0;
        padding: 4px 8px;
        border-radius: 3px;
        min-height: 20px;
    }
    QComboBox:hover {
        background-color: #f0f0f0;
        border: 1px solid #909090;
    }
    QComboBox:disabled {
        background-color: #e8e8e8;
        color: #a0a0a0;
        border: 1px solid #d0d0d0;
    }
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: right center;
        width: 20px;
        border-left: 1px solid #c0c0c0;
        background-color: #e8e8e8;
    }
    QComboBox QAbstractItemView {
        background-color: #ffffff;
        color: #000000;
        selection-background-color: #0078d4;
        selection-color: #ffffff;
        border: 1px solid #cccccc;
    }
    QScrollBar:vertical {
        background-color: #f0f0f0;
        width: 12px;
        margin: 0;
        border: none;
    }
    QScrollBar::handle:vertical {
        background-color: #c0c0c0;
        min-height: 30px;
        border-radius: 5px;
        margin: 2px;
    }
    QScrollBar::handle:vertical:hover {
        background-color: #a8a8a8;
    }
    QScrollBar::handle:vertical:pressed {
        background-color: #909090;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0;
        background: none;
    }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: none;
    }
    QScrollBar:horizontal {
        background-color: #f0f0f0;
        height: 12px;
        margin: 0;
        border: none;
    }
    QScrollBar::handle:horizontal {
        background-color: #c0c0c0;
        min-width: 30px;
        border-radius: 5px;
        margin: 2px;
    }
    QScrollBar::handle:horizontal:hover {
        background-color: #a8a8a8;
    }
    QScrollBar::handle:horizontal:pressed {
        background-color: #909090;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0;
        background: none;
    }
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
        background: none;
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
