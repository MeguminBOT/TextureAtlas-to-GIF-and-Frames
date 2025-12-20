#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from utils.duration_utils import (  # noqa: E402
    DURATION_CENTISECONDS,
    DURATION_DECISECONDS,
    DURATION_FPS,
    DURATION_MILLISECONDS,
    DURATION_NATIVE,
    convert_duration,
    duration_to_milliseconds,
    get_duration_display_meta,
    load_duration_display_value,
    milliseconds_to_duration,
    store_duration,
)


def test_duration_to_milliseconds_handles_all_units() -> None:
    assert duration_to_milliseconds(24, DURATION_FPS, "GIF") == 42
    assert duration_to_milliseconds(5, DURATION_DECISECONDS, "GIF") == 500
    assert duration_to_milliseconds(12, DURATION_CENTISECONDS, "GIF") == 120
    assert duration_to_milliseconds(123, DURATION_MILLISECONDS, "GIF") == 123
    assert duration_to_milliseconds(0, DURATION_MILLISECONDS, "GIF") == 1
    assert duration_to_milliseconds(4, DURATION_NATIVE, "GIF") == 40
    assert duration_to_milliseconds(120, DURATION_NATIVE, "WebP") == 120


def test_milliseconds_to_duration_handles_all_units() -> None:
    assert milliseconds_to_duration(42, DURATION_FPS, "GIF") == 24
    assert milliseconds_to_duration(500, DURATION_DECISECONDS, "GIF") == 5
    assert milliseconds_to_duration(120, DURATION_CENTISECONDS, "GIF") == 12
    assert milliseconds_to_duration(1, DURATION_MILLISECONDS, "GIF") == 1
    assert milliseconds_to_duration(50, DURATION_NATIVE, "GIF") == 5
    assert milliseconds_to_duration(75, DURATION_NATIVE, "WebP") == 75


def test_convert_duration_round_trip_preserves_values() -> None:
    samples = {
        DURATION_FPS: 24,
        DURATION_DECISECONDS: 7,
        DURATION_CENTISECONDS: 12,
        DURATION_MILLISECONDS: 150,
        DURATION_NATIVE: 5,
    }
    for duration_type, value in samples.items():
        ms_value = convert_duration(value, duration_type, DURATION_MILLISECONDS, "GIF")
        round_trip = convert_duration(ms_value, DURATION_MILLISECONDS, duration_type, "GIF")
        assert round_trip == value


def test_duration_display_meta_resolves_native_units() -> None:
    gif_meta = get_duration_display_meta(DURATION_NATIVE, "GIF")
    assert gif_meta.resolved_type == DURATION_CENTISECONDS
    assert gif_meta.label == "Frame delay (cs)"
    assert gif_meta.suffix == " cs"
    assert gif_meta.min_value == 1
    assert gif_meta.max_value == 10000

    webp_meta = get_duration_display_meta(DURATION_NATIVE, "WebP")
    assert webp_meta.resolved_type == DURATION_MILLISECONDS
    assert webp_meta.label == "Frame delay (ms)"
    assert webp_meta.suffix == " ms"
    assert webp_meta.min_value == 1
    assert webp_meta.max_value == 100000

    fps_meta = get_duration_display_meta(DURATION_FPS, "GIF")
    assert fps_meta.resolved_type == DURATION_FPS
    assert fps_meta.label == "Frame rate"
    assert fps_meta.suffix == " fps"
    assert fps_meta.min_value == 1
    assert fps_meta.max_value == 1000

def test_store_duration_preserves_display_value() -> None:
    """Test that store_duration captures both ms and display value."""
    stored = store_duration(60, DURATION_FPS, "GIF")
    assert stored.duration_ms == 17  # round(1000/60)
    assert stored.display_value == 60
    assert stored.display_type == DURATION_FPS

    stored_cs = store_duration(10, DURATION_CENTISECONDS, "GIF")
    assert stored_cs.duration_ms == 100
    assert stored_cs.display_value == 10
    assert stored_cs.display_type == DURATION_CENTISECONDS


def test_load_duration_display_value_uses_stored_when_types_match() -> None:
    """Test that load_duration_display_value returns stored value when types match."""
    # 60 FPS -> 17ms -> would be 59 FPS without stored value
    # With stored value, should return exact 60
    result = load_duration_display_value(
        duration_ms=17,
        stored_display_value=60,
        stored_display_type=DURATION_FPS,
        target_display_type=DURATION_FPS,
        animation_format="GIF",
    )
    assert result == 60  # Exact stored value, not round(1000/17)=59


def test_load_duration_display_value_converts_when_types_differ() -> None:
    """Test that load_duration_display_value converts when types differ."""
    # Stored as FPS but requesting milliseconds - should convert from ms
    result = load_duration_display_value(
        duration_ms=17,
        stored_display_value=60,
        stored_display_type=DURATION_FPS,
        target_display_type=DURATION_MILLISECONDS,
        animation_format="GIF",
    )
    assert result == 17  # Converted from ms, not stored FPS value


def test_load_duration_display_value_falls_back_without_stored() -> None:
    """Test that load_duration_display_value falls back to ms conversion."""
    # No stored value - should convert from ms
    result = load_duration_display_value(
        duration_ms=17,
        stored_display_value=None,
        stored_display_type=None,
        target_display_type=DURATION_FPS,
        animation_format="GIF",
    )
    assert result == 59  # round(1000/17) without stored value


def test_high_fps_values_preserve_precision() -> None:
    """Test that high FPS values like 60 and 120 preserve precision."""
    # These are the problematic values reported in the bug
    problematic_fps = [60, 120]

    for fps in problematic_fps:
        stored = store_duration(fps, DURATION_FPS, "GIF")
        restored = load_duration_display_value(
            duration_ms=stored.duration_ms,
            stored_display_value=stored.display_value,
            stored_display_type=stored.display_type,
            target_display_type=DURATION_FPS,
            animation_format="GIF",
        )
        assert restored == fps, f"FPS {fps} was not preserved (got {restored})"