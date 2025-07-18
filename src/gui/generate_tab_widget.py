#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                              QLabel, QPushButton, QGroupBox, 
                              QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox,
                              QProgressBar, QTextEdit, QFileDialog, QMessageBox,
                              QSplitter, QFrame, QSlider)
from PySide6.QtCore import Qt, QThread, Signal

from core.generator import SparrowAtlasGenerator, AtlasSettings
from gui.animation_tree_widget import AnimationTreeWidget


class GeneratorWorker(QThread):
    """Worker thread for atlas generation process."""
    
    progress_updated = Signal(int, int, str)  # current, total, message
    generation_completed = Signal(dict)  # results dictionary
    generation_failed = Signal(str)  # error message
    
    def __init__(self, input_frames, output_path, atlas_settings):
        super().__init__()
        self.input_frames = input_frames
        self.output_path = output_path
        self.atlas_settings = atlas_settings
        self.animation_groups = None  # Will be set by the caller
        
    def run(self):
        try:
            generator = SparrowAtlasGenerator(progress_callback=self.emit_progress)
            
            # Create AtlasSettings from the atlas_settings dict
            settings = AtlasSettings(
                max_size=self.atlas_settings.get('max_size', 2048),
                min_size=self.atlas_settings.get('min_size', 128),
                padding=self.atlas_settings.get('padding', 2),
                power_of_2=self.atlas_settings.get('power_of_2', True),
                optimization_level=self.atlas_settings.get('optimization_level', 5),
                efficiency_factor=self.atlas_settings.get('efficiency_factor', 1.3),
                allow_rotation=self.atlas_settings.get('allow_rotation', True)
            )
            
            # Use animation groups if available, otherwise create default
            if self.animation_groups:
                animation_groups = self.animation_groups
            else:
                animation_groups = {"Animation_01": self.input_frames}
            
            results = generator.generate_atlas(
                animation_groups,
                self.output_path,
                settings
            )
            
            if results['success']:
                self.generation_completed.emit(results)
            else:
                self.generation_failed.emit(results['error'])
                
        except Exception as e:
            self.generation_failed.emit(str(e))
    
    def emit_progress(self, current, total, message=""):
        """Thread-safe progress emission."""
        self.progress_updated.emit(current, total, message)


