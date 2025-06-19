import os
import platform
import subprocess
import sys
import requests

import tkinter as tk
from tkinter import messagebox, ttk

# Import our own modules
from utils.utilities import Utilities


class UpdateDialog:
    """
    A custom dialog window for displaying update information with changelog.
    
    Attributes:
        window (tk.Toplevel): The dialog window
        result (bool): The user's choice (True for update, False for cancel)
        
    Methods:
        __init__(parent, current_version, latest_version, changelog, update_type):
            Initialize the update dialog with version info and changelog
        show():
            Display the dialog and return the user's choice
        _on_update():
            Handle the update button click
        _on_cancel():
            Handle the cancel button click
    """
    def __init__(self, parent, current_version, latest_version, changelog, update_type):
        self.result = False
        
        try:
            self.window = tk.Toplevel(parent)
            self.window.title("Update Available")
            self.window.geometry("600x500")
            self.window.resizable(True, True)
            self.window.transient(parent)
            self.window.grab_set()
            
            self.window.update_idletasks()
            x = (self.window.winfo_screenwidth() // 2) - (600 // 2)
            y = (self.window.winfo_screenheight() // 2) - (500 // 2)
            self.window.geometry(f"600x500+{x}+{y}")
            
            self._create_widgets(current_version, latest_version, changelog, update_type)
            
        except Exception as e:
            print(f"Error creating update dialog: {e}")
            
            import tkinter.messagebox as mb
            result = mb.askyesno(
                "Update Available",
                f"An update is available!\n\nCurrent: {current_version}\nLatest: {latest_version}\n\nUpdate now?",
                parent=parent
            )
            self.result = result
            self.window = None
            
    def _create_widgets(self, current_version, latest_version, changelog, update_type):
        main_container = tk.Frame(self.window)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        content_frame = tk.Frame(main_container)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        title_label = tk.Label(content_frame, text="Update Available!", font=("Arial", 14, "bold"))
        title_label.pack(anchor="w", pady=(0, 10))
        
        info_frame = tk.Frame(content_frame)
        info_frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(info_frame, text=f"Current version:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(info_frame, text=current_version).grid(row=0, column=1, sticky="w", padx=(10, 0))
        
        tk.Label(info_frame, text=f"Latest version:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w")
        tk.Label(info_frame, text=latest_version, fg="green").grid(row=1, column=1, sticky="w", padx=(10, 0))
        
        tk.Label(info_frame, text=f"Update method:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="w")
        tk.Label(info_frame, text=update_type).grid(row=2, column=1, sticky="w", padx=(10, 0))
        
        changelog_label = tk.Label(content_frame, text="What's new in this release:", font=("Arial", 12, "bold"))
        changelog_label.pack(anchor="w", pady=(10, 5))
        
        changelog_frame = tk.Frame(content_frame, relief="sunken", borderwidth=1, height=200)
        changelog_frame.pack(fill=tk.X, pady=(0, 10))
        changelog_frame.pack_propagate(False)
        self.changelog_text = tk.Text(
            changelog_frame,
            wrap=tk.WORD,
            padx=10,
            pady=10,
            font=("Consolas", 9),
            state=tk.DISABLED,
            bg="#f8f8f8",
            height=10
        )
        
        scrollbar = ttk.Scrollbar(changelog_frame, orient=tk.VERTICAL, command=self.changelog_text.yview)
        self.changelog_text.configure(yscrollcommand=scrollbar.set)
        
        self.changelog_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.changelog_text.config(state=tk.NORMAL)
        if changelog and changelog.strip():
            cleaned_changelog = changelog.replace('\r\n', '\n').replace('\r', '\n')
            self.changelog_text.insert(tk.END, cleaned_changelog)
        else:
            self.changelog_text.insert(tk.END, "No changelog information available for this release.")
        self.changelog_text.config(state=tk.DISABLED)
        
        self.changelog_text.see("1.0")
        

        button_container = tk.Frame(main_container, relief="solid", borderwidth=1, bg="#f0f0f0")
        button_container.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))
        
        button_frame = tk.Frame(button_container, bg="#f0f0f0")
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        info_label = tk.Label(
            button_frame, 
            text="The application will restart after updating.",
            font=("Arial", 9),
            fg="gray",
            bg="#f0f0f0"
        )
        info_label.pack(side=tk.LEFT)
        cancel_btn = tk.Button(
            button_frame, 
            text="Cancel", 
            command=self._on_cancel,
            padx=10,
            pady=5        )
        cancel_btn.pack(side=tk.RIGHT)
        
        # Update button
        update_btn = tk.Button(
            button_frame, 
            text="Update Now", 
            command=self._on_update,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=5        )
        update_btn.pack(side=tk.RIGHT, padx=(5, 10))
        
        update_btn.focus_set()
        
        self.window.protocol("WM_DELETE_WINDOW", self._on_cancel)
        
    def show(self):
        if self.window:
            self.window.wait_window()
        return self.result
    
    def _on_update(self):
        self.result = True
        self.window.destroy()
    
    def _on_cancel(self):
        self.result = False
        self.window.destroy()


class UpdateChecker:
    """
    A class for managing update checks and update installation for the application.

    Attributes:
        None

    Methods:
        get_latest_release_info():
            Retrieve the latest release information from GitHub.
        check_for_updates(current_version, auto_update=False, parent_window=None):
            Check for updates and optionally prompt or perform update.
        _launch_standalone_updater(exe_mode=False):
            Launch the standalone updater script and exit the current application.
    """

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
                    if Utilities.is_compiled():
                        if platform.system() != "Windows":
                            print(f"Error: Executable updates are only supported on Windows. Current platform: {platform.system()}")
                            print(f"Please use source code updates on macOS/Linux or manually download the release.")
                            return
                        print("Running as executable, using standalone updater")
                        UpdateChecker._launch_standalone_updater(exe_mode=True)
                    else:
                        print("Running from source, using standalone updater")
                        UpdateChecker._launch_standalone_updater(exe_mode=False)
                else:
                    changelog = UpdateChecker._get_changelog()
                    
                    update_type = "executable" if Utilities.is_compiled() else "source code"
                    
                    dialog = UpdateDialog(parent, current_version, latest_version, changelog, update_type)
                    result = dialog.show()

                    if result:
                        print("User chose to update.")
                        if Utilities.is_compiled():
                            if platform.system() != "Windows":
                                error_msg = (
                                    f"Executable updates are only supported on Windows.\n"
                                    f"Current platform: {platform.system()}\n\n"
                                    f"Please use source code updates on macOS/Linux or manually download the release."
                                )
                                messagebox.showerror("Platform Not Supported", error_msg, parent=parent)
                                return
                            print("Starting executable update...")
                            UpdateChecker._launch_standalone_updater(exe_mode=True)
                        else:
                            print("Starting source update...")
                            UpdateChecker._launch_standalone_updater(exe_mode=False)
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
            
    @staticmethod
    def _launch_standalone_updater(exe_mode=False):
        print(f"Debug: _launch_standalone_updater called with exe_mode={exe_mode}")
        print(f"Debug: Utilities.is_compiled() = {Utilities.is_compiled()}")
        try:
            if Utilities.is_compiled() and exe_mode:
                # When compiled, restart the same executable with --update flag
                current_exe = sys.executable
                cmd = [current_exe, "--update", "--exe-mode", "--wait", "3"]
                
                print(f"Restarting with update mode: {' '.join(cmd)}")
                subprocess.Popen(cmd, cwd=os.path.dirname(current_exe))
                
                import time
                time.sleep(1)

                print("Exiting main application to allow update...")

                try:
                    import tkinter as tk
                    root = tk._default_root
                    if root:
                        root.quit()
                        root.destroy()
                except:
                    pass
                
                sys.exit(0)
            else:
                # When not compiled, run the updater script directly
                project_root = Utilities.find_root('README.md')
                if not project_root:
                    raise Exception("Could not find project root")
                
                updater_script = os.path.join(project_root, "src", "utils", "update_installer.py")
                if not os.path.exists(updater_script):
                    raise Exception("Update installer script not found")
                
                cmd = [sys.executable, updater_script]
                if exe_mode:
                    cmd.append("--exe-mode")
                
                print(f"Launching updater: {' '.join(cmd)}")
                subprocess.Popen(cmd, cwd=os.path.dirname(updater_script))
                
                import time
                time.sleep(1)

                print("Exiting main application to allow update...")

                try:
                    import tkinter as tk
                    root = tk._default_root
                    if root:
                        root.quit()
                        root.destroy()
                except:
                    pass
                
                sys.exit(0)
                
        except Exception as e:
            print(f"Failed to launch standalone updater: {e}")
    
    @staticmethod
    def _get_changelog():
        """Fetch the changelog from the latest GitHub release."""
        try:
            print("Fetching changelog from GitHub API...")
            url = "https://api.github.com/repos/MeguminBOT/TextureAtlas-to-GIF-and-Frames/releases/latest"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            release_data = response.json()
            changelog = release_data.get('body', '')
            
            if changelog:
                print("Changelog fetched successfully")
                return changelog
            else:
                print("No changelog found in release data")
                return "No changelog information available for this release."
                
        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch changelog: {e}")
            return "Failed to load changelog information."
        except Exception as e:
            print(f"Unexpected error fetching changelog: {e}")
            return "Failed to load changelog information."
