#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QWidget,
    QPushButton,
    QLineEdit,
    QComboBox,
    QGroupBox,
    QGridLayout,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# Import our own modules
from utils.utilities import Utilities


class OverrideSettingsWindow(QDialog):
    """
    A window for overriding animation or spritesheet settings.

    This class creates a Qt dialog that allows the user to override settings such as animation format, FPS, delay,
    period, scale, threshold, indices, and frame-keeping options for a specific animation or spritesheet.
    """

    def __init__(self, parent, name, settings_type, settings_manager, on_store_callback, app=None):
        super().__init__(parent)
        self.name = name
        self.settings_type = settings_type
        self.settings_manager = settings_manager
        self.on_store_callback = on_store_callback
        self.app = app

        # Set window title based on settings type
        title_prefix = "Animation" if settings_type == "animation" else "Spritesheet"
        self.setWindowTitle(
            self.tr("{prefix} Settings Override - {name}").format(prefix=title_prefix, name=name)
        )
        self.setModal(True)
        self.resize(500, 650)

        # Initialize UI controls
        self.animation_format_combo = None
        self.fps_spinbox = None
        self.delay_spinbox = None
        self.period_spinbox = None
        self.scale_spinbox = None
        self.threshold_spinbox = None
        self.indices_edit = None
        self.frames_edit = None
        self.frame_format_combo = None
        self.frame_scale_spinbox = None
        self.filename_edit = None

        # Get current settings
        self.get_current_settings()

        self.setup_ui()
        self.load_current_values()

    def tr(self, text):
        """Translation helper method."""
        from PySide6.QtCore import QCoreApplication

        return QCoreApplication.translate(self.__class__.__name__, text)

    def get_current_settings(self):
        """Get current settings for this animation/spritesheet."""
        self.local_settings = {}

        if self.settings_type == "animation":
            if "/" in self.name:
                spritesheet_name = self.name.rsplit("/", 1)[0]
            else:
                spritesheet_name = self.name
            animation_name = self.name
            self.local_settings = self.settings_manager.animation_settings.get(animation_name, {})
            self.spritesheet_name = spritesheet_name
            self.animation_name = animation_name
        else:
            spritesheet_name = self.name
            animation_name = None
            self.local_settings = self.settings_manager.spritesheet_settings.get(
                spritesheet_name, {}
            )
            self.spritesheet_name = spritesheet_name
            self.animation_name = None

        self.settings = self.settings_manager.get_settings(
            self.spritesheet_name, self.animation_name
        )

    def setup_ui(self):
        """Set up the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        content_layout.setSpacing(15)

        # Title
        mode_text = (
            "Animation Settings Override"
            if self.settings_type == "animation"
            else "Spritesheet Settings Override"
        )
        title_label = QLabel(mode_text)
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title_label.setStyleSheet("QLabel { color: #333333; }")
        content_layout.addWidget(title_label)

        # General settings section
        general_group = self.create_general_section()
        content_layout.addWidget(general_group)

        # Animation export settings section
        anim_group = self.create_animation_section()
        content_layout.addWidget(anim_group)

        # Frame export settings section (if applicable)
        if self.settings_type == "spritesheet":
            frame_group = self.create_frame_section()
            content_layout.addWidget(frame_group)

        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.store_input)
        ok_btn.setMinimumWidth(100)
        ok_btn.setDefault(True)
        button_layout.addWidget(ok_btn)

        if self.settings_type == "animation":
            preview_btn = QPushButton(self.tr("Preview animation"))
            preview_btn.clicked.connect(self.handle_preview_click)
            preview_btn.setMinimumWidth(130)
            button_layout.addWidget(preview_btn)

        cancel_btn = QPushButton(self.tr("Cancel"))
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setMinimumWidth(100)
        button_layout.addWidget(cancel_btn)

        main_layout.addLayout(button_layout)

    def create_general_section(self):
        """Create the general settings section."""
        group = QGroupBox("General export settings")
        layout = QGridLayout(group)

        row = 0

        # Name
        layout.addWidget(QLabel(self.tr("Name:")), row, 0)
        name_label = QLabel(self.name)
        name_label.setWordWrap(True)
        name_label.setMaximumWidth(200)
        layout.addWidget(name_label, row, 1)
        row += 1

        # Spritesheet (for animations)
        if self.settings_type == "animation" and "/" in self.name:
            layout.addWidget(QLabel(self.tr("Spritesheet:")), row, 0)
            spritesheet_label = QLabel(self.spritesheet_name)
            spritesheet_label.setWordWrap(True)
            spritesheet_label.setMaximumWidth(200)
            layout.addWidget(spritesheet_label, row, 1)
            row += 1

        # Filename (for animations)
        if self.settings_type == "animation":
            layout.addWidget(QLabel(self.tr("Filename:")), row, 0)
            self.filename_edit = QLineEdit()
            self.filename_edit.setPlaceholderText("Leave empty for auto-generated filename")
            layout.addWidget(self.filename_edit, row, 1)
            row += 1

        return group

    def create_animation_section(self):
        """Create the animation settings section."""
        group = QGroupBox("Animation export settings")
        layout = QGridLayout(group)

        row = 0

        # Animation format
        layout.addWidget(QLabel(self.tr("Animation format:")), row, 0)
        self.animation_format_combo = QComboBox()
        self.animation_format_combo.addItems(["None", "GIF", "WebP", "APNG"])
        self.animation_format_combo.currentTextChanged.connect(self.on_animation_format_change)
        layout.addWidget(self.animation_format_combo, row, 1)
        row += 1

        # FPS
        layout.addWidget(QLabel(self.tr("FPS:")), row, 0)
        self.fps_spinbox = QSpinBox()
        self.fps_spinbox.setRange(1, 144)
        self.fps_spinbox.setSuffix(" fps")
        layout.addWidget(self.fps_spinbox, row, 1)
        row += 1

        # Delay
        layout.addWidget(QLabel(self.tr("End delay (ms):")), row, 0)
        self.delay_spinbox = QSpinBox()
        self.delay_spinbox.setRange(0, 10000)
        self.delay_spinbox.setSuffix(" ms")
        layout.addWidget(self.delay_spinbox, row, 1)
        row += 1

        # Period
        layout.addWidget(QLabel(self.tr("Period (ms):")), row, 0)
        self.period_spinbox = QSpinBox()
        self.period_spinbox.setRange(0, 10000)
        self.period_spinbox.setSuffix(" ms")
        layout.addWidget(self.period_spinbox, row, 1)
        row += 1

        # Scale
        layout.addWidget(QLabel(self.tr("Scale:")), row, 0)
        self.scale_spinbox = QDoubleSpinBox()
        self.scale_spinbox.setRange(-10.0, 10.0)
        self.scale_spinbox.setSingleStep(0.1)
        self.scale_spinbox.setDecimals(2)
        layout.addWidget(self.scale_spinbox, row, 1)
        row += 1

        # Threshold
        layout.addWidget(QLabel(self.tr("Alpha threshold:")), row, 0)
        self.threshold_spinbox = QDoubleSpinBox()
        self.threshold_spinbox.setRange(0.0, 1.0)
        self.threshold_spinbox.setSingleStep(0.01)
        self.threshold_spinbox.setDecimals(3)
        layout.addWidget(self.threshold_spinbox, row, 1)
        row += 1

        # Indices
        layout.addWidget(QLabel(self.tr("Indices (comma-separated):")), row, 0)
        self.indices_edit = QLineEdit()
        self.indices_edit.setPlaceholderText("e.g., 0,1,2,3 or leave empty for all")
        layout.addWidget(self.indices_edit, row, 1)
        row += 1

        # Variable delay
        self.var_delay_check = QCheckBox("Variable delay")
        layout.addWidget(self.var_delay_check, row, 0, 1, 2)
        row += 1

        return group

    def create_frame_section(self):
        """Create the frame export settings section."""
        group = QGroupBox("Frame export settings")
        layout = QGridLayout(group)

        row = 0

        # Frames to keep
        layout.addWidget(QLabel(self.tr("Frames to keep:")), row, 0)
        self.frames_edit = QLineEdit()
        self.frames_edit.setPlaceholderText("e.g., 0,1,2,3 or leave empty for all")
        layout.addWidget(self.frames_edit, row, 1)
        row += 1

        # Frame format
        layout.addWidget(QLabel(self.tr("Frame format:")), row, 0)
        self.frame_format_combo = QComboBox()
        self.frame_format_combo.addItems(["PNG", "JPG", "JPEG", "BMP", "TIFF"])
        layout.addWidget(self.frame_format_combo, row, 1)
        row += 1

        # Frame scale
        layout.addWidget(QLabel(self.tr("Frame scale:")), row, 0)
        self.frame_scale_spinbox = QDoubleSpinBox()
        self.frame_scale_spinbox.setRange(-10.0, 10.0)
        self.frame_scale_spinbox.setSingleStep(0.1)
        self.frame_scale_spinbox.setDecimals(2)
        layout.addWidget(self.frame_scale_spinbox, row, 1)
        row += 1

        return group

    def load_current_values(self):
        """Load current values into the UI controls."""
        # General settings
        if self.filename_edit:
            self.filename_edit.setText(self.local_settings.get("filename", ""))

        # Animation settings
        anim_format = self.local_settings.get("animation_format", "")
        if anim_format and anim_format in ["None", "GIF", "WebP", "APNG"]:
            self.animation_format_combo.setCurrentText(anim_format)
        else:
            self.animation_format_combo.setCurrentText(self.settings.get("animation_format", "GIF"))

        self.fps_spinbox.setValue(self.local_settings.get("fps", self.settings.get("fps", 24)))
        self.delay_spinbox.setValue(
            self.local_settings.get("delay", self.settings.get("delay", 250))
        )
        self.period_spinbox.setValue(
            self.local_settings.get("period", self.settings.get("period", 0))
        )
        self.scale_spinbox.setValue(
            self.local_settings.get("scale", self.settings.get("scale", 1.0))
        )
        self.threshold_spinbox.setValue(
            self.local_settings.get("threshold", self.settings.get("threshold", 0.1))
        )

        # Indices
        indices = self.local_settings.get("indices", self.settings.get("indices", []))
        if indices:
            self.indices_edit.setText(",".join(map(str, indices)))

        # Variable delay
        self.var_delay_check.setChecked(
            self.local_settings.get("var_delay", self.settings.get("var_delay", False))
        )

        # Frame settings (if applicable)
        if self.settings_type == "spritesheet":
            frames = self.local_settings.get("frames", self.settings.get("frames", []))
            if frames:
                self.frames_edit.setText(",".join(map(str, frames)))

            frame_format = self.local_settings.get(
                "frame_format", self.settings.get("frame_format", "PNG")
            )
            self.frame_format_combo.setCurrentText(frame_format)

            self.frame_scale_spinbox.setValue(
                self.local_settings.get("frame_scale", self.settings.get("frame_scale", 1.0))
            )

        # Update animation format dependent fields
        self.on_animation_format_change()

    def on_animation_format_change(self):
        """Handle animation format change."""
        format_value = self.animation_format_combo.currentText()
        is_animation = format_value not in ["None", ""]

        # Enable/disable animation-specific controls
        self.fps_spinbox.setEnabled(is_animation)
        self.delay_spinbox.setEnabled(is_animation)
        self.period_spinbox.setEnabled(is_animation)
        self.var_delay_check.setEnabled(is_animation)

        # Update default filename if needed
        if self.filename_edit and self.filename_edit.text() == "":
            if self.settings_type == "animation" and "/" in self.name:
                filename = Utilities.format_filename(
                    self.settings.get("prefix"),
                    self.spritesheet_name,
                    self.name.rsplit("/", 1)[1],
                    self.settings.get("filename_format"),
                    self.settings.get("replace_rules"),
                    self.settings.get("suffix"),
                )
                self.filename_edit.setPlaceholderText(filename)

    def handle_preview_click(self):
        """Handle preview button click."""
        if self.app and hasattr(self.app, "show_animation_preview_window"):
            try:
                # Only allow animation preview for animations, not spritesheets
                if self.settings_type != "animation":
                    from PySide6.QtWidgets import QMessageBox

                    QMessageBox.information(
                        self,
                        self.tr("Info"),
                        self.tr("Preview is only available for animations, not spritesheets."),
                    )
                    return

                # Parse the animation name (format: "spritesheet.png/animation_name")
                if "/" not in self.name:
                    from PySide6.QtWidgets import QMessageBox

                    QMessageBox.warning(
                        self, self.tr("Preview Error"), self.tr("Invalid animation name format.")
                    )
                    return

                spritesheet_name, animation_name = self.name.rsplit("/", 1)

                # Find and select the spritesheet and animation in the main window
                # First, find the spritesheet
                spritesheet_found = False
                listbox_png = self.app.extract_tab_widget.listbox_png
                for i in range(listbox_png.count()):
                    item = listbox_png.item(i)
                    if item and item.text() == spritesheet_name:
                        listbox_png.setCurrentItem(item)
                        spritesheet_found = True
                        break

                if not spritesheet_found:
                    from PySide6.QtWidgets import QMessageBox

                    QMessageBox.warning(
                        self,
                        self.tr("Preview Error"),
                        self.tr("Could not find spritesheet: {name}").format(name=spritesheet_name),
                    )
                    return

                # Populate the animation list for this spritesheet
                self.app.extract_tab_widget.populate_animation_list(spritesheet_name)

                # Find and select the animation
                animation_found = False
                listbox_data = self.app.extract_tab_widget.listbox_data
                for i in range(listbox_data.count()):
                    item = listbox_data.item(i)
                    if item and item.text() == animation_name:
                        listbox_data.setCurrentItem(item)
                        animation_found = True
                        break

                if not animation_found:
                    from PySide6.QtWidgets import QMessageBox

                    QMessageBox.warning(
                        self,
                        self.tr("Preview Error"),
                        self.tr("Could not find animation: {name}").format(name=animation_name),
                    )
                    return

                # Call the preview function with the correctly selected animation
                self.app.extract_tab_widget.preview_selected_animation()

            except Exception as e:
                from PySide6.QtWidgets import QMessageBox

                QMessageBox.warning(
                    self,
                    self.tr("Preview Error"),
                    self.tr("Could not open preview: {error}").format(error=str(e)),
                )

    def store_input(self):
        """Store the input values and call the callback."""
        settings = {}

        # General settings
        if self.filename_edit:
            filename = self.filename_edit.text().strip()
            if filename:
                settings["filename"] = filename

        # Animation settings
        anim_format = self.animation_format_combo.currentText()
        if anim_format != "None":
            settings["animation_format"] = anim_format

        settings["fps"] = self.fps_spinbox.value()
        settings["delay"] = self.delay_spinbox.value()
        settings["period"] = self.period_spinbox.value()
        settings["scale"] = self.scale_spinbox.value()
        settings["threshold"] = self.threshold_spinbox.value()
        settings["var_delay"] = self.var_delay_check.isChecked()

        # Indices
        indices_text = self.indices_edit.text().strip()
        if indices_text:
            try:
                indices = [int(x.strip()) for x in indices_text.split(",") if x.strip()]
                settings["indices"] = indices
            except ValueError:
                from PySide6.QtWidgets import QMessageBox

                QMessageBox.warning(
                    self, "Invalid Input", "Indices must be comma-separated integers."
                )
                return

        # Frame settings (if applicable)
        if self.settings_type == "spritesheet":
            frames_text = self.frames_edit.text().strip()
            if frames_text:
                try:
                    frames = [int(x.strip()) for x in frames_text.split(",") if x.strip()]
                    settings["frames"] = frames
                except ValueError:
                    from PySide6.QtWidgets import QMessageBox

                    QMessageBox.warning(
                        self, "Invalid Input", "Frames must be comma-separated integers."
                    )
                    return

            settings["frame_format"] = self.frame_format_combo.currentText()
            settings["frame_scale"] = self.frame_scale_spinbox.value()

        # Call the callback with the settings
        self.on_store_callback(settings)
        self.accept()