class GenerateTabWidget(QWidget):
    """Widget containing all Generate tab functionality."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_app = parent
        self.input_frames = []
        self.output_path = ""
        self.worker = None
        self.animation_groups = {}  # Store animation group data
        
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """Set up the Generate tab UI."""
        main_layout = QVBoxLayout(self)
        
        # Create main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - File management
        left_panel = self.create_file_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Settings and controls
        right_panel = self.create_settings_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([400, 500])
        
        # Bottom panel - Progress and log
        bottom_panel = self.create_progress_panel()
        main_layout.addWidget(bottom_panel)
        
    def create_file_panel(self):
        """Create the file management panel."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(panel)
        
        # Input frames section
        input_group = QGroupBox("Input Frames")
        input_layout = QVBoxLayout(input_group)
        
        # Buttons for adding frames
        button_layout = QHBoxLayout()
        self.add_files_button = QPushButton("Add Files...")
        self.add_directory_button = QPushButton("Add Directory...")
        self.add_animation_button = QPushButton("Add New Animation")
        self.clear_frames_button = QPushButton("Clear All")
        
        button_layout.addWidget(self.add_files_button)
        button_layout.addWidget(self.add_directory_button)
        button_layout.addWidget(self.add_animation_button)
        button_layout.addWidget(self.clear_frames_button)
        input_layout.addLayout(button_layout)
        
        # Animation tree widget (replaces simple list)
        self.animation_tree = AnimationTreeWidget()
        self.animation_tree.setMinimumHeight(200)
        input_layout.addWidget(self.animation_tree)
        
        # Frame info
        self.frame_info_label = QLabel("No frames loaded")
        input_layout.addWidget(self.frame_info_label)
        
        layout.addWidget(input_group)
        
        # Output section
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout(output_group)
        
        # Output path selection
        output_path_layout = QHBoxLayout()
        self.output_path_label = QLabel("No output path selected")
        self.output_path_button = QPushButton("Browse...")
        
        output_path_layout.addWidget(self.output_path_label)
        output_path_layout.addWidget(self.output_path_button)
        output_layout.addLayout(output_path_layout)
        
        layout.addWidget(output_group)
        
        return panel
    
    def create_settings_panel(self):
        """Create the settings panel."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(panel)
        
        # Atlas settings group
        atlas_group = QGroupBox("Atlas Settings")
        atlas_layout = QGridLayout(atlas_group)
        
        # Atlas size settings
        atlas_layout.addWidget(QLabel("Max Atlas Size:"), 0, 0)
        self.max_size_combo = QComboBox()
        self.max_size_combo.addItems(['512', '1024', '2048', '4096', '8192'])
        self.max_size_combo.setCurrentText('2048')
        atlas_layout.addWidget(self.max_size_combo, 0, 1)
        
        atlas_layout.addWidget(QLabel("Min Atlas Size:"), 1, 0)
        self.min_size_combo = QComboBox()
        self.min_size_combo.addItems(['64', '128', '256', '512', '1024'])
        self.min_size_combo.setCurrentText('128')
        atlas_layout.addWidget(self.min_size_combo, 1, 1)
        
        # Padding
        atlas_layout.addWidget(QLabel("Padding:"), 2, 0)
        self.padding_spin = QSpinBox()
        self.padding_spin.setRange(0, 32)
        self.padding_spin.setValue(2)
        atlas_layout.addWidget(self.padding_spin, 2, 1)
        
        # Power of 2
        self.power_of_2_check = QCheckBox("Power of 2 dimensions")
        self.power_of_2_check.setChecked(True)
        atlas_layout.addWidget(self.power_of_2_check, 3, 0, 1, 2)
        
        # Efficiency factor
        atlas_layout.addWidget(QLabel("Efficiency Factor:"), 4, 0)
        self.efficiency_spin = QDoubleSpinBox()
        self.efficiency_spin.setRange(1.0, 3.0)
        self.efficiency_spin.setSingleStep(0.1)
        self.efficiency_spin.setValue(1.3)
        atlas_layout.addWidget(self.efficiency_spin, 4, 1)
        
        # Speed vs Optimization slider
        atlas_layout.addWidget(QLabel("Speed vs Optimization:"), 5, 0)
        self.speed_optimization_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_optimization_slider.setRange(0, 10)
        self.speed_optimization_slider.setValue(5)  # Default balanced
        self.speed_optimization_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.speed_optimization_slider.setTickInterval(1)
        atlas_layout.addWidget(self.speed_optimization_slider, 5, 1)
        
        # Speed vs Optimization labels
        speed_opt_label_layout = QHBoxLayout()
        speed_opt_label_layout.addWidget(QLabel("Fast"))
        speed_opt_label_layout.addStretch()
        speed_opt_label_layout.addWidget(QLabel("Balanced"))
        speed_opt_label_layout.addStretch()
        speed_opt_label_layout.addWidget(QLabel("Optimized"))
        atlas_layout.addLayout(speed_opt_label_layout, 6, 0, 1, 2)
        
        # Speed vs Optimization value display
        self.speed_opt_value_label = QLabel("Level: 5 (Balanced)")
        atlas_layout.addWidget(self.speed_opt_value_label, 7, 0, 1, 2)
        
        layout.addWidget(atlas_group)
        
        # Output format group
        format_group = QGroupBox("Output Format")
        format_layout = QGridLayout(format_group)
        
        # Image format
        format_layout.addWidget(QLabel("Image Format:"), 0, 0)
        self.image_format_combo = QComboBox()
        self.image_format_combo.addItems(['PNG', 'JPEG'])
        format_layout.addWidget(self.image_format_combo, 0, 1)
        
        # JPEG quality (only for JPEG)
        format_layout.addWidget(QLabel("JPEG Quality:"), 1, 0)
        self.jpeg_quality_spin = QSpinBox()
        self.jpeg_quality_spin.setRange(1, 100)
        self.jpeg_quality_spin.setValue(95)
        self.jpeg_quality_spin.setEnabled(False)
        format_layout.addWidget(self.jpeg_quality_spin, 1, 1)
        
        # Atlas type (replaces metadata formats)
        format_layout.addWidget(QLabel("Atlas Type:"), 2, 0)
        self.atlas_type_combo = QComboBox()
        self.atlas_type_combo.addItems(['Sparrow'])
        format_layout.addWidget(self.atlas_type_combo, 2, 1)
        
        layout.addWidget(format_group)
        
        # Generate button
        self.generate_button = QPushButton("Generate Atlas")
        self.generate_button.setMinimumHeight(40)
        self.generate_button.setEnabled(False)
        layout.addWidget(self.generate_button)
        
        # Preview area
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_label = QLabel("No preview available")
        self.preview_label.setMinimumHeight(150)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("border: 1px solid gray; background-color: #f0f0f0;")
        preview_layout.addWidget(self.preview_label)
        
        layout.addWidget(preview_group)
        
        return panel
    
    def create_progress_panel(self):
        """Create the progress and log panel."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        panel.setMaximumHeight(150)
        layout = QVBoxLayout(panel)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        # Log text (smaller)
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(80)
        self.log_text.setPlainText("Atlas generation log will appear here...")
        layout.addWidget(self.log_text)
        
        return panel
    
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
        self.image_format_combo.currentTextChanged.connect(self.on_format_change)
        self.speed_optimization_slider.valueChanged.connect(self.update_speed_opt_label)
        
        # Generation
        self.generate_button.clicked.connect(self.generate_atlas)
        
    def add_files(self):
        """Add individual files to the frame list."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Frame Images",
            "",
            "Image files (*.png *.jpg *.jpeg *.bmp *.tiff);;All files (*.*)"
        )
        
        if files:
            self.add_frames_to_default_animation(files)
    
    def add_directory(self):
        """Add all images from a directory to the frame list."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Directory with Frame Images",
            ""
        )
        
        if directory:
            directory_path = Path(directory)
            image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff'}
            
            files = []
            for ext in image_extensions:
                files.extend(directory_path.glob(f"*{ext}"))
                files.extend(directory_path.glob(f"*{ext.upper()}"))
            
            if files:
                self.add_frames_to_default_animation([str(f) for f in files])
            else:
                QMessageBox.information(self, "No Images", "No image files found in the selected directory.")
    
    def add_animation_group(self):
        """Add a new animation group."""
        self.animation_tree.add_animation_group()
        self.update_frame_info()
        self.update_generate_button_state()
    
    def update_speed_opt_label(self, value):
        """Update the speed optimization label based on slider value."""
        labels = {
            0: "Level: 0 (Ultra-Fast, Minimal Packing)",
            1: "Level: 1 (Ultra-Fast, Tight Packing)",
            2: "Level: 2 (Ultra-Fast, Reduced Padding)",
            3: "Level: 3 (Fast, No Rotation)",
            4: "Level: 4 (Fast, Basic Packing)",
            5: "Level: 5 (Fast, Standard Packing)",
            6: "Level: 6 (Balanced, Some Rotation)",
            7: "Level: 7 (Balanced, Full Rotation)",
            8: "Level: 8 (Optimized, Advanced)",
            9: "Level: 9 (Optimized, Maximum)",
            10: "Level: 10 (Ultra-Optimized, Slowest)"
        }
        self.speed_opt_value_label.setText(labels.get(value, f"Level: {value}"))
    
    def get_optimization_settings(self, slider_value):
        """Convert slider value to optimization settings."""
        if slider_value <= 2:
            # Ultra-fast mode - absolutely minimal optimization
            return {
                'use_numpy': False,
                'use_advanced_numpy': False,
                'orientation_optimization': False,
                'packing_strategy': 'ultra_simple',
                'efficiency_factor': 1.05,
                'tight_packing': True,
                'use_multithreading': True
            }
        elif slider_value <= 5:
            # Fast mode - minimal optimization
            return {
                'use_numpy': False,
                'use_advanced_numpy': False,
                'orientation_optimization': False,
                'packing_strategy': 'simple',
                'efficiency_factor': 1.1,
                'tight_packing': True,
                'use_multithreading': True
            }
        elif slider_value <= 7:
            # Balanced mode - moderate optimization
            return {
                'use_numpy': True,
                'use_advanced_numpy': False,
                'orientation_optimization': True,
                'packing_strategy': 'balanced',
                'efficiency_factor': 1.2,
                'tight_packing': False,
                'use_multithreading': True
            }
        else:
            # Optimized mode - full optimization
            return {
                'use_numpy': True,
                'use_advanced_numpy': True,
                'orientation_optimization': True,
                'packing_strategy': 'advanced',
                'efficiency_factor': 1.3,
                'tight_packing': False,
                'use_multithreading': True
            }
    
    def add_frames_to_default_animation(self, file_paths):
        """Add frame files to a default animation group."""
        # Create or use existing default animation
        default_animation = "Animation_01"
        
        # Add frames to the animation
        for file_path in file_paths:
            # Check if already in any animation
            if not self.is_frame_already_added(file_path):
                self.animation_tree.add_frame_to_animation(default_animation, file_path)
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
    
    def select_output_path(self):
        """Select output path for the atlas."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Atlas As",
            "",
            "PNG files (*.png);;JPEG files (*.jpg);;All files (*.*)"
        )
        
        if file_path:
            self.output_path = file_path
            self.output_path_label.setText(f"Output: {Path(file_path).name}")
            self.update_generate_button_state()
    
    def update_frame_info(self):
        """Update the frame info label."""
        total_frames = self.animation_tree.get_total_frame_count()
        animation_count = self.animation_tree.get_animation_count()
        
        if total_frames == 0:
            self.frame_info_label.setText("No frames loaded")
        else:
            self.frame_info_label.setText(f"{animation_count} animation(s), {total_frames} frame(s) total")
    
    def update_generate_button_state(self):
        """Update the generate button enabled state."""
        has_frames = self.animation_tree.get_total_frame_count() > 0
        has_output_path = bool(self.output_path)
        
        can_generate = has_frames and has_output_path
        self.generate_button.setEnabled(can_generate)
    
    def on_format_change(self, format_text):
        """Handle image format change."""
        self.jpeg_quality_spin.setEnabled(format_text == 'JPEG')
    
    def generate_atlas(self):
        """Start the atlas generation process."""
        if self.animation_tree.get_total_frame_count() == 0 or not self.output_path:
            QMessageBox.warning(self, "Error", "Please add frames and select output path.")
            return
        
        # Get all animations from the tree
        animations = self.animation_tree.get_animation_groups()
        
        # Convert to the format expected by the new generator
        animation_groups = {}
        for animation_name, frames in animations.items():
            # Sort frames by order
            sorted_frames = sorted(frames, key=lambda x: x['order'])
            animation_groups[animation_name] = [frame['path'] for frame in sorted_frames]
        
        # Prepare settings for the new generator
        atlas_settings = {
            'max_size': int(self.max_size_combo.currentText()),
            'min_size': int(self.min_size_combo.currentText()),
            'padding': self.padding_spin.value(),
            'power_of_2': self.power_of_2_check.isChecked(),
            'efficiency_factor': self.efficiency_spin.value(),
            'optimization_level': self.speed_optimization_slider.value(),
            'allow_rotation': self.speed_optimization_slider.value() > 5,  # Enable rotation for higher optimization
        }
        
        # Create a dummy input_frames list for the worker (for compatibility)
        all_input_frames = []
        for frames in animation_groups.values():
            all_input_frames.extend(frames)
        
        # Start generation in worker thread
        self.worker = GeneratorWorker(all_input_frames, self.output_path, atlas_settings)
        self.worker.animation_groups = animation_groups  # Pass animation groups to worker
        self.worker.progress_updated.connect(self.on_progress_updated)
        self.worker.generation_completed.connect(self.on_generation_completed)
        self.worker.generation_failed.connect(self.on_generation_failed)
        
        # Update UI
        self.generate_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Generating atlas...")
        self.log_text.clear()
        
        self.worker.start()
    
    def on_progress_updated(self, current, total, message):
        """Handle progress updates."""
        if total > 0:
            self.progress_bar.setValue(int((current / total) * 100))
        self.status_label.setText(f"Progress: {current}/{total} - {message}")
        self.log_text.append(f"{message}")
    
    def on_generation_completed(self, results):
        """Handle successful generation completion."""
        self.progress_bar.setVisible(False)
        self.generate_button.setEnabled(True)
        
        # Show results
        message = "Atlas generated successfully!\n\n"
        message += f"Atlas: {results['atlas_path']}\n"
        message += f"Size: {results['atlas_size'][0]}x{results['atlas_size'][1]}\n"
        message += f"Frames: {results['frames_count']}\n"
        message += f"Efficiency: {results['efficiency']:.1f}%\n"
        message += f"Format: {self.atlas_type_combo.currentText()}\n"
        message += f"Metadata files: {len(results['metadata_files'])}"
        
        self.status_label.setText("Generation completed successfully!")
        self.log_text.append("\n" + "="*50)
        self.log_text.append("GENERATION COMPLETED SUCCESSFULLY!")
        self.log_text.append("="*50)
        self.log_text.append(message)
        
        QMessageBox.information(self, "Success", message)
    
    def on_generation_failed(self, error_message):
        """Handle generation failure."""
        self.progress_bar.setVisible(False)
        self.generate_button.setEnabled(True)
        
        self.status_label.setText("Generation failed!")
        self.log_text.append("\n" + "="*50)
        self.log_text.append("GENERATION FAILED!")
        self.log_text.append("="*50)
        self.log_text.append(f"Error: {error_message}")
        
        QMessageBox.critical(self, "Generation Failed", f"Atlas generation failed:\n\n{error_message}")
