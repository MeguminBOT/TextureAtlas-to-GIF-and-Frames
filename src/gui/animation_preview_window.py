#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from typing import List

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QSlider,
    QSpinBox,
    QDoubleSpinBox,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QGroupBox,
    QCheckBox,
    QColorDialog,
    QSplitter,
    QComboBox,
    QLineEdit,
    QWidget,
    QMessageBox,
    QScrollArea,
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QSize, QRect
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor

# Try to import PIL for image processing
try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Constants for memory optimization
MAX_FRAMES_IN_MEMORY = 100  # Limit for memory-conscious mode
FRAME_CACHE_SIZE = 20  # Number of frames to keep cached around current position


class AnimationProcessor(QThread):
    """Background thread for processing animation frames with optimized memory usage"""

    frame_processed = Signal(int, QPixmap)  # frame_index, pixmap
    processing_complete = Signal()
    error_occurred = Signal(str)
    progress_updated = Signal(int, int)  # current, total

    def __init__(self, animation_path: str, settings: dict):
        super().__init__()
        self.animation_path = animation_path
        self.settings = settings
        self.frames: List[QPixmap] = []
        self.frame_durations: List[int] = []
        self._stop_requested = False

    def stop(self):
        """Request to stop processing"""
        self._stop_requested = True

    def run(self):
        """Process animation frames in background with optimizations"""
        try:
            if not PIL_AVAILABLE:
                self.error_occurred.emit("PIL/Pillow not available")
                return

            # Load animation with optimized approach
            with Image.open(self.animation_path) as img:
                frame_count = getattr(img, "n_frames", 1)

                # Pre-allocate lists for better performance
                self.frames = [QPixmap()] * frame_count
                self.frame_durations = [100] * frame_count

                # Process frames with progress reporting
                for frame_idx in range(frame_count):
                    if self._stop_requested:
                        return

                    img.seek(frame_idx)

                    # Get frame duration (default 100ms if not available)
                    duration = getattr(img, "info", {}).get("duration", 100)
                    self.frame_durations[frame_idx] = duration

                    # Convert PIL image to QPixmap more efficiently
                    frame_copy = img.copy()
                    if frame_copy.mode != "RGBA":
                        frame_copy = frame_copy.convert("RGBA")

                    # Convert to QImage with optimized format
                    w, h = frame_copy.size
                    bytes_data = frame_copy.tobytes("raw", "RGBA")
                    qimg = QImage(bytes_data, w, h, QImage.Format.Format_RGBA8888)

                    # Create pixmap optimized for rendering
                    pixmap = QPixmap.fromImage(qimg)

                    # Pre-convert to device format for better performance
                    if hasattr(pixmap, "toImage"):
                        # Ensure pixmap is in optimal format for the display device
                        device_pixmap = QPixmap(pixmap.size())
                        device_pixmap.fill(Qt.GlobalColor.transparent)
                        painter = QPainter(device_pixmap)
                        painter.setCompositionMode(
                            QPainter.CompositionMode.CompositionMode_SourceOver
                        )
                        painter.drawPixmap(0, 0, pixmap)
                        painter.end()
                        pixmap = device_pixmap

                    self.frames[frame_idx] = pixmap

                    # Emit signals for UI updates
                    self.frame_processed.emit(frame_idx, pixmap)
                    self.progress_updated.emit(frame_idx + 1, frame_count)

                    # Allow other threads to run
                    self.msleep(1)

            if not self._stop_requested:
                self.processing_complete.emit()

        except Exception as e:
            self.error_occurred.emit(f"Failed to load animation: {str(e)}")


class FrameListWidget(QListWidget):
    """Custom list widget for frame navigation"""

    frame_selected = Signal(int)
    frame_checked = Signal(int, bool)  # frame_index, checked

    def __init__(self):
        super().__init__()
        self.setMaximumWidth(140)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.currentItemChanged.connect(self._on_selection_changed)
        self.itemChanged.connect(self._on_item_changed)

    def set_frame_count(self, count: int, frame_durations: List[int] = None):
        """Set the number of frames in the list with checkboxes and optional delays"""
        self.clear()
        for i in range(count):
            # Create frame label with optional delay info
            if frame_durations and i < len(frame_durations):
                delay_ms = frame_durations[i]
                frame_text = f"Frame {i + 1} ({delay_ms}ms)"
            else:
                frame_text = f"Frame {i + 1}"

            item = QListWidgetItem(frame_text)
            item.setData(Qt.ItemDataRole.UserRole, i)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)  # All frames checked by default
            self.addItem(item)

    def update_frame_delays(self, frame_durations: List[int], show_delays: bool = True):
        """Update frame delay display in the list"""
        for i in range(self.count()):
            item = self.item(i)
            if item:
                if frame_durations and i < len(frame_durations):
                    delay_ms = frame_durations[i]
                    frame_text = f"Frame {i + 1} ({delay_ms}ms)"
                else:
                    frame_text = f"Frame {i + 1}"
                item.setText(frame_text)

    def select_frame(self, frame_index: int):
        """Select a specific frame"""
        if 0 <= frame_index < self.count():
            self.setCurrentRow(frame_index)

    def get_checked_frames(self):
        """Get list of indices of checked frames"""
        checked_frames = []
        for i in range(self.count()):
            item = self.item(i)
            if item and item.checkState() == Qt.CheckState.Checked:
                checked_frames.append(i)
        return checked_frames

    def set_checked_frames(self, frame_indices):
        """Set which frames are checked based on indices list"""
        # First uncheck all frames
        for i in range(self.count()):
            item = self.item(i)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)

        # Then check the specified frames
        for frame_index in frame_indices:
            if 0 <= frame_index < self.count():
                item = self.item(frame_index)
                if item:
                    item.setCheckState(Qt.CheckState.Checked)

    def _on_selection_changed(self, current, previous):
        """Handle frame selection change"""
        if current:
            frame_index = current.data(Qt.ItemDataRole.UserRole)
            if frame_index is not None:
                self.frame_selected.emit(frame_index)

    def _on_item_changed(self, item):
        """Handle checkbox state change"""
        frame_index = item.data(Qt.ItemDataRole.UserRole)
        if frame_index is not None:
            is_checked = item.checkState() == Qt.CheckState.Checked
            self.frame_checked.emit(frame_index, is_checked)


