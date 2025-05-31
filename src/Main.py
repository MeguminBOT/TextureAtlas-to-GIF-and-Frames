import os
import platform
import shutil
import tempfile
import threading
import tkinter as tk
import webbrowser
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
from core.extractor import Extractor
from gui.app_config_window import AppConfigWindow
from gui.help_window import HelpWindow
from gui.find_replace_window import FindReplaceWindow
from gui.override_settings_window import OverrideSettingsWindow
from gui.gif_preview_window import GifPreviewWindow
from gui.settings_window import SettingsWindow

class TextureAtlasExtractorApp:
    """
    A GUI application for extracting textures from a texture atlas and converting them to GIF and WebP formats.

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
        keep_frames (tk.StringVar): Option for keeping frames.
        keepframes_label (tk.Label): Label for keep frames option.
        keepframes_menu (ttk.Combobox): Combobox for keep frames option.
        crop_option (tk.StringVar): Cropping method variable.
        crop_menu_label (tk.Label): Label for cropping method.
        crop_menu_menu (ttk.Combobox): Combobox for cropping method.
        prefix_label (tk.Label): Label for filename prefix.
        prefix (tk.StringVar): Filename prefix variable.
        prefix_entry (tk.Entry): Entry for filename prefix.
        filename_format (tk.StringVar): Filename format variable.
        filename_format_label (tk.Label): Label for filename format.
        filename_format_menu (ttk.Combobox): Combobox for filename format.
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
        check_version(): Checks for updates to the application.
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
    """

    def __init__(self, root):
        self.root = root
        self.current_version = '1.9.4'
        self.app_config = AppConfig()
        self.settings_manager = SettingsManager()
        self.temp_dir = tempfile.mkdtemp()
        self.data_dict = {}

        self.fnf_utilities = FnfUtilities()
        self.fnf_char_json_directory = ""

        self.setup_gui()
        self.check_version()

    def setup_gui(self):
        self.root.title(f"TextureAtlas to GIF and Frames v{self.current_version}")
        self.root.geometry("900x720")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        try:
            current_os = platform.system()
            assets_path = Utilities.find_root('assets')
            if current_os == "Windows":
                if assets_path is None:
                    raise FileNotFoundError("Could not find 'assets' folder in any parent directory.")
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
        defaults = self.app_config.get_extraction_defaults() if hasattr(self.app_config, 'get_extraction_defaults') else {}

        file_menu = tk.Menu(self.menubar, tearoff=0)
        file_menu.add_command(label="Select directory", command=lambda: self.select_directory(self.input_dir, self.input_dir_label) 
            and self.settings_manager.animation_settings.clear()
            and self.settings_manager.spritesheet_settings.clear()
        )
        file_menu.add_command(label="Select files", command=lambda: self.select_files_manually(self.input_dir, self.input_dir_label))
        file_menu.add_command(label="Clear filelist and user settings", command=self.clear_filelist)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        self.menubar.add_cascade(label="File", menu=file_menu)

        import_menu = tk.Menu(self.menubar, tearoff=0)
        import_menu.add_command(label="FNF: Import settings from character data file", command=lambda: self.fnf_utilities.fnf_select_char_data_directory(self.settings_manager, self.data_dict, self.listbox_png, self.listbox_data))
        self.menubar.add_cascade(label="Import", menu=import_menu)

        help_menu = tk.Menu(self.menubar, tearoff=0)
        help_menu.add_command(label="Manual", command=HelpWindow.create_main_help_window)
        help_menu.add_separator()
        help_menu.add_command(label="FNF: GIF/WebP settings advice", command=HelpWindow.create_fnf_help_window)
        self.menubar.add_cascade(label="Help", menu=help_menu)

        advanced_menu = tk.Menu(self.menubar, tearoff=0)
        self.variable_delay = tk.BooleanVar(value=defaults.get("variable_delay"))
        self.fnf_idle_loop = tk.BooleanVar(value=defaults.get("fnf_idle_loop"))
        advanced_menu.add_checkbutton(label="Variable delay", variable=self.variable_delay)
        advanced_menu.add_checkbutton(label="FNF: Set loop delay on idle animations to 0", variable=self.fnf_idle_loop)
        self.menubar.add_cascade(label="Advanced", menu=advanced_menu)

        options_menu = tk.Menu(self.menubar, tearoff=0)
        options_menu.add_command(label="Preferences", command=self.create_app_config_window)
        self.menubar.add_cascade(label="Options", menu=options_menu)

    def setup_widgets(self):
        defaults = self.app_config.get_extraction_defaults() if hasattr(self.app_config, 'get_extraction_defaults') else {}
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.root, length=865, variable=self.progress_var)
        self.progress_bar.pack(pady=8)

        self.scrollbar_png = tk.Scrollbar(self.root)
        self.scrollbar_png.pack(side=tk.LEFT, fill=tk.Y)

        self.listbox_png = tk.Listbox(self.root, width=30, exportselection=0, yscrollcommand=self.scrollbar_png.set)
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
        self.input_button = tk.Button(self.root, text="Select directory with spritesheets", cursor="hand2",
            command=lambda: self.select_directory(self.input_dir, self.input_dir_label) 
            and self.settings_manager.animation_settings.clear()
            and self.settings_manager.spritesheet_settings.clear()
        )
        self.input_button.pack(pady=2)

        self.input_dir_label = tk.Label(self.root, text="No input directory selected")
        self.input_dir_label.pack(pady=2)

        self.output_dir = tk.StringVar()
        self.output_button = tk.Button(self.root, text="Select save directory", cursor="hand2", command=lambda: self.select_directory(self.output_dir, self.output_dir_label))
        self.output_button.pack(pady=2)

        self.output_dir_label = tk.Label(self.root, text="No output directory selected")
        self.output_dir_label.pack(pady=2)
        
        ttk.Separator(root, orient="horizontal").pack(fill="x", pady=2)

        self.animation_format = tk.StringVar(value=defaults.get("animation_format"))
        self.animation_format_label = tk.Label(self.root, text="Animation format:")
        self.animation_format_label.pack()
        self.animation_format_combobox = ttk.Combobox(
            self.root,
            textvariable=self.animation_format,
            values=["None", "GIF", "WebP", "APNG"],
            state="readonly"
        )
        self.animation_format_combobox.pack()

        self.set_framerate = tk.DoubleVar(value=defaults.get("fps"))
        self.frame_rate_label = tk.Label(self.root, text="Frame rate (fps):")
        self.frame_rate_label.pack()
        self.frame_rate_entry = tk.Entry(self.root, textvariable=self.set_framerate)
        self.frame_rate_entry.pack()

        self.set_loopdelay = tk.DoubleVar(value=defaults.get("delay"))
        self.loopdelay_label = tk.Label(self.root, text="Loop delay (ms):")
        self.loopdelay_label.pack()
        self.loopdelay_entry = tk.Entry(self.root, textvariable=self.set_loopdelay)
        self.loopdelay_entry.pack()

        self.set_minperiod = tk.DoubleVar(value=defaults.get("period"))
        self.minperiod_label = tk.Label(self.root, text="Minimum period (ms):")
        self.minperiod_label.pack()
        self.minperiod_entry = tk.Entry(self.root, textvariable=self.set_minperiod)
        self.minperiod_entry.pack()

        self.set_scale = tk.DoubleVar(value=defaults.get("scale"))
        self.scale_label = tk.Label(self.root, text="Scale:")
        self.scale_label.pack()
        self.scale_entry = tk.Entry(self.root, textvariable=self.set_scale)
        self.scale_entry.pack()

        self.set_threshold = tk.DoubleVar(value=defaults.get("threshold"))
        self.threshold_label = tk.Label(self.root, text="Alpha threshold:")
        self.threshold_label.pack()
        self.threshold_entry = tk.Entry(self.root, textvariable=self.set_threshold)
        self.threshold_entry.pack(pady=4)

        ttk.Separator(root, orient="horizontal").pack(fill="x", pady=2)

        self.keep_frames = tk.StringVar(value=defaults.get("keep_frames"))
        self.keepframes_label = tk.Label(self.root, text="Keep individual frames:")
        self.keepframes_label.pack()
        self.keepframes_menu = ttk.Combobox(self.root, textvariable=self.keep_frames)
        self.keepframes_menu['values'] = ("None", "All", "No duplicates", "First", "Last", "First, Last")
        self.keepframes_menu.pack(pady=2)

        self.crop_option = tk.StringVar(value=defaults.get("crop_option"))
        self.crop_menu_label = tk.Label(self.root, text="Cropping method:")
        self.crop_menu_label.pack()
        self.crop_menu_menu = ttk.Combobox(self.root, textvariable=self.crop_option, state="readonly")
        self.crop_menu_menu['values'] = ("None", "Animation based", "Frame based")
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
        self.filename_format_menu['values'] = ("Standardized", "No spaces", "No special characters")
        self.filename_format_menu.pack(pady=2)
        # "Standardized" example: "GodsentGaslit - Catnap - Idle"
        # "No Spaces" example: "GodsentGaslit-Catnap-Idle"
        # "No Special Characters" example: "GodsentGaslitCatnapIdle"
        self.replace_rules = []
        self.replace_button = tk.Button(self.root, text="Find and replace", cursor="hand2", command=lambda: self.create_find_and_replace_window())
        self.replace_button.pack(pady=2)
        
        self.button_frame = tk.Frame(self.root)
        self.button_frame.pack(pady=8)

        self.show_user_settings = tk.Button(self.button_frame, text="Show user settings", command=self.create_settings_window)
        self.show_user_settings.pack(side=tk.LEFT, padx=4)

        self.process_button = tk.Button(self.button_frame, text="Start process", cursor="hand2", command=lambda: self.start_process())
        self.process_button.pack(side=tk.LEFT, padx=2)

        self.author_label = tk.Label(self.root, text="Project started by AutisticLulu")
        self.author_label.pack(side='bottom')

        self.linkSourceCode = "https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames"
        self.link1 = tk.Label(self.root, text="If you wish to contribute to the project, click here!", fg="blue", cursor="hand2")
        self.link1.pack(side='bottom')
        self.link1.bind("<Button-1>", lambda e: self.contributeLink(self.linkSourceCode))

    def contributeLink(self, linkSourceCode):
        webbrowser.open_new(linkSourceCode)
        
    def check_version(self):
        UpdateChecker.check_for_updates(self.current_version)

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
                for filename in os.listdir(directory):
                    if filename.endswith('.xml') or filename.endswith('.txt'):
                        self.listbox_png.insert(tk.END, os.path.splitext(filename)[0] + '.png')
                self.listbox_png.bind('<<ListboxSelect>>', self.on_select_spritesheet)
                self.listbox_png.bind('<Double-1>', self.on_double_click_spritesheet)
                self.listbox_data.bind('<Double-1>', self.on_double_click_animation)
        return directory

    def select_files_manually(self, variable, label):
        data_files = filedialog.askopenfilenames(filetypes=[("XML and TXT files", "*.xml *.txt")])
        png_files = filedialog.askopenfilenames(filetypes=[("PNG files", "*.png")])
        variable.set(self.temp_dir)
        label.config(text=self.temp_dir)
        if data_files and png_files:
            for file in data_files:
                shutil.copy(file, self.temp_dir)
                png_filename = os.path.splitext(os.path.basename(file))[0] + '.png'
                if any(png_filename == os.path.basename(png) for png in png_files):
                    if png_filename not in [self.listbox_png.get(idx) for idx in range(self.listbox_png.size())]:
                        self.listbox_png.insert(tk.END, png_filename)
                        self.data_dict[png_filename] = os.path.basename(file)
            for file in png_files:
                shutil.copy(file, self.temp_dir)
            self.listbox_png.unbind('<<ListboxSelect>>')
            self.listbox_data.unbind('<Double-1>')
            self.listbox_png.bind('<<ListboxSelect>>', self.on_select_spritesheet)
            self.listbox_data.bind('<Double-1>', self.on_double_click_animation)
        return self.temp_dir

    def create_settings_window(self):
        SettingsWindow(self.root, self.settings_manager)

    def create_find_and_replace_window(self):
        FindReplaceWindow(self.root, self.replace_rules, self.store_replace_rules)

    def store_replace_rules(self, rules):
        self.replace_rules = rules

    def create_override_settings_window(self, window, name, settings_type):
        self.update_global_settings()
        OverrideSettingsWindow(window, name, settings_type, self.settings_manager, self.store_input, app=self)

    def on_select_spritesheet(self, evt):
        self.listbox_data.delete(0, tk.END)

        png_filename = self.listbox_png.get(self.listbox_png.curselection())
        base_filename = os.path.splitext(png_filename)[0]
        xml_filename = base_filename + '.xml'
        txt_filename = base_filename + '.txt'

        directory = self.input_dir.get()

        if os.path.isfile(os.path.join(directory, xml_filename)):
            xml_parser = XmlParser(directory, xml_filename, self.listbox_data)
            xml_parser.get_data()
        elif os.path.isfile(os.path.join(directory, txt_filename)):
            txt_parser = TxtParser(directory, txt_filename, self.listbox_data)
            txt_parser.get_data()

    def on_double_click_spritesheet(self, evt):
        spritesheet_name = self.listbox_png.get(self.listbox_png.curselection())
        new_window = tk.Toplevel()
        new_window.geometry("360x360")
        self.create_override_settings_window(new_window, spritesheet_name, "spritesheet")

    def on_double_click_animation(self, evt):
        spritesheet_name = self.listbox_png.get(self.listbox_png.curselection())
        animation_name = self.listbox_data.get(self.listbox_data.curselection())
        full_anim_name = spritesheet_name + '/' + animation_name
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
            #print(f"Removed: {spritesheet_name}")

            prefix = spritesheet_name + "/"
            anims_to_delete = [key for key in self.settings_manager.animation_settings if key.startswith(prefix)]
            for anim in anims_to_delete:
                self.settings_manager.delete_animation_settings(anim)

    def preview_gif_window(self, name, settings_type, fps_entry, delay_entry, period_entry, scale_entry, threshold_entry, indices_entry, frames_entry):
        GifPreviewWindow.preview(
            self, name, settings_type, fps_entry, delay_entry, period_entry, scale_entry, threshold_entry, indices_entry, frames_entry
        )

    def show_gif_preview_window(self, gif_path, settings):
        GifPreviewWindow.show(gif_path, settings)

    def store_input(self, window, name, settings_type, fps_entry, delay_entry, period_entry, scale_entry, threshold_entry, indices_entry, frames_entry, filename_entry):
        settings = {}
        try:
            if fps_entry.get() != '':
                settings['fps'] = float(fps_entry.get())
            if delay_entry.get() != '':
                settings['delay'] = int(float(delay_entry.get()))
            if period_entry.get() != '':
                settings['period'] = int(float(period_entry.get()))
            if scale_entry.get() != '':
                if float(scale_entry.get()) == 0:
                    raise ValueError
                settings['scale'] = float(scale_entry.get())
            if threshold_entry.get() != '':
                settings['threshold'] = min(max(float(threshold_entry.get()), 0), 1)
            if indices_entry.get() != '':
                indices = [int(ele) for ele in indices_entry.get().split(',')]
                settings['indices'] = indices
            if frames_entry.get() != '':
                settings['frames'] = frames_entry.get()
            if filename_entry and filename_entry.get() != '':
                settings['filename'] = filename_entry.get()
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
        self.settings_manager.set_global_settings(
            animation_format=self.animation_format.get(),
            fps=self.set_framerate.get(),
            delay=self.set_loopdelay.get(),
            period=self.set_minperiod.get(),
            scale=self.set_scale.get(),
            threshold=self.set_threshold.get(),
            frames=self.keep_frames.get(),
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
        
    def start_process(self):
        self.update_global_settings()

        if any(char in self.settings_manager.global_settings["prefix"] for char in r'\/:*?"<>|'):
            messagebox.showerror("Invalid Prefix", "The prefix contains invalid characters.")
            return

        process_thread = threading.Thread(target=self.run_extractor)
        process_thread.start()

    def run_extractor(self):
        spritesheet_list = [self.listbox_png.get(i) for i in range(self.listbox_png.size())]

        extractor = Extractor(self.progress_bar, self.current_version, self.settings_manager, app_config=self.app_config)
        extractor.process_directory(
            self.input_dir.get(),
            self.output_dir.get(),
            self.progress_var,
            self.root,
            spritesheet_list=spritesheet_list
        )

if __name__ == "__main__":
    root = tk.Tk()
    app = TextureAtlasExtractorApp(root)
    root.mainloop()
