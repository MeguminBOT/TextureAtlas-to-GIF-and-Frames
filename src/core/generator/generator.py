#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Texture atlas generation with configurable packing algorithms.

Provides the SparrowAtlasGenerator class for packing sprite frames into a
single atlas image and emitting a Sparrow-format XML manifest. Supports
multiple packing strategies (grid, growing, ordered, maxrects, guillotine,
shelf, skyline) selectable via AtlasSettings.algorithm_hint.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image, ImageOps
import numpy as np
import re
from typing import List, Dict, Tuple, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import time

# Import our own modules
from packers import (
    GrowingPacker,
    OrderedPacker,
    MaxRectsPacker,
    MaxRectsHeuristic,
    HybridAdaptivePacker,
    GuillotinePacker,
    GuillotinePlacement,
    GuillotineSplit,
    ShelfPackerDecreasingHeight,
    ShelfHeuristic,
    SkylinePacker,
    SkylineHeuristic,
    find_optimal_size,
    next_power_of_2,
)


class PackingAlgorithm(Enum):
    """Enumerate the heuristics the atlas builder can use for layout."""

    NONE = 0  # No optimization - simple grid
    GROWING_PACKER = 1  # Growing packer (dynamically expands)
    ORDERED_PACKER = 2  # Ordered packer (preserves order)
    MAXRECTS_PACKER = 3  # MaxRects with Best-Short-Side-Fit
    HYBRID_PACKER = 4  # Hybrid adaptive packer
    GUILLOTINE_PACKER = 5  # Guillotine bin packing
    SHELF_PACKER = 6  # Shelf bin packing (FFDH)
    SKYLINE_PACKER = 7  # Skyline bin packing


@dataclass
class Frame:
    """Snapshot of a trimmed sprite plus metadata needed for packing."""

    name: str
    image_path: str
    width: int
    height: int
    x: int = 0
    y: int = 0
    rotated: bool = False
    flip_y: bool = False
    # Original frame dimensions before trimming
    original_width: int = 0
    original_height: int = 0
    # Offset from original frame origin
    frame_x: int = 0
    frame_y: int = 0
    # Trimmed dimensions (actual sprite content)
    trimmed_width: int = 0
    trimmed_height: int = 0

    @property
    def area(self) -> int:
        """Total pixel count of the frame."""
        return self.width * self.height

    @property
    def perimeter(self) -> int:
        """Sum of width and height times two."""
        return 2 * (self.width + self.height)


@dataclass
class AtlasSettings:
    """User-facing knobs controlling atlas size, padding, and heuristics."""

    max_size: int = 2048
    min_size: int = 128
    padding: int = 2
    power_of_2: bool = True
    optimization_level: int = 5
    allow_rotation: bool = True
    algorithm_hint: Optional[str] = None
    heuristic_hint: Optional[str] = None  # Algorithm-specific heuristic key
    optimization_mode_index: int = 0
    allow_vertical_flip: bool = False
    preferred_width: Optional[int] = None
    preferred_height: Optional[int] = None
    forced_width: Optional[int] = None
    forced_height: Optional[int] = None

    @property
    def algorithm(self) -> PackingAlgorithm:
        """Get packing algorithm based on optimization level."""
        hint = (self.algorithm_hint or "growing").lower()
        hint_map = {
            "grid": PackingAlgorithm.NONE,
            "growing": PackingAlgorithm.GROWING_PACKER,
            "ordered": PackingAlgorithm.ORDERED_PACKER,
            "maxrects": PackingAlgorithm.MAXRECTS_PACKER,
            "hybrid": PackingAlgorithm.HYBRID_PACKER,
            "guillotine": PackingAlgorithm.GUILLOTINE_PACKER,
            "shelf": PackingAlgorithm.SHELF_PACKER,
            "skyline": PackingAlgorithm.SKYLINE_PACKER,
        }
        return hint_map.get(hint, PackingAlgorithm.GROWING_PACKER)

    @property
    def allow_flip(self) -> bool:
        """Whether vertical flipping is permitted during packing."""
        if self.algorithm_hint:
            return self.allow_vertical_flip
        return self.allow_vertical_flip or self.optimization_level >= 9

    @property
    def maxrects_heuristic(self) -> MaxRectsHeuristic:
        """Get MaxRects heuristic from hint string."""
        hint = (self.heuristic_hint or "bssf").lower()
        mapping = {
            "bssf": MaxRectsHeuristic.BSSF,
            "blsf": MaxRectsHeuristic.BLSF,
            "baf": MaxRectsHeuristic.BAF,
            "bl": MaxRectsHeuristic.BL,
            "cp": MaxRectsHeuristic.CP,
        }
        return mapping.get(hint, MaxRectsHeuristic.BSSF)

    @property
    def guillotine_placement(self) -> GuillotinePlacement:
        """Get Guillotine placement heuristic from hint string."""
        hint = (self.heuristic_hint or "baf").lower()
        mapping = {
            "bssf": GuillotinePlacement.BSSF,
            "blsf": GuillotinePlacement.BLSF,
            "baf": GuillotinePlacement.BAF,
            "waf": GuillotinePlacement.WAF,
        }
        return mapping.get(hint, GuillotinePlacement.BAF)

    @property
    def shelf_heuristic(self) -> ShelfHeuristic:
        """Get Shelf heuristic from hint string."""
        hint = (self.heuristic_hint or "best_height").lower()
        mapping = {
            "next_fit": ShelfHeuristic.NEXT_FIT,
            "first_fit": ShelfHeuristic.FIRST_FIT,
            "best_width": ShelfHeuristic.BEST_WIDTH_FIT,
            "best_height": ShelfHeuristic.BEST_HEIGHT_FIT,
            "worst_width": ShelfHeuristic.WORST_WIDTH_FIT,
        }
        return mapping.get(hint, ShelfHeuristic.BEST_HEIGHT_FIT)

    @property
    def skyline_heuristic(self) -> SkylineHeuristic:
        """Get Skyline heuristic from hint string."""
        hint = (self.heuristic_hint or "min_waste").lower()
        mapping = {
            "bottom_left": SkylineHeuristic.BOTTOM_LEFT,
            "min_waste": SkylineHeuristic.MIN_WASTE,
            "best_fit": SkylineHeuristic.BEST_FIT,
        }
        return mapping.get(hint, SkylineHeuristic.MIN_WASTE)


