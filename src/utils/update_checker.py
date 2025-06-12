import os
import subprocess
import sys
import requests
import threading
import time

import tkinter as tk
from tkinter import messagebox

# Import our own modules
from utils.utilities import Utilities

class UpdateChecker:
    """
    A class for managing update checks and update installation for the application.

    Attributes:
        None

    Methods:
        is_frozen():
            Determine if the application is running as a frozen executable.
        get_latest_release_info():
            Retrieve the latest release information from GitHub.
        check_for_updates(current_version, auto_update=False, parent_window=None):
            Check for updates and optionally prompt or perform update.
        _launch_standalone_updater(exe_mode=False):
            Launch the standalone updater script and exit the current application.
    """

    @staticmethod
    def is_frozen():
        return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')    @staticmethod
    def get_latest_release_info():
        url = "https://api.github.com/repos/MeguminBOT/TextureAtlas-to-GIF-and-Frames/releases/latest"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

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
                        print("Running as executable, using standalone updater")
                        UpdateChecker._launch_standalone_updater(exe_mode=True)
                    else:
                        print("Running from source, using standalone updater")
                        UpdateChecker._launch_standalone_updater(exe_mode=False)
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
        try:
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
