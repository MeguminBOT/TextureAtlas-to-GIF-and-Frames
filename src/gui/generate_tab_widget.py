#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
from pathlib import Path
from PySide6.QtWidgets import QWidget, QSpinBox, QFileDialog, QMessageBox
from PySide6.QtCore import QThread, Signal

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from core.generator import SparrowAtlasGenerator, AtlasSettings
from gui.animation_tree_widget import AnimationTreeWidget
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
                efficiency_factor=self.atlas_settings.get("efficiency_factor", 1.3),
                allow_rotation=self.atlas_settings.get("allow_rotation", True),
            )

            # Use animation groups if available, otherwise create default
            if self.animation_groups:
                animation_groups = self.animation_groups
            else:
                animation_groups = {"Animation_01": self.input_frames}

            results = generator.generate_atlas(
                animation_groups, self.output_path, settings, self.current_version
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

        self.APP_NAME = Utilities.APP_NAME
        self.ALL_FILES_FILTER = f"{self.tr('All files')} (*.*)"
        self.INPUT_FORMATS = {".bmp", ".dds", ".jpeg", ".jpg", ".png", ".tga", ".tiff", ".webp"}
        self.OUTPUT_FORMATS = [
            ("PNG", "*.png"),
            ("JPEG", "*.jpg"),
            ("BMP", "*.bmp"),
            ("TIFF", "*.tiff"),
            ("WebP", "*.webp"),
            ("TGA", "*.tga"),
            ("DDS", "*.dds"),
        ]

        self.bind_ui_elements()
        self.setup_custom_widgets()
        self.setup_connections()

        # Initialize auto-sizing state
        self.on_auto_size_toggled(self.ui.auto_size_check.isChecked())

    def tr(self, text):
        """Translation helper method."""
        from PySide6.QtCore import QCoreApplication

        return QCoreApplication.translate(self.__class__.__name__, text)

    def get_image_file_filter(self):
        """Generate file filter string for image files."""
        # Create the extensions string from the constant
        extensions = " ".join(f"*{ext}" for ext in sorted(self.INPUT_FORMATS))
        image_filter = self.tr("Image files ({0})").format(extensions)
        return f"{image_filter};;{self.ALL_FILES_FILTER}"

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
        self.clear_frames_button = self.ui.clear_frames_button

        # Output
        self.output_path_button = self.ui.output_path_button
        self.output_path_label = self.ui.output_path_label

        # Frame info
        self.frame_info_label = self.ui.frame_info_label

        # Atlas settings
        self.auto_size_check = self.ui.auto_size_check
        self.max_size_combo = self.ui.max_size_combo
        self.min_size_combo = self.ui.min_size_combo
        self.padding_spin = self.ui.padding_spin
        self.power_of_2_check = self.ui.power_of_2_check
        self.efficiency_spin = self.ui.efficiency_spin
        self.speed_optimization_slider = self.ui.speed_optimization_slider
        self.speed_opt_value_label = self.ui.speed_opt_value_label

        # Output format
        self.image_format_combo = self.ui.image_format_combo
        self.atlas_type_combo = self.ui.atlas_type_combo

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

    def setup_connections(self):
        """Set up signal-slot connections."""
        # File management
        self.add_files_button.clicked.connect(self.add_files)
        self.add_directory_button.clicked.connect(self.add_directory)
        self.add_animation_button.clicked.connect(self.add_animation_group)
        self.clear_frames_button.clicked.connect(self.clear_frames)
        self.output_path_button.clicked.connect(self.select_output_path)

        # Animation tree signals
        self.animation_tree.animation_added.connect(self.on_animation_added)
        self.animation_tree.animation_removed.connect(self.on_animation_removed)
        self.animation_tree.frame_order_changed.connect(self.update_frame_info)

        # Settings
        self.auto_size_check.toggled.connect(self.on_auto_size_toggled)
        self.power_of_2_check.toggled.connect(self.update_auto_atlas_sizes)
        self.padding_spin.valueChanged.connect(self.update_auto_atlas_sizes)
        self.efficiency_spin.valueChanged.connect(self.update_auto_atlas_sizes)
        self.image_format_combo.currentTextChanged.connect(self.on_format_change)
        self.speed_optimization_slider.valueChanged.connect(self.update_speed_opt_label)

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
                    for ext in self.INPUT_FORMATS:
                        files.extend(subfolder.glob(f"*{ext}"))
                        files.extend(subfolder.glob(f"*{ext.upper()}"))

                    if files:
                        animation_name = subfolder.name
                        new_animation_item = self.animation_tree.add_animation_group(animation_name)
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
                        self, self.APP_NAME, self.tr("No image files found in any subfolders.")
                    )
            else:
                files = []
                for ext in self.INPUT_FORMATS:
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
            self.update_auto_atlas_sizes()

    def add_animation_group(self):
        """Add a new animation group."""
        self.animation_tree.add_animation_group()
        self.update_frame_info()
        self.update_generate_button_state()

    def update_speed_opt_label(self, value):
        """Update the speed optimization label based on slider value."""
        labels = {
            0: self.tr("Level: 0 (Ultra-Fast, Minimal Packing)"),
            1: self.tr("Level: 1 (Ultra-Fast, Tight Packing)"),
            2: self.tr("Level: 2 (Ultra-Fast, Reduced Padding)"),
            3: self.tr("Level: 3 (Fast, No Rotation)"),
            4: self.tr("Level: 4 (Fast, Basic Packing)"),
            5: self.tr("Level: 5 (Fast, Standard Packing)"),
            6: self.tr("Level: 6 (Balanced, Some Rotation)"),
            7: self.tr("Level: 7 (Balanced, Full Rotation)"),
            8: self.tr("Level: 8 (Optimized, Advanced)"),
            9: self.tr("Level: 9 (Optimized, Maximum)"),
            10: self.tr("Level: 10 (Ultra-Optimized, Slowest)"),
        }
        self.speed_opt_value_label.setText(labels.get(value, self.tr("Level: {0}").format(value)))

    def get_optimization_settings(self, slider_value):
        """Convert slider value to optimization settings."""
        if slider_value <= 2:
            # Ultra-fast mode - absolutely minimal optimization
            return {
                "use_numpy": False,
                "use_advanced_numpy": False,
                "orientation_optimization": False,
                "packing_strategy": "ultra_simple",
                "efficiency_factor": 1.05,
                "tight_packing": True,
                "use_multithreading": True,
            }
        elif slider_value <= 5:
            # Fast mode - minimal optimization
            return {
                "use_numpy": False,
                "use_advanced_numpy": False,
                "orientation_optimization": False,
                "packing_strategy": "simple",
                "efficiency_factor": 1.1,
                "tight_packing": True,
                "use_multithreading": True,
            }
        elif slider_value <= 7:
            # Balanced mode - moderate optimization
            return {
                "use_numpy": True,
                "use_advanced_numpy": False,
                "orientation_optimization": True,
                "packing_strategy": "balanced",
                "efficiency_factor": 1.2,
                "tight_packing": False,
                "use_multithreading": True,
            }
        else:
            # Optimized mode - full optimization
            return {
                "use_numpy": True,
                "use_advanced_numpy": True,
                "orientation_optimization": True,
                "packing_strategy": "advanced",
                "efficiency_factor": 1.3,
                "tight_packing": False,
                "use_multithreading": True,
            }

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
        self.update_auto_atlas_sizes()  # Update auto sizes when frames are added

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
        self.update_auto_atlas_sizes()  # Update auto sizes when frames are added

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
        self.input_frames.clear()
        self.animation_tree.clear_all_animations()
        self.update_frame_info()
        self.update_generate_button_state()
        self.update_auto_atlas_sizes()  # Update auto sizes when frames are cleared

    def on_animation_added(self, animation_name):
        """Handle new animation group added."""
        self.update_frame_info()
        self.update_generate_button_state()
        self.update_auto_atlas_sizes()  # Update auto sizes when animations change

    def on_animation_removed(self, animation_name):
        """Handle animation group removed."""
        self.update_frame_info()
        self.update_generate_button_state()
        self.update_auto_atlas_sizes()  # Update auto sizes when animations change

    def select_output_path(self):
        """Select output path for the atlas."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save Atlas As"), "", self.get_output_file_filter()
        )

        if file_path:
            self.output_path = file_path
            self.output_path_label.setText(self.tr("Output: {0}").format(Path(file_path).name))
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
        has_output_path = bool(self.output_path)

        can_generate = has_frames and has_output_path
        self.generate_button.setEnabled(can_generate)

    def on_format_change(self, format_text):
        """Handle image format change."""
        self.jpeg_quality_spin.setEnabled(format_text == "JPEG")

    def generate_atlas(self):
        """Start the atlas generation process."""
        if self.animation_tree.get_total_frame_count() == 0 or not self.output_path:
            QMessageBox.warning(
                self, self.APP_NAME, self.tr("Please add frames and select output path.")
            )
            return

        # Get all animations from the tree
        animations = self.animation_tree.get_animation_groups()

        # Convert to the format expected by the new generator
        animation_groups = {}
        for animation_name, frames in animations.items():
            # Sort frames by order
            sorted_frames = sorted(frames, key=lambda x: x["order"])
            animation_groups[animation_name] = [frame["path"] for frame in sorted_frames]

        # Prepare settings for the new generator
        atlas_settings = {
            "max_size": int(self.max_size_combo.currentText()),
            "min_size": int(self.min_size_combo.currentText()),
            "padding": self.padding_spin.value(),
            "power_of_2": self.power_of_2_check.isChecked(),
            "efficiency_factor": self.efficiency_spin.value(),
            "optimization_level": self.speed_optimization_slider.value(),
            "allow_rotation": self.speed_optimization_slider.value()
            > 5,  # Enable rotation for higher optimization
        }

        # Create a dummy input_frames list for the worker (for compatibility)
        all_input_frames = []
        for frames in animation_groups.values():
            all_input_frames.extend(frames)

        # Get app version from main app
        current_version = "2.0.0"  # Default fallback
        if hasattr(self.main_app, "current_version"):
            current_version = self.main_app.current_version

        # Start generation in worker thread
        self.worker = GeneratorWorker(
            all_input_frames, self.output_path, atlas_settings, current_version
        )
        self.worker.animation_groups = animation_groups  # Pass animation groups to worker
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
            self.tr("Size: {0}x{1}").format(results["atlas_size"][0], results["atlas_size"][1])
            + "\n"
        )
        message += self.tr("Frames: {0}").format(results["frames_count"]) + "\n"
        message += self.tr("Efficiency: {0:.1f}%").format(results["efficiency"]) + "\n"
        message += self.tr("Format: {0}").format(self.atlas_type_combo.currentText()) + "\n"
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
            self, self.APP_NAME, self.tr("Atlas generation failed:\n\n{0}").format(error_message)
        )

    def calculate_auto_atlas_sizes(self):
        """Calculate optimal min and max atlas sizes based on input frames."""
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
        efficiency_factor = self.efficiency_spin.value()

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
        min_dimension = max(min_dimension, max_width + (2 * padding), max_height + (2 * padding))

        # Round up to next power of 2 if power of 2 is enabled
        if self.power_of_2_check.isChecked():
            min_dimension = 2 ** math.ceil(math.log2(min_dimension))

        # Set minimum size (ensure it's within available options)
        available_min_sizes = [64, 128, 256, 512, 1024]
        min_size = min_dimension
        for size in available_min_sizes:
            if size >= min_dimension:
                min_size = size
                break
        else:
            min_size = available_min_sizes[-1]

        # Calculate maximum size (give some headroom)
        max_dimension = min_dimension * 2
        if self.power_of_2_check.isChecked():
            max_dimension = 2 ** math.ceil(math.log2(max_dimension))

        # Set maximum size (ensure it's within available options)
        available_max_sizes = [512, 1024, 2048, 4096, 8192]
        max_size = max_dimension
        for size in available_max_sizes:
            if size >= max_dimension:
                max_size = size
                break
        else:
            max_size = available_max_sizes[-1]

        # Ensure max_size >= min_size
        if max_size < min_size:
            max_size = min_size

        return min_size, max_size

    def update_auto_atlas_sizes(self):
        """Update atlas sizes automatically if auto sizing is enabled."""
        if not self.auto_size_check.isChecked():
            return

        min_size, max_size = self.calculate_auto_atlas_sizes()

        if min_size is not None and max_size is not None:
            # Update combo boxes
            self.min_size_combo.setCurrentText(str(min_size))
            self.max_size_combo.setCurrentText(str(max_size))

            # Update status in log
            animations = self.animation_tree.get_animation_groups()
            total_frames = sum(len(frames) for frames in animations.values())

            if total_frames > 0:
                self.log_text.append(
                    self.tr("Auto-sizing: Min={0}px, Max={1}px (based on {2} frames)").format(
                        min_size, max_size, total_frames
                    )
                )
        elif self.animation_tree.get_total_frame_count() > 0:
            self.log_text.append(
                self.tr("Auto-sizing: Could not calculate sizes - image analysis failed")
            )

    def on_auto_size_toggled(self, checked):
        """Handle auto size checkbox toggle."""
        # Enable/disable size combo boxes
        self.min_size_combo.setEnabled(not checked)
        self.max_size_combo.setEnabled(not checked)

        if checked:
            self.update_auto_atlas_sizes()
            self.log_text.append(
                self.tr("Auto-sizing enabled: Atlas size will be calculated automatically")
            )
        else:
            self.log_text.append(self.tr("Auto-sizing disabled: Manual size selection enabled"))
