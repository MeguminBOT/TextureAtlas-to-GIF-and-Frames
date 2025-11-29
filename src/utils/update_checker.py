from itertools import zip_longest
from typing import Any, Dict, List, Optional

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

from version import (
    APP_VERSION,
    GITHUB_RELEASE_BY_TAG_URL,
    GITHUB_TAGS_URL,
    version_to_tuple,
)


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
    """Check GitHub tags to determine whether a newer version exists."""

    def __init__(self, current_version: Optional[str] = None):
        self.current_version = current_version or APP_VERSION

    def check_for_updates(
        self, parent_window=None
    ) -> tuple[bool, str | None, str | None]:
        """Check GitHub for a newer release and prompt the user.

        Fetches the latest release from the GitHub API, compares versions,
        and displays an update dialog if a newer version is available.

        Args:
            parent_window: Parent Qt widget for dialogs.

        Returns:
            tuple: (bool, str, dict | None)
        """

        try:
            tags = self._fetch_tags()
            selected_tag = self._find_newer_tag(tags)
            if not selected_tag:
                return False, self.current_version, None

            tag_name = selected_tag["name"]
            latest_version = tag_name.lstrip("vV")
            release_data = self._fetch_release_for_tag(tag_name)
            changelog = (
                release_data.get("body", "No changelog available.")
                if release_data
                else "No changelog available."
            )

            metadata = {
                "tag_name": tag_name,
                "zipball_url": (release_data or selected_tag).get("zipball_url"),
                "tarball_url": (release_data or selected_tag).get("tarball_url"),
            }

            if not metadata["zipball_url"]:
                QMessageBox.warning(
                    parent_window,
                    "Update Error",
                    "Could not find a downloadable archive for this release.",
                )
                return False, latest_version, None

            update_type = self.determine_update_type(self.current_version, latest_version)
            dialog = UpdateDialog(
                parent_window, self.current_version, latest_version, changelog, update_type
            )
            if dialog.show_dialog():
                return True, latest_version, metadata
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
        """Compare version strings to determine if latest is newer than current."""
        return self._compare_versions(version_to_tuple(latest), version_to_tuple(current)) > 0

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
            current_parts = version_to_tuple(current_version)
            latest_parts = version_to_tuple(latest_version)

            for idx, (latest_val, current_val) in enumerate(
                zip_longest(latest_parts, current_parts, fillvalue=0)
            ):
                if latest_val == current_val:
                    continue
                if idx == 0:
                    return "major"
                if idx == 1:
                    return "minor"
                return "patch"
            return "patch"
        except (ValueError, IndexError):
            return "patch"

    def download_and_install_update(self, update_payload=None, latest_version=None, parent_window=None):
        """Launch the standalone updater process and report success."""
        try:
            from utils.update_installer import UpdateUtilities, launch_external_updater

            exe_mode = UpdateUtilities.is_compiled()
            launch_external_updater(
                release_metadata=update_payload,
                latest_version=latest_version,
                exe_mode=exe_mode,
            )
            return True

        except ImportError:
            QMessageBox.critical(
                parent_window,
                "Update Error",
                "Update installer not available. Please download the update manually.",
            )
        except Exception as e:
            QMessageBox.critical(
                parent_window, "Update Error", f"Failed to start updater:\n{str(e)}"
            )

        return False

    def _fetch_tags(self) -> List[Dict[str, Any]]:
        response = requests.get(GITHUB_TAGS_URL, params={"per_page": 100}, timeout=15)
        response.raise_for_status()
        return response.json()

    def _find_newer_tag(self, tags: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        try:
            current_tuple = version_to_tuple(self.current_version)
        except ValueError:
            current_tuple = (0,)
        newest_tag: Optional[Dict[str, Any]] = None
        newest_tuple: Optional[tuple[int, ...]] = None

        for tag in tags:
            name = tag.get("name") or ""
            try:
                candidate_tuple = version_to_tuple(name)
            except ValueError:
                continue
            if self._compare_versions(candidate_tuple, current_tuple) <= 0:
                continue
            if not newest_tuple or self._compare_versions(candidate_tuple, newest_tuple) > 0:
                newest_tag = tag
                newest_tuple = candidate_tuple

        return newest_tag

    def _fetch_release_for_tag(self, tag_name: str) -> Optional[Dict[str, Any]]:
        response = requests.get(GITHUB_RELEASE_BY_TAG_URL.format(tag=tag_name), timeout=15)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _compare_versions(latest_parts: tuple[int, ...], current_parts: tuple[int, ...]) -> int:
        for latest_val, current_val in zip_longest(latest_parts, current_parts, fillvalue=0):
            if latest_val > current_val:
                return 1
            if latest_val < current_val:
                return -1
        return 0
