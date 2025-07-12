#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import platform
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QWidget,
    QPushButton,
    QSlider,
    QGridLayout,
    QMessageBox,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QPixmap, QImage

try:
    from PIL import Image, ImageSequence
    from PIL.Image import Resampling

    NEAREST = Resampling.NEAREST
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    try:
        from PIL import Image, ImageSequence

        NEAREST = Image.NEAREST
    except ImportError:
        PIL_AVAILABLE = False


class AnimationPreviewWindow(QDialog):
    """
    A window class for previewing animations in Qt.

    This window allows users to preview animations with controls for
    playback, frame navigation, background color adjustment, and external viewing.
    """

    def __init__(self, parent, animation_path, settings):
        super().__init__(parent)
        self.animation_path = animation_path
        self.settings = settings
        self.pil_frames = []
        self.durations = []
        self.frame_count = 0
        self.current_frame = 0
        self.playing = False
        self.scale_factor = 1.0
        self.composited_cache = {}
        self.bg_value = 127

        # Get file format
        file_ext = os.path.splitext(animation_path)[1].lower()
        self.format_name = {".gif": "GIF", ".webp": "WebP"}.get(file_ext, "Animation")

        self.setWindowTitle(f"{self.format_name} Preview")
        self.setModal(True)

        # Timer for animation playback
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self.next_frame)

        if not self.load_animation():
            return

        self.setup_ui()
        self.precompute_composited_frames()
        self.show_frame(0)

    def load_animation(self):
        """Load the animation file and extract frames."""
        if not PIL_AVAILABLE:
            QMessageBox.critical(self, "Error", "PIL/Pillow is required for animation preview.")
            self.reject()
            return False

        try:
            animation = Image.open(self.animation_path)

            file_ext = os.path.splitext(self.animation_path)[1].lower()

            if file_ext == ".webp":
                # Handle WebP animations
                self.pil_frames = []
                try:
                    while True:
                        self.pil_frames.append(animation.copy())
                        animation.seek(animation.tell() + 1)
                except EOFError:
                    pass
                animation.seek(0)
            else:
                # Handle GIF and other formats
                self.pil_frames = [frame.copy() for frame in ImageSequence.Iterator(animation)]

            self.frame_count = len(self.pil_frames)

            # Calculate durations
            self.calculate_durations(animation, file_ext)

            animation.close()
            return True

        except Exception as e:
            QMessageBox.critical(self, "Preview Error", f"Could not load animation file: {e}")
            self.reject()
            return False

    def calculate_durations(self, animation, file_ext):
        """Calculate frame durations based on settings."""
        self.durations = []

        try:
            fps = self.settings.get("fps", 24)
            delay_setting = self.settings.get("delay", 250)
            period = self.settings.get("period", 0)
            var_delay = self.settings.get("var_delay", False)

            if var_delay:
                if file_ext == ".webp":
                    for index in range(self.frame_count):
                        duration = round((index + 1) * 1000 / fps) - round(index * 1000 / fps)
                        self.durations.append(int(duration))
                else:
                    for index in range(self.frame_count):
                        duration = round((index + 1) * 1000 / fps, -1) - round(
                            index * 1000 / fps, -1
                        )
                        self.durations.append(int(duration))
            else:
                if file_ext == ".webp":
                    self.durations = [int(round(1000 / fps))] * self.frame_count
                else:
                    self.durations = [int(round(1000 / fps, -1))] * self.frame_count

            if self.durations:
                if file_ext == ".webp":
                    self.durations[-1] += int(delay_setting)
                    self.durations[-1] += max(int(period) - sum(self.durations), 0)
                else:
                    self.durations[-1] += int(delay_setting)
                    self.durations[-1] += max(int(round(period, -1)) - sum(self.durations), 0)

        except Exception:
            # Fallback: try to get durations from the animation
            try:
                if file_ext == ".webp":
                    animation.seek(0)
                    for i in range(self.frame_count):
                        try:
                            animation.seek(i)
                            duration = animation.info.get("duration", 0)
                            self.durations.append(int(duration) if duration else 42)
                        except EOFError:
                            break
                else:
                    for frame in ImageSequence.Iterator(animation):
                        duration = frame.info.get("duration", 0)
                        self.durations.append(int(duration) if duration else 42)
            except Exception:
                pass

        # Final fallback
        if not self.durations or len(self.durations) != self.frame_count:
            fps = self.settings.get("fps", 24)
            delay_setting = self.settings.get("delay", 250)
            base_delay = int(round(1000 / fps, -1))
            self.durations = [base_delay] * self.frame_count
            self.durations[-1] += int(delay_setting)

    def setup_ui(self):
        """Set up the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(5)

        # Frame counter
        self.frame_counter = QLabel(f"Frame 0 / {self.frame_count - 1}")
        self.frame_counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.frame_counter)

        # Frame slider
        slider_layout = QHBoxLayout()
        self.frame_slider = QSlider(Qt.Orientation.Horizontal)
        self.frame_slider.setMinimum(0)
        self.frame_slider.setMaximum(self.frame_count - 1)
        self.frame_slider.setValue(0)
        self.frame_slider.setMinimumWidth(300)
        self.frame_slider.valueChanged.connect(self.on_slider_change)

        slider_layout.addStretch()
        slider_layout.addWidget(self.frame_slider)
        slider_layout.addStretch()
        main_layout.addLayout(slider_layout)

        # Delays display
        self.setup_delays_display(main_layout)

        # Control buttons
        self.setup_control_buttons(main_layout)

        # Background color slider
        self.setup_background_slider(main_layout)

        # Image display label
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("QLabel { border: 1px solid gray; }")
        main_layout.addWidget(self.image_label)

        # Note text
        note_text = (
            f"Playback speed of {self.format_name} animations may not be "
            "accurately depicted in this preview window. Open the animation "
            "externally for accurate playback."
        )
        note_label = QLabel(note_text)
        note_label.setFont(QFont("Arial", 9, QFont.Weight.ExtraLight))
        note_label.setStyleSheet("QLabel { color: #333333; }")
        note_label.setWordWrap(True)
        note_label.setMargin(8)
        main_layout.addWidget(note_label)

    def setup_delays_display(self, main_layout):
        """Set up the delays display area."""
        delays_scroll = QScrollArea()
        delays_scroll.setMaximumHeight(60)
        delays_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        delays_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        delays_widget = QWidget()
        delays_layout = QGridLayout(delays_widget)
        delays_layout.setSpacing(2)

        self.delay_labels = []
        for i, duration in enumerate(self.durations):
            # Frame index
            idx_label = QLabel(str(i))
            idx_label.setFont(QFont("Arial", 8))
            idx_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            delays_layout.addWidget(idx_label, 0, i)

            # Duration
            ms_label = QLabel(f"{duration} ms")
            ms_label.setFont(QFont("Arial", 8, QFont.Weight.ExtraLight))
            ms_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            delays_layout.addWidget(ms_label, 1, i)

            self.delay_labels.append(ms_label)

        delays_scroll.setWidget(delays_widget)
        main_layout.addWidget(delays_scroll)

    def setup_control_buttons(self, main_layout):
        """Set up playback control buttons."""
        button_layout = QHBoxLayout()

        prev_btn = QPushButton("Prev")
        prev_btn.clicked.connect(self.prev_frame)
        button_layout.addWidget(prev_btn)

        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self.toggle_play)
        button_layout.addWidget(self.play_btn)

        stop_btn = QPushButton("Stop")
        stop_btn.clicked.connect(self.stop_animation)
        button_layout.addWidget(stop_btn)

        next_btn = QPushButton("Next")
        next_btn.clicked.connect(self.next_frame)
        button_layout.addWidget(next_btn)

        # External open button
        external_btn = QPushButton(f"Open {self.format_name} externally")
        external_btn.clicked.connect(self.open_external)
        button_layout.addWidget(external_btn)

        main_layout.addLayout(button_layout)

    def setup_background_slider(self, main_layout):
        """Set up the background color slider."""
        bg_layout = QHBoxLayout()

        bg_label = QLabel("Background:")
        bg_layout.addWidget(bg_label)

        self.bg_slider = QSlider(Qt.Orientation.Horizontal)
        self.bg_slider.setMinimum(0)
        self.bg_slider.setMaximum(255)
        self.bg_slider.setValue(127)
        self.bg_slider.setMinimumWidth(200)
        self.bg_slider.valueChanged.connect(self.on_bg_change)
        bg_layout.addWidget(self.bg_slider)

        bg_layout.addStretch()
        main_layout.addLayout(bg_layout)

    def precompute_composited_frames(self):
        """Precompute all composited frames for better performance."""
        self.composited_cache.clear()

        for idx, frame in enumerate(self.pil_frames):
            img = frame.convert("RGBA")

            # Scale if needed
            if self.scale_factor != 1.0:
                new_size = (int(img.width * self.scale_factor), int(img.height * self.scale_factor))
                img = img.resize(new_size, NEAREST)

            # Composite with background
            bg_img = Image.new("RGBA", img.size, (self.bg_value, self.bg_value, self.bg_value, 255))
            composited = Image.alpha_composite(bg_img, img)
            self.composited_cache[idx] = composited.convert("RGB")

    def get_composited_frame(self, idx):
        """Get a composited frame, creating it if not cached."""
        if idx in self.composited_cache:
            return self.composited_cache[idx]

        frame = self.pil_frames[idx]
        img = frame.convert("RGBA")

        if self.scale_factor != 1.0:
            new_size = (int(img.width * self.scale_factor), int(img.height * self.scale_factor))
            img = img.resize(new_size, NEAREST)

        bg_img = Image.new("RGBA", img.size, (self.bg_value, self.bg_value, self.bg_value, 255))
        composited = Image.alpha_composite(bg_img, img)
        self.composited_cache[idx] = composited.convert("RGB")
        return self.composited_cache[idx]

    def show_frame(self, idx):
        """Display the specified frame."""
        if idx < 0 or idx >= self.frame_count:
            return

        self.current_frame = idx

        # Get composited frame
        pil_img = self.get_composited_frame(idx)

        # Convert to QPixmap
        img_data = pil_img.tobytes("raw", "RGB")
        qimg = QImage(img_data, pil_img.width, pil_img.height, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)

        # Auto-scale window on first frame
        if not hasattr(self, "_window_sized"):
            self._window_sized = True
            self.auto_scale_window(pil_img.size)

        # Update image display
        self.image_label.setPixmap(pixmap)

        # Update frame counter
        self.frame_counter.setText(f"Frame {idx} / {self.frame_count - 1}")

        # Update slider
        self.frame_slider.setValue(idx)

        # Highlight current delay
        self.highlight_current_delay(idx)

    def auto_scale_window(self, img_size):
        """Auto-scale the window based on image size and screen size."""
        extra_height = 300  # For controls
        width = img_size[0]
        height = img_size[1] + extra_height

        # Get screen size
        screen = self.screen().availableGeometry()
        max_width = int(screen.width() * 0.9)
        max_height = int(screen.height() * 0.9)

        # Scale if necessary
        if width > max_width or height > max_height:
            scale_w = max_width / width
            scale_h = max_height / height
            self.scale_factor = min(scale_w, scale_h, 1.0)

            self.precompute_composited_frames()
            width = int(img_size[0] * self.scale_factor)
            height = int(img_size[1] * self.scale_factor) + extra_height

        self.resize(width, height)
        self.setMinimumSize(width, height)

    def highlight_current_delay(self, idx):
        """Highlight the current frame's delay in the delays display."""
        for i, label in enumerate(self.delay_labels):
            if i == idx:
                label.setStyleSheet("QLabel { background-color: #e0e0e0; }")
            else:
                label.setStyleSheet("")

    def on_slider_change(self, value):
        """Handle frame slider value change."""
        self.show_frame(value)

    def on_bg_change(self, value):
        """Handle background color slider change."""
        self.bg_value = value
        self.precompute_composited_frames()
        self.show_frame(self.current_frame)

    def prev_frame(self):
        """Go to previous frame."""
        new_frame = (self.current_frame - 1) % self.frame_count
        self.show_frame(new_frame)

    def next_frame(self):
        """Go to next frame."""
        new_frame = (self.current_frame + 1) % self.frame_count
        self.show_frame(new_frame)

    def toggle_play(self):
        """Toggle animation playback."""
        if self.playing:
            self.stop_animation()
        else:
            self.play_animation()

    def play_animation(self):
        """Start animation playback."""
        self.playing = True
        self.play_btn.setText("Pause")

        # Start timer with current frame's duration
        delay = max(1, self.durations[self.current_frame])
        self.playback_timer.start(delay)

    def stop_animation(self):
        """Stop animation playback."""
        self.playing = False
        self.play_btn.setText("Play")
        self.playback_timer.stop()

    def open_external(self):
        """Open the animation in an external program."""
        try:
            current_os = platform.system().lower()
            if current_os == "windows":
                os.startfile(self.animation_path)
            elif current_os == "darwin":
                subprocess.Popen(["open", self.animation_path])
            else:
                subprocess.Popen(["xdg-open", self.animation_path])
        except Exception as e:
            QMessageBox.critical(
                self, "Open External", f"Could not open animation in external program:\n{e}"
            )

    def closeEvent(self, event):
        """Handle window close event."""
        self.stop_animation()

        # Clean up temp file if it exists
        try:
            if os.path.isfile(self.animation_path):
                os.remove(self.animation_path)
        except Exception:
            pass

        event.accept()

    @staticmethod
    def show(animation_path, settings):
        """
        Static method to show an animation preview window.

        Args:
            animation_path: Path to the animation file
            settings: Settings dictionary containing preview configuration
        """
        # This would be called from the main application
        # The parent window would be passed when creating the dialog
        pass

    @staticmethod
    def preview(
        app,
        name,
        settings_type,
        animation_format_entry,
        fps_entry,
        delay_entry,
        period_entry,
        scale_entry,
        threshold_entry,
        indices_entry,
        frames_entry,
    ):
        """
        Static method to generate and preview an animation from the settings window.

        This mirrors the functionality from the original tkinter version.
        """
        settings = {}
        try:
            if animation_format_entry and animation_format_entry.text() != "":
                settings["animation_format"] = animation_format_entry.text()
            if fps_entry.text() != "":
                settings["fps"] = float(fps_entry.text())
            if delay_entry.text() != "":
                settings["delay"] = int(float(delay_entry.text()))
            if period_entry.text() != "":
                settings["period"] = int(float(period_entry.text()))
            if scale_entry.text() != "":
                settings["scale"] = float(scale_entry.text())
            if threshold_entry.text() != "":
                settings["threshold"] = min(max(float(threshold_entry.text()), 0), 1)
            if indices_entry.text() != "":
                indices = [int(ele) for ele in indices_entry.text().split(",")]
                settings["indices"] = indices
        except ValueError as e:
            QMessageBox.critical(None, "Invalid input", f"Error: {str(e)}")
            return

        # Check if APNG format is selected and block preview
        animation_format = settings.get("animation_format", "")
        if animation_format == "APNG":
            QMessageBox.information(
                None,
                "Preview Not Available",
                "Preview is not available for APNG format due to display limitations.\n\n"
                "You can still export APNG animations and view them externally.",
            )
            return

        if settings_type == "animation":
            spritesheet_name, animation_name = name.split("/", 1)
        else:
            spritesheet_name = name
            animation_name = None

        input_dir = app.input_dir.get()
        png_path = os.path.join(input_dir, spritesheet_name)
        xml_path = os.path.splitext(png_path)[0] + ".xml"
        txt_path = os.path.splitext(png_path)[0] + ".txt"
        metadata_path = xml_path if os.path.isfile(xml_path) else txt_path

        try:
            from core.extractor import Extractor

            app.update_global_settings()

            extractor = Extractor(None, app.current_version, app.settings_manager)
            animation_path = extractor.generate_temp_animation_for_preview(
                png_path, metadata_path, settings, animation_name, temp_dir=app.temp_dir
            )
            if not animation_path or not os.path.isfile(animation_path):
                QMessageBox.critical(None, "Preview Error", "Could not generate preview animation.")
                return
        except Exception as e:
            QMessageBox.critical(None, "Preview Error", f"Error generating preview animation: {e}")
            return

        app.show_animation_preview_window(animation_path, settings)
