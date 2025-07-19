#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import shutil
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QLineEdit,
    QFrame,
    QFileDialog,
    QMenu,
    QMessageBox,
)
from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtGui import QAction

from gui.enhanced_list_widget import EnhancedListWidget


class ExtractTabWidget(QWidget):
    """Widget for the Extract tab functionality."""

    def __init__(self, parent=None, use_existing_ui=False):
        super().__init__(parent)
        self.parent_app = parent
        self.use_existing_ui = use_existing_ui

        if use_existing_ui and parent:
            # Use existing UI elements from parent
            self.setup_with_existing_ui()
        else:
            # Create new UI elements (fallback)
            self.setup_ui()

        self.setup_connections()
        self.setup_default_values()

    def tr(self, text):
        """Translate text using Qt's translation system."""
        return QCoreApplication.translate("ExtractTabWidget", text)

    def setup_with_existing_ui(self):
        """Set up the widget using existing UI elements from the parent."""
        if not self.parent_app or not hasattr(self.parent_app, "ui"):
            return

        # Reference existing UI elements
        self.listbox_png = self.parent_app.ui.listbox_png
        self.listbox_data = self.parent_app.ui.listbox_data
        self.input_button = self.parent_app.ui.input_button
        self.output_button = self.parent_app.ui.output_button
        self.input_dir_label = self.parent_app.ui.input_dir_label
        self.output_dir_label = self.parent_app.ui.output_dir_label
        self.animation_export_group = self.parent_app.ui.animation_export_group
        self.frame_export_group = self.parent_app.ui.frame_export_group
        self.animation_format_combobox = self.parent_app.ui.animation_format_combobox
        self.frame_format_combobox = self.parent_app.ui.frame_format_combobox
        self.frame_rate_entry = self.parent_app.ui.frame_rate_entry
        self.loop_delay_entry = self.parent_app.ui.loop_delay_entry
        self.min_period_entry = self.parent_app.ui.min_period_entry
        self.scale_entry = self.parent_app.ui.scale_entry
        self.threshold_entry = self.parent_app.ui.threshold_entry
        self.frame_scale_entry = self.parent_app.ui.frame_scale_entry
        self.frame_selection_combobox = self.parent_app.ui.frame_selection_combobox
        self.cropping_method_combobox = self.parent_app.ui.cropping_method_combobox
        self.filename_format_combobox = self.parent_app.ui.filename_format_combobox
        self.filename_prefix_entry = self.parent_app.ui.filename_prefix_entry
        self.filename_suffix_entry = self.parent_app.ui.filename_suffix_entry
        self.advanced_filename_button = self.parent_app.ui.advanced_filename_button
        self.show_override_settings_button = self.parent_app.ui.show_override_settings_button
        self.override_spritesheet_settings_button = (
            self.parent_app.ui.override_spritesheet_settings_button
        )
        self.override_animation_settings_button = (
            self.parent_app.ui.override_animation_settings_button
        )
        self.start_process_button = self.parent_app.ui.start_process_button
        self.reset_button = self.parent_app.ui.reset_button

        # Create missing elements that might not be in the UI file
        if not hasattr(self.parent_app.ui, "compression_settings_button"):
            self.compression_settings_button = QPushButton(self.tr("Compression Settings"))
            # You might need to position this somewhere in the frame export group
        else:
            self.compression_settings_button = self.parent_app.ui.compression_settings_button

        # Convert QListView to EnhancedListWidget if needed
        if hasattr(self.listbox_png, "add_item"):
            # Already converted
            pass
        else:
            # Need to enhance the existing QListView
            from gui.enhanced_list_widget import EnhancedListWidget

            # Replace the listbox_png with EnhancedListWidget
            parent_widget = self.listbox_png.parent()
            geometry = self.listbox_png.geometry()
            self.listbox_png.setParent(None)

            self.listbox_png = EnhancedListWidget(parent_widget)
            self.listbox_png.setGeometry(geometry)
            self.listbox_png.setObjectName("listbox_png")
            self.listbox_png.setAlternatingRowColors(False)
            self.listbox_png.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

            # Do the same for listbox_data
            parent_widget = self.listbox_data.parent()
            geometry = self.listbox_data.geometry()
            self.listbox_data.setParent(None)

            self.listbox_data = EnhancedListWidget(parent_widget)
            self.listbox_data.setGeometry(geometry)
            self.listbox_data.setObjectName("listbox_data")
            self.listbox_data.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

    def setup_ui(self):
        """Set up the UI components for the extract tab."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # Top section with file lists and directory buttons
        top_section = self.create_top_section()
        main_layout.addWidget(top_section)

        # Export settings section
        export_section = self.create_export_section()
        main_layout.addWidget(export_section)

        # Bottom section with filename settings and buttons
        bottom_section = self.create_bottom_section()
        main_layout.addWidget(bottom_section)

    def create_top_section(self):
        """Create the top section with file lists and directory buttons."""
        top_widget = QWidget()
        layout = QHBoxLayout(top_widget)

        # Left side - file lists
        lists_widget = QWidget()
        lists_layout = QHBoxLayout(lists_widget)

        # Spritesheet list
        self.listbox_png = EnhancedListWidget()
        self.listbox_png.setObjectName("listbox_png")
        self.listbox_png.setFixedSize(200, 621)
        self.listbox_png.setAlternatingRowColors(False)
        self.listbox_png.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        lists_layout.addWidget(self.listbox_png)

        # Animation data list
        self.listbox_data = EnhancedListWidget()
        self.listbox_data.setObjectName("listbox_data")
        self.listbox_data.setFixedSize(200, 621)
        self.listbox_data.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        lists_layout.addWidget(self.listbox_data)

        layout.addWidget(lists_widget)

        # Right side - directory selection
        dir_widget = QWidget()
        dir_layout = QVBoxLayout(dir_widget)

        # Input directory
        self.input_button = QPushButton(self.tr("Select input directory"))
        self.input_button.setFixedSize(171, 24)
        dir_layout.addWidget(self.input_button)

        self.input_dir_label = QLabel(self.tr("No input directory selected"))
        self.input_dir_label.setFixedSize(451, 21)
        self.input_dir_label.setFrameShape(QFrame.Shape.NoFrame)
        self.input_dir_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dir_layout.addWidget(self.input_dir_label)

        # Output directory
        self.output_button = QPushButton(self.tr("Select output directory"))
        self.output_button.setFixedSize(171, 24)
        dir_layout.addWidget(self.output_button)

        self.output_dir_label = QLabel(self.tr("No output directory selected"))
        self.output_dir_label.setFixedSize(451, 21)
        self.output_dir_label.setFrameShape(QFrame.Shape.NoFrame)
        self.output_dir_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dir_layout.addWidget(self.output_dir_label)

        dir_layout.addStretch()
        layout.addWidget(dir_widget)

        return top_widget

    def create_export_section(self):
        """Create the export settings section."""
        export_widget = QWidget()
        layout = QHBoxLayout(export_widget)

        # Animation export group
        self.animation_export_group = self.create_animation_export_group()
        layout.addWidget(self.animation_export_group)

        # Frame export group
        self.frame_export_group = self.create_frame_export_group()
        layout.addWidget(self.frame_export_group)

        return export_widget

    def create_animation_export_group(self):
        """Create the animation export group box."""
        group = QGroupBox(self.tr("Animation export"))
        group.setFixedSize(191, 331)
        group.setAlignment(Qt.AlignmentFlag.AlignCenter)
        group.setCheckable(True)
        group.setChecked(True)

        # Animation format
        format_label = QLabel(self.tr("Format"))
        format_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        format_label.setGeometry(40, 30, 111, 16)
        format_label.setParent(group)

        self.animation_format_combobox = QComboBox(group)
        self.animation_format_combobox.setGeometry(10, 50, 171, 24)
        self.animation_format_combobox.addItems(["GIF", "WebP", "APNG", "Custom FFMPEG"])

        # Frame rate
        frame_rate_label = QLabel(self.tr("Frame rate"))
        frame_rate_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        frame_rate_label.setGeometry(40, 80, 111, 16)
        frame_rate_label.setParent(group)

        self.frame_rate_entry = QSpinBox(group)
        self.frame_rate_entry.setGeometry(10, 100, 171, 24)
        self.frame_rate_entry.setRange(1, 1000)
        self.frame_rate_entry.setValue(24)

        # Loop delay
        loop_delay_label = QLabel(self.tr("Loop delay"))
        loop_delay_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loop_delay_label.setGeometry(40, 130, 111, 16)
        loop_delay_label.setParent(group)

        self.loop_delay_entry = QSpinBox(group)
        self.loop_delay_entry.setGeometry(10, 150, 171, 24)
        self.loop_delay_entry.setRange(0, 10000)
        self.loop_delay_entry.setValue(250)

        # Min period
        min_period_label = QLabel(self.tr("Min period"))
        min_period_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        min_period_label.setGeometry(40, 180, 111, 16)
        min_period_label.setParent(group)

        self.min_period_entry = QSpinBox(group)
        self.min_period_entry.setGeometry(10, 200, 171, 24)
        self.min_period_entry.setRange(0, 10000)
        self.min_period_entry.setValue(0)

        # Scale
        scale_label = QLabel(self.tr("Scale"))
        scale_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scale_label.setGeometry(40, 230, 111, 16)
        scale_label.setParent(group)

        self.scale_entry = QDoubleSpinBox(group)
        self.scale_entry.setGeometry(10, 250, 171, 24)
        self.scale_entry.setRange(0.01, 100.0)
        self.scale_entry.setValue(1.0)
        self.scale_entry.setDecimals(2)
        self.scale_entry.setSingleStep(0.01)

        # Threshold
        threshold_label = QLabel(self.tr("Alpha threshold"))
        threshold_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        threshold_label.setGeometry(40, 280, 111, 16)
        threshold_label.setParent(group)

        self.threshold_entry = QSpinBox(group)
        self.threshold_entry.setGeometry(10, 300, 171, 24)
        self.threshold_entry.setRange(0, 100)
        self.threshold_entry.setValue(50)

        return group

    def create_frame_export_group(self):
        """Create the frame export group box."""
        group = QGroupBox(self.tr("Frame export"))
        group.setFixedSize(191, 331)
        group.setAlignment(Qt.AlignmentFlag.AlignCenter)
        group.setCheckable(True)
        group.setChecked(True)

        # Frame format
        format_label = QLabel(self.tr("Format"))
        format_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        format_label.setGeometry(40, 30, 111, 16)
        format_label.setParent(group)

        self.frame_format_combobox = QComboBox(group)
        self.frame_format_combobox.setGeometry(10, 50, 171, 24)
        self.frame_format_combobox.addItems(["AVIF", "BMP", "DDS", "PNG", "TGA", "TIFF", "WebP"])

        # Frame selection
        selection_label = QLabel(self.tr("Frame Selection"))
        selection_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        selection_label.setGeometry(40, 80, 111, 16)
        selection_label.setParent(group)

        self.frame_selection_combobox = QComboBox(group)
        self.frame_selection_combobox.setGeometry(10, 100, 171, 24)
        self.frame_selection_combobox.addItems(
            ["All", "No duplicates", "First", "Last", "First, Last", "Custom"]
        )

        # Frame scale
        scale_label = QLabel(self.tr("Frame scale"))
        scale_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scale_label.setGeometry(40, 130, 111, 16)
        scale_label.setParent(group)

        self.frame_scale_entry = QDoubleSpinBox(group)
        self.frame_scale_entry.setGeometry(10, 150, 171, 24)
        self.frame_scale_entry.setRange(0.01, 100.0)
        self.frame_scale_entry.setValue(1.0)
        self.frame_scale_entry.setDecimals(2)
        self.frame_scale_entry.setSingleStep(0.01)

        # Compression settings button
        self.compression_settings_button = QPushButton(self.tr("Compression settings"))
        self.compression_settings_button.setGeometry(10, 200, 171, 24)
        self.compression_settings_button.setParent(group)

        return group

    def create_bottom_section(self):
        """Create the bottom section with filename settings and buttons."""
        bottom_widget = QWidget()
        layout = QVBoxLayout(bottom_widget)

        # Filename settings
        filename_section = self.create_filename_section()
        layout.addWidget(filename_section)

        # Control buttons
        buttons_section = self.create_buttons_section()
        layout.addWidget(buttons_section)

        return bottom_widget

    def create_filename_section(self):
        """Create the filename settings section."""
        filename_widget = QWidget()
        layout = QHBoxLayout(filename_widget)

        # Cropping method
        cropping_label = QLabel(self.tr("Cropping method"))
        cropping_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(cropping_label)

        self.cropping_method_combobox = QComboBox()
        self.cropping_method_combobox.addItems(["None", "Animation based", "Frame based"])
        layout.addWidget(self.cropping_method_combobox)

        # Filename format
        format_label = QLabel(self.tr("Filename format"))
        layout.addWidget(format_label)

        self.filename_format_combobox = QComboBox()
        self.filename_format_combobox.addItems(
            ["Standardized", "No spaces", "No special characters"]
        )
        layout.addWidget(self.filename_format_combobox)

        # Filename prefix
        prefix_label = QLabel(self.tr("Prefix"))
        layout.addWidget(prefix_label)

        self.filename_prefix_entry = QLineEdit()
        layout.addWidget(self.filename_prefix_entry)

        # Filename suffix
        suffix_label = QLabel(self.tr("Suffix"))
        layout.addWidget(suffix_label)

        self.filename_suffix_entry = QLineEdit()
        layout.addWidget(self.filename_suffix_entry)

        return filename_widget

    def create_buttons_section(self):
        """Create the control buttons section."""
        buttons_widget = QWidget()
        layout = QHBoxLayout(buttons_widget)

        # Advanced filename button
        self.advanced_filename_button = QPushButton(self.tr("Advanced filename"))
        layout.addWidget(self.advanced_filename_button)

        # Override settings buttons
        self.show_override_settings_button = QPushButton(self.tr("Override settings"))
        layout.addWidget(self.show_override_settings_button)

        self.override_spritesheet_settings_button = QPushButton(self.tr("Override spritesheet"))
        layout.addWidget(self.override_spritesheet_settings_button)

        self.override_animation_settings_button = QPushButton(self.tr("Override animation"))
        layout.addWidget(self.override_animation_settings_button)

        # Control buttons
        self.reset_button = QPushButton(self.tr("Reset"))
        layout.addWidget(self.reset_button)

        self.start_process_button = QPushButton(self.tr("Start process"))
        layout.addWidget(self.start_process_button)

        return buttons_widget

    def setup_connections(self):
        """Set up signal-slot connections."""
        if not self.parent_app:
            return

        # Directory buttons
        if hasattr(self, "input_button"):
            self.input_button.clicked.connect(self.select_directory)
        if hasattr(self, "output_button"):
            self.output_button.clicked.connect(self.select_output_directory)

        # Control buttons
        if hasattr(self, "start_process_button"):
            self.start_process_button.clicked.connect(self.parent_app.start_process)
        if hasattr(self, "reset_button"):
            self.reset_button.clicked.connect(self.clear_filelist)
        if hasattr(self, "advanced_filename_button"):
            self.advanced_filename_button.clicked.connect(
                self.parent_app.create_find_and_replace_window
            )
        if hasattr(self, "show_override_settings_button"):
            self.show_override_settings_button.clicked.connect(
                self.parent_app.create_settings_window
            )
        if hasattr(self, "override_spritesheet_settings_button"):
            self.override_spritesheet_settings_button.clicked.connect(
                self.override_spritesheet_settings
            )
        if hasattr(self, "override_animation_settings_button"):
            self.override_animation_settings_button.clicked.connect(
                self.override_animation_settings
            )
        if hasattr(self, "compression_settings_button"):
            self.compression_settings_button.clicked.connect(
                self.parent_app.show_compression_settings
            )

        # List selections
        if hasattr(self, "listbox_png"):
            self.listbox_png.currentItemChanged.connect(self.on_select_spritesheet)
            self.listbox_png.currentItemChanged.connect(self.update_ui_state)
            self.listbox_png.itemDoubleClicked.connect(self.on_double_click_spritesheet)
            self.listbox_png.customContextMenuRequested.connect(self.show_listbox_png_menu)

        if hasattr(self, "listbox_data"):
            self.listbox_data.itemDoubleClicked.connect(self.on_double_click_animation)
            self.listbox_data.currentItemChanged.connect(self.update_ui_state)
            self.listbox_data.customContextMenuRequested.connect(self.show_listbox_data_menu)

        # Format change handlers
        if hasattr(self, "animation_format_combobox"):
            self.animation_format_combobox.currentTextChanged.connect(
                self.on_animation_format_change
            )
        if hasattr(self, "frame_format_combobox"):
            self.frame_format_combobox.currentTextChanged.connect(self.on_frame_format_change)

        # Export group checkbox changes
        if hasattr(self, "animation_export_group"):
            self.animation_export_group.toggled.connect(self.update_ui_state)
        if hasattr(self, "frame_export_group"):
            self.frame_export_group.toggled.connect(self.update_ui_state)

    def setup_default_values(self):
        """Set up default values from app config."""
        if self.parent_app and hasattr(self.parent_app, "app_config"):
            defaults = (
                self.parent_app.app_config.get_extraction_defaults()
                if hasattr(self.parent_app.app_config, "get_extraction_defaults")
                else {}
            )

            # Set default values for UI elements
            self.frame_rate_entry.setValue(defaults.get("frame_rate", 24))
            self.loop_delay_entry.setValue(defaults.get("loop_delay", 250))
            self.min_period_entry.setValue(defaults.get("min_period", 0))
            self.scale_entry.setValue(defaults.get("scale", 1.0))
            self.threshold_entry.setValue(defaults.get("threshold", 0.5) * 100.0)
            self.frame_scale_entry.setValue(defaults.get("frame_scale", 1.0))

            # Set default groupbox states
            self.animation_export_group.setChecked(defaults.get("animation_export", True))
            self.frame_export_group.setChecked(defaults.get("frame_export", True))

            # Set default selections
            if "animation_format" in defaults:
                format_index = self.get_animation_format_index(defaults["animation_format"])
                self.animation_format_combobox.setCurrentIndex(format_index)

            if "frame_format" in defaults:
                format_index = self.get_frame_format_index(defaults["frame_format"])
                self.frame_format_combobox.setCurrentIndex(format_index)

    def get_animation_format_index(self, format_name):
        """Get the index for animation format."""
        format_map = {"GIF": 0, "WebP": 1, "APNG": 2, "Custom FFMPEG": 3}
        return format_map.get(format_name, 0)

    def get_frame_format_index(self, format_name):
        """Get the index for frame format."""
        format_map = {"AVIF": 0, "BMP": 1, "DDS": 2, "PNG": 3, "TGA": 4, "TIFF": 5, "WebP": 6}
        return format_map.get(format_name, 0)

    # === File Management Methods ===

    def select_directory(self):
        """Opens a directory selection dialog and populates the spritesheet list."""
        if not self.parent_app:
            return

        # Start from the last used directory or default to empty
        start_directory = self.parent_app.app_config.get_last_input_directory()

        directory = QFileDialog.getExistingDirectory(
            self,
            self.tr("Select Input Directory"),
            start_directory,
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks,
        )

        if directory:
            # Save the selected directory for next time
            self.parent_app.app_config.set_last_input_directory(directory)
            self.input_dir_label.setText(directory)
            self.populate_spritesheet_list(directory)

            # Clear settings when changing directory
            self.parent_app.settings_manager.animation_settings.clear()
            self.parent_app.settings_manager.spritesheet_settings.clear()

    def select_output_directory(self):
        """Opens a directory selection dialog for output directory."""
        if not self.parent_app:
            return

        # Start from the last used directory or default to empty
        start_directory = self.parent_app.app_config.get_last_output_directory()

        directory = QFileDialog.getExistingDirectory(
            self,
            self.tr("Select Output Directory"),
            start_directory,
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks,
        )

        if directory:
            # Save the selected directory for next time
            self.parent_app.app_config.set_last_output_directory(directory)
            self.output_dir_label.setText(directory)

    def select_files_manually(self):
        """Opens a file selection dialog for manual file selection."""
        if not self.parent_app:
            return

        # Start from the last used input directory or default to empty
        start_directory = self.parent_app.app_config.get_last_input_directory()

        files, _ = QFileDialog.getOpenFileNames(
            self,
            self.tr("Select Files"),
            start_directory,
            self.tr("Image files (*.png *.jpg *.jpeg);;All files (*.*)"),
        )

        if files:
            # Save the directory of the first selected file for next time
            if files:
                first_file_dir = os.path.dirname(files[0])
                self.parent_app.app_config.set_last_input_directory(first_file_dir)

            # Clean up previous manual selection temp directory if exists
            if (
                hasattr(self.parent_app, "manual_selection_temp_dir")
                and self.parent_app.manual_selection_temp_dir
            ):
                try:
                    shutil.rmtree(self.parent_app.manual_selection_temp_dir, ignore_errors=True)
                except Exception:
                    pass

            # For manual file selection, use a temp folder
            self.parent_app.manual_selection_temp_dir = tempfile.mkdtemp(
                prefix="texture_atlas_manual_"
            )
            self.input_dir_label.setText(
                self.tr("Manual selection ({count} files)").format(count=len(files))
            )
            self.populate_spritesheet_list_from_files(
                files, self.parent_app.manual_selection_temp_dir
            )

    def populate_spritesheet_list(self, directory):
        """Populates the spritesheet list from a directory."""
        if not self.parent_app:
            return

        self.listbox_png.clear()
        self.listbox_data.clear()
        self.parent_app.data_dict.clear()

        directory_path = Path(directory)
        if not directory_path.exists():
            return

        # Find PNG files
        png_files = list(directory_path.glob("*.png"))

        for png_file in png_files:
            # Add to list
            self.listbox_png.add_item(png_file.name, str(png_file))
            # Look for corresponding data files (XML, TXT, etc.)
            self.find_data_files_for_spritesheet(png_file)

    def populate_spritesheet_list_from_files(self, files, temp_folder=None):
        """Populates the spritesheet list from manually selected files."""
        if not self.parent_app:
            return

        self.listbox_png.clear()
        self.listbox_data.clear()
        self.parent_app.data_dict.clear()

        for file_path in files:
            path = Path(file_path)
            if path.suffix.lower() in [".png", ".jpg", ".jpeg"]:
                self.listbox_png.add_item(path.name, str(path))
                # Use temp folder if provided, otherwise use original file location
                search_directory = Path(temp_folder) if temp_folder else path.parent
                self.find_data_files_for_spritesheet(path, search_directory)

    def find_data_files_for_spritesheet(self, spritesheet_path, search_directory=None):
        """Find data files (XML, TXT) associated with a spritesheet."""
        if not self.parent_app:
            return

        spritesheet_path = Path(spritesheet_path)
        base_name = spritesheet_path.stem
        # Use provided search directory or default to spritesheet's directory
        directory = Path(search_directory) if search_directory else spritesheet_path.parent

        # Initialize data dict entry
        if spritesheet_path.name not in self.parent_app.data_dict:
            self.parent_app.data_dict[spritesheet_path.name] = {}

        # Look for XML files
        xml_file = directory / f"{base_name}.xml"
        if xml_file.exists():
            self.parent_app.data_dict[spritesheet_path.name]["xml"] = str(xml_file)

        # Look for TXT files
        txt_file = directory / f"{base_name}.txt"
        if txt_file.exists():
            self.parent_app.data_dict[spritesheet_path.name]["txt"] = str(txt_file)

    def on_select_spritesheet(self, current, previous):
        """Handles the event when a PNG file is selected from the listbox."""
        if not current or not self.parent_app:
            return

        spritesheet_name = current.text()
        self.populate_animation_list(spritesheet_name)

    def populate_animation_list(self, spritesheet_name):
        """Populates the animation list for the selected spritesheet."""
        if not self.parent_app:
            return

        self.listbox_data.clear()

        if spritesheet_name not in self.parent_app.data_dict:
            # If no data files found, try to use the unknown parser
            try:
                from parsers.unknown_parser import UnknownParser

                # Get the spritesheet file path from the listbox
                current_item = self.listbox_png.currentItem()
                if current_item:
                    spritesheet_path = current_item.data(Qt.ItemDataRole.UserRole)
                    if spritesheet_path:
                        unknown_parser = UnknownParser(
                            directory=str(Path(spritesheet_path).parent),
                            png_filename=Path(spritesheet_path).name,
                            listbox_data=self.listbox_data,
                        )
                        unknown_parser.get_data()
            except Exception as e:
                print(f"Error using unknown parser: {e}")
            return

        data_files = self.parent_app.data_dict[spritesheet_name]

        # Parse XML files for animations
        if "xml" in data_files:
            try:
                from parsers.xml_parser import XmlParser

                xml_parser = XmlParser(
                    directory=str(Path(data_files["xml"]).parent),
                    xml_filename=Path(data_files["xml"]).name,
                    listbox_data=self.listbox_data,
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
                    listbox_data=self.listbox_data,
                )
                txt_parser.get_data()
            except Exception as e:
                print(f"Error parsing TXT: {e}")

        # If no data files found, try to use the unknown parser
        else:
            try:
                from parsers.unknown_parser import UnknownParser

                # Get the spritesheet file path from the listbox
                current_item = self.listbox_png.currentItem()
                if current_item:
                    spritesheet_path = current_item.data(Qt.ItemDataRole.UserRole)
                    if spritesheet_path:
                        unknown_parser = UnknownParser(
                            directory=str(Path(spritesheet_path).parent),
                            png_filename=Path(spritesheet_path).name,
                            listbox_data=self.listbox_data,
                        )
                        unknown_parser.get_data()
            except Exception as e:
                print(f"Error using unknown parser: {e}")

    def clear_filelist(self):
        """Clears the file list and resets settings."""
        if not self.parent_app:
            return

        # Clean up manual selection temp directory if exists
        if (
            hasattr(self.parent_app, "manual_selection_temp_dir")
            and self.parent_app.manual_selection_temp_dir
        ):
            try:
                import shutil

                shutil.rmtree(self.parent_app.manual_selection_temp_dir, ignore_errors=True)
                self.parent_app.manual_selection_temp_dir = None
            except Exception:
                pass

        # Clear the list widgets
        self.listbox_png.clear()
        self.listbox_data.clear()

        # Reset labels
        self.input_dir_label.setText(self.tr("No input directory selected"))
        self.output_dir_label.setText(self.tr("No output directory selected"))

        # Clear settings
        self.parent_app.settings_manager.animation_settings.clear()
        self.parent_app.settings_manager.spritesheet_settings.clear()
        self.parent_app.data_dict.clear()

        # Clear settings
        self.parent_app.settings_manager.animation_settings.clear()
        self.parent_app.settings_manager.spritesheet_settings.clear()
        self.parent_app.data_dict.clear()

    def delete_selected_spritesheet(self):
        """Deletes the selected spritesheet and related settings."""
        if not self.parent_app:
            return

        current_item = self.listbox_png.currentItem()
        if not current_item:
            return

        spritesheet_name = current_item.text()

        # Remove from data dict
        if spritesheet_name in self.parent_app.data_dict:
            del self.parent_app.data_dict[spritesheet_name]

        # Remove from list
        row = self.listbox_png.row(current_item)
        self.listbox_png.takeItem(row)

        # Clear animation list
        self.listbox_data.clear()

        # Remove related settings
        self.parent_app.settings_manager.spritesheet_settings.pop(spritesheet_name, None)

        # Clear animation list
        self.listbox_data.clear()

        # Remove related settings
        self.parent_app.settings_manager.spritesheet_settings.pop(spritesheet_name, None)

    def show_listbox_png_menu(self, position):
        """Shows the context menu for the PNG listbox."""
        if not self.parent_app:
            return

        item = self.listbox_png.itemAt(position)
        if item is None:
            return

        menu = QMenu(self)

        settings_action = QAction(self.tr("Override Settings"), self)
        settings_action.triggered.connect(self.override_spritesheet_settings)
        menu.addAction(settings_action)

        menu.addSeparator()

        delete_action = QAction(self.tr("Delete"), self)
        delete_action.triggered.connect(self.delete_selected_spritesheet)
        menu.addAction(delete_action)

        menu.exec(self.listbox_png.mapToGlobal(position))

    def show_listbox_data_menu(self, position):
        """Shows the context menu for the animation listbox."""
        if not self.parent_app:
            return

        item = self.listbox_data.itemAt(position)
        if item is None:
            return

        menu = QMenu(self)

        preview_action = QAction(self.tr("Preview Animation"), self)
        preview_action.triggered.connect(self.preview_selected_animation)
        menu.addAction(preview_action)

        menu.addSeparator()

        settings_action = QAction(self.tr("Override Settings"), self)
        settings_action.triggered.connect(self.override_animation_settings)
        menu.addAction(settings_action)

        menu.exec(self.listbox_data.mapToGlobal(position))

    def on_double_click_animation(self, item):
        """Handles the event when an animation is double-clicked in the listbox."""
        if not item or not self.parent_app:
            return

        # Get the selected spritesheet
        current_spritesheet_item = self.listbox_png.currentItem()
        if not current_spritesheet_item:
            QMessageBox.information(
                self, self.tr("Error"), self.tr("Please select a spritesheet first.")
            )
            return

        spritesheet_name = current_spritesheet_item.text()
        animation_name = item.text()
        full_anim_name = "{spritesheet}/{animation}".format(
            spritesheet=spritesheet_name, animation=animation_name
        )

        def store_settings(settings):
            """Callback to store animation settings."""
            self.parent_app.settings_manager.animation_settings[full_anim_name] = settings

        try:
            from gui.override_settings_window import OverrideSettingsWindow

            dialog = OverrideSettingsWindow(
                self.parent_app,
                full_anim_name,
                "animation",
                self.parent_app.settings_manager,
                store_settings,
                self.parent_app,
            )
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(
                self,
                self.tr("Error"),
                self.tr("Could not open animation settings: {error}").format(error=str(e)),
            )

    def on_double_click_spritesheet(self, item):
        """Handles the event when a spritesheet is double-clicked in the listbox."""
        if not item or not self.parent_app:
            return

        spritesheet_name = item.text()

        def store_settings(settings):
            """Callback to store spritesheet settings."""
            self.parent_app.settings_manager.spritesheet_settings[spritesheet_name] = settings

        try:
            from gui.override_settings_window import OverrideSettingsWindow

            dialog = OverrideSettingsWindow(
                self.parent_app,
                spritesheet_name,
                "spritesheet",
                self.parent_app.settings_manager,
                store_settings,
                self.parent_app,
            )
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(
                self,
                self.tr("Error"),
                self.tr("Could not open spritesheet settings: {error}").format(error=str(e)),
            )

    def override_spritesheet_settings(self):
        """Opens window to override settings for selected spritesheet."""
        if not self.parent_app:
            return

        current_item = self.listbox_png.currentItem()
        if not current_item:
            QMessageBox.information(
                self, self.tr("Error"), self.tr("Please select a spritesheet first.")
            )
            return

        spritesheet_name = current_item.text()

        def store_settings(settings):
            """Callback to store spritesheet settings."""
            self.parent_app.settings_manager.spritesheet_settings[spritesheet_name] = settings

        try:
            from gui.override_settings_window import OverrideSettingsWindow

            dialog = OverrideSettingsWindow(
                self.parent_app,
                spritesheet_name,
                "spritesheet",
                self.parent_app.settings_manager,
                store_settings,
                self.parent_app,
            )
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(
                self,
                self.tr("Error"),
                self.tr("Could not open spritesheet settings: {error}").format(error=str(e)),
            )

    def override_animation_settings(self):
        """Opens window to override settings for selected animation."""
        if not self.parent_app:
            return

        current_item = self.listbox_data.currentItem()
        if not current_item:
            QMessageBox.information(
                self, self.tr("Error"), self.tr("Please select an animation first.")
            )
            return

        # Get the selected spritesheet to create full animation name
        current_spritesheet_item = self.listbox_png.currentItem()
        if not current_spritesheet_item:
            QMessageBox.information(
                self, self.tr("Error"), self.tr("Please select a spritesheet first.")
            )
            return

        spritesheet_name = current_spritesheet_item.text()
        animation_name = current_item.text()
        full_anim_name = "{spritesheet}/{animation}".format(
            spritesheet=spritesheet_name, animation=animation_name
        )

        def store_settings(settings):
            """Callback to store animation settings."""
            self.parent_app.settings_manager.animation_settings[full_anim_name] = settings

        try:
            from gui.override_settings_window import OverrideSettingsWindow

            dialog = OverrideSettingsWindow(
                self.parent_app,
                full_anim_name,
                "animation",
                self.parent_app.settings_manager,
                store_settings,
                self.parent_app,
            )
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(
                self,
                self.tr("Error"),
                self.tr("Could not open animation settings: {error}").format(error=str(e)),
            )

    def preview_selected_animation(self):
        """Preview the selected animation using the new preview window."""
        if not self.parent_app:
            return

        current_item = self.listbox_data.currentItem()
        if not current_item:
            QMessageBox.information(
                self, self.tr("Error"), self.tr("Please select an animation first.")
            )
            return

        # Get the selected spritesheet
        current_spritesheet_item = self.listbox_png.currentItem()
        if not current_spritesheet_item:
            QMessageBox.information(
                self, self.tr("Error"), self.tr("Please select a spritesheet first.")
            )
            return

        spritesheet_name = current_spritesheet_item.text()
        animation_name = current_item.text()

        try:
            # Get the file paths
            spritesheet_path = current_spritesheet_item.data(Qt.ItemDataRole.UserRole)
            if not spritesheet_path:
                QMessageBox.warning(
                    self, self.tr("Preview Error"), self.tr("Could not find spritesheet file path.")
                )
                return

            # Find the metadata file
            metadata_path = None
            if spritesheet_name in self.parent_app.data_dict:
                data_files = self.parent_app.data_dict[spritesheet_name]
                if "xml" in data_files:
                    metadata_path = data_files["xml"]
                elif "txt" in data_files:
                    metadata_path = data_files["txt"]

            # Use parent app's preview functionality
            self.parent_app.preview_animation_with_paths(
                spritesheet_path, metadata_path, animation_name
            )

        except Exception as e:
            QMessageBox.warning(
                self,
                self.tr("Preview error"),
                self.tr("Could not preview animation: {error}").format(error=str(e)),
            )

    # === Settings and UI State Management ===

    def update_ui_state(self, *args):
        """Updates the UI state based on current selections and settings."""
        if not self.parent_app:
            return

        both_export_unchecked = not (
            self.animation_export_group.isChecked() or self.frame_export_group.isChecked()
        )
        self.start_process_button.setEnabled(not both_export_unchecked)

        has_spritesheet_selected = self.listbox_png.currentItem() is not None
        self.override_spritesheet_settings_button.setEnabled(has_spritesheet_selected)

        has_animation_selected = self.listbox_data.currentItem() is not None
        self.override_animation_settings_button.setEnabled(has_animation_selected)

    def on_animation_format_change(self):
        """Handles animation format selection changes."""
        if not self.parent_app:
            return

        format_index = self.animation_format_combobox.currentIndex()

        # Update UI based on format capabilities (GIF is index 0)
        if format_index == 0:  # GIF
            self.threshold_entry.setEnabled(True)
            # Find the threshold label and enable it
            for child in self.animation_export_group.children():
                if isinstance(child, QLabel) and "threshold" in child.objectName().lower():
                    child.setEnabled(True)
        else:
            self.threshold_entry.setEnabled(False)
            # Find the threshold label and disable it
            for child in self.animation_export_group.children():
                if isinstance(child, QLabel) and "threshold" in child.objectName().lower():
                    child.setEnabled(False)

    def on_frame_format_change(self):
        """Handles frame format selection changes."""
        if not self.parent_app:
            return

        # Update compression options based on format
        # This will need to be implemented when compression widgets are added
        pass

    def get_extraction_settings(self):
        """Get current extraction settings from the UI."""
        if not self.parent_app:
            return {}

        # Get format options directly from comboboxes using index mapping to avoid translation issues
        animation_format_map = ["GIF", "WebP", "APNG", "Custom FFMPEG"]
        frame_format_map = ["AVIF", "BMP", "DDS", "PNG", "TGA", "TIFF", "WebP"]
        frame_selection_map = ["All", "No duplicates", "First", "Last", "First, Last", "Custom"]
        crop_option_map = ["None", "Animation based", "Frame based"]
        filename_format_map = ["Standardized", "No spaces", "No special characters"]

        animation_format = animation_format_map[self.animation_format_combobox.currentIndex()]
        frame_format = frame_format_map[self.frame_format_combobox.currentIndex()]
        frame_selection = frame_selection_map[self.frame_selection_combobox.currentIndex()]
        crop_option = crop_option_map[self.cropping_method_combobox.currentIndex()]
        filename_format = filename_format_map[self.filename_format_combobox.currentIndex()]

        # Get export enable states from groupboxes
        animation_export = self.animation_export_group.isChecked()
        frame_export = self.frame_export_group.isChecked()

        # Get values from UI elements
        settings = {
            "animation_format": animation_format,
            "frame_format": frame_format,
            "animation_export": animation_export,
            "frame_export": frame_export,
            "fps": self.frame_rate_entry.value(),
            "delay": self.loop_delay_entry.value(),
            "period": self.min_period_entry.value(),
            "scale": self.scale_entry.value(),
            "threshold": self.threshold_entry.value() / 100.0,  # Convert % to 0-1 range
            "frame_scale": self.frame_scale_entry.value(),
            "frame_selection": frame_selection,
            "crop_option": crop_option,
            "prefix": self.filename_prefix_entry.text(),
            "suffix": self.filename_suffix_entry.text(),
            "filename_format": filename_format,
            "replace_rules": getattr(self.parent_app, "replace_rules", []),
            "var_delay": getattr(self.parent_app, "variable_delay", False),
            "fnf_idle_loop": getattr(self.parent_app, "fnf_idle_loop", False),
        }

        return settings

    def update_global_settings(self):
        """Updates the global settings from the GUI."""
        if not self.parent_app:
            return

        settings = self.get_extraction_settings()

        # Update settings manager
        for key, value in settings.items():
            self.parent_app.settings_manager.global_settings[key] = value

    def validate_extraction_inputs(self):
        """Validates the extraction inputs before starting process."""
        if not self.parent_app:
            return False, "No parent application"

        if self.input_dir_label.text() == self.tr("No input directory selected"):
            return False, self.tr("Please select an input directory first.")

        if self.output_dir_label.text() == self.tr("No output directory selected"):
            return False, self.tr("Please select an output directory first.")

        # Check if at least one export option is enabled
        if not (self.animation_export_group.isChecked() or self.frame_export_group.isChecked()):
            return False, self.tr("Please enable at least one export option (Animation or Frame).")

        # Check if there are spritesheets to process
        if self.listbox_png.count() == 0:
            return False, self.tr("No spritesheets found. Please select a directory with images.")

        return True, ""

    def get_spritesheet_list(self):
        """Get the list of spritesheets to process."""
        spritesheet_list = []
        for i in range(self.listbox_png.count()):
            item = self.listbox_png.item(i)
            if item:
                spritesheet_list.append(item.text())
        return spritesheet_list

    def check_for_unknown_atlases(self, spritesheet_list):
        """Check for atlases without metadata files (unknown atlases)."""
        if not self.parent_app:
            return False, []

        unknown_atlases = []
        input_directory = self.input_dir_label.text()

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

    def filter_unknown_atlases(self, unknown_atlases):
        """Remove unknown atlases from the spritesheet list."""
        if not self.parent_app:
            return

        for unknown_atlas in unknown_atlases:
            for i in range(self.listbox_png.count()):
                item = self.listbox_png.item(i)
                if item and item.text() == unknown_atlas:
                    self.listbox_png.takeItem(i)
                    break

        # Clear animation list since we removed spritesheets
        self.listbox_data.clear()

    def prepare_for_extraction(self):
        """Prepare the extraction process by validating inputs and updating settings."""
        if not self.parent_app:
            return False, "No parent application", []

        # Validate inputs
        is_valid, error_message = self.validate_extraction_inputs()
        if not is_valid:
            return False, error_message, []

        # Update global settings
        self.update_global_settings()

        # Get spritesheet list
        spritesheet_list = self.get_spritesheet_list()

        # Check for unknown atlases and handle user choice
        has_unknown, unknown_atlases = self.check_for_unknown_atlases(spritesheet_list)
        if has_unknown:
            from gui.unknown_atlas_warning_window import UnknownAtlasWarningWindow

            input_directory = self.input_dir_label.text()
            action = UnknownAtlasWarningWindow.show_warning(
                self.parent_app, unknown_atlases, input_directory
            )
            if action == "cancel":
                return False, "User cancelled due to unknown atlases", []
            elif action == "skip":
                self.filter_unknown_atlases(unknown_atlases)
                # Update spritesheet list after filtering
                spritesheet_list = self.get_spritesheet_list()

        return True, "", spritesheet_list

    def get_input_directory(self):
        """Get the input directory path."""
        return self.input_dir_label.text()

    def get_output_directory(self):
        """Get the output directory path."""
        return self.output_dir_label.text()

    def set_processing_state(self, is_processing):
        """Enable/disable UI elements during processing."""
        self.start_process_button.setEnabled(not is_processing)
        self.start_process_button.setText(
            self.tr("Processing...") if is_processing else self.tr("Start Process")
        )

        # Disable input controls during processing
        self.input_button.setEnabled(not is_processing)
        self.output_button.setEnabled(not is_processing)
        self.reset_button.setEnabled(not is_processing)
        self.animation_export_group.setEnabled(not is_processing)
        self.frame_export_group.setEnabled(not is_processing)
        self.cropping_method_combobox.setEnabled(not is_processing)
        self.filename_format_combobox.setEnabled(not is_processing)
        self.filename_prefix_entry.setEnabled(not is_processing)
        self.filename_suffix_entry.setEnabled(not is_processing)
