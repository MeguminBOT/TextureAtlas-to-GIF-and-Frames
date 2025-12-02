#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Skyline bin packing algorithm with multiple placement heuristics.

The Skyline algorithm maintains a "skyline" representing the top edge of
placed rectangles. Each segment has a position (x) and height (y). New
rectangles are placed by finding the best position along the skyline.

This is one of the most efficient packing algorithms, offering near-optimal
results with O(n^2) complexity in the worst case.

Heuristics:
    - BOTTOM_LEFT: Place at lowest Y position, tie-break by leftmost X
    - MIN_WASTE: Place where least space is wasted below the rectangle
    - BEST_FIT: Find position where rectangle fits best with skyline contour

Usage:
    from packers.skyline_packer import SkylinePacker
    from packers.packer_types import FrameInput, PackerOptions

    packer = SkylinePacker()
    packer.set_heuristic("min_waste")
    result = packer.pack([
        FrameInput("frame1", 100, 100),
        FrameInput("frame2", 50, 75),
    ])
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from packers.base_packer import BasePacker
from packers.packer_types import (
    FrameInput,
    PackedFrame,
    PackerOptions,
    SkylineHeuristic,
)


@dataclass
class SkylineNode:
    """A segment of the skyline.

    Attributes:
        x: Starting X position of this segment.
        y: Height (Y position of the top edge).
        width: Width of this segment.
    """

    x: int
    y: int
    width: int


