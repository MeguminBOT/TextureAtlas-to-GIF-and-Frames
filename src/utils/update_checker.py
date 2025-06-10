import os
from utils.utilities import Utilities
import shutil
import subprocess
import sys
import tempfile
import zipfile
import requests
import py7zr
import tkinter as tk
import threading
import time
from datetime import datetime
from tkinter import ttk, messagebox


class UpdateConsoleWindow:
    """Console-like window for showing detailed update progress"""

    def __init__(self, title="Update Progress", width=600, height=400):
        self.window = tk.Toplevel()
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
        self.window.after(0, self._log_safe, message, level)

    def _log_safe(self, message, level):
        timestamp = datetime.now().strftime("%H:%M:%S")

        self.console_text.config(state=tk.NORMAL)
        self.console_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
        self.console_text.insert(tk.END, f"{message}\n", level)
        self.console_text.see(tk.END)
        self.console_text.config(state=tk.DISABLED)

        self.window.update_idletasks()

    def set_progress(self, value, status_text=""):
        self.window.after(0, self._set_progress_safe, value, status_text)

    def _set_progress_safe(self, value, status_text):
        self.progressbar['value'] = value
        if status_text:
            self.progress_label.config(text=status_text)
        self.window.update_idletasks()

    def enable_restart(self, restart_callback):
        self.window.after(0, self._enable_restart_safe, restart_callback)

    def _enable_restart_safe(self, restart_callback):
        self.restart_btn.config(state=tk.NORMAL, command=restart_callback)

    def close(self):
        try:
            self.window.grab_release()
            self.window.destroy()
        except:
            pass

