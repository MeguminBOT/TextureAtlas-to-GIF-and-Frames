# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QSpinBox,
    QCheckBox,
    QComboBox,
    QPushButton,
    QGroupBox,
    QScrollArea,
    QWidget,
)
from PySide6.QtCore import Qt


class CompressionSettingsWindow(QDialog):
    """
    A dialog window for configuring compression settings based on the selected frame format.

    This window shows format-specific compression settings and integrates with the
    SettingsManager and AppConfig classes for storing and retrieving default values.
    """

    def __init__(self, parent=None, settings_manager=None, app_config=None, current_format="PNG"):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.app_config = app_config
        self.current_format = current_format.upper()

        # Store original values for comparison
        self.original_values = {}

        # Dictionary to hold all compression widgets
        self.compression_widgets = {}

        self.setWindowTitle(self.tr("Compression Settings"))
        self.setModal(True)
        self.resize(400, 500)

        self.setup_ui()
        self.load_current_values()

    def tr(self, text):
        """Translation helper method."""
        from PySide6.QtCore import QCoreApplication

        return QCoreApplication.translate(self.__class__.__name__, text)

    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Create scroll area for settings
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Create content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        # Format label
        format_label = QLabel(
            self.tr("Compression Settings for {format}").format(format=self.current_format)
        )
        format_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        content_layout.addWidget(format_label)

        # Create settings based on format
        if self.current_format == "PNG":
            self.create_png_settings(content_layout)
        elif self.current_format == "WEBP":
            self.create_webp_settings(content_layout)
        elif self.current_format == "AVIF":
            self.create_avif_settings(content_layout)
        elif self.current_format == "TIFF":
            self.create_tiff_settings(content_layout)
        else:
            # No compression settings for this format
            no_settings_label = QLabel(
                self.tr("No compression settings available for {format} format.").format(
                    format=self.current_format
                )
            )
            no_settings_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            content_layout.addWidget(no_settings_label)

        content_layout.addStretch()
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton(self.tr("Cancel"))
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        ok_button = QPushButton(self.tr("OK"))
        ok_button.clicked.connect(self.accept_changes)
        ok_button.setDefault(True)
        button_layout.addWidget(ok_button)

        layout.addLayout(button_layout)

    def create_png_settings(self, layout):
        """Create PNG compression settings."""
        group = QGroupBox("PNG Compression Settings")
        grid = QGridLayout(group)

        # Compress Level
        grid.addWidget(QLabel(self.tr("Compress Level (0-9):")), 0, 0)
        compress_level = QSpinBox()
        compress_level.setRange(0, 9)
        compress_level.setValue(9)
        compress_level.setToolTip(
            "PNG compression level (0-9):\n"
            "• 0: No compression (fastest, largest file)\n"
            "• 1-3: Low compression\n"
            "• 4-6: Medium compression\n"
            "• 7-9: High compression (slowest, smallest file)\n"
            "This doesn't affect the quality of the image, only the file size"
        )
        grid.addWidget(compress_level, 0, 1)

        # Optimize
        optimize = QCheckBox("Optimize PNG")
        optimize.setToolTip(
            "PNG optimize:\n"
            "• Enabled: Uses additional compression techniques for smaller files\n"
            "When enabled, compression level is automatically set to 9\n"
            "Results in slower processing but better compression\n\n"
            "This doesn't affect the quality of the image, only the file size"
        )
        optimize.toggled.connect(
            lambda checked: self.on_png_optimize_changed(checked, compress_level)
        )
        grid.addWidget(optimize, 1, 0, 1, 2)

        self.compression_widgets["PNG"] = {"compress_level": compress_level, "optimize": optimize}

        layout.addWidget(group)

    def create_webp_settings(self, layout):
        """Create WebP compression settings."""
        group = QGroupBox("WebP Compression Settings")
        grid = QGridLayout(group)

        # Lossless
        lossless = QCheckBox("Lossless WebP")
        lossless.setToolTip(
            "WebP lossless mode:\n"
            "• Enabled: Perfect quality preservation, larger file size\n"
            "• Disabled: Lossy compression with adjustable quality\n"
            "When enabled, quality sliders are disabled"
        )
        grid.addWidget(lossless, 0, 0, 1, 2)

        # Quality
        grid.addWidget(QLabel(self.tr("Quality (0-100):")), 1, 0)
        quality = QSpinBox()
        quality.setRange(0, 100)
        quality.setValue(100)
        quality.setToolTip(
            "WebP quality (0-100):\n"
            "• 0: Lowest quality, smallest file\n"
            "• 75: Balanced quality/size\n"
            "• 100: Highest quality, largest file\n"
            "Only used in lossy mode"
        )
        grid.addWidget(quality, 1, 1)

        # Method
        grid.addWidget(QLabel(self.tr("Method (0-6):")), 2, 0)
        method = QSpinBox()
        method.setRange(0, 6)
        method.setValue(6)
        method.setToolTip(
            "WebP compression method (0-6):\n"
            "• 0: Fastest encoding, larger file\n"
            "• 3: Balanced speed/compression\n"
            "• 6: Slowest encoding, best compression\n"
            "Higher values take more time but produce smaller files"
        )
        grid.addWidget(method, 2, 1)

        # Alpha Quality
        grid.addWidget(QLabel(self.tr("Alpha Quality (0-100):")), 3, 0)
        alpha_quality = QSpinBox()
        alpha_quality.setRange(0, 100)
        alpha_quality.setValue(100)
        alpha_quality.setToolTip(
            "WebP alpha channel quality (0-100):\n"
            "Controls transparency compression quality\n"
            "• 0: Maximum alpha compression\n"
            "• 100: Best alpha quality\n"
            "Only used in lossy mode"
        )
        grid.addWidget(alpha_quality, 3, 1)

        # Exact
        exact = QCheckBox("Exact WebP")
        exact.setToolTip(
            "WebP exact mode:\n"
            "• Enabled: Preserves RGB values in transparent areas\n"
            "• Disabled: Allows optimization of transparent pixels\n"
            "Enable for better quality when transparency matters"
        )
        grid.addWidget(exact, 4, 0, 1, 2)

        # Connect lossless toggle
        lossless.toggled.connect(
            lambda checked: self.on_webp_lossless_changed(checked, quality, alpha_quality)
        )

        self.compression_widgets["WEBP"] = {
            "lossless": lossless,
            "quality": quality,
            "method": method,
            "alpha_quality": alpha_quality,
            "exact": exact,
        }

        layout.addWidget(group)

    def create_avif_settings(self, layout):
        """Create AVIF compression settings."""
        group = QGroupBox("AVIF Compression Settings")
        grid = QGridLayout(group)

        # Lossless
        lossless = QCheckBox("Lossless AVIF")
        lossless.setToolTip(
            "AVIF lossless mode:\n"
            "• Enabled: Perfect quality preservation, larger file size\n"
            "• Disabled: Lossy compression with adjustable quality\n"
            "When enabled, quality slider is disabled"
        )
        grid.addWidget(lossless, 0, 0, 1, 2)

        # Quality
        grid.addWidget(QLabel(self.tr("Quality (0-100):")), 1, 0)
        quality = QSpinBox()
        quality.setRange(0, 100)
        quality.setValue(100)
        quality.setToolTip(
            "AVIF quality (0-100):\n"
            "• 0: Lowest quality, smallest file\n"
            "• 100: Highest quality, largest file\n"
            "Only used in lossy mode"
        )
        grid.addWidget(quality, 1, 1)

        # Speed
        grid.addWidget(QLabel(self.tr("Speed (0-10):")), 2, 0)
        speed = QSpinBox()
        speed.setRange(0, 10)
        speed.setValue(5)
        speed.setToolTip(
            "AVIF encoding speed (0-10):\n"
            "• 0: Slowest encoding, best compression\n"
            "• 5: Balanced speed/compression\n"
            "• 10: Fastest encoding, larger file\n"
            "Higher values encode faster but produce larger files.\n"
            "AVIF may take much longer to encode than other formats."
        )
        grid.addWidget(speed, 2, 1)

        # Connect lossless toggle
        lossless.toggled.connect(lambda checked: self.on_avif_lossless_changed(checked, quality))

        self.compression_widgets["AVIF"] = {
            "lossless": lossless,
            "quality": quality,
            "speed": speed,
        }

        layout.addWidget(group)

    def create_tiff_settings(self, layout):
        """Create TIFF compression settings."""
        group = QGroupBox("TIFF Compression Settings")
        grid = QGridLayout(group)

        # Compression Type
        grid.addWidget(QLabel(self.tr("Compression Type:")), 0, 0)
        compression_type = QComboBox()
        compression_type.addItems(["none", "lzw", "zip", "jpeg"])
        compression_type.setCurrentText("lzw")
        compression_type.setToolTip(
            "TIFF compression type:\n"
            "• None: No compression (largest files, fastest)\n"
            "• LZW: Lossless compression (good for graphics)\n"
            "• ZIP: Lossless compression (good for photos)\n"
            "• JPEG: Lossy compression (smallest files, adjustable quality)"
        )
        grid.addWidget(compression_type, 0, 1)

        # Quality
        grid.addWidget(QLabel(self.tr("Quality (0-100):")), 1, 0)
        quality = QSpinBox()
        quality.setRange(0, 100)
        quality.setValue(100)
        quality.setToolTip(
            "TIFF JPEG quality (0-100):\n"
            "Only used when compression type is JPEG\n"
            "• 100: Highest quality, largest file"
        )
        grid.addWidget(quality, 1, 1)

        # Optimize
        optimize = QCheckBox("Optimize TIFF")
        optimize.setToolTip(
            "TIFF optimize:\n"
            "• Enabled: Use additional optimization techniques\n"
            "Results in better compression but slower processing\n"
            "Not available when compression type is 'None'"
        )
        grid.addWidget(optimize, 2, 0, 1, 2)

        # Connect compression type change
        compression_type.currentTextChanged.connect(
            lambda text: self.on_tiff_compression_type_changed(text, quality, optimize)
        )

        self.compression_widgets["TIFF"] = {
            "compression_type": compression_type,
            "quality": quality,
            "optimize": optimize,
        }

        layout.addWidget(group)

    def on_png_optimize_changed(self, checked, compress_level_widget):
        """Handle PNG optimize checkbox changes."""
        if checked:
            compress_level_widget.setValue(9)
            compress_level_widget.setEnabled(False)
        else:
            compress_level_widget.setEnabled(True)

    def on_webp_lossless_changed(self, checked, quality_widget, alpha_quality_widget):
        """Handle WebP lossless checkbox changes."""
        quality_widget.setEnabled(not checked)
        alpha_quality_widget.setEnabled(not checked)

    def on_avif_lossless_changed(self, checked, quality_widget):
        """Handle AVIF lossless checkbox changes."""
        quality_widget.setEnabled(not checked)

    def on_tiff_compression_type_changed(self, compression_type, quality_widget, optimize_widget):
        """Handle TIFF compression type changes."""
        if compression_type == "none":
            quality_widget.setEnabled(False)
            optimize_widget.setEnabled(False)
        elif compression_type == "jpeg":
            quality_widget.setEnabled(True)
            optimize_widget.setEnabled(True)
        else:
            quality_widget.setEnabled(False)
            optimize_widget.setEnabled(True)

    def load_current_values(self):
        """Load current values from SettingsManager and AppConfig."""
        if not self.settings_manager or not self.app_config:
            return

        # Get current global settings from SettingsManager
        global_settings = self.settings_manager.global_settings

        # Get compression defaults from AppConfig
        compression_defaults = self.app_config.get_format_compression_settings(
            self.current_format.lower()
        )

        # Load format-specific settings
        if self.current_format == "PNG":
            self.load_png_values(global_settings, compression_defaults)
        elif self.current_format == "WEBP":
            self.load_webp_values(global_settings, compression_defaults)
        elif self.current_format == "AVIF":
            self.load_avif_values(global_settings, compression_defaults)
        elif self.current_format == "TIFF":
            self.load_tiff_values(global_settings, compression_defaults)

        # Store original values for comparison
        self.store_original_values()

    def load_png_values(self, global_settings, defaults):
        """Load PNG settings values."""
        if "PNG" not in self.compression_widgets:
            return

        widgets = self.compression_widgets["PNG"]

        # Load from global settings first, then fallback to defaults
        compress_level = global_settings.get(
            "png_compress_level", defaults.get("png_compress_level", 9)
        )
        optimize = global_settings.get("png_optimize", defaults.get("png_optimize", True))

        widgets["compress_level"].setValue(compress_level)
        widgets["optimize"].setChecked(optimize)

        # Trigger optimize change to update UI state
        self.on_png_optimize_changed(optimize, widgets["compress_level"])

    def load_webp_values(self, global_settings, defaults):
        """Load WebP settings values."""
        if "WEBP" not in self.compression_widgets:
            return

        widgets = self.compression_widgets["WEBP"]

        lossless = global_settings.get("webp_lossless", defaults.get("webp_lossless", True))
        quality = global_settings.get("webp_quality", defaults.get("webp_quality", 100))
        method = global_settings.get("webp_method", defaults.get("webp_method", 6))
        alpha_quality = global_settings.get(
            "webp_alpha_quality", defaults.get("webp_alpha_quality", 100)
        )
        exact = global_settings.get("webp_exact", defaults.get("webp_exact", True))

        widgets["lossless"].setChecked(lossless)
        widgets["quality"].setValue(quality)
        widgets["method"].setValue(method)
        widgets["alpha_quality"].setValue(alpha_quality)
        widgets["exact"].setChecked(exact)

        # Trigger lossless change to update UI state
        self.on_webp_lossless_changed(lossless, widgets["quality"], widgets["alpha_quality"])

    def load_avif_values(self, global_settings, defaults):
        """Load AVIF settings values."""
        if "AVIF" not in self.compression_widgets:
            return

        widgets = self.compression_widgets["AVIF"]

        lossless = global_settings.get("avif_lossless", defaults.get("avif_lossless", True))
        quality = global_settings.get("avif_quality", defaults.get("avif_quality", 100))
        speed = global_settings.get("avif_speed", defaults.get("avif_speed", 5))

        widgets["lossless"].setChecked(lossless)
        widgets["quality"].setValue(quality)
        widgets["speed"].setValue(speed)

        # Trigger lossless change to update UI state
        self.on_avif_lossless_changed(lossless, widgets["quality"])

    def load_tiff_values(self, global_settings, defaults):
        """Load TIFF settings values."""
        if "TIFF" not in self.compression_widgets:
            return

        widgets = self.compression_widgets["TIFF"]

        compression_type = global_settings.get(
            "tiff_compression_type", defaults.get("tiff_compression_type", "lzw")
        )
        quality = global_settings.get("tiff_quality", defaults.get("tiff_quality", 100))
        optimize = global_settings.get("tiff_optimize", defaults.get("tiff_optimize", True))

        widgets["compression_type"].setCurrentText(compression_type)
        widgets["quality"].setValue(quality)
        widgets["optimize"].setChecked(optimize)

        # Trigger compression type change to update UI state
        self.on_tiff_compression_type_changed(
            compression_type, widgets["quality"], widgets["optimize"]
        )

    def store_original_values(self):
        """Store the original values for comparison."""
        self.original_values = {}

        if self.current_format == "PNG" and "PNG" in self.compression_widgets:
            widgets = self.compression_widgets["PNG"]
            self.original_values = {
                "png_compress_level": widgets["compress_level"].value(),
                "png_optimize": widgets["optimize"].isChecked(),
            }
        elif self.current_format == "WEBP" and "WEBP" in self.compression_widgets:
            widgets = self.compression_widgets["WEBP"]
            self.original_values = {
                "webp_lossless": widgets["lossless"].isChecked(),
                "webp_quality": widgets["quality"].value(),
                "webp_method": widgets["method"].value(),
                "webp_alpha_quality": widgets["alpha_quality"].value(),
                "webp_exact": widgets["exact"].isChecked(),
            }
        elif self.current_format == "AVIF" and "AVIF" in self.compression_widgets:
            widgets = self.compression_widgets["AVIF"]
            self.original_values = {
                "avif_lossless": widgets["lossless"].isChecked(),
                "avif_quality": widgets["quality"].value(),
                "avif_speed": widgets["speed"].value(),
            }
        elif self.current_format == "TIFF" and "TIFF" in self.compression_widgets:
            widgets = self.compression_widgets["TIFF"]
            self.original_values = {
                "tiff_compression_type": widgets["compression_type"].currentText(),
                "tiff_quality": widgets["quality"].value(),
                "tiff_optimize": widgets["optimize"].isChecked(),
            }

    def get_current_values(self):
        """Get the current values from the widgets."""
        if self.current_format == "PNG" and "PNG" in self.compression_widgets:
            widgets = self.compression_widgets["PNG"]
            return {
                "png_compress_level": widgets["compress_level"].value(),
                "png_optimize": widgets["optimize"].isChecked(),
            }
        elif self.current_format == "WEBP" and "WEBP" in self.compression_widgets:
            widgets = self.compression_widgets["WEBP"]
            return {
                "webp_lossless": widgets["lossless"].isChecked(),
                "webp_quality": widgets["quality"].value(),
                "webp_method": widgets["method"].value(),
                "webp_alpha_quality": widgets["alpha_quality"].value(),
                "webp_exact": widgets["exact"].isChecked(),
            }
        elif self.current_format == "AVIF" and "AVIF" in self.compression_widgets:
            widgets = self.compression_widgets["AVIF"]
            return {
                "avif_lossless": widgets["lossless"].isChecked(),
                "avif_quality": widgets["quality"].value(),
                "avif_speed": widgets["speed"].value(),
            }
        elif self.current_format == "TIFF" and "TIFF" in self.compression_widgets:
            widgets = self.compression_widgets["TIFF"]
            return {
                "tiff_compression_type": widgets["compression_type"].currentText(),
                "tiff_quality": widgets["quality"].value(),
                "tiff_optimize": widgets["optimize"].isChecked(),
            }
        return {}

    def values_changed(self):
        """Check if any values have changed from the original."""
        current_values = self.get_current_values()
        return current_values != self.original_values

    def accept_changes(self):
        """Accept changes and update settings if values have changed."""
        if not self.settings_manager:
            self.accept()
            return

        # Only update if values have actually changed
        if self.values_changed():
            current_values = self.get_current_values()

            # Update global settings directly with compression settings
            self.settings_manager.set_global_settings(**current_values)

        self.accept()
