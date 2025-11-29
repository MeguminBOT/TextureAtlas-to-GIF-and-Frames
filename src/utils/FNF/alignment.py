#!/usr/bin/env python3
"""Helpers for converting Friday Night Funkin' sprite offsets to pixel coordinates."""
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence, Tuple, Union

Number = Union[int, float]


def _coerce_number(value: Any, default: float = 0.0) -> float:
    """Convert a value to float, returning default on failure.

    Args:
        value: Input to convert.
        default: Fallback if conversion fails.

    Returns:
        The numeric value as a float.
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def convert_flxsprite_offset(
    raw_offset: Mapping[str, Any],
    metadata: Any = None,
    scale: Number = 1.0,
    flip_x: bool = False,
) -> Tuple[int, int]:
    """Convert a FlxSprite offset mapping to pixel coordinates.

    Args:
        raw_offset: Mapping with 'x' and 'y' keys.
        metadata: Optional sprite metadata (currently unused).
        scale: Multiplier applied to the offset values.
        flip_x: Whether to mirror horizontally (currently unused).

    Returns:
        Tuple of (x, y) pixel offsets as integers.
    """
    raw_x = _coerce_number(raw_offset.get("x", 0.0), 0.0)
    raw_y = _coerce_number(raw_offset.get("y", 0.0), 0.0)
    scale_value = _coerce_number(scale, 1.0)

    offset_x = -raw_x
    offset_y = -raw_y

    offset_x *= scale_value
    offset_y *= scale_value

    return int(round(offset_x)), int(round(offset_y))


def resolve_fnf_offset(
    overrides: Mapping[str, Any],
    frame_key: Optional[str] = None,
    metadata: Any = None,
) -> Optional[Tuple[int, int]]:
    """Look up and convert an FNF offset from an overrides mapping.

    Args:
        overrides: Settings dict potentially containing '_fnf_raw_offsets'.
        frame_key: Optional key to retrieve a per-frame offset.
        metadata: Optional sprite metadata passed to the converter.

    Returns:
        Tuple of (x, y) pixel offsets, or None if no offset data exists.
    """
    raw_block = overrides.get("_fnf_raw_offsets")
    if not isinstance(raw_block, Mapping):
        return None

    target: Optional[Mapping[str, Any]] = None
    raw_frames = raw_block.get("frames")
    if frame_key and isinstance(raw_frames, Mapping):
        target = raw_frames.get(frame_key)

    if target is None:
        target = raw_block.get("default")

    if not isinstance(target, Mapping):
        return None

    scale = raw_block.get("scale", 1.0)
    flip_x = bool(raw_block.get("flip_x", False))

    return convert_flxsprite_offset(
        target, metadata=metadata, scale=scale, flip_x=flip_x
    )


def build_alignment_overrides(
    offsets: Optional[Sequence[Number]],
    scale: Number = 1.0,
    flip_x: bool = False,
) -> Optional[dict[str, Any]]:
    """Build an alignment overrides dict from raw offset values.

    Args:
        offsets: Two-element sequence of (x, y) offset values.
        scale: Multiplier stored with the raw offset data.
        flip_x: Horizontal flip flag stored with the raw offset data.

    Returns:
        A dict suitable for merging into animation overrides, or None
        if offsets is invalid.
    """
    if not isinstance(offsets, Sequence) or len(offsets) != 2:
        return None

    try:
        x_val = int(offsets[0])
        y_val = int(offsets[1])
    except (TypeError, ValueError):
        return None

    scale_value = _coerce_number(scale, 1.0)

    overrides: dict[str, Any] = {
        "default": {"x": -x_val, "y": -y_val},
        "frames": {},
    }
    raw_block: dict[str, Any] = {
        "default": {"x": x_val, "y": y_val},
        "frames": {},
        "scale": scale_value,
    }

    if flip_x:
        raw_block["flip_x"] = bool(flip_x)

    overrides["_fnf_raw_offsets"] = raw_block
    overrides["origin_mode"] = "top_left"
    return overrides
