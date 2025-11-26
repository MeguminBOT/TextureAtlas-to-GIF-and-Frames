"""Image helper utilities shared across extractor components."""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple, Union

import numpy as np
from PIL import Image


FrameSource = Union[Image.Image, np.ndarray]
BBox = Tuple[int, int, int, int]


def scale_image_nearest(image: Image.Image, size: float) -> Image.Image:
    """Scale an image using nearest-neighbor sampling, supporting horiz flip.

    Negative scale flips the source horizontally before resizing. Size is
    interpreted as a multiplier (1.0 keeps the original dimensions).
    """

    working = image
    if size < 0:
        working = working.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    new_width = max(1, round(working.width * abs(size)))
    new_height = max(1, round(working.height * abs(size)))
    if new_width == working.width and new_height == working.height:
        return working
    return working.resize((new_width, new_height), Image.NEAREST)


def pad_frames_to_canvas(images: Sequence[FrameSource]) -> List[np.ndarray]:
    """Pad frames so they share a common canvas size using NumPy arrays."""
    if not images:
        return []

    arrays = [ensure_rgba_array(frame) for frame in images]
    heights = [array.shape[0] for array in arrays]
    widths = [array.shape[1] for array in arrays]

    max_width = max(widths)
    max_height = max(heights)
    min_width = min(widths)
    min_height = min(heights)

    if max_width == min_width and max_height == min_height:
        return arrays

    padded: List[np.ndarray] = []
    for array in arrays:
        if array.shape[1] == max_width and array.shape[0] == max_height:
            padded.append(array)
            continue
        canvas = np.zeros((max_height, max_width, array.shape[2]), dtype=np.uint8)
        canvas[: array.shape[0], : array.shape[1]] = array
        padded.append(canvas)
    return padded


def image_to_rgba_array(image: Image.Image) -> np.ndarray:
    """Return a contiguous RGBA NumPy view of the PIL image."""

    rgba_image = image if image.mode == "RGBA" else image.convert("RGBA")
    array = np.asarray(rgba_image)
    if not array.flags["C_CONTIGUOUS"]:
        array = np.ascontiguousarray(array)
    return array


def array_to_rgba_image(array: np.ndarray) -> Image.Image:
    """Convert an RGBA NumPy array back into a PIL image."""

    if not array.flags["C_CONTIGUOUS"]:
        array = np.ascontiguousarray(array)
    return Image.fromarray(array, mode="RGBA")


def ensure_rgba_array(source: FrameSource) -> np.ndarray:
    """Return a contiguous uint8 RGBA array regardless of the backing type."""

    if isinstance(source, np.ndarray):
        array = source
    else:
        array = image_to_rgba_array(source)
    if array.dtype != np.uint8:
        array = array.astype(np.uint8, copy=False)
    if array.ndim == 2:
        array = np.expand_dims(array, axis=-1)
    if not array.flags["C_CONTIGUOUS"]:
        array = np.ascontiguousarray(array)
    return array


def ensure_pil_image(source: FrameSource) -> Image.Image:
    """Return a PIL RGBA image for downstream consumers that require PIL APIs."""

    if isinstance(source, Image.Image):
        return source if source.mode == "RGBA" else source.convert("RGBA")
    return array_to_rgba_image(source)


def frame_dimensions(source: FrameSource) -> Tuple[int, int]:
    """Return width/height for either a NumPy array or PIL image."""

    if isinstance(source, np.ndarray):
        if source.ndim == 2:
            return source.shape[1], source.shape[0]
        return source.shape[1], source.shape[0]
    return source.width, source.height


def alpha_mask(array: np.ndarray, *, threshold: int = 0) -> Optional[np.ndarray]:
    """Return a boolean mask for the alpha channel (or luminance fallback)."""

    if array.size == 0:
        return None

    if array.ndim == 2:
        return array > threshold

    if array.ndim >= 3:
        channels = array.shape[2]
        if channels == 0:
            return None
        if channels >= 4:
            return array[..., 3] > threshold
        return np.any(array[..., :channels] > threshold, axis=2)

    return None


def bbox_from_mask(mask: Optional[np.ndarray]) -> Optional[BBox]:
    """Compute a tight bounding box from a boolean alpha mask."""

    if mask is None or mask.ndim != 2:
        return None

    row_hits = np.flatnonzero(mask.any(axis=1))
    if row_hits.size == 0:
        return None
    col_hits = np.flatnonzero(mask.any(axis=0))
    if col_hits.size == 0:
        return None

    top = int(row_hits[0])
    bottom = int(row_hits[-1] + 1)
    left = int(col_hits[0])
    right = int(col_hits[-1] + 1)
    return left, top, right, bottom


def bbox_from_array(array: np.ndarray, *, threshold: int = 0) -> Optional[BBox]:
    """Return the bounding box of the visible pixels inside an array."""

    mask = alpha_mask(array, threshold=threshold)
    if mask is None:
        return None
    return bbox_from_mask(mask)


def frame_bbox(frame: FrameSource, *, threshold: int = 0) -> Optional[BBox]:
    """Safe wrapper to compute the bounding box for mixed frame sources."""

    try:
        array = ensure_rgba_array(frame)
    except Exception:
        return None
    return bbox_from_array(array, threshold=threshold)


def crop_to_bbox(array: np.ndarray, bbox: BBox) -> np.ndarray:
    """Return a view cropped to the provided bounding box (no copy if possible)."""

    if array.ndim < 2:
        return array

    height, width = array.shape[0], array.shape[1]
    left, top, right, bottom = bbox

    left = max(0, min(width, int(left)))
    top = max(0, min(height, int(top)))
    right = max(left, min(width, int(right)))
    bottom = max(top, min(height, int(bottom)))

    if left == 0 and top == 0 and right == width and bottom == height:
        return array

    return array[top:bottom, left:right]


def apply_alpha_threshold(array: np.ndarray, threshold: float) -> np.ndarray:
    """Clamp the alpha plane to {0, 255} using the provided normalized threshold."""

    if array.ndim < 3 or array.shape[2] < 4:
        return array

    try:
        value = float(threshold)
    except (TypeError, ValueError):
        return array

    value = min(max(value, 0.0), 1.0)
    working = array if array.flags.writeable else array.copy()
    alpha_view = working[..., 3]

    mask = np.empty(alpha_view.shape, dtype=bool)
    if value >= 1.0:
        np.greater_equal(alpha_view, 255, out=mask)
    elif value <= 0.0:
        np.greater(alpha_view, 0, out=mask)
    else:
        cutoff = int(round(value * 255))
        np.greater(alpha_view, cutoff, out=mask)

    np.multiply(mask, 255, out=alpha_view, casting="unsafe")
    return working
