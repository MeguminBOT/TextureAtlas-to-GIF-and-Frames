#!/usr/bin/env python3

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
    from PySide6.QtCore import Qt, QTimer, QThread
    QT_AVAILABLE = True
except ImportError:
    pass


if QT_AVAILABLE:
    class QtUpdateDialog(QDialog):
        """Qt-based dialog for displaying update progress inside the app."""

        LOG_COLORS = {
            "info": "#00ff9d",
            "warning": "#ffcc00",
            "error": "#ff6b6b",
            "success": "#4caf50",
        }

        def __init__(self, parent=None):
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

        def _run_on_ui(self, func, *args, **kwargs):
            if QThread.currentThread() == self.thread():
                func(*args, **kwargs)
            else:
                QTimer.singleShot(0, lambda: func(*args, **kwargs))

        def log(self, message, level="info"):
            color = self.LOG_COLORS.get(level, "#ffffff")
            timestamp = datetime.now().strftime("%H:%M:%S")
            safe_message = html.escape(message)
            formatted = (
                f"<span style='color:#999999;'>[{timestamp}]</span> "
                f"<span style='color:{color};'>{safe_message}</span>"
            )

            def _append():
                self.log_view.append(formatted)
                self.log_view.ensureCursorVisible()

            self._run_on_ui(_append)

        def set_progress(self, value, status_text=""):
            def _update():
                self.progress_bar.setValue(max(0, min(100, value)))
                if status_text:
                    self.progress_label.setText(status_text)

            self._run_on_ui(_update)

        def enable_restart(self, restart_callback):
            def _enable():
                self.restart_callback = restart_callback
                self.restart_button.setEnabled(True)

            self._run_on_ui(_enable)

        def allow_close(self):
            self._run_on_ui(self.close_button.setEnabled, True)

        def _handle_restart(self):
            if callable(self.restart_callback):
                self.restart_callback()

        def close(self):
            self._run_on_ui(super().close)


class UpdateUtilities:
    """Helper methods shared by the updater for filesystem and packaging tasks."""

    @staticmethod
    def find_root(target_name):
        """Walk upward from this file until `target_name` is found and return that directory."""
        root_path = os.path.abspath(__file__)
        while True:
            root_path = os.path.dirname(root_path)
            target_path = os.path.join(root_path, target_name)
            if os.path.exists(target_path):
                return root_path
            new_root = os.path.dirname(root_path)
            if new_root == root_path:  # Reached filesystem root
                break
        return None

    @staticmethod
    def is_file_locked(file_path):
        """Return True when the given file cannot be opened for read/write access."""
        if not os.path.exists(file_path):
            return False
        try:
            with open(file_path, 'r+b'):
                pass
            return False
        except (IOError, OSError, PermissionError):
            return True

    @staticmethod
    def wait_for_file_unlock(file_path, max_attempts=10, delay=1.0):
        """Poll a file until it becomes unlocked or the attempt limit is reached."""
        for attempt in range(max_attempts):
            if not UpdateUtilities.is_file_locked(file_path):
                return True
            time.sleep(delay)
        return False

    @staticmethod
    def extract_7z(archive_path, extract_dir):
        """Extract a .7z archive using py7zr if available, otherwise shell out to 7z."""
        if PY7ZR_AVAILABLE:
            with py7zr.SevenZipFile(archive_path, mode='r') as archive:
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
        """Detect whether the updater is running as a Nuitka-compiled executable."""
        if '__compiled__' in globals():
            return True
        else:
            return False

    @staticmethod
    def find_exe_files(directory):
        """Return the list of .exe filenames that live directly under `directory`."""
        exe_files = []
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isfile(item_path) and item.lower().endswith('.exe'):
                exe_files.append(item)
        return exe_files

    @staticmethod
    def has_write_access(directory):
        """Quickly test whether we can create files inside `directory`."""
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
        """Return True if the current process already has administrative/root privileges."""
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
        """Execute `command` with Windows UAC elevation; returns True if the shell launch succeeds."""
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


