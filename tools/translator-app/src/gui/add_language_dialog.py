"""Dialog for adding or editing language metadata in the translator registry."""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QLocale
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


def _build_locale_list() -> List[Tuple[str, str, str]]:
    """Build a list of all available locales from Qt.

    Returns:
        List of (code, native_name, english_name) tuples, sorted by English name.
    """
    locales: Dict[str, Tuple[str, str, str]] = {}

    for language in QLocale.Language:
        if language == QLocale.Language.AnyLanguage:
            continue
        if language == QLocale.Language.C:
            continue

        # Get countries for this language (use countriesForLanguage for compatibility)
        countries = QLocale.countriesForLanguage(language)

        if not countries:
            # Language without specific country
            locale = QLocale(language)
            code = locale.name().lower().replace("-", "_")
            if not code or code == "c":
                continue
            native_name = locale.nativeLanguageName()
            english_name = QLocale.languageToString(language)
            if native_name and english_name:
                locales[code] = (code, native_name, english_name)
        else:
            for country in countries:
                if country == QLocale.Country.AnyCountry:
                    continue
                locale = QLocale(language, country)
                code = locale.name().lower().replace("-", "_")
                if not code or code == "c":
                    continue
                native_name = locale.nativeLanguageName()
                country_native = locale.nativeCountryName()
                english_name = QLocale.languageToString(language)
                country_english = QLocale.countryToString(country)

                # For display, include country if there are multiple
                if len(countries) > 1 and country_native:
                    display_native = f"{native_name} ({country_native})"
                else:
                    display_native = native_name

                if len(countries) > 1 and country_english:
                    display_english = f"{english_name} ({country_english})"
                else:
                    display_english = english_name

                if display_native and display_english:
                    locales[code] = (code, display_native, display_english)

    # Sort by English name
    result = sorted(locales.values(), key=lambda x: x[2].lower())
    return result


# Cache the locale list since it's expensive to build
_LOCALE_CACHE: Optional[List[Tuple[str, str, str]]] = None


def get_locale_list() -> List[Tuple[str, str, str]]:
    """Get the cached locale list, building it if needed."""
    global _LOCALE_CACHE
    if _LOCALE_CACHE is None:
        _LOCALE_CACHE = _build_locale_list()
    return _LOCALE_CACHE


