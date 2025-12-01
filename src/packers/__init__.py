#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Unified packing algorithms for texture atlas generation.

This package provides multiple bin packing algorithms for combining individual
images into texture atlases. Each algorithm offers different trade-offs between
packing efficiency, speed, and flexibility.

Available Algorithms:
    - MaxRects: Best overall quality, supports 5 heuristics
    - Guillotine: Good balance of speed and quality, supports 4 placement
                  and 6 split heuristics
    - Skyline: Fast algorithm tracking the top edge of placed rectangles
    - Shelf: Simple row-based packing, fastest but may waste vertical space
    - ShelfFFDH: Shelf with height pre-sorting for better results

Quick Start:
    from packers import get_packer, pack, list_algorithms

    # Method 1: Use convenience function
    from packers.packer_types import FrameInput
    result = pack("maxrects", [
        FrameInput("sprite1", 100, 100),
        FrameInput("sprite2", 50, 75),
    ])

    # Method 2: Get packer instance for more control
    packer = get_packer("guillotine")
    packer.set_heuristic("bssf")
    result = packer.pack(frames)

    # List available algorithms
    for algo in list_algorithms():
        print(f"{algo['display_name']}: {algo['name']}")

Registry Pattern:
    The PackerRegistry class provides centralized access to all packers.
    Custom packers can be registered using the @register_packer decorator.

    from packers import register_packer, BasePacker

    @register_packer
    class MyPacker(BasePacker):
        ALGORITHM_NAME = "my-packer"
        DISPLAY_NAME = "My Custom Packer"
        ...
"""

from __future__ import annotations

# Core types - these are fundamental and have no dependencies
from packers.packer_types import (
    # Data classes
    Rect,
    RectBatch,
    FrameInput,
    PackedFrame,
    PackerOptions,
    PackerResult,
    # Heuristic enums
    MaxRectsHeuristic,
    GuillotinePlacement,
    GuillotineSplit,
    SkylineHeuristic,
    ShelfHeuristic,
    ExpandStrategy,
    # Exceptions
    PackerError,
    FrameTooLargeError,
    AtlasOverflowError,
    InvalidOptionsError,
)

# Base class
from packers.base_packer import BasePacker, SimplePacker

# Packer implementations
from packers.maxrects_packer import MaxRectsPacker
from packers.guillotine_packer import GuillotinePacker
from packers.skyline_packer import SkylinePacker
from packers.shelf_packer import ShelfPacker, ShelfPackerDecreasingHeight

# Registry and convenience functions
from packers.packer_registry import (
    PackerRegistry,
    register_packer,
    get_packer,
    pack,
    list_algorithms,
    get_heuristics_for_algorithm,
)


__all__ = [
    # Types
    "Rect",
    "RectBatch",
    "FrameInput",
    "PackedFrame",
    "PackerOptions",
    "PackerResult",
    # Heuristics
    "MaxRectsHeuristic",
    "GuillotinePlacement",
    "GuillotineSplit",
    "SkylineHeuristic",
    "ShelfHeuristic",
    "ExpandStrategy",
    # Exceptions
    "PackerError",
    "FrameTooLargeError",
    "AtlasOverflowError",
    "InvalidOptionsError",
    # Base class
    "BasePacker",
    "SimplePacker",
    # Packers
    "MaxRectsPacker",
    "GuillotinePacker",
    "SkylinePacker",
    "ShelfPacker",
    "ShelfPackerDecreasingHeight",
    # Registry
    "PackerRegistry",
    "register_packer",
    "get_packer",
    "pack",
    "list_algorithms",
    "get_heuristics_for_algorithm",
]

# Version of the packer package
__version__ = "1.0.0"
