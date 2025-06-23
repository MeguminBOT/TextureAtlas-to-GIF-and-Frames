import tkinter as tk
from tkinter import ttk


class HelpWindow:
    """
    A window class for displaying quick help and documentation for the application.

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
            "Double clicking an animation entry will open up a window where you can override the global and spritesheet settings and customize indices used for that animation.\n\n"
            "Select directory with spritesheets:\nOpens a file dialog for you to choose a folder containing the spritesheets you want to process.\nAutomatically scans the directory for .XML/.TXT and .PNG file pairs.\n\n"
            "Select save directory:\nOpens a file dialog for you to specify where the application should save the exported frames and animated images.\n\n"
            "Animation format:\nChoose the output format for animated images.\nSupports: None (no animation), GIF, WebP, and APNG.\n'None' will only export individual frames if frame format is set.\n\n"
            "Frame rate (fps):\nDefines the playback speed of the animated image in frames per second.\nHigher values create smoother but faster animations.\nAccepts decimal values for precise timing.\n\n"
            "Loop delay (ms):\nSets the minimum delay time, in milliseconds, before the animation loops again.\nUseful for preventing animations from looping too quickly.\nAdds to the final frame duration.\n\n"
            "Minimum period (ms):\nSets the minimum duration, in milliseconds, for the entire animation cycle.\nHelps ensure animations don't play too fast regardless of frame count.\n\n"
            "Scale:\nResizes frames and animations using nearest-neighbor interpolation to preserve pixel art quality.\nNegative numbers flip the sprites horizontally. Examples: 1.0 = original size, 2.0 = double size, -1.0 = flipped.\n\n"
            "Alpha threshold (GIFs only):\nThis setting adjusts the level of transparency applied to pixels in GIF images.\nThe threshold value (0.0-1.0) determines the cutoff point for transparency.\nPixels with an alpha value below this threshold become fully transparent, while those above become fully opaque.\nOnly available when animation format is set to GIF.\n\n"
            "Indices (not available in global settings):\nSelect specific frame indices to use in the animation by typing a comma-separated list of non-negative integers.\nExample: '0,1,2,1' creates a back-and-forth animation effect.\nAvailable in animation and spritesheet override settings only.\n\n"
            "Frame format:\nChoose the format for exported individual frames.\nSupports: None (no frames), AVIF, BMP, DDS, PNG, TGA, TIFF, and WebP.\nDifferent formats have different compression options and quality characteristics.\n\n"
            "Frame selection:\nDetermines which frames to keep as individual image files.\nPresets:\n• 'All' - Exports every frame\n• 'No duplicates' - Skips identical consecutive frames\n• 'First' - Only the first frame\n• 'Last' - Only the final frame\n• 'First, Last' - First and last frames only\nYou can also enter custom ranges like '0-5,10,15-20' or use negative numbers to count from the end.\n\n"
            "Frame scale:\nScale factor applied specifically to individual frame exports.\nThis is independent of the main scale setting for animations.\nExamples: 0.5 = 50% size, 2.0 = 200% size, useful for creating thumbnails or high-res versions.\n\n"
            "Compression:\nFormat-specific compression settings that affect file size and quality. Settings dynamically change based on selected frame format:\n• PNG: Compression level (0-9), optimization (when enabled, automatically sets compression to 9)\n• WebP: Quality (0-100), method (0-6), lossless mode, alpha quality (0-100), exact encoding\n• AVIF: Quality (0-100), speed (0-10), lossless mode\n• TIFF: Compression type (lzw, jpeg, raw, tiff_lzw), quality (for JPEG compression), optimization\n• TGA, BMP, DDS: No compression options available\nHigher quality/lower compression = larger files but better image quality.\n\n"
            "Cropping method:\nWhether to crop exported images to remove empty space:\n• 'Animation based' - Finds the smallest box that fits all frames (consistent size across animation)\n• 'Frame based' - Crops each frame individually to its content (variable sizes, only for exported frames)\n• 'None' - No cropping, preserves original atlas dimensions\n\n"
            "Filename prefix:\nSets a custom prefix for all exported filenames.\nUseful for organizing exports or adding version numbers.\nCannot contain invalid characters: \\ / : * ? \" < > |\n\n"
            "Filename format:\nChoose how filenames are formatted for exported images:\n• 'Standardized' - Clean format with spaces and dashes: 'Prefix - Sprite - Animation'\n• 'No spaces' - Replaces spaces with dashes: 'Prefix-Sprite-Animation'\n• 'No special characters' - Removes all special characters: 'PrefixSpriteAnimation'\n\n"
            "Find and replace:\nAllows you to find and replace specific text in the filenames of exported images.\nSupports Regular Expressions (Regex) for advanced pattern matching.\nUseful for batch renaming or removing unwanted text from filenames.\n\n"
            "Show user settings:\nOpens a window displaying all animations and spritesheets with custom settings that override the global configuration.\nHelps you review what overrides you've set and manage per-animation/spritesheet customizations.\n\n"
            "Start process:\nBegins the extraction and conversion process.\nThe progress bar will show the current status.\nButton is disabled during processing to prevent multiple simultaneous operations.\n\n"
            "_________________________________________ Context Menu (Right-click PNG list) _________________________________________\n\n"
            "Delete:\nRemoves the selected spritesheet from the processing list.\nAlso clears any custom settings associated with that spritesheet and its animations.\n\n"
            "_________________________________________ Menubar: File _________________________________________\n\n"
            "Select directory:\nOpens a file dialog for you to choose a folder containing the spritesheets you want to process.\nAutomatically clears any existing settings when switching directories.\nScans for matching .XML/.TXT and .PNG file pairs.\n\n"
            "Select files:\nOpens a file dialog for you to manually choose specific spritesheet .XML/.TXT and .PNG files.\nUseful when you only want to process specific files from a directory or files from different locations.\nFiles are copied to a temporary directory for processing.\n\n"
            "Clear filelist and user settings:\nRemoves all entries from the file lists and clears all custom animation and spritesheet settings.\nResets the application to a clean state.\n\n"
            "Exit:\nSafely closes the application and cleans up temporary files.\n\n"
            "_________________________________________ Menubar: Import _________________________________________\n\n"
            "FNF: Import settings from character data file:\nOpens a file dialog to select character data files (.json/.xml) for Friday Night Funkin' mods.\nAutomatically configures optimal settings for each character animation based on the game engine.\nSupports Psych Engine, Codename Engine, Kade Engine, and base game (V-Slice) formats.\nMust select spritesheet directory first.\nDetects engine type automatically and applies appropriate frame rates, scales, indices, and loop settings.\n\n"
            "_________________________________________ Menubar: Help _________________________________________\n\n"
            "Manual:\nOpens this comprehensive help window with detailed explanations of all features and settings.\n\n"
            "FNF: GIF/WebP settings advice:\nOpens a specialized help window with guidance specific to Friday Night Funkin' sprites.\nProvides recommended settings for different animation types (idle, sing poses, etc.).\n\n"
            "_________________________________________ Menubar: Advanced _________________________________________\n\n"
            "Variable delay:\nWhen enabled, slightly varies frame delays to more accurately achieve the target FPS.\nHelps create smoother animations that match the intended playback speed.\nUseful for precise timing requirements.\n\n"
            "FNF: Set loop delay on idle animations to 0:\nAutomatically sets loop delay to 0 for all animations containing 'idle' in their name.\nRecommended for FNF characters as idle animations should loop seamlessly without pause.\nApplies to all animations with 'idle' in the name when processing starts.\n\n"
            "_________________________________________ Menubar: Options _________________________________________\n\n"
            "Preferences:\nOpens the comprehensive application configuration window.\nAllows you to modify:\n• Resource limits (CPU threads/cores, memory limit in MB)\n• Default extraction settings for new projects (animation format, frame rate, delays, scale, etc.)\n• Compression defaults for all supported formats (PNG, WebP, AVIF, TIFF)\n• Update checking preferences (check on startup, auto-download updates)\n• UI settings\nIncludes scrollable interface with keyboard navigation:\n• Arrow keys: Scroll up/down\n• Page Up/Down: Scroll by larger increments\n• Home/End: Jump to top/bottom\n• Mouse wheel: Scroll anywhere in window\nSettings are automatically migrated between application versions.\n\n"
            "Check for Updates:\nManually checks for application updates and displays available updates with changelog.\nRespects your auto-update preferences set in the Preferences window.\nCan automatically download and install updates if enabled in preferences.\n\n"
        )
        HelpWindow.create_scrollable_help_window(help_text, "Help")

    @staticmethod
    def create_fnf_help_window():
        fnf_help_text = (
            "Use the 'FNF: Import settings from character data file' option in the Import menu,\nThis will attempt to get the correct frame rate, delay, scale and indices for each character and animation.\n(Make sure you select spritesheet directory first)\n\n"
            "Supported FNF Engines:\n• Psych Engine (.json character files)\n• Codename Engine (.json character files)\n• Kade Engine (.json character files)\n• Base Game/V-Slice (.xml character files)\n\n"
            "The import process automatically:\n• Detects the engine type from the file format and structure\n• Sets appropriate frame rates for each animation\n• Configures custom indices for specific animations\n• Applies correct scaling from character data\n• Sets loop delay to 0 for looping animations\n\n"
            "Use the 'FNF: Set loop delay on idle animations to 0' option in the Advanced menu,\nThis will set all animations containing the phrase 'idle' to have no delay before looping. Usually recommended.\n\n"
            "If those options don't work for you, you can manually set the settings for each animation.\n\n"
            "Tips for Funkipedia editors:\n"
            "• Idle animations: Set loop delay to 0 for seamless looping, in some cases 100-250ms may look better\n"
            "• Sing poses: Use 100-250ms loop delay to prevent rapid looping, this makes the GIFs less annoying to look at and reflects in-game behavior more\n"
            "• Special animations: Adjust based on intended behavior\n"
            "• Miss animations: May benefit from longer delays (250ms or above) as they often only have 1-3 frames\n"
            "• Use 'Animation based' cropping\n"
            "• Scale of 1.0 is usually preferred for quality purposes, very large characters may benefit from smaller sizes to not hit the max upload size.\n"
            "• Try using 'Variable delay' if animated exports appear too fast\n"
        )
        HelpWindow.create_scrollable_help_window(fnf_help_text, "Help (FNF Sprites)")
