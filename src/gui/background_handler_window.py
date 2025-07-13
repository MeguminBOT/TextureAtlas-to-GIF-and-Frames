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
    QFrame,
    QCheckBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QPainter


class BackgroundHandlerWindow(QDialog):
    """
    A class that handles background color detection and keying options for unknown spritesheets.

    This window displays detected background colors for unknown spritesheets with individual checkboxes
    to control whether background removal should be applied to each spritesheet.
    """

    def __init__(self, parent, detection_results):
        super().__init__(parent)
        self.detection_results = detection_results
        self.result = {}
        self.checkbox_vars = {}

        self.setWindowTitle(self.tr("Background Color Options"))
        self.setModal(True)
        self.resize(750, 550)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # Filter out images that already have transparency
        self.filtered_results = [
            result for result in detection_results if not result.get("has_transparency", False)
        ]

        # For images with transparency, automatically set them to exclude background processing
        for detection_result in detection_results:
            if detection_result.get("has_transparency", False):
                self.result[detection_result["filename"]] = "exclude_background"

        if not self.filtered_results:
            print("[BackgroundHandlerWindow] No images need background processing")
            self.accept()
            return

        print(
            f"[BackgroundHandlerWindow] Filtered to {len(self.filtered_results)} images needing background processing"
        )

        self.setup_ui()

    def tr(self, text):
        """Translation helper method."""
        from PySide6.QtCore import QCoreApplication

        return QCoreApplication.translate(self.__class__.__name__, text)

    def setup_ui(self):
        """Set up the dialog UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Title section with icon
        title_layout = QHBoxLayout()

        icon_label = QLabel("🎨")
        icon_label.setFont(QFont("Arial", 24))
        title_layout.addWidget(icon_label)

        title_text = QLabel(self.tr("Background Color Options"))
        title_text.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title_layout.addWidget(title_text)
        title_layout.addStretch()

        main_layout.addLayout(title_layout)

        # Description
        description = self.tr(
            "Found {count} unknown spritesheet(s) with background colors.\n"
            "Check the box next to each file to remove its background color during processing:"
        ).format(count=len(self.filtered_results))

        desc_label = QLabel(description)
        desc_label.setFont(QFont("Arial", 10))
        desc_label.setWordWrap(True)
        main_layout.addWidget(desc_label)

        # Global controls
        global_layout = QHBoxLayout()

        select_all_btn = QPushButton(self.tr("Select All"))
        select_all_btn.clicked.connect(self.select_all)
        select_all_btn.setMaximumWidth(100)
        global_layout.addWidget(select_all_btn)

        select_none_btn = QPushButton(self.tr("Select None"))
        select_none_btn.clicked.connect(self.select_none)
        select_none_btn.setMaximumWidth(100)
        global_layout.addWidget(select_none_btn)

        global_layout.addStretch()
        main_layout.addLayout(global_layout)

        # Scrollable area for spritesheet entries
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        content_layout.setSpacing(3)

        # Add spritesheet entries
        for i, result in enumerate(self.filtered_results):
            entry_widget = self.create_spritesheet_entry(result, i)
            content_layout.addWidget(entry_widget)

        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

        # Options explanation
        options_frame = QFrame()
        options_layout = QVBoxLayout(options_frame)

        options_label = QLabel(self.tr("Processing Options:"))
        options_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        options_layout.addWidget(options_label)

        option_text = (
            "• Checked: Remove background colors (apply color keying)\n"
            "• Unchecked: Keep background colors but exclude them during sprite detection"
        )

        options_desc = QLabel(option_text)
        options_desc.setFont(QFont("Arial", 9))
        options_desc.setStyleSheet("QLabel { margin-left: 10px; }")
        options_layout.addWidget(options_desc)

        # Add transparent background tip
        transparency_tip = QLabel(
            self.tr(
                "💡 Tip: Checked files will have transparent backgrounds in PNG, WebP, and APNG outputs"
            )
        )
        transparency_tip.setFont(QFont("Arial", 8))
        transparency_tip.setStyleSheet("QLabel { margin-left: 10px; color: #0066cc; }")
        options_layout.addWidget(transparency_tip)

        main_layout.addWidget(options_frame)

        # Button section
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        apply_btn = QPushButton(self.tr("Apply Settings"))
        apply_btn.clicked.connect(self.on_apply)
        apply_btn.setMinimumWidth(120)
        apply_btn.setDefault(True)
        button_layout.addWidget(apply_btn)

        cancel_btn = QPushButton(self.tr("Cancel"))
        cancel_btn.clicked.connect(self.on_cancel)
        cancel_btn.setMinimumWidth(120)
        button_layout.addWidget(cancel_btn)

        main_layout.addLayout(button_layout)

        # Set up keyboard shortcuts
        apply_btn.setShortcut("Return")
        cancel_btn.setShortcut("Escape")

    def create_spritesheet_entry(self, result, index):
        """Create a widget for a single spritesheet entry."""
        # Alternating background colors
        bg_color = "#f0f0f0" if index % 2 == 0 else "#ffffff"

        entry_frame = QFrame()
        entry_frame.setFrameStyle(QFrame.Shape.Box)
        entry_frame.setLineWidth(1)
        entry_frame.setStyleSheet(
            f"QFrame {{ background-color: {bg_color}; border: 1px solid #ccc; }}"
        )

        layout = QVBoxLayout(entry_frame)
        layout.setSpacing(3)
        layout.setContentsMargins(8, 4, 8, 4)

        # Header with checkbox and filename
        header_layout = QHBoxLayout()

        checkbox = QCheckBox()
        checkbox.setChecked(True)  # Default to checked
        self.checkbox_vars[result["filename"]] = checkbox
        header_layout.addWidget(checkbox)

        filename_label = QLabel(self.tr("📄 {filename}").format(filename=result["filename"]))
        filename_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        header_layout.addWidget(filename_label)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Colors section
        colors_label = QLabel(self.tr("Detected background colors:"))
        colors_label.setFont(QFont("Arial", 9))
        colors_label.setStyleSheet("QLabel { margin-left: 15px; }")
        layout.addWidget(colors_label)

        # Show up to 3 colors
        for color_index, color in enumerate(result["colors"][:3]):
            color_layout = self.create_color_sample(color, color_index)
            layout.addLayout(color_layout)

        # Show if there are more colors
        if len(result["colors"]) > 3:
            more_label = QLabel(
                self.tr("... and {count} more colors").format(count=len(result["colors"]) - 3)
            )
            more_label.setFont(QFont("Arial", 8))
            more_label.setStyleSheet("QLabel { margin-left: 25px; color: gray; }")
            layout.addWidget(more_label)

        return entry_frame

    def create_color_sample(self, color, color_index):
        """Create a layout showing a color sample and its RGB values."""
        layout = QHBoxLayout()
        layout.setContentsMargins(25, 1, 0, 1)

        # Color sample widget
        color_sample = ColorSampleWidget(color)
        color_sample.setFixedSize(16, 16)
        layout.addWidget(color_sample)

        # RGB text
        rgb_text = self.tr("RGB({r}, {g}, {b})").format(r=color[0], g=color[1], b=color[2])
        priority_text = (
            self.tr("Primary")
            if color_index == 0
            else self.tr("Secondary {index}").format(index=color_index)
        )

        color_info = QLabel(
            self.tr("{priority}: {rgb}").format(priority=priority_text, rgb=rgb_text)
        )
        color_info.setFont(QFont("Arial", 9))
        layout.addWidget(color_info)
        layout.addStretch()

        return layout

    def select_all(self):
        """Select all checkboxes."""
        for checkbox in self.checkbox_vars.values():
            checkbox.setChecked(True)

    def select_none(self):
        """Unselect all checkboxes."""
        for checkbox in self.checkbox_vars.values():
            checkbox.setChecked(False)

    def on_apply(self):
        """Handle apply button click."""
        for filename, checkbox in self.checkbox_vars.items():
            if checkbox.isChecked():
                self.result[filename] = "key_background"
            else:
                self.result[filename] = "exclude_background"
        self.accept()

    def on_cancel(self):
        """Handle cancel button click."""
        self.result.clear()
        self.result["_cancelled"] = True
        self.reject()

    def get_result(self):
        """Get the processing results."""
        return self.result

    @staticmethod
    def show_background_options(parent_window, detection_results):
        """
        Show the background handling options dialog with individual controls.

        Args:
            parent_window: The parent Qt widget
            detection_results: List of dictionaries with keys:
                - 'filename': Name of the spritesheet file
                - 'colors': List of RGB tuples for detected background colors
                - 'has_transparency': Boolean indicating if image already has transparency

        Returns:
            dict: Dictionary mapping filenames to their background handling choice:
                - 'key_background': Apply color keying (remove background)
                - 'exclude_background': Exclude background during sprite detection
                - 'skip': Skip processing this file
                - {'_cancelled': True}: User cancelled the dialog (stops extraction)
        """
        print(f"[BackgroundHandlerWindow] Called with {len(detection_results)} detection results")

        dialog = BackgroundHandlerWindow(parent_window, detection_results)
        dialog.exec()
        return dialog.get_result()

    @staticmethod
    def reset_batch_state():
        """
        Reset any batch processing state.
        Provided for compatibility with existing code.
        """
        print("[BackgroundHandlerWindow] Batch state reset for new processing")


class ColorSampleWidget(QWidget):
    """A widget that displays a color sample."""

    def __init__(self, rgb_color):
        super().__init__()
        self.color = QColor(rgb_color[0], rgb_color[1], rgb_color[2])

    def tr(self, text):
        """Translation helper method."""
        from PySide6.QtCore import QCoreApplication

        return QCoreApplication.translate(self.__class__.__name__, text)

    def paintEvent(self, event):
        """Paint the color sample."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw border
        painter.setPen(QColor(0, 0, 0))
        painter.setBrush(self.color)
        painter.drawRect(1, 1, self.width() - 2, self.height() - 2)
