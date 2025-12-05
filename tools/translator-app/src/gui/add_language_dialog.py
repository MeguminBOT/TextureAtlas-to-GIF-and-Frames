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
    """Dialog for adding or editing language metadata."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        initial_data: Optional[Dict[str, str]] = None,
        code_editable: bool = True,
    ) -> None:
        super().__init__(parent)
        self._data: Optional[Dict[str, str]] = None
        self._code_editable = code_editable
        self._initial = initial_data or {}
        self.setWindowTitle("Edit Language" if initial_data else "Add Language")

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("e.g. es_mx")
        if not code_editable:
            self.code_edit.setReadOnly(True)
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

        self._apply_initial_data()
        if self._initial:
            self.native_name_edit.setFocus()
        else:
            self.code_edit.setFocus()

    def _handle_accept(self) -> None:
        code = self.code_edit.text().strip().lower()
        if not code:
            QMessageBox.warning(self, "Missing Code", "Enter a language code before continuing.")
            return
        if self._code_editable and not re.fullmatch(r"[a-z0-9_\-]+", code):
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

    def _apply_initial_data(self) -> None:
        if not self._initial:
            return
        self.code_edit.setText(self._initial.get("code", ""))
        self.native_name_edit.setText(self._initial.get("native_name", ""))
        self.english_name_edit.setText(self._initial.get("english_name", ""))
        quality_value = self._initial.get("quality")
        if quality_value:
            index = self.quality_combo.findData(quality_value)
            if index >= 0:
                self.quality_combo.setCurrentIndex(index)


__all__ = ["AddLanguageDialog"]
