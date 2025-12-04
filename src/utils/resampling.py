#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Resampling method utilities for image scaling operations.

This module provides a centralized definition of resampling methods
supported by both Pillow and Wand (ImageMagick), with automatic selection
of optimal filters based on scaling direction (upscale vs downscale).

Usage:
    from utils.resampling import get_pil_resampling_filter, get_wand_resampling_filter

    # Get the PIL filter for a method
    pil_filter = get_pil_resampling_filter("Bicubic", scale=0.5)
    scaled = image.resize((new_w, new_h), pil_filter)

    # Get the Wand filter for a method
    wand_filter = get_wand_resampling_filter("Lanczos")
    wand_image.resize(new_w, new_h, filter=wand_filter)
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Tuple

from PIL import Image


class ResamplingMethod(Enum):
    """Available resampling methods for image scaling.

    Each method has trade-offs between quality and performance:
    - NEAREST: Fastest, pixelated results, best for pixel art
    - BILINEAR: Fast, smooth but can be blurry
    - BICUBIC: Good balance of quality and speed
    - LANCZOS: Highest quality, slower, best for photos
    - BOX: Good for downscaling, averages pixels
    - HAMMING: Similar to bilinear with less blur
    """

    NEAREST = "Nearest"
    BILINEAR = "Bilinear"
    BICUBIC = "Bicubic"
    LANCZOS = "Lanczos"
    BOX = "Box"
    HAMMING = "Hamming"


RESAMPLING_DISPLAY_NAMES: List[str] = [
    "Nearest",
    "Bilinear",
    "Bicubic",
    "Lanczos",
    "Box",
    "Hamming",
]

DEFAULT_RESAMPLING_METHOD = "Nearest"

_PIL_RESAMPLING_MAP: Dict[str, int] = {
    "Nearest": Image.Resampling.NEAREST,
    "Bilinear": Image.Resampling.BILINEAR,
    "Bicubic": Image.Resampling.BICUBIC,
    "Lanczos": Image.Resampling.LANCZOS,
    "Box": Image.Resampling.BOX,
    "Hamming": Image.Resampling.HAMMING,
}

# Mapping from display names to Wand/ImageMagick filter names
# These are the filter names accepted by wand.image.Image.resize()
# See: https://docs.wand-py.org/en/latest/wand/image.html#wand.image.BaseImage.resize
_WAND_RESAMPLING_MAP: Dict[str, str] = {
    "Nearest": "point",  # Point/nearest-neighbor sampling
    "Bilinear": "triangle",  # Linear/bilinear interpolation
    "Bicubic": "catrom",  # Catmull-Rom cubic (standard bicubic)
    "Lanczos": "lanczos",  # Lanczos windowed sinc
    "Box": "box",  # Box/averaging filter
    "Hamming": "hamming",  # Hamming windowed filter
}


def get_resampling_index(method_name: str) -> int:
    """Get the combobox index for a resampling method name.

    Args:
        method_name: Display name of the resampling method.

    Returns:
        Index in RESAMPLING_DISPLAY_NAMES, or 0 (Nearest) if not found.
    """
    try:
        return RESAMPLING_DISPLAY_NAMES.index(method_name)
    except ValueError:
        return RESAMPLING_DISPLAY_NAMES.index(DEFAULT_RESAMPLING_METHOD)


def get_resampling_name(index: int) -> str:
    """Get the resampling method name for a combobox index.

    Args:
        index: Index in the resampling combobox.

    Returns:
        Display name of the resampling method.
    """
    if 0 <= index < len(RESAMPLING_DISPLAY_NAMES):
        return RESAMPLING_DISPLAY_NAMES[index]
    return DEFAULT_RESAMPLING_METHOD


def get_pil_resampling_filter(method_name: str, scale: float = 1.0) -> int:
    """Get the PIL resampling filter constant for a method.

    Args:
        method_name: Display name of the resampling method.
        scale: Scale factor (currently unused, kept for API compatibility).

    Returns:
        PIL Image.Resampling constant suitable for resize() operations.
    """
    _ = scale  # Unused, kept for API compatibility or future use
    return _PIL_RESAMPLING_MAP.get(method_name, Image.Resampling.NEAREST)


def get_wand_resampling_filter(method_name: str, scale: float = 1.0) -> str:
    """Get the Wand/ImageMagick filter name for a resampling method.

    Args:
        method_name: Display name of the resampling method.
        scale: Scale factor (currently unused, kept for API compatibility).

    Returns:
        Wand filter name string suitable for resize() operations.
        Common values: "point", "triangle", "catrom", "lanczos", "box", "hamming"
    """
    _ = scale  # Unused, kept for API compatibility or future use
    return _WAND_RESAMPLING_MAP.get(method_name, "point")


# This is currently not properly implemented in the GUI, but it's here for future use.
# I just need to finish writing some modifications to tooltips logic which is a low priority task.
def get_resampling_tooltip(method_name: str) -> str:
    """Get a descriptive tooltip for a resampling method.

    Args:
        method_name: Display name of the resampling method.

    Returns:
        Description of the method's characteristics.
    """
    tooltips = {
        "Nearest": (
            "A non-interpolating resampler that assigns each output pixel the value "
            "of the closest input pixel. Fast and simple but produces blocky, "
            "aliasing-prone results when upscaling.\n\n"
            "Best for: Pixel art, retro graphics, or when preserving hard edges."
        ),
        "Bilinear": (
            "Performs linear interpolation across the 2×2 neighborhood of surrounding "
            "pixels. Produces smoother results than Nearest but can introduce mild "
            "blurring and loses fine detail.\n\n"
            "Best for: Quick previews or when speed matters more than quality."
        ),
        "Bicubic": (
            "Uses cubic convolution over a 4×4 pixel neighborhood, modeling intensity "
            "changes with cubic polynomials. Offers smoother gradients and better edge "
            "preservation than Bilinear, with less ringing than higher-order filters.\n\n"
            "Best for: General-purpose scaling with good quality/speed balance."
        ),
        "Lanczos": (
            "A high-quality sinc-based filter using a finite window (commonly 2-3 lobes). "
            "Provides sharp, detailed results with good frequency preservation but can "
            "introduce ringing artifacts near edges.\n\n"
            "Best for: High-resolution artwork, photos, or when maximum detail matters."
        ),
        "Box": (
            "A simple averaging filter: each output pixel is the mean of all input pixels "
            "it covers. Good for downsampling when speed matters, but produces soft images "
            "when upscaling.\n\n"
            "Best for: Fast downscaling, thumbnail generation, or mipmap creation."
        ),
        "Hamming": (
            "A windowed sinc filter using the Hamming window to reduce spectral leakage. "
            "Offers a balance between sharpness and artifact suppression, typically "
            "producing smoother results with less ringing than Lanczos.\n\n"
            "Best for: When you want Lanczos-like quality with fewer edge artifacts."
        ),
    }
    return tooltips.get(method_name, "")


def get_all_methods_with_tooltips() -> List[Tuple[str, str]]:
    """Get all resampling methods with their tooltips.

    Returns:
        List of (display_name, tooltip) tuples in display order.
    """
    return [(name, get_resampling_tooltip(name)) for name in RESAMPLING_DISPLAY_NAMES]
