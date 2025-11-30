#!/usr/bin/env python3
"""Download, apply, and verify application updates.

This module provides both a standalone entry point (``python update_installer.py``)
and library utilities for performing in-app or external update workflows.
Supports source-mode updates (zip download) and executable-mode updates
(7z archive with pre-built binaries).
"""

import os
import sys
import shutil
import subprocess
import tempfile
import zipfile
import requests
import time
import argparse
import platform
import threading
from datetime import datetime
import html
import ctypes
import json
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from version import ( # noqa: E402
    APP_VERSION,
    GITHUB_LATEST_RELEASE_URL,
    GITHUB_RELEASE_BY_TAG_URL,
)

try:
    import py7zr

    PY7ZR_AVAILABLE = True
except ImportError:
    PY7ZR_AVAILABLE = False

QT_AVAILABLE = False
try:
    from PySide6.QtWidgets import (
        QApplication,
        QDialog,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QTextEdit,
        QPushButton,
        QProgressBar,
    )
    from PySide6.QtCore import Qt, Signal

    QT_AVAILABLE = True
except ImportError:
    pass


if QT_AVAILABLE:
    class QtUpdateDialog(QDialog):
        """Qt dialog showing update progress with a log view and progress bar.

        Attributes:
            LOG_COLORS: Mapping of log level names to CSS colors.
        """

        LOG_COLORS = {
            "info": "#00ff9d",
            "warning": "#ffcc00",
            "error": "#ff6b6b",
            "success": "#4caf50",
        }

        _log_signal = Signal(str, str)
        _progress_signal = Signal(int, str)
        _enable_restart_signal = Signal(object)
        _allow_close_signal = Signal()

        def __init__(self, parent=None):
            """Initialize the dialog with log view, progress bar, and buttons."""
            super().__init__(parent)
            self.setWindowTitle("TextureAtlas Toolbox Updater")
            self.setModal(True)
            self.resize(680, 520)
            self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

            self.log_view = QTextEdit()
            self.log_view.setReadOnly(True)
            self.log_view.setStyleSheet(
                "QTextEdit {"
                "background-color: #1e1e1e;"
                "color: #e0e0e0;"
                "font-family: Consolas, 'Fira Code', monospace;"
                "font-size: 11px;"
                "}"
            )

            self.progress_label = QLabel("Initializing...")
            self.progress_label.setStyleSheet("color: #cccccc; font-size: 12px;")

            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)

            self.restart_button = QPushButton("Restart Application")
            self.restart_button.setEnabled(False)
            self.restart_button.clicked.connect(self._handle_restart)

            self.close_button = QPushButton("Close")
            self.close_button.setEnabled(False)
            self.close_button.clicked.connect(self.reject)

            button_row = QHBoxLayout()
            button_row.addStretch(1)
            button_row.addWidget(self.restart_button)
            button_row.addWidget(self.close_button)

            layout = QVBoxLayout(self)
            layout.addWidget(self.log_view)
            layout.addWidget(self.progress_label)
            layout.addWidget(self.progress_bar)
            layout.addLayout(button_row)

            self.restart_callback = None

            # Connect signals for thread-safe UI updates
            self._log_signal.connect(self._do_log)
            self._progress_signal.connect(self._do_progress)
            self._enable_restart_signal.connect(self._do_enable_restart)
            self._allow_close_signal.connect(self._do_allow_close)

        def _do_log(self, message, level):
            """Append a timestamped, colorized message to the log view."""

            color = self.LOG_COLORS.get(level, "#ffffff")
            timestamp = datetime.now().strftime("%H:%M:%S")
            safe_message = html.escape(message)
            formatted = (
                f"<span style='color:#999999;'>[{timestamp}]</span> "
                f"<span style='color:{color};'>{safe_message}</span>"
            )
            self.log_view.append(formatted)
            self.log_view.ensureCursorVisible()

        def _do_progress(self, value, status_text):
            """Update the progress bar value and optional status label."""

            self.progress_bar.setValue(max(0, min(100, value)))
            if status_text:
                self.progress_label.setText(status_text)

        def _do_enable_restart(self, callback):
            """Store a restart callback and enable the restart button."""

            self.restart_callback = callback
            self.restart_button.setEnabled(True)

        def _do_allow_close(self):
            """Enable the close button so the user can dismiss the dialog."""

            self.close_button.setEnabled(True)

        def log(self, message, level="info"):
            """Queue a log message for thread-safe display."""

            self._log_signal.emit(message, level)

        def set_progress(self, value, status_text=""):
            """Queue a progress update for thread-safe display."""

            self._progress_signal.emit(value, status_text)

        def enable_restart(self, restart_callback):
            """Queue enabling the restart button with the given callback."""

            self._enable_restart_signal.emit(restart_callback)

        def allow_close(self):
            """Queue enabling the close button."""

            self._allow_close_signal.emit()

        def _handle_restart(self):
            """Invoke the stored restart callback when the button is clicked."""

            if callable(self.restart_callback):
                self.restart_callback()


