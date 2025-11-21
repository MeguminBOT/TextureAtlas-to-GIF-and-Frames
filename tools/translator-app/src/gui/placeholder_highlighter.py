from __future__ import annotations

import re

from PySide6.QtGui import QColor, QFont, QTextCharFormat, QSyntaxHighlighter


class PlaceholderHighlighter(QSyntaxHighlighter):
    """Highlight brace-based placeholder tokens in Qt text widgets."""

    def __init__(self, parent=None, dark_mode: bool = False) -> None:
        super().__init__(parent)
        self.dark_mode = dark_mode
        self.placeholder_format = QTextCharFormat()
        self.setup_formats()

    def setup_formats(self) -> None:
        """Configure colors/fonts for the current theme."""
        if self.dark_mode:
            self.placeholder_format.setForeground(QColor(100, 200, 255))
        else:
            self.placeholder_format.setForeground(QColor(0, 100, 200))
        self.placeholder_format.setFontWeight(QFont.Bold)

    def highlightBlock(self, text: str) -> None:  # pragma: no cover - Qt painting
        pattern = r"\{[^}]*\}"
        for match in re.finditer(pattern, text):
            start = match.start()
            length = match.end() - start
            self.setFormat(start, length, self.placeholder_format)

    def set_dark_mode(self, dark_mode: bool) -> None:
        """Switch the highlight palette and refresh the document."""
        self.dark_mode = dark_mode
        self.setup_formats()
        self.rehighlight()


__all__ = ["PlaceholderHighlighter"]
