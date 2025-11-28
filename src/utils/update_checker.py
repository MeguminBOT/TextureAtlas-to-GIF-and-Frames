"""Application update checking and installation.

Provides dialogs and logic for checking GitHub releases, comparing
versions, and triggering update downloads.
"""

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
    """Dialog displaying update information and changelog.

    Attributes:
        result: User's choice; True to proceed with update, False to cancel.
    """

    def __init__(
        self,
        parent,
        current_version: str,
        latest_version: str,
        changelog: str,
        update_type: str,
    ) -> None:
        """Initialize the update dialog.

        Args:
            parent: Parent widget for dialog positioning.
            current_version: Currently installed version string.
            latest_version: Available version string.
            changelog: Release notes text.
            update_type: One of ``major``, ``minor``, or ``patch``.
        """

        super().__init__(parent)
        self.result = False

        self.setWindowTitle(self.tr("Update Available"))
        self.setFixedSize(600, 500)
        self.setModal(True)

        if parent:
            parent_rect = parent.geometry()
            self.move(
                parent_rect.x() + (parent_rect.width() - 600) // 2,
                parent_rect.y() + (parent_rect.height() - 500) // 2,
            )

        self._create_widgets(current_version, latest_version, changelog, update_type)

    def tr(self, text: str) -> str:
        """Translate text using the application's current locale."""

        from PySide6.QtCore import QCoreApplication

        return QCoreApplication.translate(self.__class__.__name__, text)

    def _create_widgets(
        self,
        current_version: str,
        latest_version: str,
        changelog: str,
        update_type: str,
    ) -> None:
        """Build the dialog UI with version info, changelog, and buttons."""

        layout = QVBoxLayout(self)

        if update_type == "major":
            title_text = "🎉 Major Update Available! 🎉"
            version_text = f"Version {latest_version} is now available!\n(You have version {current_version})"
        elif update_type == "minor":
            title_text = "✨ New Update Available! ✨"
            version_text = f"Version {latest_version} is now available!\n(You have version {current_version})"
        else:
            title_text = "🔧 Bug Fix Update Available"
            version_text = f"Version {latest_version} is now available!\n(You have version {current_version})"

        title_label = QLabel(title_text)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title_label)

        version_label = QLabel(version_text)
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("font-size: 12px; margin-bottom: 15px;")
        layout.addWidget(version_label)

        changelog_label = QLabel("What's New:")
        changelog_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(changelog_label)

        self.changelog_text = QTextEdit()
        self.changelog_text.setPlainText(changelog)
        self.changelog_text.setReadOnly(True)
        layout.addWidget(self.changelog_text)

        button_layout = QHBoxLayout()

        self.update_btn = QPushButton(self.tr("Update Now"))
        self.update_btn.setStyleSheet(
            """
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
        """
        )
        self.update_btn.clicked.connect(self._on_update)

        self.cancel_btn = QPushButton(self.tr("Cancel"))
        self.cancel_btn.setStyleSheet(
            """
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
        """
        )
        self.cancel_btn.clicked.connect(self._on_cancel)

        button_layout.addWidget(self.update_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)

    def show_dialog(self) -> bool:
        """Display the dialog modally and return the user's choice."""

        self.exec()
        return self.result

    def _on_update(self) -> None:
        """Accept the dialog and set result to True."""

        self.result = True
        self.accept()

    def _on_cancel(self) -> None:
        """Reject the dialog and set result to False."""

        self.result = False
        self.reject()


