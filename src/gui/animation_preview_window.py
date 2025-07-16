#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from typing import List

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QSlider, QSpinBox, QDoubleSpinBox,
    QPushButton, QListWidget, QListWidgetItem, QGroupBox,
    QCheckBox, QColorDialog, QSplitter, QComboBox, QLineEdit,
    QWidget, QMessageBox
)
from PySide6.QtCore import (
    Qt, QTimer, QThread, Signal, QSize, QRect
)
from PySide6.QtGui import (
    QPixmap, QImage, QPainter, QColor
)

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class AnimationProcessor(QThread):
    """Background thread for processing animation frames"""
    frame_processed = Signal(int, QPixmap)  # frame_index, pixmap
    processing_complete = Signal()
    error_occurred = Signal(str)
    
    def __init__(self, animation_path: str, settings: dict):
        super().__init__()
        self.animation_path = animation_path
        self.settings = settings
        self.frames: List[QPixmap] = []
        self.frame_durations: List[int] = []
        
    def run(self):
        """Process animation frames in background"""
        try:
            if not PIL_AVAILABLE:
                self.error_occurred.emit("PIL/Pillow not available")
                return
                
            # Load animation
            with Image.open(self.animation_path) as img:
                frame_count = getattr(img, 'n_frames', 1)
                
                for frame_idx in range(frame_count):
                    img.seek(frame_idx)
                    
                    # Get frame duration (default 100ms if not available)
                    duration = getattr(img, 'info', {}).get('duration', 100)
                    self.frame_durations.append(duration)
                    
                    # Convert PIL image to QPixmap
                    frame_copy = img.copy()
                    if frame_copy.mode != 'RGBA':
                        frame_copy = frame_copy.convert('RGBA')
                    
                    # Convert to QImage
                    w, h = frame_copy.size
                    qimg = QImage(frame_copy.tobytes(), w, h, QImage.Format.Format_RGBA8888)
                    pixmap = QPixmap.fromImage(qimg)
                    
                    self.frames.append(pixmap)
                    self.frame_processed.emit(frame_idx, pixmap)
                    
            self.processing_complete.emit()
            
        except Exception as e:
            self.error_occurred.emit(f"Failed to load animation: {str(e)}")


class FrameListWidget(QListWidget):
    """Custom list widget for frame navigation"""
    frame_selected = Signal(int)
    
    def __init__(self):
        super().__init__()
        self.setMaximumWidth(120)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.currentItemChanged.connect(self._on_selection_changed)
        
    def set_frame_count(self, count: int):
        """Set the number of frames in the list"""
        self.clear()
        for i in range(count):
            item = QListWidgetItem(f"Frame {i + 1}")
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.addItem(item)
            
    def select_frame(self, frame_index: int):
        """Select a specific frame"""
        if 0 <= frame_index < self.count():
            self.setCurrentRow(frame_index)
            
    def _on_selection_changed(self, current, previous):
        """Handle frame selection change"""
        if current:
            frame_index = current.data(Qt.ItemDataRole.UserRole)
            if frame_index is not None:
                self.frame_selected.emit(frame_index)


