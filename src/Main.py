#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Qt-based main application for TextureAtlas to GIF and Frames
This replaces the tkinter-based Main.py with a PySide6 implementation.
"""

import sys
import tempfile
import webbrowser
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox, QMenu
from PySide6.QtCore import QThread, Signal, QTimer
from PySide6.QtGui import QIcon, QAction

# Import our own modules
from utils.dependencies_checker import DependenciesChecker

# Check and configure ImageMagick
DependenciesChecker.check_and_configure_imagemagick()
from utils.app_config import AppConfig
from utils.update_checker import UpdateChecker
from utils.settings_manager import SettingsManager
from utils.fnf_utilities import FnfUtilities
from core.extractor import Extractor
from gui.app_ui import Ui_MainWindow
from gui.app_config_window_qt import AppConfigWindow
from gui.find_replace_window_qt import FindReplaceWindow
from gui.settings_window_qt import SettingsWindow
from gui.override_settings_window_qt import OverrideSettingsWindow
from gui.enhanced_list_widget import EnhancedListWidget


class ExtractorWorker(QThread):
    """Worker thread for extraction process."""

    progress_updated = Signal(int)
    extraction_completed = Signal()
    extraction_failed = Signal(str)

    def __init__(self, app_instance):
        super().__init__()
        self.app_instance = app_instance

    def run(self):
        try:
            self.app_instance.run_extractor_core()
            self.extraction_completed.emit()
        except Exception as e:
            self.extraction_failed.emit(str(e))


class TextureAtlasExtractorApp(QMainWindow):
    """
    A Qt/PySide6 GUI application for extracting textures from a texture atlas and converting them to GIF, WebP, and APNG formats.

    This class migrates the functionality from the tkinter-based TextureAtlasExtractorApp to Qt.
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

        # Replace QListView with QListWidget for easier list management
        self.setup_list_widgets()

        # Setup the application
        self.setup_gui()
        self.setup_connections()

        # Check version after a short delay
        QTimer.singleShot(250, self.check_version)

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
        self.setWindowTitle(f"TextureAtlas to GIF and Frames v{self.current_version}")
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
        self.ui.threshold_entry.setValue(defaults.get("threshold", 50))
        self.ui.frame_scale_entry.setValue(defaults.get("frame_scale", 1.0))

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
        self.ui.actionSelect_directory.triggered.connect(self.select_directory)
        self.ui.actionSelect_files.triggered.connect(self.select_files_manually)
        self.ui.actionClear_export_list.triggered.connect(self.clear_filelist)
        self.ui.actionPreferences.triggered.connect(self.create_app_config_window)
        self.ui.actionFNF_Import_settings_from_character_data_file.triggered.connect(
            self.fnf_import_settings
        )

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

        # List selections
        self.ui.listbox_png.currentItemChanged.connect(self.on_select_spritesheet)
        self.ui.listbox_data.itemDoubleClicked.connect(self.on_double_click_animation)

        # Context menu for spritesheet list
        self.ui.listbox_png.customContextMenuRequested.connect(self.show_listbox_png_menu)

        # Format change handlers
        self.ui.animation_format_combobox.currentTextChanged.connect(
            self.on_animation_format_change
        )
        self.ui.frame_format_combobox.currentTextChanged.connect(self.on_frame_format_change)

    def select_directory(self):
        """Opens a directory selection dialog and populates the spritesheet list."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Input Directory",
            "",
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks,
        )

        if directory:
            self.ui.input_dir_label.setText(directory)
            self.populate_spritesheet_list(directory)

            # Clear settings when changing directory
            self.settings_manager.animation_settings.clear()
            self.settings_manager.spritesheet_settings.clear()

    def select_output_directory(self):
        """Opens a directory selection dialog for output directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            "",
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks,
        )

        if directory:
            self.ui.output_dir_label.setText(directory)

    def select_files_manually(self):
        """Opens a file selection dialog for manual file selection."""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Files", "", "Image files (*.png *.jpg *.jpeg);;All files (*.*)"
        )

        if files:
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
            return

        data_files = self.data_dict[spritesheet_name]

        # Parse XML files for animations
        if "xml" in data_files:
            try:
                # This would need to use the actual XML parser from the original code
                # For now, this is a placeholder
                self.ui.listbox_data.add_item(
                    "Animation 1 (XML)", {"type": "xml", "file": data_files["xml"]}
                )
                self.ui.listbox_data.add_item(
                    "Animation 2 (XML)", {"type": "xml", "file": data_files["xml"]}
                )
            except Exception as e:
                print(f"Error parsing XML: {e}")

        # Parse TXT files for animations
        if "txt" in data_files:
            try:
                # This would need to use the actual TXT parser from the original code
                # For now, this is a placeholder
                self.ui.listbox_data.add_item(
                    "Animation 1 (TXT)", {"type": "txt", "file": data_files["txt"]}
                )
            except Exception as e:
                print(f"Error parsing TXT: {e}")

    def on_double_click_animation(self, item):
        """Handles the event when an animation is double-clicked in the listbox."""
        if not item:
            return

        animation_name = item.text()
        # animation_data = item.data(item.data())  # This should get the data from UserRole

        # Show animation preview or settings
        QMessageBox.information(self, "Animation Selected", f"Selected: {animation_name}")

    def show_listbox_png_menu(self, position):
        """Shows the context menu for the PNG listbox."""
        item = self.ui.listbox_png.itemAt(position)
        if item is None:
            return

        menu = QMenu(self)
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(self.delete_selected_spritesheet)
        menu.addAction(delete_action)

        menu.exec(self.ui.listbox_png.mapToGlobal(position))

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

    def create_find_and_replace_window(self):
        """Creates the Find and Replace window."""
        try:
            dialog = FindReplaceWindow(self, self.store_replace_rules, self.replace_rules)
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

        animation_name = current_item.text()

        def store_settings(settings):
            """Callback to store animation settings."""
            self.settings_manager.animation_settings[animation_name] = settings

        try:
            dialog = OverrideSettingsWindow(
                self, animation_name, "animation", self.settings_manager, store_settings, self
            )
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open animation settings: {str(e)}")

    def fnf_import_settings(self):
        """Imports settings from FNF character data file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select FNF Character Data File", "", "JSON files (*.json);;All files (*.*)"
        )

        if file_path:
            try:
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

    def update_global_settings(self):
        """Updates the global settings from the GUI."""
        # Get values from UI elements
        settings = {
            "animation_format": self.ui.animation_format_combobox.currentText(),
            "frame_rate": self.ui.frame_rate_entry.value(),
            "loop_delay": self.ui.loop_delay_entry.value(),
            "min_period": self.ui.min_period_entry.value(),
            "scale": self.ui.scale_entry.value(),
            "threshold": self.ui.threshold_entry.value(),
            "frame_format": self.ui.frame_format_combobox.currentText(),
            "frame_scale": self.ui.frame_scale_entry.value(),
            "frame_selection": self.ui.frame_selection_combobox.currentText(),
            "cropping_method": self.ui.cropping_method_combobox.currentText(),
            "filename_prefix": self.ui.filename_prefix_entry.text(),
            "filename_suffix": self.ui.filename_suffix_entry.text(),
            "filename_format": self.ui.filename_format_combobox.currentText(),
        }

        # Update settings manager
        for key, value in settings.items():
            setattr(self.settings_manager.global_settings, key, value)

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

        # Disable the process button
        self.ui.start_process_button.setEnabled(False)
        self.ui.start_process_button.setText("Processing...")

        # Start extraction in worker thread
        self.worker = ExtractorWorker(self)
        self.worker.extraction_completed.connect(self.on_extraction_completed)
        self.worker.extraction_failed.connect(self.on_extraction_failed)
        self.worker.start()

    def run_extractor_core(self):
        """Core extraction logic (runs in worker thread)."""
        # This is a placeholder for the actual extraction logic
        # The original tkinter version's run_extractor method should be adapted here
        try:
            # Create extractor instance
            extractor = Extractor(self.settings_manager, self.app_config, temp_dir=self.temp_dir)

            # Run extraction
            input_dir = self.ui.input_dir_label.text()
            output_dir = self.ui.output_dir_label.text()

            # This will need to be fully implemented based on the original tkinter version
            extractor.extract_all(input_dir, output_dir, self.data_dict)

        except Exception as e:
            raise e

    def on_extraction_completed(self):
        """Called when extraction completes successfully."""
        self.ui.start_process_button.setEnabled(True)
        self.ui.start_process_button.setText("Start process")
        QMessageBox.information(self, "Success", "Extraction completed successfully!")

    def on_extraction_failed(self, error_message):
        """Called when extraction fails."""
        self.ui.start_process_button.setEnabled(True)
        self.ui.start_process_button.setText("Start process")
        QMessageBox.critical(self, "Error", f"Extraction failed: {error_message}")

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

    # Set application properties
    app.setApplicationName("TextureAtlas to GIF and Frames")
    app.setApplicationVersion("1.9.5.1")
    app.setOrganizationName("AutisticLulu")

    try:
        # Create and show main window
        window = TextureAtlasExtractorApp()
        window.show()

        # Run application
        sys.exit(app.exec())

    except Exception as e:
        QMessageBox.critical(None, "Fatal Error", f"Application failed to start: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
