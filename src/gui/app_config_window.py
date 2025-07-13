#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import platform
import multiprocessing
import subprocess
import psutil
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QWidget,
    QPushButton,
    QLineEdit,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QGridLayout,
    QMessageBox,
    QTabWidget,
    QSpinBox,
    QDoubleSpinBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class AppConfigWindow(QDialog):
    """
    A scrollable window for configuring application settings.

    This window provides a comprehensive interface for configuring various application
    settings including resource limits, extraction defaults, compression defaults,
    update preferences, and UI options.
    """

    def __init__(self, parent, app_config):
        super().__init__(parent)
        self.app_config = app_config
        self.setWindowTitle(self.tr("App Options"))
        self.setModal(True)
        self.resize(520, 750)

        # Get system information
        self.get_system_info()

        # Initialize UI variables
        self.init_variables()

        self.setup_ui()
        self.load_current_settings()

    def tr(self, text):
        """Translation helper method."""
        from PySide6.QtCore import QCoreApplication
        return QCoreApplication.translate(self.__class__.__name__, text)


    def get_system_info(self):
        """Get system information for display."""
        self.max_cores = multiprocessing.cpu_count()
        self.max_threads = None
        self.max_memory_mb = int(psutil.virtual_memory().total / (1024 * 1024))

        # Get CPU information
        self.cpu_model = "Unknown CPU"
        try:
            if platform.system() == "Windows":
                self.cpu_model = (
                    subprocess.check_output("wmic cpu get Name", shell=True)
                    .decode(errors="ignore")
                    .split("\n")[1]
                    .strip()
                )
                self.max_threads = int(
                    subprocess.check_output("wmic cpu get NumberOfLogicalProcessors", shell=True)
                    .decode(errors="ignore")
                    .split("\n")[1]
                    .strip()
                )
            elif platform.system() == "Linux":
                with open("/proc/cpuinfo") as f:
                    for line in f:
                        if "model name" in line:
                            self.cpu_model = line.split(":")[1].strip()
                            break
                # Count logical processors
                self.max_threads = multiprocessing.cpu_count()
            elif platform.system() == "Darwin":
                self.cpu_model = (
                    subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"])
                    .decode(errors="ignore")
                    .strip()
                )
                self.max_threads = int(
                    subprocess.check_output(["sysctl", "-n", "hw.logicalcpu"])
                    .decode(errors="ignore")
                    .strip()
                )
        except Exception:
            pass

        if not self.max_threads:
            self.max_threads = self.max_cores

    def init_variables(self):
        """Initialize UI variables for settings."""
        # These will hold the UI controls
        self.cpu_threads_edit = None
        self.memory_limit_edit = None
        self.check_updates_cb = None
        self.auto_update_cb = None
        self.remember_input_dir_cb = None
        self.remember_output_dir_cb = None
        self.extraction_fields = {}
        self.compression_fields = {}

    def setup_ui(self):
        """Set up the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        # Create tab widget for organization
        tab_widget = QTabWidget()

        # System & Resources tab
        system_tab = self.create_system_tab()
        tab_widget.addTab(system_tab, "System & Resources")

        # Extraction Settings tab
        extraction_tab = self.create_extraction_tab()
        tab_widget.addTab(extraction_tab, "Extraction Defaults")

        # Compression Settings tab
        compression_tab = self.create_compression_tab()
        tab_widget.addTab(compression_tab, "Compression Defaults")

        # UI Settings tab
        ui_tab = self.create_ui_tab()
        tab_widget.addTab(ui_tab, "UI Preferences")

        # Update Settings tab
        update_tab = self.create_update_tab()
        tab_widget.addTab(update_tab, "Updates")

        main_layout.addWidget(tab_widget)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        reset_btn = QPushButton(self.tr("Reset to defaults"))
        reset_btn.clicked.connect(self.reset_to_defaults)
        reset_btn.setMinimumWidth(130)
        button_layout.addWidget(reset_btn)

        cancel_btn = QPushButton(self.tr("Cancel"))
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setMinimumWidth(100)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton(self.tr("Save"))
        save_btn.clicked.connect(self.save_config)
        save_btn.setMinimumWidth(100)
        save_btn.setDefault(True)
        button_layout.addWidget(save_btn)

        main_layout.addLayout(button_layout)

    def create_system_tab(self):
        """Create the system and resources tab."""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # System information
        sys_group = QGroupBox("Your Computer")
        sys_layout = QVBoxLayout(sys_group)

        cpu_label = QLabel(self.tr("CPU: {cpu} (Threads: {threads})").format(cpu=self.cpu_model, threads=self.max_threads))
        cpu_label.setFont(QFont("Arial", 9))
        sys_layout.addWidget(cpu_label)

        ram_label = QLabel(self.tr("RAM: {memory:,} MB").format(memory=self.max_memory_mb))
        ram_label.setFont(QFont("Arial", 9))
        sys_layout.addWidget(ram_label)

        layout.addWidget(sys_group)

        # Resource limits
        resource_group = QGroupBox("App Resource Limits")
        resource_layout = QGridLayout(resource_group)

        # CPU threads
        cpu_label = QLabel(self.tr("CPU threads to use (max: {max_threads}):").format(max_threads=self.max_threads))
        resource_layout.addWidget(cpu_label, 0, 0)

        self.cpu_threads_edit = QSpinBox()
        self.cpu_threads_edit.setRange(1, self.max_threads)
        resource_layout.addWidget(self.cpu_threads_edit, 0, 1)

        # Memory limit
        mem_label = QLabel(self.tr("Memory limit (MB, max: {max_memory}):").format(max_memory=self.max_memory_mb))
        resource_layout.addWidget(mem_label, 1, 0)

        self.memory_limit_edit = QSpinBox()
        self.memory_limit_edit.setRange(0, self.max_memory_mb)
        self.memory_limit_edit.setSuffix(" MB")
        resource_layout.addWidget(self.memory_limit_edit, 1, 1)

        mem_note = QLabel(self.tr("Note: Memory limit is for future use and not yet implemented."))
        mem_note.setFont(QFont("Arial", 8, QFont.Weight.ExtraLight))
        mem_note.setStyleSheet("QLabel { color: #666; }")
        resource_layout.addWidget(mem_note, 2, 0, 1, 2)

        layout.addWidget(resource_group)
        layout.addStretch()

        scroll_area.setWidget(widget)
        return scroll_area

    def create_extraction_tab(self):
        """Create the extraction defaults tab."""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Extraction defaults group
        group = QGroupBox("Extraction Default Settings")
        group_layout = QGridLayout(group)

        # Define extraction fields
        extraction_fields = {
            "animation_export": ("Enable animation export:", "bool", True),
            "animation_format": ("Animation format:", "combo", "GIF"),
            "fps": ("FPS:", "int", 24),
            "delay": ("End delay (ms):", "int", 250),
            "period": ("Period (ms):", "int", 0),
            "scale": ("Scale:", "float", 1.0),
            "threshold": ("Alpha threshold:", "float", 0.1),
            "frame_export": ("Enable frame export:", "bool", True),
            "frame_format": ("Frame format:", "combo", "PNG"),
            "frame_scale": ("Frame scale:", "float", 1.0),
        }

        row = 0
        for key, (label_text, field_type, default) in extraction_fields.items():
            label = QLabel(label_text)
            group_layout.addWidget(label, row, 0)

            if field_type == "bool":
                checkbox = QCheckBox()
                checkbox.setChecked(default)
                self.extraction_fields[key] = checkbox
                group_layout.addWidget(checkbox, row, 1)
            elif field_type == "combo":
                if "format" in key:
                    if "animation" in key:
                        options = ["GIF", "WebP", "APNG"]
                    else:
                        options = ["PNG", "JPG", "JPEG", "BMP", "TIFF"]

                    combo = QComboBox()
                    combo.addItems(options)
                    combo.setCurrentText(str(default))
                    self.extraction_fields[key] = combo
                    group_layout.addWidget(combo, row, 1)
            elif field_type == "int":
                spinbox = QSpinBox()
                spinbox.setRange(0, 99999)
                spinbox.setValue(default)
                self.extraction_fields[key] = spinbox
                group_layout.addWidget(spinbox, row, 1)
            elif field_type == "float":
                line_edit = QLineEdit(str(default))
                self.extraction_fields[key] = line_edit
                group_layout.addWidget(line_edit, row, 1)

            row += 1

        layout.addWidget(group)
        layout.addStretch()

        scroll_area.setWidget(widget)
        return scroll_area

    def create_compression_tab(self):
        """Create the compression defaults tab."""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # PNG Settings Group
        png_group = QGroupBox("PNG Settings")
        png_layout = QGridLayout(png_group)

        row = 0
        # PNG Compress Level
        png_layout.addWidget(QLabel(self.tr("Compress Level (0-9):")), row, 0)
        png_compress_spinbox = QSpinBox()
        png_compress_spinbox.setRange(0, 9)
        png_compress_spinbox.setValue(9)
        png_compress_spinbox.setToolTip(
            "PNG compression level (0-9):\n"
            "• 0: No compression (fastest, largest file)\n"
            "• 1-3: Low compression\n"
            "• 4-6: Medium compression\n"
            "• 7-9: High compression (slowest, smallest file)\n"
            "This doesn't affect the quality of the image, only the file size"
        )
        self.compression_fields["png_compress_level"] = png_compress_spinbox
        png_layout.addWidget(png_compress_spinbox, row, 1)
        row += 1

        # PNG Optimize
        png_optimize_checkbox = QCheckBox("Optimize PNG")
        png_optimize_checkbox.setChecked(True)
        png_optimize_checkbox.setToolTip(
            "PNG optimize:\n"
            "• Enabled: Uses additional compression techniques for smaller files\n"
            "When enabled, compression level is automatically set to 9\n"
            "Results in slower processing but better compression\n\n"
            "This doesn't affect the quality of the image, only the file size"
        )
        self.compression_fields["png_optimize"] = png_optimize_checkbox
        png_layout.addWidget(png_optimize_checkbox, row, 0, 1, 2)

        layout.addWidget(png_group)

        # WebP Settings Group
        webp_group = QGroupBox("WebP Settings")
        webp_layout = QGridLayout(webp_group)

        row = 0
        # WebP Lossless
        webp_lossless_checkbox = QCheckBox("Lossless WebP")
        webp_lossless_checkbox.setChecked(True)
        webp_lossless_checkbox.setToolTip(
            "WebP lossless mode:\n"
            "• Enabled: Perfect quality preservation, larger file size\n"
            "• Disabled: Lossy compression with adjustable quality\n"
            "When enabled, quality sliders are disabled"
        )
        self.compression_fields["webp_lossless"] = webp_lossless_checkbox
        webp_layout.addWidget(webp_lossless_checkbox, row, 0, 1, 2)
        row += 1

        # WebP Quality
        webp_layout.addWidget(QLabel(self.tr("Quality (0-100):")), row, 0)
        webp_quality_spinbox = QSpinBox()
        webp_quality_spinbox.setRange(0, 100)
        webp_quality_spinbox.setValue(90)
        webp_quality_spinbox.setToolTip(
            "WebP quality (0-100):\n"
            "• 0: Lowest quality, smallest file\n"
            "• 75: Balanced quality/size\n"
            "• 100: Highest quality, largest file\n"
            "Only used in lossy mode"
        )
        self.compression_fields["webp_quality"] = webp_quality_spinbox
        webp_layout.addWidget(webp_quality_spinbox, row, 1)
        row += 1

        # WebP Method
        webp_layout.addWidget(QLabel(self.tr("Method (0-6):")), row, 0)
        webp_method_spinbox = QSpinBox()
        webp_method_spinbox.setRange(0, 6)
        webp_method_spinbox.setValue(3)
        webp_method_spinbox.setToolTip(
            "WebP compression method (0-6):\n"
            "• 0: Fastest encoding, larger file\n"
            "• 3: Balanced speed/compression\n"
            "• 6: Slowest encoding, best compression\n"
            "Higher values take more time but produce smaller files"
        )
        self.compression_fields["webp_method"] = webp_method_spinbox
        webp_layout.addWidget(webp_method_spinbox, row, 1)
        row += 1

        # WebP Alpha Quality
        webp_layout.addWidget(QLabel(self.tr("Alpha Quality (0-100):")), row, 0)
        webp_alpha_quality_spinbox = QSpinBox()
        webp_alpha_quality_spinbox.setRange(0, 100)
        webp_alpha_quality_spinbox.setValue(90)
        webp_alpha_quality_spinbox.setToolTip(
            "WebP alpha channel quality (0-100):\n"
            "Controls transparency compression quality\n"
            "• 0: Maximum alpha compression\n"
            "• 100: Best alpha quality\n"
            "Only used in lossy mode"
        )
        self.compression_fields["webp_alpha_quality"] = webp_alpha_quality_spinbox
        webp_layout.addWidget(webp_alpha_quality_spinbox, row, 1)
        row += 1

        # WebP Exact
        webp_exact_checkbox = QCheckBox("Exact WebP")
        webp_exact_checkbox.setChecked(True)
        webp_exact_checkbox.setToolTip(
            "WebP exact mode:\n"
            "• Enabled: Preserves RGB values in transparent areas\n"
            "• Disabled: Allows optimization of transparent pixels\n"
            "Enable for better quality when transparency matters"
        )
        self.compression_fields["webp_exact"] = webp_exact_checkbox
        webp_layout.addWidget(webp_exact_checkbox, row, 0, 1, 2)

        layout.addWidget(webp_group)

        # AVIF Settings Group
        avif_group = QGroupBox("AVIF Settings")
        avif_layout = QGridLayout(avif_group)

        row = 0
        # AVIF Lossless
        avif_lossless_checkbox = QCheckBox("Lossless AVIF")
        avif_lossless_checkbox.setChecked(True)
        self.compression_fields["avif_lossless"] = avif_lossless_checkbox
        avif_layout.addWidget(avif_lossless_checkbox, row, 0, 1, 2)
        row += 1

        # AVIF Quality
        avif_layout.addWidget(QLabel(self.tr("Quality (0-100):")), row, 0)
        avif_quality_spinbox = QSpinBox()
        avif_quality_spinbox.setRange(0, 100)
        avif_quality_spinbox.setValue(90)
        avif_quality_spinbox.setToolTip(
            "AVIF quality (0-100):\n"
            "• 0-30: Low quality, very small files\n"
            "• 60-80: Good quality for most images\n"
            "• 85-95: High quality (recommended)\n"
            "• 95-100: Excellent quality, larger files"
        )
        self.compression_fields["avif_quality"] = avif_quality_spinbox
        avif_layout.addWidget(avif_quality_spinbox, row, 1)
        row += 1

        # AVIF Speed
        avif_layout.addWidget(QLabel(self.tr("Speed (0-10):")), row, 0)
        avif_speed_spinbox = QSpinBox()
        avif_speed_spinbox.setRange(0, 10)
        avif_speed_spinbox.setValue(5)
        avif_speed_spinbox.setToolTip(
            "AVIF encoding speed (0-10):\n"
            "• 0: Slowest encoding, best compression\n"
            "• 5: Balanced speed/compression (default)\n"
            "• 10: Fastest encoding, larger files\n"
            "Higher values encode faster but produce larger files"
        )
        self.compression_fields["avif_speed"] = avif_speed_spinbox
        avif_layout.addWidget(avif_speed_spinbox, row, 1)

        layout.addWidget(avif_group)

        # TIFF Settings Group
        tiff_group = QGroupBox("TIFF Settings")
        tiff_layout = QGridLayout(tiff_group)

        row = 0
        # TIFF Compression Type
        tiff_layout.addWidget(QLabel(self.tr("Compression Type:")), row, 0)
        tiff_compression_combobox = QComboBox()
        tiff_compression_combobox.addItems(["none", "lzw", "zip", "jpeg"])
        tiff_compression_combobox.setCurrentText("lzw")
        tiff_compression_combobox.setToolTip(
            "TIFF compression algorithm:\n"
            "• none: No compression, largest files\n"
            "• lzw: Lossless, good compression (recommended)\n"
            "• zip: Lossless, better compression\n"
            "• jpeg: Lossy compression, smallest files"
        )
        self.compression_fields["tiff_compression_type"] = tiff_compression_combobox
        tiff_layout.addWidget(tiff_compression_combobox, row, 1)
        row += 1

        # TIFF Quality
        tiff_layout.addWidget(QLabel(self.tr("Quality (0-100):")), row, 0)
        tiff_quality_spinbox = QSpinBox()
        tiff_quality_spinbox.setRange(0, 100)
        tiff_quality_spinbox.setValue(90)
        tiff_quality_spinbox.setToolTip(
            "TIFF quality (0-100):\n"
            "Only used with JPEG compression\n"
            "• 0-50: Low quality, small files\n"
            "• 75-90: Good quality\n"
            "• 95-100: Excellent quality"
        )
        self.compression_fields["tiff_quality"] = tiff_quality_spinbox
        tiff_layout.addWidget(tiff_quality_spinbox, row, 1)
        row += 1

        # TIFF Optimize
        tiff_optimize_checkbox = QCheckBox("Optimize TIFF")
        tiff_optimize_checkbox.setChecked(True)
        tiff_optimize_checkbox.setToolTip(
            "TIFF optimization:\n"
            "• Enabled: Optimize file structure for smaller size\n"
            "• Disabled: Standard TIFF format\n"
            "Recommended to keep enabled"
        )
        self.compression_fields["tiff_optimize"] = tiff_optimize_checkbox
        self.compression_fields["tiff_optimize"] = tiff_optimize_checkbox
        tiff_layout.addWidget(tiff_optimize_checkbox, row, 0, 1, 2)

        layout.addWidget(tiff_group)
        layout.addStretch()

        scroll_area.setWidget(widget)
        return scroll_area

    def create_update_tab(self):
        """Create the update settings tab."""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Update settings group
        group = QGroupBox("Update Preferences")
        group_layout = QVBoxLayout(group)

        self.check_updates_cb = QCheckBox("Check for updates on startup")
        self.check_updates_cb.stateChanged.connect(self.on_check_updates_change)
        group_layout.addWidget(self.check_updates_cb)

        self.auto_update_cb = QCheckBox("Auto-download and install updates")
        group_layout.addWidget(self.auto_update_cb)

        note_label = QLabel(self.tr("Note: Auto-update will download and install updates automatically when available."))
        note_label.setFont(QFont("Arial", 8, QFont.Weight.ExtraLight))
        note_label.setStyleSheet("QLabel { color: #666; }")
        note_label.setWordWrap(True)
        group_layout.addWidget(note_label)

        layout.addWidget(group)
        layout.addStretch()

        scroll_area.setWidget(widget)
        return scroll_area

    def on_check_updates_change(self, state):
        """Handle changes to the check updates checkbox."""
        # Enable/disable auto-update based on check updates setting
        self.auto_update_cb.setEnabled(state == Qt.CheckState.Checked.value)
        if state != Qt.CheckState.Checked.value:
            self.auto_update_cb.setChecked(False)

    def load_current_settings(self):
        """Load current settings from app config."""
        # Resource limits
        resource_limits = self.app_config.get("resource_limits", {})
        default_threads = (self.max_threads + 1) // 4

        cpu_default = resource_limits.get("cpu_cores", "auto")
        if cpu_default is None or cpu_default == "auto":
            cpu_default = default_threads
        self.cpu_threads_edit.setValue(int(cpu_default))

        default_mem = ((self.max_memory_mb // 4 + 9) // 10) * 10
        mem_default = resource_limits.get("memory_limit_mb", 0)
        if mem_default is None or mem_default == 0:
            mem_default = default_mem
        self.memory_limit_edit.setValue(int(mem_default))

        # Extraction defaults
        extraction_defaults = self.app_config.get("extraction_defaults", {})
        for key, control in self.extraction_fields.items():
            value = extraction_defaults.get(key)
            if value is not None:
                if isinstance(control, QComboBox):
                    control.setCurrentText(str(value))
                elif isinstance(control, QSpinBox):
                    control.setValue(int(value))
                elif isinstance(control, QLineEdit):
                    control.setText(str(value))
                elif isinstance(control, QCheckBox):
                    control.setChecked(bool(value))

        # Compression defaults
        compression_defaults = self.app_config.get("compression_defaults", {})
        for key, control in self.compression_fields.items():
            # Extract format and setting from key (e.g., "png_compress_level" -> format="png", setting="compress_level")
            if "_" in key:
                format_name = key.split("_", 1)[0]
                setting_name = "_".join(key.split("_")[1:])
                format_defaults = compression_defaults.get(format_name, {})
                value = format_defaults.get(setting_name)
            else:
                value = compression_defaults.get(key)

            if value is not None:
                if isinstance(control, QCheckBox):
                    control.setChecked(bool(value))
                elif isinstance(control, QSpinBox):
                    control.setValue(int(value))
                elif isinstance(control, QComboBox):
                    control.setCurrentText(str(value))

        # Update settings
        update_settings = self.app_config.get("update_settings", {})
        self.check_updates_cb.setChecked(update_settings.get("check_updates_on_startup", True))
        self.auto_update_cb.setChecked(update_settings.get("auto_download_updates", False))

        # UI settings
        ui_state = self.app_config.get("ui_state", {})
        if self.remember_input_dir_cb:
            self.remember_input_dir_cb.setChecked(ui_state.get("remember_input_directory", True))
        if self.remember_output_dir_cb:
            self.remember_output_dir_cb.setChecked(ui_state.get("remember_output_directory", True))

        # Update auto-update enabled state
        self.on_check_updates_change(self.check_updates_cb.checkState())

    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        reply = QMessageBox.question(
            self,
            "Reset to Defaults",
            "Are you sure you want to reset all settings to their default values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Reset resource limits
            default_threads = (self.max_threads + 1) // 4
            self.cpu_threads_edit.setValue(default_threads)

            default_mem = ((self.max_memory_mb // 4 + 9) // 10) * 10
            self.memory_limit_edit.setValue(default_mem)

            # Reset extraction defaults
            defaults = self.app_config.DEFAULTS["extraction_defaults"]

            for key, control in self.extraction_fields.items():
                if key in defaults:
                    default_value = defaults[key]
                    if isinstance(control, QComboBox):
                        control.setCurrentText(str(default_value))
                    elif isinstance(control, QSpinBox):
                        control.setValue(int(default_value))
                    elif isinstance(control, QDoubleSpinBox):
                        control.setValue(float(default_value))
                    elif isinstance(control, QCheckBox):
                        control.setChecked(bool(default_value))
                    elif isinstance(control, QLineEdit):
                        control.setText(str(default_value))

            # Reset compression defaults
            comp_defaults = self.app_config.DEFAULTS["compression_defaults"]

            for key, control in self.compression_fields.items():
                # Extract format and setting from key (e.g., "png_compress_level" -> format="png", setting="compress_level")
                if "_" in key:
                    format_name = key.split("_", 1)[0]
                    setting_name = "_".join(key.split("_")[1:])

                    if format_name in comp_defaults and setting_name in comp_defaults[format_name]:
                        default_value = comp_defaults[format_name][setting_name]

                        if isinstance(control, QCheckBox):
                            control.setChecked(bool(default_value))
                        elif isinstance(control, QSpinBox):
                            control.setValue(int(default_value))
                        elif isinstance(control, QComboBox):
                            control.setCurrentText(str(default_value))

            # Reset update settings
            update_defaults = self.app_config.DEFAULTS["update_settings"]
            self.check_updates_cb.setChecked(update_defaults.get("check_updates_on_startup", True))
            self.auto_update_cb.setChecked(update_defaults.get("auto_download_updates", False))

    def save_config(self):
        """Save the configuration settings."""
        try:
            # Validate and save resource limits
            resource_limits = {}

            cpu_threads = self.cpu_threads_edit.value()
            if cpu_threads > self.max_threads:
                raise ValueError(self.tr("CPU threads cannot exceed {max_threads}").format(max_threads=self.max_threads))
            resource_limits["cpu_cores"] = cpu_threads

            memory_limit = self.memory_limit_edit.value()
            if memory_limit > self.max_memory_mb:
                raise ValueError(self.tr("Memory limit cannot exceed {max_memory} MB").format(max_memory=self.max_memory_mb))
            resource_limits["memory_limit_mb"] = memory_limit

            # Save extraction defaults
            extraction_defaults = {}
            for key, control in self.extraction_fields.items():
                if isinstance(control, QComboBox):
                    extraction_defaults[key] = control.currentText()
                elif isinstance(control, QSpinBox):
                    extraction_defaults[key] = control.value()
                elif isinstance(control, QCheckBox):
                    extraction_defaults[key] = control.isChecked()
                elif isinstance(control, QLineEdit):
                    try:
                        if key in ["scale", "threshold", "frame_scale"]:
                            extraction_defaults[key] = float(control.text())
                        else:
                            extraction_defaults[key] = int(control.text())
                    except ValueError:
                        raise ValueError(self.tr("Invalid value for {key}: {value}").format(key=key, value=control.text()))

            # Save compression defaults
            compression_defaults = {"png": {}, "webp": {}, "avif": {}, "tiff": {}}

            for key, control in self.compression_fields.items():
                # Extract format and setting from key (e.g., "png_compress_level" -> format="png", setting="compress_level")
                if "_" in key:
                    format_name = key.split("_", 1)[0]
                    setting_name = "_".join(key.split("_")[1:])

                    if format_name in compression_defaults:
                        if isinstance(control, QCheckBox):
                            compression_defaults[format_name][setting_name] = control.isChecked()
                        elif isinstance(control, QSpinBox):
                            compression_defaults[format_name][setting_name] = control.value()
                        elif isinstance(control, QComboBox):
                            compression_defaults[format_name][setting_name] = control.currentText()

            # Save update settings
            update_settings = {
                "check_updates_on_startup": self.check_updates_cb.isChecked(),
                "auto_download_updates": self.auto_update_cb.isChecked(),
            }

            # Save UI settings
            ui_state = self.app_config.settings.setdefault("ui_state", {})
            if self.remember_input_dir_cb:
                ui_state["remember_input_directory"] = self.remember_input_dir_cb.isChecked()
            if self.remember_output_dir_cb:
                ui_state["remember_output_directory"] = self.remember_output_dir_cb.isChecked()

            # Update app config
            self.app_config.settings["resource_limits"] = resource_limits
            self.app_config.settings["extraction_defaults"] = extraction_defaults
            self.app_config.settings["compression_defaults"] = compression_defaults
            self.app_config.settings["update_settings"] = update_settings

            # Save to file
            self.app_config.save()

            QMessageBox.information(
                self, "Settings Saved", "Configuration has been saved successfully."
            )
            self.accept()

        except ValueError as e:
            QMessageBox.critical(self, self.tr("Invalid Input"), self.tr("Error: {error}").format(error=str(e)))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to save configuration: {error}").format(error=str(e)))

    @staticmethod
    def parse_value(key, val, expected_type):
        """
        Static method to parse and validate a value based on its expected type.

        Args:
            key: The configuration key name
            val: The value to parse
            expected_type: The expected type ('int', 'float', 'bool', 'str')

        Returns:
            The parsed value

        Raises:
            ValueError: If the value cannot be parsed or is invalid
        """
        if expected_type == "int":
            return int(val)
        elif expected_type == "float":
            return float(val)
        elif expected_type == "bool":
            if isinstance(val, bool):
                return val
            return str(val).lower() in ("true", "1", "yes", "on")
        else:
            return str(val)

    def create_ui_tab(self):
        """Create the UI preferences tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Directory Memory Settings group
        dir_group = QGroupBox("Directory Memory")
        dir_layout = QVBoxLayout(dir_group)

        # Remember input directory checkbox
        self.remember_input_dir_cb = QCheckBox("Remember last used input directory")
        self.remember_input_dir_cb.setToolTip(self.tr("When enabled, the app will remember and restore the last used input directory on startup"))
        dir_layout.addWidget(self.remember_input_dir_cb)

        # Remember output directory checkbox
        self.remember_output_dir_cb = QCheckBox("Remember last used output directory")
        self.remember_output_dir_cb.setToolTip(self.tr("When enabled, the app will remember and restore the last used output directory on startup"))
        dir_layout.addWidget(self.remember_output_dir_cb)

        layout.addWidget(dir_group)
        layout.addStretch()

        return widget
