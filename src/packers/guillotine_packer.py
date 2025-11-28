"""
Guillotine bin packing algorithm.

This packer subdivides the atlas into rectangular regions using guillotine cuts.
When a frame is placed, the remaining space is split either horizontally or
vertically (like a paper guillotine), creating new free rectangles.

Supports multiple placement heuristics:
- BSSF (Best Short Side Fit): Minimize short side remainder
- BLSF (Best Long Side Fit): Minimize long side remainder
- BAF (Best Area Fit): Minimize area waste
- WAF (Worst Area Fit): Maximize area waste (for uniform distribution)

Supports multiple split rules:
- SHORTER_LEFTOVER_AXIS: Split along shorter leftover side
- LONGER_LEFTOVER_AXIS: Split along longer leftover side
- SHORTER_AXIS: Split along shorter frame side
- LONGER_AXIS: Split along longer frame side
- MIN_AREA: Minimize area of smallest resulting rectangle
- MAX_AREA: Maximize area of smallest resulting rectangle
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Tuple, Optional


class GuillotinePlacement(Enum):
    """Heuristics for choosing where to place a rectangle."""

    BSSF = auto()  # Best Short Side Fit
    BLSF = auto()  # Best Long Side Fit
    BAF = auto()  # Best Area Fit
    WAF = auto()  # Worst Area Fit


class GuillotineSplit(Enum):
    """Heuristics for how to split remaining space after placement."""

    SHORTER_LEFTOVER_AXIS = auto()
    LONGER_LEFTOVER_AXIS = auto()
    SHORTER_AXIS = auto()
    LONGER_AXIS = auto()
    MIN_AREA = auto()
    MAX_AREA = auto()


@dataclass
class Rect:
    """A rectangle with position and size."""

    x: int
    y: int
    width: int
    height: int

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def short_side(self) -> int:
        return min(self.width, self.height)

    @property
    def long_side(self) -> int:
        """Return the longer side of the rectangle."""
        return max(self.width, self.height)


class GuillotinePacker:
    """
    Guillotine bin packing algorithm.

    Maintains a list of free rectangles. When placing a frame, finds the best
    fit according to the placement heuristic, then splits the free rectangle
    using the split heuristic.
    """

    def __init__(
        self,
        width: int,
        height: int,
        placement: GuillotinePlacement = GuillotinePlacement.BAF,
        split: GuillotineSplit = GuillotineSplit.SHORTER_LEFTOVER_AXIS,
        allow_rotation: bool = False,
        padding: int = 0,
    ):
        """
        Initialize the guillotine packer.

        Args:
            width: Atlas width
            height: Atlas height
            placement: Placement heuristic for choosing position
            split: Split heuristic for dividing remaining space
            allow_rotation: Whether frames can be rotated 90 degrees
            padding: Padding between frames
        """
        self.bin_width = width
        self.bin_height = height
        self.placement = placement
        self.split = split
        self.allow_rotation = allow_rotation
        self.padding = padding

        # Start with one free rectangle covering the entire bin
        self.free_rects: List[Rect] = [Rect(0, 0, width, height)]
        self.used_rects: List[Rect] = []

    def reset(self):
        """Reset packer to initial state."""
        self.free_rects = [Rect(0, 0, self.bin_width, self.bin_height)]
        self.used_rects = []

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
        best_idx = -1
        best_score = float("inf")
        best_rect = None
        best_rotated = False

        for i, free_rect in enumerate(self.free_rects):
            # Try without rotation
            if width <= free_rect.width and height <= free_rect.height:
                score = self._score_placement(width, height, free_rect)
                if score < best_score:
                    best_score = score
                    best_idx = i
                    best_rect = Rect(free_rect.x, free_rect.y, width, height)
                    best_rotated = False

            # Try with rotation
            if (
                self.allow_rotation
                and height <= free_rect.width
                and width <= free_rect.height
            ):
                score = self._score_placement(height, width, free_rect)
                if score < best_score:
                    best_score = score
                    best_idx = i
                    best_rect = Rect(free_rect.x, free_rect.y, height, width)
                    best_rotated = True

        if best_idx == -1:
            return None

        # Split the free rectangle
        self._split_free_rect(best_idx, best_rect)

        self.used_rects.append(best_rect)

        return (
            best_rect.x,
            best_rect.y,
            best_rect.width,
            best_rect.height,
            best_rotated,
        )

    def _score_placement(self, width: int, height: int, free_rect: Rect) -> float:
        """Score a potential placement (lower is better)."""
        leftover_w = free_rect.width - width
        leftover_h = free_rect.height - height

        if self.placement == GuillotinePlacement.BSSF:
            # Best Short Side Fit - minimize shorter leftover side
            return min(leftover_w, leftover_h)

        elif self.placement == GuillotinePlacement.BLSF:
            # Best Long Side Fit - minimize longer leftover side
            return max(leftover_w, leftover_h)

        elif self.placement == GuillotinePlacement.BAF:
            # Best Area Fit - minimize leftover area
            return leftover_w * free_rect.height + leftover_h * width

        elif self.placement == GuillotinePlacement.WAF:
            # Worst Area Fit - maximize leftover area (negative for min-heap behavior)
            return -(leftover_w * free_rect.height + leftover_h * width)

        return 0

    def _split_free_rect(self, free_idx: int, placed: Rect):
        """
        Split a free rectangle after placing a rect in it.

        The guillotine split creates two new rectangles from the leftover space.
        """
        free_rect = self.free_rects[free_idx]

        # Calculate leftover dimensions
        leftover_w = free_rect.width - placed.width
        leftover_h = free_rect.height - placed.height

        # Determine split direction based on heuristic
        split_horizontal = self._should_split_horizontal(
            placed.width, placed.height, leftover_w, leftover_h
        )

        # Create new free rectangles
        new_rects = []

        if split_horizontal:
            # Horizontal split: right rect is tall, bottom rect is wide
            if leftover_w > 0:
                new_rects.append(
                    Rect(
                        placed.x + placed.width,
                        free_rect.y,
                        leftover_w,
                        free_rect.height,
                    )
                )
            if leftover_h > 0:
                new_rects.append(
                    Rect(
                        free_rect.x, placed.y + placed.height, placed.width, leftover_h
                    )
                )
        else:
            # Vertical split: right rect is short, bottom rect is wide
            if leftover_w > 0:
                new_rects.append(
                    Rect(
                        placed.x + placed.width, free_rect.y, leftover_w, placed.height
                    )
                )
            if leftover_h > 0:
                new_rects.append(
                    Rect(
                        free_rect.x,
                        placed.y + placed.height,
                        free_rect.width,
                        leftover_h,
                    )
                )

        # Remove the used free rectangle and add new ones
        del self.free_rects[free_idx]
        self.free_rects.extend(new_rects)

    def _should_split_horizontal(
        self, width: int, height: int, leftover_w: int, leftover_h: int
    ) -> bool:
        """Determine if we should split horizontally or vertically."""

        if self.split == GuillotineSplit.SHORTER_LEFTOVER_AXIS:
            return leftover_w < leftover_h

        elif self.split == GuillotineSplit.LONGER_LEFTOVER_AXIS:
            return leftover_w >= leftover_h

        elif self.split == GuillotineSplit.SHORTER_AXIS:
            return width < height

        elif self.split == GuillotineSplit.LONGER_AXIS:
            return width >= height

        elif self.split == GuillotineSplit.MIN_AREA:
            # Choose split that minimizes the smallest resulting rectangle
            # Horizontal split
            h_area1 = leftover_w * (height + leftover_h)  # right rect
            h_area2 = width * leftover_h  # bottom rect
            h_min = min(h_area1, h_area2) if leftover_w > 0 and leftover_h > 0 else 0

            # Vertical split
            v_area1 = leftover_w * height  # right rect
            v_area2 = (width + leftover_w) * leftover_h  # bottom rect
            v_min = min(v_area1, v_area2) if leftover_w > 0 and leftover_h > 0 else 0

            return h_min < v_min

        elif self.split == GuillotineSplit.MAX_AREA:
            # Choose split that maximizes the smallest resulting rectangle
            h_area1 = leftover_w * (height + leftover_h)
            h_area2 = width * leftover_h
            h_min = min(h_area1, h_area2) if leftover_w > 0 and leftover_h > 0 else 0

            v_area1 = leftover_w * height
            v_area2 = (width + leftover_w) * leftover_h
            v_min = min(v_area1, v_area2) if leftover_w > 0 and leftover_h > 0 else 0

            return h_min >= v_min

        return True  # Default to horizontal

    def occupancy(self) -> float:
        """Calculate the ratio of used area to total bin area."""
        used_area = sum(rect.area for rect in self.used_rects)
        total_area = self.bin_width * self.bin_height
        return used_area / total_area if total_area > 0 else 0

    def merge_free_rects(self):
        """
        Attempt to merge adjacent free rectangles.

        This is an O(n²) operation but can improve packing efficiency
        by reducing fragmentation.
        """
        i = 0
        while i < len(self.free_rects):
            j = i + 1
            while j < len(self.free_rects):
                r1 = self.free_rects[i]
                r2 = self.free_rects[j]

                # Check if rectangles can be merged horizontally
                if r1.y == r2.y and r1.height == r2.height and r1.x + r1.width == r2.x:
                    self.free_rects[i] = Rect(
                        r1.x, r1.y, r1.width + r2.width, r1.height
                    )
                    del self.free_rects[j]
                    continue

                if r2.y == r1.y and r2.height == r1.height and r2.x + r2.width == r1.x:
                    self.free_rects[i] = Rect(
                        r2.x, r1.y, r1.width + r2.width, r1.height
                    )
                    del self.free_rects[j]
                    continue

                # Check if rectangles can be merged vertically
                if r1.x == r2.x and r1.width == r2.width and r1.y + r1.height == r2.y:
                    self.free_rects[i] = Rect(
                        r1.x, r1.y, r1.width, r1.height + r2.height
                    )
                    del self.free_rects[j]
                    continue

                if r2.x == r1.x and r2.width == r1.width and r2.y + r2.height == r1.y:
                    self.free_rects[i] = Rect(
                        r1.x, r2.y, r1.width, r1.height + r2.height
                    )
                    del self.free_rects[j]
                    continue

                j += 1
            i += 1
