"""Image helper utilities shared across extractor components."""

from __future__ import annotations

from typing import List, Sequence

from PIL import Image


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


def pad_frames_to_canvas(images: Sequence[Image.Image]) -> List[Image.Image]:
    """Pad frames so they share a common canvas size."""
    if not images:
        return []

    max_width = max(frame.width for frame in images)
    max_height = max(frame.height for frame in images)
    min_width = min(frame.width for frame in images)
    min_height = min(frame.height for frame in images)

    if max_width == min_width and max_height == min_height:
        return list(images)

    padded: List[Image.Image] = []
    for frame in images:
        if frame.width == max_width and frame.height == max_height:
            padded.append(frame)
            continue
        canvas = Image.new("RGBA", (max_width, max_height))
        canvas.paste(frame)
        padded.append(canvas)
    return padded
