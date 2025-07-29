#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QWidget,
    QPushButton,
    QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class SettingsWindow(QDialog):
    """
    A window for displaying user-overridden animation and spritesheet settings.

    This class creates a Qt dialog that lists all animation-specific and spritesheet-specific settings
    currently set by the user, allowing for easy inspection of overrides compared to global settings.
    """

    def __init__(self, parent, settings_manager):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.setWindowTitle(self.tr("Current Settings Overview"))
        self.setModal(True)
        self.resize(450, 350)

        # Create main layout
        main_layout = QVBoxLayout(self)

        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Create scrollable content widget
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Populate the settings
        self.update_settings()

        # Set scroll area widget
        scroll_area.setWidget(self.content_widget)
        main_layout.addWidget(scroll_area)

        # Add close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_button = QPushButton(self.tr("Close"))
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)

        main_layout.addLayout(button_layout)

    def tr(self, text):
        """Translation helper method."""
        from PySide6.QtCore import QCoreApplication

        return QCoreApplication.translate(self.__class__.__name__, text)

    def update_settings(self):
        """Populate the window with the current animation and spritesheet settings."""
        # Clear existing content
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Animation Settings Section
        animation_label = QLabel(self.tr("Animation Settings"))
        animation_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        animation_label.setStyleSheet("QLabel { color: #2E86AB; margin: 10px 0 5px 0; }")
        self.content_layout.addWidget(animation_label)

        if self.settings_manager.animation_settings:
            for key, value in self.settings_manager.animation_settings.items():
                setting_label = QLabel(self.tr("  {key}: {value}").format(key=key, value=value))
                setting_label.setStyleSheet("QLabel { margin-left: 20px; }")
                self.content_layout.addWidget(setting_label)
        else:
            no_settings_label = QLabel(self.tr("  No animation-specific settings configured"))
            no_settings_label.setStyleSheet(
                "QLabel { margin-left: 20px; color: #777; font-style: italic; }"
            )
            self.content_layout.addWidget(no_settings_label)

        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("QFrame { margin: 10px 0; }")
        self.content_layout.addWidget(separator)

        # Spritesheet Settings Section
        spritesheet_label = QLabel(self.tr("Spritesheet Settings"))
        spritesheet_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        spritesheet_label.setStyleSheet("QLabel { color: #A23B72; margin: 10px 0 5px 0; }")
        self.content_layout.addWidget(spritesheet_label)

        if self.settings_manager.spritesheet_settings:
            for key, value in self.settings_manager.spritesheet_settings.items():
                setting_label = QLabel(self.tr("  {key}: {value}").format(key=key, value=value))
                setting_label.setStyleSheet("QLabel { margin-left: 20px; }")
                self.content_layout.addWidget(setting_label)
        else:
            no_settings_label = QLabel(self.tr("  No spritesheet-specific settings configured"))
            no_settings_label.setStyleSheet(
                "QLabel { margin-left: 20px; color: #777; font-style: italic; }"
            )
            self.content_layout.addWidget(no_settings_label)

        # Add stretch to push content to top
        self.content_layout.addStretch()
