import platform
import requests

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QMessageBox,
)
from PySide6.QtCore import Qt


class UpdateDialog(QDialog):
    """
    A custom dialog window for displaying update information with changelog.

    Attributes:
        result (bool): The user's choice (True for update, False for cancel)

    Methods:
        __init__(parent, current_version, latest_version, changelog, update_type):
            Initialize the update dialog with version info and changelog
        show_dialog():
            Display the dialog and return the user's choice
        _on_update():
            Handle the update button click
        _on_cancel():
            Handle the cancel button click
    """

    def __init__(self, parent, current_version, latest_version, changelog, update_type):
        super().__init__(parent)
        self.result = False

        self.setWindowTitle(self.tr("Update Available"))
        self.setFixedSize(600, 500)
        self.setModal(True)

        # Center the dialog
        if parent:
            parent_rect = parent.geometry()
            self.move(
                parent_rect.x() + (parent_rect.width() - 600) // 2,
                parent_rect.y() + (parent_rect.height() - 500) // 2,
            )

        self._create_widgets(current_version, latest_version, changelog, update_type)

    def tr(self, text):
        """Translation helper method."""
        from PySide6.QtCore import QCoreApplication

        return QCoreApplication.translate(self.__class__.__name__, text)

    def _create_widgets(self, current_version, latest_version, changelog, update_type):
        layout = QVBoxLayout(self)

        # Header
        if update_type == "major":
            title_text = "🎉 Major Update Available! 🎉"
            version_text = (
                f"Version {latest_version} is now available!\n(You have version {current_version})"
            )
        elif update_type == "minor":
            title_text = "✨ New Update Available! ✨"
            version_text = (
                f"Version {latest_version} is now available!\n(You have version {current_version})"
            )
        else:  # patch
            title_text = "🔧 Bug Fix Update Available"
            version_text = (
                f"Version {latest_version} is now available!\n(You have version {current_version})"
            )

        title_label = QLabel(title_text)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title_label)

        version_label = QLabel(version_text)
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("font-size: 12px; margin-bottom: 15px;")
        layout.addWidget(version_label)

        # Changelog
        changelog_label = QLabel("What's New:")
        changelog_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(changelog_label)

        self.changelog_text = QTextEdit()
        self.changelog_text.setPlainText(changelog)
        self.changelog_text.setReadOnly(True)
        layout.addWidget(self.changelog_text)

        # Buttons
        button_layout = QHBoxLayout()

        self.update_btn = QPushButton(self.tr("Update Now"))
        self.update_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.update_btn.clicked.connect(self._on_update)

        self.cancel_btn = QPushButton(self.tr("Cancel"))
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        self.cancel_btn.clicked.connect(self._on_cancel)

        button_layout.addWidget(self.update_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)

    def show_dialog(self):
        """Display the dialog and return the user's choice."""
        self.exec()
        return self.result

    def _on_update(self):
        """Handle the update button click."""
        self.result = True
        self.accept()

    def _on_cancel(self):
        """Handle the cancel button click."""
        self.result = False
        self.reject()


class UpdateChecker:
    """
    A class for checking and managing updates.

    Methods:
        check_for_updates():
            Check if a new version is available.
        get_current_version():
            Get the current version from the app.
        download_and_install_update(download_url, latest_version):
            Download and install the latest version.
        run_update_installer(installer_path, latest_version):
            Run the update installer.
        determine_update_type(current_version, latest_version):
            Determine if the update is major, minor, or patch.
    """

    def __init__(self, current_version):
        self.current_version = current_version

    def check_for_updates(self, parent_window=None):
        """
        Check if a new version is available and show update dialog if needed.

        Args:
            parent_window: Parent Qt window for the dialog

        Returns:
            tuple: (bool, str, str) - (update_available, latest_version, download_url)
        """
        try:
            api_url = "https://api.github.com/repos/MeguminBOT/TextureAtlas-to-GIF-and-Frames/releases/latest"

            response = requests.get(api_url, timeout=10)
            response.raise_for_status()

            release_data = response.json()
            latest_version = release_data["tag_name"].lstrip("v")
            changelog = release_data.get("body", "No changelog available.")

            if self._is_newer_version(latest_version, self.current_version):
                update_type = self.determine_update_type(self.current_version, latest_version)

                # Show update dialog
                dialog = UpdateDialog(
                    parent_window, self.current_version, latest_version, changelog, update_type
                )
                if dialog.show_dialog():
                    return True, latest_version, None
                return False, latest_version, None
            else:
                return False, latest_version, None

        except requests.RequestException as e:
            QMessageBox.critical(
                parent_window, "Update Check Failed", f"Failed to check for updates:\n{str(e)}"
            )
            return False, None, None
        except Exception as e:
            QMessageBox.critical(
                parent_window,
                "Update Error",
                f"An error occurred while checking for updates:\n{str(e)}",
            )
            return False, None, None

    def _is_newer_version(self, latest, current):
        """Compare version strings to determine if latest is newer than current."""
        try:

            def version_tuple(version_str):
                # Remove 'v' prefix if present and split by '.'
                clean_version = version_str.lstrip("v")
                return tuple(map(int, clean_version.split(".")))

            return version_tuple(latest) > version_tuple(current)
        except (ValueError, AttributeError):
            return False

    def determine_update_type(self, current_version, latest_version):
        """
        Determine the type of update (major, minor, patch) based on semantic versioning.

        Args:
            current_version (str): Current version string
            latest_version (str): Latest version string

        Returns:
            str: Update type ('major', 'minor', or 'patch')
        """
        try:

            def parse_version(version_str):
                clean_version = version_str.lstrip("v")
                parts = clean_version.split(".")
                return [int(part) for part in parts[:3]]  # Take only major.minor.patch

            current_parts = parse_version(current_version)
            latest_parts = parse_version(latest_version)

            # Pad with zeros if necessary
            while len(current_parts) < 3:
                current_parts.append(0)
            while len(latest_parts) < 3:
                latest_parts.append(0)

            if latest_parts[0] > current_parts[0]:
                return "major"
            elif latest_parts[1] > current_parts[1]:
                return "minor"
            else:
                return "patch"

        except (ValueError, IndexError):
            return "patch"  # Default to patch if version parsing fails

    def download_and_install_update(self, download_url=None, latest_version=None, parent_window=None):
        """
        Download and install the update.

        Args:
            download_url (str): URL to download the update
            latest_version (str): Version being downloaded
            parent_window: Parent Qt window for dialogs
        """
        try:
            from utils.update_installer import UpdateInstaller

            installer = UpdateInstaller(parent_window)
            installer.download_and_install(download_url, latest_version, parent_window)

        except ImportError:
            QMessageBox.critical(
                parent_window,
                "Update Error",
                "Update installer not available. Please download the update manually.",
            )
        except Exception as e:
            QMessageBox.critical(
                parent_window, "Update Error", f"Failed to download and install update:\n{str(e)}"
            )
