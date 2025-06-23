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

try:
    import py7zr
    PY7ZR_AVAILABLE = True
except ImportError:
    PY7ZR_AVAILABLE = False

GUI_AVAILABLE = False
try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    GUI_AVAILABLE = True
except ImportError:
    print("GUI not available, running in console mode")


class UpdateWindow:
    """
    A class for displaying and managing the update progress window.

    Attributes:
        window (tk.Tk): The main update window.
        console_frame (tk.Frame): Frame containing the console text and scrollbar.
        console_text (tk.Text): Text widget for logging update messages.
        scrollbar (ttk.Scrollbar): Scrollbar for the console text widget.
        progress_frame (tk.Frame): Frame containing progress elements.
        progressbar (ttk.Progressbar): Progress bar for update status.
        progress_label (tk.Label): Label for progress status.
        button_frame (tk.Frame): Frame containing control buttons.
        restart_btn (tk.Button): Button to restart the application.
        close_btn (tk.Button): Button to close the update window.

    Methods:
        log(message, level="info"):
            Log a message to the update window console.
        set_progress(value, status_text=""):
            Set the progress bar value and status text.
        enable_restart(restart_callback):
            Enable the restart button and set its callback.
        close():
            Close the update window.
    """

    def __init__(self, title="Update Progress", width=600, height=480):
        if not GUI_AVAILABLE:
            raise ImportError("GUI not available")

        self.window = tk.Tk()
        self.window.title(title)
        self.window.geometry(f"{width}x{height}")
        self.window.configure(bg='#1e1e1e')

        self.window.transient()
        self.window.grab_set()
        self.window.focus_set()

        self.console_frame = tk.Frame(self.window, bg='#1e1e1e')
        self.console_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.console_text = tk.Text(
            self.console_frame,
            bg='#1e1e1e',
            fg='#ffffff',
            font=('Consolas', 10),
            insertbackground='#ffffff',
            selectbackground='#3d3d3d',
            wrap=tk.WORD,
            state=tk.DISABLED
        )

        self.scrollbar = ttk.Scrollbar(self.console_frame, orient=tk.VERTICAL, command=self.console_text.yview)
        self.console_text.configure(yscrollcommand=self.scrollbar.set)

        self.console_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.progress_frame = tk.Frame(self.window, bg='#1e1e1e')
        self.progress_frame.pack(fill=tk.X, padx=10, pady=5)

        self.progress_label = tk.Label(
            self.progress_frame,
            text="Initializing...",
            bg='#1e1e1e',
            fg='#ffffff',
            font=('Arial', 9)
        )
        self.progress_label.pack(anchor=tk.W)

        self.progressbar = ttk.Progressbar(
            self.progress_frame,
            orient="horizontal",
            length=width-20,
            mode="determinate"
        )
        self.progressbar.pack(fill=tk.X, pady=(5, 0))

        self.button_frame = tk.Frame(self.window, bg='#1e1e1e')
        self.button_frame.pack(fill=tk.X, padx=10, pady=5)

        self.restart_btn = tk.Button(
            self.button_frame,
            text="Restart Application",
            state=tk.DISABLED,
            bg='#0d7377',
            fg='white',
            font=('Arial', 9, 'bold'),
            relief=tk.FLAT,
            padx=20
        )
        self.restart_btn.pack(side=tk.RIGHT, padx=(5, 0))

        self.close_btn = tk.Button(
            self.button_frame,
            text="Close",
            command=self.close,
            bg='#444444',
            fg='white',
            font=('Arial', 9),
            relief=tk.FLAT,
            padx=20
        )
        self.close_btn.pack(side=tk.RIGHT)

        self.console_text.tag_configure("info", foreground="#00ff00")
        self.console_text.tag_configure("warning", foreground="#ffff00")
        self.console_text.tag_configure("error", foreground="#ff0000")
        self.console_text.tag_configure("success", foreground="#00ff88")
        self.console_text.tag_configure("timestamp", foreground="#888888")

        self.window.update()

    def log(self, message, level="info"):
        if hasattr(self, 'window') and self.window:
            self.window.after(0, self._log_safe, message, level)

    def _log_safe(self, message, level):
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")

            self.console_text.config(state=tk.NORMAL)
            self.console_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
            self.console_text.insert(tk.END, f"{message}\n", level)
            self.console_text.see(tk.END)
            self.console_text.config(state=tk.DISABLED)

            self.window.update_idletasks()
        except Exception:
            pass

    def set_progress(self, value, status_text=""):
        if hasattr(self, 'window') and self.window:
            self.window.after(0, self._set_progress_safe, value, status_text)

    def _set_progress_safe(self, value, status_text):
        try:
            self.progressbar['value'] = value
            if status_text:
                self.progress_label.config(text=status_text)
            self.window.update_idletasks()
        except Exception:
            pass

    def enable_restart(self, restart_callback):
        if hasattr(self, 'window') and self.window:
            self.window.after(0, self._enable_restart_safe, restart_callback)

    def _enable_restart_safe(self, restart_callback):
        try:
            self.restart_btn.config(state=tk.NORMAL, command=restart_callback)
        except Exception:
            pass

    def close(self):
        try:
            if hasattr(self, 'window') and self.window:
                self.window.grab_release()
                self.window.destroy()
        except Exception:
            pass