class SkylinePacker(BasePacker):
    """Skyline bin packing algorithm.

    The skyline is a horizontal line representing the top edge of all placed
    rectangles. When a rectangle is placed, it updates the skyline by raising
    the appropriate segments.

    Attributes:
        options: Packer configuration options.
        skyline: List of skyline segments.
        heuristic: Placement heuristic to use.
    """

    ALGORITHM_NAME = "skyline"
    DISPLAY_NAME = "Skyline Packer"
    SUPPORTED_HEURISTICS = [
        ("bottom_left", "Bottom-Left (BL)"),
        ("min_waste", "Minimum Waste"),
        ("best_fit", "Best Fit"),
    ]

    def __init__(self, options: Optional[PackerOptions] = None) -> None:
        super().__init__(options)
        self.skyline: List[SkylineNode] = []
        self.heuristic: SkylineHeuristic = SkylineHeuristic.MIN_WASTE
        self._bin_width: int = 0
        self._bin_height: int = 0
        self._placed: List[Tuple[int, int, int, int]] = []  # (x, y, w, h)

    def set_heuristic(self, heuristic_key: str) -> bool:
        """Set the placement heuristic.

        Args:
            heuristic_key: One of 'bottom_left', 'min_waste', 'best_fit'.

        Returns:
            True if heuristic was set, False if invalid key.
        """
        heuristic_map = {
            "bottom_left": SkylineHeuristic.BOTTOM_LEFT,
            "min_waste": SkylineHeuristic.MIN_WASTE,
            "best_fit": SkylineHeuristic.BEST_FIT,
        }
        if heuristic_key.lower() in heuristic_map:
            self.heuristic = heuristic_map[heuristic_key.lower()]
            self._current_heuristic = heuristic_key.lower()
            return True
        return False

    def _pack_internal(
        self,
        frames: List[FrameInput],
        width: int,
        height: int,
    ) -> List[PackedFrame]:
        """Pack frames using the Skyline algorithm."""
        self._init_bin(width, height)
        packed: List[PackedFrame] = []
        padding = self.options.padding

        for frame in frames:
            frame_w = frame.width + padding
            frame_h = frame.height + padding

            result = self._find_best_position(frame_w, frame_h)
            if result is None:
                return packed  # Cannot fit this frame

            best_x, best_y, placed_w, placed_h, rotated = result

            # Check vertical fit
            if best_y + placed_h > self._bin_height - self.options.border_padding:
                return packed  # Cannot fit

            # Create packed frame
            packed_frame = PackedFrame(
                frame=frame,
                x=best_x,
                y=best_y,
                rotated=rotated,
            )
            packed.append(packed_frame)

            # Update skyline
            self._add_skyline_level(best_x, best_y, placed_w, placed_h)
            self._placed.append((best_x, best_y, placed_w, placed_h))

        return packed

    def _init_bin(self, width: int, height: int) -> None:
        """Initialize the bin with the given dimensions."""
        self._bin_width = width
        self._bin_height = height
        self._placed = []

        border = self.options.border_padding
        # Start with a single skyline segment at y=0 (top of usable area)
        self.skyline = [SkylineNode(x=border, y=border, width=width - 2 * border)]

    def _find_best_position(
        self,
        width: int,
        height: int,
    ) -> Optional[Tuple[int, int, int, int, bool]]:
        """Find the best position for a rectangle.

        Returns:
            (x, y, width, height, rotated) or None if no fit found.
        """
        best_x = -1
        best_y = -1
        best_width = width
        best_height = height
        best_rotated = False
        best_score = float("inf")

        # Try without rotation
        result = self._find_position_for_size(width, height)
        if result is not None:
            idx, x, y, score = result
            if score < best_score:
                best_score = score
                best_x = x
                best_y = y
                best_width = width
                best_height = height
                best_rotated = False

        # Try with rotation
        if self.options.allow_rotation and width != height:
            result = self._find_position_for_size(height, width)
            if result is not None:
                idx, x, y, score = result
                # Small penalty for rotation
                score += 0.5
                if score < best_score:
                    best_score = score
                    best_x = x
                    best_y = y
                    best_width = height
                    best_height = width
                    best_rotated = True

        if best_x == -1:
            return None

        return (best_x, best_y, best_width, best_height, best_rotated)

    def _find_position_for_size(
        self,
        width: int,
        height: int,
    ) -> Optional[Tuple[int, int, int, float]]:
        """Find best position for a rectangle of given size.

        Returns:
            (skyline_index, x, y, score) or None if no fit.
        """
        best_idx = -1
        best_x = -1
        best_y = -1
        best_score = float("inf")
        border = self.options.border_padding

        for i in range(len(self.skyline)):
            result = self._fit_at_skyline_index(i, width, height)
            if result is None:
                continue

            x, y, waste = result

            # Check bounds
            if y + height > self._bin_height - border:
                continue

            # Calculate score based on heuristic
            if self.heuristic == SkylineHeuristic.BOTTOM_LEFT:
                score = float(y * self._bin_width + x)
            elif self.heuristic == SkylineHeuristic.MIN_WASTE:
                score = float(waste)
            elif self.heuristic == SkylineHeuristic.BEST_FIT:
                # Prefer positions where width matches skyline segment
                fit_score = abs(width - self.skyline[i].width)
                score = float(y * 1000 + fit_score)
            else:
                score = float(y * self._bin_width + x)

            if score < best_score:
                best_score = score
                best_x = x
                best_y = y
                best_idx = i

        if best_idx == -1:
            return None

        return (best_idx, best_x, best_y, best_score)

    def _fit_at_skyline_index(
        self,
        idx: int,
        width: int,
        height: int,
    ) -> Optional[Tuple[int, int, int]]:
        """Try to fit a rectangle starting at skyline index.

        Returns:
            (x, y, waste) if it fits, None otherwise.
        """
        x = self.skyline[idx].x
        border = self.options.border_padding

        # Check horizontal bounds
        if x + width > self._bin_width - border:
            return None

        # Find maximum Y across skyline segments the rectangle spans
        width_left = width
        i = idx
        y = 0
        waste = 0

        while width_left > 0 and i < len(self.skyline):
            node = self.skyline[i]

            # Track highest point
            if node.y > y:
                # Calculate waste: area between old y and new y
                waste += (node.y - y) * (width - width_left)
                y = node.y
            else:
                # Calculate waste below this segment
                waste += (y - node.y) * min(width_left, node.width)

            if node.x + node.width >= x + width:
                # This segment extends beyond our rectangle
                width_left = 0
            else:
                width_left -= node.width - max(0, x - node.x)

            i += 1

        # Check if we ran out of skyline segments
        if width_left > 0:
            return None

        return (x, y, waste)

    def _add_skyline_level(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        """Add a new skyline level after placing a rectangle.

        Updates the skyline to reflect the new top edge.
        """
        # Create new skyline node for the placed rectangle
        new_node = SkylineNode(x=x, y=y + height, width=width)

        # Build new skyline
        new_skyline: List[SkylineNode] = []
        i = 0

        # Copy nodes before the new rectangle
        while i < len(self.skyline) and self.skyline[i].x + self.skyline[i].width <= x:
            new_skyline.append(self.skyline[i])
            i += 1

        # Handle partial overlap on the left
        if i < len(self.skyline) and self.skyline[i].x < x:
            node = self.skyline[i]
            trimmed = SkylineNode(x=node.x, y=node.y, width=x - node.x)
            new_skyline.append(trimmed)

        # Add the new node
        new_skyline.append(new_node)

        # Skip nodes that are covered by the new rectangle
        while (
            i < len(self.skyline)
            and self.skyline[i].x + self.skyline[i].width <= x + width
        ):
            i += 1

        # Handle partial overlap on the right
        if i < len(self.skyline) and self.skyline[i].x < x + width:
            node = self.skyline[i]
            overlap = x + width - node.x
            adjusted = SkylineNode(x=x + width, y=node.y, width=node.width - overlap)
            if adjusted.width > 0:
                new_skyline.append(adjusted)
            i += 1

        # Copy remaining nodes
        while i < len(self.skyline):
            new_skyline.append(self.skyline[i])
            i += 1

        self.skyline = new_skyline
        self._merge_skyline()

    def _merge_skyline(self) -> None:
        """Merge adjacent skyline nodes with the same height."""
        if len(self.skyline) <= 1:
            return

        merged: List[SkylineNode] = [self.skyline[0]]

        for i in range(1, len(self.skyline)):
            node = self.skyline[i]
            last = merged[-1]

            if last.y == node.y:
                # Merge nodes with same height
                merged[-1] = SkylineNode(
                    x=last.x,
                    y=last.y,
                    width=last.width + node.width,
                )
            else:
                merged.append(node)

        self.skyline = merged

    def get_skyline_height(self) -> int:
        """Get the maximum height of the current skyline."""
        if not self.skyline:
            return 0
        return max(node.y for node in self.skyline)


__all__ = ["SkylinePacker", "SkylineNode"]
