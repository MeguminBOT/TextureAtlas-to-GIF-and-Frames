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
        self.setWindowTitle("App Options")
        self.setModal(True)
        self.resize(520, 750)

        # Get system information
        self.get_system_info()

        # Initialize UI variables
        self.init_variables()

        self.setup_ui()
        self.load_current_settings()

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

        # Update Settings tab
        update_tab = self.create_update_tab()
        tab_widget.addTab(update_tab, "Updates")

        main_layout.addWidget(tab_widget)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        reset_btn = QPushButton("Reset to defaults")
        reset_btn.clicked.connect(self.reset_to_defaults)
        reset_btn.setMinimumWidth(130)
        button_layout.addWidget(reset_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setMinimumWidth(100)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
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

        cpu_label = QLabel(f"CPU: {self.cpu_model} (Threads: {self.max_threads})")
        cpu_label.setFont(QFont("Arial", 9))
        sys_layout.addWidget(cpu_label)

        ram_label = QLabel(f"RAM: {self.max_memory_mb:,} MB")
        ram_label.setFont(QFont("Arial", 9))
        sys_layout.addWidget(ram_label)

        layout.addWidget(sys_group)

        # Resource limits
        resource_group = QGroupBox("App Resource Limits")
        resource_layout = QGridLayout(resource_group)

        # CPU threads
        cpu_label = QLabel(f"CPU threads to use (max: {self.max_threads}):")
        resource_layout.addWidget(cpu_label, 0, 0)

        self.cpu_threads_edit = QSpinBox()
        self.cpu_threads_edit.setRange(1, self.max_threads)
        resource_layout.addWidget(self.cpu_threads_edit, 0, 1)

        # Memory limit
        mem_label = QLabel(f"Memory limit (MB, max: {self.max_memory_mb}):")
        resource_layout.addWidget(mem_label, 1, 0)

        self.memory_limit_edit = QSpinBox()
        self.memory_limit_edit.setRange(0, self.max_memory_mb)
        self.memory_limit_edit.setSuffix(" MB")
        resource_layout.addWidget(self.memory_limit_edit, 1, 1)

        mem_note = QLabel("Note: Memory limit is for future use and not yet implemented.")
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
            "fps": ("FPS:", "int", 24),
            "delay": ("End delay (ms):", "int", 250),
            "period": ("Period (ms):", "int", 0),
            "scale": ("Scale:", "float", 1.0),
            "threshold": ("Alpha threshold:", "float", 0.1),
            "animation_format": ("Animation format:", "combo", "GIF"),
            "frame_format": ("Frame format:", "combo", "PNG"),
            "frame_scale": ("Frame scale:", "float", 1.0),
        }

        row = 0
        for key, (label_text, field_type, default) in extraction_fields.items():
            label = QLabel(label_text)
            group_layout.addWidget(label, row, 0)

            if field_type == "combo":
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

        # Compression defaults group
        group = QGroupBox("Compression Default Settings")
        group_layout = QGridLayout(group)

        # Define compression fields
        compression_fields = {
            "gif_optimize": ("Optimize GIF:", "bool", True),
            "gif_loop": ("GIF loop count:", "int", 0),
            "webp_quality": ("WebP quality:", "int", 90),
            "webp_method": ("WebP method:", "int", 4),
            "png_compress_level": ("PNG compression:", "int", 6),
            "jpg_quality": ("JPEG quality:", "int", 95),
        }

        row = 0
        for key, (label_text, field_type, default) in compression_fields.items():
            label = QLabel(label_text)
            group_layout.addWidget(label, row, 0)

            if field_type == "bool":
                checkbox = QCheckBox()
                checkbox.setChecked(default)
                self.compression_fields[key] = checkbox
                group_layout.addWidget(checkbox, row, 1)
            elif field_type == "int":
                spinbox = QSpinBox()
                if "quality" in key:
                    spinbox.setRange(0, 100)
                elif "method" in key:
                    spinbox.setRange(0, 6)
                else:
                    spinbox.setRange(0, 9999)
                spinbox.setValue(default)
                self.compression_fields[key] = spinbox
                group_layout.addWidget(spinbox, row, 1)

            row += 1

        layout.addWidget(group)
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

        note_label = QLabel(
            "Note: Auto-update will download and install updates automatically when available."
        )
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

        # Compression defaults
        compression_defaults = self.app_config.get("compression_defaults", {})
        for key, control in self.compression_fields.items():
            value = compression_defaults.get(key)
            if value is not None:
                if isinstance(control, QCheckBox):
                    control.setChecked(bool(value))
                elif isinstance(control, QSpinBox):
                    control.setValue(int(value))

        # Update settings
        update_settings = self.app_config.get("update_settings", {})
        self.check_updates_cb.setChecked(update_settings.get("check_on_startup", True))
        self.auto_update_cb.setChecked(update_settings.get("auto_download", False))

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
            defaults = {
                "fps": 24,
                "delay": 250,
                "period": 0,
                "scale": 1.0,
                "threshold": 0.1,
                "animation_format": "GIF",
                "frame_format": "PNG",
                "frame_scale": 1.0,
            }

            for key, default_value in defaults.items():
                if key in self.extraction_fields:
                    control = self.extraction_fields[key]
                    if isinstance(control, QComboBox):
                        control.setCurrentText(str(default_value))
                    elif isinstance(control, QSpinBox):
                        control.setValue(int(default_value))
                    elif isinstance(control, QLineEdit):
                        control.setText(str(default_value))

            # Reset compression defaults
            comp_defaults = {
                "gif_optimize": True,
                "gif_loop": 0,
                "webp_quality": 90,
                "webp_method": 4,
                "png_compress_level": 6,
                "jpg_quality": 95,
            }

            for key, default_value in comp_defaults.items():
                if key in self.compression_fields:
                    control = self.compression_fields[key]
                    if isinstance(control, QCheckBox):
                        control.setChecked(bool(default_value))
                    elif isinstance(control, QSpinBox):
                        control.setValue(int(default_value))

            # Reset update settings
            self.check_updates_cb.setChecked(True)
            self.auto_update_cb.setChecked(False)

    def save_config(self):
        """Save the configuration settings."""
        try:
            # Validate and save resource limits
            resource_limits = {}

            cpu_threads = self.cpu_threads_edit.value()
            if cpu_threads > self.max_threads:
                raise ValueError(f"CPU threads cannot exceed {self.max_threads}")
            resource_limits["cpu_cores"] = cpu_threads

            memory_limit = self.memory_limit_edit.value()
            if memory_limit > self.max_memory_mb:
                raise ValueError(f"Memory limit cannot exceed {self.max_memory_mb} MB")
            resource_limits["memory_limit_mb"] = memory_limit

            # Save extraction defaults
            extraction_defaults = {}
            for key, control in self.extraction_fields.items():
                if isinstance(control, QComboBox):
                    extraction_defaults[key] = control.currentText()
                elif isinstance(control, QSpinBox):
                    extraction_defaults[key] = control.value()
                elif isinstance(control, QLineEdit):
                    try:
                        if key in ["scale", "threshold", "frame_scale"]:
                            extraction_defaults[key] = float(control.text())
                        else:
                            extraction_defaults[key] = int(control.text())
                    except ValueError:
                        raise ValueError(f"Invalid value for {key}: {control.text()}")

            # Save compression defaults
            compression_defaults = {}
            for key, control in self.compression_fields.items():
                if isinstance(control, QCheckBox):
                    compression_defaults[key] = control.isChecked()
                elif isinstance(control, QSpinBox):
                    compression_defaults[key] = control.value()

            # Save update settings
            update_settings = {
                "check_on_startup": self.check_updates_cb.isChecked(),
                "auto_download": self.auto_update_cb.isChecked(),
            }

            # Update app config
            self.app_config.config["resource_limits"] = resource_limits
            self.app_config.config["extraction_defaults"] = extraction_defaults
            self.app_config.config["compression_defaults"] = compression_defaults
            self.app_config.config["update_settings"] = update_settings

            # Save to file
            self.app_config.save()

            QMessageBox.information(
                self, "Settings Saved", "Configuration has been saved successfully."
            )
            self.accept()

        except ValueError as e:
            QMessageBox.critical(self, "Invalid Input", f"Error: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {str(e)}")

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