class UpdateUtilities:
    """Helper methods shared by the updater for filesystem and packaging tasks."""

    @staticmethod
    def apply_pending_updates(search_dir=None):
        """Finalize deferred file replacements left from a prior update.

        Scans ``search_dir`` (defaulting to the src directory) for files
        ending in ``.new`` and moves them over their original counterparts.
        Call this at application startup.

        Args:
            search_dir: Root path to scan. Defaults to this file's parent.

        Returns:
            List of tuples (new_file, target_file, success) for each file.
        """
        if search_dir is None:
            # Default to the src directory
            search_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        results = []
        
        # Find all .new files recursively
        for root, _dirs, files in os.walk(search_dir):
            for filename in files:
                if filename.endswith('.new'):
                    new_file = os.path.join(root, filename)
                    # Target is the same path without .new extension
                    target_file = new_file[:-4]  # Remove '.new'
                    
                    try:
                        # Try to apply the pending update
                        if os.path.exists(target_file):
                            # Create backup
                            backup_file = target_file + '.bak'
                            try:
                                if os.path.exists(backup_file):
                                    os.remove(backup_file)
                                os.rename(target_file, backup_file)
                            except Exception:
                                # If we can't backup, try direct removal
                                os.remove(target_file)
                        
                        # Rename .new to target
                        os.rename(new_file, target_file)
                        
                        # Clean up backup if successful
                        backup_file = target_file + '.bak'
                        if os.path.exists(backup_file):
                            try:
                                os.remove(backup_file)
                            except Exception:
                                pass  # Non-critical
                        
                        results.append((new_file, target_file, True))
                    except Exception as e:
                        print(f"Failed to apply pending update {new_file}: {e}")
                        results.append((new_file, target_file, False))
        
        return results

    @staticmethod
    def find_root(target_name):
        """Walk upward from this file until ``target_name`` exists.

        Returns:
            Directory containing ``target_name``, or None if not found.
        """

        root_path = os.path.abspath(__file__)
        while True:
            root_path = os.path.dirname(root_path)
            target_path = os.path.join(root_path, target_name)
            if os.path.exists(target_path):
                return root_path
            new_root = os.path.dirname(root_path)
            if new_root == root_path:
                break
        return None

    @staticmethod
    def is_file_locked(file_path):
        """Return True if the file cannot be opened for read/write access."""

        if not os.path.exists(file_path):
            return False
        try:
            with open(file_path, "r+b"):
                pass
            return False
        except (IOError, OSError, PermissionError):
            return True

    @staticmethod
    def wait_for_file_unlock(file_path, max_attempts=10, delay=1.0):
        """Block until the file is unlocked or attempts are exhausted.

        Args:
            file_path: Absolute path to check.
            max_attempts: Maximum number of polling attempts.
            delay: Seconds to sleep between checks.

        Returns:
            True if the file became accessible, False otherwise.
        """

        for attempt in range(max_attempts):
            if not UpdateUtilities.is_file_locked(file_path):
                return True
            time.sleep(delay)
        return False

    @staticmethod
    def extract_7z(archive_path, extract_dir):
        """Extract a 7z archive using py7zr or the system ``7z`` command.

        Returns:
            True on success, False if extraction failed.
        """

        if PY7ZR_AVAILABLE:
            with py7zr.SevenZipFile(archive_path, mode="r") as archive:
                archive.extractall(path=extract_dir)
            return True
        else:
            # Fallback to system 7z command
            try:
                cmd = ['7z', 'x', archive_path, f'-o{extract_dir}', '-y']
                subprocess.run(cmd, check=True, capture_output=True, text=True)
                return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                return False

    @staticmethod
    def is_compiled():
        """Return True if running inside a Nuitka-compiled executable."""

        if '__compiled__' in globals():
            return True
        else:
            return False

    @staticmethod
    def find_exe_files(directory):
        """List ``.exe`` filenames located directly under ``directory``."""

        exe_files = []
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isfile(item_path) and item.lower().endswith(".exe"):
                exe_files.append(item)
        return exe_files

    @staticmethod
    def has_write_access(directory):
        """Return True if the current process can create files in ``directory``."""

        test_dir = directory
        if not os.path.isdir(test_dir):
            test_dir = os.path.dirname(test_dir)
        try:
            if not test_dir:
                return False
            if os.access(test_dir, os.W_OK):
                tmp_path = os.path.join(test_dir, f".tatgf_write_test_{os.getpid()}" )
                with open(tmp_path, 'w', encoding='utf-8') as tmp_file:
                    tmp_file.write('1')
                os.remove(tmp_path)
                return True
        except (PermissionError, OSError):
            return False
        return False

    @staticmethod
    def is_admin():
        """Return True if running with administrator or root privileges."""

        if os.name == 'nt':
            try:
                return bool(ctypes.windll.shell32.IsUserAnAdmin())
            except AttributeError:
                return False
        if hasattr(os, 'geteuid'):
            return os.geteuid() == 0
        return False

    @staticmethod
    def run_elevated(command):
        """Request Windows UAC elevation and execute ``command``.

        Returns:
            True if the elevated shell launch was initiated.
        """

        if os.name != 'nt':
            return False
        if not command:
            return False
        executable = command[0]
        args = subprocess.list2cmdline(command[1:])
        try:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, args, None, 1)
            return True
        except Exception as exc:
            print(f"Failed to request administrator privileges: {exc}")
            return False

def _write_metadata_file(metadata):
    """Write release metadata to a temp JSON file for the external updater."""

    temp_dir = Path(tempfile.mkdtemp(prefix="tatgf_update_"))
    metadata_path = temp_dir / "release_metadata.json"
    with metadata_path.open("w", encoding="utf-8") as handle:
        json.dump(metadata or {}, handle)
    return metadata_path


def launch_external_updater(
    release_metadata=None,
    latest_version=None,
    exe_mode=False,
    wait_seconds=3,
):
    """Spawn a detached Python process to run the updater via ``Main.py --update``.

    The new process can overwrite files (including Main.py itself) because the
    original application will have exited.

    Args:
        release_metadata: Dict with tag_name, zipball_url, etc.
        latest_version: Target version string.
        exe_mode: True to update executable builds rather than source.
        wait_seconds: Seconds to delay before the updater begins work.

    Returns:
        True if the process started successfully.
    """

    script_path = Path(__file__).resolve()
    project_root = script_path.parents[2]
    
    # Run Main.py with --update flag instead of update_installer.py directly
    # This allows Main.py to update itself since the old process will be gone
    main_py = project_root / "src" / "Main.py"
    args = [sys.executable, str(main_py), "--update"]

    if wait_seconds is not None:
        args.extend(["--wait", str(wait_seconds)])

    if exe_mode:
        args.append("--exe-mode")

    if latest_version:
        args.extend(["--target-tag", latest_version])

    # Write metadata for the new process to use
    if release_metadata:
        metadata_path = _write_metadata_file(release_metadata)
        # Store path in environment for the updater to find
        os.environ["UPDATER_METADATA_FILE"] = str(metadata_path)

    print(f"Launching external updater: {' '.join(args)}")
    print(f"Working directory: {project_root}")

    # Use CREATE_NEW_PROCESS_GROUP on Windows for proper detachment
    kwargs = {"cwd": str(project_root)}
    if os.name == "nt":
        # CREATE_NEW_PROCESS_GROUP = 0x00000200
        # DETACHED_PROCESS = 0x00000008
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS

    try:
        process = subprocess.Popen(args, **kwargs)
        print(f"Updater process started with PID: {process.pid}")
        return True
    except Exception as e:
        print(f"Failed to launch updater: {e}")
        import traceback
        traceback.print_exc()
        return False