class AddLanguageDialog(QDialog):
    """Dialog for adding or editing language metadata.

    Uses Qt's QLocale to provide comboboxes for language selection.
    Changing either the native name or English name dropdown will
    automatically update the other and set the language code.

    Attributes:
        code_edit: Line edit for the language code (auto-filled or manual).
        native_name_combo: Combo box for selecting by native name.
        english_name_combo: Combo box for selecting by English name.
        quality_combo: Combo box for quality flag selection.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        initial_data: Optional[Dict[str, str]] = None,
        code_editable: bool = True,
    ) -> None:
        """Initialize the dialog.

        Args:
            parent: Parent widget.
            initial_data: Existing language metadata to populate fields.
            code_editable: If False, the code field is read-only (edit mode).
        """
        super().__init__(parent)
        self._data: Optional[Dict[str, str]] = None
        self._code_editable = code_editable
        self._initial = initial_data or {}
        self._updating = False  # Prevent recursive updates
        self.setWindowTitle("Edit Language" if initial_data else "Add Language")

        layout = QVBoxLayout(self)
        form = QFormLayout()

        # Build locale lookup maps
        self._locales = get_locale_list()
        self._code_to_index: Dict[str, int] = {}
        self._native_to_index: Dict[str, int] = {}
        self._english_to_index: Dict[str, int] = {}

        for i, (code, native, english) in enumerate(self._locales):
            self._code_to_index[code] = i
            self._native_to_index[native] = i
            self._english_to_index[english] = i

        # Native name combobox (searchable)
        self.native_name_combo = QComboBox()
        self.native_name_combo.setEditable(True)
        self.native_name_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.native_name_combo.setMaxVisibleItems(15)
        self.native_name_combo.addItem("-- Select Language --", "")
        for code, native, english in self._locales:
            self.native_name_combo.addItem(native, code)
        form.addRow("Native Name", self.native_name_combo)

        # English name combobox (searchable)
        self.english_name_combo = QComboBox()
        self.english_name_combo.setEditable(True)
        self.english_name_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.english_name_combo.setMaxVisibleItems(15)
        self.english_name_combo.addItem("-- Select Language --", "")
        for code, native, english in self._locales:
            self.english_name_combo.addItem(english, code)
        form.addRow("English Name", self.english_name_combo)

        # Connect signals after populating to avoid premature triggering
        self.native_name_combo.currentIndexChanged.connect(self._on_native_changed)
        self.english_name_combo.currentIndexChanged.connect(self._on_english_changed)

        # Language code (auto-filled, but can be edited for custom codes)
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("Auto-filled from selection, or enter custom")
        if not code_editable:
            self.code_edit.setReadOnly(True)
        form.addRow("Code", self.code_edit)

        # Quality selection
        self.quality_combo = QComboBox()
        self.quality_combo.addItem("Machine (auto-translated)", "machine")
        self.quality_combo.addItem("Unreviewed (human, not reviewed)", "unreviewed")
        self.quality_combo.addItem("Reviewed (checked by reviewer)", "reviewed")
        self.quality_combo.addItem("Native (approved by native speakers)", "native")
        self.quality_combo.addItem("Unknown", "unknown")
        self.quality_combo.setToolTip(
            "Translation quality level:\n"
            "• Machine: Auto-translated, no human review\n"
            "• Unreviewed: Human translated but not yet reviewed\n"
            "• Reviewed: Checked by at least one reviewer\n"
            "• Native: Approved by multiple native speakers\n"
            "• Unknown: Quality status not determined"
        )
        form.addRow("Quality", self.quality_combo)

        layout.addLayout(form)

        helper = QLabel(
            "Select a language from the dropdowns, or type to search. "
            "The code will be auto-filled but can be customized if needed."
        )
        helper.setWordWrap(True)
        layout.addWidget(helper)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._handle_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._apply_initial_data()
        self.native_name_combo.setFocus()

    def _on_native_changed(self, index: int) -> None:
        """Handle native name selection change."""
        if self._updating or index <= 0:
            return
        self._updating = True
        try:
            code = self.native_name_combo.currentData()
            if code and code in self._code_to_index:
                locale_index = self._code_to_index[code]
                # Block signals to prevent cascading updates
                self.english_name_combo.blockSignals(True)
                self.english_name_combo.setCurrentIndex(locale_index + 1)
                self.english_name_combo.blockSignals(False)
                self.code_edit.setText(code)
        finally:
            self._updating = False

    def _on_english_changed(self, index: int) -> None:
        """Handle English name selection change."""
        if self._updating or index <= 0:
            return
        self._updating = True
        try:
            code = self.english_name_combo.currentData()
            if code and code in self._code_to_index:
                locale_index = self._code_to_index[code]
                # Block signals to prevent cascading updates
                self.native_name_combo.blockSignals(True)
                self.native_name_combo.setCurrentIndex(locale_index + 1)
                self.native_name_combo.blockSignals(False)
                self.code_edit.setText(code)
        finally:
            self._updating = False

    def _handle_accept(self) -> None:
        """Validate inputs and store result data on acceptance."""
        code = self.code_edit.text().strip().lower()
        if not code:
            QMessageBox.warning(
                self, "Missing Code", "Select a language or enter a code."
            )
            return
        if self._code_editable and not re.fullmatch(r"[a-z0-9_\-]+", code):
            QMessageBox.warning(
                self,
                "Invalid Code",
                "Language codes may use letters, numbers, '_' or '-'.",
            )
            return

        # Get names from combos or use code as fallback
        native_idx = self.native_name_combo.currentIndex()
        english_idx = self.english_name_combo.currentIndex()

        if native_idx > 0:
            native_name = self.native_name_combo.currentText()
        else:
            native_name = code

        if english_idx > 0:
            english_name = self.english_name_combo.currentText()
        else:
            english_name = native_name

        quality = self.quality_combo.currentData()

        self._data = {
            "code": code,
            "native_name": native_name,
            "english_name": english_name,
            "quality": quality,
        }
        self.accept()

    def get_data(self) -> Optional[Dict[str, str]]:
        """Return the entered language data, or None if cancelled."""
        return self._data

    def _apply_initial_data(self) -> None:
        """Populate form fields with initial data if provided."""
        if not self._initial:
            return

        code = self._initial.get("code", "")
        self.code_edit.setText(code)

        # Block signals during initial data population
        self.native_name_combo.blockSignals(True)
        self.english_name_combo.blockSignals(True)

        # Try to find matching locale by code
        if code and code in self._code_to_index:
            locale_index = self._code_to_index[code]
            self.native_name_combo.setCurrentIndex(locale_index + 1)
            self.english_name_combo.setCurrentIndex(locale_index + 1)
        else:
            # Custom code - try to find by name
            native = self._initial.get("native_name", "")
            english = self._initial.get("english_name", "")

            if native and native in self._native_to_index:
                self.native_name_combo.setCurrentIndex(
                    self._native_to_index[native] + 1
                )
            if english and english in self._english_to_index:
                self.english_name_combo.setCurrentIndex(
                    self._english_to_index[english] + 1
                )

        self.native_name_combo.blockSignals(False)
        self.english_name_combo.blockSignals(False)

        quality_value = self._initial.get("quality")
        if quality_value:
            index = self.quality_combo.findData(quality_value)
            if index >= 0:
                self.quality_combo.setCurrentIndex(index)


__all__ = ["AddLanguageDialog"]
