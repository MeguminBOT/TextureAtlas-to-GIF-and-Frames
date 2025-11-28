#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MaxRects bin packing implementation with multiple placement heuristics.

MaxRects is one of the most efficient 2D bin packing algorithms. It maintains
a list of free rectangles and uses various heuristics to choose optimal placements.

Supports multiple heuristics:
- BSSF (Best Short Side Fit): Minimize short side remainder - good balance
- BLSF (Best Long Side Fit): Minimize long side remainder
- BAF (Best Area Fit): Minimize total wasted area
- BL (Bottom-Left): Place as low and left as possible - simple but effective
- CP (Contact Point): Maximize contact with other rectangles - reduces gaps
"""

from __future__ import annotations

from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple


class MaxRectsHeuristic(Enum):
    """Heuristics for choosing rectangle placement."""

    BSSF = auto()  # Best Short Side Fit
    BLSF = auto()  # Best Long Side Fit
    BAF = auto()  # Best Area Fit
    BL = auto()  # Bottom-Left
    CP = auto()  # Contact Point


class MaxRectsPacker:
    """
    MaxRects bin packing implementation.

    The algorithm maintains a list of maximal free rectangles. When a sprite
    is placed, any free rectangle that overlaps is split into up to 4 new
    rectangles. Redundant rectangles (fully contained in others) are pruned.
    """

    def __init__(self, heuristic: MaxRectsHeuristic = MaxRectsHeuristic.BSSF) -> None:
        """
        Initialize the MaxRects packer.

        Args:
            heuristic: Placement heuristic to use
        """
        self.bin_width: int = 0
        self.bin_height: int = 0
        self.allow_rotation: bool = True
        self.heuristic = heuristic
        self.free_rectangles: List[Dict[str, int]] = []
        self.used_rectangles: List[Dict[str, int]] = []
        self.root: Dict[str, int] = {"w": 0, "h": 0}

    def fit(
        self,
        blocks: List[Dict[str, Any]],
        width: int,
        height: int,
        allow_rotation: bool = True,
    ) -> bool:
        """
        Fit blocks into the provided bin.

        Args:
            blocks: List of blocks with 'w' and 'h' keys
            width: Bin width
            height: Bin height
            allow_rotation: Whether to allow 90-degree rotation

        Returns:
            True if all blocks were packed successfully
        """
        if width <= 0 or height <= 0:
            return False

        self.bin_width = width
        self.bin_height = height
        self.allow_rotation = allow_rotation
        self.root = {"w": width, "h": height}
        self.free_rectangles = [{"x": 0, "y": 0, "w": width, "h": height}]
        self.used_rectangles = []

        for block in blocks:
            placement = self._find_position_for_block(block)
            if placement is None:
                return False

            block["fit"] = placement
            self.used_rectangles.append(placement)
            self._split_free_rectangles(placement)
            self._prune_free_rectangles()

        return True

    def occupancy(self) -> float:
        """Calculate the ratio of used area to total bin area."""
        used_area = sum(rect["w"] * rect["h"] for rect in self.used_rectangles)
        total_area = self.bin_width * self.bin_height
        return used_area / total_area if total_area > 0 else 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _find_position_for_block(
        self, block: Dict[str, Any]
    ) -> Optional[Dict[str, int]]:
        """Find the best position for a block according to the heuristic."""
        best_node: Optional[Dict[str, int]] = None
        best_score: Tuple[float, float] = (float("inf"), float("inf"))
        block_w = block.get("w", 0)
        block_h = block.get("h", 0)
        prefer_rotate = bool(block.get("force_rotate")) and self.allow_rotation

        # Build list of orientations to try
        orientations = []
        if prefer_rotate:
            orientations.append((block_h, block_w, True))
            orientations.append((block_w, block_h, False))
        else:
            orientations.append((block_w, block_h, False))
            if self.allow_rotation:
                orientations.append((block_h, block_w, True))

        for rect in self.free_rectangles:
            for orient_w, orient_h, rotated in orientations:
                if orient_w <= rect["w"] and orient_h <= rect["h"]:
                    score = self._score_position(
                        rect, orient_w, orient_h, rotated, block
                    )
                    if score < best_score:
                        best_score = score
                        best_node = {
                            "x": rect["x"],
                            "y": rect["y"],
                            "w": orient_w,
                            "h": orient_h,
                            "rotated": rotated,
                        }

        if best_node and block.get("force_flip_y"):
            best_node["flip_y"] = True

        return best_node

    def _score_position(
        self,
        rect: Dict[str, int],
        width: int,
        height: int,
        rotated: bool,
        block: Dict[str, Any],
    ) -> Tuple[float, float]:
        """
        Score a potential placement (lower is better).

        Returns a tuple for tie-breaking: (primary_score, secondary_score)
        """
        leftover_h = rect["h"] - height
        leftover_w = rect["w"] - width

        # Mild penalty for rotations unless explicitly requested
        rotation_penalty = 0.1 if rotated and not block.get("force_rotate") else 0.0

        if self.heuristic == MaxRectsHeuristic.BSSF:
            # Best Short Side Fit - minimize the shorter leftover side
            short_side = min(leftover_w, leftover_h)
            long_side = max(leftover_w, leftover_h)
            return (short_side + rotation_penalty, long_side)

        elif self.heuristic == MaxRectsHeuristic.BLSF:
            # Best Long Side Fit - minimize the longer leftover side
            short_side = min(leftover_w, leftover_h)
            long_side = max(leftover_w, leftover_h)
            return (long_side + rotation_penalty, short_side)

        elif self.heuristic == MaxRectsHeuristic.BAF:
            # Best Area Fit - minimize leftover area
            leftover_area = leftover_w * rect["h"] + leftover_h * width
            short_side = min(leftover_w, leftover_h)
            return (leftover_area + rotation_penalty, short_side)

        elif self.heuristic == MaxRectsHeuristic.BL:
            # Bottom-Left - prefer positions with lower Y, then lower X
            return (rect["y"] + rotation_penalty, rect["x"])

        elif self.heuristic == MaxRectsHeuristic.CP:
            # Contact Point - maximize contact with bin edges and other rects
            contact = self._contact_point_score(rect["x"], rect["y"], width, height)
            # Negate because we want maximum contact but lower scores are better
            return (-contact + rotation_penalty, rect["y"])

        # Default to BSSF
        short_side = min(leftover_w, leftover_h)
        long_side = max(leftover_w, leftover_h)
        return (short_side + rotation_penalty, long_side)

    def _contact_point_score(self, x: int, y: int, w: int, h: int) -> int:
        """
        Calculate contact points for a rectangle placement.

        Contact points are pixels where the rectangle touches:
        - The bin boundaries
        - Other already-placed rectangles
        """
        contact = 0

        # Contact with bin edges
        if x == 0:
            contact += h  # Left edge
        if y == 0:
            contact += w  # Top edge
        if x + w == self.bin_width:
            contact += h  # Right edge
        if y + h == self.bin_height:
            contact += w  # Bottom edge

        # Contact with placed rectangles
        for used in self.used_rectangles:
            ux, uy, uw, uh = used["x"], used["y"], used["w"], used["h"]

            # Check horizontal adjacency
            if x == ux + uw or x + w == ux:
                # Vertical overlap
                y_overlap = min(y + h, uy + uh) - max(y, uy)
                if y_overlap > 0:
                    contact += y_overlap

            # Check vertical adjacency
            if y == uy + uh or y + h == uy:
                # Horizontal overlap
                x_overlap = min(x + w, ux + uw) - max(x, ux)
                if x_overlap > 0:
                    contact += x_overlap

        return contact

    def _split_free_rectangles(self, used_node: Dict[str, int]) -> None:
        """Split any free rectangles that overlap with the used node."""
        new_free: List[Dict[str, int]] = []

        for rect in self.free_rectangles:
            if not self._rects_intersect(rect, used_node):
                new_free.append(rect)
                continue

            # Split horizontally - left portion
            if used_node["x"] > rect["x"] and used_node["x"] < rect["x"] + rect["w"]:
                new_rect = rect.copy()
                new_rect["w"] = used_node["x"] - rect["x"]
                new_free.append(new_rect)

            # Split horizontally - right portion
            if used_node["x"] + used_node["w"] < rect["x"] + rect["w"]:
                new_rect = rect.copy()
                new_rect["x"] = used_node["x"] + used_node["w"]
                new_rect["w"] = (
                    rect["x"] + rect["w"] - (used_node["x"] + used_node["w"])
                )
                new_free.append(new_rect)

            # Split vertically - top portion
            if used_node["y"] > rect["y"] and used_node["y"] < rect["y"] + rect["h"]:
                new_rect = rect.copy()
                new_rect["h"] = used_node["y"] - rect["y"]
                new_free.append(new_rect)

            # Split vertically - bottom portion
            if used_node["y"] + used_node["h"] < rect["y"] + rect["h"]:
                new_rect = rect.copy()
                new_rect["y"] = used_node["y"] + used_node["h"]
                new_rect["h"] = (
                    rect["y"] + rect["h"] - (used_node["y"] + used_node["h"])
                )
                new_free.append(new_rect)

        self.free_rectangles = [r for r in new_free if r["w"] > 0 and r["h"] > 0]

    def _prune_free_rectangles(self) -> None:
        """Remove free rectangles that are fully contained within others."""
        i = 0
        while i < len(self.free_rectangles):
            j = i + 1
            rect_i = self.free_rectangles[i]
            removed = False
            while j < len(self.free_rectangles):
                rect_j = self.free_rectangles[j]
                if self._is_contained_in(rect_i, rect_j):
                    removed = True
                    break
                if self._is_contained_in(rect_j, rect_i):
                    del self.free_rectangles[j]
                    continue
                j += 1
            if removed:
                del self.free_rectangles[i]
            else:
                i += 1

    @staticmethod
    def _rects_intersect(a: Dict[str, int], b: Dict[str, int]) -> bool:
        """Check if two rectangles intersect."""
        return not (
            a["x"] >= b["x"] + b["w"]
            or a["x"] + a["w"] <= b["x"]
            or a["y"] >= b["y"] + b["h"]
            or a["y"] + a["h"] <= b["y"]
        )

    @staticmethod
    def _is_contained_in(inner: Dict[str, int], outer: Dict[str, int]) -> bool:
        """Check if inner rectangle is fully contained in outer rectangle."""
        return (
            inner["x"] >= outer["x"]
            and inner["y"] >= outer["y"]
            and inner["x"] + inner["w"] <= outer["x"] + outer["w"]
            and inner["y"] + inner["h"] <= outer["y"] + outer["h"]
        )
