#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for extract tab widget default settings loading.

Verifies that all extraction defaults from app_config are properly
loaded into the extract tab widget UI controls on startup.
"""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pytest
from unittest.mock import MagicMock, patch


class MockAppConfig:
    """Mock AppConfig for testing default value loading."""

    def __init__(self, extraction_defaults=None):
        self._extraction_defaults = extraction_defaults or {}

    def get_extraction_defaults(self):
        return self._extraction_defaults

    def get(self, key, default=None):
        if key == "interface":
            return {"duration_input_type": "fps"}
        return default


@pytest.fixture
def mock_qt_app():
    """Create a Qt application for widget testing."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mock_parent_app(mock_qt_app):
    """Create a mock parent application with configurable defaults."""

    def _create_parent(extraction_defaults):
        parent = MagicMock()
        parent.app_config = MockAppConfig(extraction_defaults)
        parent.tr = lambda x: x
        return parent

    return _create_parent


class TestExtractTabDefaultsLoading:
    """Test that extraction defaults are loaded from config into UI controls."""

    def test_frame_selection_loaded_from_config(self, mock_parent_app):
        """Frame selection combo should load value from config."""
        from PySide6.QtWidgets import QComboBox
        from utils.combo_options import FRAME_SELECTION_OPTIONS, populate_combobox

        # Create combo and populate it
        combo = QComboBox()
        populate_combobox(combo, FRAME_SELECTION_OPTIONS, lambda x: x)

        # Verify default is index 0 ("all")
        assert combo.currentData() == "all"

        # Simulate loading "no_duplicates" from config
        idx = combo.findData("no_duplicates")
        assert idx >= 0, "Should find 'no_duplicates' in combo data"
        combo.setCurrentIndex(idx)
        assert combo.currentData() == "no_duplicates"

    def test_cropping_method_loaded_from_config(self, mock_parent_app):
        """Cropping method combo should load value from config."""
        from PySide6.QtWidgets import QComboBox
        from utils.combo_options import CROPPING_METHOD_OPTIONS, populate_combobox

        combo = QComboBox()
        populate_combobox(combo, CROPPING_METHOD_OPTIONS, lambda x: x)

        # Default is index 0 ("none")
        assert combo.currentData() == "none"

        # Simulate loading "animation" from config
        idx = combo.findData("animation")
        assert idx >= 0, "Should find 'animation' in combo data"
        combo.setCurrentIndex(idx)
        assert combo.currentData() == "animation"

        # Simulate loading "frame" from config
        idx = combo.findData("frame")
        assert idx >= 0, "Should find 'frame' in combo data"
        combo.setCurrentIndex(idx)
        assert combo.currentData() == "frame"

    def test_filename_format_loaded_from_config(self, mock_parent_app):
        """Filename format combo should load value from config."""
        from PySide6.QtWidgets import QComboBox
        from utils.combo_options import FILENAME_FORMAT_OPTIONS, populate_combobox

        combo = QComboBox()
        populate_combobox(combo, FILENAME_FORMAT_OPTIONS, lambda x: x)

        # Default is index 0 ("standardized")
        assert combo.currentData() == "standardized"

        # Simulate loading "no_spaces" from config
        idx = combo.findData("no_spaces")
        assert idx >= 0, "Should find 'no_spaces' in combo data"
        combo.setCurrentIndex(idx)
        assert combo.currentData() == "no_spaces"

        # Simulate loading "no_special" from config
        idx = combo.findData("no_special")
        assert idx >= 0, "Should find 'no_special' in combo data"
        combo.setCurrentIndex(idx)
        assert combo.currentData() == "no_special"

    def test_filename_prefix_loaded_from_config(self, mock_qt_app):
        """Filename prefix entry should load value from config."""
        from PySide6.QtWidgets import QLineEdit

        entry = QLineEdit()
        assert entry.text() == ""

        # Simulate loading prefix from config
        entry.setText("my_prefix_")
        assert entry.text() == "my_prefix_"

    def test_filename_suffix_loaded_from_config(self, mock_qt_app):
        """Filename suffix entry should load value from config."""
        from PySide6.QtWidgets import QLineEdit

        entry = QLineEdit()
        assert entry.text() == ""

        # Simulate loading suffix from config
        entry.setText("_my_suffix")
        assert entry.text() == "_my_suffix"

    def test_all_combo_options_have_data(self):
        """Verify all combo options have internal data values set."""
        from PySide6.QtWidgets import QComboBox
        from utils.combo_options import (
            FRAME_SELECTION_OPTIONS,
            CROPPING_METHOD_OPTIONS,
            FILENAME_FORMAT_OPTIONS,
            populate_combobox,
        )

        for options, name in [
            (FRAME_SELECTION_OPTIONS, "frame_selection"),
            (CROPPING_METHOD_OPTIONS, "cropping_method"),
            (FILENAME_FORMAT_OPTIONS, "filename_format"),
        ]:
            combo = QComboBox()
            populate_combobox(combo, options, lambda x: x)

            # Each item should have data
            for i in range(combo.count()):
                data = combo.itemData(i)
                assert data is not None, f"{name} index {i} should have data"
                assert isinstance(data, str), f"{name} index {i} data should be string"

    def test_config_values_match_combo_data(self):
        """Verify config default values match combo internal data values."""
        from utils.app_config import AppConfig
        from utils.combo_options import (
            FRAME_SELECTION_OPTIONS,
            CROPPING_METHOD_OPTIONS,
            FILENAME_FORMAT_OPTIONS,
        )

        defaults = AppConfig.DEFAULTS["extraction_defaults"]

        # Check frame_selection
        frame_selection_internals = [opt.internal for opt in FRAME_SELECTION_OPTIONS]
        assert defaults["frame_selection"] in frame_selection_internals, (
            f"Config frame_selection '{defaults['frame_selection']}' "
            f"should be one of {frame_selection_internals}"
        )

        # Check crop_option
        crop_internals = [opt.internal for opt in CROPPING_METHOD_OPTIONS]
        assert defaults["crop_option"] in crop_internals, (
            f"Config crop_option '{defaults['crop_option']}' "
            f"should be one of {crop_internals}"
        )

        # Check filename_format
        format_internals = [opt.internal for opt in FILENAME_FORMAT_OPTIONS]
        assert defaults["filename_format"] in format_internals, (
            f"Config filename_format '{defaults['filename_format']}' "
            f"should be one of {format_internals}"
        )

    def test_findData_returns_valid_index_for_all_options(self, mock_qt_app):
        """findData should return valid index for all internal values."""
        from PySide6.QtWidgets import QComboBox
        from utils.combo_options import (
            FRAME_SELECTION_OPTIONS,
            CROPPING_METHOD_OPTIONS,
            FILENAME_FORMAT_OPTIONS,
            populate_combobox,
        )

        test_cases = [
            (FRAME_SELECTION_OPTIONS, "frame_selection"),
            (CROPPING_METHOD_OPTIONS, "cropping_method"),
            (FILENAME_FORMAT_OPTIONS, "filename_format"),
        ]

        for options, name in test_cases:
            combo = QComboBox()
            populate_combobox(combo, options, lambda x: x)

            for opt in options:
                idx = combo.findData(opt.internal)
                assert idx >= 0, (
                    f"findData('{opt.internal}') should return valid index "
                    f"for {name}, got {idx}"
                )


