import os
import platform
import shutil
import tempfile
import threading
import tkinter as tk
import webbrowser
import argparse
from tkinter import filedialog, ttk, messagebox

# Import our own modules
from utils.dependencies_checker import DependenciesChecker

DependenciesChecker.check_and_configure_imagemagick()
from utils.app_config import AppConfig
from utils.update_checker import UpdateChecker
from utils.settings_manager import SettingsManager
from utils.utilities import Utilities
from utils.fnf_utilities import FnfUtilities
from parsers.xml_parser import XmlParser
from parsers.txt_parser import TxtParser
from parsers.unknown_parser import UnknownParser
from core.extractor import Extractor
from gui.app_config_window import AppConfigWindow
from gui.help_window import HelpWindow
from gui.find_replace_window import FindReplaceWindow
from gui.override_settings_window import OverrideSettingsWindow
from gui.gif_preview_window import GifPreviewWindow
from gui.settings_window import SettingsWindow
from gui.tooltip import Tooltip
from gui.unknown_atlas_warning_window import UnknownAtlasWarningWindow
from gui.background_handler_window import BackgroundHandlerWindow


class TextureAtlasExtractorApp:
    """
    A GUI application for extracting textures from a texture atlas and converting them to GIF, WebP, and APNG formats.

    Attributes:
        root (tk.Tk): The root window of the application.

        current_version (str): The current version of the application.
        app_config (AppConfig): Application configuration instance for persistent app settings.
        settings_manager (SettingsManager): Manages global, animation-specific, and spritesheet-specific settings.
        temp_dir (str): A temporary directory for storing files.
        data_dict (dict): A dictionary to store data related to the spritesheets.
        fnf_utilities (FnfUtilities): An instance of FnfUtilities for FNF-related utilities.
        fnf_char_json_directory (str): Directory for FNF character JSON files.
        replace_rules (list): List of find/replace rules.
        linkSourceCode (str): URL to the source code.

        progress_var (tk.DoubleVar): A variable to track progress for the progress bar.
        progress_bar (ttk.Progressbar): The progress bar widget.
        menubar (tk.Menu): The main menu bar.
        variable_delay (tk.BooleanVar): A flag to enable or disable variable delay between frames.
        fnf_idle_loop (tk.BooleanVar): A flag to set loop delay to 0 for idle animations in FNF.
        scrollbar_png (tk.Scrollbar): Scrollbar for the PNG listbox.
        listbox_png (tk.Listbox): Listbox for PNG files.
        scrollbar_xml (tk.Scrollbar): Scrollbar for the data listbox.
        listbox_data (tk.Listbox): Listbox for animation/data files.
        listbox_png_menu (tk.Menu): Context menu for the PNG listbox.
        input_dir (tk.StringVar): Input directory variable.
        input_button (tk.Button): Button to select input directory.
        input_dir_label (tk.Label): Label showing the selected input directory.
        output_dir (tk.StringVar): Output directory variable.
        output_button (tk.Button): Button to select output directory.
        output_dir_label (tk.Label): Label showing the selected output directory.
        animation_format (tk.StringVar): Animation format variable.
        animation_format_label (tk.Label): Label for animation format.
        animation_format_combobox (ttk.Combobox): Combobox for animation format selection.
        set_framerate (tk.DoubleVar): Frame rate variable.
        frame_rate_label (tk.Label): Label for frame rate.
        frame_rate_entry (tk.Entry): Entry for frame rate.
        set_loopdelay (tk.DoubleVar): Loop delay variable.
        loopdelay_label (tk.Label): Label for loop delay.
        loopdelay_entry (tk.Entry): Entry for loop delay.
        set_minperiod (tk.DoubleVar): Minimum period variable.
        minperiod_label (tk.Label): Label for minimum period.
        minperiod_entry (tk.Entry): Entry for minimum period.
        set_scale (tk.DoubleVar): Scale variable.
        scale_label (tk.Label): Label for scale.
        scale_entry (tk.Entry): Entry for scale.
        set_threshold (tk.DoubleVar): Alpha threshold variable.
        threshold_label (tk.Label): Label for alpha threshold.
        threshold_entry (tk.Entry): Entry for alpha threshold.
        frame_selection (tk.StringVar): Option for keeping frames.
        frame_selection_label (tk.Label): Label for keep frames option.
        frame_selection_menu (ttk.Combobox): Combobox for keep frames option.
        frame_scale (tk.DoubleVar): Scale variable for individual frame export.
        frame_scale_label (tk.Label): Label for frame scale.
        frame_scale_entry (tk.Entry): Entry for frame scale.
        frame_compression (tk.StringVar): Compression level variable for frame export.
        frame_compression_label (tk.Label): Label for frame compression.
        frame_compression_menu (ttk.Combobox): Combobox for frame compression level selection.
        crop_option (tk.StringVar): Cropping method variable.
        crop_menu_label (tk.Label): Label for cropping method.
        crop_menu_menu (ttk.Combobox): Combobox for cropping method.
        prefix_label (tk.Label): Label for filename prefix.
        prefix (tk.StringVar): Filename prefix variable.
        prefix_entry (tk.Entry): Entry for filename prefix.
        filename_format (tk.StringVar): Filename format variable.
        filename_format_label (tk.Label): Label for filename format.
        filename_format_menu (ttk.Combobox): Combobox for filename format selection.
        frame_format (tk.StringVar): Frame format variable for individual frame export formats (AVIF, BMP, DDS, PNG, TGA, TIFF, WebP).
        frame_format_label (tk.Label): Label for frame format.
        frame_format_menu (ttk.Combobox): Combobox for frame format selection.
        frame_settings_frame (tk.Frame): Main frame containing the two-column layout for animation and frame settings.
        animation_settings_frame (tk.Frame): Left column frame containing animation format settings.
        frame_settings_frame (tk.Frame): Right column frame containing frame format settings.
        replace_rules (list): List of find/replace rules for filename formatting.
        replace_button (tk.Button): Button to open find and replace window.
        button_frame (tk.Frame): Frame for bottom buttons.
        show_user_settings (tk.Button): Button to show user settings.
        process_button (tk.Button): Button to start processing.
        author_label (tk.Label): Label for author credit.
        link1 (tk.Label): Label with clickable link to source code.

    Methods:
        setup_gui(): Sets up the GUI components of the application.
        setup_menus(): Sets up the menu bar and its items.
        setup_widgets(): Sets up the widgets in the main window.
        contributeLink(linkSourceCode): Opens the source code link in a web browser.
        check_version(): Checks for updates to the application and prompts the user if the user wants to update.
        check_dependencies(): Checks and configures dependencies.
        create_app_config_window(): Creates the options window for setting CPU/memory limits and other persistent app settings via AppConfig.
        clear_filelist(): Clears the file list and resets animation and spritesheet settings.
        select_directory(variable, label): Opens a directory selection dialog and updates the label.
        select_files_manually(variable, label): Opens a file selection dialog and updates the label.
        create_settings_window(): Creates a window to display animation and spritesheet settings.
        create_find_and_replace_window(): Creates the Find and Replace window.
        store_replace_rules(rules): Stores the replace rules from the Find and Replace window.
        create_override_settings_window(window, name, settings_type): Creates a window to edit animation or spritesheet settings.
        on_select_spritesheet(evt): Handles the event when a PNG file is selected from the listbox.
        on_double_click_spritesheet(evt): Handles the event when a PNG file is double-clicked in the listbox.
        on_double_click_animation(evt): Handles the event when an animation is double-clicked in the listbox.
        show_listbox_png_menu(event): Shows the context menu for the PNG listbox.
        delete_selected_spritesheet(): Deletes the selected spritesheet and related settings.
        preview_gif_window(...): Generates and displays a preview GIF.
        show_gif_preview_window(gif_path, settings): Displays the preview GIF in a new window.
        store_input(...): Stores the input from the override settings window.
        update_global_settings(): Updates the global settings from the GUI.
        on_closing(): Handles the event when the application is closing.
        start_process(): Prepares and starts the processing thread.
        run_extractor(): Starts the process of extracting textures and converting them to GIF and WebP formats.
        _re_enable_process_button(): Re-enables the process button after extraction completion.
        _on_frame_format_change(event=None): Handles frame format selection changes and updates UI state.
        _on_frame_compression_change(event=None): Handles frame compression selection changes and updates UI state based on format compatibility.
        _on_animation_format_change(event=None): Handles animation format selection changes and updates UI state based on format capabilities.
    """

    def __init__(self, root):
        self.root = root
        self.current_version = "1.9.5"
        self.app_config = AppConfig()
        self.settings_manager = SettingsManager()
        self.temp_dir = tempfile.mkdtemp()
        self.data_dict = {}

        self.fnf_utilities = FnfUtilities()
        self.fnf_char_json_directory = ""

        self.setup_gui()
        self.root.after(250, self.check_version)

    def setup_gui(self):
        self.root.title(f"TextureAtlas to GIF and Frames v{self.current_version}")
        self.root.geometry("900x770")
        self.root.resizable(False, True)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        try:
            current_os = platform.system()
            assets_path = Utilities.find_root("assets")
            if current_os == "Windows":
                if assets_path is None:
                    raise FileNotFoundError(
                        "Could not find 'assets' folder in any parent directory."
                    )
                self.root.iconbitmap(os.path.join(assets_path, "assets", "icon.ico"))
            else:
                icon = tk.PhotoImage(file=os.path.join(assets_path, "assets", "icon.png"))
                self.root.iconphoto(True, icon)
        except Exception:
            pass

        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)

        self.setup_menus()
        self.setup_widgets()

    def setup_menus(self):
        defaults = (
            self.app_config.get_extraction_defaults()
            if hasattr(self.app_config, "get_extraction_defaults")
            else {}
        )

        file_menu = tk.Menu(self.menubar, tearoff=0)
        file_menu.add_command(
            label="Select directory",
            command=lambda: (
                self.select_directory(self.input_dir, self.input_dir_label)
                and self.settings_manager.animation_settings.clear()
                and self.settings_manager.spritesheet_settings.clear()
            ),
        )
        file_menu.add_command(
            label="Select files",
            command=lambda: self.select_files_manually(self.input_dir, self.input_dir_label),
        )
        file_menu.add_command(label="Clear filelist and user settings", command=self.clear_filelist)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        self.menubar.add_cascade(label="File", menu=file_menu)

        import_menu = tk.Menu(self.menubar, tearoff=0)
        import_menu.add_command(
            label="FNF: Import settings from character data file",
            command=lambda: self.fnf_utilities.fnf_select_char_data_directory(
                self.settings_manager, self.data_dict, self.listbox_png, self.listbox_data
            ),
        )
        self.menubar.add_cascade(label="Import", menu=import_menu)

        help_menu = tk.Menu(self.menubar, tearoff=0)
        help_menu.add_command(label="Manual", command=HelpWindow.create_main_help_window)
        help_menu.add_separator()
        help_menu.add_command(
            label="FNF: GIF/WebP settings advice", command=HelpWindow.create_fnf_help_window
        )
        self.menubar.add_cascade(label="Help", menu=help_menu)

        advanced_menu = tk.Menu(self.menubar, tearoff=0)
        self.variable_delay = tk.BooleanVar(value=defaults.get("variable_delay"))
        self.fnf_idle_loop = tk.BooleanVar(value=defaults.get("fnf_idle_loop"))
        advanced_menu.add_checkbutton(label="Variable delay", variable=self.variable_delay)
        advanced_menu.add_checkbutton(
            label="FNF: Set loop delay on idle animations to 0", variable=self.fnf_idle_loop
        )
        self.menubar.add_cascade(label="Advanced", menu=advanced_menu)

        options_menu = tk.Menu(self.menubar, tearoff=0)
        options_menu.add_command(label="Preferences", command=self.create_app_config_window)
        options_menu.add_separator()
        options_menu.add_command(
            label="Check for Updates", command=lambda: self.check_version(force=True)
        )
        self.menubar.add_cascade(label="Options", menu=options_menu)

    def setup_widgets(self):
        defaults = (
            self.app_config.get_extraction_defaults()
            if hasattr(self.app_config, "get_extraction_defaults")
            else {}
        )
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.root, length=865, variable=self.progress_var)
        self.progress_bar.pack(pady=8)

        self.scrollbar_png = tk.Scrollbar(self.root)
        self.scrollbar_png.pack(side=tk.LEFT, fill=tk.Y)

        self.listbox_png = tk.Listbox(
            self.root, width=30, exportselection=0, yscrollcommand=self.scrollbar_png.set
        )
        self.listbox_png.pack(side=tk.LEFT, fill=tk.Y)

        self.scrollbar_xml = tk.Scrollbar(self.root)
        self.scrollbar_xml.pack(side=tk.LEFT, fill=tk.Y)

        self.listbox_data = tk.Listbox(self.root, width=30, yscrollcommand=self.scrollbar_xml.set)
        self.listbox_data.pack(side=tk.LEFT, fill=tk.Y)

        self.scrollbar_png.config(command=self.listbox_png.yview)
        self.scrollbar_xml.config(command=self.listbox_data.yview)

        self.listbox_png_menu = tk.Menu(self.root, tearoff=0)
        self.listbox_png_menu.add_command(label="Delete", command=self.delete_selected_spritesheet)
        self.listbox_png.bind("<Button-3>", self.show_listbox_png_menu)

        self.input_dir = tk.StringVar()
        self.input_button = tk.Button(
            self.root,
            text="Select directory with spritesheets",
            cursor="hand2",
            command=lambda: self.select_directory(self.input_dir, self.input_dir_label)
            and self.settings_manager.animation_settings.clear()
            and self.settings_manager.spritesheet_settings.clear(),
        )
        self.input_button.pack(pady=2)

        self.input_dir_label = tk.Label(self.root, text="No input directory selected")
        self.input_dir_label.pack(pady=2)

        self.output_dir = tk.StringVar()
        self.output_button = tk.Button(
            self.root,
            text="Select save directory",
            cursor="hand2",
            command=lambda: self.select_directory(self.output_dir, self.output_dir_label),
        )
        self.output_button.pack(pady=2)

        self.output_dir_label = tk.Label(self.root, text="No output directory selected")
        self.output_dir_label.pack(pady=2)

        ttk.Separator(self.root, orient="horizontal").pack(fill="x", pady=2)

        self.frame_settings_frame = tk.Frame(self.root)
        self.frame_settings_frame.pack(fill="x", pady=2)
        self.animation_settings_frame = tk.Frame(self.frame_settings_frame)
        self.animation_settings_frame.pack(side=tk.LEFT, fill="both", expand=True, padx=(0, 5))

        # Animation settings
        self.animation_format = tk.StringVar(value=defaults.get("animation_format"))
        self.animation_format_label = tk.Label(
            self.animation_settings_frame, text="Animation format:"
        )
        self.animation_format_label.pack()
        self.animation_format_combobox = ttk.Combobox(
            self.animation_settings_frame,
            textvariable=self.animation_format,
            values=["None", "GIF", "WebP", "APNG"],
            state="readonly",
        )
        self.animation_format_combobox.bind(
            "<<ComboboxSelected>>", self._on_animation_format_change
        )
        self.animation_format_combobox.pack(pady=(0, 5))

        self.set_framerate = tk.DoubleVar(value=defaults.get("fps"))
        self.frame_rate_label = tk.Label(self.animation_settings_frame, text="Frame rate (fps):")
        self.frame_rate_label.pack()
        self.frame_rate_entry = tk.Entry(
            self.animation_settings_frame, textvariable=self.set_framerate
        )
        self.frame_rate_entry.pack(pady=(0, 5))

        self.set_loopdelay = tk.DoubleVar(value=defaults.get("delay"))
        self.loopdelay_label = tk.Label(self.animation_settings_frame, text="Loop delay (ms):")
        self.loopdelay_label.pack()
        self.loopdelay_entry = tk.Entry(
            self.animation_settings_frame, textvariable=self.set_loopdelay
        )
        self.loopdelay_entry.pack(pady=(0, 5))

        self.set_minperiod = tk.DoubleVar(value=defaults.get("period"))
        self.minperiod_label = tk.Label(self.animation_settings_frame, text="Minimum period (ms):")
        self.minperiod_label.pack()
        self.minperiod_entry = tk.Entry(
            self.animation_settings_frame, textvariable=self.set_minperiod
        )
        self.minperiod_entry.pack(pady=(0, 5))

        self.set_scale = tk.DoubleVar(value=defaults.get("scale"))
        self.scale_label = tk.Label(self.animation_settings_frame, text="Scale:")
        self.scale_label.pack()
        self.scale_entry = tk.Entry(self.animation_settings_frame, textvariable=self.set_scale)
        self.scale_entry.pack(pady=(0, 5))

        self.set_threshold = tk.DoubleVar(value=defaults.get("threshold"))
        self.threshold_label = tk.Label(self.animation_settings_frame, text="Alpha threshold:")
        self.threshold_label.pack()
        self.threshold_entry = tk.Entry(
            self.animation_settings_frame, textvariable=self.set_threshold
        )
        self.threshold_entry.pack(pady=(0, 5))

        # Frame settings
        self.frame_settings_frame = tk.Frame(self.frame_settings_frame)
        self.frame_settings_frame.pack(side=tk.LEFT, fill="both", expand=True, padx=(5, 0))

        self.frame_format = tk.StringVar(value=defaults.get("frame_format"))
        self.frame_format_label = tk.Label(self.frame_settings_frame, text="Frame format:")
        self.frame_format_label.pack()
        self.frame_format_menu = ttk.Combobox(
            self.frame_settings_frame, textvariable=self.frame_format, state="readonly"
        )
        self.frame_format_menu["values"] = (
            "None",
            "AVIF",
            "BMP",
            "DDS",
            "PNG",
            "TGA",
            "TIFF",
            "WebP",
        )
        self.frame_format_menu.bind("<<ComboboxSelected>>", self._on_frame_format_change)
        self.frame_format_menu.pack(pady=(0, 5))

        self.frame_selection = tk.StringVar(value=defaults.get("frame_selection", "All"))
        self.frame_selection_label = tk.Label(self.frame_settings_frame, text="Frame selection:")
        self.frame_selection_label.pack()
        self.frame_selection_menu = ttk.Combobox(
            self.frame_settings_frame, textvariable=self.frame_selection
        )
        self.frame_selection_menu["values"] = (
            "All",
            "No duplicates",
            "First",
            "Last",
            "First, Last",
        )
        self.frame_selection_menu.pack(pady=(0, 5))

        self.frame_scale = tk.DoubleVar(value=defaults.get("frame_scale", 1.0))
        self.frame_scale_label = tk.Label(self.frame_settings_frame, text="Frame scale:")
        self.frame_scale_label.pack()
        self.frame_scale_entry = tk.Entry(self.frame_settings_frame, textvariable=self.frame_scale)
        self.frame_scale_entry.pack(pady=(0, 5))

        # Frame Compression settings
        self.compression_frame = tk.Frame(self.frame_settings_frame)
        self.compression_frame.pack(pady=(0, 5), fill="x")

        self.frame_compression_label = tk.Label(self.compression_frame, text="Compression:")
        self.frame_compression_label.pack()

        self.compression_widgets = {}
        self._setup_compression_widgets()

        png_defaults = self.app_config.get_compression_defaults("png")
        webp_defaults = self.app_config.get_compression_defaults("webp")
        avif_defaults = self.app_config.get_compression_defaults("avif")
        tiff_defaults = self.app_config.get_compression_defaults("tiff")

        self.png_compress_level = tk.IntVar(value=png_defaults.get("compress_level", 9))
        self.png_optimize = tk.BooleanVar(value=png_defaults.get("optimize", True))
        self.webp_quality = tk.IntVar(value=webp_defaults.get("quality", 100))
        self.webp_method = tk.IntVar(value=webp_defaults.get("method", 6))
        self.webp_lossless = tk.BooleanVar(value=webp_defaults.get("lossless", True))
        self.webp_alpha_quality = tk.IntVar(value=webp_defaults.get("alpha_quality", 100))
        self.webp_exact = tk.BooleanVar(value=webp_defaults.get("exact", True))
        self.avif_quality = tk.IntVar(value=avif_defaults.get("quality", 100))
        self.avif_speed = tk.IntVar(value=avif_defaults.get("speed", 0))
        self.avif_lossless = tk.BooleanVar(value=avif_defaults.get("lossless", True))
        self.tiff_compression_type = tk.StringVar(
            value=tiff_defaults.get("compression_type", "lzw")
        )
        self.tiff_compression_type.trace_add("write", self._on_tiff_compression_type_change)
        self.tiff_quality = tk.IntVar(value=tiff_defaults.get("quality", 90))
        self.tiff_optimize = tk.BooleanVar(value=tiff_defaults.get("optimize", True))

        # General settings
        ttk.Separator(self.root, orient="horizontal").pack(fill="x", pady=2)
        self.crop_option = tk.StringVar(value=defaults.get("crop_option"))
        self.crop_menu_label = tk.Label(self.root, text="Cropping method:")
        self.crop_menu_label.pack()
        self.crop_menu_menu = ttk.Combobox(
            self.root, textvariable=self.crop_option, state="readonly"
        )
        self.crop_menu_menu["values"] = ("None", "Animation based", "Frame based")
        self.crop_menu_menu.pack(pady=2)

        self.prefix_label = tk.Label(self.root, text="Filename prefix:")
        self.prefix_label.pack()
        self.prefix = tk.StringVar(value="")
        self.prefix_entry = tk.Entry(self.root, textvariable=self.prefix)
        self.prefix_entry.pack()

        self.filename_format = tk.StringVar(value=defaults.get("filename_format"))
        self.filename_format_label = tk.Label(self.root, text="Filename format:")
        self.filename_format_label.pack()
        self.filename_format_menu = ttk.Combobox(self.root, textvariable=self.filename_format)
        self.filename_format_menu["values"] = ("Standardized", "No spaces", "No special characters")
        self.filename_format_menu.pack(pady=2)
        # "Standardized" example: "GodsentGaslit - Catnap - Idle"
        # "No Spaces" example: "GodsentGaslit-Catnap-Idle"
        # "No Special Characters" example: "GodsentGaslitCatnapIdle"

        self.replace_rules = []
        self.replace_button = tk.Button(
            self.root,
            text="Find and replace",
            cursor="hand2",
            command=lambda: self.create_find_and_replace_window(),
        )
        self.replace_button.pack(pady=2)

        self.button_frame = tk.Frame(self.root)
        self.button_frame.pack(pady=8)

        self.show_user_settings = tk.Button(
            self.button_frame, text="Show user settings", command=self.create_settings_window
        )
        self.show_user_settings.pack(side=tk.LEFT, padx=4)

        self.process_button = tk.Button(
            self.button_frame,
            text="Start process",
            cursor="hand2",
            command=lambda: self.start_process(),
        )
        self.process_button.pack(side=tk.LEFT, padx=2)

        self.author_label = tk.Label(self.root, text="Project started by AutisticLulu")
        self.author_label.pack(side="bottom")
        self.linkSourceCode = "https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames"
        self.link1 = tk.Label(
            self.root,
            text="If you wish to contribute to the project, click here!",
            fg="blue",
            cursor="hand2",
        )
        self.link1.pack(side="bottom")
        self.link1.bind("<Button-1>", lambda e: self.contributeLink(self.linkSourceCode))

        self._on_frame_format_change()
        self._on_animation_format_change()
        self._initialize_compression_defaults()

    def contributeLink(self, linkSourceCode):
        webbrowser.open_new(linkSourceCode)

    def check_version(self, force=False):
        try:
            update_settings = self.app_config.get(
                "update_settings", self.app_config.DEFAULTS["update_settings"]
            )
            check_on_startup = update_settings.get("check_updates_on_startup", True)
            auto_update = update_settings.get("auto_download_updates", False)
            if force or check_on_startup:
                UpdateChecker.check_for_updates(
                    self.current_version, auto_update=auto_update, parent_window=self.root
                )
        except Exception as e:
            print(f"Update check failed: {e}")

    def check_dependencies(self):
        DependenciesChecker.check_and_configure_imagemagick()

    def create_app_config_window(self):
        AppConfigWindow(self.root, self.app_config)

    def clear_filelist(self):
        self.listbox_png.delete(0, tk.END)
        self.listbox_data.delete(0, tk.END)
        self.settings_manager.animation_settings.clear()  # Clear animation-specific settings
        self.settings_manager.spritesheet_settings.clear()  # Clear spritesheet-specific settings

    def select_directory(self, variable, label):
        directory = filedialog.askdirectory()
        if directory:
            variable.set(directory)
            label.config(text=directory)
            if variable == self.input_dir:
                self.clear_filelist()
                processed_files = set()

                for filename in os.listdir(directory):
                    if filename.endswith(".xml") or filename.endswith(".txt"):
                        base_name = os.path.splitext(filename)[0]
                        png_filename = base_name + ".png"
                        if os.path.isfile(os.path.join(directory, png_filename)):
                            self.listbox_png.insert(tk.END, png_filename)
                            processed_files.add(png_filename)

                for filename in os.listdir(directory):
                    if (filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp')) 
                        and filename not in processed_files):
                        self.listbox_png.insert(tk.END, filename)
                
                self.listbox_png.bind("<<ListboxSelect>>", self.on_select_spritesheet)
                self.listbox_png.bind("<Double-1>", self.on_double_click_spritesheet)
                self.listbox_data.bind("<Double-1>", self.on_double_click_animation)
        return directory

    def select_files_manually(self, variable, label):
        data_files = filedialog.askopenfilenames(filetypes=[("XML and TXT files", "*.xml *.txt")])
        png_files = filedialog.askopenfilenames(filetypes=[("PNG files", "*.png")])
        variable.set(self.temp_dir)
        label.config(text=self.temp_dir)
        if data_files and png_files:
            for file in data_files:
                shutil.copy(file, self.temp_dir)
                png_filename = os.path.splitext(os.path.basename(file))[0] + ".png"
                if any(png_filename == os.path.basename(png) for png in png_files):
                    if png_filename not in [
                        self.listbox_png.get(idx) for idx in range(self.listbox_png.size())
                    ]:
                        self.listbox_png.insert(tk.END, png_filename)
                        self.data_dict[png_filename] = os.path.basename(file)
            for file in png_files:
                shutil.copy(file, self.temp_dir)
            self.listbox_png.unbind("<<ListboxSelect>>")
            self.listbox_data.unbind("<Double-1>")
            self.listbox_png.bind("<<ListboxSelect>>", self.on_select_spritesheet)
            self.listbox_data.bind("<Double-1>", self.on_double_click_animation)
        return self.temp_dir

    def create_settings_window(self):
        SettingsWindow(self.root, self.settings_manager)

    def create_find_and_replace_window(self):
        FindReplaceWindow(self.root, self.replace_rules, self.store_replace_rules)

    def store_replace_rules(self, rules):
        self.replace_rules = rules

    def create_override_settings_window(self, window, name, settings_type):
        self.update_global_settings()
        OverrideSettingsWindow(
            window, name, settings_type, self.settings_manager, self.store_input, app=self
        )

    def on_select_spritesheet(self, evt):
        self.listbox_data.delete(0, tk.END)

        png_filename = self.listbox_png.get(self.listbox_png.curselection())
        base_filename = os.path.splitext(png_filename)[0]
        xml_filename = base_filename + ".xml"
        txt_filename = base_filename + ".txt"

        directory = self.input_dir.get()

        if os.path.isfile(os.path.join(directory, xml_filename)):
            xml_parser = XmlParser(directory, xml_filename, self.listbox_data)
            xml_parser.get_data()
        elif os.path.isfile(os.path.join(directory, txt_filename)):
            txt_parser = TxtParser(directory, txt_filename, self.listbox_data)
            txt_parser.get_data()
        else:
            # Attempt using a generic parser for images with missing metadata
            image_path = os.path.join(directory, png_filename)
            if os.path.isfile(image_path):
                unknown_parser = UnknownParser(directory, png_filename, self.listbox_data)
                unknown_parser.get_data()

    def on_double_click_spritesheet(self, evt):
        spritesheet_name = self.listbox_png.get(self.listbox_png.curselection())
        new_window = tk.Toplevel()
        new_window.geometry("360x360")
        self.create_override_settings_window(new_window, spritesheet_name, "spritesheet")

    def on_double_click_animation(self, evt):
        spritesheet_name = self.listbox_png.get(self.listbox_png.curselection())
        animation_name = self.listbox_data.get(self.listbox_data.curselection())
        full_anim_name = spritesheet_name + "/" + animation_name
        new_window = tk.Toplevel()
        new_window.geometry("360x400")
        self.create_override_settings_window(new_window, full_anim_name, "animation")

    def show_listbox_png_menu(self, event):
        try:
            index = self.listbox_png.nearest(event.y)
            self.listbox_png.selection_clear(0, tk.END)
            self.listbox_png.selection_set(index)
            self.listbox_png.activate(index)
            self.listbox_png_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.listbox_png_menu.grab_release()

    def delete_selected_spritesheet(self):
        selection = self.listbox_png.curselection()
        if selection:
            spritesheet_name = self.listbox_png.get(selection[0])
            self.listbox_png.delete(selection[0])
            self.listbox_data.delete(0, tk.END)

            keys = list(self.data_dict.keys())
            if selection[0] < len(keys):
                del self.data_dict[keys[selection[0]]]

            self.settings_manager.delete_spritesheet_settings(spritesheet_name)
            # print(f"Removed: {spritesheet_name}")

            prefix = spritesheet_name + "/"
            anims_to_delete = [
                key for key in self.settings_manager.animation_settings if key.startswith(prefix)
            ]
            for anim in anims_to_delete:
                self.settings_manager.delete_animation_settings(anim)

    def preview_gif_window(
        self,
        name,
        settings_type,
        fps_entry,
        delay_entry,
        period_entry,
        scale_entry,
        threshold_entry,
        indices_entry,
        frames_entry,
    ):
        GifPreviewWindow.preview(
            self,
            name,
            settings_type,
            fps_entry,
            delay_entry,
            period_entry,
            scale_entry,
            threshold_entry,
            indices_entry,
            frames_entry,
        )

    def show_gif_preview_window(self, gif_path, settings):
        GifPreviewWindow.show(gif_path, settings)

    def store_input(
        self,
        window,
        name,
        settings_type,
        fps_entry,
        delay_entry,
        period_entry,
        scale_entry,
        threshold_entry,
        indices_entry,
        frames_entry,
        filename_entry,
        frame_format_entry=None,
        frame_scale_entry=None,
    ):
        settings = {}
        try:
            if fps_entry.get() != "":
                settings["fps"] = float(fps_entry.get())
            if delay_entry.get() != "":
                settings["delay"] = int(float(delay_entry.get()))
            if period_entry.get() != "":
                settings["period"] = int(float(period_entry.get()))
            if scale_entry.get() != "":
                if float(scale_entry.get()) == 0:
                    raise ValueError
                settings["scale"] = float(scale_entry.get())
            if threshold_entry.get() != "":
                settings["threshold"] = min(max(float(threshold_entry.get()), 0), 1)
            if indices_entry.get() != "":
                indices = [int(ele) for ele in indices_entry.get().split(",")]
                settings["indices"] = indices
            if frames_entry.get() != "":
                settings["frame_selection"] = frames_entry.get()
            if filename_entry and filename_entry.get() != "":
                settings["filename"] = filename_entry.get()
            if frame_format_entry and frame_format_entry.get() != "":
                settings["frame_format"] = frame_format_entry.get()
            if frame_scale_entry and frame_scale_entry.get() != "":
                if float(frame_scale_entry.get()) == 0:
                    raise ValueError("Frame scale cannot be zero")
                settings["frame_scale"] = float(frame_scale_entry.get())
        except ValueError as e:
            messagebox.showerror("Invalid input", f"Error: {str(e)}")
            window.lift()
            return

        settings_method_map = {
            "animation": self.settings_manager.set_animation_settings,
            "spritesheet": self.settings_manager.set_spritesheet_settings,
        }

        settings_method = settings_method_map.get(settings_type)
        if settings_method:
            settings_method(name, **settings)

        window.destroy()

    def update_global_settings(self):
        compression_settings = {
            "png_compress_level": self.png_compress_level.get(),
            "png_optimize": self.png_optimize.get(),
            "webp_lossless": self.webp_lossless.get(),
            "webp_quality": self.webp_quality.get(),
            "webp_method": self.webp_method.get(),
            "webp_alpha_quality": self.webp_alpha_quality.get(),
            "webp_exact": self.webp_exact.get(),
            "avif_lossless": self.avif_lossless.get(),
            "avif_quality": self.avif_quality.get(),
            "avif_speed": self.avif_speed.get(),
            "tiff_compression_type": self.tiff_compression_type.get(),
            "tiff_quality": self.tiff_quality.get(),
            "tiff_optimize": self.tiff_optimize.get(),
        }

        self.settings_manager.set_global_settings(
            animation_format=self.animation_format.get(),
            fps=self.set_framerate.get(),
            delay=self.set_loopdelay.get(),
            period=self.set_minperiod.get(),
            scale=self.set_scale.get(),
            threshold=self.set_threshold.get(),
            frame_format=self.frame_format.get(),
            frame_selection=self.frame_selection.get(),
            frame_scale=self.frame_scale.get(),
            compression_settings=compression_settings,
            crop_option=self.crop_option.get(),
            prefix=self.prefix.get(),
            filename_format=self.filename_format.get(),
            replace_rules=self.replace_rules,
            var_delay=self.variable_delay.get(),
            fnf_idle_loop=self.fnf_idle_loop.get(),
        )
        print("Global settings updated:", self.settings_manager.global_settings)

    def on_closing(self):
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        self.root.destroy()

    def check_for_unknown_atlases(self, spritesheet_list):
        unknown_atlases = []
        input_directory = self.input_dir.get()

        for filename in spritesheet_list:
            base_filename = filename.rsplit(".", 1)[0]
            xml_path = os.path.join(input_directory, base_filename + ".xml")
            txt_path = os.path.join(input_directory, base_filename + ".txt")
            image_path = os.path.join(input_directory, filename)

            # Check if this is an unknown atlas (no metadata file but is an image)
            if (
                not os.path.isfile(xml_path)
                and not os.path.isfile(txt_path)
                and os.path.isfile(image_path)
                and filename.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"))
            ):
                unknown_atlases.append(filename)

        return len(unknown_atlases) > 0, unknown_atlases

    def show_unknown_atlas_warning(self, unknown_atlases):
        return UnknownAtlasWarningWindow.show_warning(self.root, unknown_atlases)

    def filter_unknown_atlases(self, unknown_atlases):
        for unknown_atlas in unknown_atlases:
            for i in range(self.listbox_png.size()):
                if self.listbox_png.get(i) == unknown_atlas:
                    self.listbox_png.delete(i)
                    break

        self.listbox_data.delete(0, tk.END)

    def start_process(self):
        self.update_global_settings()

        if any(char in self.settings_manager.global_settings["prefix"] for char in r'\/:*?"<>|'):
            messagebox.showerror("Invalid Prefix", "The prefix contains invalid characters.")
            return

        spritesheet_list = [self.listbox_png.get(i) for i in range(self.listbox_png.size())]
        has_unknown, unknown_atlases = self.check_for_unknown_atlases(spritesheet_list)

        if has_unknown:
            action = self.show_unknown_atlas_warning(unknown_atlases)
            if action == 'cancel':
                return
            elif action == 'skip':
                self.filter_unknown_atlases(unknown_atlases)

        self.process_button.config(state="disabled", text="Processing...")

        process_thread = threading.Thread(target=self.run_extractor)
        process_thread.start()

    def run_extractor(self):
        try:
            spritesheet_list = [self.listbox_png.get(i) for i in range(self.listbox_png.size())]

            extractor = Extractor(
                self.progress_bar,
                self.current_version,
                self.settings_manager,
                app_config=self.app_config,
            )
            extractor.process_directory(
                self.input_dir.get(),
                self.output_dir.get(),
                self.progress_var,
                self.root,
                spritesheet_list=spritesheet_list,
            )
        finally:
            self.root.after(0, self._re_enable_process_button)

    def _re_enable_process_button(self):
        self.process_button.config(state="normal", text="Start process")

    def _on_frame_compression_change(self, event=None):
        frame_format = self.frame_format.get()

        for widget_info in self.compression_widgets.values():
            widget_info["frame"].pack_forget()

        if frame_format == "PNG":
            self._show_png_compression_widgets()
        elif frame_format == "WebP":
            self._show_webp_compression_widgets()
        elif frame_format == "AVIF":
            self._show_avif_compression_widgets()
        elif frame_format == "TIFF":
            self._show_tiff_compression_widgets()
        elif frame_format in ["TGA", "BMP", "DDS"]:
            self.frame_compression_label.config(state="disabled")
            return
        else:
            self.frame_compression_label.config(state="disabled")
            return

        self.frame_compression_label.config(state="normal")

    def _show_png_compression_widgets(self):
        widgets = self.compression_widgets["PNG"]
        widgets["frame"].pack(fill="x", pady=2)

        widgets["compress_level"].config(variable=self.png_compress_level)
        widgets["optimize"].config(variable=self.png_optimize, command=self._on_png_optimize_change)
        widgets["compress_level"].set(self.png_compress_level.get())
        if self.png_optimize.get():
            widgets["optimize"].select()
        else:
            widgets["optimize"].deselect()

        self._on_png_optimize_change()

    def _show_webp_compression_widgets(self):
        widgets = self.compression_widgets["WebP"]
        widgets["frame"].pack(fill="x", pady=2)

        widgets["lossless"].config(
            variable=self.webp_lossless, command=self._on_webp_lossless_change
        )
        widgets["quality"].config(variable=self.webp_quality)
        widgets["method"].config(variable=self.webp_method)
        widgets["alpha_quality"].config(variable=self.webp_alpha_quality)
        widgets["exact"].config(variable=self.webp_exact)

        if self.webp_lossless.get():
            widgets["lossless"].select()
        else:
            widgets["lossless"].deselect()

        widgets["quality"].set(self.webp_quality.get())
        widgets["method"].set(self.webp_method.get())
        widgets["alpha_quality"].set(self.webp_alpha_quality.get())

        if self.webp_exact.get():
            widgets["exact"].select()
        else:
            widgets["exact"].deselect()

        self._on_webp_lossless_change()

    def _show_avif_compression_widgets(self):
        widgets = self.compression_widgets["AVIF"]
        widgets["frame"].pack(fill="x", pady=2)

        widgets["lossless"].config(
            variable=self.avif_lossless, command=self._on_avif_lossless_change
        )
        widgets["quality"].config(variable=self.avif_quality)
        widgets["speed"].config(variable=self.avif_speed)
        if self.avif_lossless.get():
            widgets["lossless"].select()
        else:
            widgets["lossless"].deselect()
        widgets["quality"].set(self.avif_quality.get())
        widgets["speed"].set(self.avif_speed.get())

        self._on_avif_lossless_change()

    def _show_tiff_compression_widgets(self):
        widgets = self.compression_widgets["TIFF"]
        widgets["frame"].pack(fill="x", pady=2)

        widgets["type"].config(textvariable=self.tiff_compression_type)
        widgets["quality"].config(variable=self.tiff_quality)
        widgets["optimize"].config(variable=self.tiff_optimize)
        widgets["type"].set(self.tiff_compression_type.get())
        widgets["quality"].set(self.tiff_quality.get())
        if self.tiff_optimize.get():
            widgets["optimize"].select()
        else:
            widgets["optimize"].deselect()

        self._on_tiff_compression_type_change()

    def _on_frame_format_change(self, event=None):
        if self.frame_format.get() == "None":
            self.frame_selection_label.config(state="disabled")
            self.frame_selection_menu.config(state="disabled")
            self.frame_scale_label.config(state="disabled")
            self.frame_scale_entry.config(state="disabled")
            self.frame_compression_label.config(state="disabled")

            for widget_info in self.compression_widgets.values():
                widget_info["frame"].pack_forget()
        else:
            self.frame_selection_label.config(state="normal")
            self.frame_selection_menu.config(state="readonly")
            self.frame_scale_label.config(state="normal")
            self.frame_scale_entry.config(state="normal")
            self._on_frame_compression_change()

    def _on_animation_format_change(self, event=None):
        animation_format = self.animation_format.get()

        if animation_format == "None":
            self.frame_rate_label.config(state="disabled")
            self.frame_rate_entry.config(state="disabled")
            self.loopdelay_label.config(state="disabled")
            self.loopdelay_entry.config(state="disabled")
            self.minperiod_label.config(state="disabled")
            self.minperiod_entry.config(state="disabled")
            self.scale_label.config(state="disabled")
            self.scale_entry.config(state="disabled")
            self.threshold_label.config(state="disabled")
            self.threshold_entry.config(state="disabled")
        else:
            self.frame_rate_label.config(state="normal")
            self.frame_rate_entry.config(state="normal")
            self.loopdelay_label.config(state="normal")
            self.loopdelay_entry.config(state="normal")
            self.minperiod_label.config(state="normal")
            self.minperiod_entry.config(state="normal")
            self.scale_label.config(state="normal")
            self.scale_entry.config(state="normal")

            if animation_format.upper() == "GIF":
                self.threshold_label.config(state="normal")
                self.threshold_entry.config(state="normal")
            else:
                self.threshold_label.config(state="disabled")
                self.threshold_entry.config(state="disabled")

    def _setup_compression_widgets(self):
        self.compression_widgets = {}

        png_frame = tk.Frame(self.compression_frame)
        png_compress_level_frame = tk.Frame(png_frame)
        png_compress_level_frame.pack(fill="x", pady=2)
        png_compress_level_label = tk.Label(png_compress_level_frame, text="Compress Level (0-9):")
        png_compress_level_label.pack(side="left")
        png_compress_level_scale = tk.Scale(
            png_compress_level_frame, from_=0, to=9, orient="horizontal"
        )
        png_compress_level_scale.pack(side="right", fill="x", expand=True)

        png_optimize_frame = tk.Frame(png_frame)
        png_optimize_frame.pack(fill="x", pady=2)
        png_optimize_label = tk.Label(png_optimize_frame, text="Optimize:")
        png_optimize_label.pack(side="left")
        png_optimize_check = tk.Checkbutton(png_optimize_frame)
        png_optimize_check.pack(side="right")

        self.compression_widgets["PNG"] = {
            "frame": png_frame,
            "compress_level": png_compress_level_scale,
            "optimize": png_optimize_check,
        }

        Tooltip(
            png_compress_level_label,
            (
                "PNG compression level (0-9):\n"
                "• 0: No compression (fastest, largest file)\n"
                "• 1-3: Low compression\n"
                "• 4-6: Medium compression\n"
                "• 7-9: High compression (slowest, smallest file)\n"
                "This doesn't affect the quality of the image, only the file size"
            ),
        )
        Tooltip(
            png_compress_level_scale,
            (
                "PNG compression level (0-9):\n"
                "• 0: No compression (fastest, largest file)\n"
                "• 1-3: Low compression\n"
                "• 4-6: Medium compression\n"
                "• 7-9: High compression (slowest, smallest file)\n"
                "This doesn't affect the quality of the image, only the file size"
            ),
        )
        Tooltip(
            png_optimize_label,
            (
                "PNG optimize:\n"
                "• Enabled: Uses additional compression techniques for smaller files\n"
                "When enabled, compression level is automatically set to 9\n"
                "Results in slower processing but better compression\n\n"
                "This doesn't affect the quality of the image, only the file size"
            ),
        )
        Tooltip(
            png_optimize_check,
            (
                "PNG optimize:\n"
                "• Enabled: Uses additional compression techniques for smaller files\n"
                "When enabled, compression level is automatically set to 9\n"
                "Results in slower processing but better compression\n\n"
                "This doesn't affect the quality of the image, only the file size"
            ),
        )

        webp_frame = tk.Frame(self.compression_frame)
        webp_lossless_frame = tk.Frame(webp_frame)
        webp_lossless_frame.pack(fill="x", pady=2)
        webp_lossless_label = tk.Label(webp_lossless_frame, text="Lossless:")
        webp_lossless_label.pack(side="left")
        webp_lossless_check = tk.Checkbutton(webp_lossless_frame)
        webp_lossless_check.pack(side="right")

        webp_quality_frame = tk.Frame(webp_frame)
        webp_quality_frame.pack(fill="x", pady=2)
        webp_quality_label = tk.Label(webp_quality_frame, text="Quality (0-100):")
        webp_quality_label.pack(side="left")
        webp_quality_scale = tk.Scale(webp_quality_frame, from_=0, to=100, orient="horizontal")
        webp_quality_scale.pack(side="right", fill="x", expand=True)

        webp_method_frame = tk.Frame(webp_frame)
        webp_method_frame.pack(fill="x", pady=2)
        webp_method_label = tk.Label(webp_method_frame, text="Method (0-6):")
        webp_method_label.pack(side="left")
        webp_method_scale = tk.Scale(webp_method_frame, from_=0, to=6, orient="horizontal")
        webp_method_scale.pack(side="right", fill="x", expand=True)

        webp_alpha_quality_frame = tk.Frame(webp_frame)
        webp_alpha_quality_frame.pack(fill="x", pady=2)
        webp_alpha_quality_label = tk.Label(webp_alpha_quality_frame, text="Alpha Quality (0-100):")
        webp_alpha_quality_label.pack(side="left")
        webp_alpha_quality_scale = tk.Scale(
            webp_alpha_quality_frame, from_=0, to=100, orient="horizontal"
        )
        webp_alpha_quality_scale.pack(side="right", fill="x", expand=True)

        webp_exact_frame = tk.Frame(webp_frame)
        webp_exact_frame.pack(fill="x", pady=2)
        webp_exact_label = tk.Label(webp_exact_frame, text="Exact:")
        webp_exact_label.pack(side="left")
        webp_exact_check = tk.Checkbutton(webp_exact_frame)
        webp_exact_check.pack(side="right")

        self.compression_widgets["WebP"] = {
            "frame": webp_frame,
            "lossless": webp_lossless_check,
            "quality": webp_quality_scale,
            "method": webp_method_scale,
            "alpha_quality": webp_alpha_quality_scale,
            "exact": webp_exact_check,
        }

        Tooltip(
            webp_lossless_label,
            (
                "WebP lossless mode:\n"
                "• Enabled: Perfect quality preservation, larger file size\n"
                "• Disabled: Lossy compression with adjustable quality\n"
                "When enabled, quality sliders are disabled"
            ),
        )
        Tooltip(
            webp_lossless_check,
            (
                "WebP lossless mode:\n"
                "• Enabled: Perfect quality preservation, larger file size\n"
                "• Disabled: Lossy compression with adjustable quality\n"
                "When enabled, quality sliders are disabled"
            ),
        )
        Tooltip(
            webp_quality_label,
            (
                "WebP quality (0-100):\n"
                "• 0: Lowest quality, smallest file\n"
                "• 75: Balanced quality/size\n"
                "• 100: Highest quality, largest file\n"
                "Only used in lossy mode"
            ),
        )
        Tooltip(
            webp_quality_scale,
            (
                "WebP quality (0-100):\n"
                "• 0: Lowest quality, smallest file\n"
                "• 75: Balanced quality/size\n"
                "• 100: Highest quality, largest file\n"
                "Only used in lossy mode"
            ),
        )
        Tooltip(
            webp_method_label,
            (
                "WebP compression method (0-6):\n"
                "• 0: Fastest encoding, larger file\n"
                "• 3: Balanced speed/compression\n"
                "• 6: Slowest encoding, best compression\n"
                "Higher values take more time but produce smaller files"
            ),
        )
        Tooltip(
            webp_method_scale,
            (
                "WebP compression method (0-6):\n"
                "• 0: Fastest encoding, larger file\n"
                "• 3: Balanced speed/compression\n"
                "• 6: Slowest encoding, best compression\n"
                "Higher values take more time but produce smaller files"
            ),
        )
        Tooltip(
            webp_alpha_quality_label,
            (
                "WebP alpha channel quality (0-100):\n"
                "Controls transparency compression quality\n"
                "• 0: Maximum alpha compression\n"
                "• 100: Best alpha quality\n"
                "Only used in lossy mode"
            ),
        )
        Tooltip(
            webp_alpha_quality_scale,
            (
                "WebP alpha channel quality (0-100):\n"
                "Controls transparency compression quality\n"
                "• 0: Maximum alpha compression\n"
                "• 100: Best alpha quality\n"
                "Only used in lossy mode"
            ),
        )
        Tooltip(
            webp_exact_label,
            (
                "WebP exact mode:\n"
                "• Enabled: Preserves RGB values in transparent areas\n"
                "• Disabled: Allows optimization of transparent pixels\n"
                "Enable for better quality when transparency matters"
            ),
        )
        Tooltip(
            webp_exact_check,
            (
                "WebP exact mode:\n"
                "• Enabled: Preserves RGB values in transparent areas\n"
                "• Disabled: Allows optimization of transparent pixels\n"
                "Enable for better quality when transparency matters"
            ),
        )

        avif_frame = tk.Frame(self.compression_frame)
        avif_lossless_frame = tk.Frame(avif_frame)
        avif_lossless_frame.pack(fill="x", pady=2)
        tk.Label(avif_lossless_frame, text="Lossless:").pack(side="left")
        avif_lossless_check = tk.Checkbutton(avif_lossless_frame)
        avif_lossless_check.pack(side="right")

        avif_quality_frame = tk.Frame(avif_frame)
        avif_quality_frame.pack(fill="x", pady=2)
        tk.Label(avif_quality_frame, text="Quality (0-100):").pack(side="left")
        avif_quality_scale = tk.Scale(avif_quality_frame, from_=0, to=100, orient="horizontal")
        avif_quality_scale.pack(side="right", fill="x", expand=True)

        avif_speed_frame = tk.Frame(avif_frame)
        avif_speed_frame.pack(fill="x", pady=2)
        tk.Label(avif_speed_frame, text="Speed (0-10):").pack(side="left")
        avif_speed_scale = tk.Scale(avif_speed_frame, from_=0, to=10, orient="horizontal")
        avif_speed_scale.pack(side="right", fill="x", expand=True)

        self.compression_widgets["AVIF"] = {
            "frame": avif_frame,
            "lossless": avif_lossless_check,
            "quality": avif_quality_scale,
            "speed": avif_speed_scale,
        }

        Tooltip(
            avif_lossless_check,
            (
                "AVIF lossless mode:\n"
                "• Enabled: Perfect quality preservation, larger file size\n"
                "• Disabled: Lossy compression with adjustable quality\n"
                "When enabled, quality slider is disabled"
            ),
        )
        Tooltip(
            avif_quality_scale,
            (
                "AVIF quality (0-100):\n"
                "• 0: Lowest quality, smallest file\n"
                "• 100: Highest quality, largest file\n"
                "Only used in lossy mode"
            ),
        )
        Tooltip(
            avif_speed_scale,
            (
                "AVIF encoding speed (0-10):\n"
                "• 0: Slowest encoding, best compression\n"
                "• 5: Balanced speed/compression\n"
                "• 10: Fastest encoding, larger file\n"
                "Higher values encode faster but produce larger files.\nAVIF may take much longer to encode than other formats."
            ),
        )

        tiff_frame = tk.Frame(self.compression_frame)
        tiff_type_frame = tk.Frame(tiff_frame)
        tiff_type_frame.pack(fill="x", pady=2)
        tk.Label(tiff_type_frame, text="Compression Type:").pack(side="left")
        tiff_type_combo = ttk.Combobox(
            tiff_type_frame, values=["none", "lzw", "zip", "jpeg"], state="readonly"
        )
        tiff_type_combo.pack(side="right")

        tiff_quality_frame = tk.Frame(tiff_frame)
        tiff_quality_frame.pack(fill="x", pady=2)
        tk.Label(tiff_quality_frame, text="Quality (JPEG, 0-100):").pack(side="left")
        tiff_quality_scale = tk.Scale(tiff_quality_frame, from_=0, to=100, orient="horizontal")
        tiff_quality_scale.pack(side="right", fill="x", expand=True)

        tiff_optimize_frame = tk.Frame(tiff_frame)
        tiff_optimize_frame.pack(fill="x", pady=2)
        tk.Label(tiff_optimize_frame, text="Optimize:").pack(side="left")
        tiff_optimize_check = tk.Checkbutton(tiff_optimize_frame)
        tiff_optimize_check.pack(side="right")

        self.compression_widgets["TIFF"] = {
            "frame": tiff_frame,
            "type": tiff_type_combo,
            "quality": tiff_quality_scale,
            "optimize": tiff_optimize_check,
        }

        Tooltip(
            tiff_type_combo,
            (
                "TIFF compression type:\n"
                "• None: No compression (largest files, fastest)\n"
                "• LZW: Lossless compression (good for graphics)\n"
                "• ZIP: Lossless compression (good for photos)\n"
                "• JPEG: Lossy compression (smallest files, adjustable quality)"
            ),
        )
        Tooltip(
            tiff_quality_scale,
            (
                "TIFF JPEG quality (0-100):\n"
                "Only used when compression type is JPEG\n"
                "• 100: Highest quality, largest file"
            ),
        )
        Tooltip(
            tiff_optimize_check,
            (
                "TIFF optimize:\n"
                "• Enabled: Use additional optimization techniques\n"
                "Results in better compression but slower processing\n"
                "Not available when compression type is 'None'"
            ),
        )

        for widget_info in self.compression_widgets.values():
            widget_info["frame"].pack_forget()

    def _initialize_compression_defaults(self):
        widgets = self.compression_widgets.get("PNG", {})
        if "compress_level" in widgets:
            widgets["compress_level"].set(self.png_compress_level.get())
        if "optimize" in widgets:
            widgets["optimize"].select() if self.png_optimize.get() else widgets[
                "optimize"
            ].deselect()

        widgets = self.compression_widgets.get("WebP", {})
        if "lossless" in widgets:
            widgets["lossless"].select() if self.webp_lossless.get() else widgets[
                "lossless"
            ].deselect()
        if "quality" in widgets:
            widgets["quality"].set(self.webp_quality.get())
        if "method" in widgets:
            widgets["method"].set(self.webp_method.get())
        if "alpha_quality" in widgets:
            widgets["alpha_quality"].set(self.webp_alpha_quality.get())
        if "exact" in widgets:
            widgets["exact"].select() if self.webp_exact.get() else widgets["exact"].deselect()

        widgets = self.compression_widgets.get("AVIF", {})
        if "lossless" in widgets:
            widgets["lossless"].select() if self.avif_lossless.get() else widgets[
                "lossless"
            ].deselect()
        if "quality" in widgets:
            widgets["quality"].set(self.avif_quality.get())
        if "speed" in widgets:
            widgets["speed"].set(self.avif_speed.get())

        widgets = self.compression_widgets.get("TIFF", {})
        if "type" in widgets:
            widgets["type"].set(self.tiff_compression_type.get())
        if "quality" in widgets:
            widgets["quality"].set(self.tiff_quality.get())
        if "optimize" in widgets:
            widgets["optimize"].select() if self.tiff_optimize.get() else widgets[
                "optimize"
            ].deselect()

    def _on_png_optimize_change(self):
        if hasattr(self, "compression_widgets") and "PNG" in self.compression_widgets:
            widgets = self.compression_widgets["PNG"]
            if "compress_level" in widgets and "optimize" in widgets:
                if self.png_optimize.get():
                    widgets["compress_level"].config(state="disabled")
                    self.png_compress_level.set(9)
                else:
                    widgets["compress_level"].config(state="normal")

    def _on_webp_lossless_change(self):
        if hasattr(self, "compression_widgets") and "WebP" in self.compression_widgets:
            widgets = self.compression_widgets["WebP"]
            if "quality" in widgets and "alpha_quality" in widgets and "lossless" in widgets:
                if self.webp_lossless.get():
                    widgets["quality"].config(state="disabled")
                    widgets["alpha_quality"].config(state="disabled")
                else:
                    widgets["quality"].config(state="normal")
                    widgets["alpha_quality"].config(state="normal")

    def _on_avif_lossless_change(self):
        if hasattr(self, "compression_widgets") and "AVIF" in self.compression_widgets:
            widgets = self.compression_widgets["AVIF"]
            if "quality" in widgets and "lossless" in widgets:
                if self.avif_lossless.get():
                    widgets["quality"].config(state="disabled")
                else:
                    widgets["quality"].config(state="normal")

    def _on_tiff_compression_type_change(self, *args):
        if hasattr(self, "compression_widgets") and "TIFF" in self.compression_widgets:
            widgets = self.compression_widgets["TIFF"]
            if "type" in widgets and "quality" in widgets and "optimize" in widgets:
                compression_type = self.tiff_compression_type.get()

                if compression_type == "none":
                    widgets["quality"].config(state="disabled")
                    widgets["optimize"].config(state="disabled")
                elif compression_type == "jpeg":
                    widgets["quality"].config(state="normal")
                    widgets["optimize"].config(state="normal")
                else:
                    widgets["quality"].config(state="disabled")
                    widgets["optimize"].config(state="normal")

