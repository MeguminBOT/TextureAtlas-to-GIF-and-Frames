import sys
import webbrowser
import requests

import tkinter as tk
from tkinter import messagebox

class UpdateChecker:
    """
    A class to check for updates of the application by comparing the current version with the latest version available online.
    Methods:
    check_for_updates(current_version: str) -> None
        Checks if there is a newer version of the application available online.
        If a newer version is found, prompts the user to download it.
        If the user agrees, opens the web browser to the latest release page and exits the application.
        If the user declines, continues running the application.
        If there is no internet connection or an error occurs, prints an error message.
    """

    @staticmethod
    def check_for_updates(current_version):
        try:
            response = requests.get('https://raw.githubusercontent.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/main/latestVersion.txt')
            latest_version = response.text.strip()

            if latest_version > current_version:
                root = tk.Tk()
                root.withdraw()
                result = messagebox.askyesno("Update available", "An update is available. Do you want to download it now?")
                if result:
                    print("User chose to download the update.")
                    webbrowser.open('https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/releases/latest')
                    sys.exit()
                else:
                    print("User chose not to download the update.")
                root.destroy()
            else:
                print("You are using the latest version of the application.")
        except requests.exceptions.RequestException as err:
            print("No internet connection or something went wrong, could not check for updates.")
            print("Error details:", err)