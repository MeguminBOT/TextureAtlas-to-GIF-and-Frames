import os
import shutil
import tempfile
import threading
import tkinter as tk
import webbrowser
from tkinter import filedialog, ttk, messagebox

# Import our own modules
from dependencies_checker import DependenciesChecker
from update_checker import UpdateChecker
from settings_manager import SettingsManager
from fnf_utilities import FnfUtilities
from xml_parser import XmlParser 
from txt_parser import TxtParser
from extractor import Extractor
from help_window import HelpWindow

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
        on_select_spritesheet(evt): Handles the event when a PNG file is selected from the listbox.
        on_double_click_spritesheet(evt): Handles the event when a PNG file is double-clicked in the listbox.
        on_double_click_animation(evt): Handles the event when an XML file is double-clicked in the listbox.
        create_override_settings_window(window, name, settings_type): Creates a window to edit animation or spritesheet settings.
        store_input(window, name, settings_type, fps_entry, delay_entry, period_entry, scale_entry, threshold_entry, indices_entry, frames_entry): Stores the input from the override settings window.
        on_closing(): Handles the event when the application is closing.
        start_process(): Prepares and starts the processing thread.
        run_extractor(): Starts the process of extracting textures and converting them to GIF and WebP formats.
    """

    def __init__(self, root):
        self.root = root
        self.settings_manager = SettingsManager()
        self.data_dict = {}
        self.temp_dir = tempfile.mkdtemp()
        self.fnf_char_json_directory = ""
        self.current_version = '1.9.3'
        self.replace_rules = []
        self.fnf_utilities = FnfUtilities()

        self.setup_gui()
        self.check_version()
        self.check_dependencies()

    def setup_gui(self):
        self.root.title("TextureAtlas to GIF and Frames")
        self.root.geometry("900x680")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)

        self.setup_menus()
        self.setup_widgets()

    def setup_menus(self):
        file_menu = tk.Menu(self.menubar, tearoff=0)
        file_menu.add_command(label="Select directory", command=lambda: self.select_directory(self.input_dir, self.input_dir_label) and self.user_settings.clear())
        file_menu.add_command(label="Select files", command=lambda: self.select_files_manually(self.input_dir, self.input_dir_label))
        file_menu.add_command(label="Clear filelist and user settings", command=self.clear_filelist)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        self.menubar.add_cascade(label="File", menu=file_menu)

        import_menu = tk.Menu(self.menubar, tearoff=0)
        import_menu.add_command(label="FNF: Import FPS from character json", command=lambda: self.fnf_utilities.fnf_select_char_json_directory(self.user_settings, self.data_dict, self.listbox_png, self.listbox_data))
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

        self.create_gif = tk.BooleanVar()
        self.gif_checkbox = tk.Checkbutton(self.root, text="Create GIFs for each animation", variable=self.create_gif)
        self.gif_checkbox.pack()

        self.create_webp = tk.BooleanVar()
        self.webp_checkbox = tk.Checkbutton(self.root, text="Create WebPs for each animation", variable=self.create_webp)
        self.webp_checkbox.pack()

        self.set_framerate = tk.DoubleVar(value=24)
        self.frame_rate_label = tk.Label(self.root, text="Frame Rate (fps):")
        self.frame_rate_label.pack()
        self.frame_rate_entry = tk.Entry(self.root, textvariable=self.set_framerate)
        self.frame_rate_entry.pack()

        self.set_loopdelay = tk.DoubleVar(value=250)
        self.loopdelay_label = tk.Label(self.root, text="Loop Delay (ms):")
        self.loopdelay_label.pack()
        self.loopdelay_entry = tk.Entry(self.root, textvariable=self.set_loopdelay)
        self.loopdelay_entry.pack()

        self.set_minperiod = tk.DoubleVar(value=0)
        self.minperiod_label = tk.Label(self.root, text="Minimum Period (ms):")
        self.minperiod_label.pack()
        self.minperiod_entry = tk.Entry(self.root, textvariable=self.set_minperiod)
        self.minperiod_entry.pack()

        self.set_scale = tk.DoubleVar(value=1)
        self.scale_label = tk.Label(self.root, text="Scale:")
        self.scale_label.pack()
        self.scale_entry = tk.Entry(self.root, textvariable=self.set_scale)
        self.scale_entry.pack()

        self.set_threshold = tk.DoubleVar(value=0.5)
        self.threshold_label = tk.Label(self.root, text="Alpha Threshold:")
        self.threshold_label.pack()
        self.threshold_entry = tk.Entry(self.root, textvariable=self.set_threshold)
        self.threshold_entry.pack()

        self.keep_frames = tk.StringVar(value='all')
        self.keepframes_label = tk.Label(self.root, text="Keep individual frames:")
        self.keepframes_label.pack()
        self.keepframes_menu = ttk.Combobox(self.root, textvariable=self.keep_frames)
        self.keepframes_menu['values'] = ("all", "none", "first", "last", "first, last")
        self.keepframes_menu.pack(pady=2)

        self.crop_option = tk.StringVar(value="Animation based")
        self.crop_label = tk.Label(self.root, text="PNG Cropping Method")
        self.crop_label.pack()
        self.crop_menu = tk.OptionMenu(self.root, self.crop_option, "None", "Frame based", "Animation based")
        self.crop_menu.pack(pady=1)

        self.prefix_label = tk.Label(self.root, text="Filename prefix:")
        self.prefix_label.pack()
        self.prefix = tk.StringVar(value="")
        self.prefix_entry = tk.Entry(self.root, textvariable=self.prefix)
        self.prefix_entry.pack()
        
        self.filename_format = tk.StringVar(value="Standardized")
        self.filename_format_label = tk.Label(self.root, text="Filename Format:")
        self.filename_format_label.pack()
        self.filename_format_menu = ttk.Combobox(self.root, textvariable=self.filename_format)
        self.filename_format_menu['values'] = ("Standardized", "No Spaces", "No Special Characters")
        self.filename_format_menu.pack(pady=1)
        # "Standardized" example: "GodsentGaslit - Catnap - Idle"
        # "No Spaces" example: "GodsentGaslit-Catnap-Idle"
        # "No Special Characters" example: "GodsentGaslitCatnapIdle"

        self.replace_button = tk.Button(self.root, text="Find and replace", cursor="hand2", command=lambda: self.create_find_and_replace_window())
        self.replace_button.pack(pady=2)
        
        self.button_frame = tk.Frame(self.root)
        self.button_frame.pack(pady=8)

        self.show_user_settings = tk.Button(self.button_frame, text="Show User Settings", command=self.create_settings_window)
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
        self.settings_window = tk.Toplevel()
        self.settings_window.geometry("400x300")
        settings_canvas = tk.Canvas(self.settings_window)
        settings_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        settings_scrollbar = tk.Scrollbar(self.settings_window, orient=tk.VERTICAL, command=settings_canvas.yview)
        settings_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        settings_canvas.config(yscrollcommand=settings_scrollbar.set)
        settings_frame = tk.Frame(settings_canvas)
        settings_canvas.create_window((0, 0), window=settings_frame, anchor=tk.NW)
        self.update_settings_window(settings_frame, settings_canvas)
        settings_frame.update_idletasks()
        settings_canvas.config(scrollregion=settings_canvas.bbox("all"))

    def update_settings_window(self, settings_frame, settings_canvas):
        for widget in settings_frame.winfo_children():
            widget.destroy()

        tk.Label(settings_frame, text="Animation Settings").pack(pady=10)
        for key, value in self.settings_manager.animation_settings.items():
            tk.Label(settings_frame, text=f"{key}: {value}").pack(anchor=tk.W, padx=20)

        tk.Label(settings_frame, text="Spritesheet Settings").pack(pady=10)
        for key, value in self.settings_manager.spritesheet_settings.items():
            tk.Label(settings_frame, text=f"{key}: {value}").pack(anchor=tk.W, padx=20)

        settings_frame.update_idletasks()
        settings_canvas.config(scrollregion=settings_canvas.bbox("all"))
        
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
        new_window.geometry("360x360")
        self.create_override_settings_window(new_window, full_anim_name, "animation")

    def create_override_settings_window(self, window, name, settings_type):
        settings_map = {
            "animation": self.settings_manager.animation_settings,
            "spritesheet": self.settings_manager.spritesheet_settings,
        }
        settings = settings_map.get(settings_type, {}).get(name, {})

    def create_find_and_replace_window(self):
        self.replace_window = tk.Toplevel()
        print(self.replace_rules)
        tk.Label(self.replace_window, text="Find and replace").pack()
        add_button = tk.Button(self.replace_window, text='Add rule', command=lambda: self.add_replace_rule({"find":"","replace":"","regex":False}))
        add_button.pack()
        self.rules_frame = tk.Frame(self.replace_window)
        for rule in self.replace_rules:
            self.add_replace_rule(rule)
        self.rules_frame.pack()
        ok_button = tk.Button(self.replace_window, text='OK', command=lambda: self.store_replace_rules())
        ok_button.pack()

    def add_replace_rule(self, rule):
        frame = tk.Frame(self.rules_frame)
        frame['borderwidth'] = 2
        frame['relief'] = 'sunken'
        find_entry = tk.Entry(frame)
        find_entry.insert(0, rule["find"])
        find_entry.pack()
        replace_entry = tk.Entry(frame)
        replace_entry.insert(0, rule["replace"])
        replace_entry.pack()
        regex_checkbox = ttk.Checkbutton(frame, text="Regular expression")
        regex_checkbox.pack()
        delete_rule_button = tk.Button(frame, text="Delete", command=lambda: frame.destroy())
        delete_rule_button.pack()
        regex_checkbox.invoke()
        if not rule["regex"]:
            regex_checkbox.invoke()
        frame.pack(pady=2)
        self.rules_frame.update()
        return frame

    def store_replace_rules(self):
        self.replace_rules = []
        for rule in self.rules_frame.winfo_children():
            rule_settings = rule.winfo_children()
            self.replace_rules.append({"find":rule_settings[0].get(),"replace":rule_settings[1].get(),"regex": "selected" in rule_settings[2].state()})
        self.replace_window.destroy()

    def create_animation_settings_window(self, window, name, settings_dict):
        tk.Label(window, text="FPS for " + name).pack()
        fps_entry = tk.Entry(window)
        if settings:
            fps_entry.insert(0, str(settings.get('fps', '')))
        fps_entry.pack()

        tk.Label(window, text="Delay for " + name).pack()
        delay_entry = tk.Entry(window)
        if settings:
            delay_entry.insert(0, str(settings.get('delay', '')))
        delay_entry.pack()

        tk.Label(window, text="Min period for " + name).pack()
        period_entry = tk.Entry(window)
        if settings:
            period_entry.insert(0, str(settings.get('period', '')))
        period_entry.pack()

        tk.Label(window, text="Scale for " + name).pack()
        scale_entry = tk.Entry(window)
        if settings:
            scale_entry.insert(0, str(settings.get('scale', '')))
        scale_entry.pack()

        tk.Label(window, text="Threshold for " + name).pack()
        threshold_entry = tk.Entry(window)
        if settings:
            threshold_entry.insert(0, str(settings.get('threshold', '')))
        threshold_entry.pack()

        tk.Label(window, text="Indices for " + name).pack()
        indices_entry = tk.Entry(window)
        if settings:
            indices_entry.insert(0, str(settings.get('indices', '')).translate(str.maketrans('', '', '[] ')))
        indices_entry.pack()

        tk.Label(window, text="Keep frames for " + name).pack()
        frames_entry = tk.Entry(window)
        if settings:
            frames_entry.insert(0, str(settings.get('frames', '')))
        frames_entry.pack()

        tk.Button(window, text="OK", command=lambda: self.store_input(
            window, name, settings_type, fps_entry, delay_entry, period_entry, scale_entry, threshold_entry, indices_entry, frames_entry
        )).pack()

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
        
    def on_closing(self):
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        self.root.destroy()
        
    def start_process(self):
        self.settings_manager.set_global_settings(
            create_gif=self.create_gif.get(),
            create_webp=self.create_webp.get(),
            framerate=self.set_framerate.get(),
            loop_delay=self.set_loopdelay.get(),
            min_period=self.set_minperiod.get(),
            scale=self.set_scale.get(),
            threshold=self.set_threshold.get(),
            keep_frames=self.keep_frames.get(),
            crop_option=self.crop_option.get(),
            prefix=self.prefix.get(),
            filename_format=self.filename_format.get(),
            variable_delay=self.variable_delay.get(),
            replace_rules=self.replace_rules,
            fnf_idle_loop=self.fnf_idle_loop.get()
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
            self.root
        )

if __name__ == "__main__":
    root = tk.Tk()
    app = TextureAtlasExtractorApp(root)
    root.mainloop()
