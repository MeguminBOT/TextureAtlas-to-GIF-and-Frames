#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import shutil
import tempfile
import webbrowser
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox, QMenu
from PySide6.QtCore import QThread, Signal, QTimer, Qt
from PySide6.QtGui import QIcon, QAction

# Import our own modules
from utils.dependencies_checker import DependenciesChecker
DependenciesChecker.check_and_configure_imagemagick()  # This function must be called before any other operations that require ImageMagick (DO NOT MOVE THIS IMPORT LINE)
from utils.app_config import AppConfig
from utils.update_checker import UpdateChecker
from utils.settings_manager import SettingsManager
from utils.fnf_utilities import FnfUtilities
from core.extractor import Extractor
from gui.app_ui import Ui_MainWindow
from gui.app_config_window import AppConfigWindow
from gui.enhanced_list_widget import EnhancedListWidget
from gui.settings_window import SettingsWindow
from gui.find_replace_window import FindReplaceWindow
from gui.override_settings_window import OverrideSettingsWindow
from gui.help_window import HelpWindow
from gui.contributors_window import ContributorsWindow
from gui.processing_window import ProcessingWindow
from gui.unknown_atlas_warning_window import UnknownAtlasWarningWindow
from gui.background_handler_window import BackgroundHandlerWindow
from gui.compression_settings_window import CompressionSettingsWindow


class ExtractorWorker(QThread):
    """Worker thread for extraction process."""

    progress_updated = Signal(int, int, str)  # current, total, filename
    statistics_updated = Signal(
        int, int, int
    )  # frames_generated, animations_generated, sprites_failed
    debug_message = Signal(str)  # debug message for processing log
    extraction_completed = Signal(str)  # completion message
    extraction_failed = Signal(str)
    error_occurred = Signal(str, str)  # title, message
    question_needed = Signal(str, str)  # title, message

    def __init__(self, app_instance, spritesheet_list):
        super().__init__()
        self.app_instance = app_instance
        self.spritesheet_list = spritesheet_list
        self.continue_on_error = True

    def run(self):
        try:
            print(f"[ExtractorWorker] Starting extraction of {len(self.spritesheet_list)} files")
            completion_message = self.app_instance.run_extractor_core(
                self.spritesheet_list, self.emit_progress
            )
            print(f"[ExtractorWorker] Extraction completed: {completion_message}")
            self.extraction_completed.emit(completion_message)
        except Exception as e:
            print(f"[ExtractorWorker] Extraction failed: {str(e)}")
            self.extraction_failed.emit(str(e))

    def emit_progress(self, current, total, filename=""):
        """Thread-safe progress emission."""
        print(f"[ExtractorWorker] Progress: {current}/{total} - {filename}")
        self.progress_updated.emit(current, total, filename)

    def emit_statistics(self, frames_generated, animations_generated, sprites_failed):
        """Thread-safe statistics emission."""
        print(
            f"[ExtractorWorker] Stats: F:{frames_generated}, A:{animations_generated}, S:{sprites_failed}"
        )
        self.statistics_updated.emit(frames_generated, animations_generated, sprites_failed)


