#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Optimal atlas size calculator using binary search.

This module provides utilities for finding the minimum atlas size that can
fit all frames using a given packing algorithm. It uses binary search to
efficiently find the optimal dimensions, avoiding wasted space.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable, Optional

from .maxrects_packer import MaxRectsPacker, MaxRectsHeuristic
from .guillotine_packer import GuillotinePacker, GuillotinePlacement
from .shelf_packer import ShelfPackerDecreasingHeight, ShelfHeuristic
from .skyline_packer import SkylinePacker, SkylineHeuristic


@dataclass
class SizeResult:
    """Result of atlas size calculation."""

    width: int
    height: int
    occupancy: float  # Ratio of used to total area (0-1)
    algorithm_used: str


def next_power_of_2(n: int) -> int:
    """Return the next power of 2 >= n."""
    if n <= 0:
        return 1
    return 1 << (n - 1).bit_length()


def calculate_bounds(
    frames: list[tuple[int, int]], padding: int = 0
) -> tuple[int, int, int, int]:
    """
    Calculate theoretical bounds for atlas size.

    Args:
        frames: List of (width, height) tuples
        padding: Padding around each frame

    Returns:
        (min_dimension, max_dimension, total_area, max_frame_dimension)
    """
    if not frames:
        return (1, 1, 1, 1)

    total_area = 0
    max_dim = 0

    for w, h in frames:
        pw = w + padding * 2
        ph = h + padding * 2
        total_area += pw * ph
        max_dim = max(max_dim, pw, ph)

    # Minimum dimension is the largest frame dimension
    min_dim = max_dim

    # Maximum dimension: all frames in one row/column
    max_w = sum(w + padding * 2 for w, h in frames)
    max_h = sum(h + padding * 2 for w, h in frames)
    max_dimension = max(max_w, max_h)

    return (min_dim, max_dimension, total_area, max_dim)


def try_pack_maxrects(
    frames: list[tuple[int, int, Any]],
    width: int,
    height: int,
    padding: int = 0,
    allow_rotation: bool = False,
    heuristic: MaxRectsHeuristic = MaxRectsHeuristic.BSSF,
) -> bool:
    """
    Try to pack frames using MaxRects algorithm.

    Args:
        frames: List of (width, height, user_data) tuples
        width: Atlas width
        height: Atlas height
        padding: Padding around each frame
        allow_rotation: Allow 90-degree rotation
        heuristic: MaxRects placement heuristic

    Returns:
        True if all frames fit
    """
    blocks = [
        {"w": w + padding * 2, "h": h + padding * 2, "data": data}
        for w, h, data in frames
    ]

    packer = MaxRectsPacker(heuristic=heuristic)
    return packer.fit(blocks, width, height, allow_rotation=allow_rotation)


def try_pack_skyline(
    frames: list[tuple[int, int, Any]],
    width: int,
    height: int,
    padding: int = 0,
    allow_rotation: bool = False,
    heuristic: SkylineHeuristic = SkylineHeuristic.MIN_WASTE,
) -> bool:
    """Try to pack frames using Skyline algorithm."""
    packer = SkylinePacker(
        width,
        height,
        heuristic=heuristic,
        allow_rotation=allow_rotation,
        padding=padding,
    )

    pack_input = [(w, h, data) for w, h, data in frames]
    result = packer.pack(pack_input)
    return len(result) == len(frames)


def try_pack_guillotine(
    frames: list[tuple[int, int, Any]],
    width: int,
    height: int,
    padding: int = 0,
    allow_rotation: bool = False,
) -> bool:
    """Try to pack frames using Guillotine algorithm."""
    packer = GuillotinePacker(
        width,
        height,
        placement=GuillotinePlacement.BAF,
        allow_rotation=allow_rotation,
        padding=padding,
    )

    pack_input = [(w, h, data) for w, h, data in frames]
    result = packer.pack(pack_input)
    return len(result) == len(frames)


def try_pack_shelf(
    frames: list[tuple[int, int, Any]],
    width: int,
    height: int,
    padding: int = 0,
    allow_rotation: bool = False,
) -> bool:
    """Try to pack frames using Shelf algorithm."""
    packer = ShelfPackerDecreasingHeight(
        width,
        height,
        heuristic=ShelfHeuristic.BEST_HEIGHT_FIT,
        allow_rotation=allow_rotation,
        padding=padding,
    )

    pack_input = [(w, h, data) for w, h, data in frames]
    result = packer.pack(pack_input)
    return len(result) == len(frames)


