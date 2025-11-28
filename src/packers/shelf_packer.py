"""
Shelf bin packing algorithm.

This packer organizes frames into horizontal shelves (rows). Each shelf has a
fixed height determined by the first (tallest) frame placed on it. Subsequent
frames are placed left-to-right until no more fit, then a new shelf is created.

Shelf packing is simpler and faster than MaxRects/Guillotine but may waste more
vertical space within shelves. Good for frames of similar heights.

Supports multiple heuristics:
- NEXT_FIT: Always use the current (last) shelf
- FIRST_FIT: Use the first shelf where the frame fits
- BEST_WIDTH_FIT: Use shelf with least remaining width after placement
- BEST_HEIGHT_FIT: Use shelf whose height matches frame height best
- WORST_WIDTH_FIT: Use shelf with most remaining width (for load balancing)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Tuple, Optional


class ShelfHeuristic(Enum):
    """Heuristics for choosing which shelf to place a frame on."""

    NEXT_FIT = auto()  # Use current shelf only
    FIRST_FIT = auto()  # Use first shelf that fits
    BEST_WIDTH_FIT = auto()  # Minimize remaining width
    BEST_HEIGHT_FIT = auto()  # Minimize height difference
    WORST_WIDTH_FIT = auto()  # Maximize remaining width


@dataclass
class Shelf:
    """A horizontal shelf in the bin."""

    y: int  # Top of shelf
    height: int  # Shelf height (fixed once first item placed)
    used_width: int = 0  # Width consumed so far

    def remaining_width(self, bin_width: int) -> int:
        """Calculate remaining width on this shelf."""
        return bin_width - self.used_width


class ShelfPacker:
    """
    Shelf bin packing algorithm.

    Maintains a list of horizontal shelves. Frames are placed on shelves
    left-to-right. When a frame doesn't fit on any existing shelf, a new
    shelf is created below the others.
    """

    def __init__(
        self,
        width: int,
        height: int,
        heuristic: ShelfHeuristic = ShelfHeuristic.BEST_HEIGHT_FIT,
        allow_rotation: bool = False,
        padding: int = 0,
    ):
        """
        Initialize the shelf packer.

        Args:
            width: Atlas width
            height: Atlas height
            heuristic: Shelf selection heuristic
            allow_rotation: Whether frames can be rotated 90 degrees
            padding: Padding between frames
        """
        self.bin_width = width
        self.bin_height = height
        self.heuristic = heuristic
        self.allow_rotation = allow_rotation
        self.padding = padding

        self.shelves: List[Shelf] = []
        self.current_y = 0  # Y position for next new shelf
        self.placed: List[Tuple[int, int, int, int]] = []  # x, y, w, h

    def reset(self):
        """Reset packer to initial state."""
        self.shelves = []
        self.current_y = 0
        self.placed = []

    def pack(
        self, frames: List[Tuple[int, int, any]]
    ) -> List[Tuple[int, int, int, int, bool, any]]:
        """
        Pack frames into the bin.

        Args:
            frames: List of (width, height, user_data) tuples

        Returns:
            List of (x, y, width, height, rotated, user_data) for placed frames.
            Returns empty list if any frame couldn't be placed.
        """
        results = []

        for width, height, data in frames:
            # Add padding to frame dimensions
            padded_w = width + self.padding
            padded_h = height + self.padding

            result = self._insert_rect(padded_w, padded_h)
            if result is None:
                return []  # Failed to pack

            x, y, placed_w, placed_h, rotated = result

            # Store result with original dimensions (remove padding)
            results.append((x, y, width, height, rotated, data))

        return results

    def _insert_rect(
        self, width: int, height: int
    ) -> Optional[Tuple[int, int, int, int, bool]]:
        """
        Insert a single rectangle.

        Returns:
            (x, y, width, height, rotated) if successful, None otherwise
        """
        # Try to find a suitable shelf
        result = self._find_shelf(width, height, False)

        # Try with rotation if enabled and no fit found
        if result is None and self.allow_rotation:
            result = self._find_shelf(height, width, True)

        # If still no fit, try creating a new shelf
        if result is None:
            result = self._create_new_shelf(width, height, False)

        if result is None and self.allow_rotation:
            result = self._create_new_shelf(height, width, True)

        return result

    def _find_shelf(
        self, width: int, height: int, rotated: bool
    ) -> Optional[Tuple[int, int, int, int, bool]]:
        """Find an existing shelf that can fit the rectangle."""

        if not self.shelves:
            return None

        if self.heuristic == ShelfHeuristic.NEXT_FIT:
            # Only try the last shelf
            shelf = self.shelves[-1]
            if self._fits_on_shelf(shelf, width, height):
                return self._place_on_shelf(shelf, width, height, rotated)
            return None

        best_shelf = None
        best_score = float("inf")

        for shelf in self.shelves:
            if not self._fits_on_shelf(shelf, width, height):
                continue

            if self.heuristic == ShelfHeuristic.FIRST_FIT:
                # Use first shelf that fits
                return self._place_on_shelf(shelf, width, height, rotated)

            elif self.heuristic == ShelfHeuristic.BEST_WIDTH_FIT:
                # Minimize remaining width after placement
                remaining = shelf.remaining_width(self.bin_width) - width
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
                remaining = shelf.remaining_width(self.bin_width) - width
                score = -remaining  # Negative because we want maximum
                if score < best_score:
                    best_score = score
                    best_shelf = shelf

        if best_shelf is not None:
            return self._place_on_shelf(best_shelf, width, height, rotated)

        return None

    def _fits_on_shelf(self, shelf: Shelf, width: int, height: int) -> bool:
        """Check if a rectangle fits on the given shelf."""
        # Must fit within remaining width
        if shelf.remaining_width(self.bin_width) < width:
            return False
        # Must not exceed shelf height
        if height > shelf.height:
            return False
        return True

    def _place_on_shelf(
        self, shelf: Shelf, width: int, height: int, rotated: bool
    ) -> Tuple[int, int, int, int, bool]:
        """Place a rectangle on a shelf."""
        x = shelf.used_width
        y = shelf.y

        shelf.used_width += width
        self.placed.append((x, y, width, height))

        return (x, y, width, height, rotated)

    def _create_new_shelf(
        self, width: int, height: int, rotated: bool
    ) -> Optional[Tuple[int, int, int, int, bool]]:
        """Create a new shelf for the rectangle."""
        # Check if new shelf would exceed bin height
        if self.current_y + height > self.bin_height:
            return None

        # Check width fits
        if width > self.bin_width:
            return None

        # Create new shelf with height matching the first item
        new_shelf = Shelf(y=self.current_y, height=height)
        self.shelves.append(new_shelf)
        self.current_y += height

        return self._place_on_shelf(new_shelf, width, height, rotated)

    def occupancy(self) -> float:
        """Calculate the ratio of used area to total bin area."""
        used_area = sum(w * h for x, y, w, h in self.placed)
        total_area = self.bin_width * self.bin_height
        return used_area / total_area if total_area > 0 else 0

    def shelf_occupancy(self) -> float:
        """Calculate the ratio of used area to shelf area (ignoring bottom waste)."""
        if not self.shelves:
            return 0

        used_area = sum(w * h for x, y, w, h in self.placed)
        shelf_area = sum(shelf.height * self.bin_width for shelf in self.shelves)
        return used_area / shelf_area if shelf_area > 0 else 0


class ShelfPackerDecreasingHeight(ShelfPacker):
    """
    Shelf packer that pre-sorts frames by decreasing height.

    This is the classic "First Fit Decreasing Height" (FFDH) algorithm,
    which typically achieves better packing than unsorted shelf packing.
    """

    def pack(
        self, frames: List[Tuple[int, int, any]]
    ) -> List[Tuple[int, int, int, int, bool, any]]:
        """
        Pack frames sorted by decreasing height.

        Args:
            frames: List of (width, height, user_data) tuples

        Returns:
            List of (x, y, width, height, rotated, user_data) for placed frames.
            Returns empty list if any frame couldn't be placed.
        """
        # Sort by height descending, then width descending
        indexed_frames = [(w, h, data, i) for i, (w, h, data) in enumerate(frames)]
        sorted_frames = sorted(indexed_frames, key=lambda f: (-f[1], -f[0]))

        # Pack in sorted order
        temp_results = []
        for width, height, data, original_idx in sorted_frames:
            padded_w = width + self.padding
            padded_h = height + self.padding

            result = self._insert_rect(padded_w, padded_h)
            if result is None:
                return []  # Failed to pack

            x, y, placed_w, placed_h, rotated = result
            temp_results.append((x, y, width, height, rotated, data, original_idx))

        # Restore original order
        temp_results.sort(key=lambda r: r[6])
        results = [(x, y, w, h, rot, data) for x, y, w, h, rot, data, _ in temp_results]

        return results