class AnimationDisplay(QLabel):
    """Custom widget for displaying animation frames"""
    
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(600, 500)
        self.setScaledContents(False)
        self.setStyleSheet("border: 1px solid gray; background-color: transparent;")
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self._background_color = QColor(255, 255, 255, 255)
        self._show_transparency = False
        self._checkered_pattern = None
        self._current_pixmap = None
        self._scale_factor = 1.0
        self._original_size = None
        self._auto_scale = True
        
    def set_background_color(self, color: QColor):
        """Set the background color for transparent animations"""
        self._background_color = color
        self._show_transparency = False
        self.update()
        
    def set_transparency_background(self, show_transparency: bool):
        """Set whether to show transparency with checkered pattern"""
        self._show_transparency = show_transparency
        if show_transparency:
            self._create_checkered_pattern()
        self.update()
        
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
        
    def set_scale_factor(self, scale: float):
        """Set the scale factor for the displayed frame"""
        self._scale_factor = scale
        self._auto_scale = False
        self.update()
        
    def set_frame(self, pixmap: QPixmap):
        """Set the current frame to display"""
        self._current_pixmap = pixmap
        if pixmap and not pixmap.isNull():
            self._original_size = pixmap.size()
            
            # Auto-scale to fit display on first frame if not manually set
            if self._auto_scale:
                self._calculate_auto_scale()
                
        self.update()
        
    def _calculate_auto_scale(self):
        """Calculate automatic scale to fit the display while maintaining aspect ratio"""
        if not self._original_size:
            return
            
        # Get available space (leave some margin)
        available_width = self.width() - 20
        available_height = self.height() - 20
        
        # Calculate scale factors for width and height
        width_scale = available_width / self._original_size.width()
        height_scale = available_height / self._original_size.height()
        
        # Use the smaller scale factor to ensure it fits in both dimensions
        # But don't scale up beyond original size unless needed
        auto_scale = min(width_scale, height_scale, 1.0)
        
        # Only use auto scale if it would make the image reasonably sized
        if auto_scale > 0.1:
            self._scale_factor = auto_scale
        else:
            self._scale_factor = 1.0
            
    def reset_auto_scale(self):
        """Reset to auto-scaling mode"""
        self._auto_scale = True
        if self._original_size:
            self._calculate_auto_scale()
            self.update()
        
    def paintEvent(self, event):
        """Custom paint event to handle background and scaling"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        if self._current_pixmap and not self._current_pixmap.isNull():
            # Calculate scaled size
            pixmap_size = self._current_pixmap.size()
            scaled_size = QSize(
                int(pixmap_size.width() * self._scale_factor),
                int(pixmap_size.height() * self._scale_factor)
            )
            
            # Center the pixmap
            widget_rect = self.rect()
            x = (widget_rect.width() - scaled_size.width()) // 2
            y = (widget_rect.height() - scaled_size.height()) // 2
            
            target_rect = QRect(x, y, scaled_size.width(), scaled_size.height())
            
            # Fill background only for the animation area, not the entire widget
            if self._show_transparency and self._checkered_pattern:
                # Tile the checkered pattern only within the animation bounds
                pattern_size = self._checkered_pattern.size()
                
                for px in range(target_rect.x(), target_rect.x() + target_rect.width(), pattern_size.width()):
                    for py in range(target_rect.y(), target_rect.y() + target_rect.height(), pattern_size.height()):
                        # Clip the pattern to fit within the target rectangle
                        clip_width = min(pattern_size.width(), target_rect.x() + target_rect.width() - px)
                        clip_height = min(pattern_size.height(), target_rect.y() + target_rect.height() - py)
                        
                        if clip_width > 0 and clip_height > 0:
                            source_rect = QRect(0, 0, clip_width, clip_height)
                            dest_rect = QRect(px, py, clip_width, clip_height)
                            painter.drawPixmap(dest_rect, self._checkered_pattern, source_rect)
            else:
                # Use solid color background only for the animation area
                painter.fillRect(target_rect, self._background_color)
            
            # Draw the pixmap on top
            painter.drawPixmap(target_rect, self._current_pixmap)
            
        painter.end()
        
    def resizeEvent(self, event):
        """Handle resize events to recalculate auto-scale"""
        super().resizeEvent(event)
        if self._auto_scale and self._original_size:
            self._calculate_auto_scale()
            self.update()


class AnimationPreviewWindow(QDialog):
    """
    Modern animation preview window with real-time playback and settings.
    """
    
    def __init__(self, parent, animation_path: str, settings: dict):
        super().__init__(parent)
        self.animation_path = animation_path
        self.settings = settings.copy() if settings else {}
        
        # Animation state
        self.frames: List[QPixmap] = []
        self.frame_durations: List[int] = []
        self.current_frame = 0
        self.is_playing = False
        
        # UI components
        self.display = None
        self.frame_list = None
        self.play_button = None
        self.position_slider = None
        self.timer = None
        
        # Settings widgets
        self.fps_spinbox = None
        self.scale_spinbox = None
        self.loop_checkbox = None
        
        self.init_ui()
        self.load_animation()
        
        # Set up auto-scaling after UI is ready
        QTimer.singleShot(100, self.display.reset_auto_scale)
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Animation Preview")
        self.setMinimumSize(1000, 800)
        self.resize(1400, 1000)
        
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
        
        # Setup timer for playback
        self.timer = QTimer()
        self.timer.timeout.connect(self.next_frame)
        
        # Update UI state
        self.update_format_settings()
        self.update_frame_selection_ui()
        
    def create_frame_panel(self) -> QWidget:
        """Create the frame list panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        layout.addWidget(QLabel("Frames:"))
        
        self.frame_list = FrameListWidget()
        self.frame_list.frame_selected.connect(self.goto_frame)
        layout.addWidget(self.frame_list)
        
        return panel
        
    def create_display_panel(self) -> QWidget:
        """Create the animation display panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Display area
        self.display = AnimationDisplay()
        layout.addWidget(self.display)
        
        # Frame info
        self.frame_info_label = QLabel("Frame 1 / 1")
        self.frame_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.frame_info_label)
        
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
        self.format_combo.setCurrentText(self.settings.get('animation_format', 'GIF'))
        self.format_combo.currentTextChanged.connect(self.on_format_changed)
        format_layout.addWidget(self.format_combo, 0, 1)
        
        layout.addWidget(format_group)
        
        # Playback settings
        playback_group = QGroupBox("Playback")
        playback_layout = QGridLayout(playback_group)
        
        # FPS setting
        playback_layout.addWidget(QLabel("FPS:"), 0, 0)
        self.fps_spinbox = QSpinBox()
        self.fps_spinbox.setRange(1, 60)
        self.fps_spinbox.setValue(self.settings.get('fps', 24))
        self.fps_spinbox.valueChanged.connect(self.on_fps_changed)
        playback_layout.addWidget(self.fps_spinbox, 0, 1)
        
        # Loop delay setting
        playback_layout.addWidget(QLabel("Loop Delay (ms):"), 1, 0)
        self.delay_spinbox = QSpinBox()
        self.delay_spinbox.setRange(0, 5000)
        self.delay_spinbox.setValue(self.settings.get('delay', 250))
        self.delay_spinbox.valueChanged.connect(self.on_delay_changed)
        playback_layout.addWidget(self.delay_spinbox, 1, 1)
        
        # Minimum period setting
        playback_layout.addWidget(QLabel("Min Period (ms):"), 2, 0)
        self.period_spinbox = QSpinBox()
        self.period_spinbox.setRange(0, 10000)
        self.period_spinbox.setValue(self.settings.get('period', 0))
        self.period_spinbox.valueChanged.connect(self.on_period_changed)
        playback_layout.addWidget(self.period_spinbox, 2, 1)
        
        # Variable delay option
        self.var_delay_checkbox = QCheckBox("Variable delay")
        self.var_delay_checkbox.setChecked(self.settings.get('var_delay', False))
        self.var_delay_checkbox.toggled.connect(self.on_var_delay_changed)
        playback_layout.addWidget(self.var_delay_checkbox, 3, 0, 1, 2)
        
        # Loop option (for preview only)
        self.loop_checkbox = QCheckBox("Loop preview")
        self.loop_checkbox.setChecked(True)
        playback_layout.addWidget(self.loop_checkbox, 4, 0, 1, 2)
        
        layout.addWidget(playback_group)
        
        # Frame settings
        frame_group = QGroupBox("Frame Settings")
        frame_layout = QGridLayout(frame_group)
        
        # Frame selection
        frame_layout.addWidget(QLabel("Frame Selection:"), 0, 0)
        self.frame_selection_combo = QComboBox()
        self.frame_selection_combo.addItems(["All", "No duplicates", "First", "Last", "First, Last", "Custom"])
        self.frame_selection_combo.setCurrentText(self.settings.get('frame_selection', 'All'))
        self.frame_selection_combo.currentTextChanged.connect(self.on_frame_selection_changed)
        frame_layout.addWidget(self.frame_selection_combo, 0, 1)
        
        # Custom indices (only shown when Custom is selected)
        self.indices_label = QLabel("Custom Indices:")
        self.indices_edit = QLineEdit()
        self.indices_edit.setPlaceholderText("e.g., 0,2,4 or 0-5")
        self.indices_edit.textChanged.connect(self.on_indices_changed)
        frame_layout.addWidget(self.indices_label, 1, 0)
        frame_layout.addWidget(self.indices_edit, 1, 1)
        
        # Initially hide custom indices
        self.indices_label.setVisible(False)
        self.indices_edit.setVisible(False)
        
        # Animation scale setting
        frame_layout.addWidget(QLabel("Animation Scale:"), 2, 0)
        self.anim_scale_spinbox = QDoubleSpinBox()
        self.anim_scale_spinbox.setRange(0.1, 10.0)
        self.anim_scale_spinbox.setSingleStep(0.1)
        self.anim_scale_spinbox.setValue(self.settings.get('scale', 1.0))
        self.anim_scale_spinbox.valueChanged.connect(self.on_anim_scale_changed)
        frame_layout.addWidget(self.anim_scale_spinbox, 2, 1)
        
        layout.addWidget(frame_group)
        
        # Display settings
        display_group = QGroupBox("Display")
        display_layout = QGridLayout(display_group)
        
        # Preview scale setting (separate from animation scale)
        display_layout.addWidget(QLabel("Preview Scale:"), 0, 0)
        self.scale_spinbox = QDoubleSpinBox()
        self.scale_spinbox.setRange(0.1, 5.0)
        self.scale_spinbox.setSingleStep(0.1)
        self.scale_spinbox.setValue(1.0)
        self.scale_spinbox.valueChanged.connect(self.on_scale_changed)
        display_layout.addWidget(self.scale_spinbox, 0, 1)
        
        # Background color
        display_layout.addWidget(QLabel("Background:"), 1, 0)
        bg_layout = QHBoxLayout()
        
        self.bg_color_button = QPushButton()
        self.bg_color_button.setFixedSize(50, 30)
        self.bg_color_button.setStyleSheet("background-color: white; border: 1px solid gray;")
        self.bg_color_button.clicked.connect(self.choose_background_color)
        bg_layout.addWidget(self.bg_color_button)
        
        # Transparency background checkbox
        self.transparency_checkbox = QCheckBox("Show transparency")
        self.transparency_checkbox.setChecked(False)
        self.transparency_checkbox.toggled.connect(self.on_transparency_changed)
        bg_layout.addWidget(self.transparency_checkbox)
        
        bg_widget = QWidget()
        bg_widget.setLayout(bg_layout)
        display_layout.addWidget(bg_widget, 1, 1)
        
        layout.addWidget(display_group)
        
        # Cropping settings
        crop_group = QGroupBox("Cropping")
        crop_layout = QGridLayout(crop_group)
        
        crop_layout.addWidget(QLabel("Crop Option:"), 0, 0)
        self.crop_combo = QComboBox()
        self.crop_combo.addItems(["None", "Animation based", "Frame based"])
        self.crop_combo.setCurrentText(self.settings.get('crop_option', 'None'))
        self.crop_combo.currentTextChanged.connect(self.on_crop_changed)
        crop_layout.addWidget(self.crop_combo, 0, 1)
        
        layout.addWidget(crop_group)
        
        # GIF-specific settings
        self.gif_group = QGroupBox("GIF Settings")
        gif_layout = QGridLayout(self.gif_group)
        
        gif_layout.addWidget(QLabel("Threshold:"), 0, 0)
        self.threshold_spinbox = QDoubleSpinBox()
        self.threshold_spinbox.setRange(0.0, 1.0)
        self.threshold_spinbox.setSingleStep(0.1)
        self.threshold_spinbox.setValue(self.settings.get('threshold', 0.5))
        self.threshold_spinbox.valueChanged.connect(self.on_threshold_changed)
        gif_layout.addWidget(self.threshold_spinbox, 0, 1)
        
        layout.addWidget(self.gif_group)
        
        # Export settings
        export_group = QGroupBox("Export")
        export_layout = QVBoxLayout(export_group)
        
        self.regenerate_button = QPushButton("Regenerate with Settings")
        self.regenerate_button.clicked.connect(self.regenerate_animation)
        export_layout.addWidget(self.regenerate_button)
        
        layout.addWidget(export_group)
        
        # Spacer
        layout.addStretch()
        
        # Update GIF settings visibility
        self.update_format_settings()
        
        return panel
        
    def create_controls(self) -> QHBoxLayout:
        """Create playback controls"""
        controls_layout = QHBoxLayout()
        
        # Playback buttons
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.toggle_playback)
        controls_layout.addWidget(self.play_button)
        
        prev_button = QPushButton("Previous")
        prev_button.clicked.connect(self.previous_frame)
        controls_layout.addWidget(prev_button)
        
        next_button = QPushButton("Next")
        next_button.clicked.connect(self.next_frame)
        controls_layout.addWidget(next_button)
        
        # Position slider
        controls_layout.addWidget(QLabel("Position:"))
        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setMinimum(0)
        self.position_slider.valueChanged.connect(self.on_position_changed)
        controls_layout.addWidget(self.position_slider)
        
        return controls_layout
        
    def load_animation(self):
        """Load animation frames"""
        if not os.path.exists(self.animation_path):
            QMessageBox.warning(self, "Error", f"Animation file not found: {self.animation_path}")
            return
            
        # Start background processing
        self.processor = AnimationProcessor(self.animation_path, self.settings)
        self.processor.frame_processed.connect(self.on_frame_processed)
        self.processor.processing_complete.connect(self.on_processing_complete)
        self.processor.error_occurred.connect(self.on_processing_error)
        self.processor.start()
        
    def on_frame_processed(self, frame_index: int, pixmap: QPixmap):
        """Handle processed frame"""
        # Extend frames list if needed
        while len(self.frames) <= frame_index:
            self.frames.append(QPixmap())
            
        self.frames[frame_index] = pixmap
        
        # Update display if this is the current frame
        if frame_index == self.current_frame:
            self.display.set_frame(pixmap)
            
    def on_processing_complete(self):
        """Handle completion of frame processing"""
        frame_count = len(self.frames)
        
        # Update frame list
        self.frame_list.set_frame_count(frame_count)
        
        # Update position slider
        self.position_slider.setMaximum(max(0, frame_count - 1))
        
        # Get frame durations from processor
        self.frame_durations = self.processor.frame_durations
        
        # Show first frame
        if self.frames:
            self.current_frame = 0
            self.update_display()
            self.frame_list.select_frame(0)
            
        print(f"Animation loaded: {frame_count} frames")
        
    def on_processing_error(self, error_message: str):
        """Handle processing error"""
        QMessageBox.warning(self, "Error", error_message)
        
    def update_display(self):
        """Update the display with current frame"""
        if 0 <= self.current_frame < len(self.frames):
            pixmap = self.frames[self.current_frame]
            self.display.set_frame(pixmap)
            
            # Update frame info
            total_frames = len(self.frames)
            self.frame_info_label.setText(f"Frame {self.current_frame + 1} / {total_frames}")
            
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
        """Start playback"""
        if not self.frames:
            return
            
        self.is_playing = True
        self.play_button.setText("Pause")
        
        # Calculate timer interval based on current frame duration
        if self.current_frame < len(self.frame_durations):
            frame_duration = self.frame_durations[self.current_frame]
        else:
            frame_duration = 100  # Default 100ms
            
        interval = max(1, frame_duration)
        self.timer.start(interval)
        
    def pause(self):
        """Pause playback"""
        self.is_playing = False
        self.play_button.setText("Play")
        self.timer.stop()
        
    def next_frame(self):
        """Go to next frame"""
        if not self.frames:
            return
            
        self.current_frame += 1
        
        if self.current_frame >= len(self.frames):
            if self.loop_checkbox.isChecked():
                self.current_frame = 0
            else:
                self.current_frame = len(self.frames) - 1
                self.pause()
                
        self.update_display()
        
        # Update timer interval for variable frame durations
        if self.is_playing and self.current_frame < len(self.frame_durations):
            frame_duration = self.frame_durations[self.current_frame]
            interval = max(1, frame_duration)
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
            
    def on_position_changed(self, position: int):
        """Handle position slider change"""
        self.goto_frame(position)
        
    def on_fps_changed(self, fps: int):
        """Handle FPS change"""
        self.settings['fps'] = fps
        
        # Restart timer if playing
        if self.is_playing:
            self.pause()
            self.play()
            
    def on_scale_changed(self, scale: float):
        """Handle preview scale change"""
        if scale == 1.0:
            # Reset to auto-scale mode at 1.0
            self.display.reset_auto_scale()
        else:
            # Use manual scale
            self.display.set_scale_factor(scale)
        
    def choose_background_color(self):
        """Choose background color"""
        color = QColorDialog.getColor(Qt.GlobalColor.white, self, "Choose Background Color")
        if color.isValid():
            self.display.set_background_color(color)
            # Update button color
            self.bg_color_button.setStyleSheet(
                f"background-color: {color.name()}; border: 1px solid gray;"
            )
            # Disable transparency when using solid color
            self.transparency_checkbox.setChecked(False)
            
    def on_transparency_changed(self, checked: bool):
        """Handle transparency background toggle"""
        self.display.set_transparency_background(checked)
        # Update button enabled state
        self.bg_color_button.setEnabled(not checked)
            
    def regenerate_animation(self):
        """Regenerate animation with current settings"""
        try:
            # Import the extractor to regenerate with new settings
            from core.extractor import Extractor
            
            # Get current spritesheet and animation info
            current_spritesheet_item = self.parent().ui.listbox_png.currentItem()
            current_animation_item = self.parent().ui.listbox_data.currentItem()
            
            if not current_spritesheet_item or not current_animation_item:
                QMessageBox.warning(self, "Error", "Please select a spritesheet and animation first.")
                return
            
            # Get the file paths
            spritesheet_path = current_spritesheet_item.data(Qt.ItemDataRole.UserRole)
            if not spritesheet_path:
                QMessageBox.warning(self, "Error", "Could not find spritesheet file path.")
                return
            
            # Find the metadata file
            spritesheet_name = current_spritesheet_item.text()
            metadata_path = None
            if spritesheet_name in self.parent().data_dict:
                data_files = self.parent().data_dict[spritesheet_name]
                if "xml" in data_files:
                    metadata_path = data_files["xml"]
                elif "txt" in data_files:
                    metadata_path = data_files["txt"]
                
            # Generate new preview with current settings
            extractor = Extractor(None, "2.0.0", self.parent().settings_manager)
            
            # Get complete settings including global, spritesheet, and animation overrides
            animation_name = current_animation_item.text()
            complete_settings = self.parent().get_complete_preview_settings(spritesheet_name, animation_name)
            
            # Update with current values from the preview window controls
            complete_settings.update({
                'fps': self.fps_spinbox.value(),
                'scale': self.scale_spinbox.value(),
                'frame_selection': 'All',  # Force all frames for preview
                'crop_option': 'None',     # Force no cropping for preview
            })
            
            # Create temp animation with complete settings
            temp_path = extractor.generate_temp_animation_for_preview(
                atlas_path=spritesheet_path,
                metadata_path=metadata_path,
                settings=complete_settings,
                animation_name=animation_name
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
        format_type = self.format_combo.currentText()
        # Only show GIF-specific settings for GIF format
        self.gif_group.setVisible(format_type == "GIF")
        
    def update_frame_selection_ui(self):
        """Show/hide custom indices based on frame selection"""
        selection = self.frame_selection_combo.currentText()
        show_custom = selection == "Custom"
        self.indices_label.setVisible(show_custom)
        self.indices_edit.setVisible(show_custom)
        
    def on_format_changed(self, format_type):
        """Handle format change"""
        self.settings['animation_format'] = format_type
        self.update_format_settings()
        
    def on_delay_changed(self, delay):
        """Handle loop delay change"""
        self.settings['delay'] = delay
        
    def on_period_changed(self, period):
        """Handle minimum period change"""
        self.settings['period'] = period
        
    def on_var_delay_changed(self, enabled):
        """Handle variable delay change"""
        self.settings['var_delay'] = enabled
        
    def on_frame_selection_changed(self, selection):
        """Handle frame selection change"""
        self.settings['frame_selection'] = selection
        self.update_frame_selection_ui()
        
    def on_indices_changed(self, indices_text):
        """Handle custom indices change"""
        self.settings['indices_text'] = indices_text
        # Parse indices for immediate feedback
        try:
            if indices_text.strip():
                # Parse ranges and individual numbers
                indices = []
                for part in indices_text.split(','):
                    part = part.strip()
                    if '-' in part:
                        start, end = map(int, part.split('-'))
                        indices.extend(range(start, end + 1))
                    else:
                        indices.append(int(part))
                self.settings['indices'] = indices
            else:
                self.settings.pop('indices', None)
        except ValueError:
            # Invalid format, ignore for now
            pass
            
    def on_anim_scale_changed(self, scale):
        """Handle animation scale change"""
        self.settings['scale'] = scale
        self.regenerate_animation()
        
    def on_crop_changed(self, crop_option):
        """Handle crop option change"""
        self.settings['crop_option'] = crop_option
        self.regenerate_animation()
        
    def on_threshold_changed(self, threshold):
        """Handle threshold change"""
        self.settings['transparency_threshold'] = threshold / 100.0
        self.regenerate_animation()
