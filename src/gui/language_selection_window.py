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
        self.setFixedSize(400, 150)

        # Center the window on parent
        if parent:
            self.move(
                parent.x() + (parent.width() - self.width()) // 2,
                parent.y() + (parent.height() - self.height()) // 2,
            )

    def tr(self, text):
        """Translate text using Qt's translation system."""
        return QCoreApplication.translate("LanguageSelectionWindow", text)

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
        self.language_combo.setMinimumWidth(200)
        lang_layout.addWidget(self.language_combo)

        lang_layout.addStretch()
        layout.addLayout(lang_layout)

        # Populate language options
        self.populate_languages()

        # Info label
        self.info_label = QLabel(
            self.tr(
                "Note: The application will need to restart to fully apply the language change."
            )
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
            available_languages = {"en": "English"}

        # Clear existing items
        self.language_combo.clear()

        # Add auto option
        self.language_combo.addItem(self.tr("Auto (System Default)"), "auto")

        # Add separator
        self.language_combo.insertSeparator(1)

        # Add available languages
        current_index = 0
        for lang_code, display_name in available_languages.items():
            self.language_combo.addItem(display_name, lang_code)

            # Select current language
            if lang_code == self.current_language:
                current_index = self.language_combo.count() - 1

        # Handle "auto" selection
        if self.current_language == "auto":
            current_index = 0

        self.language_combo.setCurrentIndex(current_index)

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
            # No change needed
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
        # Get current language from parent if available
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
