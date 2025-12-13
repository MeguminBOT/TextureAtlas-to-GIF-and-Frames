"""Theme options dialog for configuring appearance settings.

Provides a dialog for users to configure dark/light mode, icon style,
and custom icon asset paths.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .icon_provider import IconProvider, IconStyle, IconType


class ThemeOptionsDialog(QDialog):
    """Dialog for configuring theme and icon style options.

    Allows users to toggle dark mode, choose icon styles (emoji, simplified,
    or custom), and specify a folder for custom icon assets.

    Signals:
        settings_changed: Emitted when settings are applied.
    """

    settings_changed = Signal(dict)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        dark_mode: bool = False,
        icon_style: str = "simplified",
        custom_icons_path: str = "",
    ) -> None:
        """Initialize the theme options dialog.

        Args:
            parent: Parent widget.
            dark_mode: Current dark mode state.
            icon_style: Current icon style ('emoji', 'simplified', 'custom').
            custom_icons_path: Path to custom icon assets folder.
        """
        super().__init__(parent)
        self.setWindowTitle("Theme Options")
        self.setMinimumWidth(450)

        self._initial_dark_mode = dark_mode
        self._initial_icon_style = icon_style
        self._initial_custom_path = custom_icons_path

        self._build_ui()
        self._load_current_settings()

    def _build_ui(self) -> None:
        """Build the dialog layout."""
        layout = QVBoxLayout(self)

        # Theme group
        theme_group = QGroupBox("Theme")
        theme_layout = QFormLayout(theme_group)

        self.dark_mode_checkbox = QCheckBox("Enable Dark Mode")
        self.dark_mode_checkbox.setToolTip(
            "Switch between dark and light color schemes."
        )
        theme_layout.addRow(self.dark_mode_checkbox)

        layout.addWidget(theme_group)

        # Icon style group
        icon_group = QGroupBox("Icon Style")
        icon_layout = QVBoxLayout(icon_group)

        style_row = QHBoxLayout()
        style_label = QLabel("Display style:")
        self.style_combo = QComboBox()
        self.style_combo.addItem("Simplified (Colored circles)", "simplified")
        self.style_combo.addItem("Emoji characters", "emoji")
        self.style_combo.addItem("Custom icons", "custom")
        self.style_combo.setToolTip(
            "Choose how status indicators are displayed:\n"
            "• Simplified: Clean colored circles\n"
            "• Emoji: Unicode emoji characters (✅, ❌, etc.)\n"
            "• Custom: Your own icon assets"
        )
        self.style_combo.currentIndexChanged.connect(self._on_style_changed)
        style_row.addWidget(style_label)
        style_row.addWidget(self.style_combo, 1)
        icon_layout.addLayout(style_row)

        # Custom path selector
        self.custom_path_widget = QWidget()
        custom_layout = QHBoxLayout(self.custom_path_widget)
        custom_layout.setContentsMargins(0, 5, 0, 0)
        path_label = QLabel("Icons folder:")
        self.custom_path_edit = QLineEdit()
        self.custom_path_edit.setPlaceholderText("Path to custom icon assets...")
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_custom_path)
        custom_layout.addWidget(path_label)
        custom_layout.addWidget(self.custom_path_edit, 1)
        custom_layout.addWidget(browse_btn)
        icon_layout.addWidget(self.custom_path_widget)

        # Help text for custom icons
        self.custom_help_label = QLabel(
            "<small>Place PNG files named: icon_success.png, icon_error.png, "
            "icon_machine.png, icon_native.png, etc.</small>"
        )
        self.custom_help_label.setWordWrap(True)
        self.custom_help_label.setStyleSheet("color: gray;")
        icon_layout.addWidget(self.custom_help_label)

        # Preview section
        preview_row = QHBoxLayout()
        preview_label = QLabel("Preview:")
        self.preview_widget = QLabel()
        self.preview_widget.setMinimumHeight(30)
        preview_row.addWidget(preview_label)
        preview_row.addWidget(self.preview_widget, 1)
        icon_layout.addLayout(preview_row)

        layout.addWidget(icon_group)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        apply_btn = button_box.button(QDialogButtonBox.StandardButton.Apply)
        if apply_btn:
            apply_btn.clicked.connect(self._on_apply)
        layout.addWidget(button_box)

    def _load_current_settings(self) -> None:
        """Load current settings into the dialog controls."""
        self.dark_mode_checkbox.setChecked(self._initial_dark_mode)

        # Set icon style combo
        for i in range(self.style_combo.count()):
            if self.style_combo.itemData(i) == self._initial_icon_style:
                self.style_combo.setCurrentIndex(i)
                break

        self.custom_path_edit.setText(self._initial_custom_path)
        self._on_style_changed()
        self._update_preview()

    def _on_style_changed(self) -> None:
        """Handle icon style selection change."""
        style = self.style_combo.currentData()
        is_custom = style == "custom"
        self.custom_path_widget.setVisible(is_custom)
        self.custom_help_label.setVisible(is_custom)
        self._update_preview()

    def _browse_custom_path(self) -> None:
        """Open folder browser for custom icons path."""
        current = self.custom_path_edit.text()
        start_dir = current if current and Path(current).exists() else ""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Custom Icons Folder",
            start_dir,
        )
        if folder:
            self.custom_path_edit.setText(folder)
            self._update_preview()

    def _update_preview(self) -> None:
        """Update the preview display based on current settings."""
        style_str = self.style_combo.currentData()
        custom_path = self.custom_path_edit.text().strip()

        # Create a temporary provider for preview
        style = IconStyle(style_str) if style_str else IconStyle.SIMPLIFIED
        path = Path(custom_path) if custom_path else None

        temp_provider = IconProvider(style=style, custom_assets_path=path)

        if style == IconStyle.EMOJI:
            preview_text = (
                f"Machine: {temp_provider.get_text(IconType.QUALITY_MACHINE)}  "
                f"Unreviewed: {temp_provider.get_text(IconType.QUALITY_UNREVIEWED)}  "
                f"Reviewed: {temp_provider.get_text(IconType.QUALITY_REVIEWED)}  "
                f"Native: {temp_provider.get_text(IconType.QUALITY_NATIVE)}"
            )
            self.preview_widget.setText(preview_text)
        else:
            # For non-emoji modes, show colored indicators
            colors = {
                "Machine": "#9c27b0",  # Purple
                "Unreviewed": "#ff9800",  # Orange
                "Reviewed": "#00bcd4",  # Cyan
                "Native": "#2196f3",  # Blue
            }
            html = " ".join(
                f'<span style="color: {color};">●</span> {name}'
                for name, color in colors.items()
            )
            self.preview_widget.setText("")
            self.preview_widget.setTextFormat(Qt.TextFormat.RichText)
            self.preview_widget.setText(html)

    def get_settings(self) -> Dict[str, Any]:
        """Retrieve the current dialog settings.

        Returns:
            Dictionary with 'dark_mode', 'icon_style', and 'custom_icons_path'.
        """
        return {
            "dark_mode": self.dark_mode_checkbox.isChecked(),
            "icon_style": self.style_combo.currentData(),
            "custom_icons_path": self.custom_path_edit.text().strip(),
        }

    def _on_apply(self) -> None:
        """Apply current settings without closing the dialog."""
        self.settings_changed.emit(self.get_settings())

    def _on_accept(self) -> None:
        """Apply settings and close the dialog."""
        self.settings_changed.emit(self.get_settings())
        self.accept()


__all__ = ["ThemeOptionsDialog"]