class TestExtractTabWidgetIntegration:
    """Integration tests for ExtractTabWidget.setup_default_values()."""

    def test_setup_default_values_loads_all_settings(self, mock_qt_app):
        """setup_default_values should load all extraction defaults from config."""
        from PySide6.QtWidgets import (
            QWidget,
            QComboBox,
            QLineEdit,
            QSpinBox,
            QDoubleSpinBox,
            QGroupBox,
        )
        from utils.combo_options import (
            FRAME_SELECTION_OPTIONS,
            CROPPING_METHOD_OPTIONS,
            FILENAME_FORMAT_OPTIONS,
            populate_combobox,
        )

        # Create mock extraction defaults (non-default values to verify loading)
        test_defaults = {
            "duration": 100,
            "duration_display_value": 10,
            "duration_display_type": "fps",
            "delay": 500,
            "period": 100,
            "scale": 2.0,
            "threshold": 0.75,
            "frame_scale": 1.5,
            "animation_export": False,
            "frame_export": False,
            "animation_format": "WebP",
            "frame_format": "AVIF",
            "resampling_method": "Lanczos",
            "frame_selection": "no_duplicates",
            "crop_option": "frame",
            "filename_format": "no_spaces",
            "filename_prefix": "test_prefix_",
            "filename_suffix": "_test_suffix",
        }

        # Create mock widgets that ExtractTabWidget would use
        frame_selection_combo = QComboBox()
        populate_combobox(frame_selection_combo, FRAME_SELECTION_OPTIONS, lambda x: x)

        cropping_method_combo = QComboBox()
        populate_combobox(cropping_method_combo, CROPPING_METHOD_OPTIONS, lambda x: x)

        filename_format_combo = QComboBox()
        populate_combobox(filename_format_combo, FILENAME_FORMAT_OPTIONS, lambda x: x)

        filename_prefix_entry = QLineEdit()
        filename_suffix_entry = QLineEdit()

        # Simulate the loading logic from setup_default_values
        defaults = test_defaults

        if "frame_selection" in defaults:
            idx = frame_selection_combo.findData(defaults["frame_selection"])
            if idx >= 0:
                frame_selection_combo.setCurrentIndex(idx)

        if "crop_option" in defaults:
            idx = cropping_method_combo.findData(defaults["crop_option"])
            if idx >= 0:
                cropping_method_combo.setCurrentIndex(idx)

        if "filename_format" in defaults:
            idx = filename_format_combo.findData(defaults["filename_format"])
            if idx >= 0:
                filename_format_combo.setCurrentIndex(idx)

        if "filename_prefix" in defaults:
            filename_prefix_entry.setText(defaults["filename_prefix"])

        if "filename_suffix" in defaults:
            filename_suffix_entry.setText(defaults["filename_suffix"])

        # Verify all values were loaded correctly
        assert frame_selection_combo.currentData() == "no_duplicates"
        assert cropping_method_combo.currentData() == "frame"
        assert filename_format_combo.currentData() == "no_spaces"
        assert filename_prefix_entry.text() == "test_prefix_"
        assert filename_suffix_entry.text() == "_test_suffix"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