class UpdateChecker:
    """Checks GitHub releases for application updates.

    Attributes:
        current_version: The currently installed version string.
    """

    def __init__(self, current_version: str) -> None:
        """Initialize the update checker.

        Args:
            current_version: The currently installed version string.
        """

        self.current_version = current_version

    def check_for_updates(
        self, parent_window=None
    ) -> tuple[bool, str | None, str | None]:
        """Check GitHub for a newer release and prompt the user.

        Fetches the latest release from the GitHub API, compares versions,
        and displays an update dialog if a newer version is available.

        Args:
            parent_window: Parent Qt widget for dialogs.

        Returns:
            A tuple (proceed, latest_version, download_url) where proceed is
            True if the user accepted the update and a download URL exists.
        """

        try:
            api_url = "https://api.github.com/repos/MeguminBOT/TextureAtlas-to-GIF-and-Frames/releases/latest"

            response = requests.get(api_url, timeout=10)
            response.raise_for_status()

            release_data = response.json()
            latest_version = release_data["tag_name"].lstrip("v")
            changelog = release_data.get("body", "No changelog available.")

            download_url = None
            assets = release_data.get("assets", [])

            system = platform.system().lower()
            for asset in assets:
                name = asset["name"].lower()
                if system == "windows" and "windows" in name and name.endswith(".zip"):
                    download_url = asset["browser_download_url"]
                    break
                elif system == "darwin" and "mac" in name and name.endswith(".zip"):
                    download_url = asset["browser_download_url"]
                    break
                elif system == "linux" and "linux" in name and name.endswith(".zip"):
                    download_url = asset["browser_download_url"]
                    break

            if self._is_newer_version(latest_version, self.current_version):
                update_type = self.determine_update_type(
                    self.current_version, latest_version
                )

                dialog = UpdateDialog(
                    parent_window,
                    self.current_version,
                    latest_version,
                    changelog,
                    update_type,
                )
                if dialog.show_dialog():
                    if download_url:
                        return True, latest_version, download_url
                    else:
                        QMessageBox.warning(
                            parent_window,
                            "Update Error",
                            f"No download available for {platform.system()}.\n"
                            f"Please visit the GitHub releases page to download manually.",
                        )
                        return False, latest_version, None
                else:
                    return False, latest_version, None
            else:
                return False, latest_version, None

        except requests.RequestException as e:
            QMessageBox.critical(
                parent_window,
                "Update Check Failed",
                f"Failed to check for updates:\n{str(e)}",
            )
            return False, None, None
        except Exception as e:
            QMessageBox.critical(
                parent_window,
                "Update Error",
                f"An error occurred while checking for updates:\n{str(e)}",
            )
            return False, None, None

    def _is_newer_version(self, latest: str, current: str) -> bool:
        """Check if latest version is newer than current using semantic versioning."""

        try:
            def version_tuple(version_str: str) -> tuple[int, ...]:
                clean_version = version_str.lstrip("v")
                return tuple(map(int, clean_version.split(".")))

            return version_tuple(latest) > version_tuple(current)
        except (ValueError, AttributeError):
            return False

    def determine_update_type(self, current_version: str, latest_version: str) -> str:
        """Classify an update as major, minor, or patch.

        Uses semantic versioning: major.minor.patch. Compares corresponding
        segments to determine which changed.

        Args:
            current_version: Currently installed version string.
            latest_version: Available version string.

        Returns:
            Update type: ``major``, ``minor``, or ``patch``.
        """

        try:
            def parse_version(version_str: str) -> list[int]:
                clean_version = version_str.lstrip("v")
                parts = clean_version.split(".")
                return [int(part) for part in parts[:3]]

            current_parts = parse_version(current_version)
            latest_parts = parse_version(latest_version)

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
            return "patch"

    def download_and_install_update(
        self, download_url: str, latest_version: str, parent_window=None
    ) -> None:
        """Download and install an update.

        Delegates to :class:`UpdateInstaller` for the actual download and
        installation process.

        Args:
            download_url: URL to download the update archive.
            latest_version: Version string being downloaded.
            parent_window: Parent Qt widget for progress dialogs.
        """

        try:
            from utils.update_installer import UpdateInstaller

            installer = UpdateInstaller()
            installer.download_and_install(download_url, latest_version, parent_window)

        except ImportError:
            QMessageBox.critical(
                parent_window,
                "Update Error",
                "Update installer not available. Please download the update manually.",
            )
        except Exception as e:
            QMessageBox.critical(
                parent_window,
                "Update Error",
                f"Failed to download and install update:\n{str(e)}",
            )