def binary_search_dimension(
    frames: list[tuple[int, int, Any]],
    fixed_dim: int,
    search_dim_is_width: bool,
    min_val: int,
    max_val: int,
    try_pack_fn: Callable[[int, int], bool],
    power_of_2: bool = False,
) -> int:
    """
    Binary search for the minimum value of one dimension.

    Args:
        frames: Frame data
        fixed_dim: The fixed dimension value
        search_dim_is_width: If True, we're searching for width; else height
        min_val: Minimum search value
        max_val: Maximum search value
        try_pack_fn: Function that takes (width, height) and returns True if packing succeeds
        power_of_2: If True, only try power-of-2 values

    Returns:
        Minimum dimension value that works
    """
    if power_of_2:
        # Generate power-of-2 candidates
        candidates = []
        val = next_power_of_2(min_val)
        while val <= max_val:
            candidates.append(val)
            val *= 2

        # Linear search through power-of-2 values (they're sparse)
        for val in candidates:
            if search_dim_is_width:
                if try_pack_fn(val, fixed_dim):
                    return val
            else:
                if try_pack_fn(fixed_dim, val):
                    return val

        return max_val

    # Standard binary search
    lo, hi = min_val, max_val
    result = max_val

    while lo <= hi:
        mid = (lo + hi) // 2

        if search_dim_is_width:
            success = try_pack_fn(mid, fixed_dim)
        else:
            success = try_pack_fn(fixed_dim, mid)

        if success:
            result = mid
            hi = mid - 1
        else:
            lo = mid + 1

    return result


def find_optimal_size(
    frames: list[tuple[int, int, Any]],
    try_pack_fn: Callable[[int, int], bool],
    min_size: int = 1,
    max_size: int = 8192,
    padding: int = 0,
    power_of_2: bool = False,
    prefer_square: bool = True,
    fixed_width: Optional[int] = None,
    fixed_height: Optional[int] = None,
) -> SizeResult:
    """
    Find the optimal atlas size using binary search.

    This uses a two-phase approach:
    1. Find minimum square size that fits all frames
    2. Try to reduce one dimension while keeping the other

    Args:
        frames: List of (width, height, user_data) tuples
        try_pack_fn: Function that takes (width, height) and returns True if packing succeeds
        min_size: Minimum atlas dimension
        max_size: Maximum atlas dimension
        padding: Padding around each frame (already included in try_pack_fn)
        power_of_2: Constrain dimensions to powers of 2
        prefer_square: Try to keep dimensions close to square
        fixed_width: If set, use this exact width
        fixed_height: If set, use this exact height

    Returns:
        SizeResult with optimal dimensions and metrics
    """
    if not frames:
        dim = min_size if not power_of_2 else next_power_of_2(min_size)
        return SizeResult(width=dim, height=dim, occupancy=0.0, algorithm_used="none")

    # Calculate bounds
    frame_dims = [(w, h) for w, h, _ in frames]
    min_dim, max_dimension, total_area, max_frame_dim = calculate_bounds(
        frame_dims, padding
    )

    # Ensure minimum size can fit the largest frame
    min_dim = max(min_dim, min_size)

    # Handle fixed dimensions
    if fixed_width and fixed_height:
        w, h = fixed_width, fixed_height
        if power_of_2:
            w, h = next_power_of_2(w), next_power_of_2(h)
        return SizeResult(
            width=w,
            height=h,
            occupancy=total_area / (w * h) if w * h > 0 else 0,
            algorithm_used="fixed",
        )

    # Phase 1: Find minimum square size
    lo = min_dim
    hi = min(max_size, int(math.sqrt(total_area) * 2) + max_frame_dim)

    if power_of_2:
        lo = next_power_of_2(lo)
        hi = next_power_of_2(hi)

    best_square = hi

    # Binary search for square size
    while lo <= hi:
        if power_of_2:
            # For power-of-2, we can only try specific values
            mid = lo
            while mid < hi and mid * 2 <= (lo + hi) // 2:
                mid *= 2
        else:
            mid = (lo + hi) // 2

        if try_pack_fn(mid, mid):
            best_square = mid
            hi = mid - 1 if not power_of_2 else mid // 2
            if power_of_2 and hi < lo:
                break
        else:
            lo = mid + 1 if not power_of_2 else mid * 2

    # If a fixed dimension is specified, optimize the other
    if fixed_width:
        w = fixed_width
        if power_of_2:
            w = next_power_of_2(w)
        h = binary_search_dimension(
            frames, w, False, min_dim, max_size, try_pack_fn, power_of_2
        )
        return SizeResult(
            width=w,
            height=h,
            occupancy=total_area / (w * h) if w * h > 0 else 0,
            algorithm_used="fixed_width",
        )

    if fixed_height:
        h = fixed_height
        if power_of_2:
            h = next_power_of_2(h)
        w = binary_search_dimension(
            frames, h, True, min_dim, max_size, try_pack_fn, power_of_2
        )
        return SizeResult(
            width=w,
            height=h,
            occupancy=total_area / (w * h) if w * h > 0 else 0,
            algorithm_used="fixed_height",
        )

    # Phase 2: Try to reduce one dimension
    # Start with the best square and try making it narrower or shorter
    best_width = best_square
    best_height = best_square
    best_area = best_width * best_height

    # Try reducing width
    min_w = binary_search_dimension(
        frames, best_height, True, min_dim, best_width, try_pack_fn, power_of_2
    )
    if min_w * best_height < best_area:
        best_width = min_w
        best_area = min_w * best_height

    # Try reducing height with the new width
    min_h = binary_search_dimension(
        frames, best_width, False, min_dim, best_height, try_pack_fn, power_of_2
    )
    if best_width * min_h < best_area:
        best_height = min_h
        best_area = best_width * min_h

    # Try the opposite order: reduce height first, then width
    alt_height = binary_search_dimension(
        frames, best_square, False, min_dim, best_square, try_pack_fn, power_of_2
    )
    alt_width = binary_search_dimension(
        frames, alt_height, True, min_dim, best_square, try_pack_fn, power_of_2
    )

    if alt_width * alt_height < best_area:
        best_width = alt_width
        best_height = alt_height
        best_area = alt_width * alt_height

    occupancy = total_area / best_area if best_area > 0 else 0

    return SizeResult(
        width=best_width,
        height=best_height,
        occupancy=occupancy,
        algorithm_used="binary_search",
    )


