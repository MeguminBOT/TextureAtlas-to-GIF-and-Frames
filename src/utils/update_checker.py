import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
import requests
import py7zr
import tkinter as tk
from tkinter import ttk, messagebox

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
        return getattr(sys, 'frozen', False)

    @staticmethod
    def get_latest_release_info():
        url = "https://api.github.com/repos/MeguminBOT/TextureAtlas-to-GIF-and-Frames/releases/latest"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def update_source():
        progress_win = tk.Toplevel()
        progress_win.title("Updating (Source)")
        progress_win.geometry("400x180")
        progress_label = tk.Label(progress_win, text="Starting update...", anchor="w", justify="left")
        progress_label.pack(fill=tk.X, padx=10, pady=5)
        progressbar = ttk.Progressbar(progress_win, orient="horizontal", length=350, mode="determinate")
        progressbar.pack(padx=10, pady=5)
        progress_text = tk.Text(progress_win, height=5, width=48, state="disabled")
        progress_text.pack(padx=10, pady=5)
        progress_win.update()

        def set_status(msg):
            progress_label.config(text=msg)
            progress_text.config(state="normal")
            progress_text.insert(tk.END, msg + "\n")
            progress_text.see(tk.END)
            progress_text.config(state="disabled")
            progress_win.update()

        if shutil.which("git") and os.path.isdir(".git"):
            try:
                set_status("Running git pull...")
                subprocess.run(["git", "pull"], check=True)
                set_status("Source code updated via git pull. Please restart the application.")
                progressbar['value'] = 100
            except Exception as e:
                set_status(f"Git pull failed: {e}")
                messagebox.showerror("Update failed", f"Git pull failed: {e}")
        else:
            try:
                set_status("Fetching release info...")
                info = UpdateChecker.get_latest_release_info()
                zip_url = info["zipball_url"]
                set_status("Downloading latest source zip...")
                r = requests.get(zip_url, stream=True)
                total = int(r.headers.get('content-length', 0))
                with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
                    tmp_path = tmp.name
                    downloaded = 0
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            tmp.write(chunk)
                            downloaded += len(chunk)
                            if total:
                                progressbar['value'] = min(100, downloaded * 100 // total)
                                progress_win.update()
                set_status("Extracting zip...")
                with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                    extract_dir = tempfile.mkdtemp()
                    zip_ref.extractall(extract_dir)
                set_status("Copying files...")

                for root, dirs, files in os.walk(extract_dir):
                    rel_path = os.path.relpath(root, extract_dir)
                    dest_dir = os.path.join(os.getcwd(), rel_path) if rel_path != '.' else os.getcwd()
                    os.makedirs(dest_dir, exist_ok=True)
                    for file in files:
                        src_file = os.path.join(root, file)
                        dst_file = os.path.join(dest_dir, file)
                        shutil.move(src_file, dst_file)
                os.remove(tmp_path)
                set_status("Update complete! Please restart the application.")
                progressbar['value'] = 100
            except Exception as e:
                set_status(f"Source update failed: {e}")
                messagebox.showerror("Update failed", f"Source update failed: {e}")
        progress_win.after(2000, progress_win.destroy)

    @staticmethod
    def update_exe():
        try:
            progress_win = tk.Toplevel()
            progress_win.title("Updating (Executable)")
            progress_win.geometry("400x200")
            
            progress_label = tk.Label(progress_win, text="Starting update...", anchor="w", justify="left")
            progress_label.pack(fill=tk.X, padx=10, pady=5)
            
            progressbar = ttk.Progressbar(progress_win, orient="horizontal", length=350, mode="determinate")
            progressbar.pack(padx=10, pady=5)
            
            progress_text = tk.Text(progress_win, height=6, width=48, state="disabled")
            progress_text.pack(padx=10, pady=5)
            
            progress_win.update()

            def set_status(msg):
                progress_label.config(text=msg)
                progress_text.config(state="normal")
                progress_text.insert(tk.END, msg + "\n")
                progress_text.see(tk.END)
                progress_text.config(state="disabled")
                progress_win.update()
            set_status("Fetching release info...")

            info = UpdateChecker.get_latest_release_info()
            z7_asset = next((a for a in info["assets"] if a["name"].endswith(".7z")), None)

            if not z7_asset:
                set_status("No .7z asset found in latest release.")
                messagebox.showerror("Update failed", "No .7z asset found in latest release.")
                progress_win.after(2000, progress_win.destroy)
                return

            z7_url = z7_asset["browser_download_url"]
            exe_path = sys.executable
            temp_dir = tempfile.mkdtemp()
            z7_path = os.path.join(temp_dir, z7_asset["name"])

            set_status("Downloading latest .7z update...")
            r = requests.get(z7_url, stream=True)
            total = int(r.headers.get('content-length', 0))
            downloaded = 0

            with open(z7_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            progressbar['value'] = min(100, downloaded * 100 // total)
                            progress_win.update()

            set_status("Extracting update (using py7zr)...")
            extract_dir = os.path.join(temp_dir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)

            try:
                with py7zr.SevenZipFile(z7_path, mode='r') as archive:
                    archive.extractall(path=extract_dir)
            except Exception as e:
                set_status(f"Extraction failed: {e}")
                messagebox.showerror("Update failed", f"Extraction failed: {e}\nMake sure the .7z file is valid.")
                shutil.rmtree(temp_dir, ignore_errors=True)
                progress_win.after(2000, progress_win.destroy)
                return

            set_status("Searching for new executable...")
            new_exe_path = None

            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.lower().endswith(".exe"):
                        new_exe_path = os.path.join(root, file)
                        break
                if new_exe_path:
                    break

            if not new_exe_path:
                set_status("No .exe found in extracted update.")
                messagebox.showerror("Update failed", "No .exe found in extracted update.")
                shutil.rmtree(temp_dir, ignore_errors=True)
                progress_win.after(2000, progress_win.destroy)
                return

            set_status("Preparing to replace executable...")
            bat_path = exe_path + ".bat"
            staged_exe = exe_path + ".new"
            shutil.copy2(new_exe_path, staged_exe)
            shutil.rmtree(temp_dir, ignore_errors=True)
            with open(bat_path, "w") as f:
                f.write(f"""
@echo off
ping 127.0.0.1 -n 2 > nul
move /Y "{staged_exe}" "{exe_path}"
start "" "{exe_path}"
del "%~f0"
                """)

            set_status("Update complete! Restarting...")
            progressbar['value'] = 100
            progress_win.update()
            progress_win.after(1000, progress_win.destroy)
            os.startfile(bat_path)
            sys.exit()
        except Exception as e:
            messagebox.showerror("Update failed", f"Executable update failed: {e}")

    @staticmethod
    def check_for_updates(current_version, auto_update=False, parent_window=None):
        try:
            response = requests.get('https://raw.githubusercontent.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/main/latestVersion.txt')
            latest_version = response.text.strip()

            if latest_version > current_version:
                parent = parent_window if parent_window is not None else tk.Tk()
                if parent_window is None:
                    parent.withdraw()
                if auto_update:
                    print("An update is available. Automatically downloading and installing...")
                    if UpdateChecker.is_frozen():
                        UpdateChecker.update_exe()
                    else:
                        UpdateChecker.update_source()
                    sys.exit()
                else:
                    result = messagebox.askyesno("Update available", "An update is available. Do you want to download and install it now?\n\nThe app will restart after updating.", parent=parent)
                    if result:
                        print("User chose to update.")
                        if UpdateChecker.is_frozen():
                            UpdateChecker.update_exe()
                        else:
                            UpdateChecker.update_source()
                        sys.exit()
                    else:
                        print("User chose not to update.")
                if parent_window is None:
                    parent.destroy()
            else:
                print("You are using the latest version of the application.")
        except requests.exceptions.RequestException as err:
            print("No internet connection or something went wrong, could not check for updates.")
            print("Error details:", err)