class AnimationDisplay(QScrollArea):
    """Custom widget for displaying animation frames with scroll support and actual size display"""

    scale_changed = Signal(float)  # Signal emitted when scale changes via wheel

    def __init__(self):
        super().__init__()

        # Create the label that will hold the pixmap
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: transparent;")
        self.image_label.setScaledContents(False)

        # Set up the scroll area
        self.setWidget(self.image_label)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setMinimumSize(600, 500)
        self.setStyleSheet("border: 1px solid gray; background-color: transparent;")

        # Display properties
        self._background_color = QColor(127, 127, 127, 255)
        self._background_mode = "None"  # "None", "Solid Color", or "Transparency Pattern"
        self._checkered_pattern = None
        self._current_pixmap = None
        self._scale_factor = 1.0
        self._original_size = None

        # Performance optimizations
        self._cached_scaled_pixmap = None
        self._cached_scale = None

        # Install event filter on the image label to capture wheel events
        self.image_label.installEventFilter(self)

    def eventFilter(self, source, event):
        """Filter events to capture wheel events over the image"""
        if source == self.image_label and event.type() == event.Type.Wheel:
            return self.wheelEvent(event)
        return super().eventFilter(source, event)

    def wheelEvent(self, event):
        """Handle mouse wheel events for zooming (Ctrl+Scroll to zoom)"""
        # Only zoom if Ctrl is pressed (standard zoom behavior)
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Get wheel angle delta (positive for zoom in, negative for zoom out)
            angle_delta = event.angleDelta().y()

            # Calculate zoom factor (standard zoom increments of 10%)
            zoom_factor = 1.1 if angle_delta > 0 else 1.0 / 1.1

            # Apply zoom
            new_scale = self._scale_factor * zoom_factor

            # Clamp scale to reasonable limits (0.1x to 5x)
            new_scale = max(0.1, min(5.0, new_scale))

            # Update scale factor and emit signal if scale changed
            old_scale = self._scale_factor
            self.set_scale_factor(new_scale)

            # Emit scale change signal to update UI controls
            if abs(old_scale - new_scale) > 0.001:
                self.scale_changed.emit(new_scale)

            # Accept the event to prevent it from being passed to parent widgets
            event.accept()
            return True
        else:
            # Pass the event to the parent if Ctrl is not pressed
            return super().wheelEvent(event)

    def set_background_color(self, color: QColor):
        """Set the background color for solid color mode"""
        self._background_color = color
        self._background_mode = "Solid Color"
        # Always keep scroll area background transparent - background is handled in frame compositing
        self.setStyleSheet("border: 1px solid gray; background-color: transparent;")
        self.update_display()

    def set_background_mode(self, mode: str):
        """Set the background mode: 'None', 'Solid Color', or 'Transparency Pattern'"""
        self._background_mode = mode
        if mode == "Transparency Pattern":
            self._create_checkered_pattern()

        # Always keep scroll area background transparent - background is handled in frame compositing
        self.setStyleSheet("border: 1px solid gray; background-color: transparent;")
        self.update_display()

    def set_transparency_background(self, show_transparency: bool):
        """Legacy method for compatibility - maps to new background mode system"""
        if show_transparency:
            self.set_background_mode("Transparency Pattern")
        else:
            self.set_background_mode("Solid Color")

    def _create_checkered_pattern(self):
        """Create a checkered pattern for transparency background"""
        checker_size = 16
        pattern_size = checker_size * 2

        self._checkered_pattern = QPixmap(pattern_size, pattern_size)
        painter = QPainter(self._checkered_pattern)

        # Light gray and white squares
        light_gray = QColor(240, 240, 240)
        white = QColor(255, 255, 255)

        # Draw the checkered pattern
        for x in range(0, pattern_size, checker_size):
            for y in range(0, pattern_size, checker_size):
                # Determine color based on position
                is_light = ((x // checker_size) + (y // checker_size)) % 2 == 0
                color = light_gray if is_light else white
                painter.fillRect(x, y, checker_size, checker_size, color)

        painter.end()

    def get_scale_factor(self):
        """Get the current scale factor"""
        return self._scale_factor

    def set_scale_factor(self, scale: float):
        """Set the scale factor for the displayed frame"""
        if abs(self._scale_factor - scale) > 0.001:  # Only update if significantly different
            self._scale_factor = scale

            # Clear cache when scale changes
            self._cached_scaled_pixmap = None
            self._cached_scale = None

            self.update_display()

    def set_frame(self, pixmap: QPixmap):
        """Set the current frame to display at actual size with scaling"""
        self._current_pixmap = pixmap

        # Clear cached scaled pixmap when frame changes
        self._cached_scaled_pixmap = None
        self._cached_scale = None

        if pixmap and not pixmap.isNull():
            self._original_size = pixmap.size()

        self.update_display()

    def update_display(self):
        """Update the display with current frame and scaling"""
        if not self._current_pixmap or self._current_pixmap.isNull():
            self.image_label.clear()
            return

        # Calculate scaled size
        pixmap_size = self._current_pixmap.size()
        scaled_width = int(pixmap_size.width() * self._scale_factor)
        scaled_height = int(pixmap_size.height() * self._scale_factor)
        scaled_size = QSize(scaled_width, scaled_height)

        # Use cached scaled pixmap if available and scale hasn't changed
        if (
            self._cached_scaled_pixmap
            and self._cached_scale
            and abs(self._cached_scale - self._scale_factor) < 0.001
            and self._cached_scaled_pixmap.size() == scaled_size
        ):
            display_pixmap = self._cached_scaled_pixmap
        else:
            # Create new scaled pixmap
            if self._scale_factor == 1.0:
                display_pixmap = self._current_pixmap
            else:
                display_pixmap = self._current_pixmap.scaled(
                    scaled_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )

                # Cache the scaled pixmap
                self._cached_scaled_pixmap = display_pixmap
                self._cached_scale = self._scale_factor

        # Handle background based on mode
        if self._background_mode == "Transparency Pattern" and self._checkered_pattern:
            # Create a new pixmap with checkered background
            final_pixmap = QPixmap(display_pixmap.size())
            final_pixmap.fill(Qt.GlobalColor.transparent)

            painter = QPainter(final_pixmap)

            # Tile the checkered pattern
            pattern_size = self._checkered_pattern.size()
            for x in range(0, final_pixmap.width(), pattern_size.width()):
                for y in range(0, final_pixmap.height(), pattern_size.height()):
                    painter.drawPixmap(x, y, self._checkered_pattern)

            # Draw the animation frame on top
            painter.drawPixmap(0, 0, display_pixmap)
            painter.end()

            self.image_label.setPixmap(final_pixmap)
        elif self._background_mode == "Solid Color":
            # Create a new pixmap with solid background color matching the display size
            final_pixmap = QPixmap(display_pixmap.size())
            final_pixmap.fill(self._background_color)

            painter = QPainter(final_pixmap)
            # Draw the animation frame on top
            painter.drawPixmap(0, 0, display_pixmap)
            painter.end()

            self.image_label.setPixmap(final_pixmap)
        else:
            # No background - just show the frame as-is
            self.image_label.setPixmap(display_pixmap)

        # Resize the label to fit the pixmap
        self.image_label.resize(display_pixmap.size())

    def clear_cache(self):
        """Clear rendering cache to free memory"""
        self._cached_scaled_pixmap = None
        self._cached_scale = None


class AnimationPreviewWindow(QDialog):
    """
    Modern animation preview window with real-time playback and settings.
    """

    # Signal to emit saved settings
    settings_saved = Signal(dict)

    def __init__(self, parent, animation_path: str, settings: dict):
        super().__init__(parent)
        self.animation_path = animation_path
        self.settings = settings.copy() if settings else {}

        # Animation state
        self.frames: List[QPixmap] = []
        self.frame_durations: List[int] = []
        self.current_frame = 0
        self.is_playing = False
        self.is_loading = False
        self.processor = None
        self._loop_delay_applied = False  # Track if loop delay was applied this cycle

        # Performance optimization flags
        self._last_update_time = 0
        self._update_throttle = 16  # ~60 FPS max update rate

        # UI components
        self.display = None
        self.frame_list = None
        self.play_button = None
        self.position_slider = None
        self.timer = None
        self.progress_label = None

        # Settings widgets
        self.fps_spinbox = None
        self.scale_spinbox = None
        self.loop_checkbox = None

        self.init_ui()
        self.load_animation()

    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Animation Preview")
        self.setMinimumSize(960, 480)
        self.resize(1366, 768)

        # Enable maximize button and window resizing
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )

        # Main layout
        main_layout = QVBoxLayout(self)

        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # Left panel: Frame list
        left_panel = self.create_frame_panel()
        splitter.addWidget(left_panel)

        # Center panel: Animation display
        center_panel = self.create_display_panel()
        splitter.addWidget(center_panel)

        # Right panel: Settings
        right_panel = self.create_settings_panel()
        splitter.addWidget(right_panel)

        # Set splitter proportions
        splitter.setStretchFactor(0, 0)  # Frame list: fixed width
        splitter.setStretchFactor(1, 1)  # Display: stretches
        splitter.setStretchFactor(2, 0)  # Settings: fixed width

        # Bottom controls
        controls_layout = self.create_controls()
        main_layout.addLayout(controls_layout)

        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()  # Push buttons to the right

        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.reject)
        button_layout.addWidget(close_button)

        # Close and Save button
        close_save_button = QPushButton("Close and Save")
        close_save_button.clicked.connect(self.close_and_save)
        button_layout.addWidget(close_save_button)

        main_layout.addLayout(button_layout)

        # Setup timer for playback
        self.timer = QTimer()
        self.timer.timeout.connect(self.next_frame)

        # Update UI state
        self.update_format_settings()

    def close_and_save(self):
        """Close the preview and save current settings directly to animation overrides"""
        # Get checked frame indices
        checked_frames = self.get_checked_frame_indices()

        # Build settings dict with current preview settings from UI controls
        save_settings = {
            "fps": self.fps_spinbox.value(),
            "scale": self.anim_scale_spinbox.value(),
            "animation_format": self.format_combo.currentText(),
            "delay": self.delay_spinbox.value(),
            "period": self.period_spinbox.value(),
            "threshold": self.threshold_spinbox.value(),
            "var_delay": self.var_delay_checkbox.isChecked(),
            "crop_option": self.crop_combo.currentText(),
        }

        # Add frame indices if any frames are unchecked (skip frames functionality)
        if len(checked_frames) < len(self.frames) and checked_frames:
            save_settings["indices"] = checked_frames

        # Emit signal with settings to pass to main window for saving
        self.settings_saved.emit(save_settings)

        # Close the window
        self.accept()

    def create_frame_panel(self) -> QWidget:
        """Create the frame list panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        layout.addWidget(QLabel("Frames:"))

        self.frame_list = FrameListWidget()
        self.frame_list.frame_selected.connect(self.goto_frame)
        self.frame_list.frame_checked.connect(self.on_frame_checked)
        layout.addWidget(self.frame_list)

        return panel

    def create_display_panel(self) -> QWidget:
        """Create the animation display panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Display area with scroll support
        self.display = AnimationDisplay()

        # Set tooltip to inform users about zoom functionality
        self.display.setToolTip("Hold Ctrl and use mouse wheel to zoom in/out")

        # Connect scale change signal to update spinbox
        self.display.scale_changed.connect(self.on_display_scale_changed)

        layout.addWidget(self.display)

        # Status info layout
        info_layout = QHBoxLayout()

        # Frame info
        self.frame_info_label = QLabel("Frame 1 / 1")
        self.frame_info_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        info_layout.addWidget(self.frame_info_label)

        # Progress info (shown during loading)
        self.progress_label = QLabel("")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.progress_label.setStyleSheet("color: #666;")
        info_layout.addWidget(self.progress_label)

        layout.addLayout(info_layout)

        return panel

    def create_settings_panel(self) -> QWidget:
        """Create the settings panel"""
        panel = QWidget()
        panel.setMaximumWidth(300)
        layout = QVBoxLayout(panel)

        # Animation Format settings
        format_group = QGroupBox("Animation Format")
        format_layout = QGridLayout(format_group)

        format_layout.addWidget(QLabel("Format:"), 0, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["GIF", "WebP", "APNG"])
        self.format_combo.setCurrentText(self.settings.get("animation_format", "GIF"))
        self.format_combo.currentTextChanged.connect(self.on_format_changed)
        format_layout.addWidget(self.format_combo, 0, 1)

        layout.addWidget(format_group)

        # Animation settings (renamed from Playback)
        playback_group = QGroupBox("Animation Settings")
        playback_layout = QGridLayout(playback_group)

        # FPS setting
        playback_layout.addWidget(QLabel("FPS:"), 0, 0)
        self.fps_spinbox = QSpinBox()
        self.fps_spinbox.setRange(1, 60)
        self.fps_spinbox.setValue(self.settings.get("fps", 24))
        self.fps_spinbox.valueChanged.connect(self.on_fps_changed)
        playback_layout.addWidget(self.fps_spinbox, 0, 1)

        # Loop delay setting
        playback_layout.addWidget(QLabel("Loop Delay (ms):"), 1, 0)
        self.delay_spinbox = QSpinBox()
        self.delay_spinbox.setRange(0, 5000)
        self.delay_spinbox.setValue(self.settings.get("delay", 250))
        self.delay_spinbox.valueChanged.connect(self.on_delay_changed)
        playback_layout.addWidget(self.delay_spinbox, 1, 1)

        # Minimum period setting
        playback_layout.addWidget(QLabel("Min Period (ms):"), 2, 0)
        self.period_spinbox = QSpinBox()
        self.period_spinbox.setRange(0, 10000)
        self.period_spinbox.setValue(self.settings.get("period", 0))
        self.period_spinbox.valueChanged.connect(self.on_period_changed)
        playback_layout.addWidget(self.period_spinbox, 2, 1)

        # Variable delay option
        self.var_delay_checkbox = QCheckBox("Variable delay")
        self.var_delay_checkbox.setChecked(self.settings.get("var_delay", False))
        self.var_delay_checkbox.toggled.connect(self.on_var_delay_changed)
        playback_layout.addWidget(self.var_delay_checkbox, 3, 0, 1, 2)

        # Animation scale setting (moved from frame settings)
        playback_layout.addWidget(QLabel("Scale:"), 4, 0)
        self.anim_scale_spinbox = QDoubleSpinBox()
        self.anim_scale_spinbox.setRange(0.1, 10.0)
        self.anim_scale_spinbox.setSingleStep(0.1)
        self.anim_scale_spinbox.setValue(self.settings.get("scale", 1.0))
        self.anim_scale_spinbox.valueChanged.connect(self.on_anim_scale_changed)
        playback_layout.addWidget(self.anim_scale_spinbox, 4, 1)

        # Indices setting
        playback_layout.addWidget(QLabel("Indices:"), 5, 0)
        self.indices_edit = QLineEdit()
        self.indices_edit.setPlaceholderText("e.g., 0,2,4 or 0-5 (leave empty for all frames)")
        self.indices_edit.textChanged.connect(self.on_indices_changed)
        playback_layout.addWidget(self.indices_edit, 5, 1)

        # Crop option setting
        playback_layout.addWidget(QLabel("Crop Option:"), 6, 0)
        self.crop_combo = QComboBox()
        self.crop_combo.addItems(["None", "Animation based", "Frame based"])
        self.crop_combo.setCurrentText(self.settings.get("crop_option", "None"))
        self.crop_combo.currentTextChanged.connect(self.on_crop_changed)
        playback_layout.addWidget(self.crop_combo, 6, 1)

        # Threshold setting (moved from GIF-specific)
        playback_layout.addWidget(QLabel("Threshold:"), 7, 0)
        self.threshold_spinbox = QDoubleSpinBox()
        self.threshold_spinbox.setRange(0.0, 1.0)
        self.threshold_spinbox.setSingleStep(0.1)
        self.threshold_spinbox.setValue(self.settings.get("threshold", 0.5))
        self.threshold_spinbox.valueChanged.connect(self.on_threshold_changed)
        playback_layout.addWidget(self.threshold_spinbox, 7, 1)

        layout.addWidget(playback_group)

        # Display settings
        display_group = QGroupBox("Display")
        display_layout = QGridLayout(display_group)

        # Loop option (moved from preview settings)
        self.loop_checkbox = QCheckBox("Loop preview")
        self.loop_checkbox.setChecked(True)
        display_layout.addWidget(self.loop_checkbox, 0, 0, 1, 2)

        # Preview scale setting (separate from animation scale)
        display_layout.addWidget(QLabel("Preview Zoom:"), 1, 0)
        self.scale_spinbox = QSpinBox()
        self.scale_spinbox.setRange(10, 500)  # 10% to 500%
        self.scale_spinbox.setSingleStep(10)
        self.scale_spinbox.setValue(100)  # 100% = 1.0x
        self.scale_spinbox.setSuffix("%")
        self.scale_spinbox.setToolTip("Preview zoom level (also controlled by Ctrl+Mouse Wheel)")
        self.scale_spinbox.valueChanged.connect(self.on_scale_percentage_changed)
        display_layout.addWidget(self.scale_spinbox, 1, 1)

        # Background options
        display_layout.addWidget(QLabel("Background:"), 2, 0)
        bg_layout = QVBoxLayout()

        # Background mode selection
        self.bg_mode_combo = QComboBox()
        self.bg_mode_combo.addItems(["None", "Solid Color", "Transparency Pattern"])
        self.bg_mode_combo.setCurrentText("None")
        self.bg_mode_combo.currentTextChanged.connect(self.on_background_mode_changed)
        bg_layout.addWidget(self.bg_mode_combo)

        # Color selection (only shown for solid color mode)
        self.bg_color_button = QPushButton()
        self.bg_color_button.setFixedSize(50, 30)
        self.bg_color_button.setStyleSheet(
            "background-color: rgb(127, 127, 127); border: 1px solid gray;"
        )
        self.bg_color_button.clicked.connect(self.choose_background_color)
        bg_layout.addWidget(self.bg_color_button)

        bg_widget = QWidget()
        bg_widget.setLayout(bg_layout)
        display_layout.addWidget(bg_widget, 2, 1)

        layout.addWidget(display_group)

        # Export settings
        export_group = QGroupBox("Export")
        export_layout = QVBoxLayout(export_group)

        self.regenerate_button = QPushButton("Force Regenerate Animation")
        self.regenerate_button.clicked.connect(self.regenerate_animation)
        export_layout.addWidget(self.regenerate_button)

        layout.addWidget(export_group)

        # Spacer
        layout.addStretch()

        # Update GIF settings visibility (now handled in animation settings)
        self.update_format_settings()

        return panel

    def create_controls(self) -> QVBoxLayout:
        """Create playback controls"""
        controls_layout = QVBoxLayout()

        # Top row: Playback buttons (centered)
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # Playback buttons
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.toggle_playback)
        button_layout.addWidget(self.play_button)

        prev_button = QPushButton("Previous")
        prev_button.clicked.connect(self.previous_frame)
        button_layout.addWidget(prev_button)

        next_button = QPushButton("Next")
        next_button.clicked.connect(self.next_frame)
        button_layout.addWidget(next_button)

        button_layout.addStretch()
        controls_layout.addLayout(button_layout)

        # Bottom row: Position slider
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel("Position:"))
        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setMinimum(0)
        self.position_slider.valueChanged.connect(self.on_position_changed)
        slider_layout.addWidget(self.position_slider)
        controls_layout.addLayout(slider_layout)

        return controls_layout

    def load_animation(self):
        """Load animation frames with optimized real-time processing"""
        if not os.path.exists(self.animation_path):
            QMessageBox.warning(self, "Error", f"Animation file not found: {self.animation_path}")
            return

        # Clean up previous processor if exists
        if self.processor and self.processor.isRunning():
            self.processor.stop()
            self.processor.wait(1000)  # Wait up to 1 second

        # Clear previous data
        self.frames.clear()
        self.frame_durations.clear()

        # Set loading state
        self.is_loading = True
        self.progress_label.setText("Loading...")

        # Disable playback during loading
        if self.play_button:
            self.play_button.setEnabled(False)

        # Start background processing with progress tracking
        self.processor = AnimationProcessor(self.animation_path, self.settings)
        self.processor.frame_processed.connect(self.on_frame_processed)
        self.processor.processing_complete.connect(self.on_processing_complete)
        self.processor.error_occurred.connect(self.on_processing_error)
        self.processor.progress_updated.connect(self.on_progress_updated)
        self.processor.start()

    def on_progress_updated(self, current: int, total: int):
        """Handle loading progress updates"""
        if self.progress_label:
            percentage = int((current / total) * 100) if total > 0 else 0
            self.progress_label.setText(f"Loading... {percentage}% ({current}/{total})")

    def on_frame_processed(self, frame_index: int, pixmap: QPixmap):
        """Handle processed frame with throttled updates"""
        import time

        current_time = time.time() * 1000  # Convert to milliseconds

        # Extend frames list if needed
        while len(self.frames) <= frame_index:
            self.frames.append(QPixmap())

        self.frames[frame_index] = pixmap

        # Throttle display updates to avoid overwhelming the UI
        if frame_index == 0 or current_time - self._last_update_time > self._update_throttle:
            # Update display if this is the current frame or first frame
            if frame_index == self.current_frame or (frame_index == 0 and self.current_frame == 0):
                self.display.set_frame(pixmap)
                self._last_update_time = current_time

    def on_processing_complete(self):
        """Handle completion of frame processing with optimized setup"""
        frame_count = len(self.frames)

        # Reset loading state
        self.is_loading = False
        self.progress_label.setText(f"Loaded {frame_count} frames")

        # Re-enable playback controls
        if self.play_button:
            self.play_button.setEnabled(True)

        # Get frame durations from processor for optimized playback
        if self.processor and hasattr(self.processor, "frame_durations"):
            self.frame_durations = self.processor.frame_durations.copy()

        # Update frame list efficiently - always show frame delays if available
        if self.frame_durations:
            self.frame_list.set_frame_count(frame_count, self.frame_durations)
        else:
            self.frame_list.set_frame_count(frame_count)

        # Apply any existing indices setting to checkbox states
        if "indices" in self.settings and self.settings["indices"]:
            # If indices are specified, uncheck all frames first, then check only the specified ones
            self.frame_list.set_checked_frames(self.settings["indices"])
        # If no indices setting, all frames remain checked (default)

        # Update position slider
        self.position_slider.setMaximum(max(0, frame_count - 1))

        # Show first frame and reset position
        if self.frames:
            self.current_frame = 0
            self.update_display()
            self.frame_list.select_frame(0)

        print(f"Animation loaded efficiently: {frame_count} frames")

    def on_processing_error(self, error_message: str):
        """Handle processing error with cleanup"""
        self.is_loading = False
        self.progress_label.setText("Error loading animation")

        # Re-enable controls
        if self.play_button:
            self.play_button.setEnabled(True)

        QMessageBox.warning(self, "Error", error_message)

    def cleanup_resources(self):
        """Clean up resources and memory"""
        # Stop any running processes
        if self.processor and self.processor.isRunning():
            self.processor.stop()
            self.processor.wait(1000)  # Wait up to 1 second

        # Stop playback
        if self.timer and self.timer.isActive():
            self.timer.stop()

        # Clear cache
        if hasattr(self.display, "clear_cache"):
            self.display.clear_cache()

        # Clear frame data to free memory
        self.frames.clear()
        self.frame_durations.clear()

        # Reset state
        self.current_frame = 0
        self.is_playing = False
        self.is_loading = False

    def closeEvent(self, event):
        """Handle window close event with proper cleanup"""
        self.cleanup_resources()
        super().closeEvent(event)

    def update_display(self):
        """Update the display with current frame"""

        if 0 <= self.current_frame < len(self.frames):
            pixmap = self.frames[self.current_frame]
            self.display.set_frame(pixmap)

            # Update frame info with delay information (always show if available)
            total_frames = len(self.frames)
            frame_info = f"Frame {self.current_frame + 1} / {total_frames}"

            # Add delay info if we have frame durations
            if self.frame_durations and self.current_frame < len(self.frame_durations):
                delay_ms = self.frame_durations[self.current_frame]
                frame_info += f" ({delay_ms}ms)"

            self.frame_info_label.setText(frame_info)

            # Update position slider
            self.position_slider.blockSignals(True)
            self.position_slider.setValue(self.current_frame)
            self.position_slider.blockSignals(False)

            # Update frame list selection
            self.frame_list.select_frame(self.current_frame)

    def toggle_playback(self):
        """Toggle play/pause"""
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def play(self):
        """Start playback using settings values"""
        if not self.frames:
            return

        self.is_playing = True
        self.play_button.setText("Pause")

        # Reset loop delay flag when starting playback
        self._loop_delay_applied = False

        # Use FPS setting from settings to calculate consistent frame duration
        fps = self.settings.get("fps", 24)
        interval = int(1000 / fps)  # Convert FPS to milliseconds

        # Apply minimum period if set
        min_period = self.settings.get("period", 0)
        if min_period > 0:
            interval = max(interval, min_period)

        self.timer.start(interval)

    def pause(self):
        """Pause playback"""
        self.is_playing = False
        self.play_button.setText("Play")
        self.timer.stop()

        # Reset loop delay flag when pausing so next play cycle gets the delay
        self._loop_delay_applied = False

    def next_frame(self):
        """Go to next frame (only checked frames during playback)"""
        if not self.frames:
            return

        # During playback, only advance to checked frames
        if self.is_playing:
            self.goto_next_checked_frame()
            # Note: goto_next_checked_frame handles its own timer management
        else:
            # Manual navigation - advance normally
            self.current_frame += 1

            # Handle looping with loop delay
            if self.current_frame >= len(self.frames):
                if self.loop_checkbox.isChecked():
                    self.current_frame = 0
                    # Apply loop delay when restarting the animation
                    if self.is_playing:
                        loop_delay = self.settings.get("delay", 250)
                        if loop_delay > 0:
                            # Stop current timer and restart with loop delay
                            self.timer.stop()
                            self.timer.start(loop_delay)
                            self.update_display()
                            return
                else:
                    self.current_frame = len(self.frames) - 1
                    self.pause()

            self.update_display()

            # Ensure consistent FPS timing from settings when playing
            if self.is_playing:
                fps = self.settings.get("fps", 24)
                interval = int(1000 / fps)
                # Apply minimum period if set
                min_period = self.settings.get("period", 0)
                if min_period > 0:
                    interval = max(interval, min_period)
                self.timer.start(interval)

    def previous_frame(self):
        """Go to previous frame"""
        if not self.frames:
            return

        self.current_frame -= 1
        if self.current_frame < 0:
            self.current_frame = max(0, len(self.frames) - 1)

        self.update_display()

    def goto_frame(self, frame_index: int):
        """Go to specific frame"""
        if 0 <= frame_index < len(self.frames):
            self.current_frame = frame_index
            self.update_display()

    def on_frame_checked(self, frame_index, checked):
        """Handle frame checkbox state change"""
        # If current frame is unchecked, move to next checked frame
        if not checked and self.current_frame == frame_index:
            self.goto_next_checked_frame()

        # Update the custom indices text field to reflect current checkbox state
        self.update_indices_text_from_checkboxes()

    def update_indices_text_from_checkboxes(self):
        """Update the indices text field based on current checkbox states"""
        checked_frames = self.get_checked_frame_indices()
        total_frames = len(self.frames)

        # If all frames are checked, clear the indices field (means "all frames")
        if len(checked_frames) == total_frames:
            self.indices_edit.blockSignals(True)
            self.indices_edit.setText("")
            self.indices_edit.blockSignals(False)
            self.settings.pop("indices", None)
        else:
            # Convert checked frames to compact string representation
            indices_text = self.compress_indices_to_text(checked_frames)
            self.indices_edit.blockSignals(True)
            self.indices_edit.setText(indices_text)
            self.indices_edit.blockSignals(False)
            self.settings["indices"] = checked_frames

    def compress_indices_to_text(self, indices):
        """Convert a list of indices to a compact string representation (e.g., '0,2-5,7')"""
        if not indices:
            return ""

        indices = sorted(set(indices))  # Remove duplicates and sort
        result = []
        i = 0

        while i < len(indices):
            start = indices[i]
            end = start

            # Find consecutive numbers
            while i + 1 < len(indices) and indices[i + 1] == indices[i] + 1:
                i += 1
                end = indices[i]

            # Add to result
            if start == end:
                result.append(str(start))
            else:
                result.append(f"{start}-{end}")

            i += 1

        return ",".join(result)

    def get_checked_frame_indices(self):
        """Get list of checked frame indices"""
        return self.frame_list.get_checked_frames()

    def goto_next_checked_frame(self):
        """Go to the next checked frame for playback"""
        checked_frames = self.get_checked_frame_indices()
        if not checked_frames:
            return

        # Find next checked frame after current
        next_frames = [f for f in checked_frames if f > self.current_frame]
        if next_frames:
            self.goto_frame(next_frames[0])
            # Reset loop delay flag when advancing normally (not looping back)
            self._loop_delay_applied = False
        else:
            # We're at the end - apply loop delay if needed before looping back
            if self.is_playing and self.loop_checkbox.isChecked() and not self._loop_delay_applied:
                loop_delay = self.settings.get("delay", 250)
                if loop_delay > 0:
                    # Stop current timer and stay on current frame for loop delay duration
                    self.timer.stop()
                    # Use single shot timer for loop delay, then go to first frame
                    QTimer.singleShot(loop_delay, self._loop_to_first_frame)
                    # Mark that loop delay has been applied for this cycle
                    self._loop_delay_applied = True
                    return

            # No loop delay or already applied - go directly to first frame
            self.goto_frame(checked_frames[0])
            # Mark as looped to prevent repeated delays
            if self.is_playing and self.loop_checkbox.isChecked():
                self._loop_delay_applied = True

    def goto_previous_checked_frame(self):
        """Go to the previous checked frame for playback"""
        checked_frames = self.get_checked_frame_indices()
        if not checked_frames:
            return

        # Find previous checked frame before current
        prev_frames = [f for f in checked_frames if f < self.current_frame]
        if prev_frames:
            self.goto_frame(prev_frames[-1])
        else:
            # Loop to last checked frame
            self.goto_frame(checked_frames[-1])

    def on_position_changed(self, position: int):
        """Handle position slider change"""
        self.goto_frame(position)

    def on_fps_changed(self, fps: int):
        """Handle FPS change"""
        self.settings["fps"] = fps

        # If variable delay is enabled, update frame delays while preserving loop delays
        if self.settings.get("var_delay", False) and self.frame_durations:
            # Calculate variable delays using the same logic as the exporter
            new_durations = []
            for index in range(len(self.frame_durations)):
                # Variable delay: cumulative timing approach
                duration = round((index + 1) * 1000 / fps, -1) - round(index * 1000 / fps, -1)
                new_durations.append(int(duration))

            # Apply loop delay and period to the last frame (like in exporter)
            loop_delay = self.settings.get("delay", 250)
            period = self.settings.get("period", 0)

            new_durations[-1] += loop_delay
            new_durations[-1] += max(round(period, -1) - sum(new_durations), 0)

            # Update frame durations
            self.frame_durations = new_durations

            # Update frame list display with new delays
            if hasattr(self.frame_list, "update_frame_delays"):
                self.frame_list.update_frame_delays(self.frame_durations, True)

            # Update current frame info display
            self.update_display()
        else:
            # Even without variable delay, update the display to show new FPS timing
            self._update_frame_delay_display()

        # Restart timer with new interval if playing
        if self.is_playing:
            interval = int(1000 / fps)  # Convert FPS to milliseconds
            # Apply minimum period if set
            min_period = self.settings.get("period", 0)
            if min_period > 0:
                interval = max(interval, min_period)
            self.timer.start(interval)

        # Regenerate animation to apply new FPS to the actual animation file
        self.regenerate_animation()

    def on_display_scale_changed(self, scale: float):
        """Handle scale changes from wheel events - update the spinbox"""
        # Block signals to prevent recursive calls
        self.scale_spinbox.blockSignals(True)
        # Convert scale factor to percentage (1.0 = 100%)
        percentage = int(scale * 100)
        self.scale_spinbox.setValue(percentage)
        self.scale_spinbox.blockSignals(False)

    def on_scale_percentage_changed(self, percentage: int):
        """Handle preview scale percentage change"""
        # Convert percentage to scale factor (100% = 1.0)
        scale = percentage / 100.0
        self.display.set_scale_factor(scale)

    def on_scale_changed(self, scale: float):
        """Legacy method for compatibility - handle preview scale change"""
        self.display.set_scale_factor(scale)

    def choose_background_color(self):
        """Choose background color"""
        color = QColorDialog.getColor(QColor(127, 127, 127), self, "Choose Background Color")
        if color.isValid():
            self.display.set_background_color(color)
            # Update button color
            self.bg_color_button.setStyleSheet(
                f"background-color: {color.name()}; border: 1px solid gray;"
            )
            # Switch to solid color mode
            self.bg_mode_combo.setCurrentText("Solid Color")

    def on_background_mode_changed(self, mode: str):
        """Handle background mode change"""
        self.display.set_background_mode(mode)
        # Show/hide color button based on mode
        self.bg_color_button.setVisible(mode == "Solid Color")

    def on_transparency_changed(self, checked: bool):
        """Legacy method for compatibility - handle transparency background toggle"""
        self.display.set_transparency_background(checked)

    def regenerate_animation(self):
        """Regenerate animation with current settings and optimized loading"""
        try:
            # Import the extractor to regenerate with new settings
            from core.extractor import Extractor

            # Get current spritesheet and animation info
            current_spritesheet_item = self.parent().extract_tab_widget.listbox_png.currentItem()
            current_animation_item = self.parent().extract_tab_widget.listbox_data.currentItem()

            if not current_spritesheet_item or not current_animation_item:
                QMessageBox.warning(
                    self, "Error", "Please select a spritesheet and animation first."
                )
                return

            # Show progress during regeneration
            current_format = self.settings.get("animation_format", "GIF")
            self.progress_label.setText(f"Generating {current_format}...")
            self.play_button.setEnabled(False)

            # Get the file paths
            spritesheet_path = current_spritesheet_item.data(Qt.ItemDataRole.UserRole)
            if not spritesheet_path:
                QMessageBox.warning(self, "Error", "Could not find spritesheet file path.")
                return

            # Find the metadata file
            spritesheet_name = current_spritesheet_item.text()
            metadata_path = None
            spritemap_info = None
            if spritesheet_name in self.parent().data_dict:
                data_files = self.parent().data_dict[spritesheet_name]
                if isinstance(data_files, dict):
                    if "xml" in data_files:
                        metadata_path = data_files["xml"]
                    elif "txt" in data_files:
                        metadata_path = data_files["txt"]
                    elif "spritemap" in data_files:
                        spritemap_info = data_files["spritemap"]

            # Generate new preview with current settings
            extractor = Extractor(None, "2.0.0", self.parent().settings_manager)

            # Get complete settings including global, spritesheet, and animation overrides
            animation_name = current_animation_item.text()
            complete_settings = self.parent().get_complete_preview_settings(
                spritesheet_name, animation_name
            )

            # Update with current values from the preview window controls
            complete_settings.update(
                {
                    "animation_format": self.settings.get(
                        "animation_format", "GIF"
                    ),  # Use current format selection
                    "fps": self.fps_spinbox.value(),
                    "scale": self.anim_scale_spinbox.value(),  # Use animation scale, not preview scale
                    "crop_option": self.settings.get(
                        "crop_option", "None"
                    ),  # Use current crop option
                    "delay": self.settings.get("delay", 250),  # Include loop delay
                    "period": self.settings.get("period", 0),  # Include minimum period
                    "var_delay": self.settings.get("var_delay", False),  # Include variable delay
                }
            )

            # Include custom indices if specified
            indices_text = self.indices_edit.text().strip()
            if indices_text:
                try:
                    indices = []
                    for part in indices_text.split(","):
                        part = part.strip()
                        if "-" in part:
                            start, end = map(int, part.split("-"))
                            indices.extend(range(start, end + 1))
                        else:
                            indices.append(int(part))
                    complete_settings["indices"] = indices
                    complete_settings["frame_selection"] = "Custom"
                except ValueError:
                    # Invalid format, use all frames
                    complete_settings["frame_selection"] = "All"
            else:
                # No indices specified, use all frames
                complete_settings["frame_selection"] = "All"

            # Include format-specific settings
            if self.settings.get("animation_format") == "GIF":
                complete_settings["threshold"] = self.settings.get("threshold", 0.5)

            # Create temp animation with complete settings
            temp_path = extractor.generate_temp_animation_for_preview(
                atlas_path=spritesheet_path,
                metadata_path=metadata_path,
                settings=complete_settings,
                animation_name=animation_name,
                spritemap_info=spritemap_info,
                spritesheet_label=spritesheet_name,
            )

            if temp_path and os.path.exists(temp_path):
                # Reload with new file
                self.animation_path = temp_path
                self.settings = complete_settings
                self.frames.clear()
                self.frame_durations.clear()
                self.load_animation()
            else:
                QMessageBox.warning(self, "Error", "Failed to regenerate animation.")

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to regenerate animation: {str(e)}")

    def update_format_settings(self):
        """Show/hide settings based on selected format"""
        # All settings are now in animation settings group, no format-specific hiding needed
        pass

    def on_format_changed(self, format_type):
        """Handle format change and regenerate animation"""
        self.settings["animation_format"] = format_type
        self.update_format_settings()

        # Regenerate animation with new format
        self.regenerate_animation()

    def on_delay_changed(self, delay):
        """Handle loop delay change"""
        self.settings["delay"] = delay

        # Update frame delay display to reflect new loop delay timing
        self._update_frame_delay_display()

        # Regenerate animation to apply new loop delay to the actual animation file
        self.regenerate_animation()

    def on_period_changed(self, period):
        """Handle minimum period change"""
        self.settings["period"] = period

        # Update frame delay display to reflect new period timing
        self._update_frame_delay_display()

        # Restart timer with new period if playing
        if self.is_playing:
            fps = self.settings.get("fps", 24)
            interval = int(1000 / fps)

            # Apply minimum period
            if period > 0:
                interval = max(interval, period)
            self.timer.start(interval)

    def on_var_delay_changed(self, enabled):
        """Handle variable delay change"""
        self.settings["var_delay"] = enabled

        # If variable delay is enabled, adjust frame delays while preserving loop delays
        if enabled and self.frame_durations:
            fps = self.settings.get("fps", 24)

            # Calculate variable delays using the same logic as the exporter
            new_durations = []
            for index in range(len(self.frame_durations)):
                # Variable delay: cumulative timing approach
                duration = round((index + 1) * 1000 / fps, -1) - round(index * 1000 / fps, -1)
                new_durations.append(int(duration))

            # Apply loop delay and period to the last frame (like in exporter)
            loop_delay = self.settings.get("delay", 250)
            period = self.settings.get("period", 0)

            new_durations[-1] += loop_delay
            new_durations[-1] += max(round(period, -1) - sum(new_durations), 0)

            # Update frame durations
            self.frame_durations = new_durations

            # Update frame list display with new delays
            if hasattr(self.frame_list, "update_frame_delays"):
                self.frame_list.update_frame_delays(self.frame_durations, True)

            # Update current frame info display
            self.update_display()
        else:
            # Variable delay disabled - update display to show calculated delays
            self._update_frame_delay_display()

        # Regenerate animation to apply new variable delay setting to the actual animation file
        self.regenerate_animation()

    def on_indices_changed(self, indices_text):
        """Handle custom indices change"""
        self.settings["indices_text"] = indices_text
        # Parse indices and update frame checkboxes
        try:
            if indices_text.strip():
                # Parse ranges and individual numbers
                indices = []
                for part in indices_text.split(","):
                    part = part.strip()
                    if "-" in part:
                        start, end = map(int, part.split("-"))
                        indices.extend(range(start, end + 1))
                    else:
                        indices.append(int(part))

                # Clamp indices to valid range
                indices = [i for i in indices if 0 <= i < len(self.frames)]
                self.settings["indices"] = indices

                # Update frame list checkboxes to match the indices
                if hasattr(self.frame_list, "set_checked_frames"):
                    self.frame_list.set_checked_frames(indices)
            else:
                self.settings.pop("indices", None)
                # If no indices, check all frames
                if hasattr(self.frame_list, "set_checked_frames") and self.frames:
                    all_indices = list(range(len(self.frames)))
                    self.frame_list.set_checked_frames(all_indices)
        except ValueError:
            # Invalid format, ignore for now
            pass

    def on_anim_scale_changed(self, scale):
        """Handle animation scale change"""
        self.settings["scale"] = scale
        self.regenerate_animation()

    def on_crop_changed(self, crop_option):
        """Handle crop option change"""
        self.settings["crop_option"] = crop_option
        self.regenerate_animation()

    def on_threshold_changed(self, threshold):
        """Handle threshold change"""
        self.settings["threshold"] = threshold
        self.regenerate_animation()

    def _restart_normal_timer(self):
        """Restart the timer with normal FPS timing after loop delay"""
        if self.is_playing:
            fps = self.settings.get("fps", 24)
            interval = int(1000 / fps)
            # Apply minimum period if set
            min_period = self.settings.get("period", 0)
            if min_period > 0:
                interval = max(interval, min_period)
            self.timer.start(interval)

    def _loop_to_first_frame(self):
        """Go to first checked frame after loop delay and restart normal timer"""
        if self.is_playing:
            checked_frames = self.get_checked_frame_indices()
            if checked_frames:
                self.goto_frame(checked_frames[0])
                # Restart normal timer
                self._restart_normal_timer()

    def _update_frame_delay_display(self):
        """Update frame delay display in the frame list based on current settings"""
        if not self.frame_durations or not hasattr(self, "frame_list"):
            return

        # Create display delays based on current settings
        fps = self.settings.get("fps", 24)
        loop_delay = self.settings.get("delay", 250)
        var_delay = self.settings.get("var_delay", False)
        period = self.settings.get("period", 0)

        display_delays = []

        if var_delay:
            # Use actual frame durations when variable delay is enabled
            display_delays = self.frame_durations.copy()
        else:
            # Calculate what the delays would be based on FPS and settings (like in exporter)
            # Fixed delay for all frames
            fixed_delay = round(1000 / fps, -1)
            display_delays = [int(fixed_delay)] * len(self.frame_durations)

            # Apply loop delay and period to the last frame (like in exporter)
            display_delays[-1] += loop_delay
            display_delays[-1] += max(round(period, -1) - sum(display_delays), 0)

        # Update the frame list display
        if hasattr(self.frame_list, "update_frame_delays"):
            self.frame_list.update_frame_delays(display_delays, True)

        # Update current frame info if we're showing it
        self.update_display()
