import shutil
import os
import platform
import tkinter as tk
import webbrowser

# Import our own modules
from utils.utilities import Utilities

class DependenciesChecker:
    """
    A class to check and configure dependencies.

    Methods:
        show_error_popup_with_links(message, links):
            Displays an error message in a popup window with clickable links.
        check_imagemagick():
            Checks if ImageMagick is installed on the system.
        configure_imagemagick():
            Configures the environment to use a bundled version of ImageMagick.
        check_and_configure_imagemagick():
            Checks if ImageMagick is installed and configures it if not found.
    """

    @staticmethod
    def show_error_popup_with_links(message, links):
        root = tk.Tk()
        root.title("Error")
        root.geometry("300x200")
        root.resizable(False, False)

        window_width = 300
        window_height = 200
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x_cord = int((screen_width / 2) - (window_width / 2))
        y_cord = int((screen_height / 2) - (window_height / 2))
        root.geometry(f"{window_width}x{window_height}+{x_cord}+{y_cord}")

        msg = tk.Label(root, text=message, wraplength=360, justify="left")
        msg.pack(pady=20)

        for link_text, link_url in links:
            link = tk.Label(root, text=link_text, fg="blue", cursor="hand2")
            link.pack()
            link.bind("<Button-1>", lambda e, url=link_url: webbrowser.open_new(url))

        close_btn = tk.Button(root, text="Close", command=root.destroy)
        close_btn.pack(pady=10)

        root.mainloop()

    @staticmethod
    def check_imagemagick():
        return shutil.which("magick") is not None

    @staticmethod
    def configure_imagemagick():
        imagemagick_path = Utilities.find_root('ImageMagick')
        if imagemagick_path is None:
            raise FileNotFoundError("Could not find 'ImageMagick' folder in any parent directory.")
        dll_path = os.path.join(imagemagick_path, 'ImageMagick')
        if not os.path.isdir(dll_path):
            raise FileNotFoundError(f"Expected ImageMagick folder but couldn't be found at: {dll_path}")

        os.environ['PATH'] = dll_path + os.pathsep + os.environ.get('PATH', '')
        os.environ['MAGICK_HOME'] = dll_path
        os.environ['MAGICK_CODER_MODULE_PATH'] = dll_path

        print(f"Using bundled ImageMagick from: {dll_path}")

    @staticmethod
    def check_and_configure_imagemagick():
        if DependenciesChecker.check_imagemagick():
            print("Using the user's existing ImageMagick.")
            return

        if platform.system() == "Windows":
            print("System ImageMagick not found. Attempting to configure bundled version.")
            try:
                DependenciesChecker.configure_imagemagick()
                print("Configured bundled ImageMagick.")
                return
            except Exception as e:
                print(f"Failed to configure bundled ImageMagick: {e}")

        msg = ("ImageMagick not found or failed to initialize.\n\nMake sure you followed install steps correctly.\n"
               "If the issue persists, install ImageMagick manually.")
        links = [
            ("Installation Steps", "https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/wiki/Installation"),
            ("Install ImageMagick", "https://imagemagick.org/script/download.php")
        ]
        DependenciesChecker.show_error_popup_with_links(msg, links)
        raise Exception(msg)