class UpdateChecker:
    """
    A class for managing update checks and update installation for the application.

    Methods:
        is_frozen():
            Return True if the app is running as a frozen executable (PyInstaller/standalone), else False.
        get_latest_release_info():
            Fetch and return the latest GitHub release info as a dict.
        update_source():
            Download and update the app source code (for non-frozen mode). Supports git pull or zip download and extraction.
        update_exe():
            Download the latest .7z release from GitHub, extract it using py7zr, and replace the running executable (for frozen mode).
            Handles progress UI, extraction, and safe replacement with a batch script.
        check_for_updates(current_version, auto_update=False, parent_window=None):
            Check for updates by comparing the current version to the latest version online.
            If an update is available, prompt the user (unless auto_update is True), then download and install the update (source or exe as appropriate).
            Supports both manual and auto-update flows, and can use a parent Tk window for dialogs.
    """

    @staticmethod
    def is_frozen():
        return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

    @staticmethod
    def get_latest_release_info():
        url = "https://api.github.com/repos/MeguminBOT/TextureAtlas-to-GIF-and-Frames/releases/latest"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def update_source():
        console = UpdateConsoleWindow("Source Code Update", 650, 450)

        def do_update():
            try:
                console.log("Starting source code update process...", "info")
                console.set_progress(5, "Checking update method...")

                if shutil.which("git") and os.path.isdir(".git"):
                    # Find the project root (the folder containing README.md)
                    project_root = Utilities.find_root('README.md')
                    if not project_root:
                        raise Exception("Could not determine project root (README.md not found)")
                    console.log(f"Git detected, attempting git pull in {project_root}...", "info")
                    console.set_progress(10, "Running git pull...")

                    try:
                        result = subprocess.run(
                            ["git", "pull"], 
                            capture_output=True, 
                            text=True, 
                            check=True,
                            cwd=project_root
                        )

                        console.log(f"Git pull output: {result.stdout.strip()}", "success")
                        if result.stderr:
                            console.log(f"Git warnings: {result.stderr.strip()}", "warning")

                        console.set_progress(100, "Update complete!")
                        console.log("Source code updated successfully via git pull!", "success")
                        console.log("Please restart the application to use the updated version.", "info")

                        def restart_app():
                            console.close()
                            python = sys.executable
                            os.execl(python, python, *sys.argv)

                        console.enable_restart(restart_app)

                    except subprocess.CalledProcessError as e:
                        console.log(f"Git pull failed with return code {e.returncode}", "error")
                        console.log(f"Error output: {e.stderr}", "error")
                        raise e

                else:
                    console.log("Git not available, downloading source archive...", "info")
                    console.set_progress(10, "Fetching release information...")


                    info = UpdateChecker.get_latest_release_info()
                    zip_url = info["zipball_url"]
                    console.log(f"Found latest release: {info.get('tag_name', 'unknown')}", "info")
                    console.log(f"Download URL: {zip_url}", "info")

                    console.set_progress(20, "Downloading source archive...")


                    console.log("Starting download...", "info")
                    response = requests.get(zip_url, stream=True)
                    response.raise_for_status()

                    total_size = int(response.headers.get('content-length', 0))
                    console.log(f"Download size: {total_size / 1024 / 1024:.2f} MB", "info")

                    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_file:
                        tmp_path = tmp_file.name
                        downloaded = 0

                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                tmp_file.write(chunk)
                                downloaded += len(chunk)
                                if total_size:
                                    progress = 20 + (downloaded * 40 // total_size)
                                    console.set_progress(progress, f"Downloaded {downloaded / 1024 / 1024:.1f} MB")

                    console.log(f"Download complete: {tmp_path}", "success")
                    console.set_progress(60, "Extracting archive...")

                    with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                        extract_dir = tempfile.mkdtemp()
                        console.log(f"Extracting to: {extract_dir}", "info")
                        zip_ref.extractall(extract_dir)

                    extracted_contents = os.listdir(extract_dir)
                    if len(extracted_contents) != 1 or not os.path.isdir(os.path.join(extract_dir, extracted_contents[0])):
                        raise Exception("Unexpected archive structure")

                    source_dir = os.path.join(extract_dir, extracted_contents[0])
                    console.log(f"Source directory: {source_dir}", "info")

                    console.set_progress(80, "Copying files...")

                    # Find the project root (the folder containing README.md)
                    project_root = Utilities.find_root('README.md')
                    if not project_root:
                        raise Exception("Could not determine project root (README.md not found)")
                    console.log(f"Target directory: {project_root}", "info")


                    # Recursively copy all contents of source_dir into project_root, merging folders and overwriting files
                    def merge_copy(src, dst):
                        for item in os.listdir(src):
                            s = os.path.join(src, item)
                            d = os.path.join(dst, item)
                            if os.path.isdir(s):
                                if os.path.exists(d):
                                    merge_copy(s, d)
                                else:
                                    shutil.copytree(s, d)
                            else:
                                os.makedirs(os.path.dirname(d), exist_ok=True)
                                shutil.copy2(s, d)

                    console.log("Merging extracted files into project root...", "info")
                    merge_copy(source_dir, project_root)
                    console.log("All files and folders merged successfully.", "success")

                    os.remove(tmp_path)
                    shutil.rmtree(extract_dir, ignore_errors=True)
                    console.log("Cleanup completed", "info")

                    console.set_progress(100, "Update complete!")
                    console.log("Source code update completed successfully!", "success")
                    console.log("Please restart the application to use the updated version.", "info")

                    def restart_app():
                        console.close()
                        python = sys.executable
                        os.execl(python, python, *sys.argv)

                    console.enable_restart(restart_app)

            except Exception as e:
                console.log(f"Update failed: {str(e)}", "error")
                console.set_progress(0, "Update failed!")
                messagebox.showerror("Update Failed", f"Source update failed: {str(e)}")

        threading.Thread(target=do_update, daemon=True).start()

    @staticmethod
    def update_exe():
        console = UpdateConsoleWindow("Executable Update", 650, 450)

        def do_update():
            try:
                console.log("Starting executable update process...", "info")
                console.set_progress(5, "Fetching release information...")

                info = UpdateChecker.get_latest_release_info()
                console.log(f"Found latest release: {info.get('tag_name', 'unknown')}", "info")
                console.log(f"Release name: {info.get('name', 'unknown')}", "info")

                z7_asset = None
                for asset in info.get("assets", []):
                    console.log(f"Available asset: {asset['name']} ({asset['size']} bytes)", "info")
                    if asset["name"].endswith(".7z"):
                        z7_asset = asset
                        break

                if not z7_asset:
                    console.log("No .7z asset found in latest release", "error")
                    console.set_progress(0, "Update failed!")
                    messagebox.showerror("Update Failed", "No .7z asset found in latest release.")
                    return

                console.log(f"Using asset: {z7_asset['name']}", "success")
                console.log(f"Asset size: {z7_asset['size'] / 1024 / 1024:.2f} MB", "info")

                z7_url = z7_asset["browser_download_url"]
                exe_path = sys.executable
                console.log(f"Current executable: {exe_path}", "info")

                console.set_progress(10, "Preparing temporary directory...")
                temp_dir = tempfile.mkdtemp()
                console.log(f"Temporary directory: {temp_dir}", "info")

                z7_path = os.path.join(temp_dir, z7_asset["name"])

                console.set_progress(15, "Downloading update...")
                console.log("Starting download...", "info")

                response = requests.get(z7_url, stream=True)
                response.raise_for_status()

                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0

                with open(z7_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size:
                                progress = 15 + (downloaded * 30 // total_size)
                                console.set_progress(progress, f"Downloaded {downloaded / 1024 / 1024:.1f} MB")

                console.log(f"Download complete: {z7_path}", "success")
                console.set_progress(45, "Extracting update archive...")

                extract_dir = os.path.join(temp_dir, "extracted")
                os.makedirs(extract_dir, exist_ok=True)
                console.log(f"Extracting to: {extract_dir}", "info")

                try:
                    with py7zr.SevenZipFile(z7_path, mode='r') as archive:
                        file_list = archive.getnames()
                        console.log(f"Archive contains {len(file_list)} files", "info")

                        archive.extractall(path=extract_dir)
                        console.log("Extraction completed successfully", "success")

                except Exception as e:
                    console.log(f"Extraction failed: {str(e)}", "error")
                    console.log("Make sure the .7z file is valid and not corrupted", "error")
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    console.set_progress(0, "Update failed!")
                    messagebox.showerror("Update Failed", f"Extraction failed: {str(e)}")
                    return

                console.set_progress(70, "Searching for new executable...")

                new_exe_path = None
                exe_files_found = []

                for root, dirs, files in os.walk(extract_dir):
                    for file in files:
                        if file.lower().endswith(".exe"):
                            full_path = os.path.join(root, file)
                            exe_files_found.append(full_path)
                            console.log(f"Found executable: {full_path}", "info")

                            current_exe_name = os.path.basename(exe_path).lower()
                            if file.lower() == current_exe_name:
                                new_exe_path = full_path
                            elif new_exe_path is None:
                                new_exe_path = full_path

                if not new_exe_path:
                    console.log("No executable (.exe) found in extracted update", "error")
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    console.set_progress(0, "Update failed!")
                    messagebox.showerror("Update Failed", "No executable found in extracted update.")
                    return

                console.log(f"Using executable: {new_exe_path}", "success")

                console.set_progress(80, "Preparing replacement...")

                staged_exe = exe_path + ".new"
                bat_path = exe_path + ".update.bat"

                console.log(f"Staging new executable: {staged_exe}", "info")
                shutil.copy2(new_exe_path, staged_exe)

                if not os.path.exists(staged_exe):
                    console.log("Failed to stage new executable", "error")
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    console.set_progress(0, "Update failed!")
                    messagebox.showerror("Update Failed", "Failed to stage new executable.")
                    return

                staged_size = os.path.getsize(staged_exe)
                console.log(f"Staged executable size: {staged_size / 1024 / 1024:.2f} MB", "info")

                console.set_progress(90, "Creating update script...")
                
                console.log(f"Creating update script: {bat_path}", "info")
                with open(bat_path, "w") as f:
                    f.write(f"""@echo off
echo Update Script Starting...
echo Waiting for application to close...
ping 127.0.0.1 -n 3 > nul

echo Backing up current executable...
if exist "{exe_path}.backup" del "{exe_path}.backup"
move "{exe_path}" "{exe_path}.backup"

echo Installing new executable...
move "{staged_exe}" "{exe_path}"

echo Starting updated application...
start "" "{exe_path}"

echo Cleaning up...
if exist "{exe_path}.backup" del "{exe_path}.backup"
del "%~f0"
""")

                shutil.rmtree(temp_dir, ignore_errors=True)
                console.log("Temporary files cleaned up", "info")

                console.set_progress(100, "Update ready!")
                console.log("Executable update preparation completed successfully!", "success")
                console.log("The application will be replaced when you restart.", "info")
                console.log(f"Update script created: {bat_path}", "info")

                def restart_now():
                    console.log("Starting update script and exiting...", "info")
                    console.close()
                    os.startfile(bat_path)
                    sys.exit(0)

                console.enable_restart(restart_now)

            except Exception as e:
                console.log(f"Executable update failed: {str(e)}", "error")
                console.set_progress(0, "Update failed!")
                messagebox.showerror("Update Failed", f"Executable update failed: {str(e)}")

        threading.Thread(target=do_update, daemon=True).start()

    @staticmethod
    def check_for_updates(current_version, auto_update=False, parent_window=None):
        try:
            print(f"Checking for updates... Current version: {current_version}")

            response = requests.get(
                'https://raw.githubusercontent.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/main/latestVersion.txt',
                timeout=10
            )
            response.raise_for_status()
            latest_version = response.text.strip()

            print(f"Latest version available: {latest_version}")

            if latest_version > current_version:
                print("Update available!")

                parent = parent_window if parent_window is not None else tk.Tk()
                if parent_window is None:
                    parent.withdraw()

                if auto_update:
                    print("Auto-update enabled, starting update process...")
                    if UpdateChecker.is_frozen():
                        print("Running as executable, using executable update method")
                        UpdateChecker.update_exe()
                    else:
                        print("Running from source, using source update method")
                        UpdateChecker.update_source()
                else:
                    update_type = "executable" if UpdateChecker.is_frozen() else "source code"
                    message = (
                        f"An update is available!\n\n"
                        f"Current version: {current_version}\n"
                        f"Latest version: {latest_version}\n\n"
                        f"Update method: {update_type}\n\n"
                        f"Do you want to download and install it now?\n"
                        f"The application will restart after updating."
                    )

                    result = messagebox.askyesno(
                        "Update Available", 
                        message, 
                        parent=parent
                    )

                    if result:
                        print("User chose to update.")
                        if UpdateChecker.is_frozen():
                            print("Starting executable update...")
                            UpdateChecker.update_exe()
                        else:
                            print("Starting source update...")
                            UpdateChecker.update_source()
                    else:
                        print("User chose not to update.")

                if parent_window is None:
                    parent.destroy()

            else:
                print("You are using the latest version of the application.")

        except requests.exceptions.Timeout:
            print("Update check timed out - no internet connection or server not responding")

        except requests.exceptions.ConnectionError:
            print("No internet connection available for update check")

        except requests.exceptions.RequestException as err:
            print(f"Network error during update check: {err}")

        except Exception as err:
            print(f"Unexpected error during update check: {err}")
            import traceback
            traceback.print_exc()