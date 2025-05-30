import tkinter as tk
from tkinter import ttk

class HelpWindow:
    """
    A window class for displaying help and documentation for the application.

    This class provides static methods to create scrollable help windows with detailed instructions
    and guidance for using the application, including special advice for FNF (Friday Night Funkin') sprites.

    Methods:
        create_scrollable_help_window(help_text, title="Help"):
            Creates a scrollable help window with the provided help text and title.
        create_main_help_window():
            Opens the main help window with instructions and feature descriptions.
        create_fnf_help_window():
            Opens a help window with guidance specific to FNF sprites and settings.
    """

    @staticmethod
    def create_scrollable_help_window(help_text, title="Help"):
        help_window = tk.Toplevel()
        help_window.geometry("800x600")
        help_window.title(title)

        main_frame = ttk.Frame(help_window)
        main_frame.pack(fill=tk.BOTH, expand=1)

        canvas = tk.Canvas(main_frame)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        scrollable_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        help_label = tk.Label(scrollable_frame, text=help_text, justify="left", padx=10, pady=10, wraplength=780)
        help_label.pack()

    @staticmethod
    def create_main_help_window():
        help_text = (
            "_________________________________________ Main Window _________________________________________\n\n"
            "Double clicking a spritesheet entry will open up a window where you can override the global settings and customize indices used for all the animations in that spritesheet.\n\n"
            "Double clicking an animation entry will open up a window where you can override the global and spritesheets' and customize indices used for that animation.\n\n"
            "Select directory with spritesheets:\nOpens a file dialog for you to choose a folder containing the spritesheets you want to process.\n\n"
            "Select save directory:\nOpens a file dialog for you to specify where the application should save the exported frames and animated images.\n\n\n"
            "Animation format:\nChoose the output format for animated images, currently supports GIF, WebP and APNG\n\n"
            "Frame rate (fps):\nDefines the playback speed of the animated image in frames per second.\n\n"
            "Loop delay (ms):\nSets the minimum delay time, in milliseconds, before the animation loops again.\n\n"
            "Minimum period (ms):\nSets the minimum duration, in milliseconds, before the animation loops again.\n\n"
            "Scale:\nResizes frames and animations using nearest-neighbor interpolation to preserve pixels. Negative numbers flip the sprites horizontally.\n\n"
            "Alpha threshold (GIFs only):\nThis setting adjusts the level of transparency applied to pixels in GIF images.\nThe threshold value determines the cutoff point for transparency.\nPixels with an alpha value below this threshold become fully transparent, while those above the threshold become fully opaque.\n\n"
            "Indices (not available in global settings):\nSelect the frame indices to use in the animation by typing a comma-separated list of non-negative integers.\n\n\n"
            "Keep individual frames:\nWheter to keep exported frames as PNGs.\nThis option has a few presets like 'No duplicates', you can also directly enter a comma-separated list of integers or integer ranges. Negative numbers count from the final frame\n\n"
            "Cropping method:\nWheter to crop exported images.\n'Animation based' finds the smallest possible size for the entire animation.\n'Frame based' finds the smallest possible size for each frame *Only applied on exported pngs*.\n'None' turns cropping off.\n\n"
            "Filename prefix:\nSets a prefix to the filenames of the exported images.\n\n"
            "Filename format:\nChoose how filenames are formatted when exported images.\n'Standardized' keeps names clean with spaces and dashes, example: 'Prefix - Sprite - Animation'\n\n"
            "Find and replace:\nAllows you to find and replace specific text in the filenames of the exported images.\nAlso supports the usage of 'Regular Expression' (Regex), a powerful way to search using patterns.\n\n"
            "Show user settings:\nOpens a window displaying a list of animations and spritesheets with settings that override the global configuration.\n\n"
            "Start process:\nBegins the exporting process.\n\n"
            "_________________________________________ Menubar: File _________________________________________\n\n"
            "Select directory:\nOpens a file dialog for you to choose a folder containing the spritesheets you want to process.\n\n"
            "Select Files:\nOpens a file dialog for you to manually choose spritesheet .XML/TXT and .PNG files.\n\n"
            "Clear Filelist and User settings:\nRemoves all entries from the list and clears the settings.\n\n"
            "Exit:\nExits the application\n\n"
            "_________________________________________ Menubar: Import _________________________________________\n\n"
            "(FNF) Import settings from character data file:\nOpens a file dialog for you to choose the folder containing the data files of your characters, attempting to automatically set the correct settings of each animation. Supports Psych Engine, Codename Engine and Kade Engine.\n\n"
            "_________________________________________ Menubar: Advanced _________________________________________\n\n"
            "Variable Delay:\nWhen enabled, vary the delays of each frame slightly to more accurately reach the desired fps.\n\n"
            "Use all CPU threads:\nWhen checked, the application utilizes all available CPU threads. When unchecked, it uses only half of the available CPU threads.\n\n"
            "(FNF) Set idle loop delay to 0:\nSets all animations containing the phrase 'idle' to have no delay before looping. Usually recommended.\n\n"
        )
        HelpWindow.create_scrollable_help_window(help_text, "Help")

    @staticmethod
    def create_fnf_help_window():
        fnf_help_text = (
            "Use the 'FNF: Import settings character data files' option in the Import menu,\nThis will attempt to get the correct frame rate, delay, scale and indices for each character and animation.\n(Make sure you select spritesheet directory first)\n\n"
            "Use the 'FNF: Set idle loop delay to 0' option in the Advanced menu,\nThis will set all animations containing the phrase 'idle' to have no delay before looping. Usually recommended.\n\n"
            "If those options don't work for you, you can manually set the settings for each animation. Here's some general guidelines for the delay below:\n\n"
            "Loop delay:\n"
            "For anything that doesn't need to smoothly loop like sing poses for characters, 250 ms is recommended (100 ms minimum)\n"
            "Idle animations usually looks best with 0\n"
            "Idle animations usually looks best with 0, some do look better with 150-250ms.\n"
            "If unsure about the loop delay, start by leaving it at default, start processing, then inspect the generated gifs.\n"
            "Doesn't look good? Just double click the animation name in the application and change the delay and start processing again."
        )
        HelpWindow.create_scrollable_help_window(fnf_help_text, "Help (FNF Sprites)")