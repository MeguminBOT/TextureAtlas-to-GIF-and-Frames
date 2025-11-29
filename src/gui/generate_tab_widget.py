#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget,
    QSpinBox,
    QFileDialog,
    QMessageBox,
    QComboBox,
    QLabel,
)
from PySide6.QtCore import QThread, Signal

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Import our own modules
from core.generator import SparrowAtlasGenerator, AtlasSettings
from gui.generator.animation_tree_widget import AnimationTreeWidget
from parsers.xml_parser import XmlParser
from utils.utilities import Utilities


class GeneratorWorker(QThread):
    """Worker thread for atlas generation process."""

    progress_updated = Signal(int, int, str)  # current, total, message
    generation_completed = Signal(dict)  # results dictionary
    generation_failed = Signal(str)  # error message

    def __init__(self, input_frames, output_path, atlas_settings, current_version):
        super().__init__()
        self.input_frames = input_frames
        self.output_path = output_path
        self.atlas_settings = atlas_settings
        self.animation_groups = None  # Will be set by the caller
        self.current_version = current_version
        self.output_format = "starling-xml"  # Default format

    def run(self):
        try:
            generator = SparrowAtlasGenerator(progress_callback=self.emit_progress)

            # Create AtlasSettings from the atlas_settings dict
            settings = AtlasSettings(
                max_size=self.atlas_settings.get("max_size", 4096),
                min_size=self.atlas_settings.get("min_size", 128),
                padding=self.atlas_settings.get("padding", 2),
                power_of_2=self.atlas_settings.get("power_of_2", True),
                optimization_level=self.atlas_settings.get("optimization_level", 5),
                allow_rotation=self.atlas_settings.get("allow_rotation", True),
                allow_vertical_flip=self.atlas_settings.get(
                    "allow_vertical_flip", False
                ),
                algorithm_hint=self.atlas_settings.get("preferred_algorithm"),
                heuristic_hint=self.atlas_settings.get("heuristic_hint"),
                optimization_mode_index=self.atlas_settings.get(
                    "optimization_mode_index", 0
                ),
                preferred_width=self.atlas_settings.get("preferred_width"),
                preferred_height=self.atlas_settings.get("preferred_height"),
                forced_width=self.atlas_settings.get("forced_width"),
                forced_height=self.atlas_settings.get("forced_height"),
            )

            # Use animation groups if available, otherwise create default
            if self.animation_groups:
                animation_groups = self.animation_groups
            else:
                animation_groups = {"Animation_01": self.input_frames}

            # Generate atlas with selected output format
            results = generator.generate_atlas(
                animation_groups,
                self.output_path,
                settings,
                self.current_version,
                output_format=self.output_format,
            )

            if results["success"]:
                self.generation_completed.emit(results)
            else:
                self.generation_failed.emit(results["error"])

        except Exception as e:
            self.generation_failed.emit(str(e))

    def emit_progress(self, current, total, message=""):
        """Thread-safe progress emission."""
        self.progress_updated.emit(current, total, message)


