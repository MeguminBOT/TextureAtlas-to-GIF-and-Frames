from __future__ import annotations

import re
from typing import Dict, Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)


class AddLanguageDialog(QDialog):
    """Dialog for adding new language metadata."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Language")
        self._data: Optional[Dict[str, str]] = None

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("e.g. es_mx")
        form.addRow("Code", self.code_edit)

        self.native_name_edit = QLineEdit()
        self.native_name_edit.setPlaceholderText("Native name (e.g. Español)")
        form.addRow("Native Name", self.native_name_edit)

        self.english_name_edit = QLineEdit()
        self.english_name_edit.setPlaceholderText("English name (e.g. Spanish)")
        form.addRow("English Name", self.english_name_edit)

        self.quality_combo = QComboBox()
        self.quality_combo.addItem("Machine (auto)", "machine")
        self.quality_combo.addItem("Native (human)", "native")
        self.quality_combo.addItem("Unknown", "unknown")
        form.addRow("Quality", self.quality_combo)

        layout.addLayout(form)

        helper = QLabel("Language codes should match Qt expectations (e.g. en, es_mx, fr_ca).")
        helper.setWordWrap(True)
        layout.addWidget(helper)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._handle_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.code_edit.setFocus()

    def _handle_accept(self) -> None:
        code = self.code_edit.text().strip().lower()
        if not code:
            QMessageBox.warning(self, "Missing Code", "Enter a language code before continuing.")
            return
        if not re.fullmatch(r"[a-z0-9_\-]+", code):
            QMessageBox.warning(
                self, "Invalid Code", "Language codes may use letters, numbers, '_' or '-'."
            )
            return

        native_name = self.native_name_edit.text().strip() or code
        english_name = self.english_name_edit.text().strip() or native_name
        quality = self.quality_combo.currentData()

        self._data = {
            "code": code,
            "native_name": native_name,
            "english_name": english_name,
            "quality": quality,
        }
        self.accept()

    def get_data(self) -> Optional[Dict[str, str]]:
        return self._data


__all__ = ["AddLanguageDialog"]