class Updater:
    """Download and apply updates, optionally reporting progress through the Qt UI."""

    def __init__(self, ui=None, exe_mode=False):
        """Initialize the updater and create a log file in the app directory when possible."""
        self.ui = ui
        self.exe_mode = exe_mode
        self.log_file = None
        self._setup_log_file()

    def _setup_log_file(self):
        """Create the `logs` directory if needed and configure a timestamped log file."""
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
        """Send a message to the UI or stdout and mirror it into the updater log."""
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
        """Update the progress bar text/value or print a fallback message in console mode."""
        if self.ui:
            self.ui.set_progress(progress, message)
        else:
            print(f"Progress: {progress}% - {message}")

    def enable_restart(self, restart_func):
        """Wire the restart callback into the UI or print manual instructions."""
        if self.ui:
            self.ui.enable_restart(restart_func)
        else:
            print("Update complete! Please restart the application manually.")

    @staticmethod
    def get_latest_release_info():
        """Fetch the latest GitHub release metadata and return the parsed JSON."""
        url = "https://api.github.com/repos/MeguminBOT/TextureAtlas-to-GIF-and-Frames/releases/latest"

        ### URLs for testing purposes:
        # url = "https://api.github.com/repos/MeguminBOT/for-testing-purposes/releases/tags/tatgf-test-quick"
        # url = "https://api.github.com/repos/MeguminBOT/for-testing-purposes/releases/tags/tatgf-test-source-update"
        # url = "https://api.github.com/repos/MeguminBOT/for-testing-purposes/releases/tags/tatgf-test-executable-update"

        response = requests.get(url)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _detect_project_root(directory, exe_mode=False):
        """Check whether `directory` looks like a valid project root for the active mode."""
        if exe_mode:
            required_folders = ['assets', 'ImageMagick']
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
            required_folders = ['assets', 'ImageMagick', 'src']
            required_files = ['latestVersion.txt', 'LICENSE', 'README.md']

            for folder in required_folders:
                if not os.path.isdir(os.path.join(directory, folder)):
                    return False

            for file in required_files:
                if not os.path.isfile(os.path.join(directory, file)):
                    return False

            return True

    @staticmethod
    def _find_github_zipball_root(extract_dir):
        """Return the real project root inside a GitHub release/zipball extraction."""
        extracted_contents = os.listdir(extract_dir)

        if len(extracted_contents) == 1:
            potential_root = os.path.join(extract_dir, extracted_contents[0])
            if os.path.isdir(potential_root):
                root_contents = os.listdir(potential_root)
                project_indicators = ['src', 'README.md', 'assets', 'ImageMagick']
                found_indicators = [item for item in project_indicators if item in root_contents]

                if found_indicators:
                    return potential_root

        for item in extracted_contents:
            item_path = os.path.join(extract_dir, item)
            if os.path.isdir(item_path):
                if Updater._detect_project_root(item_path, exe_mode=False):
                    return item_path

        return None

    def wait_for_main_app_closure(self, max_wait_seconds=30):
        """Poll for locked files to ensure the app is closed before copying in updates."""
        self.log("Waiting for main application to close...")
        self.set_progress(5, "Waiting for application closure...")

        # For executable mode, wait longer since DLLs might need more time to be released
        if self.exe_mode:
            max_wait_seconds = 60
            self.log("Executable mode detected, extending wait time for DLL release...", "info")

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
                        if dll_file.lower().endswith('.dll'):
                            dll_path = os.path.join(imagemagick_dir, dll_file)
                            if UpdateUtilities.is_file_locked(dll_path):
                                locked_files.append(dll_path)

            else:
                project_root = self.find_project_root()
                if project_root:
                    main_py = os.path.join(project_root, "src", "Main.py")
                    if os.path.exists(main_py) and UpdateUtilities.is_file_locked(main_py):
                        locked_files.append(main_py)

            if not locked_files:
                self.log("Application appears to be closed", "success")
                return True
            else:
                if len(locked_files) <= 3:  # Only log a few files to avoid spam
                    self.log(f"Still waiting for {len(locked_files)} files to be released: {', '.join([os.path.basename(f) for f in locked_files[:3]])}", "info")
                else:
                    self.log(f"Still waiting for {len(locked_files)} files to be released...", "info")

            time.sleep(3)

        self.log("Timeout waiting for application closure", "warning")
        return False

    def find_project_root(self):
        """Locate the project root depending on whether we run from source or executable."""
        if self.exe_mode:
            if UpdateUtilities.is_compiled():
                return os.path.dirname(sys.executable)
            else:
                # Extra fallback just in case.
                return os.getcwd()
        else:
            return UpdateUtilities.find_root('README.md')

    def create_updater_backup(self):
        """Save a `.backup` copy of this updater script so it can be restored if needed."""
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
        """Remove the backup updater file created earlier, ignoring errors."""
        try:
            current_script = os.path.abspath(__file__)
            backup_script = current_script + ".backup"

            if os.path.exists(backup_script):
                os.remove(backup_script)
                self.log("Cleaned up updater backup", "info")
        except Exception as e:
            self.log(f"Warning: Could not clean up updater backup: {e}", "warning")

    def update_source(self):
        """Download the latest source zipball and merge it into the local checkout."""
        try:
            self.log("Starting standalone source code update...", "info")
            self.set_progress(10, "Finding project root...")

            project_root = self.find_project_root()
            if not project_root:
                raise Exception("Could not determine project root (README.md not found)")

            self.log(f"Project root: {project_root}", "info")

            self._ensure_write_permissions(project_root)

            self.create_updater_backup()

            if not self.wait_for_main_app_closure():
                self.log("Continuing update despite locked files (may fail)...", "warning")

            self.set_progress(15, "Fetching release information...")

            info = self.get_latest_release_info()
            zip_url = info["zipball_url"]
            self.log(f"Found latest release: {info.get('tag_name', 'unknown')}", "info")

            self.set_progress(20, "Downloading source archive...")
            self.log("Starting download...", "info")

            response = requests.get(zip_url, stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
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
                            self.set_progress(progress, f"Downloaded {downloaded / 1024 / 1024:.1f} MB")

            self.log(f"Download complete: {tmp_path}", "success")
            self.set_progress(60, "Extracting archive...")

            with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                extract_dir = tempfile.mkdtemp()
                self.log(f"Extracting to: {extract_dir}", "info")
                zip_ref.extractall(extract_dir)

            self.set_progress(70, "Detecting project structure...")

            source_project_root = self._find_github_zipball_root(extract_dir)

            # Fallback if the expected structure in the release zipball is not found
            # This will help in case the file structure changes between releases
            if not source_project_root:
                self.log("Release zipball structure not found, trying main branch...", "warning")

                os.remove(tmp_path)
                shutil.rmtree(extract_dir, ignore_errors=True)

                main_branch_url = "https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/archive/refs/heads/main.zip"
                self.log(f"Fallback URL: {main_branch_url}", "info")

                response = requests.get(main_branch_url, stream=True)
                response.raise_for_status()

                total_size = int(response.headers.get('content-length', 0))

                with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_file:
                    tmp_path = tmp_file.name
                    downloaded = 0

                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            tmp_file.write(chunk)
                            downloaded += len(chunk)
                            if total_size:
                                progress = 25 + (downloaded * 35 // total_size)
                                self.set_progress(progress, f"Downloaded {downloaded / 1024 / 1024:.1f} MB")

                with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                    extract_dir = tempfile.mkdtemp()
                    zip_ref.extractall(extract_dir)

                source_project_root = self._find_github_zipball_root(extract_dir)
                if not source_project_root:
                    raise Exception("Could not find project structure in either release or main branch")

            self.log(f"Found source root: {source_project_root}", "success")

            zipball_contents = os.listdir(source_project_root)
            self.log(f"Source contains: {', '.join(zipball_contents)}", "info")

            self.set_progress(80, "Copying files...")

            items_to_copy = ['assets', 'ImageMagick', 'src', 'latestVersion.txt', 'LICENSE', 'README.md']

            optional_items = ['.gitignore', '.github', 'docs', 'setup']
            for item in optional_items:
                if os.path.exists(os.path.join(source_project_root, item)):
                    items_to_copy.append(item)
                    self.log(f"Found optional item: {item}", "info")

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
            self.log("Please restart the application to use the updated version.", "info")

            def restart_app():
                if self.ui:
                    self.ui.close()

                main_py = os.path.join(project_root, "src", "Main.py")
                if os.path.exists(main_py):
                    try:
                        subprocess.Popen([sys.executable, main_py], cwd=os.path.dirname(main_py))
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
        """Download the latest packaged executable build and overwrite the installed files."""
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
                self.log("Continuing update despite locked files (may fail)...", "warning")

            self._ensure_write_permissions(app_root)

            self.set_progress(15, "Fetching release information...")

            info = self.get_latest_release_info()
            self.log(f"Found latest release: {info.get('tag_name', 'unknown')}", "info")

            assets = info.get('assets', [])
            seven_z_asset = None

            for asset in assets:
                if asset['name'].lower().endswith('.7z'):
                    seven_z_asset = asset
                    break

            if not seven_z_asset:
                raise Exception("No .7z release file found in latest release")

            download_url = seven_z_asset['browser_download_url']
            file_size = seven_z_asset.get('size', 0)

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
                            self.set_progress(progress, f"Downloaded {downloaded / 1024 / 1024:.1f} MB")

            self.log(f"Download complete: {tmp_path}", "success")
            self.set_progress(60, "Extracting archive...")

            extract_dir = tempfile.mkdtemp()
            self.log(f"Extracting to: {extract_dir}", "info")

            if not UpdateUtilities.extract_7z(tmp_path, extract_dir):
                raise Exception("Failed to extract 7z archive. Make sure py7zr is installed or 7z command is available.")

            self.set_progress(70, "Detecting release structure...")

            extracted_contents = os.listdir(extract_dir)
            self.log(f"Extracted contents: {', '.join(extracted_contents)}", "info")

            release_root = extract_dir
            if len(extracted_contents) == 1 and os.path.isdir(os.path.join(extract_dir, extracted_contents[0])):
                potential_root = os.path.join(extract_dir, extracted_contents[0])
                contents = os.listdir(potential_root)
                if any(item.lower().endswith('.exe') for item in contents):
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
                backup_dir = os.path.join(tempfile.gettempdir(), f"app_backup_{int(time.time())}")
                os.makedirs(backup_dir, exist_ok=True)

                backup_exe = os.path.join(backup_dir, os.path.basename(current_exe))
                try:
                    shutil.copy2(current_exe, backup_exe)
                    self.log(f"Backed up current executable to: {backup_exe}", "info")
                except Exception as e:
                    self.log(f"Warning: Could not backup current executable: {e}", "warning")

            items_to_copy = ['assets', 'ImageMagick', 'LICENSE', 'README.md']
            items_to_copy.extend(exe_files)

            optional_items = ['docs', '.gitignore']
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
                            if item.lower().endswith('.exe') and os.path.exists(dst_path):
                                backup_name = dst_path + ".old"
                                if os.path.exists(backup_name):
                                    try:
                                        os.remove(backup_name)
                                    except Exception:
                                        pass
                                try:
                                    os.rename(dst_path, backup_name)
                                    self.log(f"Renamed old executable to {backup_name}", "info")
                                except Exception as e:
                                    self.log(f"Could not rename old executable: {e}", "warning")

                            self._copy_file_with_retry(src_path, dst_path)
                        self.log(f"Successfully installed {item}", "success")
                    except Exception as e:
                        self.log(f"Failed to install {item}: {str(e)}", "error")
                        if item.lower().endswith('.exe'):
                            raise e
                else:
                    self.log(f"Warning: {item} not found in release", "warning")

            os.remove(tmp_path)
            shutil.rmtree(extract_dir, ignore_errors=True)
            self.log("Cleanup completed", "info")

            self.set_progress(100, "Update complete!")
            self.log("Executable update completed successfully!", "success")
            self.log("Please restart the application to use the updated version.", "info")

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
                            process = subprocess.Popen([main_exe], cwd=app_root, shell=True)
                            self.log(f"Started process with PID: {process.pid}", "success")
                        else:
                            # For non-Nuitka (shouldn't happen in exe mode but just in case)
                            process = subprocess.Popen([main_exe], cwd=app_root)
                            self.log(f"Started process with PID: {process.pid}", "success")

                        self.log("Application restart initiated successfully", "success")

                        # Give the process a moment to start
                        import time
                        time.sleep(2)

                    except Exception as e:
                        self.log(f"Failed to restart application: {e}", "error")
                        self.log(f"Please manually start the application from: {main_exe}", "warning")
                else:
                    self.log("No executable found to restart", "error")
                    self.log(f"Available files in {app_root}: {', '.join(os.listdir(app_root))}", "info")

                sys.exit(0)

            self.enable_restart(restart_app)

        except Exception as e:
            self.log(f"Executable update failed: {str(e)}", "error")
            self.set_progress(0, "Update failed!")
            if self.ui:
                self.ui.log(f"Executable update failed: {str(e)}", "error")

    def _merge_directory(self, src_dir, dst_dir):
        """Recursively copy a tree from `src_dir` into `dst_dir`, overwriting file contents."""
        for root, dirs, files in os.walk(src_dir):
            rel_path = os.path.relpath(root, src_dir)
            if rel_path == '.':
                target_dir = dst_dir
            else:
                target_dir = os.path.join(dst_dir, rel_path)

            os.makedirs(target_dir, exist_ok=True)

            for file in files:
                src_file = os.path.join(root, file)
                dst_file = os.path.join(target_dir, file)
                self._copy_file_with_retry(src_file, dst_file)

    def _copy_file_with_retry(self, src_file, dst_file, max_attempts=5):
        """Copy a file with retry/backoff logic, handling locked DLLs when necessary."""
        for attempt in range(max_attempts):
            try:
                os.makedirs(os.path.dirname(dst_file), exist_ok=True)

                if dst_file.lower().endswith('.dll') and os.path.exists(dst_file):
                    backup_dll = dst_file + ".old"
                    try:
                        if os.path.exists(backup_dll):
                            os.remove(backup_dll)
                        os.rename(dst_file, backup_dll)
                        self.log(f"Backed up existing DLL: {os.path.basename(dst_file)}", "info")
                    except Exception as e:
                        self.log(f"Could not backup DLL {os.path.basename(dst_file)}: {e}", "warning")

                shutil.copy2(src_file, dst_file)
                return

            except (PermissionError, OSError) as e:
                if attempt < max_attempts - 1:
                    self.log(f"Copy attempt {attempt + 1} failed for {os.path.basename(dst_file)}: {e}", "warning")
                    self.log("Waiting before retry...", "info")
                    time.sleep(3)
                else:
                    if dst_file.lower().endswith('.dll'):
                        try:
                            temp_name = dst_file + ".new"
                            shutil.copy2(src_file, temp_name)
                            if os.path.exists(dst_file):
                                os.remove(dst_file)
                            os.rename(temp_name, dst_file)
                            self.log(f"Successfully updated DLL using temp file method: {os.path.basename(dst_file)}", "success")
                            return

                        except Exception as temp_e:
                            self.log(f"Temp file method also failed for {os.path.basename(dst_file)}: {temp_e}", "error")
                    raise e

    def _ensure_write_permissions(self, target_dir):
        """Request elevation when the updater lacks permission to modify `target_dir`."""
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
        """Create the command used to relaunch the updater with admin rights."""
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
    """Qt-integrated installer that reuses Updater logic within the main app."""

    def __init__(self, parent=None):
        """Store the optional parent widget and ensure Qt is available."""
        if not QT_AVAILABLE:
            raise ImportError("PySide6 is required for the integrated updater UI")
        self.parent = parent

    def download_and_install(self, download_url=None, latest_version=None, parent_window=None, exe_mode=None):
        """Launch the updater dialog and run the appropriate update flow."""

        dialog_parent = parent_window or self.parent
        QApplication.instance() or QApplication(sys.argv)
        dialog = QtUpdateDialog(dialog_parent)
        exe_mode = UpdateUtilities.is_compiled() if exe_mode is None else exe_mode
        updater = Updater(ui=dialog, exe_mode=exe_mode)

        mode_label = "executable" if exe_mode else "source"
        dialog.log(f"Starting {mode_label} update...", "info")
        if latest_version:
            dialog.log(f"Target version: {latest_version}", "info")
        if download_url:
            dialog.log(
                "Fetch the latest release.",
                "warning",
            )

        def _run_update():
            try:
                if exe_mode:
                    updater.update_exe()
                else:
                    updater.update_source()
            except Exception as err:
                dialog.log(f"Update process encountered an error: {err}", "error")
                dialog.allow_close()
            else:
                dialog.allow_close()

        worker = threading.Thread(target=_run_update, daemon=True)
        worker.start()
        dialog.exec()


def main():
    parser = argparse.ArgumentParser(description="Standalone updater for TextureAtlas-to-GIF-and-Frames")
    parser.add_argument("--no-gui", action="store_true", help="Run in console mode without GUI")
    parser.add_argument("--exe-mode", action="store_true", help="Run in executable update mode")
    parser.add_argument("--wait", type=int, default=3, help="Seconds to wait before starting update")

    args = parser.parse_args()

    if args.wait > 0:
        print(f"Waiting {args.wait} seconds for main application to close...")
        time.sleep(args.wait)

    if not args.no_gui and QT_AVAILABLE:
        installer = UpdateInstaller()
        installer.download_and_install(exe_mode=args.exe_mode)
        return

    updater = Updater(ui=None, exe_mode=args.exe_mode)
    if args.exe_mode:
        updater.update_exe()
    else:
        updater.update_source()


if __name__ == "__main__":
    main()