class TextureAtlasExtractorApp(QMainWindow):
    """
    A Qt/PySide6 GUI application for extracting textures from a texture atlas and converting them to GIF, WebP, and APNG formats.
    """

    def __init__(self):
        super().__init__()

        # Initialize core attributes
        self.current_version = "1.9.5.1"
        self.app_config = AppConfig()
        self.settings_manager = SettingsManager()
        self.temp_dir = tempfile.mkdtemp()
        self.manual_selection_temp_dir = (
            None  # For storing temp directory used in manual file selection
        )
        self.data_dict = {}

        self.fnf_utilities = FnfUtilities()
        self.fnf_char_json_directory = ""
        self.replace_rules = []
        self.linkSourceCode = "https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames"

        # Initialize UI
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Initialize advanced menu variables
        defaults = (
            self.app_config.get_extraction_defaults()
            if hasattr(self.app_config, "get_extraction_defaults")
            else {}
        )
        self.variable_delay = defaults.get("variable_delay", False)
        self.fnf_idle_loop = defaults.get("fnf_idle_loop", False)

        # Create advanced menu actions
        self.setup_advanced_menu()

        # Replace QListView with QListWidget for easier list management
        self.setup_list_widgets()

        # Setup the application
        self.setup_gui()
        self.setup_connections()

        # Check version after a short delay
        QTimer.singleShot(250, self.check_version)

    def setup_advanced_menu(self):
        """Set up the advanced menu with variable delay and FNF options."""
        # Create variable delay action
        self.variable_delay_action = QAction("Variable delay", self, checkable=True)
        self.variable_delay_action.setChecked(self.variable_delay)
        self.variable_delay_action.setStatusTip(
            "Enable variable delay between frames for more accurate timing"
        )

        # Create FNF idle loop action
        self.fnf_idle_loop_action = QAction(
            "FNF: Set loop delay on idle animations to 0", self, checkable=True
        )
        self.fnf_idle_loop_action.setChecked(self.fnf_idle_loop)
        self.fnf_idle_loop_action.setStatusTip(
            "Automatically set loop delay to 0 for animations with 'idle' in their name"
        )

        # Add actions to advanced menu
        self.ui.advanced_menu.addAction(self.variable_delay_action)
        self.ui.advanced_menu.addAction(self.fnf_idle_loop_action)

    def setup_list_widgets(self):
        """Replace the QListView widgets with QListWidget for easier management."""
        # Replace spritesheet list
        old_png_list = self.ui.listbox_png
        self.ui.listbox_png = EnhancedListWidget(old_png_list.parent())
        self.ui.listbox_png.setGeometry(old_png_list.geometry())
        self.ui.listbox_png.setObjectName("listbox_png")
        old_png_list.setParent(None)

        # Replace animation data list
        old_data_list = self.ui.listbox_data
        self.ui.listbox_data = EnhancedListWidget(old_data_list.parent())
        self.ui.listbox_data.setGeometry(old_data_list.geometry())
        self.ui.listbox_data.setObjectName("listbox_data")
        old_data_list.setParent(None)

    def setup_gui(self):
        """Sets up the GUI components of the application."""
        self.setWindowTitle(f"TextureAtlas Toolbox v{self.current_version}")
        self.resize(900, 770)

        # Set application icon if available
        icon_path = Path("assets/icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # Initialize default values from app config
        defaults = (
            self.app_config.get_extraction_defaults()
            if hasattr(self.app_config, "get_extraction_defaults")
            else {}
        )

        # Set default values for UI elements
        self.ui.frame_rate_entry.setValue(defaults.get("frame_rate", 24))
        self.ui.loop_delay_entry.setValue(defaults.get("loop_delay", 250))
        self.ui.min_period_entry.setValue(defaults.get("min_period", 0))
        self.ui.scale_entry.setValue(defaults.get("scale", 1.0))
        self.ui.threshold_entry.setValue(
            defaults.get("threshold", 0.5) * 100.0
        )  # Convert from 0-1 to 0-100 for UI
        self.ui.frame_scale_entry.setValue(defaults.get("frame_scale", 1.0))

        # Set default groupbox states
        self.ui.animation_export_group.setChecked(defaults.get("animation_export", True))
        self.ui.frame_export_group.setChecked(defaults.get("frame_export", True))

        # Set default selections
        if "animation_format" in defaults:
            format_index = self.ui.animation_format_combobox.findText(defaults["animation_format"])
            if format_index >= 0:
                self.ui.animation_format_combobox.setCurrentIndex(format_index)

        if "frame_format" in defaults:
            format_index = self.ui.frame_format_combobox.findText(defaults["frame_format"])
            if format_index >= 0:
                self.ui.frame_format_combobox.setCurrentIndex(format_index)

    def setup_connections(self):
        """Sets up signal-slot connections for UI elements."""
        # Menu actions
        self.ui.select_directory.triggered.connect(self.select_directory)
        self.ui.select_files.triggered.connect(self.select_files_manually)
        self.ui.clear_export_list.triggered.connect(self.clear_filelist)
        self.ui.preferences.triggered.connect(self.create_app_config_window)
        self.ui.fnf_import_settings.triggered.connect(self.fnf_import_settings)
        self.ui.help_manual.triggered.connect(self.show_help_manual)
        self.ui.help_fnf.triggered.connect(self.show_help_fnf)
        self.ui.show_contributors.triggered.connect(self.show_contributors_window)

        # Advanced menu actions
        self.variable_delay_action.toggled.connect(self.on_variable_delay_toggled)
        self.fnf_idle_loop_action.toggled.connect(self.on_fnf_idle_loop_toggled)

        # Buttons
        self.ui.input_button.clicked.connect(self.select_directory)
        self.ui.output_button.clicked.connect(self.select_output_directory)
        self.ui.start_process_button.clicked.connect(self.start_process)
        self.ui.reset_button.clicked.connect(self.clear_filelist)
        self.ui.advanced_filename_button.clicked.connect(self.create_find_and_replace_window)
        self.ui.show_override_settings_button.clicked.connect(self.create_settings_window)
        self.ui.override_spritesheet_settings_button.clicked.connect(
            self.override_spritesheet_settings
        )
        self.ui.override_animation_settings_button.clicked.connect(self.override_animation_settings)
        self.ui.compression_settings_button.clicked.connect(self.show_compression_settings)

        # List selections
        self.ui.listbox_png.currentItemChanged.connect(self.on_select_spritesheet)
        self.ui.listbox_png.currentItemChanged.connect(self.update_ui_state)
        self.ui.listbox_png.itemDoubleClicked.connect(self.on_double_click_spritesheet)
        self.ui.listbox_data.itemDoubleClicked.connect(self.on_double_click_animation)
        self.ui.listbox_data.currentItemChanged.connect(self.update_ui_state)

        # Context menus
        self.ui.listbox_png.customContextMenuRequested.connect(self.show_listbox_png_menu)
        self.ui.listbox_data.customContextMenuRequested.connect(self.show_listbox_data_menu)

        # Format change handlers
        self.ui.animation_format_combobox.currentTextChanged.connect(
            self.on_animation_format_change
        )
        self.ui.frame_format_combobox.currentTextChanged.connect(self.on_frame_format_change)

        # Export group checkbox changes
        self.ui.animation_export_group.toggled.connect(self.update_ui_state)
        self.ui.frame_export_group.toggled.connect(self.update_ui_state)

        # Initial UI state update
        self.update_ui_state()

    def select_directory(self):
        """Opens a directory selection dialog and populates the spritesheet list."""
        # Start from the last used directory or default to empty
        start_directory = self.app_config.get_last_input_directory()

        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Input Directory",
            start_directory,
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks,
        )

        if directory:
            # Save the selected directory for next time
            self.app_config.set_last_input_directory(directory)

            self.ui.input_dir_label.setText(directory)
            self.populate_spritesheet_list(directory)

            # Clear settings when changing directory
            self.settings_manager.animation_settings.clear()
            self.settings_manager.spritesheet_settings.clear()

    def select_output_directory(self):
        """Opens a directory selection dialog for output directory."""
        # Start from the last used directory or default to empty
        start_directory = self.app_config.get_last_output_directory()

        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            start_directory,
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks,
        )

        if directory:
            # Save the selected directory for next time
            self.app_config.set_last_output_directory(directory)
            self.ui.output_dir_label.setText(directory)

    def select_files_manually(self):
        """Opens a file selection dialog for manual file selection."""
        # Start from the last used input directory or default to empty
        start_directory = self.app_config.get_last_input_directory()

        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Files",
            start_directory,
            "Image files (*.png *.jpg *.jpeg);;All files (*.*)",
        )

        if files:
            # Save the directory of the first selected file for next time
            if files:
                import os

                first_file_dir = os.path.dirname(files[0])
                self.app_config.set_last_input_directory(first_file_dir)

            # Clean up previous manual selection temp directory if exists
            if self.manual_selection_temp_dir:
                try:
                    import shutil

                    shutil.rmtree(self.manual_selection_temp_dir, ignore_errors=True)
                except Exception:
                    pass

            # For manual file selection, use a temp folder
            import tempfile

            self.manual_selection_temp_dir = tempfile.mkdtemp(prefix="texture_atlas_manual_")
            self.ui.input_dir_label.setText(f"Manual selection ({len(files)} files)")
            self.populate_spritesheet_list_from_files(files, self.manual_selection_temp_dir)

    def populate_spritesheet_list(self, directory):
        """Populates the spritesheet list from a directory."""
        self.ui.listbox_png.clear()
        self.ui.listbox_data.clear()
        self.data_dict.clear()

        directory_path = Path(directory)
        if not directory_path.exists():
            return

        # Find PNG files
        png_files = list(directory_path.glob("*.png"))

        for png_file in png_files:
            # Add to list
            self.ui.listbox_png.add_item(png_file.name, str(png_file))

            # Look for corresponding data files (XML, TXT, etc.)
            self.find_data_files_for_spritesheet(png_file)

    def populate_spritesheet_list_from_files(self, files, temp_folder=None):
        """Populates the spritesheet list from manually selected files."""
        self.ui.listbox_png.clear()
        self.ui.listbox_data.clear()
        self.data_dict.clear()

        for file_path in files:
            path = Path(file_path)
            if path.suffix.lower() in [".png", ".jpg", ".jpeg"]:
                self.ui.listbox_png.add_item(path.name, str(path))
                # Use temp folder if provided, otherwise use original file location
                search_directory = Path(temp_folder) if temp_folder else path.parent
                self.find_data_files_for_spritesheet(path, search_directory)

    def find_data_files_for_spritesheet(self, spritesheet_path, search_directory=None):
        """Find data files (XML, TXT) associated with a spritesheet."""
        spritesheet_path = Path(spritesheet_path)
        base_name = spritesheet_path.stem
        # Use provided search directory or default to spritesheet's directory
        directory = Path(search_directory) if search_directory else spritesheet_path.parent

        # Initialize data dict entry
        if spritesheet_path.name not in self.data_dict:
            self.data_dict[spritesheet_path.name] = {}

        # Look for XML files
        xml_file = directory / f"{base_name}.xml"
        if xml_file.exists():
            self.data_dict[spritesheet_path.name]["xml"] = str(xml_file)

        # Look for TXT files
        txt_file = directory / f"{base_name}.txt"
        if txt_file.exists():
            self.data_dict[spritesheet_path.name]["txt"] = str(txt_file)

    def on_select_spritesheet(self, current, previous):
        """Handles the event when a PNG file is selected from the listbox."""
        if not current:
            return

        spritesheet_name = current.text()
        self.populate_animation_list(spritesheet_name)

    def populate_animation_list(self, spritesheet_name):
        """Populates the animation list for the selected spritesheet."""
        self.ui.listbox_data.clear()

        if spritesheet_name not in self.data_dict:
            # If no data files found, try to use the unknown parser
            try:
                from parsers.unknown_parser import UnknownParser

                # Get the spritesheet file path from the listbox
                current_item = self.ui.listbox_png.currentItem()
                if current_item:
                    spritesheet_path = current_item.data(Qt.ItemDataRole.UserRole)
                    if spritesheet_path:
                        unknown_parser = UnknownParser(
                            directory=str(Path(spritesheet_path).parent),
                            png_filename=Path(spritesheet_path).name,
                            listbox_data=self.ui.listbox_data,
                        )
                        unknown_parser.get_data()
            except Exception as e:
                print(f"Error using unknown parser: {e}")
            return

        data_files = self.data_dict[spritesheet_name]

        # Parse XML files for animations
        if "xml" in data_files:
            try:
                from parsers.xml_parser import XmlParser

                xml_parser = XmlParser(
                    directory=str(Path(data_files["xml"]).parent),
                    xml_filename=Path(data_files["xml"]).name,
                    listbox_data=self.ui.listbox_data,
                )
                xml_parser.get_data()
            except Exception as e:
                print(f"Error parsing XML: {e}")

        # Parse TXT files for animations (only if no XML found)
        elif "txt" in data_files:
            try:
                from parsers.txt_parser import TxtParser

                txt_parser = TxtParser(
                    directory=str(Path(data_files["txt"]).parent),
                    txt_filename=Path(data_files["txt"]).name,
                    listbox_data=self.ui.listbox_data,
                )
                txt_parser.get_data()
            except Exception as e:
                print(f"Error parsing TXT: {e}")

        # If no data files found, try to use the unknown parser
        else:
            try:
                from parsers.unknown_parser import UnknownParser

                # Get the spritesheet file path from the listbox
                current_item = self.ui.listbox_png.currentItem()
                if current_item:
                    spritesheet_path = current_item.data(Qt.ItemDataRole.UserRole)
                    if spritesheet_path:
                        unknown_parser = UnknownParser(
                            directory=str(Path(spritesheet_path).parent),
                            png_filename=Path(spritesheet_path).name,
                            listbox_data=self.ui.listbox_data,
                        )
                        unknown_parser.get_data()
            except Exception as e:
                print(f"Error using unknown parser: {e}")

    def on_double_click_animation(self, item):
        """Handles the event when an animation is double-clicked in the listbox."""
        if not item:
            return

        # Get the selected spritesheet
        current_spritesheet_item = self.ui.listbox_png.currentItem()
        if not current_spritesheet_item:
            QMessageBox.information(self, "Info", "Please select a spritesheet first.")
            return

        spritesheet_name = current_spritesheet_item.text()
        animation_name = item.text()
        full_anim_name = f"{spritesheet_name}/{animation_name}"

        def store_settings(settings):
            """Callback to store animation settings."""
            self.settings_manager.animation_settings[full_anim_name] = settings

        try:
            dialog = OverrideSettingsWindow(
                self, full_anim_name, "animation", self.settings_manager, store_settings, self
            )
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open animation settings: {str(e)}")

    def on_double_click_spritesheet(self, item):
        """Handles the event when a spritesheet is double-clicked in the listbox."""
        if not item:
            return

        spritesheet_name = item.text()

        def store_settings(settings):
            """Callback to store spritesheet settings."""
            self.settings_manager.spritesheet_settings[spritesheet_name] = settings

        try:
            dialog = OverrideSettingsWindow(
                self, spritesheet_name, "spritesheet", self.settings_manager, store_settings, self
            )
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open spritesheet settings: {str(e)}")

    def show_listbox_png_menu(self, position):
        """Shows the context menu for the PNG listbox."""
        item = self.ui.listbox_png.itemAt(position)
        if item is None:
            return

        menu = QMenu(self)

        settings_action = QAction("Override Settings", self)
        settings_action.triggered.connect(self.override_spritesheet_settings)
        menu.addAction(settings_action)

        menu.addSeparator()

        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(self.delete_selected_spritesheet)
        menu.addAction(delete_action)

        menu.exec(self.ui.listbox_png.mapToGlobal(position))

    def show_listbox_data_menu(self, position):
        """Shows the context menu for the animation listbox."""
        item = self.ui.listbox_data.itemAt(position)
        if item is None:
            return

        menu = QMenu(self)
        settings_action = QAction("Override Settings", self)
        settings_action.triggered.connect(self.override_animation_settings)
        menu.addAction(settings_action)

        menu.exec(self.ui.listbox_data.mapToGlobal(position))

    def delete_selected_spritesheet(self):
        """Deletes the selected spritesheet and related settings."""
        current_item = self.ui.listbox_png.currentItem()
        if not current_item:
            return

        spritesheet_name = current_item.text()

        # Remove from data dict
        if spritesheet_name in self.data_dict:
            del self.data_dict[spritesheet_name]

        # Remove from list
        row = self.ui.listbox_png.row(current_item)
        self.ui.listbox_png.takeItem(row)

        # Clear animation list
        self.ui.listbox_data.clear()

        # Remove related settings
        self.settings_manager.spritesheet_settings.pop(spritesheet_name, None)

    def clear_filelist(self):
        """Clears the file list and resets settings."""
        # Clean up manual selection temp directory if exists
        if self.manual_selection_temp_dir:
            try:
                import shutil

                shutil.rmtree(self.manual_selection_temp_dir, ignore_errors=True)
                self.manual_selection_temp_dir = None
            except Exception:
                pass

        # Clear the list widgets
        self.ui.listbox_png.clear()
        self.ui.listbox_data.clear()

        # Reset labels
        self.ui.input_dir_label.setText("No input directory selected")
        self.ui.output_dir_label.setText("No output directory selected")

        # Clear settings
        self.settings_manager.animation_settings.clear()
        self.settings_manager.spritesheet_settings.clear()
        self.data_dict.clear()

    def create_app_config_window(self):
        """Creates the preferences/app config window."""
        try:
            dialog = AppConfigWindow(self, self.app_config)
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Could not open preferences: {str(e)}")

    def show_help_manual(self):
        """Shows the main help window with application manual."""
        try:
            HelpWindow.create_main_help_window(self)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open help window: {str(e)}")

    def show_help_fnf(self):
        """Shows the FNF-specific help window."""
        try:
            HelpWindow.create_fnf_help_window(self)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open FNF help window: {str(e)}")

    def show_contributors_window(self):
        """Shows the contributors window."""
        try:
            ContributorsWindow.show_contributors(self)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open contributors window: {str(e)}")

    def show_compression_settings(self):
        """Shows the compression settings window for the current frame format."""
        try:
            current_format = self.ui.frame_format_combobox.currentText()
            dialog = CompressionSettingsWindow(
                parent=self,
                settings_manager=self.settings_manager,
                app_config=self.app_config,
                current_format=current_format,
            )
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(
                self, "Error", f"Could not open compression settings window: {str(e)}"
            )

    def create_find_and_replace_window(self):
        """Creates the Find and Replace window."""
        try:
            dialog = FindReplaceWindow(self.store_replace_rules, self.replace_rules, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Could not open find/replace window: {str(e)}")

    def create_settings_window(self):
        """Creates the settings overview window."""
        try:
            dialog = SettingsWindow(self, self.settings_manager)
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Could not open settings window: {str(e)}")

    def store_replace_rules(self, rules):
        """Stores the replace rules from the Find and Replace window."""
        self.replace_rules = rules

    def override_spritesheet_settings(self):
        """Opens window to override settings for selected spritesheet."""
        current_item = self.ui.listbox_png.currentItem()
        if not current_item:
            QMessageBox.information(self, "Info", "Please select a spritesheet first.")
            return

        spritesheet_name = current_item.text()

        def store_settings(settings):
            """Callback to store spritesheet settings."""
            self.settings_manager.spritesheet_settings[spritesheet_name] = settings

        try:
            dialog = OverrideSettingsWindow(
                self, spritesheet_name, "spritesheet", self.settings_manager, store_settings, self
            )
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open spritesheet settings: {str(e)}")

    def override_animation_settings(self):
        """Opens window to override settings for selected animation."""
        current_item = self.ui.listbox_data.currentItem()
        if not current_item:
            QMessageBox.information(self, "Info", "Please select an animation first.")
            return

        # Get the selected spritesheet to create full animation name
        current_spritesheet_item = self.ui.listbox_png.currentItem()
        if not current_spritesheet_item:
            QMessageBox.information(self, "Info", "Please select a spritesheet first.")
            return

        spritesheet_name = current_spritesheet_item.text()
        animation_name = current_item.text()
        full_anim_name = f"{spritesheet_name}/{animation_name}"

        def store_settings(settings):
            """Callback to store animation settings."""
            self.settings_manager.animation_settings[full_anim_name] = settings

        try:
            dialog = OverrideSettingsWindow(
                self, full_anim_name, "animation", self.settings_manager, store_settings, self
            )
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open animation settings: {str(e)}")

    def fnf_import_settings(self):
        """Imports settings from FNF character data file."""
        # Start from the last used input directory for FNF files
        start_directory = self.app_config.get_last_input_directory()

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select FNF Character Data File",
            start_directory,
            "JSON files (*.json);;All files (*.*)",
        )

        if file_path:
            try:
                # Save the directory of the selected file for next time
                import os

                file_dir = os.path.dirname(file_path)
                self.app_config.set_last_input_directory(file_dir)

                # Use the existing FNF utilities
                self.fnf_utilities.import_character_settings(file_path)
                QMessageBox.information(self, "Success", "FNF settings imported successfully!")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to import FNF settings: {str(e)}")

    def check_version(self, force=False):
        """Checks for updates to the application."""
        try:
            update_checker = UpdateChecker(self.current_version)
            if update_checker.check_for_updates() or force:
                # Show update dialog
                reply = QMessageBox.question(
                    self,
                    "Update Available",
                    "A new version is available! Would you like to visit the download page?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )

                if reply == QMessageBox.StandardButton.Yes:
                    webbrowser.open(self.linkSourceCode)
        except Exception as e:
            if force:
                QMessageBox.warning(
                    self, "Update Check Failed", f"Could not check for updates: {str(e)}"
                )

    def update_ui_state(self, *args):
        """Updates the UI state based on current selections and settings."""
        both_export_unchecked = not (
            self.ui.animation_export_group.isChecked() or self.ui.frame_export_group.isChecked()
        )
        self.ui.start_process_button.setEnabled(not both_export_unchecked)

        has_spritesheet_selected = self.ui.listbox_png.currentItem() is not None
        self.ui.override_spritesheet_settings_button.setEnabled(has_spritesheet_selected)

        has_animation_selected = self.ui.listbox_data.currentItem() is not None
        self.ui.override_animation_settings_button.setEnabled(has_animation_selected)

    def on_animation_format_change(self):
        """Handles animation format selection changes."""
        format_text = self.ui.animation_format_combobox.currentText()

        # Update UI based on format capabilities
        if format_text == "GIF":
            self.ui.threshold_entry.setEnabled(True)
            self.ui.threshold_label.setEnabled(True)
        else:
            self.ui.threshold_entry.setEnabled(False)
            self.ui.threshold_label.setEnabled(False)

    def on_frame_format_change(self):
        """Handles frame format selection changes."""
        # Update compression options based on format
        # This will need to be implemented when compression widgets are added
        pass

    def on_variable_delay_toggled(self, checked):
        """Handle the variable delay menu toggle."""
        self.variable_delay = checked
        # Update the app config if needed
        if hasattr(self.app_config, "settings"):
            self.app_config.settings["variable_delay"] = checked

    def on_fnf_idle_loop_toggled(self, checked):
        """Handle the FNF idle loop menu toggle."""
        self.fnf_idle_loop = checked
        # Update the app config if needed
        if hasattr(self.app_config, "settings"):
            self.app_config.settings["fnf_idle_loop"] = checked

    def update_global_settings(self):
        """Updates the global settings from the GUI."""
        # Get format options directly from comboboxes (decoupled from groupbox checkboxes)
        animation_format = self.ui.animation_format_combobox.currentText()
        frame_format = self.ui.frame_format_combobox.currentText()

        # Get export enable states from groupboxes
        animation_export = self.ui.animation_export_group.isChecked()
        frame_export = self.ui.frame_export_group.isChecked()

        # Get values from UI elements
        settings = {
            "animation_format": animation_format,
            "frame_format": frame_format,
            "animation_export": animation_export,
            "frame_export": frame_export,
            "fps": self.ui.frame_rate_entry.value(),
            "delay": self.ui.loop_delay_entry.value(),
            "period": self.ui.min_period_entry.value(),
            "scale": self.ui.scale_entry.value(),
            "threshold": self.ui.threshold_entry.value() / 100.0,  # Convert % to 0-1 range
            "frame_scale": self.ui.frame_scale_entry.value(),
            "frame_selection": self.ui.frame_selection_combobox.currentText(),
            "crop_option": self.ui.cropping_method_combobox.currentText(),
            "prefix": self.ui.filename_prefix_entry.text(),
            "suffix": self.ui.filename_suffix_entry.text(),
            "filename_format": self.ui.filename_format_combobox.currentText(),
            "replace_rules": getattr(self, "replace_rules", []),
            "var_delay": self.variable_delay,
            "fnf_idle_loop": self.fnf_idle_loop,
        }

        # Update settings manager
        for key, value in settings.items():
            self.settings_manager.global_settings[key] = value

    def start_process(self):
        """Prepares and starts the processing thread."""
        # Validate inputs
        if self.ui.input_dir_label.text() == "No input directory selected":
            QMessageBox.warning(self, "Error", "Please select an input directory first.")
            return

        if self.ui.output_dir_label.text() == "No output directory selected":
            QMessageBox.warning(self, "Error", "Please select an output directory first.")
            return

        # Update global settings
        self.update_global_settings()

        # Get spritesheet list
        spritesheet_list = []
        for i in range(self.ui.listbox_png.count()):
            item = self.ui.listbox_png.item(i)
            if item:
                spritesheet_list.append(item.text())

        # Check for unknown atlases and handle user choice
        has_unknown, unknown_atlases = self.check_for_unknown_atlases(spritesheet_list)
        if has_unknown:
            action = self.show_unknown_atlas_warning(unknown_atlases)
            if action == "cancel":
                return
            elif action == "skip":
                self.filter_unknown_atlases(unknown_atlases)
                # Update spritesheet list after filtering
                spritesheet_list = []
                for i in range(self.ui.listbox_png.count()):
                    item = self.ui.listbox_png.item(i)
                    if item:
                        spritesheet_list.append(item.text())

        # Handle background detection for unknown spritesheets in main thread
        from core.extractor import Extractor

        # Create a temporary extractor instance with required arguments
        temp_extractor = Extractor(
            progress_callback=None,
            current_version=self.current_version,
            settings_manager=self.settings_manager,
        )
        input_dir = self.ui.input_dir_label.text()
        if temp_extractor._handle_unknown_spritesheets_background_detection(
            input_dir, spritesheet_list, self
        ):
            # User cancelled background detection
            return

        # Create and show processing window
        self.processing_window = ProcessingWindow(self)
        self.processing_window.start_processing(len(spritesheet_list))
        self.processing_window.show()
        self.processing_window.raise_()  # Bring to front
        self.processing_window.activateWindow()  # Make it active

        # Disable the process button
        self.ui.start_process_button.setEnabled(False)
        self.ui.start_process_button.setText("Processing...")

        # Start extraction in worker thread
        self.worker = ExtractorWorker(self, spritesheet_list)
        self.worker.extraction_completed.connect(self.on_extraction_completed)
        self.worker.extraction_failed.connect(self.on_extraction_failed)
        self.worker.progress_updated.connect(self.on_progress_updated)
        self.worker.statistics_updated.connect(self.on_statistics_updated)
        self.worker.debug_message.connect(self.on_debug_message)
        self.worker.error_occurred.connect(self.on_worker_error)
        self.worker.question_needed.connect(self.on_worker_question)
        self.worker.start()

    def run_extractor_core(self, spritesheet_list, progress_signal):
        """Core extraction logic (runs in worker thread)."""
        try:
            print(f"[run_extractor_core] Starting with {len(spritesheet_list)} files")

            # Create progress callback that emits signals to update UI
            def progress_callback(current, total, filename=""):
                print(f"[progress_callback] {current}/{total} - {filename}")
                progress_signal(current, total, filename)

            # Create statistics callback to track generation statistics
            def statistics_callback(frames_generated, animations_generated, sprites_failed):
                print(
                    f"[statistics_callback] F:{frames_generated}, A:{animations_generated}, S:{sprites_failed}"
                )
                if hasattr(self, "worker") and self.worker:
                    print(
                        f"[statistics_callback] Emitting to worker: F:{frames_generated}, A:{animations_generated}, S:{sprites_failed}"
                    )
                    self.worker.emit_statistics(
                        frames_generated, animations_generated, sprites_failed
                    )
                else:
                    print("[statistics_callback] No worker available to emit statistics")

            # Create debug callback to send processing log updates
            def debug_callback(message):
                print(f"[debug_callback] {message}")
                # Emit debug message through a new signal
                if hasattr(self.worker, "debug_message"):
                    self.worker.debug_message.emit(message)

            # Create extractor instance
            extractor = Extractor(
                progress_callback,
                self.current_version,
                self.settings_manager,
                app_config=self.app_config,
                statistics_callback=statistics_callback,
            )

            # Set additional callbacks
            extractor.debug_callback = debug_callback
            extractor.fnf_idle_loop = self.fnf_idle_loop

            # Run extraction
            input_dir = self.ui.input_dir_label.text()
            output_dir = self.ui.output_dir_label.text()

            print(f"[run_extractor_core] Input: {input_dir}, Output: {output_dir}")

            extractor.process_directory(
                input_dir,
                output_dir,
                parent_window=self,
                spritesheet_list=spritesheet_list,
            )

            return "Extraction completed successfully!"

        except Exception as e:
            print(f"[run_extractor_core] Error: {str(e)}")
            raise e

    def on_extraction_completed(self, completion_message):
        """Called when extraction completes successfully."""
        print(f"[on_extraction_completed] {completion_message}")
        self.ui.start_process_button.setEnabled(True)
        self.ui.start_process_button.setText("Start process")

        if hasattr(self, "processing_window"):
            self.processing_window.processing_completed(True, completion_message)

    def on_extraction_failed(self, error_message):
        """Called when extraction fails."""
        print(f"[on_extraction_failed] {error_message}")
        self.ui.start_process_button.setEnabled(True)
        self.ui.start_process_button.setText("Start process")

        if hasattr(self, "processing_window"):
            self.processing_window.processing_completed(False, error_message)

    def on_progress_updated(self, current, total, filename):
        """Updates the processing window with progress information."""
        print(f"[on_progress_updated] {current}/{total} - {filename}")
        if hasattr(self, "processing_window") and self.processing_window:
            self.processing_window.update_progress(current, total, filename)
        else:
            print("[on_progress_updated] No processing window available")

    def on_statistics_updated(self, frames_generated, animations_generated, sprites_failed):
        """Updates the processing window with statistics information."""
        print(
            f"[on_statistics_updated] F:{frames_generated}, A:{animations_generated}, S:{sprites_failed}"
        )
        if hasattr(self, "processing_window") and self.processing_window:
            self.processing_window.update_statistics(
                frames_generated, animations_generated, sprites_failed
            )
        else:
            print("[on_statistics_updated] No processing window available")

    def on_debug_message(self, message):
        """Handle debug messages from worker thread."""
        print(f"[on_debug_message] {message}")
        if hasattr(self, "processing_window") and self.processing_window:
            self.processing_window.add_debug_message(message)
        else:
            print("[on_debug_message] No processing window available")

    def on_worker_error(self, title, message):
        """Handle error messages from worker thread."""
        QMessageBox.critical(self, title, message)

    def on_worker_question(self, title, message):
        """Handle question dialogs from worker thread."""
        reply = QMessageBox.question(
            self, title, message, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        # Send the response back to the worker
        if hasattr(self, "worker"):
            self.worker.continue_on_error = reply == QMessageBox.StandardButton.Yes

    def check_for_unknown_atlases(self, spritesheet_list):
        """Check for atlases without metadata files (unknown atlases)."""
        unknown_atlases = []
        input_directory = self.ui.input_dir_label.text()

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
        """Show the unknown atlas warning dialog."""
        input_directory = self.ui.input_dir_label.text()
        return UnknownAtlasWarningWindow.show_warning(self, unknown_atlases, input_directory)

    def filter_unknown_atlases(self, unknown_atlases):
        """Remove unknown atlases from the spritesheet list."""
        for unknown_atlas in unknown_atlases:
            for i in range(self.ui.listbox_png.count()):
                item = self.ui.listbox_png.item(i)
                if item and item.text() == unknown_atlas:
                    self.ui.listbox_png.takeItem(i)
                    break

        # Clear animation list since we removed spritesheets
        self.ui.listbox_data.clear()

    def closeEvent(self, event):
        """Handles the window close event."""
        # Clean up temporary files
        try:
            import shutil

            shutil.rmtree(self.temp_dir, ignore_errors=True)
            # Clean up manual selection temp directory
            if self.manual_selection_temp_dir:
                shutil.rmtree(self.manual_selection_temp_dir, ignore_errors=True)
        except Exception:
            pass

        # Save settings if needed
        try:
            self.app_config.save_settings()
        except Exception:
            pass

        event.accept()


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)

    try:
        # Create the main window first to access version
        window = TextureAtlasExtractorApp()

        # Set application properties using the window's version
        app.setApplicationName("TextureAtlas Toolbox")
        app.setApplicationVersion(window.current_version)
        app.setOrganizationName("AutisticLulu")

        # Show the window
        window.show()

        # Run application
        sys.exit(app.exec())

    except Exception as e:
        QMessageBox.critical(None, "Fatal Error", f"Application failed to start: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
