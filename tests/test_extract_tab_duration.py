#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication, QWidget

from gui.extract_tab_widget import ExtractTabWidget


class AppConfigStub:
    def __init__(self, interface: dict | None = None):
        self._interface = interface or {"duration_input_type": "fps"}

    def get_extraction_defaults(self) -> dict:
        return {}

    def get(self, key: str, default=None):
        if key == "interface":
            return self._interface
        return default


class ExtractTabAppStub(QWidget):
    def __init__(self, interface: dict):
        super().__init__()
        self.app_config = AppConfigStub(interface)
        self.settings_manager = SimpleNamespace(global_settings={})
        self.replace_rules: list[str] = []
        self.variable_delay = False
        self.fnf_idle_loop = False

    # Slots referenced during setup
    def start_process(self):
        pass

    def create_find_and_replace_window(self):
        pass

    def create_settings_window(self):
        pass

    def show_compression_settings(self):
        pass



@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.mark.parametrize(
    "duration_type, anim_format, spin_value, expected_ms",
    [
        ("fps", "GIF", 25, 40),
        ("deciseconds", "GIF", 5, 500),
        ("centiseconds", "GIF", 7, 70),
        ("milliseconds", "GIF", 120, 120),
        ("native", "GIF", 8, 80),
        ("native", "WebP", 150, 150),
    ],
)
def test_extract_tab_converts_duration_inputs(qt_app, duration_type, anim_format, spin_value, expected_ms):
    parent = ExtractTabAppStub({"duration_input_type": duration_type})
    widget = ExtractTabWidget(parent, use_existing_ui=False)

    widget.animation_format_combobox.setCurrentText(anim_format)
    widget.update_frame_rate_display()
    widget.frame_rate_entry.setValue(spin_value)

    settings = widget.get_extraction_settings()

    assert settings["duration"] == expected_ms

    widget.deleteLater()
    parent.deleteLater()
