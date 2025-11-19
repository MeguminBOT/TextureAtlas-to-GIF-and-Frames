#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MaxRects bin packing implementation used for advanced sprite packing."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


class MaxRectsPacker:
    """Reference MaxRects implementation with light rotation heuristics."""

    def __init__(self) -> None:
        self.bin_width: int = 0
        self.bin_height: int = 0
        self.allow_rotation: bool = True
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
        """Fit blocks into the provided bin returning True on success."""

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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _find_position_for_block(self, block: Dict[str, Any]) -> Optional[Dict[str, int]]:
        best_node: Optional[Dict[str, int]] = None
        best_score: Tuple[float, float] = (float("inf"), float("inf"))
        block_w = block.get("w", 0)
        block_h = block.get("h", 0)
        prefer_rotate = bool(block.get("force_rotate")) and self.allow_rotation

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
                    score = self._score_position(rect, orient_w, orient_h, rotated, block)
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
        leftover_h = rect["h"] - height
        leftover_w = rect["w"] - width
        short_side_fit = min(leftover_w, leftover_h)
        long_side_fit = max(leftover_w, leftover_h)
        # Mild penalty for rotations unless explicitly requested
        rotation_penalty = 0.1 if rotated and not block.get("force_rotate") else 0.0
        return short_side_fit + rotation_penalty, long_side_fit

    def _split_free_rectangles(self, used_node: Dict[str, int]) -> None:
        new_free: List[Dict[str, int]] = []

        for rect in self.free_rectangles:
            if not self._rects_intersect(rect, used_node):
                new_free.append(rect)
                continue

            # Split horizontally
            if used_node["x"] > rect["x"] and used_node["x"] < rect["x"] + rect["w"]:
                new_rect = rect.copy()
                new_rect["w"] = used_node["x"] - rect["x"]
                new_free.append(new_rect)

            if used_node["x"] + used_node["w"] < rect["x"] + rect["w"]:
                new_rect = rect.copy()
                new_rect["x"] = used_node["x"] + used_node["w"]
                new_rect["w"] = rect["x"] + rect["w"] - (used_node["x"] + used_node["w"])
                new_free.append(new_rect)

            # Split vertically
            if used_node["y"] > rect["y"] and used_node["y"] < rect["y"] + rect["h"]:
                new_rect = rect.copy()
                new_rect["h"] = used_node["y"] - rect["y"]
                new_free.append(new_rect)

            if used_node["y"] + used_node["h"] < rect["y"] + rect["h"]:
                new_rect = rect.copy()
                new_rect["y"] = used_node["y"] + used_node["h"]
                new_rect["h"] = rect["y"] + rect["h"] - (used_node["y"] + used_node["h"])
                new_free.append(new_rect)

        self.free_rectangles = [r for r in new_free if r["w"] > 0 and r["h"] > 0]

    def _prune_free_rectangles(self) -> None:
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
        return not (
            a["x"] >= b["x"] + b["w"]
            or a["x"] + a["w"] <= b["x"]
            or a["y"] >= b["y"] + b["h"]
            or a["y"] + a["h"] <= b["y"]
        )

    @staticmethod
    def _is_contained_in(inner: Dict[str, int], outer: Dict[str, int]) -> bool:
        return (
            inner["x"] >= outer["x"]
            and inner["y"] >= outer["y"]
            and inner["x"] + inner["w"] <= outer["x"] + outer["w"]
            and inner["y"] + inner["h"] <= outer["y"] + outer["h"]
        )