class UpdateUtilities:
    """
    A utility class for update-related file and directory operations.
    Contains duplicates from utils/utilities.py, but are required here as well.

    Attributes:
        None

    Methods:
        find_root(target_name):
            Find project root by looking for a target file or folder.
        is_file_locked(file_path):
            Check if a file is currently locked.
        wait_for_file_unlock(file_path, max_attempts=10, delay=1.0):
            Wait for a file to become unlocked.
        extract_7z(archive_path, extract_dir):
            Extract a 7z archive to a directory.
        is_compiled():
            Check if running as a Nuitka-compiled Nuitka executable.
        find_exe_files(directory):
            Find .exe files in a directory.
    """

    @staticmethod
    def find_root(target_name):
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
        for attempt in range(max_attempts):
            if not UpdateUtilities.is_file_locked(file_path):
                return True
            time.sleep(delay)
        return False

    @staticmethod
    def extract_7z(archive_path, extract_dir):
        if PY7ZR_AVAILABLE:
            with py7zr.SevenZipFile(archive_path, mode='r') as archive:
                archive.extractall(path=extract_dir)
            return True
        else:
            # Fallback to system 7z command
            try:
                cmd = ['7z', 'x', archive_path, f'-o{extract_dir}', '-y']
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                return False

    @staticmethod
    def is_compiled():
        if '__compiled__' in globals():
            return True
        else:
            return False

    @staticmethod
    def find_exe_files(directory):
        exe_files = []
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isfile(item_path) and item.lower().endswith('.exe'):
                exe_files.append(item)
        return exe_files


