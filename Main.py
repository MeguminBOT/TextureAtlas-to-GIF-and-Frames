import os
import shutil
import re
import tempfile
import tkinter as tk
import webbrowser
from tkinter import filedialog, ttk, messagebox
from PySide6.QtWidgets import QMessageBox, QFileDialog, QLabel, QVBoxLayout, QWidget, QLineEdit, QListView, QCheckBox, QDoubleSpinBox, QSpinBox, QFrame, QPushButton, QScrollArea, QFormLayout, QDialog
from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItemModel, QStandardItem

# Import our own modules
from dependencies_checker import DependenciesChecker
from update_checker import UpdateChecker
from fnf_utilities import FnfUtilities
from xml_parser import XmlParser 
from txt_parser import TxtParser
from extractor import Extractor
from help_window import HelpWindow
from user_interface import Ui_MainWindow

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
        self.current_version = '1.9.2'
        self.quant_frames = {}
        self.fnf_utilities = FnfUtilities()
        self.qt = Ui_MainWindow()

        self.setup_gui()
        self.check_version()
        self.check_dependencies()

    def setup_gui(self):
        self.root.title("TextureAtlas to GIF and Frames")
        self.root.geometry("900x560")
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
        self.better_colors = tk.BooleanVar()
        self.variable_delay = tk.BooleanVar()
        self.use_all_threads = tk.BooleanVar()
        advanced_menu.add_checkbutton(label="Higher color quality", variable=self.better_colors)
        advanced_menu.add_checkbutton(label="Variable delay", variable=self.variable_delay)
        advanced_menu.add_checkbutton(label="Use all CPU threads", variable=self.use_all_threads)
        self.menubar.add_cascade(label="Advanced", menu=advanced_menu)

    def setup_widgets(self):
        self.progress_bar = self.qt.progressBar
        self.progress_bar.setValue(0)

        self.listbox_png = self.qt.ui_listview_sprites()
        self.listbox_data = self.qt.ui_listview_animations()

        self.input_dir = ""
        self.input_dir_label = self.qt.ui_input_field
        self.input_button = self.qt.ui_button_select_directory
        self.input_button.clicked.connect(lambda: self.select_directory("input") and self.user_settings.clear())

        self.output_dir = ""
        self.output_dir_label = self.qt.ui_output_field
        self.output_button = self.qt.ui_button_save_directory
        self.output_button.clicked.connect(lambda: self.select_directory("output"))
        
        self.listbox_png_model = QStandardItemModel(self.listbox_png)
        self.listbox_png.setModel(self.listbox_png_model)

        self.listbox_data_model = QStandardItemModel(self.listbox_data)
        self.listbox_data.setModel(self.listbox_data_model)

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

        self.crop_pngs = tk.BooleanVar()
        self.crop_pngs_checkbox = tk.Checkbutton(self.root, text="Crop individual frames", variable=self.crop_pngs)
        self.crop_pngs_checkbox.pack(pady=1)

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
        self.listbox_png_model.clear()
        self.listbox_data_model.clear()
        self.user_settings.clear()

    def select_directory(self, dir_type):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            if dir_type == "input":
                self.input_dir = directory
                self.input_dir_label.setText(directory)
                self.clear_filelist()
                for filename in os.listdir(directory):
                    if filename.endswith('.xml') or filename.endswith('.txt'):
                        self.listbox_png_model.appendRow(QStandardItem(os.path.splitext(filename)[0] + '.png'))
                self.listbox_png.selectionModel().selectionChanged.connect(self.on_select_png)
                self.listbox_png.doubleClicked.connect(self.on_double_click_png)
                self.listbox_data.doubleClicked.connect(self.on_double_click_xml)
            elif dir_type == "output":
                self.output_dir = directory
                self.output_dir_label.setText(directory)
        return directory

    def select_files_manually(self, variable, label):
        data_files, _ = QFileDialog.getOpenFileNames(self, "Select XML and TXT files", "", "XML and TXT files (*.xml *.txt)")
        png_files, _ = QFileDialog.getOpenFileNames(self, "Select PNG files", "", "PNG files (*.png)")
        variable = self.temp_dir
        label.setText(self.temp_dir)
        if data_files and png_files:
            for file in data_files:
                shutil.copy(file, self.temp_dir)
                png_filename = os.path.splitext(os.path.basename(file))[0] + '.png'
                if any(png_filename == os.path.basename(png) for png in png_files):
                    if png_filename not in [self.listbox_png_model.item(idx).text() for idx in range(self.listbox_png_model.rowCount())]:
                        self.listbox_png_model.appendRow(QStandardItem(png_filename))
                        self.data_dict[png_filename] = os.path.basename(file)
            for file in png_files:
                shutil.copy(file, self.temp_dir)
            self.listbox_png.selectionModel().selectionChanged.connect(self.on_select_png)
            self.listbox_data.doubleClicked.connect(self.on_double_click_xml)
        return self.temp_dir

    def create_settings_window(self):
            self.settings_window = QDialog(self)
            self.settings_window.setWindowTitle("Settings")
            self.settings_window.setGeometry(100, 100, 400, 300)

            scroll_area = QScrollArea(self.settings_window)
            scroll_area.setWidgetResizable(True)

            settings_frame = QFrame(scroll_area)
            settings_layout = QVBoxLayout(settings_frame)

            self.update_settings_window(settings_layout)

            scroll_area.setWidget(settings_frame)

            layout = QVBoxLayout(self.settings_window)
            layout.addWidget(scroll_area)
            self.settings_window.setLayout(layout)

            self.settings_window.exec()

    def update_settings_window(self, layout):
            layout.addWidget(QLabel("Animation Settings"))
            for key, value in self.user_settings.items():
                layout.addWidget(QLabel(f"{key}: {value}"))

            layout.addWidget(QLabel("Spritesheet Settings"))
            for key, value in self.spritesheet_settings.items():
                layout.addWidget(QLabel(f"{key}: {value}"))
        
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

    def on_double_click_png(self, index):
        spritesheet_name = index.data()
        new_window = QWidget()
        new_window.setGeometry(100, 100, 360, 360)
        self.create_animation_settings_window(new_window, spritesheet_name, self.spritesheet_settings)
        new_window.show()

    def on_double_click_xml(self, index):
        animation_name = index.data()
        selected_indexes = self.listbox_png.selectionModel().selectedIndexes()
        if selected_indexes:
            spritesheet_name = selected_indexes[0].data()
            full_anim_name = spritesheet_name + '/' + animation_name
            new_window = QWidget()
            new_window.setGeometry(100, 100, 360, 360)
            self.create_animation_settings_window(new_window, full_anim_name, self.user_settings)
            new_window.show()

    def create_animation_settings_window(self, window, name, settings_dict):
        layout = QFormLayout(window)

        fps_entry = QLineEdit()
        if name in settings_dict:
            fps_entry.setText(str(settings_dict[name].get('fps', '')))
        layout.addRow(f"FPS for {name}", fps_entry)

        delay_entry = QLineEdit()
        if name in settings_dict:
            delay_entry.setText(str(settings_dict[name].get('delay', '')))
        layout.addRow(f"Delay for {name}", delay_entry)

        period_entry = QLineEdit()
        if name in settings_dict:
            period_entry.setText(str(settings_dict[name].get('period', '')))
        layout.addRow(f"Min period for {name}", period_entry)

        scale_entry = QLineEdit()
        if name in settings_dict:
            scale_entry.setText(str(settings_dict[name].get('scale', '')))
        layout.addRow(f"Scale for {name}", scale_entry)

        threshold_entry = QLineEdit()
        if name in settings_dict:
            threshold_entry.setText(str(settings_dict[name].get('threshold', '')))
        layout.addRow(f"Threshold for {name}", threshold_entry)

        indices_entry = QLineEdit()
        if name in settings_dict:
            indices_entry.setText(str(settings_dict[name].get('indices', '')).translate(str.maketrans('', '', '[] ')))
        layout.addRow(f"Indices for {name}", indices_entry)

        frames_entry = QLineEdit()
        if name in settings_dict:
            frames_entry.setText(str(settings_dict[name].get('frames', '')))
        layout.addRow(f"Keep frames for {name}", frames_entry)

        ok_button = QPushButton("OK")
        ok_button.clicked.connect(lambda: self.store_input(window, name, settings_dict, fps_entry, delay_entry, period_entry, scale_entry, threshold_entry, indices_entry, frames_entry))
        layout.addWidget(ok_button)

        window.setLayout(layout)

    def store_input(self, window, name, settings_dict, fps_entry, delay_entry, period_entry, scale_entry, threshold_entry, indices_entry, frames_entry):
        anim_settings = {}
        try:
            if fps_entry.text() != '':
                anim_settings['fps'] = float(fps_entry.text())
        except ValueError:
            QMessageBox.critical(self, "Invalid input", "Please enter a valid float for FPS.")
            window.raise_()
            return
        try:
            if delay_entry.text() != '':
                anim_settings['delay'] = int(delay_entry.text())
        except ValueError:
            QMessageBox.critical(self, "Invalid input", "Please enter a valid integer for delay.")
            window.raise_()
            return
        try:
            if period_entry.text() != '':
                anim_settings['period'] = int(period_entry.text())
        except ValueError:
            QMessageBox.critical(self, "Invalid input", "Please enter a valid integer for period.")
            window.raise_()
            return
        try:
            if scale_entry.text() != '':
                if float(scale_entry.text()) == 0:
                    raise ValueError
                anim_settings['scale'] = float(scale_entry.text())
        except ValueError:
            QMessageBox.critical(self, "Invalid input", "Please enter a valid float for scale.")
            window.raise_()
            return
        try:
            if threshold_entry.text() != '':
                anim_settings['threshold'] = min(max(float(threshold_entry.text()), 0), 1)
        except ValueError:
            QMessageBox.critical(self, "Invalid input", "Please enter a valid float between 0 and 1 inclusive for threshold.")
            window.raise_()
            return
        try:
            if indices_entry.text() != '':
                indices = [int(ele) for ele in indices_entry.text().split(',')]
                anim_settings['indices'] = indices
        except ValueError:
            QMessageBox.critical(self, "Invalid input", "Please enter a comma-separated list of integers for indices.")
            window.raise_()
            return
        try:
            if frames_entry.text() != '':
                if not re.fullmatch(r',|all|first|last|first, ?last|none', frames_entry.text().lower()):
                    keep_frames = [ele for ele in frames_entry.text().split(',')]
                    for entry in keep_frames:
                        if not re.fullmatch(r'-?\d+(--?\d+)?', entry):
                            raise ValueError
                anim_settings['frames'] = frames_entry.text().lower()
        except ValueError:
            QMessageBox.critical(self, "Invalid input", "Please enter a keyword or a comma-separated list of integers or integer ranges for keep frames.")
            window.raise_()
            return
        if len(anim_settings) > 0:
            settings_dict[name] = anim_settings
        elif settings_dict.get(name):
            settings_dict.pop(name)
        window.close()
        
    def on_closing(self):
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        self.root.destroy()
        
    def start_process(self):
        extractor = Extractor(self.progress_bar, self.current_version)
        extractor.process_directory(
            self.input_dir.get(),
            self.output_dir.get(),
            self.progress_bar,
            self.root,
            self.create_gif.get(),
            self.create_webp.get(),
            self.set_framerate.get(),
            self.set_loopdelay.get(),
            self.set_minperiod.get(),
            self.set_scale.get(),
            self.set_threshold.get(),
            self.keep_frames.get(),
            self.crop_pngs.get(),
            self.variable_delay.get(),
            self.better_colors.get()
        )

if __name__ == "__main__":
    root = tk.Tk()
    app = TextureAtlasExtractorApp(root)
    root.mainloop()