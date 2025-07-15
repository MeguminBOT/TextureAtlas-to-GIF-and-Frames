#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QMessageBox,
)
from PySide6.QtCore import QCoreApplication


class LanguageSelectionWindow(QDialog):
    """
    A dialog window for selecting the application language.

    This window displays available languages with their native names, English names,
    and quality indicators:

    Quality Indicators:
    - ✅ Native: Highest quality (human-reviewed, native speakers)
    - 👥 Community: Good quality community contributions
    - 🤖 Machine: Machine translated (may contain inaccuracies)
    - ⚠️ Partial: Incomplete translation (some text still in English)
    """

    def __init__(self, parent=None, current_language="en"):
        super().__init__(parent)
        self.parent_window = parent
        self.current_language = current_language
        self.new_language = current_language

        self.setup_ui()
        self.setup_connections()

        # Set window properties
        self.setWindowTitle(self.tr("Language Settings"))
        self.setModal(True)
        self.setFixedSize(500, 300)  # Increased size for custom translation section

        # Center the window on parent
        if parent:
            self.move(
                parent.x() + (parent.width() - self.width()) // 2,
                parent.y() + (parent.height() - self.height()) // 2,
            )

    def tr(self, text):
        """Translate text using Qt's translation system."""
        return QCoreApplication.translate("LanguageSelectionWindow", text)

    def _format_language_display_name(self, native_name, english_name):
        """
        Format a language display name, handling existing parentheses smartly.

        Args:
            native_name (str): Native language name (may contain parentheses)
            english_name (str): English language name

        Returns:
            str: Properly formatted display name
        """
        if not english_name or english_name == native_name:
            return native_name

        # Check if native name already contains the English name
        if english_name.lower() in native_name.lower():
            return native_name

        # Always use forward slash for consistency
        return f"{native_name} / {english_name}"

    def get_auto_detected_language(self):
        """
        Get the auto-detected language based on system locale.
        Returns the system locale language if available, otherwise returns 'en'.
        """
        # Get translation manager
        translation_manager = None
        if self.parent_window and hasattr(self.parent_window, "translation_manager"):
            translation_manager = self.parent_window.translation_manager
        else:
            try:
                from utils.translation_manager import get_translation_manager

                translation_manager = get_translation_manager()
            except ImportError:
                return "en"

        if not translation_manager:
            return "en"

        # Get system locale
        system_locale = translation_manager.get_system_locale()

        # Get available languages
        available_languages = translation_manager.get_available_languages()

        # Check if system locale is available
        if system_locale in available_languages:
            return system_locale

        # If not available, default to English
        return "en"

    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title label
        title_label = QLabel(self.tr("Select Application Language"))
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)

        # Language selection
        lang_layout = QHBoxLayout()

        self.language_label = QLabel(self.tr("Language:"))
        lang_layout.addWidget(self.language_label)

        self.language_combo = QComboBox()
        self.language_combo.setMinimumWidth(280)  # Increased width for native + English names
        lang_layout.addWidget(self.language_combo)

        lang_layout.addStretch()
        layout.addLayout(lang_layout)

        # Populate language options
        self.populate_languages()

        # Info label
        self.info_label = QLabel(
            self.tr(
                "Note: The application may need to be restarted to fully apply the language change.\n"
                "Auto detects your system language and falls back to English if unavailable.\n"
                "Quality indicators: {native} Native, {community} Community, {machine} Machine, {partial} Partial"
            ).format(native="✅", community="👥", machine="🤖", partial="⚠️")
        )
        self.info_label.setStyleSheet("color: #666; font-size: 10px;")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_button = QPushButton(self.tr("Cancel"))
        self.cancel_button.setMinimumWidth(80)
        button_layout.addWidget(self.cancel_button)

        self.apply_button = QPushButton(self.tr("Apply"))
        self.apply_button.setMinimumWidth(80)
        self.apply_button.setDefault(True)
        button_layout.addWidget(self.apply_button)

        layout.addLayout(button_layout)

    def setup_connections(self):
        """Set up signal-slot connections."""
        self.language_combo.currentTextChanged.connect(self.on_language_changed)
        self.cancel_button.clicked.connect(self.reject)
        self.apply_button.clicked.connect(self.apply_language_change)

    def populate_languages(self):
        """Populate the language combobox with available languages."""
        if self.parent_window and hasattr(self.parent_window, "get_available_languages"):
            available_languages = self.parent_window.get_available_languages()
        else:
            # Fallback if parent doesn't have the method
            available_languages = {
                "en": {"name": "English", "english_name": "English", "quality": "native"},
                "pt_br": {"name": "Portuguese (Brazil)", "english_name": "Portuguese (Brazil)", "quality": "native"},
                "sv": {"name": "Svenska", "english_name": "Swedish", "quality": "native"},
            }

        # Get translation manager for helper methods
        translation_manager = None
        if self.parent_window and hasattr(self.parent_window, "translation_manager"):
            translation_manager = self.parent_window.translation_manager
        else:
            try:
                from utils.translation_manager import get_translation_manager

                translation_manager = get_translation_manager()
            except ImportError:
                pass

        # Clear existing items
        self.language_combo.clear()

        # Add auto option with detected language info
        auto_detected_lang = self.get_auto_detected_language()
        auto_detected_display = "English"  # Default fallback

        # Get display name for auto-detected language
        if translation_manager:
            auto_detected_display = translation_manager.get_display_name(auto_detected_lang)
        elif auto_detected_lang in available_languages:
            lang_info = available_languages[auto_detected_lang]
            if isinstance(lang_info, dict):
                auto_detected_display = lang_info.get("name", auto_detected_lang)

        auto_display_text = self.tr("Auto (System Default): {language}").format(
            language=auto_detected_display
        )
        self.language_combo.addItem(auto_display_text, "auto")

        # Add separator
        self.language_combo.insertSeparator(1)

        # Add available languages
        for lang_code, lang_info in available_languages.items():
            if isinstance(lang_info, dict):
                # Use translation manager helper methods if available
                if translation_manager:
                    display_name = translation_manager.get_display_name(
                        lang_code, show_english=True
                    )
                    quality = translation_manager.get_quality_level(lang_code)
                else:
                    # Fallback to manual construction
                    native_name = lang_info.get("name", lang_code)
                    english_name = lang_info.get("english_name", "")
                    quality = lang_info.get("quality", "unknown")

                    if english_name and lang_code != "en":
                        display_name = self._format_language_display_name(native_name, english_name)
                    else:
                        display_name = native_name

                # Add quality indicator at the front
                if quality == "native":
                    display_name = f"✅ {display_name}"
                elif quality == "community":
                    display_name = f"👥 {display_name}"
                elif quality == "machine":
                    display_name = f"🤖 {display_name}"
                elif quality == "partial":
                    display_name = f"⚠️ {display_name}"
            else:
                # Fallback for old string format
                display_name = lang_info

            self.language_combo.addItem(display_name, lang_code)

        # Set the current selection based on current_language
        # Search through all items to find the matching data value
        selection_index = 0  # Default to auto
        for i in range(self.language_combo.count()):
            item_data = self.language_combo.itemData(i)
            if item_data == self.current_language:
                selection_index = i
                break

        self.language_combo.setCurrentIndex(selection_index)

    def on_language_changed(self):
        """Handle language selection change."""
        self.new_language = self.language_combo.currentData()

    def apply_language_change(self):
        """Apply the language change."""
        if self.new_language != self.current_language:
            try:
                if self.parent_window and hasattr(self.parent_window, "change_language"):
                    self.parent_window.change_language(self.new_language)
                    self.accept()
                else:
                    QMessageBox.warning(
                        self,
                        self.tr("Error"),
                        self.tr("Could not change language: Parent window not available"),
                    )
            except Exception as e:
                QMessageBox.warning(
                    self, self.tr("Error"), self.tr("Failed to change language: {}").format(str(e))
                )
        else:
            self.accept()


def show_language_selection(parent=None):
    """
    Show the language selection dialog.

    Args:
        parent: Parent window

    Returns:
        bool: True if language was changed, False otherwise
    """
    try:
        current_language = "en"
        if parent and hasattr(parent, "app_config"):
            current_language = parent.app_config.get_language()

        dialog = LanguageSelectionWindow(parent, current_language)
        result = dialog.exec()

        return result == QDialog.DialogCode.Accepted

    except Exception as e:
        if parent:
            from PySide6.QtCore import QCoreApplication

            error_msg = QCoreApplication.translate(
                "LanguageSelectionWindow", "Could not open language selection: {error}"
            ).format(error=str(e))
            QMessageBox.warning(
                parent, QCoreApplication.translate("LanguageSelectionWindow", "Error"), error_msg
            )
        return False
