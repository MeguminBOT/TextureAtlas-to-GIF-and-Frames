import tkinter as tk
from tkinter import ttk

class HelpWindow:
    """
    A class used to create help windows with scrollable text for the application.
    Methods:
        create_scrollable_help_window(help_text, title="Help"):
            Creates a scrollable help window with the provided help text and title.
        create_main_help_window():
            Creates the main help window with detailed instructions and descriptions of the application's features.
        create_fnf_help_window():
            Creates a help window specific to the FNF (Friday Night Funkin') sprites, providing guidance on importing FPS settings and loop delays.
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
            "Double clicking a spritesheet entry will open up a window where you can override the global fps/loop/alpha settings and customize indices used for all the animations in that spritesheet.\n\n"
            "Double clicking an animation entry will open up a window where you can override the global and spritesheets' fps/loop/alpha settings and customize indices used for that animation.\n\n"
            "Select Directory with Spritesheets:\nOpens a file dialog for you to choose a folder containing the spritesheets you want to process.\n\n"
            "Select Save Directory:\nOpens a file dialog for you to specify where the application should save the exported frames or GIF/WebP files.\n\n"
            "Create GIFs for Each Animation:\nWhen enabled, generates animated .GIF files for each animation found in the spritesheet data.\n\n"
            "Create WebPs for Each Animation:\nWhen enabled, generates animated .WebP files for each animation found in the spritesheet data.\n\n"
            "Frame Rate (fps):\nDefines the playback speed of the animated image in frames per second.\n\n"
            "Loop Delay (ms):\nSets the minimum delay time, in milliseconds, before the animation loops again.\n\n"
            "Minimum Period (ms):\nSets the minimum duration, in milliseconds, before the animation loops again.\n\n"
            "Scale:\nResizes frames and animations using nearest-neighbor interpolation to preserve pixels. Negative numbers flip the sprites horizontally.\n\n"
            "Alpha Threshold (GIFs only):\nThis setting adjusts the level of transparency applied to pixels in GIF images.\nThe threshold value determines the cutoff point for transparency.\nPixels with an alpha value below this threshold become fully transparent, while those above the threshold become fully opaque.\n\n"
            "Indices (not available in global settings):\nSelect the frame indices to use in the animation by typing a comma-separated list of non-negative integers.\n\n"
            "Keep Individual Frames:\nSelect the frames of the animation to save by typing 'all', 'first', 'last', 'none', or a comma-separated list of integers or integer ranges. Negative numbers count from the final frame.\n\n"
            "Crop Individual Frames:\nCrops every extracted png frame. (This doesn't affect GIFs, WebP's or single frame animations)\n\n"
            "Show User Settings:\nOpens a window displaying a list of animations and spritesheets with settings that override the global configuration.\n\n"
            "Start Process:\nBegins the tasks you have selected for processing.\n\n"
            "_________________________________________ Menubar: File _________________________________________\n\n"
            "Select Directory:\nOpens a file dialog for you to choose a folder containing the spritesheets you want to process.\n\n"
            "Select Files:\nOpens a file dialog for you to manually choose spritesheet .XML/TXT and .PNG files.\n\n"
            "Clear Filelist and User settings:\nRemoves all entries from the list and clears the settings.\n\n"
            "Exit:\nExits the application\n\n"
            "_________________________________________ Menubar: Import _________________________________________\n\n"
            "(FNF) Import FPS from character json:\nOpens a file dialog for you to choose the folder containing the json files of your characters to automatically set the correct fps values of each animation.\nFPS values are added to the User Settings.\n\n"
            "*NOT YET IMPLEMENTED* (FNF) Set idle loop delay to 0:\nSets all animations containing the phrase 'idle' to have no delay before looping. Usually recommended.\n\n"
            "_________________________________________ Menubar: Advanced _________________________________________\n\n"
            "Higher Color Quality (GIFs only):\nWhen enabled, use Wand to achieve better colors. May increase processing time.\n\n"
            "Variable Delay:\nWhen enabled, vary the delays of each frame slightly to more accurately reach the desired fps.\n\n"
            "Use All CPU Threads:\nWhen checked, the application utilizes all available CPU threads. When unchecked, it uses only half of the available CPU threads.\n\n"
        )
        HelpWindow.create_scrollable_help_window(help_text, "Help")

    @staticmethod
    def create_fnf_help_window():
        fnf_help_text = (
            "Use the import fps button to get the correct framerate from the character json files. (Make sure you select spritesheet directory first)\n\n"
            "Loop delay:\n"
            "For anything that doesn't need to smoothly loop like sing poses for characters, 250 ms is recommended (100 ms minimum)\n"
            "Idle animations usually looks best with 0\n"
            "Idle animations usually looks best with 0, some do look better with 150-250ms.\n"
            "If unsure about the loop delay, start by leaving it at default, start processing, then inspect the generated gifs.\n"
            "Doesn't look good? Just double click the animation name in the application and change the delay and start processing again."
        )
        HelpWindow.create_scrollable_help_window(fnf_help_text, "Help (FNF Sprites)")
