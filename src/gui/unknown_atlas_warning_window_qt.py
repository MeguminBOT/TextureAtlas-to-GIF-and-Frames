#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Qt-based Unknown Atlas Warning Window
Replaces the tkinter-based unknown_atlas_warning_window.py
"""

import os
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QWidget,
    QPushButton,
    QFrame,
    QGridLayout,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class UnknownAtlasWarningWindow(QDialog):
    """
    A Qt dialog that displays a warning about unknown atlases and provides options for handling them.

    This window shows a list of detected unknown atlases and explains their limitations,
    then allows the user to choose whether to proceed, skip, or cancel the operation.
    """

    def __init__(self, parent, unknown_atlases, input_directory=None):
        super().__init__(parent)
        self.unknown_atlases = unknown_atlases
        self.input_directory = input_directory
        self.result = "cancel"

        self.setWindowTitle("Unknown Atlas Warning")
        self.setModal(True)
        self.resize(650, 750)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.setup_ui()

    def setup_ui(self):
        """Set up the dialog UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Title section with warning icon
        title_layout = QHBoxLayout()

        warning_label = QLabel("⚠️")
        warning_label.setFont(QFont("Arial", 24))
        title_layout.addWidget(warning_label)

        title_text = QLabel("Unknown Atlas Warning")
        title_text.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title_layout.addWidget(title_text)
        title_layout.addStretch()

        main_layout.addLayout(title_layout)

        # Warning message
        message_text = (
            f"Warning: {len(self.unknown_atlases)} unknown atlas type(s) detected:\n\n"
            f"This means either the metadata file is missing or is unsupported.\n\n"
            f"The tool can attempt to extract the unknown atlas(es) but has these limitations:\n"
            f"• Animation export is not supported\n"
            f"• Cropping may be inconsistent\n"
            f"• Sprite detection may miss or incorrectly identify sprites\n"
            f"• Output may not be usable in rare cases\n\n"
            f"What would you like to do?"
        )

        message_label = QLabel(message_text)
        message_label.setWordWrap(True)
        message_label.setFont(QFont("Arial", 10))
        message_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        message_label.setStyleSheet("QLabel { margin-bottom: 15px; }")
        main_layout.addWidget(message_label)

        # Affected files section
        files_label = QLabel("Affected files:")
        files_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        main_layout.addWidget(files_label)

        # Create thumbnail section
        self.create_thumbnail_section(main_layout)

        # Button section
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        proceed_btn = QPushButton("Proceed anyway")
        proceed_btn.clicked.connect(self.on_proceed)
        proceed_btn.setMinimumWidth(120)
        proceed_btn.setDefault(True)
        button_layout.addWidget(proceed_btn)

        skip_btn = QPushButton("Skip unknown")
        skip_btn.clicked.connect(self.on_skip)
        skip_btn.setMinimumWidth(120)
        button_layout.addWidget(skip_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.on_cancel)
        cancel_btn.setMinimumWidth(120)
        button_layout.addWidget(cancel_btn)

        main_layout.addLayout(button_layout)

        # Set up keyboard shortcuts
        proceed_btn.setShortcut("Return")
        cancel_btn.setShortcut("Escape")

    def create_thumbnail_section(self, main_layout):
        """Create the thumbnail display section."""
        # Create scroll area for thumbnails
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(250)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Create widget to hold thumbnails
        thumbnail_widget = QWidget()
        thumbnail_layout = QGridLayout(thumbnail_widget)
        thumbnail_layout.setSpacing(10)

        # Add thumbnails in grid layout
        max_cols = 3
        row = 0
        col = 0

        for i, atlas_name in enumerate(self.unknown_atlases[:12]):
            thumb_frame = self.create_thumbnail_frame(atlas_name)
            thumbnail_layout.addWidget(thumb_frame, row, col)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        # Show "and more" if there are additional files
        if len(self.unknown_atlases) > 12:
            more_label = QLabel(f"... and {len(self.unknown_atlases) - 12} more")
            more_label.setFont(QFont("Arial", 10, QFont.Weight.ExtraLight))
            more_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            more_label.setStyleSheet("QLabel { color: #666; padding: 20px; }")
            thumbnail_layout.addWidget(more_label, row, col)

        # Set column stretch
        for i in range(max_cols):
            thumbnail_layout.setColumnStretch(i, 1)

        scroll_area.setWidget(thumbnail_widget)
        main_layout.addWidget(scroll_area)

    def create_thumbnail_frame(self, atlas_name):
        """Create a frame with thumbnail and filename for an atlas."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.Box)
        frame.setLineWidth(1)
        frame.setStyleSheet("QFrame { background-color: white; border: 1px solid #ccc; }")
        frame.setFixedSize(160, 140)

        layout = QVBoxLayout(frame)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)

        # Create thumbnail
        thumbnail_label = QLabel()
        thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumbnail_label.setFixedSize(80, 80)

        thumbnail_pixmap = self.create_thumbnail(atlas_name)
        if thumbnail_pixmap:
            thumbnail_label.setPixmap(thumbnail_pixmap)
        else:
            # Placeholder for failed thumbnails
            thumbnail_label.setText("📷")
            thumbnail_label.setFont(QFont("Arial", 20))
            thumbnail_label.setStyleSheet(
                "QLabel { border: 1px solid #ddd; background-color: #f5f5f5; }"
            )

        layout.addWidget(thumbnail_label)

        # Filename label
        name_label = QLabel(atlas_name)
        name_label.setFont(QFont("Arial", 8))
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setWordWrap(True)
        name_label.setMaximumWidth(150)
        layout.addWidget(name_label)

        return frame

    def create_thumbnail(self, filename):
        """Create a thumbnail pixmap for the given filename."""
        if not PIL_AVAILABLE or not self.input_directory:
            return None

        try:
            file_path = os.path.join(self.input_directory, filename)
            if not os.path.exists(file_path):
                return None

            with Image.open(file_path) as img:
                # Handle transparency
                if img.mode in ("RGBA", "LA", "P"):
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    background.paste(
                        img,
                        mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None,
                    )
                    img = background
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                # Create thumbnail
                img.thumbnail((80, 80), Image.Resampling.LANCZOS)

                # Convert to Qt pixmap
                img_path = os.path.join(os.environ.get("TEMP", "/tmp"), f"thumb_{filename}.png")
                img.save(img_path)
                pixmap = QPixmap(img_path)

                # Clean up temp file
                try:
                    os.remove(img_path)
                except Exception:
                    pass

                return pixmap.scaled(
                    80,
                    80,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )

        except Exception as e:
            print(f"Failed to create thumbnail for {filename}: {e}")
            return None

    def on_proceed(self):
        """Handle proceed button click."""
        self.result = "proceed"
        self.accept()

    def on_skip(self):
        """Handle skip button click."""
        self.result = "skip"
        self.accept()

    def on_cancel(self):
        """Handle cancel button click."""
        self.result = "cancel"
        self.reject()

    def get_result(self):
        """Get the user's choice."""
        return self.result

    @staticmethod
    def show_warning(parent_window, unknown_atlases, input_directory=None):
        """
        Show the unknown atlas warning dialog.

        Args:
            parent_window: The parent Qt widget
            unknown_atlases: List of unknown atlas filenames
            input_directory: Directory containing the atlas files (for thumbnails)

        Returns:
            str: User's choice - 'proceed', 'skip', or 'cancel'
        """
        dialog = UnknownAtlasWarningWindow(parent_window, unknown_atlases, input_directory)
        dialog.exec()
        return dialog.get_result()
