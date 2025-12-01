#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Shelf bin packing algorithm with multiple heuristics.

The Shelf algorithm organizes frames into horizontal shelves (rows). Each shelf
has a fixed height determined by the first (tallest) frame placed on it.
Subsequent frames are placed left-to-right until no more fit, then a new shelf
is created below.

Shelf packing is simpler and faster than MaxRects/Guillotine but may waste more
vertical space within shelves. Best suited for frames of similar heights.

Heuristics:
    - NEXT_FIT: Always use the current (last) shelf
    - FIRST_FIT: Use the first shelf where the frame fits
    - BEST_WIDTH_FIT: Use shelf with least remaining width after placement
    - BEST_HEIGHT_FIT: Use shelf whose height matches frame height best
    - WORST_WIDTH_FIT: Use shelf with most remaining width (load balancing)

This module also includes ShelfPackerDecreasingHeight which pre-sorts frames
by height for the classic "First Fit Decreasing Height" (FFDH) algorithm.

Usage:
    from packers.shelf_packer import ShelfPacker, ShelfPackerDecreasingHeight
    from packers.packer_types import FrameInput, PackerOptions

    packer = ShelfPacker()
    packer.set_heuristic("best_height")
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
    ShelfHeuristic,
)


@dataclass
class Shelf:
    """A horizontal shelf in the bin.

    Attributes:
        y: Top Y coordinate of the shelf.
        height: Height of the shelf (set by first item).
        used_width: Width consumed by placed frames.
    """

    y: int
    height: int
    used_width: int = 0

    def remaining_width(self, bin_width: int, border: int = 0) -> int:
        """Calculate remaining usable width on this shelf."""
        return bin_width - 2 * border - self.used_width


