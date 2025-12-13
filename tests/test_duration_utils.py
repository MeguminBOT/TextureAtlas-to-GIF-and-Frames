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
    milliseconds_to_duration,
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
