#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Guillotine bin packing algorithm with multiple split heuristics.

The Guillotine algorithm subdivides the atlas into rectangular regions using
guillotine cuts (like cutting paper). When a frame is placed, the remaining
space is split either horizontally or vertically, creating new free rectangles.

Placement Heuristics:
    - BSSF (Best Short Side Fit): Minimize short side remainder
    - BLSF (Best Long Side Fit): Minimize long side remainder
    - BAF (Best Area Fit): Minimize area waste
    - WAF (Worst Area Fit): Maximize area waste (uniform distribution)

Split Heuristics:
    - SHORTER_LEFTOVER_AXIS: Split along shorter leftover side
    - LONGER_LEFTOVER_AXIS: Split along longer leftover side
    - SHORTER_AXIS: Split along shorter frame side
    - LONGER_AXIS: Split along longer frame side
    - MIN_AREA: Minimize area of smallest resulting rectangle
    - MAX_AREA: Maximize area of smallest resulting rectangle

Usage:
    from packers.guillotine_packer import GuillotinePacker
    from packers.packer_types import FrameInput, PackerOptions

    packer = GuillotinePacker()
    packer.set_heuristic("baf")  # Best Area Fit
    packer.set_split_heuristic("shorter_leftover")
    result = packer.pack([
        FrameInput("frame1", 100, 100),
        FrameInput("frame2", 50, 75),
    ])
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from packers.base_packer import BasePacker
from packers.packer_types import (
    FrameInput,
    GuillotinePlacement,
    GuillotineSplit,
    PackedFrame,
    PackerOptions,
    Rect,
)