class ShelfPacker(BasePacker):
    """Shelf bin packing algorithm.

    Maintains a list of horizontal shelves. Frames are placed on shelves
    left-to-right. When a frame does not fit on any existing shelf, a new
    shelf is created below the others.

    Attributes:
        options: Packer configuration options.
        shelves: List of shelf objects.
        heuristic: Shelf selection heuristic.
    """

    ALGORITHM_NAME = "shelf"
    DISPLAY_NAME = "Shelf Packer"
    SUPPORTED_HEURISTICS = [
        ("next_fit", "Next Fit"),
        ("first_fit", "First Fit"),
        ("best_width", "Best Width Fit"),
        ("best_height", "Best Height Fit"),
        ("worst_width", "Worst Width Fit"),
    ]

    def __init__(self, options: Optional[PackerOptions] = None) -> None:
        super().__init__(options)
        self.shelves: List[Shelf] = []
        self.heuristic: ShelfHeuristic = ShelfHeuristic.BEST_HEIGHT_FIT
        self._bin_width: int = 0
        self._bin_height: int = 0
        self._current_y: int = 0
        self._placed: List[Tuple[int, int, int, int]] = []

    def set_heuristic(self, heuristic_key: str) -> bool:
        """Set the shelf selection heuristic.

        Args:
            heuristic_key: One of 'next_fit', 'first_fit', 'best_width',
                          'best_height', 'worst_width'.

        Returns:
            True if heuristic was set, False if invalid key.
        """
        heuristic_map = {
            "next_fit": ShelfHeuristic.NEXT_FIT,
            "first_fit": ShelfHeuristic.FIRST_FIT,
            "best_width": ShelfHeuristic.BEST_WIDTH_FIT,
            "best_height": ShelfHeuristic.BEST_HEIGHT_FIT,
            "worst_width": ShelfHeuristic.WORST_WIDTH_FIT,
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
        """Pack frames using the Shelf algorithm."""
        self._init_bin(width, height)
        packed: List[PackedFrame] = []
        padding = self.options.padding

        for frame in frames:
            frame_w = frame.width + padding
            frame_h = frame.height + padding

            result = self._insert_frame(frame_w, frame_h)
            if result is None:
                return packed  # Cannot fit this frame

            x, y, placed_w, placed_h, rotated = result

            packed_frame = PackedFrame(
                frame=frame,
                x=x,
                y=y,
                rotated=rotated,
            )
            packed.append(packed_frame)
            self._placed.append((x, y, placed_w, placed_h))

        return packed

    def _init_bin(self, width: int, height: int) -> None:
        """Initialize the bin with the given dimensions."""
        self._bin_width = width
        self._bin_height = height
        self._current_y = self.options.border_padding
        self.shelves = []
        self._placed = []

    def _insert_frame(
        self,
        width: int,
        height: int,
    ) -> Optional[Tuple[int, int, int, int, bool]]:
        """Insert a frame into a shelf.

        Returns:
            (x, y, width, height, rotated) or None if cannot fit.
        """
        # Try to find a suitable existing shelf
        result = self._find_shelf(width, height, False)

        # Try with rotation if enabled
        if result is None and self.options.allow_rotation:
            result = self._find_shelf(height, width, True)

        # If still no fit, create a new shelf
        if result is None:
            result = self._create_new_shelf(width, height, False)

        if result is None and self.options.allow_rotation:
            result = self._create_new_shelf(height, width, True)

        return result

    def _find_shelf(
        self,
        width: int,
        height: int,
        rotated: bool,
    ) -> Optional[Tuple[int, int, int, int, bool]]:
        """Find an existing shelf that can fit the frame."""
        if not self.shelves:
            return None

        border = self.options.border_padding

        if self.heuristic == ShelfHeuristic.NEXT_FIT:
            # Only try the last shelf
            shelf = self.shelves[-1]
            if self._fits_on_shelf(shelf, width, height):
                return self._place_on_shelf(shelf, width, height, rotated)
            return None

        best_shelf: Optional[Shelf] = None
        best_score = float("inf")

        for shelf in self.shelves:
            if not self._fits_on_shelf(shelf, width, height):
                continue

            if self.heuristic == ShelfHeuristic.FIRST_FIT:
                # Use first shelf that fits
                return self._place_on_shelf(shelf, width, height, rotated)

            elif self.heuristic == ShelfHeuristic.BEST_WIDTH_FIT:
                # Minimize remaining width after placement
                remaining = shelf.remaining_width(self._bin_width, border) - width
                if remaining < best_score:
                    best_score = remaining
                    best_shelf = shelf

            elif self.heuristic == ShelfHeuristic.BEST_HEIGHT_FIT:
                # Minimize wasted vertical space
                height_diff = shelf.height - height
                if height_diff >= 0 and height_diff < best_score:
                    best_score = height_diff
                    best_shelf = shelf

            elif self.heuristic == ShelfHeuristic.WORST_WIDTH_FIT:
                # Maximize remaining width (use fullest shelves last)
                remaining = shelf.remaining_width(self._bin_width, border) - width
                score = -remaining  # Negate for minimum search
                if score < best_score:
                    best_score = score
                    best_shelf = shelf

        if best_shelf is not None:
            return self._place_on_shelf(best_shelf, width, height, rotated)

        return None

    def _fits_on_shelf(self, shelf: Shelf, width: int, height: int) -> bool:
        """Check if a frame fits on the given shelf."""
        border = self.options.border_padding

        # Must fit within remaining width
        if shelf.remaining_width(self._bin_width, border) < width:
            return False

        # Must not exceed shelf height
        if height > shelf.height:
            return False

        return True

    def _place_on_shelf(
        self,
        shelf: Shelf,
        width: int,
        height: int,
        rotated: bool,
    ) -> Tuple[int, int, int, int, bool]:
        """Place a frame on a shelf."""
        border = self.options.border_padding
        x = border + shelf.used_width
        y = shelf.y

        shelf.used_width += width

        return (x, y, width, height, rotated)

    def _create_new_shelf(
        self,
        width: int,
        height: int,
        rotated: bool,
    ) -> Optional[Tuple[int, int, int, int, bool]]:
        """Create a new shelf for the frame."""
        border = self.options.border_padding

        # Check if new shelf would exceed bin height
        if self._current_y + height > self._bin_height - border:
            return None

        # Check width fits
        if width > self._bin_width - 2 * border:
            return None

        # Create new shelf with height matching the first item
        new_shelf = Shelf(y=self._current_y, height=height)
        self.shelves.append(new_shelf)
        self._current_y += height

        return self._place_on_shelf(new_shelf, width, height, rotated)

    def shelf_occupancy(self) -> float:
        """Calculate ratio of used area to shelf area (ignoring bottom waste)."""
        if not self.shelves:
            return 0.0

        used_area = sum(w * h for x, y, w, h in self._placed)
        shelf_area = sum(
            shelf.height * (self._bin_width - 2 * self.options.border_padding)
            for shelf in self.shelves
        )
        return used_area / shelf_area if shelf_area > 0 else 0.0


class ShelfPackerDecreasingHeight(ShelfPacker):
    """Shelf packer with pre-sorting by decreasing height.

    This is the classic "First Fit Decreasing Height" (FFDH) algorithm,
    which typically achieves better packing than unsorted shelf packing.

    Frames are sorted by height descending before packing, but the original
    order is preserved in the output.
    """

    ALGORITHM_NAME = "shelf-ffdh"
    DISPLAY_NAME = "Shelf Packer (FFDH)"

    def _pack_internal(
        self,
        frames: List[FrameInput],
        width: int,
        height: int,
    ) -> List[PackedFrame]:
        """Pack frames sorted by decreasing height."""
        self._init_bin(width, height)
        padding = self.options.padding

        # Create indexed list for sorting
        indexed_frames = [(f, i) for i, f in enumerate(frames)]

        # Sort by height descending, then width descending
        sorted_frames = sorted(
            indexed_frames,
            key=lambda x: (x[0].height, x[0].width),
            reverse=True,
        )

        # Pack in sorted order, tracking original indices
        temp_results: List[Tuple[PackedFrame, int]] = []

        for frame, original_idx in sorted_frames:
            frame_w = frame.width + padding
            frame_h = frame.height + padding

            result = self._insert_frame(frame_w, frame_h)
            if result is None:
                # Return only successfully packed frames in original order
                temp_results.sort(key=lambda x: x[1])
                return [pf for pf, _ in temp_results]

            x, y, placed_w, placed_h, rotated = result

            packed_frame = PackedFrame(
                frame=frame,
                x=x,
                y=y,
                rotated=rotated,
            )
            temp_results.append((packed_frame, original_idx))
            self._placed.append((x, y, placed_w, placed_h))

        # Restore original order
        temp_results.sort(key=lambda x: x[1])
        return [pf for pf, _ in temp_results]


__all__ = ["ShelfPacker", "ShelfPackerDecreasingHeight", "Shelf"]