class GenerateTabWidget(QWidget):
    """Widget containing all Generate tab functionality."""

    # Constants

    def __init__(self, ui, parent=None):
        super().__init__(parent)
        self.main_app = parent
        self.ui = ui
        self.input_frames = []
        self.output_path = ""
        self.worker = None
        self.animation_groups = {}
        self.atlas_settings = {}
        self._initial_mode_index = 0
        self._algorithm_slider_initialized = False
        self._mode_by_algorithm = {}

        self.APP_NAME = Utilities.APP_NAME
        self.ALL_FILES_FILTER = f"{self.tr('All files')} (*.*)"

        # Combined image formats - used for both input and output
        self.IMAGE_FORMATS = {
            ".bmp": "BMP",
            ".dds": "DDS",
            ".jpeg": "JPEG",
            ".jpg": "JPEG",
            ".png": "PNG",
            ".tga": "TGA",
            ".tiff": "TIFF",
            ".webp": "WebP",
        }

        # Data formats for spritesheet metadata
        self.DATA_FORMATS = {".xml", ".XML", ".txt", ".TXT", ".json", ".JSON"}

        # Commonly used format constants
        self.PNG_FORMAT = ".png"
        self.PNG_FORMAT_NAME = "PNG"
        self.JPEG_FORMAT_NAME = "JPEG"

        self.bind_ui_elements()
        self.setup_custom_widgets()
        self.setup_connections()
        self._configure_packer_combo()
        self._configure_atlas_type_combo()

        # Initialize slider/algorithm state before size wiring
        self.on_algorithm_changed(self.packer_method_combobox.currentText())

        # Initialize atlas sizing state
        self.on_atlas_size_method_changed(self.atlas_size_method_combobox.currentText())

    @property
    def INPUT_FORMATS(self):
        """Backward compatibility property for input formats."""
        return set(self.IMAGE_FORMATS.keys())

    @property
    def OUTPUT_FORMATS(self):
        """Generate output formats list from IMAGE_FORMATS."""
        formats = []
        for ext, name in self.IMAGE_FORMATS.items():
            if ext.startswith("."):
                pattern = f"*{ext}"
                formats.append((name, pattern))
        return formats

    def tr(self, text):
        """Translation helper method."""
        from PySide6.QtCore import QCoreApplication

        return QCoreApplication.translate(self.__class__.__name__, text)

    def get_image_file_filter(self):
        """Generate file filter string for image files."""
        # Create the extensions string from the IMAGE_FORMATS constant
        extensions = " ".join(f"*{ext}" for ext in sorted(self.IMAGE_FORMATS.keys()))
        image_filter = self.tr("Image files ({0})").format(extensions)
        return f"{image_filter};;{self.ALL_FILES_FILTER}"

    def get_atlas_image_file_filter(self):
        """Generate file filter string for atlas image files (all supported formats)."""
        # Create the extensions string from the IMAGE_FORMATS constant
        extensions = " ".join(f"*{ext}" for ext in sorted(self.IMAGE_FORMATS.keys()))
        atlas_filter = self.tr("Atlas image files ({0})").format(extensions)
        return f"{atlas_filter};;{self.ALL_FILES_FILTER}"

    def get_data_file_filter(self):
        """Generate file filter string for spritesheet data files."""
        extensions = " ".join(f"*{ext}" for ext in sorted(self.DATA_FORMATS))
        data_filter = self.tr("Spritesheet data files ({0})").format(extensions)
        return f"{data_filter};;{self.ALL_FILES_FILTER}"

    def get_xml_file_filter(self):
        """Generate file filter string for XML files (backward compatibility)."""
        return self.get_data_file_filter()

    def get_output_file_filter(self):
        """Generate file filter string for output formats."""
        format_filters = []
        for format_name, pattern in self.OUTPUT_FORMATS:
            format_filters.append(f"{format_name} {self.tr('files')} ({pattern})")

        # Join all format filters and add the all files filter
        return ";;".join(format_filters + [self.ALL_FILES_FILTER])

    def bind_ui_elements(self):
        """Bind to UI elements from the compiled UI."""
        # File management buttons
        self.add_files_button = self.ui.add_files_button
        self.add_directory_button = self.ui.add_directory_button
        self.add_animation_button = self.ui.add_animation_button
        self.add_existing_atlas_button = self.ui.add_existing_atlas_button
        self.clear_frames_button = self.ui.clear_frames_button

        # Frame info
        self.frame_info_label = self.ui.frame_info_label

        # Atlas settings
        self.atlas_size_method_combobox = self.ui.atlas_size_method_combobox
        self.atlas_size_spinbox_1 = self.ui.atlas_size_spinbox_1
        self.atlas_size_spinbox_2 = self.ui.atlas_size_spinbox_2
        self.atlas_size_label_1 = self.ui.atlas_size_label_1
        self.atlas_size_label_2 = self.ui.atlas_size_label_2
        self.padding_spin = self.ui.padding_spin
        self.power_of_2_check = self.ui.power_of_2_check
        self.speed_optimization_slider = self.ui.speed_optimization_slider
        self.speed_optimization_value_label = self.ui.speed_optimization_value_label

        # Output format
        self.image_format_combo = self.ui.image_format_combo
        self.atlas_type_combo = self.ui.atlas_type_combo
        self.packer_method_combobox = self.ui.packer_method_combobox

        # Generate button
        self.generate_button = self.ui.generate_button

        # Progress
        self.progress_bar = self.ui.progress_bar
        self.status_label = self.ui.status_label
        self.log_text = self.ui.log_text

    def setup_custom_widgets(self):
        """Set up custom widgets that need to replace placeholders."""
        self.animation_tree = AnimationTreeWidget()
        self.animation_tree.setMinimumHeight(200)

        placeholder = self.ui.animation_tree_placeholder
        layout = placeholder.parent().layout()

        index = layout.indexOf(placeholder)

        layout.removeWidget(placeholder)
        placeholder.setParent(None)
        layout.insertWidget(index, self.animation_tree)

        self.jpeg_quality_spin = QSpinBox()
        self.jpeg_quality_spin.setRange(1, 100)
        self.jpeg_quality_spin.setValue(95)
        self.jpeg_quality_spin.setEnabled(False)

        # Create heuristic selection combo box and label
        self._setup_heuristic_combo()

    def setup_connections(self):
        """Set up signal-slot connections."""
        # File management
        self.add_files_button.clicked.connect(self.add_files)
        self.add_directory_button.clicked.connect(self.add_directory)
        self.add_animation_button.clicked.connect(self.add_animation_group)
        self.add_existing_atlas_button.clicked.connect(self.add_existing_atlas)
        self.clear_frames_button.clicked.connect(self.clear_frames)

        # Animation tree signals
        self.animation_tree.animation_added.connect(self.on_animation_added)
        self.animation_tree.animation_removed.connect(self.on_animation_removed)
        self.animation_tree.frame_order_changed.connect(self.update_frame_info)

        # Settings
        self.atlas_size_method_combobox.currentTextChanged.connect(
            self.on_atlas_size_method_changed
        )
        self.atlas_size_spinbox_1.valueChanged.connect(self.update_atlas_size_estimates)
        self.atlas_size_spinbox_2.valueChanged.connect(self.update_atlas_size_estimates)
        self.power_of_2_check.toggled.connect(self.update_atlas_size_estimates)
        self.padding_spin.valueChanged.connect(self.update_atlas_size_estimates)
        self.image_format_combo.currentTextChanged.connect(self.on_format_change)
        self.speed_optimization_slider.valueChanged.connect(
            self.on_speed_slider_changed
        )
        self.packer_method_combobox.currentTextChanged.connect(
            self.on_algorithm_changed
        )

        # Generation
        self.generate_button.clicked.connect(self.generate_atlas)

    def add_files(self):
        """Add individual files to a new animation group."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            self.tr("Select frames"),
            "",
            self.get_image_file_filter(),
        )

        if files:
            self.add_frames_to_new_animation(files)

    def add_directory(self):
        """Add all images from a directory to the frame list."""
        directory = QFileDialog.getExistingDirectory(
            self, self.tr("Select directory with frame images"), ""
        )

        if directory:
            directory_path = Path(directory)

            subfolders = [item for item in directory_path.iterdir() if item.is_dir()]

            if subfolders:
                animations_created = 0
                for subfolder in subfolders:
                    files = []
                    for ext in self.IMAGE_FORMATS.keys():
                        files.extend(subfolder.glob(f"*{ext}"))
                        files.extend(subfolder.glob(f"*{ext.upper()}"))

                    if files:
                        animation_name = subfolder.name
                        new_animation_item = self.animation_tree.add_animation_group(
                            animation_name
                        )
                        actual_animation_name = new_animation_item.text(0)

                        for file_path in files:
                            if not self.is_frame_already_added(str(file_path)):
                                self.animation_tree.add_frame_to_animation(
                                    actual_animation_name, str(file_path)
                                )
                                self.input_frames.append(str(file_path))

                        animations_created += 1

                if animations_created > 0:
                    QMessageBox.information(
                        self,
                        self.APP_NAME,
                        self.tr("Created {0} animation(s) from subfolders.").format(
                            animations_created
                        ),
                    )
                else:
                    QMessageBox.information(
                        self,
                        self.APP_NAME,
                        self.tr("No image files found in any subfolders."),
                    )
            else:
                files = []
                for ext in self.IMAGE_FORMATS.keys():
                    files.extend(directory_path.glob(f"*{ext}"))
                    files.extend(directory_path.glob(f"*{ext.upper()}"))

                if files:
                    self.add_frames_to_default_animation([str(f) for f in files])
                else:
                    QMessageBox.information(
                        self,
                        self.APP_NAME,
                        self.tr("No image files found in the selected directory."),
                    )

            self.update_frame_info()
            self.update_generate_button_state()
            self.update_atlas_size_estimates()

    def add_animation_group(self):
        """Add a new animation group."""
        self.animation_tree.add_animation_group()
        self.update_frame_info()
        self.update_generate_button_state()

    def add_existing_atlas(self):
        """Add frames from an existing Sparrow/Starling atlas (image + data file)."""
        # First select the atlas image file (any supported format)
        atlas_file, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Select Atlas Image File"),
            "",
            self.get_atlas_image_file_filter(),
        )

        if not atlas_file:
            return

        atlas_path = Path(atlas_file)
        atlas_directory = atlas_path.parent
        atlas_name = atlas_path.stem

        # Look for corresponding data file (XML, TXT, JSON)
        data_file = None
        possible_data_names = [f"{atlas_name}{ext}" for ext in self.DATA_FORMATS]

        for data_name in possible_data_names:
            data_path = atlas_directory / data_name
            if data_path.exists():
                data_file = str(data_path)
                break

        # If no data file found automatically, ask user to select one
        if not data_file:
            data_file, _ = QFileDialog.getOpenFileName(
                self,
                self.tr("Select Atlas Data File"),
                str(atlas_directory),
                self.get_data_file_filter(),
            )

            if not data_file:
                QMessageBox.warning(
                    self,
                    self.APP_NAME,
                    self.tr(
                        "Both atlas image and data files are required to import an atlas."
                    ),
                )
                return

        try:
            # Parse the data file to extract frame information
            # Currently supports XML format, but can be extended for JSON/TXT formats
            sprites_data = XmlParser.parse_xml_data(data_file)

            if not sprites_data:
                QMessageBox.warning(
                    self,
                    self.APP_NAME,
                    self.tr("No frames found in the selected atlas data file."),
                )
                return

            # Load the atlas image
            if not PIL_AVAILABLE:
                QMessageBox.critical(
                    self,
                    self.APP_NAME,
                    self.tr(
                        "PIL (Pillow) is required to extract frames from atlas files."
                    ),
                )
                return

            atlas_image = Image.open(atlas_file)

            # Create a temporary directory for extracted frames
            import tempfile

            temp_dir = Path(tempfile.mkdtemp(prefix="atlas_frames_"))

            # Group frames by animation name
            animation_groups = {}
            for sprite_data in sprites_data:
                frame_name = sprite_data["name"]

                # Extract animation name from frame name
                # Common patterns: "animName_0000", "animName0001", "animName 0", "animName.0", etc.
                animation_name = self._extract_animation_name(frame_name)

                if animation_name not in animation_groups:
                    animation_groups[animation_name] = []
                animation_groups[animation_name].append(sprite_data)

            # Create animation groups and extract frames
            total_frames_added = 0
            for animation_name, frames_data in animation_groups.items():
                try:
                    # Create animation group
                    self.animation_tree.add_animation_group(animation_name)

                    # Sort frames by name to maintain proper order
                    frames_data.sort(key=lambda x: x["name"])

                    frames_added_to_animation = 0
                    for sprite_data in frames_data:
                        try:
                            # Extract frame from atlas
                            x, y = sprite_data["x"], sprite_data["y"]
                            width, height = sprite_data["width"], sprite_data["height"]
                            rotated = sprite_data.get("rotated", False)

                            # Extract the sprite region
                            sprite_region = atlas_image.crop(
                                (x, y, x + width, y + height)
                            )

                            # Handle rotation if needed
                            if rotated:
                                sprite_region = sprite_region.rotate(-90, expand=True)

                            # Save as temporary file
                            frame_filename = f"{sprite_data['name']}{self.PNG_FORMAT}"
                            # Sanitize filename
                            import re

                            frame_filename = re.sub(
                                r'[<>:"/\\|?*]', "_", frame_filename
                            )

                            temp_frame_path = temp_dir / frame_filename
                            sprite_region.save(temp_frame_path, self.PNG_FORMAT_NAME)

                            # Add to animation and input frames list
                            temp_frame_str = str(temp_frame_path)
                            if not self.is_frame_already_added(temp_frame_str):
                                self.animation_tree.add_frame_to_animation(
                                    animation_name, temp_frame_str
                                )
                                self.input_frames.append(temp_frame_str)
                                frames_added_to_animation += 1

                        except Exception as e:
                            print(f"Error extracting frame {sprite_data['name']}: {e}")
                            continue

                    total_frames_added += frames_added_to_animation
                    print(
                        f"Added {frames_added_to_animation} frames to animation '{animation_name}'"
                    )

                except Exception as e:
                    print(f"Error processing animation '{animation_name}': {e}")
                    continue

            # Close the atlas image
            atlas_image.close()

            if total_frames_added > 0:
                QMessageBox.information(
                    self,
                    self.APP_NAME,
                    self.tr(
                        "Successfully imported {0} frames from atlas '{1}' into {2} animations."
                    ).format(total_frames_added, atlas_name, len(animation_groups)),
                )

                # Store temp directory for cleanup later
                if not hasattr(self, "temp_atlas_dirs"):
                    self.temp_atlas_dirs = []
                self.temp_atlas_dirs.append(temp_dir)

                self.update_frame_info()
                self.update_generate_button_state()
                self.update_atlas_size_estimates()
            else:
                QMessageBox.information(
                    self,
                    self.APP_NAME,
                    self.tr("All frames from this atlas were already added."),
                )
                # Clean up empty temp directory
                import shutil

                shutil.rmtree(temp_dir, ignore_errors=True)

        except Exception as e:
            QMessageBox.critical(
                self,
                self.APP_NAME,
                self.tr("Error importing atlas: {0}").format(str(e)),
            )

    def _configure_packer_combo(self):
        """Populate the packer combo box with supported algorithms."""
        algorithm_options = [
            (self.tr("Growing (Auto Expand)"), "growing"),
            (self.tr("Grid (Legacy Fill)"), "grid"),
            (self.tr("Ordered Rows"), "ordered"),
            (self.tr("MaxRects (Tightest)"), "maxrects"),
            (self.tr("Guillotine"), "guillotine"),
            (self.tr("Shelf (FFDH)"), "shelf"),
            (self.tr("Skyline"), "skyline"),
            (self.tr("Hybrid Adaptive (Experimental)"), "hybrid"),
        ]

        self.packer_method_combobox.blockSignals(True)
        self.packer_method_combobox.clear()
        for label, key in algorithm_options:
            self.packer_method_combobox.addItem(label, key)
        self.packer_method_combobox.setCurrentIndex(0)
        self.packer_method_combobox.blockSignals(False)

    def _setup_heuristic_combo(self):
        """Create and insert the heuristic combo box after packer method combo."""
        # Create label and combo box for heuristic selection
        self.heuristic_label = QLabel(self.tr("Heuristic"))
        self.heuristic_combobox = QComboBox()
        self.heuristic_combobox.setMinimumWidth(140)

        # Find the packer_method_combobox's parent layout (should be a grid layout)
        packer_combo = self.packer_method_combobox
        parent_widget = packer_combo.parent()
        inserted = False
        if parent_widget and parent_widget.layout():
            layout = parent_widget.layout()
            # Try to find position of packer combo in grid layout
            from PySide6.QtWidgets import QGridLayout

            if isinstance(layout, QGridLayout):
                # Find where the packer combo is
                for row in range(layout.rowCount()):
                    for col in range(layout.columnCount()):
                        item = layout.itemAtPosition(row, col)
                        if item and item.widget() == packer_combo:
                            # Insert heuristic widgets in row 7 (after image_format at row 6)
                            layout.addWidget(self.heuristic_label, 7, 0)
                            layout.addWidget(self.heuristic_combobox, 7, 2)
                            inserted = True
                            break
                    if inserted:
                        break

        if not inserted:
            # Fallback: just hide if we can't find the layout
            self.heuristic_label.setVisible(False)
            self.heuristic_combobox.setVisible(False)

    def _get_heuristic_options(self, algorithm_key: str):
        """Return (label, key) tuples for the given algorithm's heuristics."""
        if algorithm_key == "maxrects":
            return [
                (self.tr("Best Short Side Fit (BSSF)"), "bssf"),
                (self.tr("Best Long Side Fit (BLSF)"), "blsf"),
                (self.tr("Best Area Fit (BAF)"), "baf"),
                (self.tr("Bottom-Left (BL)"), "bl"),
                (self.tr("Contact Point (CP)"), "cp"),
            ]
        elif algorithm_key == "guillotine":
            return [
                (self.tr("Best Short Side Fit (BSSF)"), "bssf"),
                (self.tr("Best Long Side Fit (BLSF)"), "blsf"),
                (self.tr("Best Area Fit (BAF)"), "baf"),
                (self.tr("Worst Area Fit (WAF)"), "waf"),
            ]
        elif algorithm_key == "shelf":
            return [
                (self.tr("Next Fit"), "next_fit"),
                (self.tr("First Fit"), "first_fit"),
                (self.tr("Best Width Fit"), "best_width"),
                (self.tr("Best Height Fit"), "best_height"),
                (self.tr("Worst Width Fit"), "worst_width"),
            ]
        elif algorithm_key == "skyline":
            return [
                (self.tr("Bottom-Left"), "bottom_left"),
                (self.tr("Min Waste"), "min_waste"),
                (self.tr("Best Fit"), "best_fit"),
            ]
        else:
            # Algorithms without heuristics
            return []

    def _update_heuristic_combo(self, algorithm_key: str):
        """Update the heuristic combo box based on selected algorithm."""
        options = self._get_heuristic_options(algorithm_key)

        self.heuristic_combobox.blockSignals(True)
        self.heuristic_combobox.clear()

        if options:
            for label, key in options:
                self.heuristic_combobox.addItem(label, key)
            self.heuristic_combobox.setCurrentIndex(0)
            self.heuristic_combobox.setEnabled(True)
            self.heuristic_label.setEnabled(True)
            self.heuristic_combobox.setVisible(True)
            self.heuristic_label.setVisible(True)
        else:
            self.heuristic_combobox.addItem(self.tr("N/A"), "")
            self.heuristic_combobox.setEnabled(False)
            self.heuristic_label.setEnabled(False)
            # Keep visible but disabled for consistency
            self.heuristic_combobox.setVisible(True)
            self.heuristic_label.setVisible(True)

        self.heuristic_combobox.blockSignals(False)

    def _configure_atlas_type_combo(self):
        """Populate the atlas type combo box with available export formats."""
        # Define format options with display names and internal keys
        # Format: (Display Name, format_key, file_extension)
        format_options = [
            (self.tr("Sparrow/Starling XML"), "starling-xml", ".xml"),
            (self.tr("JSON Hash"), "json-hash", ".json"),
            (self.tr("JSON Array"), "json-array", ".json"),
            (self.tr("TexturePacker XML"), "texture-packer-xml", ".xml"),
            (self.tr("Spine Atlas"), "spine", ".atlas"),
            (self.tr("Phaser 3 JSON"), "phaser3", ".json"),
            (self.tr("CSS Spritesheet"), "css", ".css"),
            (self.tr("Plain Text"), "txt", ".txt"),
            (self.tr("Plist (Cocos2d)"), "plist", ".plist"),
            (self.tr("UIKit Plist"), "uikit-plist", ".plist"),
            (self.tr("Godot Atlas"), "godot", ".tpsheet"),
            (self.tr("Egret2D JSON"), "egret2d", ".json"),
            (self.tr("Paper2D (Unreal)"), "paper2d", ".paper2dsprites"),
            (self.tr("Unity TexturePacker"), "unity", ".tpsheet"),
        ]

        self.atlas_type_combo.blockSignals(True)
        self.atlas_type_combo.clear()
        for display_name, format_key, extension in format_options:
            # Store both format_key and extension as tuple in userData
            self.atlas_type_combo.addItem(display_name, (format_key, extension))
        self.atlas_type_combo.setCurrentIndex(0)  # Default to Sparrow
        self.atlas_type_combo.blockSignals(False)

    def _get_selected_export_format(self):
        """Get the currently selected export format key and extension.

        Returns:
            tuple: (format_key, extension) for the selected format.
        """
        data = self.atlas_type_combo.currentData()
        if data:
            return data
        # Fallback to Sparrow if no data
        return ("starling-xml", ".xml")

    def _current_algorithm_key(self):
        data = self.packer_method_combobox.currentData()
        if data:
            return data
        text = self.packer_method_combobox.currentText().lower()
        if "grow" in text:
            return "growing"
        if "order" in text:
            return "ordered"
        if "max" in text:
            return "maxrects"
        if "hybrid" in text or "advanced" in text:
            return "hybrid"
        if "grid" in text:
            return "grid"
        if "guillotine" in text:
            return "guillotine"
        if "shelf" in text or "ffdh" in text:
            return "shelf"
        if "skyline" in text:
            return "skyline"
        return "growing"

    def _algorithm_level_specs(self):
        return {
            "grid": {
                "steps": [self.tr("Grid Fill")],
                "allow_rotation": [False],
                "allow_flip": [False],
            },
            "growing": {
                "steps": [
                    self.tr("Fast Fill"),
                    self.tr("Balanced Height"),
                    self.tr("Dense Packing"),
                ],
                "allow_rotation": [False, False, True],
                "allow_flip": [False, False, False],
            },
            "ordered": {
                "steps": [
                    self.tr("Preserve Rows"),
                    self.tr("Row Optimize"),
                ],
                "allow_rotation": [False, False],
                "allow_flip": [False, False],
            },
            "maxrects": {
                "steps": [
                    self.tr("Basic Fit"),
                    self.tr("Allow Rotation"),
                    self.tr("Tight Fit"),
                    self.tr("Aggressive"),
                ],
                "allow_rotation": [False, True, True, True],
                "allow_flip": [False, False, False, True],
            },
            "guillotine": {
                "steps": [
                    self.tr("Best Area Fit"),
                    self.tr("Allow Rotation"),
                    self.tr("Tight Packing"),
                ],
                "allow_rotation": [False, True, True],
                "allow_flip": [False, False, False],
            },
            "shelf": {
                "steps": [
                    self.tr("Height Fit"),
                    self.tr("Allow Rotation"),
                ],
                "allow_rotation": [False, True],
                "allow_flip": [False, False],
            },
            "skyline": {
                "steps": [
                    self.tr("Min Waste"),
                    self.tr("Allow Rotation"),
                    self.tr("Best Fit"),
                ],
                "allow_rotation": [False, True, True],
                "allow_flip": [False, False, False],
            },
            "hybrid": {
                "steps": [
                    self.tr("Analyzer"),
                    self.tr("Adaptive"),
                    self.tr("Experimental"),
                ],
                "allow_rotation": [False, True, True],
                "allow_flip": [False, True, True],
            },
        }

    def on_algorithm_changed(self, _text):
        key = self._current_algorithm_key()

        # Update heuristic combo box
        self._update_heuristic_combo(key)

        # Update speed optimization slider
        specs = self._algorithm_level_specs().get(key)
        if not specs:
            return
        max_value = len(specs["steps"]) - 1
        if key in self._mode_by_algorithm:
            cached_value = self._mode_by_algorithm[key]
        else:
            cached_value = self.speed_optimization_slider.value()
        cached_value = max(0, min(cached_value, max_value))

        self.speed_optimization_slider.blockSignals(True)
        self.speed_optimization_slider.setMaximum(max_value)
        if self.speed_optimization_slider.value() != cached_value:
            self.speed_optimization_slider.setValue(cached_value)
        self.speed_optimization_slider.blockSignals(False)

        self._mode_by_algorithm[key] = cached_value
        self.update_speed_opt_label(cached_value)

        if not self._algorithm_slider_initialized:
            self._initial_mode_index = cached_value
            self._algorithm_slider_initialized = True

    def on_speed_slider_changed(self, value):
        key = self._current_algorithm_key()
        self._mode_by_algorithm[key] = value
        self.update_speed_opt_label(value)

    def update_speed_opt_label(self, value):
        specs = self._algorithm_level_specs().get(self._current_algorithm_key())
        if not specs:
            self.speed_optimization_value_label.setText(
                self.tr("Level: {0}").format(value)
            )
            return
        steps = specs["steps"]
        value = max(0, min(value, len(steps) - 1))
        description = steps[value]
        self.speed_optimization_value_label.setText(
            f"{self.tr('Mode')} {value + 1}/{len(steps)} - {description}"
        )

    def get_optimization_settings(self, slider_value):
        """Convert slider value to optimization settings."""
        specs = self._algorithm_level_specs().get(self._current_algorithm_key())
        if not specs:
            return {}
        index = max(0, min(slider_value, len(specs["steps"]) - 1))
        return {
            "allow_rotation": specs["allow_rotation"][index],
            "allow_flip": specs["allow_flip"][index],
        }

    def _determine_algorithm_hint(self):
        return self._current_algorithm_key()

    def _get_selected_heuristic(self):
        """Get the currently selected heuristic key from the combo box."""
        if hasattr(self, "heuristic_combobox") and self.heuristic_combobox.isEnabled():
            return self.heuristic_combobox.currentData()
        return None

    def add_frames_to_default_animation(self, file_paths):
        """Add frame files to a default animation group."""
        # Create or use existing default animation
        default_animation = self.tr("New animation")

        # Add frames to the animation
        for file_path in file_paths:
            # Check if already in any animation
            if not self.is_frame_already_added(file_path):
                self.animation_tree.add_frame_to_animation(default_animation, file_path)
                self.input_frames.append(file_path)

        self.update_frame_info()
        self.update_generate_button_state()
        self.update_atlas_size_estimates()  # Update atlas size estimates when frames are added

    def add_frames_to_new_animation(self, file_paths):
        """Add frame files to a new animation group."""
        # Create a new animation group
        new_animation_item = self.animation_tree.add_animation_group()
        animation_name = new_animation_item.text(0)  # Get the actual name assigned

        # Add frames to the new animation
        for file_path in file_paths:
            # Check if already in any animation
            if not self.is_frame_already_added(file_path):
                self.animation_tree.add_frame_to_animation(animation_name, file_path)
                self.input_frames.append(file_path)

        self.update_frame_info()
        self.update_generate_button_state()
        self.update_atlas_size_estimates()  # Update atlas size estimates when frames are added

    def is_frame_already_added(self, file_path):
        """Check if a frame is already added to any animation."""
        animations = self.animation_tree.get_animation_groups()

        for animation_name, frames in animations.items():
            for frame in frames:
                if frame["path"] == file_path:
                    return True

        return False

    def clear_frames(self):
        """Clear all frames from all animations."""
        # Clean up temporary atlas directories
        if hasattr(self, "temp_atlas_dirs"):
            import shutil

            for temp_dir in self.temp_atlas_dirs:
                try:
                    if temp_dir.exists():
                        shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception as e:
                    print(f"Error cleaning up temp directory {temp_dir}: {e}")
            self.temp_atlas_dirs.clear()

        self.input_frames.clear()
        self.animation_tree.clear_all_animations()
        self.update_frame_info()
        self.update_generate_button_state()
        self.update_atlas_size_estimates()  # Update atlas size estimates when frames are cleared

    def on_animation_added(self, animation_name):
        """Handle new animation group added."""
        self.update_frame_info()
        self.update_generate_button_state()
        self.update_atlas_size_estimates()  # Update atlas size estimates when animations change

    def on_animation_removed(self, animation_name):
        """Handle animation group removed."""
        self.update_frame_info()
        self.update_generate_button_state()
        self.update_atlas_size_estimates()  # Update atlas size estimates when animations change

    def update_frame_info(self):
        """Update the frame info label."""
        total_frames = self.animation_tree.get_total_frame_count()
        animation_count = self.animation_tree.get_animation_count()

        if total_frames == 0:
            self.frame_info_label.setText(self.tr("No frames loaded"))
        else:
            self.frame_info_label.setText(
                self.tr("{0} animation(s), {1} frame(s) total").format(
                    animation_count, total_frames
                )
            )

    def update_generate_button_state(self):
        """Update the generate button enabled state."""
        has_frames = self.animation_tree.get_total_frame_count() > 0
        self.generate_button.setEnabled(has_frames)

    def on_format_change(self, format_text):
        """Handle image format change."""
        self.jpeg_quality_spin.setEnabled(format_text == self.JPEG_FORMAT_NAME)

    def generate_atlas(self):
        """Start the atlas generation process."""
        if self.animation_tree.get_total_frame_count() == 0:
            QMessageBox.warning(
                self,
                self.APP_NAME,
                self.tr("Please add frames before generating atlas."),
            )
            return

        # Open save dialog to select output path
        file_path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save Atlas As"), "", self.get_output_file_filter()
        )

        if not file_path:
            # User cancelled the save dialog
            return

        selected_path = Path(file_path)
        if selected_path.suffix:
            file_path = str(selected_path.with_suffix(""))

        self.output_path = file_path

        # Get all animations from the tree
        animations = self.animation_tree.get_animation_groups()

        # Convert to the format expected by the new generator
        animation_groups = {}
        for animation_name, frames in animations.items():
            # Sort frames by order
            sorted_frames = sorted(frames, key=lambda x: x["order"])
            animation_groups[animation_name] = [
                frame["path"] for frame in sorted_frames
            ]

        # Prepare settings for the new generator
        method = self.atlas_size_method_combobox.currentText()
        algorithm_hint = self._determine_algorithm_hint()
        heuristic_hint = self._get_selected_heuristic()
        level_settings = self.get_optimization_settings(
            self.speed_optimization_slider.value()
        )
        allow_rotation = level_settings.get("allow_rotation", False)
        allow_vertical_flip = level_settings.get("allow_flip", False)

        if method == "Automatic":
            # For automatic mode, calculate optimal sizes
            width_est, height_est = self.calculate_atlas_size_estimates()
            if width_est is None or height_est is None:
                # Fallback to reasonable defaults
                width_est, height_est = 1024, 1024

            atlas_settings = {
                "max_size": max(width_est, height_est) * 2,  # Give some headroom
                "min_size": min(width_est, height_est),
                "padding": self.padding_spin.value(),
                "power_of_2": self.power_of_2_check.isChecked(),
                "optimization_level": self.speed_optimization_slider.value(),
                "allow_rotation": allow_rotation,
                "allow_vertical_flip": allow_vertical_flip,
                "atlas_size_method": "automatic",
                "preferred_width": width_est,
                "preferred_height": height_est,
                "preferred_algorithm": algorithm_hint,
                "heuristic_hint": heuristic_hint,
                "optimization_mode_index": self.speed_optimization_slider.value(),
            }
        elif method == "MinMax":
            atlas_settings = {
                "max_size": self.atlas_size_spinbox_2.value(),
                "min_size": self.atlas_size_spinbox_1.value(),
                "padding": self.padding_spin.value(),
                "power_of_2": self.power_of_2_check.isChecked(),
                "optimization_level": self.speed_optimization_slider.value(),
                "allow_rotation": allow_rotation,
                "allow_vertical_flip": allow_vertical_flip,
                "atlas_size_method": "minmax",
                "preferred_algorithm": algorithm_hint,
                "heuristic_hint": heuristic_hint,
                "optimization_mode_index": self.speed_optimization_slider.value(),
            }
        elif method == "Manual":
            atlas_settings = {
                "max_size": max(
                    self.atlas_size_spinbox_1.value(), self.atlas_size_spinbox_2.value()
                ),
                "min_size": min(
                    self.atlas_size_spinbox_1.value(), self.atlas_size_spinbox_2.value()
                ),
                "padding": self.padding_spin.value(),
                "power_of_2": self.power_of_2_check.isChecked(),
                "optimization_level": self.speed_optimization_slider.value(),
                "allow_rotation": allow_rotation,
                "allow_vertical_flip": allow_vertical_flip,
                "atlas_size_method": "manual",
                "forced_width": self.atlas_size_spinbox_1.value(),
                "forced_height": self.atlas_size_spinbox_2.value(),
                "preferred_algorithm": algorithm_hint,
                "heuristic_hint": heuristic_hint,
                "optimization_mode_index": self.speed_optimization_slider.value(),
            }

            # Show warning for manual mode
            total_area = 0
            animations = self.animation_tree.get_animation_groups()
            for animation_name, frames in animations.items():
                for frame in frames:
                    try:
                        with Image.open(frame["path"]) as img:
                            width, height = img.size
                            total_area += (width + 2 * self.padding_spin.value()) * (
                                height + 2 * self.padding_spin.value()
                            )
                    except Exception:
                        continue

            atlas_area = (
                self.atlas_size_spinbox_1.value() * self.atlas_size_spinbox_2.value()
            )
            if (
                total_area > atlas_area * 0.8
            ):  # If frames use more than 80% of atlas space
                reply = QMessageBox.question(
                    self,
                    self.tr("Manual Size Warning"),
                    self.tr(
                        "The specified atlas size may not be large enough to fit all frames. Continue anyway?"
                    ),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.No:
                    return

        # Create a dummy input_frames list for the worker (for compatibility)
        all_input_frames = []
        for frames in animation_groups.values():
            all_input_frames.extend(frames)

        # Get app version from main app
        current_version = "2.0.0"  # Default fallback
        if hasattr(self.main_app, "current_version"):
            current_version = self.main_app.current_version

        # Get selected output format
        format_key, format_ext = self._get_selected_export_format()

        # Start generation in worker thread
        self.worker = GeneratorWorker(
            all_input_frames, self.output_path, atlas_settings, current_version
        )
        self.worker.animation_groups = (
            animation_groups  # Pass animation groups to worker
        )
        self.worker.output_format = format_key  # Set the output format
        self.worker.progress_updated.connect(self.on_progress_updated)
        self.worker.generation_completed.connect(self.on_generation_completed)
        self.worker.generation_failed.connect(self.on_generation_failed)

        # Update UI
        self.generate_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText(self.tr("Generating atlas..."))
        self.log_text.clear()

        self.worker.start()

    def on_progress_updated(self, current, total, message):
        """Handle progress updates."""
        if total > 0:
            self.progress_bar.setValue(int((current / total) * 100))
        self.status_label.setText(
            self.tr("Progress: {0}/{1} - {2}").format(current, total, message)
        )
        self.log_text.append(f"{message}")

    def on_generation_completed(self, results):
        """Handle successful generation completion."""
        self.progress_bar.setVisible(False)
        self.generate_button.setEnabled(True)

        # Show results
        message = self.tr("Atlas generated successfully!") + "\n\n"
        message += self.tr("Atlas: {0}").format(results["atlas_path"]) + "\n"
        message += (
            self.tr("Size: {0}x{1}").format(
                results["atlas_size"][0], results["atlas_size"][1]
            )
            + "\n"
        )
        message += self.tr("Frames: {0}").format(results["frames_count"]) + "\n"
        message += self.tr("Efficiency: {0:.1f}%").format(results["efficiency"]) + "\n"
        message += (
            self.tr("Format: {0}").format(self.atlas_type_combo.currentText()) + "\n"
        )
        message += self.tr("Metadata files: {0}").format(len(results["metadata_files"]))

        self.status_label.setText(self.tr("Generation completed successfully!"))
        self.log_text.append("\n" + "=" * 50)
        self.log_text.append(self.tr("GENERATION COMPLETED SUCCESSFULLY!"))
        self.log_text.append("=" * 50)
        self.log_text.append(message)

        QMessageBox.information(self, self.APP_NAME, message)

    def on_generation_failed(self, error_message):
        """Handle generation failure."""
        self.progress_bar.setVisible(False)
        self.generate_button.setEnabled(True)

        self.status_label.setText(self.tr("Generation failed!"))
        self.log_text.append("\n" + "=" * 50)
        self.log_text.append(self.tr("Generation failed!").upper())
        self.log_text.append("=" * 50)
        self.log_text.append(self.tr("Error: {0}").format(error_message))

        QMessageBox.critical(
            self,
            self.APP_NAME,
            self.tr("Atlas generation failed:\n\n{0}").format(error_message),
        )

    def calculate_atlas_size_estimates(self):
        """Calculate optimal atlas sizes based on input frames for display purposes."""
        animations = self.animation_tree.get_animation_groups()
        if not animations:
            return None, None

        frame_dimensions = []
        total_area = 0
        max_width = 0
        max_height = 0

        # Analyze all frames to get dimensions
        for animation_name, frames in animations.items():
            for frame in frames:
                try:
                    with Image.open(frame["path"]) as img:
                        width, height = img.size
                        frame_dimensions.append((width, height))
                        total_area += width * height
                        max_width = max(max_width, width)
                        max_height = max(max_height, height)
                except Exception:
                    # Skip invalid images
                    continue

        if not frame_dimensions:
            return None, None

        # Calculate required area with padding
        padding = self.padding_spin.value()

        # Auto-determine efficiency factor based on optimization level (same as generator)
        optimization_level = self.speed_optimization_slider.value()
        if optimization_level <= 3:
            efficiency_factor = 1.5  # More conservative for basic packing
        elif optimization_level <= 6:
            efficiency_factor = 1.3  # Balanced
        elif optimization_level <= 9:
            efficiency_factor = 1.2  # More aggressive
        else:
            efficiency_factor = 1.15  # Most aggressive for ultra optimization

        # Add padding to each frame's area
        padded_total_area = 0
        for width, height in frame_dimensions:
            padded_width = width + (2 * padding)
            padded_height = height + (2 * padding)
            padded_total_area += padded_width * padded_height

        # Apply efficiency factor (accounts for packing inefficiency)
        estimated_area = padded_total_area * efficiency_factor

        # Calculate minimum atlas size needed
        min_dimension = math.ceil(math.sqrt(estimated_area))

        # Ensure minimum atlas can fit the largest frame
        min_dimension = max(
            min_dimension, max_width + (2 * padding), max_height + (2 * padding)
        )

        # Round up to next power of 2 if power of 2 is enabled
        if self.power_of_2_check.isChecked():
            min_dimension = 2 ** math.ceil(math.log2(min_dimension))

        # For automatic mode, we'll use square dimensions
        # For display, assume roughly square but allow some variation
        width_estimate = min_dimension
        height_estimate = min_dimension

        # Try to make it slightly more rectangular if that's more efficient
        aspect_ratio = max_width / max_height if max_height > 0 else 1.0
        if aspect_ratio > 1.5:  # Wide frames
            width_estimate = int(min_dimension * 1.2)
            height_estimate = int(min_dimension * 0.8)
        elif aspect_ratio < 0.67:  # Tall frames
            width_estimate = int(min_dimension * 0.8)
            height_estimate = int(min_dimension * 1.2)

        # Apply power of 2 constraint if needed
        if self.power_of_2_check.isChecked():
            width_estimate = 2 ** math.ceil(math.log2(width_estimate))
            height_estimate = 2 ** math.ceil(math.log2(height_estimate))

        return width_estimate, height_estimate

    def update_atlas_size_estimates(self):
        """Update atlas size estimates based on current settings."""
        method = self.atlas_size_method_combobox.currentText()

        if method == "Automatic":
            width_est, height_est = self.calculate_atlas_size_estimates()

            if width_est is not None and height_est is not None:
                # Update the grayed out spinboxes with estimates
                self.atlas_size_spinbox_1.setValue(width_est)
                self.atlas_size_spinbox_2.setValue(height_est)

                # Update status in log
                animations = self.animation_tree.get_animation_groups()
                total_frames = sum(len(frames) for frames in animations.values())

                if total_frames > 0:
                    self.log_text.append(
                        self.tr(
                            "Auto-sizing: Estimated {0}x{1}px (based on {2} frames)"
                        ).format(width_est, height_est, total_frames)
                    )
            elif self.animation_tree.get_total_frame_count() > 0:
                self.log_text.append(
                    self.tr(
                        "Auto-sizing: Could not calculate sizes - image analysis failed"
                    )
                )

    def on_atlas_size_method_changed(self, method_text):
        """Handle atlas size method change."""
        if method_text == "Automatic":
            # Grey out spinboxes and show estimated values
            self.atlas_size_spinbox_1.setEnabled(False)
            self.atlas_size_spinbox_2.setEnabled(False)

            # Change labels
            self.atlas_size_label_1.setText(self.tr("Width"))
            self.atlas_size_label_2.setText(self.tr("Height"))

            # Update with estimates
            self.update_atlas_size_estimates()

            self.log_text.append(
                self.tr(
                    "Atlas sizing: Automatic mode enabled - size will be calculated automatically"
                )
            )

        elif method_text == "MinMax":
            # Enable spinboxes for min/max size input
            self.atlas_size_spinbox_1.setEnabled(True)
            self.atlas_size_spinbox_2.setEnabled(True)

            # Change labels
            self.atlas_size_label_1.setText(self.tr("Min size"))
            self.atlas_size_label_2.setText(self.tr("Max size"))

            # Set reasonable defaults if not already set
            if self.atlas_size_spinbox_1.value() == 0:
                self.atlas_size_spinbox_1.setValue(512)
            if self.atlas_size_spinbox_2.value() == 0:
                self.atlas_size_spinbox_2.setValue(2048)

            self.log_text.append(
                self.tr(
                    "Atlas sizing: MinMax mode enabled - atlas will be constrained between min and max sizes"
                )
            )

        elif method_text == "Manual":
            # Enable spinboxes for manual width/height input
            self.atlas_size_spinbox_1.setEnabled(True)
            self.atlas_size_spinbox_2.setEnabled(True)

            # Change labels
            self.atlas_size_label_1.setText(self.tr("Width"))
            self.atlas_size_label_2.setText(self.tr("Height"))

            # Set reasonable defaults if not already set
            if self.atlas_size_spinbox_1.value() == 0:
                self.atlas_size_spinbox_1.setValue(1024)
            if self.atlas_size_spinbox_2.value() == 0:
                self.atlas_size_spinbox_2.setValue(1024)

            self.log_text.append(
                self.tr(
                    "Atlas sizing: Manual mode enabled - exact dimensions will be forced (warning will be shown if frames don't fit)"
                )
            )

    def __del__(self):
        """Cleanup temporary directories when widget is destroyed."""
        if hasattr(self, "temp_atlas_dirs"):
            import shutil

            for temp_dir in self.temp_atlas_dirs:
                try:
                    if temp_dir.exists():
                        shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception:
                    pass  # Ignore errors during cleanup

    def _extract_animation_name(self, frame_name):
        """
        Extract animation name from frame name.

        Handles common patterns like:
        - "animName_0000" -> "animName"
        - "animName0001" -> "animName"
        - "animName 0" -> "animName"
        - "animName.0" -> "animName"
        - "animName-0" -> "animName"
        - "animName001" -> "animName"
        """
        import re

        # Remove file extension if present
        name = frame_name
        if "." in name:
            name = name.rsplit(".", 1)[0]

        # Pattern to match common frame numbering schemes
        # This regex captures everything before the frame number
        patterns = [
            r"^(.+?)_\d+$",  # name_0000
            r"^(.+?)\s+\d+$",  # name 0000
            r"^(.+?)\.\d+$",  # name.0000
            r"^(.+?)-\d+$",  # name-0000
            r"^(.+?)\d+$",  # name0000 (digits at the end)
        ]

        for pattern in patterns:
            match = re.match(pattern, name)
            if match:
                return match.group(1).strip()

        # If no pattern matches, return the original name (might be a single frame animation)
        return name
