#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Qt-compatible Dependencies Checker
Replaces the tkinter-dependent dependencies_checker.py with a Qt implementation.
"""

import shutil
import os
import platform
from typing import List, Tuple

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QApplication,
    QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# Import utilities
from utils.utilities import Utilities


class ErrorDialogWithLinks(QDialog):
    """Qt dialog for displaying error messages with clickable links."""

    def __init__(self, message: str, links: List[Tuple[str, str]], parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Error"))
        self.setFixedSize(400, 300)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        # Center the dialog
        if parent:
            self.move(parent.geometry().center() - self.rect().center())

        self.setup_ui(message, links)

    def tr(self, text):
        """Translation helper method."""
        from PySide6.QtCore import QCoreApplication
        return QCoreApplication.translate(self.__class__.__name__, text)


    def setup_ui(self, message: str, links: List[Tuple[str, str]]):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Message label
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(msg_label)

        # Links
        for link_text, link_url in links:
            link_label = QLabel(f'<a href="{link_url}">{link_text}</a>')
            link_label.setOpenExternalLinks(True)
            link_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            layout.addWidget(link_label)

        # Spacer
        layout.addStretch()

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        ok_button.setFixedWidth(80)
        button_layout.addWidget(ok_button)

        layout.addLayout(button_layout)


class DependenciesChecker:
    """Qt-compatible dependencies checker for the application."""

    @staticmethod
    def show_error_popup_with_links(message: str, links: List[Tuple[str, str]], parent=None):
        """
        Shows an error popup with clickable links using Qt.

        Args:
            message: Error message to display
            links: List of (link_text, link_url) tuples
            parent: Parent widget for the dialog
        """
        # Ensure we have a QApplication instance
        app = QApplication.instance()
        if app is None:
            app = QApplication([])

        dialog = ErrorDialogWithLinks(message, links, parent)
        dialog.exec()

    @staticmethod
    def show_error_popup(message: str, parent=None):
        """
        Shows a simple error popup using Qt.

        Args:
            message: Error message to display
            parent: Parent widget for the dialog
        """
        # Ensure we have a QApplication instance
        app = QApplication.instance()
        if app is None:
            app = QApplication([])

        QMessageBox.critical(parent, "Error", message)

    @staticmethod
    def check_imagemagick():
        """Check if ImageMagick is available in the system."""
        return shutil.which("magick") is not None

    @staticmethod
    def configure_imagemagick():
        """Configure bundled ImageMagick by setting environment variables."""
        imagemagick_path = Utilities.find_root("ImageMagick")
        if imagemagick_path is None:
            raise FileNotFoundError("Could not find 'ImageMagick' folder in any parent directory.")

        dll_path = os.path.join(imagemagick_path, "ImageMagick")
        if not os.path.isdir(dll_path):
            raise FileNotFoundError(
                f"Expected ImageMagick folder but couldn't be found at: {dll_path}"
            )

        os.environ["PATH"] = dll_path + os.pathsep + os.environ.get("PATH", "")
        os.environ["MAGICK_HOME"] = dll_path
        os.environ["MAGICK_CODER_MODULE_PATH"] = dll_path

        print(f"Using bundled ImageMagick from: {dll_path}")

    @staticmethod
    def check_and_configure_imagemagick():
        """
        Check for ImageMagick and configure bundled version if needed.

        Returns:
            bool: True if ImageMagick is available, False otherwise
        """
        if DependenciesChecker.check_imagemagick():
            print("Using the user's existing ImageMagick.")
            return True

        if platform.system() == "Windows":
            print("System ImageMagick not found. Attempting to configure bundled version.")
            try:
                DependenciesChecker.configure_imagemagick()
                print("Configured bundled ImageMagick.")
                return True
            except Exception as e:
                print(f"Failed to configure bundled ImageMagick: {e}")

        # Show error message with platform-specific links
        msg = (
            "ImageMagick not found or failed to initialize.\n\n"
            "Make sure you followed install steps correctly.\n"
            "If the issue persists, install ImageMagick manually."
        )

        if platform.system() == "Windows":
            links = [
                (
                    "App Installation Steps",
                    "https://textureatlastoolbox.com/installation.html",
                ),
                (
                    "Download ImageMagick for Windows",
                    "https://imagemagick.org/script/download.php#windows",
                ),
                (
                    "ImageMagick Windows Binary",
                    "https://download.imagemagick.org/ImageMagick/download/binaries/",
                ),
            ]
        elif platform.system() == "Darwin":  # macOS
            links = [
                (
                    "App Installation Steps",
                    "https://textureatlastoolbox.com/installation.html",
                ),
                (
                    "Download ImageMagick for macOS",
                    "https://imagemagick.org/script/download.php#macosx",
                ),
                ("Install via Homebrew: brew install imagemagick", "https://brew.sh/"),
            ]
        else:  # Linux and others
            links = [
                (
                    "App Installation Steps",
                    "https://textureatlastoolbox.com/installation.html",
                ),
                (
                    "Download ImageMagick for Linux",
                    "https://imagemagick.org/script/download.php#unix",
                ),
                (
                    "Ubuntu/Debian command: sudo apt install imagemagick",
                    "https://packages.ubuntu.com/imagemagick",
                ),
            ]

        DependenciesChecker.show_error_popup_with_links(msg, links)
        return False