if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description="TextureAtlas to GIF and Frames")
        parser.add_argument("--update", action="store_true", help="Run in update mode")
        parser.add_argument("--exe-mode", action="store_true", help="Force executable update mode")
        parser.add_argument(
            "--wait", type=int, default=3, help="Seconds to wait before starting update"
        )
        args = parser.parse_args()

        if args.update:
            from utils.update_installer import Updater, UpdateUtilities

            print("Starting update process...")
            if args.wait > 0:
                print(f"Waiting {args.wait} seconds...")
                import time

                time.sleep(args.wait)

            exe_mode = args.exe_mode or Utilities.is_compiled()
            updater = Updater(use_gui=True, exe_mode=exe_mode)

            if exe_mode:
                print("Running executable update...")
                updater.update_exe()
            else:
                print("Running source update...")
                updater.update_source()

            if updater.use_gui and updater.console:
                updater.console.window.mainloop()
        else:
            print("Starting main application...")
            root = tk.Tk()
            app = TextureAtlasExtractorApp(root)
            print("Application initialized successfully.")
            root.mainloop()

    except Exception as e:
        print(f"Fatal error during startup: {e}")
        import traceback

        traceback.print_exc()

        if Utilities.is_compiled():
            try:
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror(
                    "Startup Error",
                    f"The application failed to start:\n\n{str(e)}\n\nPlease check the console output for more details.",
                )
                root.destroy()
            except Exception:
                pass

        import sys

        sys.exit(1)
