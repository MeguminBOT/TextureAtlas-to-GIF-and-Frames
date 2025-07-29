#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QCheckBox
from PySide6.QtCore import Qt, QSettings


class MachineTranslationDisclaimerDialog(QDialog):
    """
    Dialog to show machine translation disclaimers to users.
    """

    def __init__(self, parent=None, language_name="", disclaimer_title="", disclaimer_message=""):
        super().__init__(parent)
        self.language_name = language_name
        self.disclaimer_title = disclaimer_title
        self.disclaimer_message = disclaimer_message
        self.setup_ui()

    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle(self.disclaimer_title)
        self.setModal(True)
        self.resize(500, 300)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Header with icon and title
        header_layout = QHBoxLayout()
        
        # Robot icon for machine translation
        icon_label = QLabel()
        icon_label.setText("🤖")  # Robot emoji
        icon_label.setStyleSheet("font-size: 32px;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFixedSize(48, 48)
        header_layout.addWidget(icon_label)
        
        # Title
        title_label = QLabel(f"{self.disclaimer_title}\n{self.language_name}")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-left: 10px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Disclaimer message
        message_text = QTextEdit()
        message_text.setPlainText(self.disclaimer_message)
        message_text.setReadOnly(True)
        message_text.setMaximumHeight(120)
        message_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid palette(mid);
                padding: 8px;
                background-color: palette(base);
                color: palette(text);
                border-radius: 4px;
            }
        """)
        layout.addWidget(message_text)
        
        # Don't show again checkbox
        self.dont_show_checkbox = QCheckBox(self.tr("Don't show this disclaimer again for this language"))
        layout.addWidget(self.dont_show_checkbox)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # GitHub button (optional)
        github_button = QPushButton(self.tr("View on GitHub"))
        github_button.clicked.connect(self.open_github)
        button_layout.addWidget(github_button)
        
        # OK button
        ok_button = QPushButton(self.tr("OK"))
        ok_button.setDefault(True)
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)
        
        layout.addLayout(button_layout)

    def tr(self, text):
        """Translate text using Qt's translation system."""
        from PySide6.QtCore import QCoreApplication
        return QCoreApplication.translate("MachineTranslationDisclaimerDialog", text)

    def open_github(self):
        """Open the GitHub repository for translation contributions."""
        import webbrowser
        webbrowser.open("https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames")

    def should_save_preference(self):
        """Check if the user doesn't want to see this disclaimer again."""
        return self.dont_show_checkbox.isChecked()

    @staticmethod
    def should_show_disclaimer(language_code):
        """Check if we should show the disclaimer for a language."""
        settings = QSettings()
        return not settings.value(f"translations/hide_disclaimer_{language_code}", False, type=bool)

    @staticmethod
    def set_disclaimer_preference(language_code, hide=True):
        """Save the user's preference about showing the disclaimer."""
        settings = QSettings()
        settings.setValue(f"translations/hide_disclaimer_{language_code}", hide)

    @staticmethod
    def show_machine_translation_disclaimer(parent, translation_manager, language_code, language_name):
        """
        Show machine translation disclaimer if needed.
        
        Args:
            parent: Parent widget
            translation_manager: Translation manager instance
            language_code: Language code being switched to
            language_name: Display name of the language
            
        Returns:
            bool: True if user accepted, False if cancelled
        """
        # Check if we should show the disclaimer
        if not MachineTranslationDisclaimerDialog.should_show_disclaimer(language_code):
            return True
            
        # Check if the language is machine translated
        if not translation_manager.is_machine_translated(language_code):
            return True
            
        # Get disclaimer text
        title, message = translation_manager.get_machine_translation_disclaimer()
        
        # Show the dialog
        dialog = MachineTranslationDisclaimerDialog(parent, language_name, title, message)
        result = dialog.exec()
        
        # Save preference if requested
        if dialog.should_save_preference():
            MachineTranslationDisclaimerDialog.set_disclaimer_preference(language_code, True)
            
        return result == QDialog.DialogCode.Accepted
