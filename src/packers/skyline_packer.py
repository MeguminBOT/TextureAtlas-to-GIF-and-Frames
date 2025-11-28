"""
Skyline bin packing algorithm.

The Skyline algorithm maintains a "skyline" representing the top edge of placed
rectangles. Each segment of the skyline has a position (x) and height (y).
New rectangles are placed by finding the best position along the skyline.

This is one of the most efficient packing algorithms, offering near-optimal
results with O(n²) complexity.

Supports multiple heuristics:
- BOTTOM_LEFT: Place at lowest Y position, tie-break by leftmost X
- MIN_WASTE: Place where least space is wasted below the rectangle
- BEST_FIT: Find position where rectangle fits best with skyline
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Optional


class SkylineHeuristic(Enum):
    """Heuristics for choosing placement position."""

    BOTTOM_LEFT = auto()  # Minimize Y, then X
    MIN_WASTE = auto()  # Minimize wasted space below rectangle
    BEST_FIT = auto()  # Best fit to skyline contour


@dataclass
class SkylineNode:
    """A segment of the skyline."""

    x: int  # Starting X position
    y: int  # Height (Y position of top)
    width: int  # Width of this segment


class SkylinePacker:
    """
    Skyline bin packing algorithm.

    The skyline is a horizontal line representing the top edge of all placed
    rectangles. When a rectangle is placed, it updates the skyline by raising
    the appropriate segments.
    """

    def __init__(
        self,
        width: int,
        height: int,
        heuristic: SkylineHeuristic = SkylineHeuristic.MIN_WASTE,
        allow_rotation: bool = False,
        padding: int = 0,
    ):
        """
        Initialize the skyline packer.

        Args:
            width: Atlas width
            height: Atlas height
            heuristic: Placement heuristic
            allow_rotation: Whether frames can be rotated 90 degrees
            padding: Padding between frames
        """
        self.bin_width = width
        self.bin_height = height
        self.heuristic = heuristic
        self.allow_rotation = allow_rotation
        self.padding = padding

        # Initialize skyline with a single segment at y=0
        self.skyline: list[SkylineNode] = [SkylineNode(0, 0, width)]
        self.placed: list[tuple[int, int, int, int]] = []  # x, y, w, h

    def reset(self):
        """Reset packer to initial state."""
        self.skyline = [SkylineNode(0, 0, self.bin_width)]
        self.placed = []

    def pack(
        self, frames: list[tuple[int, int, Any]]
    ) -> list[tuple[int, int, int, int, bool, Any]]:
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

            # Store result with original dimensions
            results.append((x, y, width, height, rotated, data))

        return results

    def _insert_rect(
        self, width: int, height: int
    ) -> Optional[tuple[int, int, int, int, bool]]:
        """
        Insert a single rectangle.

        Returns:
            (x, y, width, height, rotated) if successful, None otherwise
        """
        best_x = -1
        best_y = -1
        best_idx = -1
        best_width = width
        best_height = height
        best_rotated = False
        best_score = float("inf")

        # Try without rotation
        result = self._find_best_position(width, height)
        if result is not None:
            idx, x, y, score = result
            if score < best_score:
                best_score = score
                best_x = x
                best_y = y
                best_idx = idx
                best_width = width
                best_height = height
                best_rotated = False

        # Try with rotation
        if self.allow_rotation:
            result = self._find_best_position(height, width)
            if result is not None:
                idx, x, y, score = result
                if score < best_score:
                    best_score = score
                    best_x = x
                    best_y = y
                    best_idx = idx
                    best_width = height
                    best_height = width
                    best_rotated = True

        if best_idx == -1:
            return None

        # Place the rectangle and update skyline
        self._add_skyline_level(best_idx, best_x, best_y, best_width, best_height)
        self.placed.append((best_x, best_y, best_width, best_height))

        return (best_x, best_y, best_width, best_height, best_rotated)

    def _find_best_position(
        self, width: int, height: int
    ) -> Optional[tuple[int, int, int, float]]:
        """
        Find the best position for a rectangle of given dimensions.

        Returns:
            (skyline_index, x, y, score) if a position is found, None otherwise
        """
        best_idx = -1
        best_x = -1
        best_y = -1
        best_score = float("inf")

        for i in range(len(self.skyline)):
            result = self._fit_at_skyline_index(i, width, height)
            if result is None:
                continue

            x, y, waste = result

            # Check if rectangle fits within bin
            if y + height > self.bin_height:
                continue

            # Score based on heuristic
            if self.heuristic == SkylineHeuristic.BOTTOM_LEFT:
                score = y * self.bin_width + x
            elif self.heuristic == SkylineHeuristic.MIN_WASTE:
                score = waste
            elif self.heuristic == SkylineHeuristic.BEST_FIT:
                # Prefer positions where rectangle width matches skyline segment
                fit_score = abs(width - self.skyline[i].width)
                score = y * 1000 + fit_score
            else:
                score = y * self.bin_width + x

            if score < best_score:
                best_score = score
                best_x = x
                best_y = y
                best_idx = i

        if best_idx == -1:
            return None

        return (best_idx, best_x, best_y, best_score)

    def _fit_at_skyline_index(
        self, idx: int, width: int, height: int
    ) -> Optional[tuple[int, int, int]]:
        """
        Try to fit a rectangle starting at skyline index.

        Returns:
            (x, y, waste) if it fits, None otherwise
        """
        x = self.skyline[idx].x

        # Check if rectangle fits horizontally
        if x + width > self.bin_width:
            return None

        # Find the maximum Y across all skyline segments the rectangle spans
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

    def _add_skyline_level(self, idx: int, x: int, y: int, width: int, height: int):
        """
        Add a new skyline level after placing a rectangle.

        This updates the skyline to reflect the new top edge.
        """
        # Create new skyline node for the placed rectangle
        new_node = SkylineNode(x, y + height, width)

        # Remove all skyline nodes that are completely covered
        new_skyline = []
        i = 0

        # Copy nodes before the new rectangle
        while i < len(self.skyline) and self.skyline[i].x + self.skyline[i].width <= x:
            new_skyline.append(self.skyline[i])
            i += 1

        # Handle partial overlap on the left
        if i < len(self.skyline) and self.skyline[i].x < x:
            node = self.skyline[i]
            # Trim this node
            trimmed = SkylineNode(node.x, node.y, x - node.x)
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
            # Adjust start position
            overlap = x + width - node.x
            adjusted = SkylineNode(x + width, node.y, node.width - overlap)
            if adjusted.width > 0:
                new_skyline.append(adjusted)
            i += 1

        # Copy remaining nodes
        while i < len(self.skyline):
            new_skyline.append(self.skyline[i])
            i += 1

        self.skyline = new_skyline
        self._merge_skyline()

    def _merge_skyline(self):
        """Merge adjacent skyline nodes with the same height."""
        if len(self.skyline) <= 1:
            return

        merged = [self.skyline[0]]

        for i in range(1, len(self.skyline)):
            node = self.skyline[i]
            last = merged[-1]

            if last.y == node.y:
                # Merge nodes
                merged[-1] = SkylineNode(last.x, last.y, last.width + node.width)
            else:
                merged.append(node)

        self.skyline = merged

    def occupancy(self) -> float:
        """Calculate the ratio of used area to total bin area."""
        used_area = sum(w * h for x, y, w, h in self.placed)
        total_area = self.bin_width * self.bin_height
        return used_area / total_area if total_area > 0 else 0

    def get_skyline_height(self) -> int:
        """Get the maximum height of the current skyline."""
        if not self.skyline:
            return 0
        return max(node.y for node in self.skyline)
