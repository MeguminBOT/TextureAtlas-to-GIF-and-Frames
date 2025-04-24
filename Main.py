import os
import shutil
import re
import tempfile
import threading
import tkinter as tk
import webbrowser
from tkinter import filedialog, ttk, messagebox

# Import our own modules
from dependencies_checker import DependenciesChecker
from update_checker import UpdateChecker
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
        user_settings (dict): A dictionary to store user settings.
        spritesheet_settings (dict): A dictionary to store spritesheet settings.
        data_dict (dict): A dictionary to store data related to the spritesheets.
        temp_dir (str): A temporary directory for storing files.
        fnf_char_json_directory (str): Directory for FNF character JSON files.
        current_version (str): The current version of the application.
        quant_frames (dict): A dictionary to store quantized frames.
        fnf_utilities (FnfUtilities): An instance of FnfUtilities for FNF-related utilities.
    Methods:
        setup_gui(): Sets up the GUI components of the application.
        setup_menus(): Sets up the menu bar and its items.
        setup_widgets(): Sets up the widgets in the main window.
        contributeLink(linkSourceCode): Opens the source code link in a web browser.
        check_version(): Checks for updates to the application.
        check_dependencies(): Checks and configures dependencies.
        clear_filelist(): Clears the file list and user settings.
        select_directory(variable, label): Opens a directory selection dialog and updates the label.
        select_files_manually(variable, label): Opens a file selection dialog and updates the label.
        create_settings_window(): Creates a window to display user and spritesheet settings.
        update_settings_window(settings_frame, settings_canvas): Updates the settings window with current settings.
        on_select_png(evt): Handles the event when a PNG file is selected from the listbox.
        on_double_click_png(evt): Handles the event when a PNG file is double-clicked in the listbox.
        on_double_click_xml(evt): Handles the event when an XML file is double-clicked in the listbox.
        create_animation_settings_window(window, name, settings_dict): Creates a window to edit animation settings.
        store_input(window, name, settings_dict, fps_entry, delay_entry, period_entry, scale_entry, threshold_entry, indices_entry, frames_entry): Stores the input from the animation settings window.
        on_closing(): Handles the event when the application is closing.
        start_process(): Starts the process of extracting textures and converting them to GIF and WebP formats.
    """

    def __init__(self, root):
        self.root = root
        self.user_settings = {}
        self.spritesheet_settings = {}
        self.data_dict = {}
        self.temp_dir = tempfile.mkdtemp()
        self.fnf_char_json_directory = ""
        self.current_version = '1.9.3'
        self.quant_frames = {}
        self.fnf_utilities = FnfUtilities()

        self.setup_gui()
        self.check_version()
        self.check_dependencies()

    def setup_gui(self):
        self.root.title("TextureAtlas to GIF and Frames")
        self.root.geometry("900x640")
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
        self.input_button = tk.Button(self.root, text="Select directory with spritesheets", cursor="hand2", command=lambda: self.select_directory(self.input_dir, self.input_dir_label) and self.user_settings.clear())
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
        self.keepframes_entry = tk.Entry(self.root, textvariable=self.keep_frames)
        self.keepframes_entry.pack(pady=2)

        self.crop_option = tk.StringVar(value="Animation based")
        self.crop_label = tk.Label(self.root, text="PNG Cropping Method")
        self.crop_label.pack()
        self.crop_menu = tk.OptionMenu(self.root, self.crop_option, "None", "Frame based", "Animation based")
        self.crop_menu.pack(pady=1)

        self.button_frame = tk.Frame(self.root)
        self.button_frame.pack(pady=8)
        
        self.prefix_label = tk.Label(self.root, text="Filename prefix:")
        self.prefix_label.pack()
        self.prefix = tk.StringVar(value="")
        self.prefix_entry = tk.Entry(self.root, textvariable=self.prefix)
        self.prefix_entry.pack()

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
        self.user_settings.clear()

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
                self.listbox_png.bind('<<ListboxSelect>>', self.on_select_png)
                self.listbox_png.bind('<Double-1>', self.on_double_click_png)
                self.listbox_data.bind('<Double-1>', self.on_double_click_xml)
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
            self.listbox_png.bind('<<ListboxSelect>>', self.on_select_png)
            self.listbox_data.bind('<Double-1>', self.on_double_click_xml)
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
        for key, value in self.user_settings.items():
            tk.Label(settings_frame, text=f"{key}: {value}").pack(anchor=tk.W, padx=20)
        tk.Label(settings_frame, text="Spritesheet Settings").pack(pady=10)
        for key, value in self.spritesheet_settings.items():
            tk.Label(settings_frame, text=f"{key}: {value}").pack(anchor=tk.W, padx=20)
        settings_frame.update_idletasks()
        settings_canvas.config(scrollregion=settings_canvas.bbox("all"))
        
    def on_select_png(self, evt):
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

    def on_double_click_png(self, evt):
        spritesheet_name = self.listbox_png.get(self.listbox_png.curselection())
        new_window = tk.Toplevel()
        new_window.geometry("360x360")
        self.create_animation_settings_window(new_window, spritesheet_name, self.spritesheet_settings)

    def on_double_click_xml(self, evt):
        spritesheet_name = self.listbox_png.get(self.listbox_png.curselection())
        animation_name = self.listbox_data.get(self.listbox_data.curselection())
        full_anim_name = spritesheet_name + '/' + animation_name
        new_window = tk.Toplevel()
        new_window.geometry("360x360")
        self.create_animation_settings_window(new_window, full_anim_name, self.user_settings)

    def create_animation_settings_window(self, window, name, settings_dict):
        tk.Label(window, text="FPS for " + name).pack()
        fps_entry = tk.Entry(window)
        if name in settings_dict:
            fps_entry.insert(0, str(settings_dict[name].get('fps', '')))
        fps_entry.pack()
        
        tk.Label(window, text="Delay for " + name).pack()
        delay_entry = tk.Entry(window)
        if name in settings_dict:
            delay_entry.insert(0, str(settings_dict[name].get('delay', '')))
        delay_entry.pack()
        
        tk.Label(window, text="Min period for " + name).pack()
        period_entry = tk.Entry(window)
        if name in settings_dict:
            period_entry.insert(0, str(settings_dict[name].get('period', '')))
        period_entry.pack()
        
        tk.Label(window, text="Scale for " + name).pack()
        scale_entry = tk.Entry(window)
        if name in settings_dict:
            scale_entry.insert(0, str(settings_dict[name].get('scale', '')))
        scale_entry.pack()
        
        tk.Label(window, text="Threshold for " + name).pack()
        threshold_entry = tk.Entry(window)
        if name in settings_dict:
            threshold_entry.insert(0, str(settings_dict[name].get('threshold', '')))
        threshold_entry.pack()
        
        tk.Label(window, text="Indices for " + name).pack()
        indices_entry = tk.Entry(window)
        if name in settings_dict:
            indices_entry.insert(0, str(settings_dict[name].get('indices', '')).translate(str.maketrans('','','[] ')))
        indices_entry.pack()
        
        tk.Label(window, text="Keep frames for " + name).pack()
        frames_entry = tk.Entry(window)
        if name in settings_dict:
            frames_entry.insert(0, str(settings_dict[name].get('frames', '')))
        frames_entry.pack()
        
        tk.Button(window, text="OK", command=lambda: self.store_input(window, name, settings_dict, fps_entry, delay_entry, period_entry, scale_entry, threshold_entry, indices_entry, frames_entry)).pack()

    def store_input(self, window, name, settings_dict, fps_entry, delay_entry, period_entry, scale_entry, threshold_entry, indices_entry, frames_entry):
        anim_settings = {}
        try:
            if fps_entry.get() != '':
                anim_settings['fps'] = float(fps_entry.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a valid float for FPS.")
            window.lift()
            return
        try:
            if delay_entry.get() != '':
                anim_settings['delay'] = int(delay_entry.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a valid integer for delay.")
            window.lift()
            return
        try:
            if period_entry.get() != '':
                anim_settings['period'] = int(period_entry.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a valid integer for period.")
            window.lift()
            return
        try:
            if scale_entry.get() != '':
                if float(scale_entry.get()) == 0:
                    raise ValueError
                anim_settings['scale'] = float(scale_entry.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a valid float for scale.")
            window.lift()
            return
        try:
            if threshold_entry.get() != '':
                anim_settings['threshold'] = min(max(float(threshold_entry.get()), 0), 1)
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a valid float between 0 and 1 inclusive for threshold.")
            window.lift()
            return
        try:
            if indices_entry.get() != '':
                indices = [int(ele) for ele in indices_entry.get().split(',')]
                anim_settings['indices'] = indices
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a comma-separated list of integers for indices.")
            window.lift()
            return
        try:
            if frames_entry.get() != '':
                if not re.fullmatch(r',|all|first|last|first, ?last|none', frames_entry.get().lower()):
                    keep_frames = [ele for ele in frames_entry.get().split(',')]
                    for entry in keep_frames:
                        if not re.fullmatch(r'-?\d+(--?\d+)?', entry):
                            raise ValueError
                anim_settings['frames'] = frames_entry.get().lower()
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a keyword or a comma-separated list of integers or integer ranges for keep frames.")
            window.lift()
            return
        if len(anim_settings) > 0:
            settings_dict[name] = anim_settings
        elif settings_dict.get(name):
            settings_dict.pop(name)
        window.destroy()
        
    def on_closing(self):
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        self.root.destroy()
        
    def start_process(self):
        process_thread = threading.Thread(target=self.run_extractor)
        process_thread.start()

    def run_extractor(self):
        extractor = Extractor(self.progress_bar, self.current_version, self.spritesheet_settings, self.user_settings)
        prefix = self.prefix.get()
        if any(char in prefix for char in r'\/:*?"<>|'):
            messagebox.showerror("Invalid Prefix", "The prefix contains invalid characters.")
            return

        extractor.process_directory(
            self.input_dir.get(),
            self.output_dir.get(),
            self.progress_var,
            self.root,
            self.create_gif.get(),
            self.create_webp.get(),
            self.set_framerate.get(),
            self.set_loopdelay.get(),
            self.set_minperiod.get(),
            self.set_scale.get(),
            self.set_threshold.get(),
            self.keep_frames.get(),
            self.crop_option.get(),
            self.prefix.get(),
            self.variable_delay.get(),
            self.fnf_idle_loop.get()
        )

if __name__ == "__main__":
    root = tk.Tk()
    app = TextureAtlasExtractorApp(root)
    root.mainloop()
