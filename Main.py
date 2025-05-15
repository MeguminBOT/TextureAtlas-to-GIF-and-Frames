import os
import shutil
import tempfile
import threading
import tkinter as tk
import webbrowser
from tkinter import filedialog, ttk, messagebox
import xml.etree.ElementTree as ET

# Import our own modules
from utils.dependencies_checker import DependenciesChecker
DependenciesChecker.check_and_configure_imagemagick()
from utils.update_checker import UpdateChecker
from utils.settings_manager import SettingsManager
from utils.fnf_utilities import FnfUtilities
from parsers.xml_parser import XmlParser 
from parsers.txt_parser import TxtParser
from core.extractor import Extractor
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
        settings_manager (SettingsManager): Manages global, animation-specific, and spritesheet-specific settings.
        data_dict (dict): A dictionary to store data related to the spritesheets.
        temp_dir (str): A temporary directory for storing files.
        fnf_char_json_directory (str): Directory for FNF character JSON files.
        current_version (str): The current version of the application.
        fnf_utilities (FnfUtilities): An instance of FnfUtilities for FNF-related utilities.
        progress_var (tk.DoubleVar): A variable to track progress for the progress bar.
        variable_delay (tk.BooleanVar): A flag to enable or disable variable delay between frames.
        use_all_threads (tk.BooleanVar): A flag to enable or disable the use of all CPU threads.
        fnf_idle_loop (tk.BooleanVar): A flag to set loop delay to 0 for idle animations in FNF.

    Methods:
        setup_gui(): Sets up the GUI components of the application.
        setup_menus(): Sets up the menu bar and its items.
        setup_widgets(): Sets up the widgets in the main window.
        contributeLink(linkSourceCode): Opens the source code link in a web browser.
        check_version(): Checks for updates to the application.
        check_dependencies(): Checks and configures dependencies.
        clear_filelist(): Clears the file list and resets animation and spritesheet settings.
        select_directory(variable, label): Opens a directory selection dialog and updates the label.
        select_files_manually(variable, label): Opens a file selection dialog and updates the label.
        create_settings_window(): Creates a window to display animation and spritesheet settings.
        update_settings_window(settings_frame, settings_canvas): Updates the settings window with current settings.
        on_select_tree(evt): Handles the event when an item is selected in the Treeview.
        on_double_click_tree(evt): Handles the event when an item is double-clicked in the Treeview.
        create_find_and_replace_window(): Creates the Find and Replace window.
        add_replace_rule(): Adds a replace rule to the Find and Replace window.
        store_replace_rules(): Stores the replace rules from the Find and Replace window.
        create_override_settings_window(window, name, settings_type): Creates a window to edit animation or spritesheet settings.
        store_input(window, name, settings_type, fps_entry, delay_entry, period_entry, scale_entry, threshold_entry, indices_entry, frames_entry): Stores the input from the override settings window.
        preview_gif_window(name, settings_type, fps_entry, delay_entry, period_entry, scale_entry, threshold_entry, indices_entry, frames_entry): Generates and displays a preview GIF.
        show_gif_preview_window(gif_path, settings): Displays the preview GIF in a new window.
        on_closing(): Handles the event when the application is closing.
        start_process(): Prepares and starts the processing thread.
        run_extractor(): Starts the process of extracting textures and converting them to GIF and WebP formats.
    """

    def __init__(self, root):
        self.root = root
        self.current_version = '1.9.3'
        self.settings_manager = SettingsManager()
        self.temp_dir = tempfile.mkdtemp()
        self.data_dict = {}

        self.fnf_utilities = FnfUtilities()
        self.fnf_char_json_directory = ""

        self.setup_gui()
        self.check_version()

    def setup_gui(self):
        self.root.title("TextureAtlas to GIF and Frames")
        self.root.geometry("900x720")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)

        self.setup_menus()
        self.setup_widgets()

    def setup_menus(self):
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
        import_menu.add_command(label="FNF: Import settings from character data file", command=lambda: self.fnf_utilities.fnf_select_char_data_directory(self.settings_manager, self.data_dict, self.tree, None) or self.add_settings_to_tree())
        self.menubar.add_cascade(label="Import", menu=import_menu)

        help_menu = tk.Menu(self.menubar, tearoff=0)
        help_menu.add_command(label="Manual", command=HelpWindow.create_main_help_window)
        help_menu.add_separator()
        help_menu.add_command(label="FNF: GIF/WebP settings advice", command=HelpWindow.create_fnf_help_window)
        self.menubar.add_cascade(label="Help", menu=help_menu)

        advanced_menu = tk.Menu(self.menubar, tearoff=0)
        self.variable_delay = tk.BooleanVar()
        self.use_all_threads = tk.BooleanVar()
        self.fnf_idle_loop = tk.BooleanVar()
        advanced_menu.add_checkbutton(label="Variable delay", variable=self.variable_delay)
        advanced_menu.add_checkbutton(label="Use all CPU threads", variable=self.use_all_threads)
        advanced_menu.add_checkbutton(label="FNF: Set loop delay on idle animations to 0", variable=self.fnf_idle_loop)
        self.menubar.add_cascade(label="Advanced", menu=advanced_menu)

    def setup_widgets(self):
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.root, length=865, variable=self.progress_var)
        self.progress_bar.pack(pady=8)

        self.tree = ttk.Treeview(self.root, columns=("Type",), show="tree headings", height=25)
        self.tree.heading("#0", text="Spritesheet/Animation")
        self.tree.heading("Type", text="Type")
        self.tree.column("#0", width=300, anchor="w")
        self.tree.column("Type", width=100, anchor="w")
        self.tree.pack(side=tk.LEFT, fill=tk.Y)
        self.tree.bind('<<TreeviewSelect>>', self.on_select_tree)
        self.tree.bind('<Double-1>', self.on_double_click_tree)

        self.input_dir = tk.StringVar()
        self.input_button = tk.Button(self.root, text="Select directory with spritesheets", cursor="hand2",
            command=lambda: self.select_directory(self.input_dir, self.input_dir_label) 
            and self.settings_manager.animation_settings.clear()
            and self.settings_manager.spritesheet_settings.clear()
        )
        self.input_button.pack(pady=2)

        self.input_dir_label = tk.Label(self.root, text="No input directory selected")
        self.input_dir_label.pack(pady=4)

        self.output_dir = tk.StringVar()
        self.output_button = tk.Button(self.root, text="Select save directory", cursor="hand2", command=lambda: self.select_directory(self.output_dir, self.output_dir_label))
        self.output_button.pack(pady=2)

        self.output_dir_label = tk.Label(self.root, text="No output directory selected")
        self.output_dir_label.pack(pady=4)
        
        ttk.Separator(self.root, orient="horizontal").pack(fill="x", pady=2)

        self.animation_format = tk.StringVar(value="None")
        self.animation_format_label = tk.Label(self.root, text="Animation format:")
        self.animation_format_label.pack()
        self.animation_format_combobox = ttk.Combobox(
            self.root,
            textvariable=self.animation_format,
            values=["None", "GIF", "WebP", "APNG"],
            state="readonly"
        )
        self.animation_format_combobox.pack()

        self.set_framerate = tk.DoubleVar(value=24)
        self.frame_rate_label = tk.Label(self.root, text="Frame rate (fps):")
        self.frame_rate_label.pack()
        self.frame_rate_entry = tk.Entry(self.root, textvariable=self.set_framerate)
        self.frame_rate_entry.pack()

        self.set_loopdelay = tk.DoubleVar(value=250)
        self.loopdelay_label = tk.Label(self.root, text="Loop delay (ms):")
        self.loopdelay_label.pack()
        self.loopdelay_entry = tk.Entry(self.root, textvariable=self.set_loopdelay)
        self.loopdelay_entry.pack()

        self.set_minperiod = tk.DoubleVar(value=0)
        self.minperiod_label = tk.Label(self.root, text="Minimum period (ms):")
        self.minperiod_label.pack()
        self.minperiod_entry = tk.Entry(self.root, textvariable=self.set_minperiod)
        self.minperiod_entry.pack()

        self.set_scale = tk.DoubleVar(value=1)
        self.scale_label = tk.Label(self.root, text="Scale:")
        self.scale_label.pack()
        self.scale_entry = tk.Entry(self.root, textvariable=self.set_scale)
        self.scale_entry.pack()

        self.set_threshold = tk.DoubleVar(value=0.5)
        self.threshold_label = tk.Label(self.root, text="Alpha threshold:")
        self.threshold_label.pack()
        self.threshold_entry = tk.Entry(self.root, textvariable=self.set_threshold)
        self.threshold_entry.pack(pady=8)
        
        ttk.Separator(self.root, orient="horizontal").pack(fill="x", pady=2)

        self.keep_frames = tk.StringVar(value='All')
        self.keepframes_label = tk.Label(self.root, text="Keep individual frames:")
        self.keepframes_label.pack()
        self.keepframes_menu = ttk.Combobox(self.root, textvariable=self.keep_frames)
        self.keepframes_menu['values'] = ("None", "All", "No duplicates", "First", "Last", "First, Last")
        self.keepframes_menu.pack(pady=2)

        self.crop_option = tk.StringVar(value="Animation based")
        self.crop_menu_label = tk.Label(self.root, text="Cropping method:")
        self.crop_menu_label.pack()
        self.crop_menu_menu = ttk.Combobox(self.root, textvariable=self.crop_option, state="readonly")
        self.crop_menu_menu['values'] = ("None", "Animation based", "Frame based")
        self.crop_menu_menu.pack(pady=1)

        self.prefix_label = tk.Label(self.root, text="Filename prefix:")
        self.prefix_label.pack()
        self.prefix = tk.StringVar(value="")
        self.prefix_entry = tk.Entry(self.root, textvariable=self.prefix)
        self.prefix_entry.pack()
        
        self.filename_format = tk.StringVar(value="Standardized")
        self.filename_format_label = tk.Label(self.root, text="Filename format:")
        self.filename_format_label.pack()
        self.filename_format_menu = ttk.Combobox(self.root, textvariable=self.filename_format)
        self.filename_format_menu['values'] = ("Standardized", "No spaces", "No special characters")
        self.filename_format_menu.pack(pady=1)
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

    def clear_filelist(self):
        self.tree.delete(*self.tree.get_children())
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
                        png_name = os.path.splitext(filename)[0] + '.png'
                        parent_id = self.tree.insert('', 'end', text=png_name, values=("Spritesheet",))
                        xml_filename = os.path.splitext(png_name)[0] + '.xml'
                        txt_filename = os.path.splitext(png_name)[0] + '.txt'
                        
                        if os.path.isfile(os.path.join(directory, xml_filename)):
                            xml_parser = XmlParser(directory, xml_filename, self.tree)
                            for anim in xml_parser.extract_names(ET.parse(os.path.join(directory, xml_filename)).getroot()):
                                self.tree.insert(parent_id, 'end', text=anim, values=("Animation",))
                        elif os.path.isfile(os.path.join(directory, txt_filename)):
                            txt_parser = TxtParser(directory, txt_filename, self.tree)
                            for anim in txt_parser.extract_names():
                                self.tree.insert(parent_id, 'end', text=anim, values=("Animation",))
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
                    if not any(self.tree.item(child)['text'] == png_filename for child in self.tree.get_children()):
                        parent_id = self.tree.insert('', 'end', text=png_filename, values=("Spritesheet",))
                        self.data_dict[png_filename] = os.path.basename(file)
                        ext = os.path.splitext(file)[1]
                        
                        if ext == '.xml':
                            xml_parser = XmlParser(self.temp_dir, os.path.basename(file), self.tree)
                            for anim in xml_parser.extract_names(ET.parse(file).getroot()):
                                self.tree.insert(parent_id, 'end', text=anim, values=("Animation",))
                        elif ext == '.txt':
                            txt_parser = TxtParser(self.temp_dir, os.path.basename(file), self.tree)
                            for anim in txt_parser.extract_names():
                                self.tree.insert(parent_id, 'end', text=anim, values=("Animation",))
            for file in png_files:
                shutil.copy(file, self.temp_dir)
        return self.temp_dir

    def create_settings_window(self):
        SettingsWindow(self.root, self.settings_manager)

    def create_find_and_replace_window(self):
        FindReplaceWindow(self.root, self.replace_rules, self.store_replace_rules)

    def store_replace_rules(self, rules):
        self.replace_rules = rules

    def create_override_settings_window(self, window, name, settings_type):
        OverrideSettingsWindow(window, name, settings_type, self.settings_manager, self.store_input, app=self)

    def on_select_tree(self, evt):
        pass

    def on_double_click_tree(self, evt):
        selected = self.tree.selection()
        if not selected:
            return

        item_id = selected[0]
        parent_id = self.tree.parent(item_id)
    
        if parent_id == '':
            spritesheet_name = self.tree.item(item_id)['text']
            new_window = tk.Toplevel()
            new_window.geometry("360x360")
            self.create_override_settings_window(new_window, spritesheet_name, "spritesheet")
        else:
            spritesheet_name = self.tree.item(parent_id)['text']
            animation_name = self.tree.item(item_id)['text']
            full_anim_name = spritesheet_name + '/' + animation_name
            new_window = tk.Toplevel()
            new_window.geometry("360x360")
            self.create_override_settings_window(new_window, full_anim_name, "animation")

    def preview_gif_window(self, name, settings_type, fps_entry, delay_entry, period_entry, scale_entry, threshold_entry, indices_entry, frames_entry):
        GifPreviewWindow.preview(
            self, name, settings_type, fps_entry, delay_entry, period_entry, scale_entry, threshold_entry, indices_entry, frames_entry
        )

    def show_gif_preview_window(self, gif_path, settings):
        GifPreviewWindow.show(gif_path, settings)

    def store_input(self, window, name, settings_type, fps_entry, delay_entry, period_entry, scale_entry, threshold_entry, indices_entry, frames_entry):
        settings = {}
        try:
            if fps_entry.get() != '':
                settings['fps'] = float(fps_entry.get())
            if delay_entry.get() != '':
                settings['delay'] = int(delay_entry.get())
            if period_entry.get() != '':
                settings['period'] = int(period_entry.get())
            if scale_entry.get() != '':
                if float(scale_entry.get()) == 0:
                    raise ValueError
                settings['scale'] = float(scale_entry.get())
            if threshold_entry.get() != '':
                settings['threshold'] = min(max(float(threshold_entry.get()), 0), 1)
            print("indices_entry.get(): "+indices_entry.get())
            if indices_entry.get() != '':
                indices = [int(ele) for ele in indices_entry.get().split(',')]
                settings['indices'] = indices
            if frames_entry.get() != '':
                settings['frames'] = frames_entry.get().lower()
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
        self.add_settings_to_tree()
        
    def on_closing(self):
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        self.root.destroy()
        
    def start_process(self):
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

        if any(char in self.settings_manager.global_settings["prefix"] for char in r'\/:*?"<>|'):
            messagebox.showerror("Invalid Prefix", "The prefix contains invalid characters.")
            return

        process_thread = threading.Thread(target=self.run_extractor)
        process_thread.start()

    def run_extractor(self):
        extractor = Extractor(self.progress_bar, self.current_version, self.settings_manager)
        extractor.process_directory(
            self.input_dir.get(),
            self.output_dir.get(),
            self.progress_var,
            self.root,
        )

    def add_settings_to_tree(self):
        # Nesting, nesting, nesting, nesting, i'm crying, will fix this later.
        for spritesheet_item in self.tree.get_children():
            for anim_item in self.tree.get_children(spritesheet_item):
                for setting_item in self.tree.get_children(anim_item):
                    self.tree.delete(setting_item)

            for setting_item in self.tree.get_children(spritesheet_item):
                if self.tree.item(setting_item)['text'].startswith('['):
                    self.tree.delete(setting_item)

        for spritesheet, settings in self.settings_manager.spritesheet_settings.items():
            for item in self.tree.get_children():
                if self.tree.item(item)['text'] == spritesheet:
                    for key, value in settings.items():
                        self.tree.insert(item, 'end', text=f"[{key}]", values=(str(value),))

        for anim_full, settings in self.settings_manager.animation_settings.items():
            if '/' in anim_full:
                spritesheet, animation = anim_full.split('/', 1)
                for item in self.tree.get_children():
                    if self.tree.item(item)['text'] == spritesheet:
                        for child in self.tree.get_children(item):
                            if self.tree.item(child)['text'] == animation:
                                for key, value in settings.items():
                                    self.tree.insert(child, 'end', text=f"[{key}]", values=(str(value),))

if __name__ == "__main__":
    root = tk.Tk()
    app = TextureAtlasExtractorApp(root)
    root.mainloop()
