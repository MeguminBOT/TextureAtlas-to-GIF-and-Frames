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

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QApplication)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class ErrorDialogWithLinks(QDialog):
    """Qt dialog for displaying error messages with clickable links."""
    
    def __init__(self, message: str, links: List[Tuple[str, str]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Error")
        self.setFixedSize(400, 300)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        # Center the dialog
        if parent:
            self.move(parent.geometry().center() - self.rect().center())
        
        self.setup_ui(message, links)
    
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
            link_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            link_label.setFont(QFont("Arial", 10, QFont.Weight.Normal))
            layout.addWidget(link_label)
        
        layout.addStretch()
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        close_btn.setFixedWidth(100)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)


class DependenciesChecker:
    """
    A Qt-compatible class to check and configure dependencies.

    Methods:
        show_error_popup_with_links(message, links):
            Displays an error message in a Qt popup window with clickable links.
        check_imagemagick():
            Checks if ImageMagick is installed on the system.
        configure_imagemagick():
            Configures the environment to use a bundled version of ImageMagick.
        check_and_configure_imagemagick():
            Checks if ImageMagick is installed and configures it if not found.
    """

    @staticmethod
    def show_error_popup_with_links(message: str, links: List[Tuple[str, str]], parent=None):
        """
        Display an error message in a Qt popup window with clickable links.
        
        Args:
            message: The error message to display
            links: List of (link_text, link_url) tuples
            parent: Optional parent widget
        """
        try:
            # Find the main window if parent is not provided
            if parent is None:
                app = QApplication.instance()
                if app:
                    for widget in app.topLevelWidgets():
                        if widget.isMainWindow():
                            parent = widget
                            break
            
            dialog = ErrorDialogWithLinks(message, links, parent)
            dialog.exec()
        except Exception as e:
            print(f"Error showing error dialog: {e}")
            # Fallback to console output
            print(f"Error: {message}")
            for link_text, link_url in links:
                print(f"Link: {link_text} - {link_url}")

    @staticmethod
    def check_imagemagick():
        """
        Check if ImageMagick is installed on the system.
        
        Returns:
            bool: True if ImageMagick is found, False otherwise
        """
        try:
            # Try to find magick command
            if shutil.which("magick"):
                return True
            
            # Also try convert command for older ImageMagick versions
            if shutil.which("convert"):
                return True
            
            return False
        except Exception:
            return False

    @staticmethod
    def configure_imagemagick():
        """
        Configure the environment to use a bundled version of ImageMagick.
        
        This method sets up the PATH environment variable to include the
        bundled ImageMagick directory if it exists.
        """
        try:
            # Get the directory where the main script is located
            script_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Go up two levels to get to the project root
            project_root = os.path.dirname(os.path.dirname(script_dir))
            
            # Look for bundled ImageMagick
            imagemagick_dir = os.path.join(project_root, "ImageMagick")
            
            if os.path.exists(imagemagick_dir):
                # Add ImageMagick directory to PATH
                current_path = os.environ.get("PATH", "")
                if imagemagick_dir not in current_path:
                    os.environ["PATH"] = f"{imagemagick_dir}{os.pathsep}{current_path}"
                    print(f"Added {imagemagick_dir} to PATH")
                    return True
            
            return False
        except Exception as e:
            print(f"Error configuring ImageMagick: {e}")
            return False

    @staticmethod
    def check_and_configure_imagemagick():
        """
        Check if ImageMagick is installed and configure it if not found.
        
        This method first checks if ImageMagick is available in the system PATH.
        If not found, it tries to configure a bundled version.
        If still not found, it shows an error dialog with download links.
        
        Returns:
            bool: True if ImageMagick is available, False otherwise
        """
        try:
            # First check if ImageMagick is already available
            if DependenciesChecker.check_imagemagick():
                return True
            
            # Try to configure bundled version
            if DependenciesChecker.configure_imagemagick():
                # Check again after configuration
                if DependenciesChecker.check_imagemagick():
                    return True
            
            # If still not found, show error dialog
            system = platform.system().lower()
            
            message = (
                "ImageMagick is required but not found on your system.\n\n"
                "Please download and install ImageMagick from one of the links below, "
                "then restart the application."
            )
            
            if system == "windows":
                links = [
                    ("Download ImageMagick for Windows", "https://imagemagick.org/script/download.php#windows"),
                    ("Alternative: Install via Chocolatey", "https://chocolatey.org/packages/imagemagick")
                ]
            elif system == "darwin":  # macOS
                links = [
                    ("Download ImageMagick for macOS", "https://imagemagick.org/script/download.php#macosx"),
                    ("Alternative: Install via Homebrew", "https://formulae.brew.sh/formula/imagemagick")
                ]
            else:  # Linux and others
                links = [
                    ("Download ImageMagick for Linux", "https://imagemagick.org/script/download.php#unix"),
                    ("Ubuntu/Debian: apt install imagemagick", "https://packages.ubuntu.com/imagemagick"),
                    ("CentOS/RHEL: yum install ImageMagick", "https://centos.pkgs.org/7/centos-x86_64/ImageMagick-6.7.8.9-18.el7.x86_64.rpm.html")
                ]
            
            DependenciesChecker.show_error_popup_with_links(message, links)
            return False
            
        except Exception as e:
            print(f"Error in check_and_configure_imagemagick: {e}")
            return False

        root.mainloop()

    @staticmethod
    def check_imagemagick():
        return shutil.which("magick") is not None

    @staticmethod
    def configure_imagemagick():
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
        if DependenciesChecker.check_imagemagick():
            print("Using the user's existing ImageMagick.")
            return

        if platform.system() == "Windows":
            print("System ImageMagick not found. Attempting to configure bundled version.")
            try:
                DependenciesChecker.configure_imagemagick()
                print("Configured bundled ImageMagick.")
                return
            except Exception as e:
                print(f"Failed to configure bundled ImageMagick: {e}")

        msg = (
            "ImageMagick not found or failed to initialize.\n\nMake sure you followed install steps correctly.\n"
            "If the issue persists, install ImageMagick manually."
        )
        links = [
            (
                "Installation Steps",
                "https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/wiki/Installation",
            ),
            ("Install ImageMagick", "https://imagemagick.org/script/download.php"),
        ]
        DependenciesChecker.show_error_popup_with_links(msg, links)
        raise Exception(msg)