class GuillotinePacker(BasePacker):
    """Guillotine bin packing algorithm.

    Maintains a list of free rectangles. When placing a frame, finds the best
    fit according to the placement heuristic, then splits the free rectangle
    using the split heuristic. Unlike MaxRects, each free rectangle is only
    split once (no overlap tracking needed).

    Attributes:
        options: Packer configuration options.
        free_rects: List of available free rectangles.
        placement_heuristic: How to choose where to place frames.
        split_heuristic: How to split remaining space after placement.
    """

    ALGORITHM_NAME = "guillotine"
    DISPLAY_NAME = "Guillotine Packer"
    SUPPORTED_HEURISTICS = [
        ("bssf", "Best Short Side Fit (BSSF)"),
        ("blsf", "Best Long Side Fit (BLSF)"),
        ("baf", "Best Area Fit (BAF)"),
        ("waf", "Worst Area Fit (WAF)"),
    ]

    def __init__(self, options: Optional[PackerOptions] = None) -> None:
        super().__init__(options)
        self.free_rects: List[Rect] = []
        self.placement_heuristic: GuillotinePlacement = GuillotinePlacement.BAF
        self.split_heuristic: GuillotineSplit = GuillotineSplit.SHORTER_LEFTOVER_AXIS
        self._bin_width: int = 0
        self._bin_height: int = 0

    def set_heuristic(self, heuristic_key: str) -> bool:
        """Set the placement heuristic.

        Args:
            heuristic_key: One of 'bssf', 'blsf', 'baf', 'waf'.

        Returns:
            True if heuristic was set, False if invalid key.
        """
        heuristic_map = {
            "bssf": GuillotinePlacement.BSSF,
            "blsf": GuillotinePlacement.BLSF,
            "baf": GuillotinePlacement.BAF,
            "waf": GuillotinePlacement.WAF,
        }
        if heuristic_key.lower() in heuristic_map:
            self.placement_heuristic = heuristic_map[heuristic_key.lower()]
            self._current_heuristic = heuristic_key.lower()
            return True
        return False

    def set_split_heuristic(self, split_key: str) -> bool:
        """Set the split heuristic.

        Args:
            split_key: One of 'shorter_leftover', 'longer_leftover',
                       'shorter_axis', 'longer_axis', 'min_area', 'max_area'.

        Returns:
            True if heuristic was set, False if invalid key.
        """
        split_map = {
            "shorter_leftover": GuillotineSplit.SHORTER_LEFTOVER_AXIS,
            "longer_leftover": GuillotineSplit.LONGER_LEFTOVER_AXIS,
            "shorter_axis": GuillotineSplit.SHORTER_AXIS,
            "longer_axis": GuillotineSplit.LONGER_AXIS,
            "min_area": GuillotineSplit.MIN_AREA,
            "max_area": GuillotineSplit.MAX_AREA,
        }
        if split_key.lower() in split_map:
            self.split_heuristic = split_map[split_key.lower()]
            return True
        return False

    def _pack_internal(
        self,
        frames: List[FrameInput],
        width: int,
        height: int,
    ) -> List[PackedFrame]:
        """Pack frames using the Guillotine algorithm."""
        self._init_bin(width, height)
        packed: List[PackedFrame] = []
        padding = self.options.padding

        for frame in frames:
            frame_w = frame.width + padding
            frame_h = frame.height + padding

            result = self._find_best_position(frame_w, frame_h)
            if result is None:
                return packed  # Cannot fit this frame

            rect_idx, best_x, best_y, placed_w, placed_h, rotated = result

            # Create packed frame
            packed_frame = PackedFrame(
                frame=frame,
                x=best_x,
                y=best_y,
                rotated=rotated,
            )
            packed.append(packed_frame)

            # Split the free rectangle
            self._split_free_rect(rect_idx, best_x, best_y, placed_w, placed_h)

        return packed

    def _init_bin(self, width: int, height: int) -> None:
        """Initialize the bin with the given dimensions."""
        self._bin_width = width
        self._bin_height = height
        self.free_rects = []

        border = self.options.border_padding
        self.free_rects.append(
            Rect(border, border, width - 2 * border, height - 2 * border)
        )

    def _find_best_position(
        self,
        width: int,
        height: int,
    ) -> Optional[Tuple[int, int, int, int, int, bool]]:
        """Find the best position for a rectangle.

        Returns:
            (rect_index, x, y, width, height, rotated) or None if no fit.
        """
        best_score = float("inf")
        best_result: Optional[Tuple[int, int, int, int, int, bool]] = None

        for i, rect in enumerate(self.free_rects):
            # Try without rotation
            if width <= rect.width and height <= rect.height:
                score = self._score_placement(width, height, rect)
                if score < best_score:
                    best_score = score
                    best_result = (i, rect.x, rect.y, width, height, False)

            # Try with rotation
            if self.options.allow_rotation:
                if height <= rect.width and width <= rect.height:
                    score = self._score_placement(height, width, rect)
                    if score < best_score:
                        best_score = score
                        best_result = (i, rect.x, rect.y, height, width, True)

        return best_result

    def _score_placement(self, width: int, height: int, rect: Rect) -> float:
        """Score a potential placement (lower is better)."""
        leftover_w = rect.width - width
        leftover_h = rect.height - height

        if self.placement_heuristic == GuillotinePlacement.BSSF:
            # Best Short Side Fit
            return float(min(leftover_w, leftover_h))

        elif self.placement_heuristic == GuillotinePlacement.BLSF:
            # Best Long Side Fit
            return float(max(leftover_w, leftover_h))

        elif self.placement_heuristic == GuillotinePlacement.BAF:
            # Best Area Fit - minimize leftover area
            return float(leftover_w * rect.height + leftover_h * width)

        elif self.placement_heuristic == GuillotinePlacement.WAF:
            # Worst Area Fit - maximize leftover area (negate)
            return -float(leftover_w * rect.height + leftover_h * width)

        return 0.0

    def _split_free_rect(
        self,
        rect_idx: int,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        """Split a free rectangle after placing a frame.

        The guillotine split creates two new rectangles from the leftover space.
        The split direction is determined by the split heuristic.
        """
        rect = self.free_rects[rect_idx]
        leftover_w = rect.width - width
        leftover_h = rect.height - height

        # Determine split direction
        split_horizontal = self._should_split_horizontal(
            width, height, leftover_w, leftover_h
        )

        # Create new free rectangles
        new_rects: List[Rect] = []

        if split_horizontal:
            # Horizontal split:
            # Right rect spans full height of original
            # Bottom rect only spans placed width
            if leftover_w > 0:
                new_rects.append(
                    Rect(x + width, rect.y, leftover_w, rect.height)
                )
            if leftover_h > 0:
                new_rects.append(
                    Rect(x, y + height, width, leftover_h)
                )
        else:
            # Vertical split:
            # Bottom rect spans full width of original
            # Right rect only spans placed height
            if leftover_h > 0:
                new_rects.append(
                    Rect(rect.x, y + height, rect.width, leftover_h)
                )
            if leftover_w > 0:
                new_rects.append(
                    Rect(x + width, y, leftover_w, height)
                )

        # Remove the used free rectangle and add new ones
        del self.free_rects[rect_idx]
        self.free_rects.extend(new_rects)

    def _should_split_horizontal(
        self,
        width: int,
        height: int,
        leftover_w: int,
        leftover_h: int,
    ) -> bool:
        """Determine if we should split horizontally or vertically."""
        heuristic = self.split_heuristic

        if heuristic == GuillotineSplit.SHORTER_LEFTOVER_AXIS:
            return leftover_w < leftover_h

        elif heuristic == GuillotineSplit.LONGER_LEFTOVER_AXIS:
            return leftover_w >= leftover_h

        elif heuristic == GuillotineSplit.SHORTER_AXIS:
            return width < height

        elif heuristic == GuillotineSplit.LONGER_AXIS:
            return width >= height

        elif heuristic == GuillotineSplit.MIN_AREA:
            # Choose split that minimizes the smallest resulting rectangle
            # Horizontal split
            h_area1 = leftover_w * (height + leftover_h) if leftover_w > 0 else 0
            h_area2 = width * leftover_h if leftover_h > 0 else 0
            h_min = min(h_area1, h_area2) if h_area1 > 0 and h_area2 > 0 else max(h_area1, h_area2)

            # Vertical split
            v_area1 = leftover_w * height if leftover_w > 0 else 0
            v_area2 = (width + leftover_w) * leftover_h if leftover_h > 0 else 0
            v_min = min(v_area1, v_area2) if v_area1 > 0 and v_area2 > 0 else max(v_area1, v_area2)

            return h_min < v_min

        elif heuristic == GuillotineSplit.MAX_AREA:
            # Choose split that maximizes the smallest resulting rectangle
            h_area1 = leftover_w * (height + leftover_h) if leftover_w > 0 else 0
            h_area2 = width * leftover_h if leftover_h > 0 else 0
            h_min = min(h_area1, h_area2) if h_area1 > 0 and h_area2 > 0 else max(h_area1, h_area2)

            v_area1 = leftover_w * height if leftover_w > 0 else 0
            v_area2 = (width + leftover_w) * leftover_h if leftover_h > 0 else 0
            v_min = min(v_area1, v_area2) if v_area1 > 0 and v_area2 > 0 else max(v_area1, v_area2)

            return h_min >= v_min

        return True  # Default to horizontal

    def merge_free_rects(self) -> None:
        """Attempt to merge adjacent free rectangles.

        This is O(n^2) but can improve packing efficiency by reducing
        fragmentation. Call this periodically during packing for best results.
        """
        i = 0
        while i < len(self.free_rects):
            j = i + 1
            merged = False
            while j < len(self.free_rects):
                r1 = self.free_rects[i]
                r2 = self.free_rects[j]

                # Check horizontal merge (same height, adjacent)
                if r1.y == r2.y and r1.height == r2.height:
                    if r1.right == r2.x:
                        self.free_rects[i] = Rect(
                            r1.x, r1.y, r1.width + r2.width, r1.height
                        )
                        del self.free_rects[j]
                        merged = True
                        continue
                    elif r2.right == r1.x:
                        self.free_rects[i] = Rect(
                            r2.x, r1.y, r1.width + r2.width, r1.height
                        )
                        del self.free_rects[j]
                        merged = True
                        continue

                # Check vertical merge (same width, adjacent)
                if r1.x == r2.x and r1.width == r2.width:
                    if r1.bottom == r2.y:
                        self.free_rects[i] = Rect(
                            r1.x, r1.y, r1.width, r1.height + r2.height
                        )
                        del self.free_rects[j]
                        merged = True
                        continue
                    elif r2.bottom == r1.y:
                        self.free_rects[i] = Rect(
                            r1.x, r2.y, r1.width, r1.height + r2.height
                        )
                        del self.free_rects[j]
                        merged = True
                        continue

                j += 1

            if not merged:
                i += 1


__all__ = ["GuillotinePacker"]