class Updater:
    """Download and apply updates, reporting progress through an optional Qt UI.

    Supports both source-mode (zipball) and executable-mode (7z) updates.
    """

    def __init__(self, ui=None, exe_mode=False, target_tag=None, release_metadata=None):
        """Create an Updater with optional Qt UI and target release info.

        Args:
            ui: QtUpdateDialog or similar object with log/set_progress methods.
            exe_mode: True when updating a compiled executable distribution.
            target_tag: Specific tag to update to, or None for latest.
            release_metadata: Pre-fetched release info dict.
        """
        self.ui = ui
        self.exe_mode = exe_mode
        self.log_file = None
        self.target_tag = target_tag
        self.release_metadata = release_metadata or {}
        self._setup_log_file()

    def _setup_log_file(self):
        """Create the ``logs`` directory and open a timestamped log file."""

        try:
            if self.exe_mode and UpdateUtilities.is_compiled():
                app_dir = os.path.dirname(sys.executable)
            else:
                app_dir = self.find_project_root() or os.getcwd()
            logs_dir = os.path.join(app_dir, "logs")
            os.makedirs(logs_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            self.log_file = os.path.join(logs_dir, f"update_{timestamp}.log")
        except Exception as e:
            print(f"[WARNING] Could not set up log file: {e}")
            self.log_file = None

    def log(self, message, level="info"):
        """Log a message to the UI (or stdout) and mirror it to the log file."""

        if self.ui:
            self.ui.log(message, level)
        else:
            prefix = f"[{level.upper()}]" if level != "info" else ""
            print(f"{prefix} {message}")
        # Save to log file if available
        if self.log_file:
            try:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(f"[{timestamp}] [{level.upper()}] {message}\n")
            except Exception as e:
                # Only print warning if not in GUI mode
                if not self.ui:
                    print(f"[WARNING] Could not write to log file: {e}")

    def set_progress(self, progress, message=""):
        """Update progress bar value, falling back to console output if no UI."""

        if self.ui:
            self.ui.set_progress(progress, message)
        else:
            print(f"Progress: {progress}% - {message}")

    def enable_restart(self, restart_func):
        """Provide a restart callback to the UI or print manual instructions."""

        if self.ui:
            self.ui.enable_restart(restart_func)
        else:
            print("Update complete! Please restart the application manually.")

    @staticmethod
    def get_latest_release_info(tag_name=None, fallback_metadata=None):
        """Fetch release metadata from GitHub or use provided fallback.

        When ``fallback_metadata`` already contains a zipball_url, no network
        request is made.

        Args:
            tag_name: Specific tag to query, or None for latest release.
            fallback_metadata: Pre-fetched metadata dict.

        Returns:
            Dict with tag_name, zipball_url, and other release fields.
        """
        # If we already have complete metadata with download URL, use it directly
        if fallback_metadata and fallback_metadata.get("zipball_url"):
            data = {"tag_name": tag_name or fallback_metadata.get("tag_name", "unknown")}
            data.update(fallback_metadata)
            return data

        # Otherwise, try to fetch from GitHub
        if tag_name:
            response = requests.get(GITHUB_RELEASE_BY_TAG_URL.format(tag=tag_name), timeout=30)
            if response.status_code == 404 and fallback_metadata:
                data = {"tag_name": tag_name}
                data.update(fallback_metadata)
                return data
            response.raise_for_status()
            return response.json()

        response = requests.get(GITHUB_LATEST_RELEASE_URL, timeout=30)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _detect_project_root(directory, exe_mode=False):
        """Return True if ``directory`` matches the expected project layout.

        For executable mode, checks for assets, ImageMagick, and at least one
        .exe file. For source mode, also requires src, LICENSE, README.md, etc.
        """
        if exe_mode:
            required_folders = ["assets", "ImageMagick"]
            required_files = []

            for folder in required_folders:
                if not os.path.isdir(os.path.join(directory, folder)):
                    return False

            # Check for at least one .exe file
            exe_files = UpdateUtilities.find_exe_files(directory)
            if not exe_files:
                return False

            return True
        else:
            # For source mode, look for full project structure
            required_folders = ["assets", "ImageMagick", "src"]
            required_files = ["latestVersion.txt", "LICENSE", "README.md"]

            for folder in required_folders:
                if not os.path.isdir(os.path.join(directory, folder)):
                    return False

            for file in required_files:
                if not os.path.isfile(os.path.join(directory, file)):
                    return False

            return True

    @staticmethod
    def _find_github_zipball_root(extract_dir):
        """Locate the actual project root inside a GitHub zipball extraction.

        Returns:
            Path to the nested project directory, or None if not found.
        """
        extracted_contents = os.listdir(extract_dir)

        if len(extracted_contents) == 1:
            potential_root = os.path.join(extract_dir, extracted_contents[0])
            if os.path.isdir(potential_root):
                root_contents = os.listdir(potential_root)
                project_indicators = ["src", "README.md", "assets", "ImageMagick"]
                found_indicators = [
                    item for item in project_indicators if item in root_contents
                ]

                if found_indicators:
                    return potential_root

        for item in extracted_contents:
            item_path = os.path.join(extract_dir, item)
            if os.path.isdir(item_path):
                if Updater._detect_project_root(item_path, exe_mode=False):
                    return item_path

        return None

    def wait_for_main_app_closure(self, max_wait_seconds=30):
        """Block until key application files are unlocked.

        In executable mode, the wait time is extended to allow DLLs to be
        released.

        Args:
            max_wait_seconds: Timeout before giving up.

        Returns:
            True if files became accessible, False on timeout.
        """
        self.log("Waiting for main application to close...")
        self.set_progress(5, "Waiting for application closure...")

        # For executable mode, wait longer since DLLs might need more time to be released
        if self.exe_mode:
            max_wait_seconds = 60
            self.log(
                "Executable mode detected, extending wait time for DLL release...",
                "info",
            )

        start_time = time.time()
        while time.time() - start_time < max_wait_seconds:
            locked_files = []

            if self.exe_mode and UpdateUtilities.is_compiled():
                current_exe = sys.executable
                if UpdateUtilities.is_file_locked(current_exe):
                    locked_files.append(current_exe)

                # Also check for ImageMagick DLLs that might be locked
                app_root = os.path.dirname(current_exe)
                imagemagick_dir = os.path.join(app_root, "ImageMagick")
                if os.path.exists(imagemagick_dir):
                    for dll_file in os.listdir(imagemagick_dir):
                        if dll_file.lower().endswith(".dll"):
                            dll_path = os.path.join(imagemagick_dir, dll_file)
                            if UpdateUtilities.is_file_locked(dll_path):
                                locked_files.append(dll_path)

            else:
                project_root = self.find_project_root()
                if project_root:
                    main_py = os.path.join(project_root, "src", "Main.py")
                    if os.path.exists(main_py) and UpdateUtilities.is_file_locked(
                        main_py
                    ):
                        locked_files.append(main_py)

            if not locked_files:
                self.log("Application appears to be closed", "success")
                return True
            else:
                if len(locked_files) <= 3:  # Only log a few files to avoid spam
                    self.log(
                        f"Still waiting for {len(locked_files)} files to be released: {', '.join([os.path.basename(f) for f in locked_files[:3]])}",
                        "info",
                    )
                else:
                    self.log(
                        f"Still waiting for {len(locked_files)} files to be released...",
                        "info",
                    )

            time.sleep(3)

        self.log("Timeout waiting for application closure", "warning")
        return False

    def find_project_root(self):
        """Determine the project root for source or executable mode."""

        if self.exe_mode:
            if UpdateUtilities.is_compiled():
                return os.path.dirname(sys.executable)
            else:
                # Extra fallback just in case.
                return os.getcwd()
        else:
            return UpdateUtilities.find_root("README.md")

    def create_updater_backup(self):
        """Copy this script to a ``.backup`` file so it can be restored on failure."""

        try:
            current_script = os.path.abspath(__file__)
            backup_script = current_script + ".backup"

            shutil.copy2(current_script, backup_script)
            self.log(f"Created updater backup: {backup_script}", "info")
            return backup_script

        except Exception as e:
            self.log(f"Warning: Could not create updater backup: {e}", "warning")
            return None

    def cleanup_updater_backup(self):
        """Delete the ``.backup`` file if it exists."""

        try:
            current_script = os.path.abspath(__file__)
            backup_script = current_script + ".backup"

            if os.path.exists(backup_script):
                os.remove(backup_script)
                self.log("Cleaned up updater backup", "info")
        except Exception as e:
            self.log(f"Warning: Could not clean up updater backup: {e}", "warning")

    def update_source(self):
        """Download and merge the latest source zipball into the local checkout."""
        try:
            self.log("Starting standalone source code update...", "info")
            self.set_progress(10, "Finding project root...")

            project_root = self.find_project_root()
            if not project_root:
                raise Exception(
                    "Could not determine project root (README.md not found)"
                )

            self.log(f"Project root: {project_root}", "info")

            self._ensure_write_permissions(project_root)

            self.create_updater_backup()

            if not self.wait_for_main_app_closure():
                self.log(
                    "Continuing update despite locked files (may fail)...", "warning"
                )

            self.set_progress(15, "Fetching release information...")

            info = self.get_latest_release_info(self.target_tag, self.release_metadata)
            zip_url = info["zipball_url"]
            self.log(f"Found latest release: {info.get('tag_name', 'unknown')}", "info")

            self.set_progress(20, "Downloading source archive...")
            self.log("Starting download...", "info")

            response = requests.get(zip_url, stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            self.log(f"Download size: {total_size / 1024 / 1024:.2f} MB", "info")

            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_file:
                tmp_path = tmp_file.name
                downloaded = 0

                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        tmp_file.write(chunk)
                        downloaded += len(chunk)
                        if total_size:
                            progress = 20 + (downloaded * 40 // total_size)
                            self.set_progress(
                                progress,
                                f"Downloaded {downloaded / 1024 / 1024:.1f} MB",
                            )

            self._verify_download_size(tmp_path, total_size, downloaded, "source archive")

            self.log(f"Download complete: {tmp_path}", "success")
            self.set_progress(60, "Extracting archive...")

            with zipfile.ZipFile(tmp_path, "r") as zip_ref:
                extract_dir = tempfile.mkdtemp()
                self.log(f"Extracting to: {extract_dir}", "info")
                zip_ref.extractall(extract_dir)

            self.set_progress(70, "Detecting project structure...")

            source_project_root = self._find_github_zipball_root(extract_dir)

            # Fallback if the expected structure in the release zipball is not found
            # This will help in case the file structure changes between releases
            if not source_project_root:
                self.log(
                    "Release zipball structure not found, trying main branch...",
                    "warning",
                )

                os.remove(tmp_path)
                shutil.rmtree(extract_dir, ignore_errors=True)

                main_branch_url = "https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/archive/refs/heads/main.zip"
                self.log(f"Fallback URL: {main_branch_url}", "info")

                response = requests.get(main_branch_url, stream=True)
                response.raise_for_status()

                total_size = int(response.headers.get("content-length", 0))

                with tempfile.NamedTemporaryFile(
                    suffix=".zip", delete=False
                ) as tmp_file:
                    tmp_path = tmp_file.name
                    downloaded = 0

                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            tmp_file.write(chunk)
                            downloaded += len(chunk)
                            if total_size:
                                progress = 25 + (downloaded * 35 // total_size)
                                self.set_progress(
                                    progress,
                                    f"Downloaded {downloaded / 1024 / 1024:.1f} MB",
                                )

                self._verify_download_size(tmp_path, total_size, downloaded, "fallback source archive")

                with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                    extract_dir = tempfile.mkdtemp()
                    zip_ref.extractall(extract_dir)

                source_project_root = self._find_github_zipball_root(extract_dir)
                if not source_project_root:
                    raise Exception(
                        "Could not find project structure in either release or main branch"
                    )

            self.log(f"Found source root: {source_project_root}", "success")

            zipball_contents = os.listdir(source_project_root)
            self.log(f"Source contains: {', '.join(zipball_contents)}", "info")

            self.set_progress(80, "Copying files...")

            # Dynamically discover what to copy from the source
            # Core items that should always be copied if they exist
            core_items = [
                "assets",
                "ImageMagick",
                "src",
                "latestVersion.txt",
                "LICENSE",
                "README.md",
            ]

            # Optional items that may or may not exist
            optional_items = [".gitignore", ".github", "docs", "setup", "tests", "tools"]

            # Items to skip (user/local data that shouldn't be overwritten)
            skip_items = {"logs", "__pycache__", ".git", "config", "user_data", "cache", ".venv", "venv"}

            # Build the list of items to copy based on what actually exists in source
            items_to_copy = []

            # Add core items that exist in source
            for item in core_items:
                if os.path.exists(os.path.join(source_project_root, item)):
                    items_to_copy.append(item)
                else:
                    self.log(f"Core item '{item}' not found in source (may have been removed)", "warning")

            # Add optional items that exist in source
            for item in optional_items:
                if os.path.exists(os.path.join(source_project_root, item)):
                    items_to_copy.append(item)
                    self.log(f"Found optional item: {item}", "info")

            # Also check for any other top-level items in source that we might have missed
            for item in zipball_contents:
                if item not in items_to_copy and item not in skip_items:
                    src_path = os.path.join(source_project_root, item)
                    # Only add files or directories that look like project files
                    if os.path.isfile(src_path) or (os.path.isdir(src_path) and not item.startswith('.')):
                        items_to_copy.append(item)
                        self.log(f"Found additional item: {item}", "info")

            self.log(f"Will update {len(items_to_copy)} items: {', '.join(items_to_copy)}", "info")

            for item in items_to_copy:
                src_path = os.path.join(source_project_root, item)
                dst_path = os.path.join(project_root, item)

                if os.path.exists(src_path):
                    self.log(f"Copying {item}...", "info")
                    try:
                        if os.path.isdir(src_path):
                            if os.path.exists(dst_path):
                                self._merge_directory(src_path, dst_path)
                            else:
                                shutil.copytree(src_path, dst_path)
                        else:
                            self._copy_file_with_retry(src_path, dst_path)
                        self.log(f"Successfully copied {item}", "success")
                    except Exception as e:
                        self.log(f"Failed to copy {item}: {str(e)}", "error")
                else:
                    self.log(f"Warning: {item} not found in source", "warning")

            os.remove(tmp_path)
            shutil.rmtree(extract_dir, ignore_errors=True)
            self.log("Cleanup completed", "info")

            self.cleanup_updater_backup()

            self.set_progress(100, "Update complete!")
            self.log("Source code update completed successfully!", "success")
            self.log(
                "Please restart the application to use the updated version.", "info"
            )

            def restart_app():
                if self.ui:
                    self.ui.close()

                main_py = os.path.join(project_root, "src", "Main.py")
                if os.path.exists(main_py):
                    try:
                        subprocess.Popen(
                            [sys.executable, main_py], cwd=os.path.dirname(main_py)
                        )
                    except Exception:
                        pass
                sys.exit(0)

            self.enable_restart(restart_app)

        except Exception as e:
            self.log(f"Update failed: {str(e)}", "error")
            self.set_progress(0, "Update failed!")
            if self.ui:
                self.ui.log(f"Standalone update failed: {str(e)}", "error")

    def update_exe(self):
        """Download the latest 7z executable package and install it."""
        try:
            self.log("Starting executable update...", "info")

            if platform.system() != "Windows":
                raise Exception(
                    f"Executable updates are only supported on Windows currently. Current platform: {platform.system()}.\n"
                    "If you're running a compiled executable for macOS or Linux, your version isn't official."
                )

            self.set_progress(10, "Finding application directory...")

            if UpdateUtilities.is_compiled():
                current_exe = sys.executable
                app_root = os.path.dirname(current_exe)
            else:
                app_root = self.find_project_root()
                if not app_root:
                    raise Exception("Could not determine application directory")
                current_exe = None

                exe_files = UpdateUtilities.find_exe_files(app_root)
                if exe_files:
                    for exe_file in exe_files:
                        if "TextureAtlas" in exe_file or "Main" in exe_file:
                            current_exe = os.path.join(app_root, exe_file)
                            break
                    if not current_exe:
                        current_exe = os.path.join(app_root, exe_files[0])

            self.log(f"Application directory: {app_root}", "info")
            if current_exe:
                self.log(f"Current executable: {current_exe}", "info")

            if not self.wait_for_main_app_closure():
                self.log(
                    "Continuing update despite locked files (may fail)...", "warning"
                )

            self._ensure_write_permissions(app_root)

            self.set_progress(15, "Fetching release information...")

            info = self.get_latest_release_info(self.target_tag, self.release_metadata)
            self.log(f"Found latest release: {info.get('tag_name', 'unknown')}", "info")

            assets = info.get("assets", [])
            seven_z_asset = None

            for asset in assets:
                if asset["name"].lower().endswith(".7z"):
                    seven_z_asset = asset
                    break

            if not seven_z_asset:
                raise Exception("No .7z release file found in latest release")

            download_url = seven_z_asset["browser_download_url"]
            file_size = seven_z_asset.get("size", 0)

            self.log(f"Downloading: {seven_z_asset['name']}", "info")
            self.log(f"Size: {file_size / 1024 / 1024:.2f} MB", "info")

            self.set_progress(20, "Downloading executable archive...")

            response = requests.get(download_url, stream=True)
            response.raise_for_status()

            with tempfile.NamedTemporaryFile(suffix=".7z", delete=False) as tmp_file:
                tmp_path = tmp_file.name
                downloaded = 0

                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        tmp_file.write(chunk)
                        downloaded += len(chunk)
                        if file_size:
                            progress = 20 + (downloaded * 40 // file_size)
                            self.set_progress(
                                progress,
                                f"Downloaded {downloaded / 1024 / 1024:.1f} MB",
                            )

            self._verify_download_size(tmp_path, file_size, downloaded, "executable archive")

            self.log(f"Download complete: {tmp_path}", "success")
            self.set_progress(60, "Extracting archive...")

            extract_dir = tempfile.mkdtemp()
            self.log(f"Extracting to: {extract_dir}", "info")

            if not UpdateUtilities.extract_7z(tmp_path, extract_dir):
                raise Exception(
                    "Failed to extract 7z archive. Make sure py7zr is installed or 7z command is available."
                )

            self.set_progress(70, "Detecting release structure...")

            extracted_contents = os.listdir(extract_dir)
            self.log(f"Extracted contents: {', '.join(extracted_contents)}", "info")

            release_root = extract_dir
            if len(extracted_contents) == 1 and os.path.isdir(
                os.path.join(extract_dir, extracted_contents[0])
            ):
                potential_root = os.path.join(extract_dir, extracted_contents[0])
                contents = os.listdir(potential_root)
                if any(item.lower().endswith(".exe") for item in contents):
                    release_root = potential_root

            release_contents = os.listdir(release_root)
            self.log(f"Release contents: {', '.join(release_contents)}", "info")

            exe_files = UpdateUtilities.find_exe_files(release_root)
            if not exe_files:
                raise Exception("No executable files found in release")

            self.log(f"Found executables: {', '.join(exe_files)}", "info")

            self.set_progress(80, "Installing update...")

            backup_dir = None
            if current_exe and os.path.exists(current_exe):
                backup_dir = os.path.join(
                    tempfile.gettempdir(), f"app_backup_{int(time.time())}"
                )
                os.makedirs(backup_dir, exist_ok=True)

                backup_exe = os.path.join(backup_dir, os.path.basename(current_exe))
                try:
                    shutil.copy2(current_exe, backup_exe)
                    self.log(f"Backed up current executable to: {backup_exe}", "info")
                except Exception as e:
                    self.log(
                        f"Warning: Could not backup current executable: {e}", "warning"
                    )

            items_to_copy = ["assets", "ImageMagick", "LICENSE", "README.md"]
            items_to_copy.extend(exe_files)

            optional_items = ["docs", ".gitignore"]
            for item in optional_items:
                if os.path.exists(os.path.join(release_root, item)):
                    items_to_copy.append(item)

            for item in items_to_copy:
                src_path = os.path.join(release_root, item)
                dst_path = os.path.join(app_root, item)

                if os.path.exists(src_path):
                    self.log(f"Installing {item}...", "info")
                    try:
                        if os.path.isdir(src_path):
                            if os.path.exists(dst_path):
                                self._merge_directory(src_path, dst_path)
                            else:
                                shutil.copytree(src_path, dst_path)
                        else:
                            if item.lower().endswith(".exe") and os.path.exists(
                                dst_path
                            ):
                                backup_name = dst_path + ".old"
                                if os.path.exists(backup_name):
                                    try:
                                        os.remove(backup_name)
                                    except Exception:
                                        pass
                                try:
                                    os.rename(dst_path, backup_name)
                                    self.log(
                                        f"Renamed old executable to {backup_name}",
                                        "info",
                                    )
                                except Exception as e:
                                    self.log(
                                        f"Could not rename old executable: {e}",
                                        "warning",
                                    )

                            self._copy_file_with_retry(src_path, dst_path)
                        self.log(f"Successfully installed {item}", "success")
                    except Exception as e:
                        self.log(f"Failed to install {item}: {str(e)}", "error")
                        if item.lower().endswith(".exe"):
                            raise e
                else:
                    self.log(f"Warning: {item} not found in release", "warning")

            os.remove(tmp_path)
            shutil.rmtree(extract_dir, ignore_errors=True)
            self.log("Cleanup completed", "info")

            self.set_progress(100, "Update complete!")
            self.log("Executable update completed successfully!", "success")
            self.log(
                "Please restart the application to use the updated version.", "info"
            )

            def restart_app():
                if self.ui:
                    self.ui.close()

                main_exe = None
                for exe_file in exe_files:
                    exe_path = os.path.join(app_root, exe_file)
                    if os.path.exists(exe_path):
                        if "TextureAtlas" in exe_file or "Main" in exe_file:
                            main_exe = exe_path
                            break
                        elif not main_exe:
                            main_exe = exe_path

                if main_exe:
                    try:
                        self.log("Attempting to restart application...", "info")
                        self.log(f"Executable: {main_exe}", "info")
                        self.log(f"Working directory: {app_root}", "info")

                        if UpdateUtilities.is_compiled():
                            # For Nuitka executables, try with shell=True for better compatibility
                            process = subprocess.Popen(
                                [main_exe], cwd=app_root, shell=True
                            )
                            self.log(
                                f"Started process with PID: {process.pid}", "success"
                            )
                        else:
                            # For non-Nuitka (shouldn't happen in exe mode but just in case)
                            process = subprocess.Popen([main_exe], cwd=app_root)
                            self.log(
                                f"Started process with PID: {process.pid}", "success"
                            )

                        self.log(
                            "Application restart initiated successfully", "success"
                        )

                        # Give the process a moment to start
                        import time

                        time.sleep(2)

                    except Exception as e:
                        self.log(f"Failed to restart application: {e}", "error")
                        self.log(
                            f"Please manually start the application from: {main_exe}",
                            "warning",
                        )
                else:
                    self.log("No executable found to restart", "error")
                    self.log(
                        f"Available files in {app_root}: {', '.join(os.listdir(app_root))}",
                        "info",
                    )

                sys.exit(0)

            self.enable_restart(restart_app)

        except Exception as e:
            self.log(f"Executable update failed: {str(e)}", "error")
            self.set_progress(0, "Update failed!")
            if self.ui:
                self.ui.log(f"Executable update failed: {str(e)}", "error")

    def _merge_directory(self, src_dir, dst_dir):
        """Recursively copy files from ``src_dir`` to ``dst_dir``.

        Overwrites existing files and removes obsolete files in the destination
        that no longer exist in the source. User data directories such as logs
        and config are preserved.
        """
        # Directories that should never be deleted (user data)
        preserved_dirs = {'logs', '__pycache__', '.git', 'config', 'user_data', 'cache'}
        # File extensions that should never be deleted (user data)
        preserved_extensions = {'.log', '.cfg', '.ini', '.user', '.local'}

        # First, copy all files from source to destination
        files_copied = 0
        files_failed = 0
        important_files = []  # Track important files like Main.py
        
        for root, dirs, files in os.walk(src_dir):
            rel_path = os.path.relpath(root, src_dir)
            if rel_path == ".":
                target_dir = dst_dir
            else:
                target_dir = os.path.join(dst_dir, rel_path)

            os.makedirs(target_dir, exist_ok=True)

            for file in files:
                src_file = os.path.join(root, file)
                dst_file = os.path.join(target_dir, file)
                
                # Track important files
                if file.lower() in ('main.py', '__init__.py', 'version.py', 'update_installer.py', 'update_checker.py'):
                    rel_file_path = os.path.join(rel_path, file) if rel_path != "." else file
                    important_files.append(rel_file_path)
                
                try:
                    success = self._copy_file_with_retry(src_file, dst_file)
                    if success:
                        files_copied += 1
                    else:
                        files_failed += 1
                except Exception as e:
                    self.log(f"ERROR copying {file}: {e}", "error")
                    files_failed += 1

        self.log(f"Copied {files_copied} files to {os.path.basename(dst_dir)}", "info")
        if files_failed > 0:
            self.log(f"Failed to copy {files_failed} files", "warning")
        
        # Log important files that were updated
        if important_files:
            self.log(f"Key files processed: {', '.join(important_files)}", "success")

        # Then, remove files in destination that don't exist in source
        # This cleans up old files that were removed in the new version
        # For src/ directory, we always clean up obsolete files (except user config)
        files_removed = 0
        
        # Files that should never be deleted (user data)
        preserved_files = {'app_config.cfg'}
        
        for root, dirs, files in os.walk(dst_dir):
            rel_path = os.path.relpath(root, dst_dir)

            # Skip preserved directories
            if any(preserved in rel_path.split(os.sep) for preserved in preserved_dirs):
                continue

            for file in files:
                # Skip preserved file types
                if any(file.lower().endswith(ext) for ext in preserved_extensions):
                    continue
                
                # Skip specifically preserved files (like app_config.cfg)
                if file.lower() in preserved_files:
                    continue

                dst_file = os.path.join(root, file)

                # Determine the corresponding source path
                if rel_path == ".":
                    src_file = os.path.join(src_dir, file)
                else:
                    src_file = os.path.join(src_dir, rel_path, file)

                # If file doesn't exist in source, it's obsolete - remove it
                if not os.path.exists(src_file):
                    try:
                        os.remove(dst_file)
                        files_removed += 1
                        self.log(f"Removed obsolete file: {os.path.join(rel_path, file)}", "info")
                    except Exception as e:
                        self.log(f"Could not remove obsolete file {file}: {e}", "warning")

        if files_removed > 0:
            self.log(f"Cleaned up {files_removed} obsolete files", "info")

    def _copy_file_with_retry(self, src_file, dst_file, max_attempts=5):
        """Copy a file with retry/backoff logic for locked files.

        Falls back to creating a ``.new`` placeholder when the original is
        locked so the file can be applied on next startup.

        Args:
            src_file: Source path.
            dst_file: Destination path.
            max_attempts: Number of copy attempts before giving up.

        Returns:
            True on success.
        """
        filename = os.path.basename(dst_file)
        file_ext = os.path.splitext(filename)[1].lower()

        # Files that might be locked and need special handling
        lockable_extensions = {'.dll', '.exe', '.py', '.pyd', '.so'}
        is_lockable = file_ext in lockable_extensions

        for attempt in range(max_attempts):
            try:
                os.makedirs(os.path.dirname(dst_file), exist_ok=True)

                # For lockable files that exist, try backup/rename strategy first
                if is_lockable and os.path.exists(dst_file):
                    backup_name = dst_file + ".old"
                    try:
                        if os.path.exists(backup_name):
                            os.remove(backup_name)
                        os.rename(dst_file, backup_name)
                        self.log(f"Backed up existing file: {filename}", "info")
                    except PermissionError:
                        # File is locked, will try direct copy anyway
                        self.log(f"Could not backup {filename} (file in use), attempting direct overwrite", "warning")
                    except Exception as e:
                        self.log(f"Could not backup {filename}: {e}", "warning")

                shutil.copy2(src_file, dst_file)
                
                # Clean up backup if copy succeeded
                backup_name = dst_file + ".old"
                if os.path.exists(backup_name):
                    try:
                        os.remove(backup_name)
                    except Exception:
                        pass  # Not critical if we can't remove the backup
                
                return True

            except (PermissionError, OSError) as e:
                if attempt < max_attempts - 1:
                    self.log(
                        f"Copy attempt {attempt + 1}/{max_attempts} failed for {filename}: {e}",
                        "warning",
                    )
                    self.log("Waiting 3 seconds before retry...", "info")
                    time.sleep(3)
                else:
                    # Last attempt - try temp file method for lockable files
                    if is_lockable:
                        try:
                            temp_name = dst_file + ".new"
                            self.log(f"Trying temp file method for {filename}...", "info")
                            shutil.copy2(src_file, temp_name)
                            
                            # Try to remove original and rename temp
                            try:
                                if os.path.exists(dst_file):
                                    os.remove(dst_file)
                            except PermissionError:
                                # Can't remove original, but temp is ready
                                # On next app start, the .new file will be there
                                self.log(
                                    f"Created {filename}.new - original file locked. "
                                    "New version will be available after restart.",
                                    "warning"
                                )
                                return True
                            
                            os.rename(temp_name, dst_file)
                            self.log(
                                f"Successfully updated {filename} using temp file method",
                                "success",
                            )
                            return True

                        except Exception as temp_e:
                            self.log(
                                f"All methods failed for {filename}: {temp_e}",
                                "error",
                            )
                    
                    self.log(f"Failed to copy {filename} after {max_attempts} attempts: {e}", "error")
                    raise e
        
        return False

    @staticmethod
    def _verify_download_size(file_path, expected_size, recorded_size, label):
        """Raise IOError if downloaded file size differs from expected."""

        if not expected_size:
            return
        actual_size = os.path.getsize(file_path)
        if actual_size != expected_size or (recorded_size and recorded_size != expected_size):
            raise IOError(
                f"{label} integrity check failed (expected {expected_size} bytes, got {actual_size})."
            )

    def _ensure_write_permissions(self, target_dir):
        """Request UAC elevation when write access to ``target_dir`` is denied."""

        if not target_dir:
            return
        if UpdateUtilities.has_write_access(target_dir) or UpdateUtilities.is_admin():
            return

        compiled_mode = self.exe_mode and UpdateUtilities.is_compiled()

        self.log(
            f"Administrator privileges are required to modify files under {target_dir}.",
            "warning",
        )

        if compiled_mode:
            command = self._build_elevation_command()
            if UpdateUtilities.run_elevated(command):
                self.log("Elevation request sent. Closing current updater instance...", "info")
                if self.ui:
                    self.ui.allow_close()
                sys.exit(0)

        raise PermissionError(
            "Administrator privileges are required to update this installation. "
            "Please rerun the updater as an administrator."
        )

    def _build_elevation_command(self):
        """Build the command list for relaunching the updater with admin rights."""

        cmd = [sys.executable]
        if not UpdateUtilities.is_compiled():
            cmd.append(os.path.abspath(__file__))

        cmd.append("--wait=0")

        if self.exe_mode and "--exe-mode" not in cmd:
            cmd.append("--exe-mode")

        if "--no-gui" not in cmd:
            cmd.append("--no-gui")

        return cmd


class UpdateInstaller:
    """High-level Qt-integrated installer reusing Updater logic."""

    def __init__(self, parent=None):
        """Store an optional parent widget and verify Qt is available."""

        if not QT_AVAILABLE:
            raise ImportError("PySide6 is required for the integrated updater UI")
        self.parent = parent

    def download_and_install(
        self,
        release_metadata=None,
        latest_version=None,
        parent_window=None,
        exe_mode=None,
    ):
        """Launch the updater dialog and run the appropriate update flow."""

        dialog_parent = parent_window or self.parent
        QApplication.instance() or QApplication(sys.argv)
        dialog = QtUpdateDialog(dialog_parent)
        exe_mode = UpdateUtilities.is_compiled() if exe_mode is None else exe_mode
        metadata = release_metadata or {}
        updater = Updater(
            ui=dialog,
            exe_mode=exe_mode,
            target_tag=metadata.get("tag_name"),
            release_metadata=metadata,
        )

        mode_label = "executable" if exe_mode else "source"
        dialog.log(f"Starting {mode_label} update...", "info")
        dialog.log(f"Currently running version {APP_VERSION}", "info")
        if latest_version:
            dialog.log(f"Target version: {latest_version}", "info")
        if metadata.get("zipball_url"):
            dialog.log(f"Download URL available: {metadata['zipball_url'][:60]}...", "info")
        else:
            dialog.log(
                "No download URL provided; falling back to GitHub release discovery.",
                "warning",
            )

        def _run_update():
            try:
                print(f"[Worker Thread] Starting {mode_label} update...")
                if exe_mode:
                    updater.update_exe()
                else:
                    updater.update_source()
                print("[Worker Thread] Update completed successfully")
            except Exception as err:
                print(f"[Worker Thread] Error: {err}")
                import traceback
                traceback.print_exc()
                dialog.log(f"Update process encountered an error: {err}", "error")
                dialog.allow_close()
            else:
                dialog.allow_close()

        worker = threading.Thread(target=_run_update, daemon=True)
        worker.start()
        print("[Main Thread] Worker thread started, entering dialog.exec()")
        dialog.exec()
        print("[Main Thread] Dialog closed")


def main():
    parser = argparse.ArgumentParser(description="Standalone updater for TextureAtlas-to-GIF-and-Frames")
    parser.add_argument("--no-gui", action="store_true", help="Run in console mode without GUI")
    parser.add_argument("--exe-mode", action="store_true", help="Run in executable update mode")
    parser.add_argument("--wait", type=int, default=3, help="Seconds to wait before starting update")
    parser.add_argument("--metadata-file", help="Path to release metadata JSON", default=None)
    parser.add_argument("--latest-version", help="Target version label", default=None)

    args = parser.parse_args()

    if args.wait > 0:
        print(f"Waiting {args.wait} seconds for main application to close...")
        time.sleep(args.wait)

    release_metadata = None
    if args.metadata_file:
        metadata_path = Path(args.metadata_file)
        try:
            release_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        finally:
            try:
                metadata_path.unlink()
            except OSError:
                pass

    if not args.no_gui and QT_AVAILABLE:
        installer = UpdateInstaller()
        installer.download_and_install(
            release_metadata=release_metadata,
            latest_version=args.latest_version,
            exe_mode=args.exe_mode,
        )
        return

    updater = Updater(
        ui=None,
        exe_mode=args.exe_mode,
        target_tag=(release_metadata or {}).get("tag_name"),
        release_metadata=release_metadata,
    )
    if args.exe_mode:
        updater.update_exe()
    else:
        updater.update_source()


if __name__ == "__main__":
    main()