class Updater:
    """
    A class for managing the update process of the application.

    Attributes:
        use_gui (bool): Whether to use the GUI for updates.
        exe_mode (bool): Whether running in executable update mode.
        console (UpdateWindow or None): The update window or None for console mode.
        log_file (str or None): Path to the log file for saving logs.

    Methods:
        log(message, level="info"):
            Log a message to the update console or print to stdout, and save to log file.
        set_progress(progress, message=""):
            Set the update progress and status message.
        enable_restart(restart_func):
            Enable the restart button or print restart instructions.
        get_latest_release_info():
            Get the latest release info from GitHub.
        find_project_root():
            Find the project root directory.
        wait_for_main_app_closure(max_wait_seconds=30):
            Wait for the main application to close before updating.
        create_updater_backup():
            Create a backup of the updater script.
        cleanup_updater_backup():
            Remove the updater backup script.
        update_source():
            Perform the update process for the source code.
        update_exe():
            Perform the update process for the executable.
        _detect_project_root(directory):
            Detect if a directory is a valid project root.
        _find_github_zipball_root(extract_dir):
            Find the root directory in a GitHub zipball extraction.
        _merge_directory(src_dir, dst_dir):
            Merge the contents of two directories.
        _copy_file_with_retry(src_file, dst_file, max_attempts=5):
            Copy a file with retry logic on failure.
    """

    def __init__(self, use_gui=True, exe_mode=False):
        self.use_gui = use_gui and GUI_AVAILABLE
        self.exe_mode = exe_mode
        self.console = None
        self.log_file = None
        if self.use_gui:
            try:
                self.console = UpdateWindow("TextureAtlas to GIF and Frames Updater", 650, 480)
            except Exception:
                self.use_gui = False
                print("Failed to create GUI, falling back to console mode")
        self._setup_log_file()

    def _setup_log_file(self):
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
        if self.console:
            self.console.log(message, level)
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
                if not self.console:
                    print(f"[WARNING] Could not write to log file: {e}")

    def set_progress(self, progress, message=""):
        if self.console:
            self.console.set_progress(progress, message)
        else:
            print(f"Progress: {progress}% - {message}")

    def enable_restart(self, restart_func):
        if self.console:
            self.console.enable_restart(restart_func)
        else:
            print("Update complete! Please restart the application manually.")

    @staticmethod
    def get_latest_release_info():
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
        if self.exe_mode:
            if UpdateUtilities.is_compiled():
                return os.path.dirname(sys.executable)
            else:
                # Extra fallback just in case.
                return os.getcwd()
        else:
            return UpdateUtilities.find_root('README.md')

    def create_updater_backup(self):
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
        try:
            current_script = os.path.abspath(__file__)
            backup_script = current_script + ".backup"

            if os.path.exists(backup_script):
                os.remove(backup_script)
                self.log("Cleaned up updater backup", "info")
        except Exception as e:
            self.log(f"Warning: Could not clean up updater backup: {e}", "warning")

    def update_source(self):
        try:
            self.log("Starting standalone source code update...", "info")
            self.set_progress(10, "Finding project root...")

            project_root = self.find_project_root()
            if not project_root:
                raise Exception("Could not determine project root (README.md not found)")

            self.log(f"Project root: {project_root}", "info")

            active_updater = self.create_updater_backup()

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
                if self.console:
                    self.console.close()

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
            if self.console and GUI_AVAILABLE:
                messagebox.showerror("Update Failed", f"Standalone update failed: {str(e)}")

    def update_exe(self):
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
                if self.console:
                    self.console.close()

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
            if self.console and GUI_AVAILABLE:
                messagebox.showerror("Update Failed", f"Executable update failed: {str(e)}")

    def _merge_directory(self, src_dir, dst_dir):
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


def main():
    parser = argparse.ArgumentParser(description="Standalone updater for TextureAtlas-to-GIF-and-Frames")
    parser.add_argument("--no-gui", action="store_true", help="Run in console mode without GUI")
    parser.add_argument("--exe-mode", action="store_true", help="Run in executable update mode")
    parser.add_argument("--wait", type=int, default=3, help="Seconds to wait before starting update")

    args = parser.parse_args()

    if args.wait > 0:
        print(f"Waiting {args.wait} seconds for main application to close...")
        time.sleep(args.wait)

    updater = Updater(use_gui=not args.no_gui, exe_mode=args.exe_mode)

    if updater.use_gui:
        def run_update():
            if args.exe_mode:
                updater.update_exe()
            else:
                updater.update_source()

        thread = threading.Thread(target=run_update, daemon=True)
        thread.start()

        if updater.console:
            updater.console.window.mainloop()
    else:
        if args.exe_mode:
            updater.update_exe()
        else:
            updater.update_source()


if __name__ == "__main__":
    main()
