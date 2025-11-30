#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Texture atlas packing algorithms.

This module contains various bin packing algorithms for organizing sprites
into texture atlases efficiently.

Available Packers:
- GrowingPacker: Basic growing bin packer, expands canvas as needed
- OrderedPacker: Row-based packer that preserves frame order
- MaxRectsPacker: Advanced algorithm with multiple heuristics (BSSF, BLSF, BAF, BL, CP)
- GuillotinePacker: Subdivides space with guillotine cuts
- ShelfPacker: Organizes frames into horizontal shelves
- SkylinePacker: Tracks top edge of placed rectangles
- HybridAdaptivePacker: Wrapper with analysis hooks

Size Optimization:
- find_optimal_size: Binary search for minimum atlas dimensions
- find_optimal_size_multi_algorithm: Try multiple packers, return best result
"""

from .growing_packer import GrowingPacker
from .ordered_packer import OrderedPacker
from .maxrects_packer import MaxRectsPacker, MaxRectsHeuristic
from .guillotine_packer import GuillotinePacker, GuillotinePlacement, GuillotineSplit
from .shelf_packer import ShelfPacker, ShelfPackerDecreasingHeight, ShelfHeuristic
from .skyline_packer import SkylinePacker, SkylineHeuristic
from .hybrid_adaptive_packer import HybridAdaptivePacker
from .size_optimizer import (
    SizeResult,
    find_optimal_size,
    find_optimal_size_multi_algorithm,
    next_power_of_2,
    calculate_bounds,
)

__all__ = [
    # Core packers
    "GrowingPacker",
    "OrderedPacker",
    "MaxRectsPacker",
    "GuillotinePacker",
    "ShelfPacker",
    "ShelfPackerDecreasingHeight",
    "SkylinePacker",
    "HybridAdaptivePacker",
    # Heuristic enums
    "MaxRectsHeuristic",
    "GuillotinePlacement",
    "GuillotineSplit",
    "ShelfHeuristic",
    "SkylineHeuristic",
    # Size optimization
    "SizeResult",
    "find_optimal_size",
    "find_optimal_size_multi_algorithm",
    "next_power_of_2",
    "calculate_bounds",
]
