#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Base class for all texture atlas packing algorithms.

Provides the abstract interface that all packers must implement, plus
shared utilities for frame preprocessing, atlas sizing, and result building.

The packer system provides a clean separation of concerns:
    - Packers: Layout algorithms that assign positions to frames.
    - Exporters: Convert packed layouts to atlas images and metadata.

Usage:
    from packers.base_packer import BasePacker
    from packers.packer_types import FrameInput, PackerOptions

    class MyPacker(BasePacker):
        ALGORITHM_NAME = "my-packer"
        DISPLAY_NAME = "My Custom Packer"

        def _pack_internal(self, frames, options):
            # Implement packing logic
            ...
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

from packers.packer_types import (
    ExpandStrategy,
    FrameInput,
    FrameTooLargeError,
    PackedFrame,
    PackerError,
    PackerErrorCode,
    PackerOptions,
    PackerResult,
)


class BasePacker(ABC):
    """Abstract base class for texture atlas packing algorithms.

    Subclasses must implement:
        - _pack_internal(): Core packing algorithm logic.
        - ALGORITHM_NAME: Unique identifier for the algorithm.
        - DISPLAY_NAME: Human-readable name for UI display.

    The base class provides:
        - pack(): Main entry point with preprocessing and postprocessing.
        - Frame sorting utilities.
        - Atlas sizing and expansion logic.
        - Result building and efficiency calculation.

    Attributes:
        options: Packer configuration options.
    """

    # Subclasses must define these
    ALGORITHM_NAME: str = ""
    DISPLAY_NAME: str = ""

    # Optional: List of supported heuristics for this algorithm
    SUPPORTED_HEURISTICS: List[Tuple[str, str]] = []  # [(key, display_name), ...]

    def __init__(self, options: Optional[PackerOptions] = None) -> None:
        """Initialize the packer with optional configuration.

        Args:
            options: Packer options controlling sizing and layout.
                     Uses defaults if not provided.
        """
        self.options = options or PackerOptions()
        self._current_heuristic: Optional[str] = None

    @abstractmethod
    def _pack_internal(
        self,
        frames: List[FrameInput],
        width: int,
        height: int,
    ) -> List[PackedFrame]:
        """Core packing algorithm implementation.

        Subclasses implement their specific packing logic here.
        The frames are already preprocessed (sorted, validated).

        Args:
            frames: List of frames to pack (already sorted/validated).
            width: Available atlas width.
            height: Available atlas height.

        Returns:
            List of PackedFrame with assigned positions.
            Returns empty list if frames cannot fit.
        """
        pass

    def pack(self, frames: List[FrameInput]) -> PackerResult:
        """Pack frames into an atlas layout.

        This is the main entry point for packing. Handles:
        - Input validation
        - Frame preprocessing (sorting, cloning)
        - Atlas sizing and expansion
        - Result building with efficiency metrics

        Args:
            frames: List of frames to pack.

        Returns:
            PackerResult with packed frames, dimensions, and diagnostics.
        """
        result = PackerResult(algorithm_name=self.ALGORITHM_NAME)

        # Validate inputs
        if not frames:
            result.add_error(
                PackerErrorCode.NO_FRAMES_PROVIDED,
                "No frames provided for packing",
            )
            return result

        try:
            # Validate options
            self.options.validate()

            # Clone frames to avoid modifying originals
            work_frames = [f.clone() for f in frames]

            # Validate frame sizes
            self._validate_frames(work_frames)

            # Sort frames for better packing
            work_frames = self._sort_frames(work_frames)

            # Determine initial atlas size
            init_width, init_height = self._calculate_initial_size(work_frames)

            # Try packing with expansion
            packed, final_width, final_height = self._pack_with_expansion(
                work_frames, init_width, init_height
            )

            if not packed:
                result.add_error(
                    PackerErrorCode.CANNOT_FIT_ALL,
                    f"Cannot fit all {len(frames)} frames within "
                    f"{self.options.max_width}x{self.options.max_height}",
                )
                return result

            # Apply power-of-two constraint if requested
            if self.options.power_of_two:
                final_width = self._next_power_of_two(final_width)
                final_height = self._next_power_of_two(final_height)

            # Apply square constraint if requested
            if self.options.force_square:
                final_width = final_height = max(final_width, final_height)

            # Build result
            result.success = True
            result.packed_frames = packed
            result.atlas_width = final_width
            result.atlas_height = final_height
            result.heuristic_name = self._current_heuristic
            result.calculate_efficiency()

        except PackerError as e:
            result.add_error(e.code, e.message, e.details)
        except Exception as e:
            result.add_error(
                PackerErrorCode.UNKNOWN_ERROR,
                f"Unexpected error during packing: {e}",
                details={"exception_type": type(e).__name__},
            )

        return result

    def set_heuristic(self, heuristic_key: str) -> bool:
        """Set the heuristic to use for packing.

        Args:
            heuristic_key: Key identifying the heuristic.

        Returns:
            True if heuristic was set successfully, False if not supported.
        """
        valid_keys = [h[0] for h in self.SUPPORTED_HEURISTICS]
        if heuristic_key in valid_keys:
            self._current_heuristic = heuristic_key
            return True
        elif not self.SUPPORTED_HEURISTICS:
            # Algorithm doesn't use heuristics
            return True
        return False

    # =========================================================================
    # Frame Preprocessing
    # =========================================================================

    def _validate_frames(self, frames: List[FrameInput]) -> None:
        """Validate frame dimensions against max size.

        Raises:
            FrameTooLargeError: If any frame exceeds maximum dimensions.
        """
        padding = self.options.padding
        border = self.options.border_padding
        max_w = self.options.max_width - 2 * border
        max_h = self.options.max_height - 2 * border

        for frame in frames:
            effective_w = frame.width + padding
            effective_h = frame.height + padding

            # With rotation, check if it fits either way
            if self.options.allow_rotation:
                fits_normal = effective_w <= max_w and effective_h <= max_h
                fits_rotated = effective_h <= max_w and effective_w <= max_h
                if not (fits_normal or fits_rotated):
                    raise FrameTooLargeError(
                        PackerErrorCode.FRAME_TOO_LARGE,
                        f"Frame '{frame.id}' ({frame.width}x{frame.height}) "
                        f"exceeds maximum dimensions even when rotated",
                        details={"frame_id": frame.id, "max_size": (max_w, max_h)},
                    )
            else:
                if effective_w > max_w or effective_h > max_h:
                    raise FrameTooLargeError(
                        PackerErrorCode.FRAME_TOO_LARGE,
                        f"Frame '{frame.id}' ({frame.width}x{frame.height}) "
                        f"exceeds maximum dimensions ({max_w}x{max_h})",
                        details={"frame_id": frame.id, "max_size": (max_w, max_h)},
                    )

    def _sort_frames(self, frames: List[FrameInput]) -> List[FrameInput]:
        """Sort frames for better packing efficiency.

        Args:
            frames: Frames to sort.

        Returns:
            Sorted copy of frames list.
        """
        if self.options.sort_by_area:
            # Sort by area descending
            return sorted(frames, key=lambda f: f.width * f.height, reverse=True)
        elif self.options.sort_by_max_side:
            # Sort by max(width, height) descending, then by min side
            return sorted(
                frames,
                key=lambda f: (max(f.width, f.height), min(f.width, f.height)),
                reverse=True,
            )
        return frames

    # =========================================================================
    # Atlas Sizing
    # =========================================================================

    def _calculate_initial_size(self, frames: List[FrameInput]) -> Tuple[int, int]:
        """Calculate initial atlas size based on frame dimensions.

        Uses a square-ish estimate based on total area, constrained
        by the maximum dimensions.

        Args:
            frames: Frames to pack.

        Returns:
            (width, height) tuple for initial atlas size.
        """
        padding = self.options.padding
        border = self.options.border_padding

        # Find largest frame dimensions (include padding between sprites)
        max_frame_w = max(f.width for f in frames) + padding
        max_frame_h = max(f.height for f in frames) + padding

        # Smallest workspace that can physically fit every frame (include borders)
        min_width = max_frame_w + 2 * border
        min_height = max_frame_h + 2 * border

        # Clamp to allowed maxima; validation already guarantees they fit
        width = min(min_width, self.options.max_width)
        height = min(min_height, self.options.max_height)

        return width, height

    def _pack_with_expansion(
        self,
        frames: List[FrameInput],
        init_width: int,
        init_height: int,
    ) -> Tuple[List[PackedFrame], int, int]:
        """Attempt packing with automatic atlas expansion.

        Args:
            frames: Frames to pack.
            init_width: Initial atlas width.
            init_height: Initial atlas height.

        Returns:
            (packed_frames, final_width, final_height) or ([], 0, 0) if failed.
        """
        width, height = init_width, init_height
        max_w, max_h = self.options.max_width, self.options.max_height
        strategy = self.options.expand_strategy

        padding = self.options.padding

        while width <= max_w and height <= max_h:
            packed = self._pack_internal(frames, width, height)

            if len(packed) == len(frames):
                # Success - calculate tight bounds
                # Note: PackedFrame.width/height are source dimensions;
                # we need to add padding to match actual placement
                if packed:
                    final_w = max(p.x + p.width + padding for p in packed)
                    final_h = max(p.y + p.height + padding for p in packed)
                else:
                    final_w = 0
                    final_h = 0

                # Add border padding
                final_w += self.options.border_padding
                final_h += self.options.border_padding

                return packed, final_w, final_h

            if strategy == ExpandStrategy.DISABLED:
                break

            # Expand atlas
            new_width, new_height = self._expand_atlas(width, height, strategy)

            # If no expansion occurred (at max size), break to avoid infinite loop
            if new_width == width and new_height == height:
                break

            width, height = new_width, new_height

        return [], 0, 0

    def _expand_atlas(
        self,
        width: int,
        height: int,
        strategy: ExpandStrategy,
    ) -> Tuple[int, int]:
        """Expand atlas dimensions according to strategy.

        Args:
            width: Current width.
            height: Current height.
            strategy: Expansion strategy.

        Returns:
            (new_width, new_height) tuple.
        """
        max_w, max_h = self.options.max_width, self.options.max_height

        if strategy == ExpandStrategy.WIDTH_FIRST:
            if width < max_w:
                return min(width * 2, max_w), height
            else:
                return width, min(height * 2, max_h)

        elif strategy == ExpandStrategy.HEIGHT_FIRST:
            if height < max_h:
                return width, min(height * 2, max_h)
            else:
                return min(width * 2, max_w), height

        elif strategy == ExpandStrategy.SHORT_SIDE:
            if width <= height and width < max_w:
                return min(width * 2, max_w), height
            elif height < max_h:
                return width, min(height * 2, max_h)
            else:
                return min(width * 2, max_w), height

        elif strategy == ExpandStrategy.LONG_SIDE:
            if width >= height and width < max_w:
                return min(width * 2, max_w), height
            elif height < max_h:
                return width, min(height * 2, max_h)
            else:
                return min(width * 2, max_w), height

        elif strategy == ExpandStrategy.BOTH:
            return min(width * 2, max_w), min(height * 2, max_h)

        # DISABLED - shouldn't reach here
        return width, height

    # =========================================================================
    # Utilities
    # =========================================================================

    @staticmethod
    def _next_power_of_two(value: int) -> int:
        """Round up to the next power of two.

        Args:
            value: Input value.

        Returns:
            Smallest power of two >= value.
        """
        if value <= 0:
            return 1
        power = 1
        while power < value:
            power *= 2
        return power

    @classmethod
    def get_supported_heuristics(cls) -> List[Tuple[str, str]]:
        """Get list of heuristics supported by this algorithm.

        Returns:
            List of (key, display_name) tuples.
        """
        return cls.SUPPORTED_HEURISTICS.copy()

    @classmethod
    def can_pack(cls, algorithm_name: str) -> bool:
        """Check if this packer handles the given algorithm name.

        Args:
            algorithm_name: Algorithm name to check.

        Returns:
            True if this packer handles the algorithm.
        """
        return algorithm_name.lower() == cls.ALGORITHM_NAME.lower()


class SimplePacker(BasePacker):
    """Simple row-based packer for basic use cases.

    Places frames left-to-right, top-to-bottom in rows.
    Fast but not space-efficient. Useful for ordered layouts.
    """

    ALGORITHM_NAME = "simple"
    DISPLAY_NAME = "Simple Row Packer"

    def _pack_internal(
        self,
        frames: List[FrameInput],
        width: int,
        height: int,
    ) -> List[PackedFrame]:
        """Pack frames in simple rows."""
        packed: List[PackedFrame] = []
        padding = self.options.padding
        border = self.options.border_padding

        x = border
        y = border
        row_height = 0
        available_width = width - 2 * border
        available_height = height - 2 * border

        for frame in frames:
            frame_w = frame.width + padding
            frame_h = frame.height + padding

            # Check if frame fits in current row
            if x + frame_w > border + available_width:
                # Move to next row
                x = border
                y += row_height
                row_height = 0

            # Check if frame fits vertically
            if y + frame_h > border + available_height:
                # Cannot fit
                return packed

            # Place frame
            packed.append(PackedFrame(frame=frame, x=x, y=y))

            x += frame_w
            row_height = max(row_height, frame_h)

        return packed


__all__ = ["BasePacker", "SimplePacker"]