def find_optimal_size_multi_algorithm(
    frames: list[tuple[int, int, Any]],
    min_size: int = 1,
    max_size: int = 8192,
    padding: int = 0,
    power_of_2: bool = False,
    allow_rotation: bool = False,
) -> tuple[SizeResult, str]:
    """
    Try multiple packing algorithms and return the best result.

    This function tries several algorithms and returns the one that
    produces the smallest atlas.

    Args:
        frames: List of (width, height, user_data) tuples
        min_size: Minimum atlas dimension
        max_size: Maximum atlas dimension
        padding: Padding around each frame
        power_of_2: Constrain dimensions to powers of 2
        allow_rotation: Allow 90-degree rotation

    Returns:
        Tuple of (SizeResult, algorithm_name)
    """
    algorithms = [
        (
            "MaxRects-BSSF",
            lambda w, h: try_pack_maxrects(
                frames, w, h, padding, allow_rotation, MaxRectsHeuristic.BSSF
            ),
        ),
        (
            "MaxRects-BAF",
            lambda w, h: try_pack_maxrects(
                frames, w, h, padding, allow_rotation, MaxRectsHeuristic.BAF
            ),
        ),
        (
            "Skyline-MinWaste",
            lambda w, h: try_pack_skyline(
                frames, w, h, padding, allow_rotation, SkylineHeuristic.MIN_WASTE
            ),
        ),
        (
            "Guillotine-BAF",
            lambda w, h: try_pack_guillotine(frames, w, h, padding, allow_rotation),
        ),
    ]

    best_result: Optional[SizeResult] = None
    best_algorithm = ""
    best_area = float("inf")

    for name, try_pack_fn in algorithms:
        try:
            result = find_optimal_size(
                frames,
                try_pack_fn,
                min_size=min_size,
                max_size=max_size,
                padding=padding,
                power_of_2=power_of_2,
            )

            area = result.width * result.height
            if area < best_area:
                best_area = area
                best_result = result
                best_algorithm = name

        except Exception:
            continue

    if best_result is None:
        # Fallback: return max size
        dim = max_size if not power_of_2 else next_power_of_2(max_size // 2)
        best_result = SizeResult(dim, dim, 0.0, "fallback")
        best_algorithm = "fallback"

    return best_result, best_algorithm