class Rectangle:
    """Lightweight rectangle helper used by the packing simulators."""

    def __init__(self, x: int, y: int, width: int, height: int):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    @property
    def right(self) -> int:
        """X-coordinate of the right edge."""
        return self.x + self.width

    @property
    def bottom(self) -> int:
        """Y-coordinate of the bottom edge."""
        return self.y + self.height

    @property
    def area(self) -> int:
        """Total pixel count of the rectangle."""
        return self.width * self.height

    def intersects(self, other: "Rectangle") -> bool:
        """Return True when two rectangles overlap in 2D space."""
        return not (
            self.right <= other.x
            or other.right <= self.x
            or self.bottom <= other.y
            or other.bottom <= self.y
        )


class SparrowAtlasGenerator:
    """Pack sprite frames into a texture atlas with metadata output.

    Supports multiple packing algorithms (grid, growing, maxrects, etc.)
    and emits metadata in various formats via MetadataWriter.

    Attributes:
        progress_callback: Optional callable receiving (current, total, message).
        frames: List of Frame objects populated after loading.
    """

    def __init__(self, progress_callback: Optional[Callable] = None) -> None:
        """Initialize the generator.

        Args:
            progress_callback: Optional callable for progress updates.
        """
        self.progress_callback = progress_callback
        self.frames: List[Frame] = []

    def generate_atlas(
        self,
        animation_groups: Dict[str, List[str]],
        output_path: str,
        settings: AtlasSettings,
        current_version: str,
        output_format: str = "starling-xml",
    ) -> Dict:
        """Pack frames, render the atlas bitmap, and emit metadata.

        Args:
            animation_groups (dict[str, list[str]]): Mapping of animation names to
                ordered frame paths.
            output_path (str): Destination prefix for the PNG/metadata pair.
            settings (AtlasSettings): Packing heuristics and canvas constraints.
            current_version (str): App version recorded in the metadata.
            output_format (str): Metadata format key (e.g., "starling-xml",
                "json-hash", "spine"). Defaults to "starling-xml".

        Returns:
            dict: Result payload describing success, file paths, and stats.
        """
        start_time = time.time()

        try:
            # Check if the output format supports rotation/flip; disable if not
            from core.generator.metadata_writer import MetadataWriter

            if not MetadataWriter.supports_rotation(output_format):
                settings.allow_rotation = False
            if not MetadataWriter.supports_flip(output_format):
                settings.allow_vertical_flip = False

            # Step 1: Load and prepare frames
            self._update_progress(0, 5, "Loading frames...")
            self._load_frames(animation_groups)

            if not self.frames:
                return {"success": False, "error": "No frames to pack"}

            # Step 2: Sort frames for optimal packing
            self._update_progress(1, 5, "Sorting frames...")
            self._sort_frames(settings)

            # Step 3: Calculate optimal atlas size
            self._update_progress(2, 5, "Calculating atlas size...")
            atlas_width, atlas_height = self._calculate_atlas_size(settings)

            # Step 4: Pack frames into atlas
            self._update_progress(3, 5, "Packing frames...")
            if not self._pack_frames(atlas_width, atlas_height, settings):
                return {"success": False, "error": "Could not fit all frames in atlas"}

            # Step 5: Generate output files
            self._update_progress(4, 5, "Generating output...")
            atlas_image = self._create_atlas_image(atlas_width, atlas_height)

            # Save atlas image
            image_path = f"{output_path}.png"
            atlas_image.save(image_path, "PNG")

            # Generate metadata using MetadataWriter for format flexibility
            from core.generator.metadata_writer import MetadataWriter

            writer = MetadataWriter(self.frames, atlas_width, atlas_height)
            image_name = Path(image_path).name
            metadata_path = writer.write_metadata(
                output_path,
                output_format,
                image_name=image_name,
                version=current_version,
                pretty_print=True,
            )

            self._update_progress(5, 5, "Complete!")

            generation_time = time.time() - start_time

            return {
                "success": True,
                "atlas_path": image_path,
                "xml_path": metadata_path,  # Keep for backward compat
                "metadata_path": metadata_path,
                "atlas_size": (atlas_width, atlas_height),
                "frame_count": len(self.frames),
                "frames_count": len(self.frames),
                "generation_time": generation_time,
                "efficiency": self._calculate_efficiency(atlas_width, atlas_height),
                "metadata_files": [metadata_path],
                "output_format": output_format,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _load_frames(self, animation_groups: Dict[str, List[str]]):
        """Read every frame image and capture trimmed bounds plus metadata.

        Args:
            animation_groups (dict[str, list[str]]): Mapping of animation names
                to frame file paths in draw order.
        """
        self.frames = []

        for animation_name, frame_paths in animation_groups.items():
            for i, frame_path in enumerate(frame_paths):
                try:
                    with Image.open(frame_path) as img:
                        # Store original dimensions
                        original_width, original_height = img.width, img.height

                        # Trim whitespace to get actual content bounds
                        trimmed_bounds = self._get_trim_bounds(img)
                        if trimmed_bounds:
                            left, top, right, bottom = trimmed_bounds
                            trimmed_width = right - left
                            trimmed_height = bottom - top
                            frame_x = left
                            frame_y = top
                        else:
                            # No trimming needed - image is fully opaque
                            trimmed_width = original_width
                            trimmed_height = original_height
                            frame_x = 0
                            frame_y = 0
                            left, top = 0, 0

                        frame_name = f"{animation_name}{i:04d}"
                        frame = Frame(
                            name=frame_name,
                            image_path=frame_path,
                            width=trimmed_width,  # Use trimmed dimensions for packing
                            height=trimmed_height,
                            original_width=original_width,
                            original_height=original_height,
                            frame_x=frame_x,
                            frame_y=frame_y,
                            trimmed_width=trimmed_width,
                            trimmed_height=trimmed_height,
                        )
                        # Store trim bounds for later use in atlas creation
                        frame._trim_bounds = (
                            left,
                            top,
                            left + trimmed_width,
                            top + trimmed_height,
                        )
                        self.frames.append(frame)
                except Exception as e:
                    print(f"Error loading frame {frame_path}: {e}")
                    continue

    def _sort_frames(self, settings: AtlasSettings):
        """Sort frames for optimal packing based on selected algorithm and mode."""
        mode = max(0, settings.optimization_mode_index)
        algorithm = settings.algorithm

        if algorithm == PackingAlgorithm.NONE:
            # Grid mode keeps incoming order for compatibility
            return

        if algorithm == PackingAlgorithm.GROWING_PACKER:
            if mode == 0:
                return  # fastest path, preserve import order
            if mode == 1:
                self.frames.sort(key=lambda f: f.height, reverse=True)
            else:
                self.frames.sort(
                    key=lambda f: (max(f.width, f.height), f.area), reverse=True
                )
            return

        if algorithm == PackingAlgorithm.ORDERED_PACKER:
            if mode == 0:
                return
            self.frames.sort(key=lambda f: (f.height, f.width), reverse=True)
            return

        if algorithm in (
            PackingAlgorithm.MAXRECTS_PACKER,
            PackingAlgorithm.HYBRID_PACKER,
            PackingAlgorithm.GUILLOTINE_PACKER,
            PackingAlgorithm.SHELF_PACKER,
            PackingAlgorithm.SKYLINE_PACKER,
        ):
            if mode <= 1:
                self.frames.sort(key=lambda f: f.area, reverse=True)
            else:
                self.frames.sort(
                    key=lambda f: (max(f.width, f.height), f.area), reverse=True
                )
            return

        # Default fallback: prefer area sorting for any future algorithm types
        self.frames.sort(key=lambda f: f.area, reverse=True)

    def _calculate_atlas_size(self, settings: AtlasSettings) -> Tuple[int, int]:
        """Determine which sizing helper to use based on the active algorithm.

        Args:
            settings (AtlasSettings): Includes ``algorithm`` and size limits.

        Returns:
            Tuple[int, int]: Width and height that a downstream packer should
                consume.
        """
        if settings.algorithm == PackingAlgorithm.NONE:
            # Grid packing needs pre-calculated dimensions
            return self._calculate_grid_size(settings)
        elif settings.algorithm == PackingAlgorithm.GROWING_PACKER:
            # Growing packer determines its own optimal size
            return self._get_growing_packer_size(settings)
        elif settings.algorithm == PackingAlgorithm.ORDERED_PACKER:
            # Ordered packer determines its own optimal size
            return self._get_ordered_packer_size(settings)
        elif settings.algorithm == PackingAlgorithm.MAXRECTS_PACKER:
            return self._get_maxrects_packer_size(settings)
        elif settings.algorithm == PackingAlgorithm.HYBRID_PACKER:
            return self._get_hybrid_packer_size(settings)
        elif settings.algorithm == PackingAlgorithm.GUILLOTINE_PACKER:
            return self._get_guillotine_packer_size(settings)
        elif settings.algorithm == PackingAlgorithm.SHELF_PACKER:
            return self._get_shelf_packer_size(settings)
        elif settings.algorithm == PackingAlgorithm.SKYLINE_PACKER:
            return self._get_skyline_packer_size(settings)
        else:
            # Default to growing packer
            return self._get_growing_packer_size(settings)

    def _calculate_grid_size(self, settings: AtlasSettings) -> Tuple[int, int]:
        """Simulate a naïve grid and return the most compact rectangular canvas.

        Args:
            settings (AtlasSettings): Provides padding, power-of-two policy, and
                canvas limits.

        Returns:
            Tuple[int, int]: Width and height that can accommodate every frame
                when placed in the computed rows/columns.
        """
        if not self.frames:
            return settings.min_size, settings.min_size

        # Calculate frame dimensions
        max_width = max(f.width for f in self.frames)
        max_height = max(f.height for f in self.frames)
        frame_count = len(self.frames)

        # Calculate cell dimensions with padding
        cell_width = max_width + settings.padding * 2
        cell_height = max_height + settings.padding * 2

        # Try different grid arrangements to find the most compact
        best_area = float("inf")
        best_width, best_height = 0, 0

        # Try various grid configurations
        for cols in range(
            1, min(frame_count + 1, 20)
        ):  # Limit to reasonable number of columns
            rows = int(np.ceil(frame_count / cols))

            grid_width = cols * cell_width
            grid_height = rows * cell_height

            # Apply power of 2 constraint if needed
            if settings.power_of_2:
                grid_width = self._next_power_of_2(grid_width)
                grid_height = self._next_power_of_2(grid_height)

            # Clamp to size limits
            grid_width = min(max(grid_width, settings.min_size), settings.max_size)
            grid_height = min(max(grid_height, settings.min_size), settings.max_size)

            # Check if this arrangement is better (smaller total area)
            total_area = grid_width * grid_height
            if total_area < best_area:
                best_area = total_area
                best_width, best_height = grid_width, grid_height

        return best_width, best_height

    def _get_growing_packer_size(self, settings: AtlasSettings) -> Tuple[int, int]:
        """Dry-run the growing packer to learn the required canvas bounds.

        Args:
            settings (AtlasSettings): In-progress atlas configuration that stores
                intermediate packing results.

        Returns:
            Tuple[int, int]: Width and height that safely contain every frame
                when packed with the growing heuristic.
        """
        if not self.frames:
            return settings.min_size, settings.min_size

        # Convert frames to blocks format
        blocks = []
        for frame in self.frames:
            blocks.append(
                {
                    "w": frame.width + settings.padding * 2,
                    "h": frame.height + settings.padding * 2,
                }
            )

        # Sort blocks by height (largest first) for better packing
        blocks.sort(key=lambda b: b["h"], reverse=True)

        # Use growing packer to determine optimal size
        packer = GrowingPacker()
        packer.fit(blocks)

        # Get the final dimensions from the packer
        width = packer.root["w"] if packer.root else settings.min_size
        height = packer.root["h"] if packer.root else settings.min_size

        # Apply power of 2 constraint if needed
        if settings.power_of_2:
            width = self._next_power_of_2(width)
            height = self._next_power_of_2(height)

        # Clamp to size limits
        width = min(max(width, settings.min_size), settings.max_size)
        height = min(max(height, settings.min_size), settings.max_size)

        return width, height

    def _build_blocks_for_advanced_packers(
        self, settings: AtlasSettings, include_frame: bool = False
    ) -> List[Dict[str, object]]:
        """Build block dicts for packing algorithms.

        Args:
            settings: Atlas settings with padding and mode hints.
            include_frame: Attach Frame reference to each block if True.

        Returns:
            List of block dicts sorted by max dimension descending.
        """
        pad = settings.padding * 2
        blocks: List[Dict[str, object]] = []

        for frame in self.frames:
            block: Dict[str, object] = {
                "w": frame.width + pad,
                "h": frame.height + pad,
                "id": frame.name,
            }
            if include_frame:
                block["frame"] = frame
            self._apply_mode_hints(block, settings)
            blocks.append(block)

        blocks.sort(key=lambda b: max(b["w"], b["h"]), reverse=True)
        return blocks

    def _apply_mode_hints(
        self, block: Dict[str, object], settings: AtlasSettings
    ) -> None:
        """Annotate a block with rotation/flip hints based on optimization mode.

        Args:
            block: Mutable block dict to update in place.
            settings: Atlas settings controlling mode behavior.
        """
        if not settings.algorithm_hint:
            return

        algorithm = settings.algorithm
        mode = settings.optimization_mode_index

        if algorithm == PackingAlgorithm.MAXRECTS_PACKER:
            width = block.get("w", 0)
            height = block.get("h", 0)
            aspect = width / height if height else 1.0

            if mode >= 2 and settings.allow_rotation:
                # Encourage rotating tall sprites to free columns when running tight
                if aspect < 0.85:
                    block["force_rotate"] = True
                else:
                    block.pop("force_rotate", None)

            if mode >= 3 and settings.allow_flip:
                block["force_flip_y"] = height > width and height - width > 8
            else:
                block.pop("force_flip_y", None)

        elif algorithm == PackingAlgorithm.HYBRID_PACKER:
            if mode == 0:
                block.pop("force_rotate", None)
                block.pop("force_flip_y", None)
            elif mode >= 2 and settings.allow_flip:
                height = block.get("h", 0)
                width = block.get("w", 0)
                block["force_flip_y"] = height > width * 1.05

    def _generate_candidate_bins(
        self, settings: AtlasSettings
    ) -> List[Tuple[int, int]]:
        """Build candidate atlas sizes for binary search.

        Args:
            settings: Atlas settings with size constraints.

        Returns:
            List of (width, height) tuples sorted by area ascending.
        """
        if not self.frames:
            return [(settings.min_size, settings.min_size)]

        candidates: List[Tuple[int, int]] = []

        def register(width: int, height: int) -> None:
            width = int(min(max(width, settings.min_size), settings.max_size))
            height = int(min(max(height, settings.min_size), settings.max_size))
            if settings.power_of_2:
                width = self._next_power_of_2(width)
                height = self._next_power_of_2(height)
            candidate = (width, height)
            if candidate not in candidates:
                candidates.append(candidate)

        if settings.forced_width and settings.forced_height:
            register(settings.forced_width, settings.forced_height)

        if settings.preferred_width and settings.preferred_height:
            register(settings.preferred_width, settings.preferred_height)

        pad = settings.padding * 2
        max_dim = max(max(frame.width, frame.height) + pad for frame in self.frames)
        register(max_dim, max_dim)

        total_area = sum(
            (frame.width + pad) * (frame.height + pad) for frame in self.frames
        )
        square_side = int(np.ceil(np.sqrt(total_area)))
        register(square_side, square_side)

        side = max_dim
        while side < settings.max_size:
            side *= 2
            register(side, side)
            register(side * 2, side)
            register(side, side * 2)

        candidates.sort(key=lambda dims: dims[0] * dims[1])
        return candidates

    def _search_size_with_packer(
        self,
        settings: AtlasSettings,
        packer_cls,
        allow_flip: bool = False,
    ) -> Tuple[int, int]:
        """Find the smallest bin that fits all frames.

        Args:
            settings: Atlas settings with size constraints.
            packer_cls: Packer class with a fit() method.
            allow_flip: Pass flip permission to hybrid packer.

        Returns:
            Tuple of (width, height) for the smallest successful bin.
        """
        blocks = self._build_blocks_for_advanced_packers(settings, include_frame=False)
        if not blocks:
            return settings.min_size, settings.min_size

        candidates = self._generate_candidate_bins(settings)
        best_dims = candidates[-1]

        for width, height in candidates:
            trial_blocks = [dict(block) for block in blocks]
            packer = packer_cls()
            if isinstance(packer, HybridAdaptivePacker):
                success = packer.fit(
                    trial_blocks,
                    width,
                    height,
                    allow_rotation=settings.allow_rotation,
                    allow_flip=allow_flip,
                )
            else:
                success = packer.fit(
                    trial_blocks,
                    width,
                    height,
                    allow_rotation=settings.allow_rotation,
                )

            if success:
                best_dims = (width, height)
                break

        return best_dims

    def _get_maxrects_packer_size(self, settings: AtlasSettings) -> Tuple[int, int]:
        """Estimate atlas size using MaxRects packer."""
        return self._search_size_with_packer(settings, MaxRectsPacker)

    def _get_hybrid_packer_size(self, settings: AtlasSettings) -> Tuple[int, int]:
        """Estimate atlas size using Hybrid adaptive packer."""
        return self._search_size_with_packer(
            settings, HybridAdaptivePacker, allow_flip=settings.allow_flip
        )

    def _get_guillotine_packer_size(self, settings: AtlasSettings) -> Tuple[int, int]:
        """Estimate atlas size using Guillotine packer."""
        return self._get_optimal_size_with_binary_search(settings, "guillotine")

    def _get_shelf_packer_size(self, settings: AtlasSettings) -> Tuple[int, int]:
        """Estimate atlas size using Shelf packer."""
        return self._get_optimal_size_with_binary_search(settings, "shelf")

    def _get_skyline_packer_size(self, settings: AtlasSettings) -> Tuple[int, int]:
        """Estimate atlas size using Skyline packer."""
        return self._get_optimal_size_with_binary_search(settings, "skyline")

    def _get_optimal_size_with_binary_search(
        self, settings: AtlasSettings, packer_type: str
    ) -> Tuple[int, int]:
        """Use binary search to find the optimal atlas size for new packers.

        Args:
            settings: Atlas settings with size constraints
            packer_type: One of 'guillotine', 'shelf', 'skyline'

        Returns:
            Optimal (width, height) tuple
        """
        if not self.frames:
            return settings.min_size, settings.min_size

        pad = settings.padding * 2
        frames = [(f.width + pad, f.height + pad, f) for f in self.frames]

        # Create a packer test function
        def try_pack(width: int, height: int) -> bool:
            if packer_type == "guillotine":
                packer = GuillotinePacker(
                    width,
                    height,
                    placement=settings.guillotine_placement,
                    allow_rotation=settings.allow_rotation,
                    padding=0,  # Padding already added to frame dims
                )
                pack_input = [(w, h, data) for w, h, data in frames]
                result = packer.pack(pack_input)
                return len(result) == len(frames)

            elif packer_type == "shelf":
                packer = ShelfPackerDecreasingHeight(
                    width,
                    height,
                    heuristic=settings.shelf_heuristic,
                    allow_rotation=settings.allow_rotation,
                    padding=0,
                )
                pack_input = [(w, h, data) for w, h, data in frames]
                result = packer.pack(pack_input)
                return len(result) == len(frames)

            elif packer_type == "skyline":
                packer = SkylinePacker(
                    width,
                    height,
                    heuristic=settings.skyline_heuristic,
                    allow_rotation=settings.allow_rotation,
                    padding=0,
                )
                pack_input = [(w, h, data) for w, h, data in frames]
                result = packer.pack(pack_input)
                return len(result) == len(frames)

            return False

        # Use find_optimal_size from our optimizer
        result = find_optimal_size(
            frames,
            try_pack,
            min_size=settings.min_size,
            max_size=settings.max_size,
            padding=0,  # Already included in frames
            power_of_2=settings.power_of_2,
            fixed_width=settings.forced_width,
            fixed_height=settings.forced_height,
        )

        return result.width, result.height

    def _get_ordered_packer_size(self, settings: AtlasSettings) -> Tuple[int, int]:
        """Dry-run the ordered packer to estimate canvas bounds.

        Args:
            settings (AtlasSettings): Atlas constraints and padding rules.

        Returns:
            Tuple[int, int]: Width and height that honor the frame order while
                fitting within the selected limits.
        """
        if not self.frames:
            return settings.min_size, settings.min_size

        # Convert frames to blocks format
        blocks = []
        for frame in self.frames:
            blocks.append(
                {
                    "w": frame.width + settings.padding * 2,
                    "h": frame.height + settings.padding * 2,
                }
            )

        # Use ordered packer to determine optimal size
        packer = OrderedPacker()
        packer.fit(blocks)

        # Get the final dimensions from the packer
        width = packer.root["w"] if packer.root else settings.min_size
        height = packer.root["h"] if packer.root else settings.min_size

        # Apply power of 2 constraint if needed
        if settings.power_of_2:
            width = self._next_power_of_2(width)
            height = self._next_power_of_2(height)

        # Clamp to size limits
        width = min(max(width, settings.min_size), settings.max_size)
        height = min(max(height, settings.min_size), settings.max_size)

        return width, height

    def _pack_growing(
        self, atlas_width: int, atlas_height: int, settings: AtlasSettings
    ) -> bool:
        """Pack frames with the growing heuristic that can expand on demand.

        Args:
            atlas_width (int): Width of the destination canvas; unused but kept
                for signature parity.
            atlas_height (int): Height of the destination canvas; unused but
                kept for signature parity.
            settings (AtlasSettings): Padding and rotation configuration that
                mirrors the eventual render pass.

        Returns:
            bool: ``True`` when every frame receives coordinates; ``False`` if
                the simulated packer fails to place a block.
        """
        if not self.frames:
            return True

        # Convert frames to blocks format expected by GrowingPacker
        blocks = []
        for frame in self.frames:
            blocks.append(
                {
                    "w": frame.width + settings.padding * 2,
                    "h": frame.height + settings.padding * 2,
                    "frame": frame,
                }
            )

        # Sort blocks by height (largest first) for better packing
        blocks.sort(key=lambda b: b["h"], reverse=True)

        # Use growing packer
        packer = GrowingPacker()
        packer.fit(blocks)

        # Set frame positions (accounting for padding)
        for block in blocks:
            fit = block.get("fit")
            if not fit:
                return False

            frame = block["frame"]
            frame.x = fit["x"] + settings.padding
            frame.y = fit["y"] + settings.padding
            frame.rotated = False
            frame.flip_y = False

        return True

    def _pack_ordered(
        self, atlas_width: int, atlas_height: int, settings: AtlasSettings
    ) -> bool:
        """Pack frames in list order while staying within the target bounds.

        Args:
            atlas_width (int): Width that the ordered packer should respect.
            atlas_height (int): Height that the ordered packer should respect.
            settings (AtlasSettings): Padding rules and rotation flag mirrored
                from the UI settings.

        Returns:
            bool: ``True`` if every frame receives a slot; ``False`` otherwise.
        """
        if not self.frames:
            return True

        # Convert frames to blocks format expected by OrderedPacker
        blocks = []
        for frame in self.frames:
            blocks.append(
                {
                    "w": frame.width + settings.padding * 2,
                    "h": frame.height + settings.padding * 2,
                    "frame": frame,
                }
            )

        # Use ordered packer
        packer = OrderedPacker()
        packer.fit(blocks)

        # Set frame positions (accounting for padding)
        for block in blocks:
            fit = block.get("fit")
            if not fit:
                return False

            frame = block["frame"]
            frame.x = fit["x"] + settings.padding
            frame.y = fit["y"] + settings.padding

            # Ordered packer never rotates or flips
            frame.rotated = False
            frame.flip_y = False

        return True

    def _pack_maxrects(
        self, atlas_width: int, atlas_height: int, settings: AtlasSettings
    ) -> bool:
        """Pack frames using the MaxRects algorithm.

        Args:
            atlas_width: Target canvas width.
            atlas_height: Target canvas height.
            settings: Atlas configuration with heuristic selection.

        Returns:
            True if all frames were placed successfully.
        """
        if not self.frames:
            return True

        blocks = self._build_blocks_for_advanced_packers(settings, include_frame=True)
        packer = MaxRectsPacker(heuristic=settings.maxrects_heuristic)
        success = packer.fit(
            blocks,
            atlas_width,
            atlas_height,
            allow_rotation=settings.allow_rotation,
        )

        if not success:
            return False

        return self._apply_block_positions(blocks, settings)

    def _pack_hybrid(
        self, atlas_width: int, atlas_height: int, settings: AtlasSettings
    ) -> bool:
        """Pack frames using the Hybrid adaptive algorithm.

        Args:
            atlas_width: Target canvas width.
            atlas_height: Target canvas height.
            settings: Atlas configuration with flip permission.

        Returns:
            True if all frames were placed successfully.
        """
        if not self.frames:
            return True

        blocks = self._build_blocks_for_advanced_packers(settings, include_frame=True)
        packer = HybridAdaptivePacker()
        success = packer.fit(
            blocks,
            atlas_width,
            atlas_height,
            allow_rotation=settings.allow_rotation,
            allow_flip=settings.allow_flip,
        )

        if not success:
            return False

        return self._apply_block_positions(blocks, settings)

    def _pack_guillotine(
        self, atlas_width: int, atlas_height: int, settings: AtlasSettings
    ) -> bool:
        """Pack frames using the Guillotine bin packing algorithm.

        Args:
            atlas_width: Target canvas width
            atlas_height: Target canvas height
            settings: Atlas configuration

        Returns:
            True if packing succeeded
        """
        if not self.frames:
            return True

        pad = settings.padding * 2
        pack_input = [(f.width + pad, f.height + pad, f) for f in self.frames]

        packer = GuillotinePacker(
            atlas_width,
            atlas_height,
            placement=settings.guillotine_placement,
            allow_rotation=settings.allow_rotation,
            padding=0,  # Padding already in dims
        )

        results = packer.pack(pack_input)
        if len(results) != len(self.frames):
            return False

        # Apply positions to frames
        for x, y, w, h, rotated, frame in results:
            frame.x = x + settings.padding
            frame.y = y + settings.padding
            frame.rotated = rotated
            frame.flip_y = False

        return True

    def _pack_shelf(
        self, atlas_width: int, atlas_height: int, settings: AtlasSettings
    ) -> bool:
        """Pack frames using the Shelf bin packing algorithm (FFDH variant).

        Args:
            atlas_width: Target canvas width
            atlas_height: Target canvas height
            settings: Atlas configuration

        Returns:
            True if packing succeeded
        """
        if not self.frames:
            return True

        pad = settings.padding * 2
        pack_input = [(f.width + pad, f.height + pad, f) for f in self.frames]

        packer = ShelfPackerDecreasingHeight(
            atlas_width,
            atlas_height,
            heuristic=settings.shelf_heuristic,
            allow_rotation=settings.allow_rotation,
            padding=0,
        )

        results = packer.pack(pack_input)
        if len(results) != len(self.frames):
            return False

        for x, y, w, h, rotated, frame in results:
            frame.x = x + settings.padding
            frame.y = y + settings.padding
            frame.rotated = rotated
            frame.flip_y = False

        return True

    def _pack_skyline(
        self, atlas_width: int, atlas_height: int, settings: AtlasSettings
    ) -> bool:
        """Pack frames using the Skyline bin packing algorithm.

        Args:
            atlas_width: Target canvas width
            atlas_height: Target canvas height
            settings: Atlas configuration

        Returns:
            True if packing succeeded
        """
        if not self.frames:
            return True

        pad = settings.padding * 2
        pack_input = [(f.width + pad, f.height + pad, f) for f in self.frames]

        packer = SkylinePacker(
            atlas_width,
            atlas_height,
            heuristic=settings.skyline_heuristic,
            allow_rotation=settings.allow_rotation,
            padding=0,
        )

        results = packer.pack(pack_input)
        if len(results) != len(self.frames):
            return False

        for x, y, w, h, rotated, frame in results:
            frame.x = x + settings.padding
            frame.y = y + settings.padding
            frame.rotated = rotated
            frame.flip_y = False

        return True

    def _apply_block_positions(
        self, blocks: List[Dict[str, object]], settings: AtlasSettings
    ) -> bool:
        """Transfer packed positions from blocks to Frame objects.

        Args:
            blocks: Block dicts containing fit results and frame references.
            settings: Atlas settings with padding offset.

        Returns:
            True if all blocks have valid placements.
        """
        for block in blocks:
            fit = block.get("fit")
            frame = block.get("frame")
            if not fit or frame is None:
                return False

            frame.x = fit["x"] + settings.padding
            frame.y = fit["y"] + settings.padding
            frame.rotated = bool(fit.get("rotated", False))
            frame.flip_y = bool(fit.get("flip_y", False))

        return True

    def _pack_frames(
        self, atlas_width: int, atlas_height: int, settings: AtlasSettings
    ) -> bool:
        """Dispatch to the packer that corresponds to ``settings.algorithm``.

        Args:
            atlas_width (int): Target canvas width supplied by the sizing
                helpers.
            atlas_height (int): Target canvas height supplied by the sizing
                helpers.
            settings (AtlasSettings): User-selected options that imply the
                algorithm and padding.

        Returns:
            bool: ``True`` when the chosen packer succeeds.
        """
        if settings.algorithm == PackingAlgorithm.NONE:
            return self._pack_grid(atlas_width, atlas_height, settings)
        elif settings.algorithm == PackingAlgorithm.GROWING_PACKER:
            return self._pack_growing(atlas_width, atlas_height, settings)
        elif settings.algorithm == PackingAlgorithm.ORDERED_PACKER:
            return self._pack_ordered(atlas_width, atlas_height, settings)
        elif settings.algorithm == PackingAlgorithm.MAXRECTS_PACKER:
            return self._pack_maxrects(atlas_width, atlas_height, settings)
        elif settings.algorithm == PackingAlgorithm.HYBRID_PACKER:
            return self._pack_hybrid(atlas_width, atlas_height, settings)
        elif settings.algorithm == PackingAlgorithm.GUILLOTINE_PACKER:
            return self._pack_guillotine(atlas_width, atlas_height, settings)
        elif settings.algorithm == PackingAlgorithm.SHELF_PACKER:
            return self._pack_shelf(atlas_width, atlas_height, settings)
        elif settings.algorithm == PackingAlgorithm.SKYLINE_PACKER:
            return self._pack_skyline(atlas_width, atlas_height, settings)
        else:
            # Default to growing packer for other algorithms
            return self._pack_growing(atlas_width, atlas_height, settings)

    def _pack_grid(
        self, atlas_width: int, atlas_height: int, settings: AtlasSettings
    ) -> bool:
        """Lay out sprites in a naïve grid when no optimization is desired.

        Args:
            atlas_width (int): Width of the candidate grid canvas.
            atlas_height (int): Height of the candidate grid canvas.
            settings (AtlasSettings): Padding controls used to size each cell.

        Returns:
            bool: ``True`` when the grid fits every frame; ``False`` if the
                canvas is undersized.
        """
        if not self.frames:
            return True

        max_width = max(f.width for f in self.frames) if self.frames else 0
        max_height = max(f.height for f in self.frames) if self.frames else 0

        cell_width = max_width + settings.padding * 2
        cell_height = max_height + settings.padding * 2

        # Calculate how many columns and rows we can fit
        cols = max(1, atlas_width // cell_width)
        rows = max(1, atlas_height // cell_height)

        # Check if we can fit all frames
        if cols * rows < len(self.frames):
            return False

        # Position frames in the grid
        for i, frame in enumerate(self.frames):
            col = i % cols
            row = i // cols

            x = col * cell_width + settings.padding
            y = row * cell_height + settings.padding

            # Double-check bounds
            if x + frame.width > atlas_width or y + frame.height > atlas_height:
                return False

            frame.x = x
            frame.y = y
            frame.rotated = False
            frame.flip_y = False

        return True

    def _create_atlas_image(self, atlas_width: int, atlas_height: int) -> Image.Image:
        """Composite the packed sprites onto a transparent RGBA canvas.

        Args:
            atlas_width (int): Width of the atlas bitmap.
            atlas_height (int): Height of the atlas bitmap.

        Returns:
            Image.Image: Pillow image containing every sprite at its packed
                location.
        """
        atlas = Image.new("RGBA", (atlas_width, atlas_height), (0, 0, 0, 0))

        for frame in self.frames:
            try:
                with Image.open(frame.image_path) as img:
                    # Extract the trimmed portion of the image
                    if hasattr(frame, "_trim_bounds"):
                        left, top, right, bottom = frame._trim_bounds
                        trimmed_img = img.crop((left, top, right, bottom))
                    else:
                        trimmed_img = img

                    if frame.flip_y:
                        trimmed_img = ImageOps.flip(trimmed_img)

                    if frame.rotated:
                        # 90° clockwise rotation (PIL -90° is clockwise)
                        trimmed_img = trimmed_img.rotate(-90, expand=True)

                    atlas.paste(trimmed_img, (frame.x, frame.y))
            except Exception as e:
                print(f"Error pasting frame {frame.name}: {e}")
                continue

        return atlas

    def _generate_sparrow_xml(
        self,
        output_path: str,
        atlas_width: int,
        atlas_height: int,
        current_version: str,
        settings: AtlasSettings = None,
    ) -> str:
        """Generate Sparrow XML with embedded comments.

        Args:
            output_path: Base path used to derive the PNG filename.
            atlas_width: Atlas width for reference (unused in output).
            atlas_height: Atlas height for reference (unused in output).
            current_version: App version recorded in XML comments.
            settings: Optional settings for algorithm info in comments.

        Returns:
            XML string with header comments and SubTexture elements.
        """
        atlas_png_name = Path(f"{output_path}.png").name
        root = ET.Element("TextureAtlas")
        root.set("imagePath", atlas_png_name)

        # Sort frames alphabetically and numerically by name
        sorted_frames = sorted(
            self.frames, key=lambda f: self._natural_sort_key(f.name)
        )

        for frame in sorted_frames:
            subtexture = ET.SubElement(root, "SubTexture")
            subtexture.set("name", frame.name)
            subtexture.set("x", str(frame.x))
            subtexture.set("y", str(frame.y))
            subtexture.set("width", str(frame.width))
            subtexture.set("height", str(frame.height))
            subtexture.set("frameX", str(-frame.frame_x))
            subtexture.set("frameY", str(-frame.frame_y))
            subtexture.set("frameWidth", str(frame.original_width))
            subtexture.set("frameHeight", str(frame.original_height))
            subtexture.set("flipX", "false")
            subtexture.set("flipY", str(frame.flip_y).lower())
            subtexture.set("rotated", str(frame.rotated).lower())

        # Create XML string with proper header and comments
        xml_declaration = '<?xml version="1.0" encoding="utf-8"?>\n'

        # Pretty print XML
        from xml.dom import minidom

        rough_string = ET.tostring(root, encoding="unicode")
        parsed = minidom.parseString(rough_string)
        pretty_xml = parsed.toprettyxml(indent="  ")

        # Remove the default XML declaration from minidom output
        lines = pretty_xml.split("\n")
        if lines[0].startswith("<?xml"):
            lines = lines[1:]

        # Add our custom header and comments
        result_lines = [xml_declaration.rstrip()]
        result_lines.append(f'<TextureAtlas imagePath="{atlas_png_name}">')
        result_lines.append(
            f"    <!-- Generated by TextureAtlas Toolbox v{current_version} -->"
        )

        # Add optimization level info if available
        if settings:
            result_lines.append(
                f"    <!-- Optimization Level: {settings.optimization_level} -->"
            )
            try:
                algorithm_label_map = {
                    PackingAlgorithm.NONE: "Grid",
                    PackingAlgorithm.GROWING_PACKER: "Growing",
                    PackingAlgorithm.ORDERED_PACKER: "Ordered",
                    PackingAlgorithm.MAXRECTS_PACKER: "MaxRects",
                    PackingAlgorithm.HYBRID_PACKER: "Hybrid Adaptive",
                }
                algorithm_label = algorithm_label_map.get(
                    settings.algorithm, settings.algorithm.name.title()
                )
                result_lines.append(
                    f"    <!-- Packing Algorithm: {algorithm_label} -->"
                )
            except Exception:
                pass

        result_lines.append("    <!-- https://textureatlastoolbox.com/ -->")
        result_lines.append(
            "    <!-- https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/ -->"
        )

        # Add all SubTexture elements
        for frame in sorted_frames:
            result_lines.append(
                f'    <SubTexture name="{frame.name}" x="{frame.x}" y="{frame.y}" '
                + f'width="{frame.width}" height="{frame.height}" frameX="{-frame.frame_x}" frameY="{-frame.frame_y}" '
                + f'frameWidth="{frame.original_width}" frameHeight="{frame.original_height}" '
                + f'flipX="false" flipY="{str(frame.flip_y).lower()}" rotated="{str(frame.rotated).lower()}"/>'
            )

        result_lines.append("</TextureAtlas>")

        return "\n".join(result_lines)

    def _natural_sort_key(self, text: str):
        """Return a list-based key that enables human-friendly ordering.

        Args:
            text (str): Frame identifier such as ``idle_0010``.

        Returns:
            list: Mixed string/int chunks suited for ``sorted``.
        """
        # Split text into parts: letters and numbers
        parts = re.split(r"(\d+)", text)
        # Convert numeric parts to integers for proper sorting
        result = []
        for part in parts:
            if part.isdigit():
                result.append(int(part))
            else:
                result.append(part)
        return result

    def _calculate_efficiency(self, atlas_width: int, atlas_height: int) -> float:
        """Estimate how much of the atlas area ended up covered by sprites.

        Args:
            atlas_width (int): Final atlas width.
            atlas_height (int): Final atlas height.

        Returns:
            float: Percentage of the atlas area consumed by frames.
        """
        if not self.frames:
            return 0.0

        used_area = sum(f.area for f in self.frames)
        total_area = atlas_width * atlas_height
        return (used_area / total_area) * 100 if total_area > 0 else 0.0

    def _next_power_of_2(self, value: int) -> int:
        """Find the next power-of-two value that is >= ``value``.

        Args:
            value (int): Input dimension that requires rounding.

        Returns:
            int: Adjusted dimension suitable for GPU hardware limits.
        """
        return 2 ** int(np.ceil(np.log2(value)))

    def _update_progress(self, current: int, total: int, message: str = ""):
        """Relay a progress tuple to the optional UI callback.

        Args:
            current (int): Step index that just completed.
            total (int): Total number of steps in the workflow.
            message (str): Human-friendly status description.
        """
        if self.progress_callback:
            self.progress_callback(current, total, message)

    def _get_trim_bounds(self, img: Image.Image) -> Optional[Tuple[int, int, int, int]]:
        """Locate the alpha bounding box for a sprite frame.

        Args:
            img (Image.Image): Source image that may include transparent
                padding.

        Returns:
            Optional[Tuple[int, int, int, int]]: Trim rectangle if opaque pixels
                exist, otherwise ``None`` when the image is empty.
        """

        if img.mode != "RGBA":
            img = img.convert("RGBA")

        alpha = img.split()[-1]

        bbox = alpha.getbbox()
        if bbox is None:
            return None

        return bbox

    @staticmethod
    def fast_image_cmp(img1: Image.Image, img2: Image.Image) -> bool:
        """Compare two images for exact pixel equality.

        Args:
            img1: First image to compare.
            img2: Second image to compare.

        Returns:
            True if images are identical, False otherwise.
        """
        if img1.size != img2.size:
            return False
        if img1.tobytes() != img2.tobytes():
            return False

        from PIL import ImageChops

        return ImageChops.difference(img1, img2).getbbox() is None
