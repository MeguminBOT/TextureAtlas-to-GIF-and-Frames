"""Utilities for normalizing, selecting, and preparing frames for exporters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterator, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image

from core.extractor.frame_selector import FrameSelector
from core.extractor.image_utils import (
    array_to_rgba_image,
    FrameSource,
    crop_to_bbox,
    ensure_rgba_array,
    frame_bbox,
)

FrameTuple = Tuple[str, FrameSource, dict]


@dataclass(frozen=True)
class AnimationContext:
    """Container describing a prepared set of frames for export."""

    spritesheet_name: str
    animation_name: str
    settings: dict
    frames: List[FrameTuple]
    kept_indices: List[int]
    single_frame: bool

    def with_frames(self, frames: Sequence[FrameTuple]) -> "AnimationContext":
        """Return a copy of this context with a new frame list."""
        return AnimationContext(
            spritesheet_name=self.spritesheet_name,
            animation_name=self.animation_name,
            settings=self.settings,
            frames=list(frames),
            kept_indices=list(self.kept_indices),
            single_frame=self.single_frame,
        )

    def iter_selected_frames(self) -> Iterator[FrameTuple]:
        """Yield the frames referenced by kept_indices in order."""
        for index in self.kept_indices:
            if 0 <= index < len(self.frames):
                yield self.frames[index]

    @property
    def selected_frames(self) -> List[FrameTuple]:
        return list(self.iter_selected_frames())


class FramePipeline:
    """Shared helpers for frame sorting, selection, and preparation."""

    def build_context(
        self,
        spritesheet_name: str,
        animation_name: str,
        image_tuples: Sequence[FrameTuple],
        settings: dict,
    ) -> AnimationContext:
        frames = self._normalize_frames(image_tuples, settings)
        single_frame = FrameSelector.is_single_frame(frames)
        kept_frames = FrameSelector.get_kept_frames(settings, single_frame, frames)
        kept_indices = FrameSelector.get_kept_frame_indices(kept_frames, frames)
        return AnimationContext(
            spritesheet_name=spritesheet_name,
            animation_name=animation_name,
            settings=settings,
            frames=frames,
            kept_indices=kept_indices,
            single_frame=single_frame,
        )

    def _normalize_frames(
        self, image_tuples: Sequence[FrameTuple], settings: dict
    ) -> List[FrameTuple]:
        frames = list(image_tuples or [])
        if not frames:
            return frames

        if self._should_preserve_sequence(frames):
            frames.sort(
                key=lambda frame: (
                    frame[2].get("editor_sequence_index", 0)
                    if isinstance(frame[2], dict)
                    else 0
                ),
            )
        else:
            frames.sort(key=lambda frame: frame[0])

        indices = self._sanitize_indices(settings.get("indices"), len(frames))
        if indices:
            frames = [frames[i] for i in indices]

        normalized: List[FrameTuple] = []
        for name, image, metadata in frames:
            normalized.append((name, ensure_rgba_array(image), metadata))

        return normalized

    @staticmethod
    def _should_preserve_sequence(frames: Sequence[FrameTuple]) -> bool:
        for _, _, metadata in frames:
            if isinstance(metadata, dict) and "editor_sequence_index" in metadata:
                return True
        return False

    @staticmethod
    def _sanitize_indices(indices: Optional[Sequence[int]], length: int) -> List[int]:
        if not isinstance(indices, Sequence):
            return []
        sanitized: List[int] = []
        for raw in indices:
            try:
                index = int(raw)
            except (TypeError, ValueError):
                continue
            if index < 0:
                index += length
            if 0 <= index < length:
                sanitized.append(index)
        return sanitized


def compute_shared_bbox(
    images: Sequence[FrameSource],
) -> Optional[Tuple[int, int, int, int]]:
    """Return the shared bounding box for a collection of frames or arrays."""
    min_x, min_y, max_x, max_y = (
        float("inf"),
        float("inf"),
        float("-inf"),
        float("-inf"),
    )

    for frame in images:
        bbox = frame_bbox(frame)
        if bbox is None:
            continue
        min_x = min(min_x, bbox[0])
        min_y = min(min_y, bbox[1])
        max_x = max(max_x, bbox[2])
        max_y = max(max_y, bbox[3])

    if min_x == float("inf") or max_x == float("-inf"):
        return None
    return int(min_x), int(min_y), int(max_x), int(max_y)


def prepare_scaled_sequence(
    images: Sequence[FrameSource],
    scale_image: Callable[[Image.Image, float], Image.Image],
    scale: float,
    crop_option: Optional[str],
) -> List[Image.Image]:
    """Crop (if requested) and scale all frames in a sequence."""
    scale_value = scale if isinstance(scale, (int, float)) else 1.0
    crop_mode = (crop_option or "None").lower()

    crop_box = None
    frame_arrays: Optional[List[np.ndarray]] = None
    if crop_mode != "none":
        frame_arrays = [ensure_rgba_array(frame) for frame in images]
        crop_box = compute_shared_bbox(frame_arrays)
        if crop_box is None:
            return []

    processed: List[Image.Image] = []
    for index, frame in enumerate(images):
        frame_array = (
            frame_arrays[index]
            if frame_arrays is not None
            else ensure_rgba_array(frame)
        )
        working_array = crop_to_bbox(frame_array, crop_box) if crop_box else frame_array
        working_image = array_to_rgba_image(working_array)
        processed.append(scale_image(working_image, scale_value))
    return processed


def build_frame_durations(
    frame_count: int,
    fps: Optional[float],
    delay: Optional[float],
    period: Optional[float],
    var_delay: bool,
    *,
    round_to_ten: bool = False,
) -> List[int]:
    """Compute frame durations (milliseconds) honoring delay/period rules."""
    if frame_count <= 0:
        return []

    fps_value = float(fps) if fps else 24.0
    if fps_value <= 0:
        fps_value = 24.0

    base_interval = 1000.0 / fps_value
    durations: List[float] = []
    for index in range(frame_count):
        if var_delay:
            next_mark = (index + 1) * base_interval
            current_mark = index * base_interval
            duration = next_mark - current_mark
        else:
            duration = base_interval
        if round_to_ten:
            duration = round(duration, -1)
        durations.append(duration)

    delay_value = delay or 0.0
    period_value = period or 0.0
    if round_to_ten:
        delay_value = round(delay_value, -1)
        period_value = round(period_value, -1)

    durations[-1] += delay_value
    total_elapsed = sum(durations)
    durations[-1] += max(period_value - total_elapsed, 0.0)

    if round_to_ten:
        return [int(round(value / 10.0)) * 10 for value in durations]
    return [int(round(value)) for value in durations]
