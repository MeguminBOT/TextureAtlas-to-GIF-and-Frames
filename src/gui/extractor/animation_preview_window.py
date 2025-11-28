#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Animation preview dialog for viewing and adjusting extracted animations.

Provides a real-time preview of GIF, WebP, and APNG animations with playback
controls, frame selection, and export settings. Runs frame loading in a
background thread to maintain UI responsiveness.
"""

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

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

MAX_FRAMES_IN_MEMORY = 100
FRAME_CACHE_SIZE = 20


class AnimationProcessor(QThread):
    """Background thread for loading animation frames with optimized memory.

    Reads animation files frame-by-frame and emits signals as each frame
    is converted to a QPixmap. Supports early termination via ``stop()``.

    Signals:
        frame_processed(int, QPixmap): Emitted when a frame is ready.
        processing_complete(): Emitted when all frames are loaded.
        error_occurred(str): Emitted with an error message on failure.
        progress_updated(int, int): Emitted with current and total frame count.

    Attributes:
        frames: List of loaded QPixmap frames.
        frame_durations: Per-frame display durations in milliseconds.
    """

    frame_processed = Signal(int, QPixmap)
    processing_complete = Signal()
    error_occurred = Signal(str)
    progress_updated = Signal(int, int)

    def __init__(self, animation_path: str, settings: dict):
        """Initialize the animation processor.

        Args:
            animation_path: Path to the animation file (GIF, WebP, or APNG).
            settings: Animation settings dictionary (currently unused).
        """
        super().__init__()
        self.animation_path = animation_path
        self.settings = settings
        self.frames: List[QPixmap] = []
        self.frame_durations: List[int] = []
        self._stop_requested = False

    def stop(self):
        """Request to stop processing."""
        self._stop_requested = True

    def run(self):
        """Process animation frames in background with optimizations."""
        try:
            if not PIL_AVAILABLE:
                self.error_occurred.emit("PIL/Pillow not available")
                return

            with Image.open(self.animation_path) as img:
                frame_count = getattr(img, "n_frames", 1)

                self.frames = [QPixmap()] * frame_count
                self.frame_durations = [100] * frame_count

                for frame_idx in range(frame_count):
                    if self._stop_requested:
                        return

                    img.seek(frame_idx)

                    duration = getattr(img, "info", {}).get("duration", 100)
                    self.frame_durations[frame_idx] = duration

                    frame_copy = img.copy()
                    if frame_copy.mode != "RGBA":
                        frame_copy = frame_copy.convert("RGBA")

                    w, h = frame_copy.size
                    bytes_data = frame_copy.tobytes("raw", "RGBA")
                    qimg = QImage(bytes_data, w, h, QImage.Format.Format_RGBA8888)
                    pixmap = QPixmap.fromImage(qimg)

                    if hasattr(pixmap, "toImage"):
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
                    self.frame_processed.emit(frame_idx, pixmap)
                    self.progress_updated.emit(frame_idx + 1, frame_count)
                    self.msleep(1)

            if not self._stop_requested:
                self.processing_complete.emit()

        except Exception as e:
            self.error_occurred.emit(f"Failed to load animation: {str(e)}")


class FrameListWidget(QListWidget):
    """List widget for frame navigation with checkbox selection.

    Displays all animation frames with optional delay labels and checkboxes
    for including or excluding frames from playback and export.

    Signals:
        frame_selected(int): Emitted when a frame is clicked.
        frame_checked(int, bool): Emitted when a checkbox is toggled.
    """

    frame_selected = Signal(int)
    frame_checked = Signal(int, bool)

    def __init__(self):
        super().__init__()
        self.setMaximumWidth(140)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.currentItemChanged.connect(self._on_selection_changed)
        self.itemChanged.connect(self._on_item_changed)

    def set_frame_count(self, count: int, frame_durations: List[int] = None):
        """Populate the list with frame entries.

        Args:
            count: Number of frames to display.
            frame_durations: Optional per-frame delays in milliseconds.
        """
        self.clear()
        for i in range(count):
            if frame_durations and i < len(frame_durations):
                delay_ms = frame_durations[i]
                frame_text = f"Frame {i + 1} ({delay_ms}ms)"
            else:
                frame_text = f"Frame {i + 1}"

            item = QListWidgetItem(frame_text)
            item.setData(Qt.ItemDataRole.UserRole, i)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.addItem(item)

    def update_frame_delays(self, frame_durations: List[int], show_delays: bool = True):
        """Refresh delay labels on existing frame entries.

        Args:
            frame_durations: Per-frame delays in milliseconds.
            show_delays: Whether to display delays in the label text.
        """
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
        """Highlight a frame in the list.

        Args:
            frame_index: Zero-based index of the frame to select.
        """
        if 0 <= frame_index < self.count():
            self.setCurrentRow(frame_index)

    def get_checked_frames(self):
        """Return indices of all checked frames.

        Returns:
            List of zero-based indices for frames whose checkbox is checked.
        """
        checked_frames = []
        for i in range(self.count()):
            item = self.item(i)
            if item and item.checkState() == Qt.CheckState.Checked:
                checked_frames.append(i)
        return checked_frames

    def set_checked_frames(self, frame_indices):
        """Check only the specified frames, unchecking all others.

        Args:
            frame_indices: Iterable of zero-based frame indices to check.
        """
        for i in range(self.count()):
            item = self.item(i)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)

        for frame_index in frame_indices:
            if 0 <= frame_index < self.count():
                item = self.item(frame_index)
                if item:
                    item.setCheckState(Qt.CheckState.Checked)

    def _on_selection_changed(self, current, previous):
        """Emit frame_selected when the list selection changes.

        Args:
            current: Newly selected QListWidgetItem.
            previous: Previously selected QListWidgetItem.
        """
        if current:
            frame_index = current.data(Qt.ItemDataRole.UserRole)
            if frame_index is not None:
                self.frame_selected.emit(frame_index)

    def _on_item_changed(self, item):
        """Emit frame_checked when a checkbox state changes.

        Args:
            item: The QListWidgetItem whose checkbox was toggled.
        """
        frame_index = item.data(Qt.ItemDataRole.UserRole)
        if frame_index is not None:
            is_checked = item.checkState() == Qt.CheckState.Checked
            self.frame_checked.emit(frame_index, is_checked)


class AnimationDisplay(QScrollArea):
    """Scrollable widget for displaying animation frames with zoom support.

    Supports solid-color and checkered transparency backgrounds as well as
    Ctrl+wheel zoom. Caches scaled pixmaps to minimize redraw cost.

    Signals:
        scale_changed(float): Emitted when the zoom level changes.
    """

    scale_changed = Signal(float)

    def __init__(self):
        super().__init__()

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: transparent;")
        self.image_label.setScaledContents(False)

        self.setWidget(self.image_label)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setMinimumSize(600, 500)
        self.setStyleSheet("border: 1px solid gray; background-color: transparent;")

        self._background_color = QColor(127, 127, 127, 255)
        self._background_mode = "None"
        self._checkered_pattern = None
        self._current_pixmap = None
        self._scale_factor = 1.0
        self._original_size = None

        self._cached_scaled_pixmap = None
        self._cached_scale = None

        self.image_label.installEventFilter(self)

    def eventFilter(self, source, event):
        """Forward wheel events from the image label to this widget.

        Args:
            source: The watched QObject.
            event: The incoming QEvent.

        Returns:
            True if the event was handled, False otherwise.
        """
        if source == self.image_label and event.type() == event.Type.Wheel:
            return self.wheelEvent(event)
        return super().eventFilter(source, event)

    def wheelEvent(self, event):
        """Zoom the frame on Ctrl+scroll, scroll otherwise.

        Args:
            event: QWheelEvent containing scroll delta and modifiers.

        Returns:
            True if zooming was applied, otherwise the parent result.
        """
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            angle_delta = event.angleDelta().y()
            zoom_factor = 1.1 if angle_delta > 0 else 1.0 / 1.1
            new_scale = self._scale_factor * zoom_factor
            new_scale = max(0.1, min(5.0, new_scale))
            old_scale = self._scale_factor
            self.set_scale_factor(new_scale)
            if abs(old_scale - new_scale) > 0.001:
                self.scale_changed.emit(new_scale)

            event.accept()
            return True
        else:
            return super().wheelEvent(event)

    def set_background_color(self, color: QColor):
        """Set a solid background color and switch to Solid Color mode.

        Args:
            color: QColor to fill behind the frame.
        """
        self._background_color = color
        self._background_mode = "Solid Color"
        self.setStyleSheet("border: 1px solid gray; background-color: transparent;")
        self.update_display()

    def set_background_mode(self, mode: str):
        """Switch the background rendering mode.

        Args:
            mode: One of 'None', 'Solid Color', or 'Transparency Pattern'.
        """
        self._background_mode = mode
        if mode == "Transparency Pattern":
            self._create_checkered_pattern()

        self.setStyleSheet("border: 1px solid gray; background-color: transparent;")
        self.update_display()

    def set_transparency_background(self, show_transparency: bool):
        """Toggle transparency pattern on or off.

        Deprecated: use ``set_background_mode()`` instead.

        Args:
            show_transparency: If True, enable the checkered pattern.
        """
        if show_transparency:
            self.set_background_mode("Transparency Pattern")
        else:
            self.set_background_mode("Solid Color")

    def _create_checkered_pattern(self):
        """Build a repeating checkered tile for transparency backgrounds."""
        checker_size = 16
        pattern_size = checker_size * 2

        self._checkered_pattern = QPixmap(pattern_size, pattern_size)
        painter = QPainter(self._checkered_pattern)

        light_gray = QColor(240, 240, 240)
        white = QColor(255, 255, 255)

        for x in range(0, pattern_size, checker_size):
            for y in range(0, pattern_size, checker_size):
                is_light = ((x // checker_size) + (y // checker_size)) % 2 == 0
                color = light_gray if is_light else white
                painter.fillRect(x, y, checker_size, checker_size, color)

        painter.end()

    def get_scale_factor(self):
        """Return the current zoom multiplier.

        Returns:
            Zoom factor where 1.0 is 100%.
        """
        return self._scale_factor

    def set_scale_factor(self, scale: float):
        """Apply a new zoom level and refresh the display.

        Args:
            scale: Zoom multiplier (1.0 = 100%).
        """
        if abs(self._scale_factor - scale) > 0.001:
            self._scale_factor = scale

            self._cached_scaled_pixmap = None
            self._cached_scale = None

            self.update_display()

    def set_frame(self, pixmap: QPixmap):
        """Display a new frame pixmap at the current zoom level.

        Args:
            pixmap: QPixmap to render in the scroll area.
        """
        self._current_pixmap = pixmap
        self._cached_scaled_pixmap = None
        self._cached_scale = None

        if pixmap and not pixmap.isNull():
            self._original_size = pixmap.size()

        self.update_display()

    def update_display(self):
        """Redraw the current frame with scaling and background applied."""
        if not self._current_pixmap or self._current_pixmap.isNull():
            self.image_label.clear()
            return

        pixmap_size = self._current_pixmap.size()
        scaled_width = int(pixmap_size.width() * self._scale_factor)
        scaled_height = int(pixmap_size.height() * self._scale_factor)
        scaled_size = QSize(scaled_width, scaled_height)

        if (
            self._cached_scaled_pixmap
            and self._cached_scale
            and abs(self._cached_scale - self._scale_factor) < 0.001
            and self._cached_scaled_pixmap.size() == scaled_size
        ):
            display_pixmap = self._cached_scaled_pixmap
        else:
            if self._scale_factor == 1.0:
                display_pixmap = self._current_pixmap
            else:
                display_pixmap = self._current_pixmap.scaled(
                    scaled_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )

                self._cached_scaled_pixmap = display_pixmap
                self._cached_scale = self._scale_factor

        if self._background_mode == "Transparency Pattern" and self._checkered_pattern:
            final_pixmap = QPixmap(display_pixmap.size())
            final_pixmap.fill(Qt.GlobalColor.transparent)

            painter = QPainter(final_pixmap)

            pattern_size = self._checkered_pattern.size()
            for x in range(0, final_pixmap.width(), pattern_size.width()):
                for y in range(0, final_pixmap.height(), pattern_size.height()):
                    painter.drawPixmap(x, y, self._checkered_pattern)

            painter.drawPixmap(0, 0, display_pixmap)
            painter.end()

            self.image_label.setPixmap(final_pixmap)
        elif self._background_mode == "Solid Color":
            final_pixmap = QPixmap(display_pixmap.size())
            final_pixmap.fill(self._background_color)

            painter = QPainter(final_pixmap)
            painter.drawPixmap(0, 0, display_pixmap)
            painter.end()

            self.image_label.setPixmap(final_pixmap)
        else:
            self.image_label.setPixmap(display_pixmap)

        self.image_label.resize(display_pixmap.size())

    def clear_cache(self):
        """Discard cached scaled pixmaps to free memory."""
        self._cached_scaled_pixmap = None
        self._cached_scale = None


class AnimationPreviewWindow(QDialog):
    """Dialog for previewing and configuring animation playback.

    Loads frames in a background thread and provides controls for FPS,
    scale, looping, frame selection, and background display. Emits
    ``settings_saved`` when the user closes and saves.

    Signals:
        settings_saved(dict): Emitted with the chosen export settings.

    Attributes:
        animation_path: Path to the animation file being previewed.
        settings: Dictionary of current animation settings.
        frames: List of loaded QPixmap frames.
        frame_durations: Per-frame display durations in milliseconds.
    """

    settings_saved = Signal(dict)

    def __init__(self, parent, animation_path: str, settings: dict):
        """Create the preview dialog and start loading frames.

        Args:
            parent: Parent widget (typically the main application window).
            animation_path: Path to the animation file to preview.
            settings: Initial animation settings dictionary.
        """
        super().__init__(parent)
        self.animation_path = animation_path
        self.settings = settings.copy() if settings else {}

        self.frames: List[QPixmap] = []
        self.frame_durations: List[int] = []
        self.current_frame = 0
        self.is_playing = False
        self.is_loading = False
        self.processor = None
        self._loop_delay_applied = False

        self._last_update_time = 0
        self._update_throttle = 16

        self.display = None
        self.frame_list = None
        self.play_button = None
        self.position_slider = None
        self.timer = None
        self.progress_label = None

        self.fps_spinbox = None
        self.scale_spinbox = None
        self.loop_checkbox = None

        self.init_ui()
        self.load_animation()

    def init_ui(self):
        """Build the dialog layout and connect signals."""
        self.setWindowTitle("Animation Preview")
        self.setMinimumSize(960, 480)
        self.resize(1366, 768)

        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )

        main_layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        left_panel = self.create_frame_panel()
        splitter.addWidget(left_panel)

        center_panel = self.create_display_panel()
        splitter.addWidget(center_panel)

        right_panel = self.create_settings_panel()
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)

        controls_layout = self.create_controls()
        main_layout.addLayout(controls_layout)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.reject)
        button_layout.addWidget(close_button)

        close_save_button = QPushButton("Close and Save")
        close_save_button.clicked.connect(self.close_and_save)
        button_layout.addWidget(close_save_button)

        main_layout.addLayout(button_layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.next_frame)

        self.update_format_settings()

    def close_and_save(self):
        """Emit settings_saved with current settings and close the dialog."""
        checked_frames = self.get_checked_frame_indices()

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

        if len(checked_frames) < len(self.frames) and checked_frames:
            save_settings["indices"] = checked_frames

        self.settings_saved.emit(save_settings)

        self.accept()

    def create_frame_panel(self) -> QWidget:
        """Build the left panel containing the frame list.

        Returns:
            QWidget with the frame list layout.
        """
        panel = QWidget()
        layout = QVBoxLayout(panel)

        layout.addWidget(QLabel("Frames:"))

        self.frame_list = FrameListWidget()
        self.frame_list.frame_selected.connect(self.goto_frame)
        self.frame_list.frame_checked.connect(self.on_frame_checked)
        layout.addWidget(self.frame_list)

        return panel

    def create_display_panel(self) -> QWidget:
        """Build the center panel containing the animation display.

        Returns:
            QWidget with the animation display and info labels.
        """
        panel = QWidget()
        layout = QVBoxLayout(panel)

        self.display = AnimationDisplay()

        self.display.setToolTip("Hold Ctrl and use mouse wheel to zoom in/out")

        self.display.scale_changed.connect(self.on_display_scale_changed)

        layout.addWidget(self.display)

        info_layout = QHBoxLayout()

        self.frame_info_label = QLabel("Frame 1 / 1")
        self.frame_info_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        info_layout.addWidget(self.frame_info_label)

        self.progress_label = QLabel("")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.progress_label.setStyleSheet("color: #666;")
        info_layout.addWidget(self.progress_label)

        layout.addLayout(info_layout)

        return panel

    def create_settings_panel(self) -> QWidget:
        """Build the right panel containing format and playback controls.

        Returns:
            QWidget with grouped settings controls.
        """
        panel = QWidget()
        panel.setMaximumWidth(300)
        layout = QVBoxLayout(panel)

        format_group = QGroupBox("Animation Format")
        format_layout = QGridLayout(format_group)

        format_layout.addWidget(QLabel("Format:"), 0, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["GIF", "WebP", "APNG"])
        self.format_combo.setCurrentText(self.settings.get("animation_format", "GIF"))
        self.format_combo.currentTextChanged.connect(self.on_format_changed)
        format_layout.addWidget(self.format_combo, 0, 1)

        layout.addWidget(format_group)

        playback_group = QGroupBox("Animation Settings")
        playback_layout = QGridLayout(playback_group)

        playback_layout.addWidget(QLabel("FPS:"), 0, 0)
        self.fps_spinbox = QSpinBox()
        self.fps_spinbox.setRange(1, 60)
        self.fps_spinbox.setValue(self.settings.get("fps", 24))
        self.fps_spinbox.valueChanged.connect(self.on_fps_changed)
        playback_layout.addWidget(self.fps_spinbox, 0, 1)

        playback_layout.addWidget(QLabel("Loop Delay (ms):"), 1, 0)
        self.delay_spinbox = QSpinBox()
        self.delay_spinbox.setRange(0, 5000)
        self.delay_spinbox.setValue(self.settings.get("delay", 250))
        self.delay_spinbox.valueChanged.connect(self.on_delay_changed)
        playback_layout.addWidget(self.delay_spinbox, 1, 1)

        playback_layout.addWidget(QLabel("Min Period (ms):"), 2, 0)
        self.period_spinbox = QSpinBox()
        self.period_spinbox.setRange(0, 10000)
        self.period_spinbox.setValue(self.settings.get("period", 0))
        self.period_spinbox.valueChanged.connect(self.on_period_changed)
        playback_layout.addWidget(self.period_spinbox, 2, 1)

        self.var_delay_checkbox = QCheckBox("Variable delay")
        self.var_delay_checkbox.setChecked(self.settings.get("var_delay", False))
        self.var_delay_checkbox.toggled.connect(self.on_var_delay_changed)
        playback_layout.addWidget(self.var_delay_checkbox, 3, 0, 1, 2)

        playback_layout.addWidget(QLabel("Scale:"), 4, 0)
        self.anim_scale_spinbox = QDoubleSpinBox()
        self.anim_scale_spinbox.setRange(0.1, 10.0)
        self.anim_scale_spinbox.setSingleStep(0.1)
        self.anim_scale_spinbox.setValue(self.settings.get("scale", 1.0))
        self.anim_scale_spinbox.valueChanged.connect(self.on_anim_scale_changed)
        playback_layout.addWidget(self.anim_scale_spinbox, 4, 1)

        playback_layout.addWidget(QLabel("Indices:"), 5, 0)
        self.indices_edit = QLineEdit()
        self.indices_edit.setPlaceholderText(
            "e.g., 0,2,4 or 0-5 (leave empty for all frames)"
        )
        self.indices_edit.textChanged.connect(self.on_indices_changed)
        playback_layout.addWidget(self.indices_edit, 5, 1)

        playback_layout.addWidget(QLabel("Crop Option:"), 6, 0)
        self.crop_combo = QComboBox()
        self.crop_combo.addItems(["None", "Animation based", "Frame based"])
        self.crop_combo.setCurrentText(self.settings.get("crop_option", "None"))
        self.crop_combo.currentTextChanged.connect(self.on_crop_changed)
        playback_layout.addWidget(self.crop_combo, 6, 1)

        playback_layout.addWidget(QLabel("Threshold:"), 7, 0)
        self.threshold_spinbox = QDoubleSpinBox()
        self.threshold_spinbox.setRange(0.0, 1.0)
        self.threshold_spinbox.setSingleStep(0.1)
        self.threshold_spinbox.setValue(self.settings.get("threshold", 0.5))
        self.threshold_spinbox.valueChanged.connect(self.on_threshold_changed)
        playback_layout.addWidget(self.threshold_spinbox, 7, 1)

        layout.addWidget(playback_group)

        display_group = QGroupBox("Display")
        display_layout = QGridLayout(display_group)

        self.loop_checkbox = QCheckBox("Loop preview")
        self.loop_checkbox.setChecked(True)
        display_layout.addWidget(self.loop_checkbox, 0, 0, 1, 2)

        display_layout.addWidget(QLabel("Preview Zoom:"), 1, 0)
        self.scale_spinbox = QSpinBox()
        self.scale_spinbox.setRange(10, 500)
        self.scale_spinbox.setSingleStep(10)
        self.scale_spinbox.setValue(100)
        self.scale_spinbox.setSuffix("%")
        self.scale_spinbox.setToolTip(
            "Preview zoom level (also controlled by Ctrl+Mouse Wheel)"
        )
        self.scale_spinbox.valueChanged.connect(self.on_scale_percentage_changed)
        display_layout.addWidget(self.scale_spinbox, 1, 1)

        display_layout.addWidget(QLabel("Background:"), 2, 0)
        bg_layout = QVBoxLayout()

        self.bg_mode_combo = QComboBox()
        self.bg_mode_combo.addItems(["None", "Solid Color", "Transparency Pattern"])
        self.bg_mode_combo.setCurrentText("None")
        self.bg_mode_combo.currentTextChanged.connect(self.on_background_mode_changed)
        bg_layout.addWidget(self.bg_mode_combo)

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

        export_group = QGroupBox("Export")
        export_layout = QVBoxLayout(export_group)

        self.regenerate_button = QPushButton("Force Regenerate Animation")
        self.regenerate_button.clicked.connect(self.regenerate_animation)
        export_layout.addWidget(self.regenerate_button)

        layout.addWidget(export_group)

        layout.addStretch()

        self.update_format_settings()

        return panel

    def create_controls(self) -> QVBoxLayout:
        """Build playback control buttons and position slider.

        Returns:
            QVBoxLayout containing the playback controls.
        """
        controls_layout = QVBoxLayout()

        button_layout = QHBoxLayout()
        button_layout.addStretch()

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

        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel("Position:"))
        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setMinimum(0)
        self.position_slider.valueChanged.connect(self.on_position_changed)
        slider_layout.addWidget(self.position_slider)
        controls_layout.addLayout(slider_layout)

        return controls_layout

    def load_animation(self):
        """Start loading animation frames in a background thread."""
        if not os.path.exists(self.animation_path):
            QMessageBox.warning(
                self, "Error", f"Animation file not found: {self.animation_path}"
            )
            return

        if self.processor and self.processor.isRunning():
            self.processor.stop()
            self.processor.wait(1000)

        self.frames.clear()
        self.frame_durations.clear()

        self.is_loading = True
        self.progress_label.setText("Loading...")

        if self.play_button:
            self.play_button.setEnabled(False)

        self.processor = AnimationProcessor(self.animation_path, self.settings)
        self.processor.frame_processed.connect(self.on_frame_processed)
        self.processor.processing_complete.connect(self.on_processing_complete)
        self.processor.error_occurred.connect(self.on_processing_error)
        self.processor.progress_updated.connect(self.on_progress_updated)
        self.processor.start()

    def on_progress_updated(self, current: int, total: int):
        """Update the progress label during frame loading.

        Args:
            current: Number of frames loaded so far.
            total: Total number of frames in the animation.
        """
        if self.progress_label:
            percentage = int((current / total) * 100) if total > 0 else 0
            self.progress_label.setText(f"Loading... {percentage}% ({current}/{total})")

    def on_frame_processed(self, frame_index: int, pixmap: QPixmap):
        """Store a loaded frame and update the display if visible.

        Args:
            frame_index: Zero-based index of the processed frame.
            pixmap: The converted QPixmap for this frame.
        """
        import time

        current_time = time.time() * 1000

        while len(self.frames) <= frame_index:
            self.frames.append(QPixmap())

        self.frames[frame_index] = pixmap

        if (
            frame_index == 0
            or current_time - self._last_update_time > self._update_throttle
        ):
            if frame_index == self.current_frame or (
                frame_index == 0 and self.current_frame == 0
            ):
                self.display.set_frame(pixmap)
                self._last_update_time = current_time

    def on_processing_complete(self):
        """Finalize frame loading and enable playback controls."""
        frame_count = len(self.frames)

        self.is_loading = False
        self.progress_label.setText(f"Loaded {frame_count} frames")

        if self.play_button:
            self.play_button.setEnabled(True)

        if self.processor and hasattr(self.processor, "frame_durations"):
            self.frame_durations = self.processor.frame_durations.copy()

        if self.frame_durations:
            self.frame_list.set_frame_count(frame_count, self.frame_durations)
        else:
            self.frame_list.set_frame_count(frame_count)

        if "indices" in self.settings and self.settings["indices"]:
            self.frame_list.set_checked_frames(self.settings["indices"])

        self.position_slider.setMaximum(max(0, frame_count - 1))

        if self.frames:
            self.current_frame = 0
            self.update_display()
            self.frame_list.select_frame(0)

        print(f"Animation loaded efficiently: {frame_count} frames")

    def on_processing_error(self, error_message: str):
        """Display an error and re-enable controls on load failure.

        Args:
            error_message: Description of the error that occurred.
        """
        self.is_loading = False
        self.progress_label.setText("Error loading animation")

        if self.play_button:
            self.play_button.setEnabled(True)

        QMessageBox.warning(self, "Error", error_message)

    def cleanup_resources(self):
        """Stop the processor thread, timer, and release frames."""
        if self.processor and self.processor.isRunning():
            self.processor.stop()
            self.processor.wait(1000)

        if self.timer and self.timer.isActive():
            self.timer.stop()

        if hasattr(self.display, "clear_cache"):
            self.display.clear_cache()

        self.frames.clear()
        self.frame_durations.clear()

        self.current_frame = 0
        self.is_playing = False
        self.is_loading = False

    def closeEvent(self, event):
        """Release resources before the dialog closes.

        Args:
            event: QCloseEvent for the dialog.
        """
        self.cleanup_resources()
        super().closeEvent(event)

    def update_display(self):
        """Show the current frame and update UI state."""

        if 0 <= self.current_frame < len(self.frames):
            pixmap = self.frames[self.current_frame]
            self.display.set_frame(pixmap)

            total_frames = len(self.frames)
            frame_info = f"Frame {self.current_frame + 1} / {total_frames}"

            if self.frame_durations and self.current_frame < len(self.frame_durations):
                delay_ms = self.frame_durations[self.current_frame]
                frame_info += f" ({delay_ms}ms)"

            self.frame_info_label.setText(frame_info)

            self.position_slider.blockSignals(True)
            self.position_slider.setValue(self.current_frame)
            self.position_slider.blockSignals(False)

            self.frame_list.select_frame(self.current_frame)

    def toggle_playback(self):
        """Start or pause animation playback."""
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def play(self):
        """Begin frame-by-frame playback at the configured FPS."""
        if not self.frames:
            return

        self.is_playing = True
        self.play_button.setText("Pause")

        self._loop_delay_applied = False
        fps = self.settings.get("fps", 24)

        interval = int(1000 / fps)
        min_period = self.settings.get("period", 0)
        if min_period > 0:
            interval = max(interval, min_period)

        self.timer.start(interval)

    def pause(self):
        """Stop playback and reset the button label."""
        self.is_playing = False
        self.play_button.setText("Play")
        self.timer.stop()

        self._loop_delay_applied = False

    def next_frame(self):
        """Advance to the next frame, skipping unchecked frames during playback."""
        if not self.frames:
            return

        if self.is_playing:
            self.goto_next_checked_frame()
        else:
            self.current_frame += 1

            if self.current_frame >= len(self.frames):
                if self.loop_checkbox.isChecked():
                    self.current_frame = 0
                    if self.is_playing:
                        loop_delay = self.settings.get("delay", 250)
                        if loop_delay > 0:
                            self.timer.stop()
                            self.timer.start(loop_delay)
                            self.update_display()
                            return
                else:
                    self.current_frame = len(self.frames) - 1
                    self.pause()

            self.update_display()

            if self.is_playing:
                fps = self.settings.get("fps", 24)
                interval = int(1000 / fps)
                min_period = self.settings.get("period", 0)
                if min_period > 0:
                    interval = max(interval, min_period)
                self.timer.start(interval)

    def previous_frame(self):
        """Step back to the previous frame."""
        if not self.frames:
            return

        self.current_frame -= 1
        if self.current_frame < 0:
            self.current_frame = max(0, len(self.frames) - 1)

        self.update_display()

    def goto_frame(self, frame_index: int):
        """Display a specific frame.

        Args:
            frame_index: Zero-based index of the frame to show.
        """
        if 0 <= frame_index < len(self.frames):
            self.current_frame = frame_index
            self.update_display()

    def on_frame_checked(self, frame_index, checked):
        """Handle frame checkbox toggling.

        Args:
            frame_index: Zero-based index of the toggled frame.
            checked: True if the checkbox is now checked.
        """
        if not checked and self.current_frame == frame_index:
            self.goto_next_checked_frame()

        self.update_indices_text_from_checkboxes()

    def update_indices_text_from_checkboxes(self):
        """Synchronize the indices text field with checkbox states."""
        checked_frames = self.get_checked_frame_indices()
        total_frames = len(self.frames)

        if len(checked_frames) == total_frames:
            self.indices_edit.blockSignals(True)
            self.indices_edit.setText("")
            self.indices_edit.blockSignals(False)
            self.settings.pop("indices", None)
        else:
            indices_text = self.compress_indices_to_text(checked_frames)
            self.indices_edit.blockSignals(True)
            self.indices_edit.setText(indices_text)
            self.indices_edit.blockSignals(False)
            self.settings["indices"] = checked_frames

    def compress_indices_to_text(self, indices):
        """Convert a list of indices to a compact range string.

        Args:
            indices: Iterable of integer frame indices.

        Returns:
            String like '0,2-5,7' representing the indices.
        """
        if not indices:
            return ""

        indices = sorted(set(indices))
        result = []
        i = 0

        while i < len(indices):
            start = indices[i]
            end = start

            while i + 1 < len(indices) and indices[i + 1] == indices[i] + 1:
                i += 1
                end = indices[i]

            if start == end:
                result.append(str(start))
            else:
                result.append(f"{start}-{end}")

            i += 1

        return ",".join(result)

    def get_checked_frame_indices(self):
        """Return a list of checked frame indices from the frame list.

        Returns:
            List of zero-based indices for all checked frames.
        """
        return self.frame_list.get_checked_frames()

    def goto_next_checked_frame(self):
        """Advance to the next checked frame, looping if enabled."""
        checked_frames = self.get_checked_frame_indices()
        if not checked_frames:
            return

        next_frames = [f for f in checked_frames if f > self.current_frame]
        if next_frames:
            self.goto_frame(next_frames[0])
            self._loop_delay_applied = False
        else:
            if (
                self.is_playing
                and self.loop_checkbox.isChecked()
                and not self._loop_delay_applied
            ):
                loop_delay = self.settings.get("delay", 250)
                if loop_delay > 0:
                    self.timer.stop()
                    QTimer.singleShot(loop_delay, self._loop_to_first_frame)
                    self._loop_delay_applied = True
                    return

            self.goto_frame(checked_frames[0])
            if self.is_playing and self.loop_checkbox.isChecked():
                self._loop_delay_applied = True

    def goto_previous_checked_frame(self):
        """Return to the previous checked frame."""
        checked_frames = self.get_checked_frame_indices()
        if not checked_frames:
            return

        prev_frames = [f for f in checked_frames if f < self.current_frame]
        if prev_frames:
            self.goto_frame(prev_frames[-1])
        else:
            self.goto_frame(checked_frames[-1])

    def on_position_changed(self, position: int):
        """Jump to the frame indicated by the position slider.

        Args:
            position: Slider value representing the frame index.
        """
        self.goto_frame(position)

    def on_fps_changed(self, fps: int):
        """Update playback speed and regenerate the animation.

        Args:
            fps: New frames per second value.
        """
        self.settings["fps"] = fps

        if self.settings.get("var_delay", False) and self.frame_durations:
            new_durations = []
            for index in range(len(self.frame_durations)):
                duration = round((index + 1) * 1000 / fps, -1) - round(
                    index * 1000 / fps, -1
                )
                new_durations.append(int(duration))

            loop_delay = self.settings.get("delay", 250)
            period = self.settings.get("period", 0)

            new_durations[-1] += loop_delay
            new_durations[-1] += max(round(period, -1) - sum(new_durations), 0)

            self.frame_durations = new_durations

            if hasattr(self.frame_list, "update_frame_delays"):
                self.frame_list.update_frame_delays(self.frame_durations, True)

            self.update_display()
        else:
            self._update_frame_delay_display()

        if self.is_playing:
            interval = int(1000 / fps)
            min_period = self.settings.get("period", 0)
            if min_period > 0:
                interval = max(interval, min_period)
            self.timer.start(interval)

        self.regenerate_animation()

    def on_display_scale_changed(self, scale: float):
        """Sync the zoom spinbox when the display is scrolled.

        Args:
            scale: New zoom factor from the display widget.
        """
        self.scale_spinbox.blockSignals(True)
        percentage = int(scale * 100)
        self.scale_spinbox.setValue(percentage)
        self.scale_spinbox.blockSignals(False)

    def on_scale_percentage_changed(self, percentage: int):
        """Apply a new preview zoom level from the spinbox.

        Args:
            percentage: Zoom percentage (100 = 100%).
        """
        scale = percentage / 100.0
        self.display.set_scale_factor(scale)

    def on_scale_changed(self, scale: float):
        """Apply a preview zoom level directly.

        Deprecated: use ``on_scale_percentage_changed()`` instead.

        Args:
            scale: Zoom factor (1.0 = 100%).
        """
        self.display.set_scale_factor(scale)

    def choose_background_color(self):
        """Open a color dialog and apply the chosen background."""
        color = QColorDialog.getColor(
            QColor(127, 127, 127), self, "Choose Background Color"
        )
        if color.isValid():
            self.display.set_background_color(color)
            self.bg_color_button.setStyleSheet(
                f"background-color: {color.name()}; border: 1px solid gray;"
            )
            self.bg_mode_combo.setCurrentText("Solid Color")

    def on_background_mode_changed(self, mode: str):
        """Switch the display background and show/hide the color button.

        Args:
            mode: One of 'None', 'Solid Color', or 'Transparency Pattern'.
        """
        self.display.set_background_mode(mode)
        self.bg_color_button.setVisible(mode == "Solid Color")

    def on_transparency_changed(self, checked: bool):
        """Toggle transparency background display.

        Deprecated: use ``on_background_mode_changed()`` instead.

        Args:
            checked: True to show the transparency pattern.
        """
        self.display.set_transparency_background(checked)

    def regenerate_animation(self):
        """Re-export the animation with current settings and reload it."""
        try:
            from core.extractor import Extractor

            current_spritesheet_item = (
                self.parent().extract_tab_widget.listbox_png.currentItem()
            )
            current_animation_item = (
                self.parent().extract_tab_widget.listbox_data.currentItem()
            )

            if not current_spritesheet_item or not current_animation_item:
                QMessageBox.warning(
                    self, "Error", "Please select a spritesheet and animation first."
                )
                return

            current_format = self.settings.get("animation_format", "GIF")
            self.progress_label.setText(f"Generating {current_format}...")
            self.play_button.setEnabled(False)

            spritesheet_path = current_spritesheet_item.data(Qt.ItemDataRole.UserRole)
            if not spritesheet_path:
                QMessageBox.warning(
                    self, "Error", "Could not find spritesheet file path."
                )
                return

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

            extractor = Extractor(None, "2.0.0", self.parent().settings_manager)

            animation_name = current_animation_item.text()
            complete_settings = self.parent().get_complete_preview_settings(
                spritesheet_name, animation_name
            )

            complete_settings.update(
                {
                    "animation_format": self.settings.get("animation_format", "GIF"),
                    "fps": self.fps_spinbox.value(),
                    "scale": self.anim_scale_spinbox.value(),
                    "crop_option": self.settings.get("crop_option", "None"),
                    "delay": self.settings.get("delay", 250),
                    "period": self.settings.get("period", 0),
                    "var_delay": self.settings.get("var_delay", False),
                }
            )

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
                    complete_settings["frame_selection"] = "All"
            else:
                complete_settings["frame_selection"] = "All"

            if self.settings.get("animation_format") == "GIF":
                complete_settings["threshold"] = self.settings.get("threshold", 0.5)

            temp_path = extractor.generate_temp_animation_for_preview(
                atlas_path=spritesheet_path,
                metadata_path=metadata_path,
                settings=complete_settings,
                animation_name=animation_name,
                spritemap_info=spritemap_info,
                spritesheet_label=spritesheet_name,
            )

            if temp_path and os.path.exists(temp_path):
                self.animation_path = temp_path
                self.settings = complete_settings
                self.frames.clear()
                self.frame_durations.clear()
                self.load_animation()
            else:
                QMessageBox.warning(self, "Error", "Failed to regenerate animation.")

        except Exception as e:
            QMessageBox.warning(
                self, "Error", f"Failed to regenerate animation: {str(e)}"
            )

    def update_format_settings(self):
        """Show or hide controls depending on the selected format."""
        pass

    def on_format_changed(self, format_type):
        """Update the animation format and regenerate.

        Args:
            format_type: New format string ('GIF', 'WebP', or 'APNG').
        """
        self.settings["animation_format"] = format_type
        self.update_format_settings()

        self.regenerate_animation()

    def on_delay_changed(self, delay):
        """Update the loop delay and regenerate.

        Args:
            delay: Delay in milliseconds before looping.
        """
        self.settings["delay"] = delay

        self._update_frame_delay_display()

        self.regenerate_animation()

    def on_period_changed(self, period):
        """Update the minimum frame period.

        Args:
            period: Minimum duration in milliseconds per frame.
        """
        self.settings["period"] = period

        self._update_frame_delay_display()

        if self.is_playing:
            fps = self.settings.get("fps", 24)
            interval = int(1000 / fps)

            if period > 0:
                interval = max(interval, period)
            self.timer.start(interval)

    def on_var_delay_changed(self, enabled):
        """Toggle variable per-frame delay and regenerate.

        Args:
            enabled: True to calculate unique delays per frame.
        """
        self.settings["var_delay"] = enabled

        if enabled and self.frame_durations:
            fps = self.settings.get("fps", 24)

            new_durations = []
            for index in range(len(self.frame_durations)):
                duration = round((index + 1) * 1000 / fps, -1) - round(
                    index * 1000 / fps, -1
                )
                new_durations.append(int(duration))

            loop_delay = self.settings.get("delay", 250)
            period = self.settings.get("period", 0)

            new_durations[-1] += loop_delay
            new_durations[-1] += max(round(period, -1) - sum(new_durations), 0)

            self.frame_durations = new_durations

            if hasattr(self.frame_list, "update_frame_delays"):
                self.frame_list.update_frame_delays(self.frame_durations, True)

            self.update_display()
        else:
            self._update_frame_delay_display()

        self.regenerate_animation()

    def on_indices_changed(self, indices_text):
        """Parse the indices text and update frame selection.

        Args:
            indices_text: Comma/range notation like '0,2-5,7'.
        """
        self.settings["indices_text"] = indices_text
        try:
            if indices_text.strip():
                indices = []
                for part in indices_text.split(","):
                    part = part.strip()
                    if "-" in part:
                        start, end = map(int, part.split("-"))
                        indices.extend(range(start, end + 1))
                    else:
                        indices.append(int(part))

                indices = [i for i in indices if 0 <= i < len(self.frames)]
                self.settings["indices"] = indices

                if hasattr(self.frame_list, "set_checked_frames"):
                    self.frame_list.set_checked_frames(indices)
            else:
                self.settings.pop("indices", None)
                if hasattr(self.frame_list, "set_checked_frames") and self.frames:
                    all_indices = list(range(len(self.frames)))
                    self.frame_list.set_checked_frames(all_indices)
        except ValueError:
            pass

    def on_anim_scale_changed(self, scale):
        """Update the animation export scale and regenerate.

        Args:
            scale: Export scale factor.
        """
        self.settings["scale"] = scale
        self.regenerate_animation()

    def on_crop_changed(self, crop_option):
        """Update the crop option and regenerate.

        Args:
            crop_option: One of 'None', 'Animation based', or 'Frame based'.
        """
        self.settings["crop_option"] = crop_option
        self.regenerate_animation()

    def on_threshold_changed(self, threshold):
        """Update the GIF threshold and regenerate.

        Args:
            threshold: Quantization threshold for GIF exports.
        """
        self.settings["threshold"] = threshold
        self.regenerate_animation()

    def _restart_normal_timer(self):
        """Resume playback with the configured FPS interval."""
        if self.is_playing:
            fps = self.settings.get("fps", 24)
            interval = int(1000 / fps)
            min_period = self.settings.get("period", 0)
            if min_period > 0:
                interval = max(interval, min_period)
            self.timer.start(interval)

    def _loop_to_first_frame(self):
        """Jump to the first checked frame and resume playback."""
        if self.is_playing:
            checked_frames = self.get_checked_frame_indices()
            if checked_frames:
                self.goto_frame(checked_frames[0])
                self._restart_normal_timer()

    def _update_frame_delay_display(self):
        """Recalculate and refresh the frame delay labels."""
        if not self.frame_durations or not hasattr(self, "frame_list"):
            return

        fps = self.settings.get("fps", 24)
        loop_delay = self.settings.get("delay", 250)
        var_delay = self.settings.get("var_delay", False)
        period = self.settings.get("period", 0)

        display_delays = []

        if var_delay:
            display_delays = self.frame_durations.copy()
        else:
            fixed_delay = round(1000 / fps, -1)
            display_delays = [int(fixed_delay)] * len(self.frame_durations)

            display_delays[-1] += loop_delay
            display_delays[-1] += max(round(period, -1) - sum(display_delays), 0)

        if hasattr(self.frame_list, "update_frame_delays"):
            self.frame_list.update_frame_delays(display_delays, True)

        self.update_display()
