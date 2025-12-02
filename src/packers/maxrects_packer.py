#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""MaxRects bin packing algorithm with multiple placement heuristics.

MaxRects is one of the most efficient 2D bin packing algorithms. It maintains
a list of maximal free rectangles and uses various heuristics to choose
optimal placements. When a frame is placed, overlapping free rectangles are
split, and fully contained rectangles are pruned.

Supports multiple heuristics:
    - BSSF (Best Short Side Fit): Minimize short side remainder - good balance
    - BLSF (Best Long Side Fit): Minimize long side remainder
    - BAF (Best Area Fit): Minimize total wasted area
    - BL (Bottom-Left): Place as low and left as possible
    - CP (Contact Point): Maximize contact with edges - reduces gaps

Based on the MAXRECTS algorithm by Jukka Jylänki.
Uses NumPy for efficient rectangle intersection tests.

Usage:
    from packers.maxrects_packer import MaxRectsPacker
    from packers.packer_types import FrameInput, PackerOptions

    packer = MaxRectsPacker()
    packer.set_heuristic("bssf")  # Best Short Side Fit
    result = packer.pack([
        FrameInput("frame1", 100, 100),
        FrameInput("frame2", 50, 75),
    ])
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np

from packers.base_packer import BasePacker
from packers.packer_types import (
    FrameInput,
    MaxRectsHeuristic,
    PackedFrame,
    PackerOptions,
    Rect,
)


