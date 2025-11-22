#!/usr/bin/env python3
"""Shared helpers for translating Friday Night Funkin' offsets."""
from __future__ import annotations

from typing import Any, Mapping, Optional, Tuple, Union

Number = Union[int, float]


def _coerce_number(value: Any, default: float = 0.0) -> float:
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

    return convert_flxsprite_offset(target, metadata=metadata, scale=scale, flip_x=flip_x)
