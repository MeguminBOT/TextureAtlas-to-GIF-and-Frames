#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget,
    QSpinBox,
    QFileDialog,
    QMessageBox,
    QComboBox,
    QLabel,
    QPushButton,
)
from PySide6.QtCore import QThread, Signal

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Import our own modules
from gui.generator.animation_tree_widget import AnimationTreeWidget
from parsers.xml_parser import XmlParser
from utils.utilities import Utilities

# Import the new generator system
from core.generator import AtlasGenerator, GeneratorOptions, get_available_algorithms

SUPPORTED_ROTATION_FORMATS = frozenset(
    {
        "starling-xml",
        "json-hash",
        "json-array",
        "aseprite",
        "texture-packer-xml",
        "spine",
        "phaser3",
        "plist",
        "paper2d",
    }
)

SUPPORTED_FLIP_FORMATS = frozenset({"starling-xml"})


class GeneratorWorker(QThread):
    """Worker thread for atlas generation."""

    progress_updated = Signal(int, int, str)
    generation_completed = Signal(dict)
    generation_failed = Signal(str)

    def __init__(self, input_frames, output_path, atlas_settings, current_version):
        super().__init__()
        self.input_frames = input_frames
        self.output_path = output_path
        self.atlas_settings = atlas_settings
        self.animation_groups = None
        self.current_version = current_version
        self.output_format = "starling-xml"

    def run(self):
        """Execute atlas generation in background thread."""
        try:
            if not self.animation_groups:
                self.generation_failed.emit("No animation groups provided")
                return

            # Build generator options from atlas_settings
            options = GeneratorOptions(
                algorithm=self.atlas_settings.get("preferred_algorithm", "maxrects"),
                heuristic=self.atlas_settings.get("heuristic_hint"),
                max_width=self.atlas_settings.get("max_size", 8192),
                max_height=self.atlas_settings.get("max_size", 8192),
                padding=self.atlas_settings.get("padding", 2),
                power_of_two=self.atlas_settings.get("power_of_2", False),
                allow_rotation=self.atlas_settings.get("allow_rotation", False),
                allow_flip=self.atlas_settings.get("allow_vertical_flip", False),
                export_format=self.output_format,
                compression_settings=self.atlas_settings.get("compression_settings"),
            )

            # Handle manual sizing
            if self.atlas_settings.get("atlas_size_method") == "manual":
                options.max_width = self.atlas_settings.get("forced_width", 8192)
                options.max_height = self.atlas_settings.get("forced_height", 8192)

            # Create generator and set progress callback
            generator = AtlasGenerator()
            generator.set_progress_callback(self.emit_progress)

            # Run generation
            result = generator.generate(
                animation_groups=self.animation_groups,
                output_path=self.output_path,
                options=options,
            )

            if result.success:
                self.generation_completed.emit(result.to_dict())
            else:
                error_msg = "; ".join(result.errors) if result.errors else "Unknown error"
                self.generation_failed.emit(error_msg)

        except Exception as e:
            self.generation_failed.emit(f"Generation error: {e}")

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

        self.APP_NAME = Utilities.APP_NAME
        self.ALL_FILES_FILTER = f"{self.tr('All files')} (*.*)"

        # Combined image formats - used for both input and output
        self.IMAGE_FORMATS = {
            ".png": "PNG",
            ".bmp": "BMP",
            ".dds": "DDS",
            ".jpeg": "JPEG",
            ".jpg": "JPEG",
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

        # Initialize heuristic combo for current algorithm
        self.on_algorithm_changed(self.packer_method_combobox.currentText())

        # Initialize atlas sizing state
        self.on_atlas_size_method_changed(self.atlas_size_method_combobox.currentText())

        # Initialize rotation/flip checkboxes based on selected format
        self._update_rotation_flip_state()

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
        self.allow_rotation_check = self.ui.allow_rotation_check
        self.allow_flip_check = self.ui.allow_flip_check

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
        self.image_format_combo.currentTextChanged.connect(self.on_format_change)
        self.atlas_type_combo.currentIndexChanged.connect(
            self._update_rotation_flip_state
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
        """Populate the packer combo box with available algorithms from the registry."""
        # Get algorithms from the new packer registry
        algorithms = get_available_algorithms()

        # Add a few legacy/convenience options at the top
        algorithm_options = [
            ("Automatic (Best Fit)", "auto"),
        ]

        # Add registered algorithms
        for algo in algorithms:
            display_name = algo.get("display_name", algo["name"].title())
            algorithm_options.append((display_name, algo["name"]))

        self.packer_method_combobox.blockSignals(True)
        self.packer_method_combobox.clear()
        for label, key in algorithm_options:
            self.packer_method_combobox.addItem(label, key)
        self.packer_method_combobox.setCurrentIndex(0)
        self.packer_method_combobox.blockSignals(False)

    def _setup_heuristic_combo(self):
        """Create and insert the heuristic combo box and compression button."""
        # Create label and combo box for heuristic selection
        self.heuristic_label = QLabel(self.tr("Heuristic"))
        self.heuristic_combobox = QComboBox()
        self.heuristic_combobox.setMinimumWidth(140)

        # Create compression settings button
        self.compression_settings_button = QPushButton(self.tr("Compression Settings..."))
        self.compression_settings_button.setToolTip(
            self.tr("Configure format-specific compression options for the output image")
        )
        self.compression_settings_button.clicked.connect(self.show_compression_settings)

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
                            # Insert compression button in row 8
                            layout.addWidget(self.compression_settings_button, 8, 2)
                            inserted = True
                            break
                    if inserted:
                        break

        if not inserted:
            # Fallback: just hide if we can't find the layout
            self.heuristic_label.setVisible(False)
            self.heuristic_combobox.setVisible(False)
            self.compression_settings_button.setVisible(False)

    def _get_heuristic_options(self, algorithm_key: str):
        """Return (label, key) tuples for the given algorithm's heuristics.

        Always includes "Auto (Best Result)" as the first option, which
        will try all heuristics and pick the one with best efficiency.
        """
        # Get heuristics from the packer registry
        from packers import get_heuristics_for_algorithm

        heuristics = get_heuristics_for_algorithm(algorithm_key)

        # Fallback for 'auto' algorithm - show maxrects heuristics
        if not heuristics and algorithm_key == "auto":
            heuristics = get_heuristics_for_algorithm("maxrects")

        if heuristics:
            # Start with Auto option, then add algorithm-specific heuristics
            options = [(self.tr("Auto (Best Result)"), "auto")]
            options.extend([(display, key) for key, display in heuristics])
            return options

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
            ("Sparrow/Starling XML", "starling-xml", ".xml"),
            ("JSON Hash", "json-hash", ".json"),
            ("JSON Array", "json-array", ".json"),
            ("Aseprite JSON", "aseprite", ".json"),
            ("TexturePacker XML", "texture-packer-xml", ".xml"),
            ("Spine Atlas", "spine", ".atlas"),
            ("Phaser 3 JSON", "phaser3", ".json"),
            ("CSS Spritesheet", "css", ".css"),
            ("Plain Text", "txt", ".txt"),
            ("Plist (Cocos2d)", "plist", ".plist"),
            ("UIKit Plist", "uikit-plist", ".plist"),
            ("Godot Atlas", "godot", ".tpsheet"),
            ("Egret2D JSON", "egret2d", ".json"),
            ("Paper2D (Unreal)", "paper2d", ".paper2dsprites"),
            ("Unity TexturePacker", "unity", ".tpsheet"),
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
        if "max" in text:
            return "maxrects"
        if "guillotine" in text:
            return "guillotine"
        else:
            pass

    def on_algorithm_changed(self, _text):
        """Handle packer algorithm selection change."""
        key = self._current_algorithm_key()
        # Update heuristic combo box based on selected algorithm
        self._update_heuristic_combo(key)

    def _update_rotation_flip_state(self):
        """Update rotation and flip checkboxes based on selected atlas format.

        Enables/disables checkboxes based on format support and shows warnings
        for non-standard features.
        """
        format_key, _ = self._get_selected_export_format()

        # Check format support for rotation
        supports_rotation = format_key in SUPPORTED_ROTATION_FORMATS
        self.allow_rotation_check.setEnabled(supports_rotation)
        if supports_rotation:
            self.allow_rotation_check.setToolTip(
                self.tr(
                    "Allow the packer to rotate sprites 90° clockwise for tighter packing."
                )
            )
        else:
            self.allow_rotation_check.setChecked(False)
            self.allow_rotation_check.setToolTip(
                self.tr("Rotation is not supported by {0} format.").format(format_key)
            )

        # Check format support for flip (only starling-xml with HaxeFlixel)
        supports_flip = format_key in SUPPORTED_FLIP_FORMATS
        self.allow_flip_check.setEnabled(supports_flip)
        if supports_flip:
            self.allow_flip_check.setToolTip(
                self.tr(
                    "Allow the packer to flip sprites for tighter packing.\n\n"
                    "Warning: This is a non-standard extension only supported by HaxeFlixel.\n"
                    "Most Starling/Sparrow implementations will ignore flip attributes."
                )
            )
        else:
            self.allow_flip_check.setChecked(False)
            self.allow_flip_check.setToolTip(
                self.tr(
                    "Flip is not supported by {0} format.\n"
                    "Only Sparrow/Starling XML with HaxeFlixel supports flip attributes."
                ).format(format_key)
            )

    def _determine_algorithm_hint(self):
        return self._current_algorithm_key()

    def _get_selected_heuristic(self):
        """Get the currently selected heuristic key from the combo box."""
        if hasattr(self, "heuristic_combobox") and self.heuristic_combobox.isEnabled():
            return self.heuristic_combobox.currentData()
        return None

    def show_compression_settings(self):
        """Show the compression settings dialog for the current image format."""
        try:
            from gui.extractor.compression_settings_window import (
                CompressionSettingsWindow,
            )

            # Get current image format from the combo box
            current_format = self.image_format_combo.currentText().upper()

            # Get settings_manager and app_config from main app if available
            settings_manager = None
            app_config = None
            if hasattr(self.main_app, "settings_manager"):
                settings_manager = self.main_app.settings_manager
            if hasattr(self.main_app, "app_config"):
                app_config = self.main_app.app_config

            dialog = CompressionSettingsWindow(
                parent=self,
                settings_manager=settings_manager,
                app_config=app_config,
                current_format=current_format,
            )
            dialog.exec()

        except Exception as e:
            QMessageBox.warning(
                self,
                self.APP_NAME,
                self.tr("Could not open compression settings: {0}").format(str(e)),
            )

    def _get_compression_settings(self):
        """Get compression settings for the current image format.

        Returns a dict of format-specific compression options.
        """
        current_format = self.image_format_combo.currentText().upper()
        settings = {}

        # Try to get settings from app_config (compression settings are stored there)
        if hasattr(self.main_app, "app_config"):
            app_config = self.main_app.app_config
            if hasattr(app_config, "get_format_compression_settings"):
                settings = app_config.get_format_compression_settings(current_format) or {}

        return settings

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

    def on_animation_added(self, animation_name):
        """Handle new animation group added."""
        self.update_frame_info()
        self.update_generate_button_state()

    def on_animation_removed(self, animation_name):
        """Handle animation group removed."""
        self.update_frame_info()
        self.update_generate_button_state()

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

        # Get rotation/flip settings from checkboxes
        allow_rotation = self.allow_rotation_check.isChecked()
        allow_vertical_flip = self.allow_flip_check.isChecked()

        if method == "Automatic":
            atlas_settings = {
                "padding": self.padding_spin.value(),
                "power_of_2": self.power_of_2_check.isChecked(),
                "allow_rotation": allow_rotation,
                "allow_vertical_flip": allow_vertical_flip,
                "atlas_size_method": "automatic",
                "preferred_algorithm": algorithm_hint,
                "heuristic_hint": heuristic_hint,
            }
        elif method == "MinMax":
            atlas_settings = {
                "max_size": self.atlas_size_spinbox_2.value(),
                "min_size": self.atlas_size_spinbox_1.value(),
                "padding": self.padding_spin.value(),
                "power_of_2": self.power_of_2_check.isChecked(),
                "allow_rotation": allow_rotation,
                "allow_vertical_flip": allow_vertical_flip,
                "atlas_size_method": "minmax",
                "preferred_algorithm": algorithm_hint,
                "heuristic_hint": heuristic_hint,
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
                "allow_rotation": allow_rotation,
                "allow_vertical_flip": allow_vertical_flip,
                "atlas_size_method": "manual",
                "forced_width": self.atlas_size_spinbox_1.value(),
                "forced_height": self.atlas_size_spinbox_2.value(),
                "preferred_algorithm": algorithm_hint,
                "heuristic_hint": heuristic_hint,
            }
        else:
            # Fallback to automatic
            atlas_settings = {
                "padding": self.padding_spin.value(),
                "power_of_2": self.power_of_2_check.isChecked(),
                "allow_rotation": allow_rotation,
                "allow_vertical_flip": allow_vertical_flip,
                "atlas_size_method": "automatic",
                "preferred_algorithm": algorithm_hint,
                "heuristic_hint": heuristic_hint,
            }

        # Add compression settings to atlas_settings
        atlas_settings["compression_settings"] = self._get_compression_settings()

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

    def on_atlas_size_method_changed(self, method_text):
        """Handle atlas size method change."""
        if method_text == "Automatic":
            # Grey out spinboxes while automatic sizing is selected
            self.atlas_size_spinbox_1.setEnabled(False)
            self.atlas_size_spinbox_2.setEnabled(False)

            # Change labels
            self.atlas_size_label_1.setText(self.tr("Width"))
            self.atlas_size_label_2.setText(self.tr("Height"))

            self.log_text.append(
                self.tr("Atlas sizing: Automatic mode selected.")
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