class MaxRectsPacker(BasePacker):
    """MaxRects bin packing implementation.

    The algorithm maintains a list of maximal free rectangles. When a frame
    is placed, any free rectangle that overlaps is split into up to 4 new
    rectangles. Redundant rectangles (fully contained in others) are pruned.

    Attributes:
        options: Packer configuration options.
        free_rects: List of free rectangles in the atlas.
        used_rects: List of placed rectangles.
        heuristic: Current placement heuristic.
    """

    ALGORITHM_NAME = "maxrects"
    DISPLAY_NAME = "MaxRects Packer"
    SUPPORTED_HEURISTICS = [
        ("bssf", "Best Short Side Fit (BSSF)"),
        ("blsf", "Best Long Side Fit (BLSF)"),
        ("baf", "Best Area Fit (BAF)"),
        ("bl", "Bottom-Left (BL)"),
        ("cp", "Contact Point (CP)"),
    ]

    def __init__(self, options: Optional[PackerOptions] = None) -> None:
        super().__init__(options)
        self.free_rects: List[Rect] = []
        self.used_rects: List[Rect] = []
        self.heuristic: MaxRectsHeuristic = MaxRectsHeuristic.BSSF
        self._bin_width: int = 0
        self._bin_height: int = 0

    def set_heuristic(self, heuristic_key: str) -> bool:
        """Set the placement heuristic.

        Args:
            heuristic_key: One of 'bssf', 'blsf', 'baf', 'bl', 'cp'.

        Returns:
            True if heuristic was set, False if invalid key.
        """
        heuristic_map = {
            "bssf": MaxRectsHeuristic.BSSF,
            "blsf": MaxRectsHeuristic.BLSF,
            "baf": MaxRectsHeuristic.BAF,
            "bl": MaxRectsHeuristic.BL,
            "cp": MaxRectsHeuristic.CP,
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
        """Pack frames using the MaxRects algorithm."""
        self._init_bin(width, height)
        packed: List[PackedFrame] = []
        padding = self.options.padding

        for frame in frames:
            frame_w = frame.width + padding
            frame_h = frame.height + padding

            result = self._find_best_position(frame_w, frame_h)
            if result is None:
                return packed  # Cannot fit this frame

            best_x, best_y, best_w, best_h, rotated = result

            # Create packed frame
            packed_frame = PackedFrame(
                frame=frame,
                x=best_x,
                y=best_y,
                rotated=rotated,
            )
            packed.append(packed_frame)

            # Update free rectangles
            placed_rect = Rect(best_x, best_y, best_w, best_h)
            self._place_rect(placed_rect)

        return packed

    def _init_bin(self, width: int, height: int) -> None:
        """Initialize the bin with the given dimensions."""
        self._bin_width = width
        self._bin_height = height
        self.free_rects = []
        self.used_rects = []

        border = self.options.border_padding
        self.free_rects.append(
            Rect(border, border, width - 2 * border, height - 2 * border)
        )

    def _find_best_position(
        self,
        width: int,
        height: int,
    ) -> Optional[Tuple[int, int, int, int, bool]]:
        """Find the best position for a rectangle of the given size.

        Args:
            width: Rectangle width (including padding).
            height: Rectangle height (including padding).

        Returns:
            (x, y, width, height, rotated) or None if no position found.
        """
        best_score = (float("inf"), float("inf"))
        best_result: Optional[Tuple[int, int, int, int, bool]] = None

        for rect in self.free_rects:
            # Try without rotation
            if width <= rect.width and height <= rect.height:
                score = self._score_position(rect, width, height)
                if score < best_score:
                    best_score = score
                    best_result = (rect.x, rect.y, width, height, False)

            # Try with rotation
            if self.options.allow_rotation:
                if height <= rect.width and width <= rect.height:
                    score = self._score_position(rect, height, width)
                    # Small penalty for rotation
                    score = (score[0] + 0.1, score[1])
                    if score < best_score:
                        best_score = score
                        best_result = (rect.x, rect.y, height, width, True)

        return best_result

    def _score_position(
        self,
        rect: Rect,
        width: int,
        height: int,
    ) -> Tuple[float, float]:
        """Score a potential placement position (lower is better).

        Returns a tuple for tie-breaking: (primary_score, secondary_score).
        """
        leftover_w = rect.width - width
        leftover_h = rect.height - height

        if self.heuristic == MaxRectsHeuristic.BSSF:
            # Best Short Side Fit - minimize the shorter leftover side
            short_side = min(leftover_w, leftover_h)
            long_side = max(leftover_w, leftover_h)
            return (float(short_side), float(long_side))

        elif self.heuristic == MaxRectsHeuristic.BLSF:
            # Best Long Side Fit - minimize the longer leftover side
            short_side = min(leftover_w, leftover_h)
            long_side = max(leftover_w, leftover_h)
            return (float(long_side), float(short_side))

        elif self.heuristic == MaxRectsHeuristic.BAF:
            # Best Area Fit - minimize leftover area
            leftover_area = leftover_w * rect.height + leftover_h * width
            short_side = min(leftover_w, leftover_h)
            return (float(leftover_area), float(short_side))

        elif self.heuristic == MaxRectsHeuristic.BL:
            # Bottom-Left - prefer lower Y, then lower X
            return (float(rect.y), float(rect.x))

        elif self.heuristic == MaxRectsHeuristic.CP:
            # Contact Point - maximize contact with edges
            contact = self._calculate_contact_score(rect.x, rect.y, width, height)
            # Negate because lower scores are better
            return (-float(contact), float(rect.y))

        # Default to BSSF
        short_side = min(leftover_w, leftover_h)
        long_side = max(leftover_w, leftover_h)
        return (float(short_side), float(long_side))

    def _calculate_contact_score(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> int:
        """Calculate contact points for a rectangle placement.

        Contact points are pixels where the rectangle touches:
        - The bin boundaries
        - Other already-placed rectangles
        """
        border = self.options.border_padding
        contact = 0

        # Contact with bin edges
        if x == border:
            contact += height  # Left edge
        if y == border:
            contact += width  # Top edge
        if x + width == self._bin_width - border:
            contact += height  # Right edge
        if y + height == self._bin_height - border:
            contact += width  # Bottom edge

        # Contact with placed rectangles
        for used in self.used_rects:
            # Check horizontal adjacency
            if x == used.right or x + width == used.x:
                # Calculate vertical overlap
                y_start = max(y, used.y)
                y_end = min(y + height, used.bottom)
                if y_end > y_start:
                    contact += y_end - y_start

            # Check vertical adjacency
            if y == used.bottom or y + height == used.y:
                # Calculate horizontal overlap
                x_start = max(x, used.x)
                x_end = min(x + width, used.right)
                if x_end > x_start:
                    contact += x_end - x_start

        return contact

    def _place_rect(self, rect: Rect) -> None:
        """Place a rectangle and update free rectangles."""
        self.used_rects.append(rect)

        # Split all free rectangles that intersect with the placed rect
        new_free: List[Rect] = []

        for free_rect in self.free_rects:
            if not free_rect.intersects(rect):
                new_free.append(free_rect)
                continue

            # Split the free rectangle around the placed rectangle
            splits = self._split_rect(free_rect, rect)
            new_free.extend(splits)

        self.free_rects = new_free

        # Prune rectangles that are fully contained in others
        self._prune_free_rects()

    def _split_rect(self, free_rect: Rect, placed: Rect) -> List[Rect]:
        """Split a free rectangle around a placed rectangle.

        Creates up to 4 new rectangles from the portions of free_rect
        that don't overlap with placed.
        """
        result: List[Rect] = []

        # Left portion
        if placed.x > free_rect.x:
            result.append(
                Rect(
                    free_rect.x,
                    free_rect.y,
                    placed.x - free_rect.x,
                    free_rect.height,
                )
            )

        # Right portion
        if placed.right < free_rect.right:
            result.append(
                Rect(
                    placed.right,
                    free_rect.y,
                    free_rect.right - placed.right,
                    free_rect.height,
                )
            )

        # Top portion
        if placed.y > free_rect.y:
            result.append(
                Rect(
                    free_rect.x,
                    free_rect.y,
                    free_rect.width,
                    placed.y - free_rect.y,
                )
            )

        # Bottom portion
        if placed.bottom < free_rect.bottom:
            result.append(
                Rect(
                    free_rect.x,
                    placed.bottom,
                    free_rect.width,
                    free_rect.bottom - placed.bottom,
                )
            )

        # Filter out zero-area rectangles
        return [r for r in result if r.area > 0]

    def _prune_free_rects(self) -> None:
        """Remove free rectangles that are fully contained in others.

        This is O(n²) but necessary for correctness. Uses NumPy for
        vectorized containment checks when there are many rectangles.
        """
        if len(self.free_rects) <= 1:
            return

        # Use numpy for efficient batch containment checks
        n = len(self.free_rects)
        if n > 20:
            self._prune_free_rects_numpy()
        else:
            self._prune_free_rects_simple()

    def _prune_free_rects_simple(self) -> None:
        """Simple O(n²) pruning for small lists."""
        i = 0
        while i < len(self.free_rects):
            j = i + 1
            remove_i = False
            while j < len(self.free_rects):
                ri = self.free_rects[i]
                rj = self.free_rects[j]

                if rj.contains(ri):
                    remove_i = True
                    break
                elif ri.contains(rj):
                    del self.free_rects[j]
                    continue
                j += 1

            if remove_i:
                del self.free_rects[i]
            else:
                i += 1

    def _prune_free_rects_numpy(self) -> None:
        """NumPy-accelerated pruning for larger lists."""
        n = len(self.free_rects)
        if n == 0:
            return

        # Convert to numpy arrays
        rects = np.array(
            [(r.x, r.y, r.right, r.bottom) for r in self.free_rects],
            dtype=np.int32,
        )

        # Keep track of which rectangles to remove
        remove = np.zeros(n, dtype=bool)

        for i in range(n):
            if remove[i]:
                continue

            # Check if any other rectangle contains this one
            # A contains B if: A.x <= B.x and A.y <= B.y and
            #                  A.right >= B.right and A.bottom >= B.bottom
            contains_i = (
                (rects[:, 0] <= rects[i, 0])
                & (rects[:, 1] <= rects[i, 1])
                & (rects[:, 2] >= rects[i, 2])
                & (rects[:, 3] >= rects[i, 3])
            )
            contains_i[i] = False  # Don't compare with self

            if np.any(contains_i):
                remove[i] = True

        # Keep only non-removed rectangles
        self.free_rects = [self.free_rects[i] for i in range(n) if not remove[i]]

    def occupancy(self) -> float:
        """Calculate the ratio of used area to total bin area."""
        used_area = sum(r.area for r in self.used_rects)
        total_area = self._bin_width * self._bin_height
        return used_area / total_area if total_area > 0 else 0.0


__all__ = ["MaxRectsPacker"]
