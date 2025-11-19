"""Lightweight helpers for inspecting Adobe Spritemap timelines without rendering."""

from __future__ import annotations

from typing import Dict, List, Optional


def _frame_duration(frame: dict) -> int:
    """Return clamped duration for a single frame entry."""
    duration = frame.get("DU", 1)
    try:
        duration = int(duration)
    except (TypeError, ValueError):
        duration = 1
    return max(1, duration)


def compute_layers_length(layers: Optional[List[dict]]) -> int:
    """Compute the total frame count for a set of layers."""
    if not layers:
        return 0

    total = 0
    for layer in layers:
        frames = layer.get("FR", []) or []
        if not frames:
            continue
        last_frame = frames[-1]
        start_index = int(last_frame.get("I", 0))
        total = max(total, start_index + _frame_duration(last_frame))
    return total


def compute_symbol_lengths(animation_json: dict) -> Dict[str, int]:
    """Return a mapping of symbol name to total frame count."""
    lengths: Dict[str, int] = {}
    for symbol in animation_json.get("SD", {}).get("S", []):
        name = symbol.get("SN")
        if not name:
            continue
        layers = symbol.get("TL", {}).get("L", [])
        lengths[name] = compute_layers_length(layers)
    return lengths


def _extract_label_ranges_from_layers(layers: Optional[List[dict]]) -> List[Dict[str, int]]:
    """Internal helper shared by root and nested timelines."""
    labels: List[Dict[str, int]] = []
    if not layers:
        return labels

    for layer in layers:
        frames = layer.get("FR", [])
        for frame in frames:
            label_name = frame.get("N")
            if not label_name:
                continue
            start = int(frame.get("I", 0))
            duration = _frame_duration(frame)
            labels.append({"name": label_name, "start": start, "end": start + duration})
        if labels:
            break

    labels.sort(key=lambda item: item["start"])
    unique: List[Dict[str, int]] = []
    seen = set()
    for entry in labels:
        if entry["name"] in seen:
            continue
        seen.add(entry["name"])
        unique.append(entry)
    return unique


def extract_label_ranges(animation_json: dict, symbol_name: Optional[str] = None) -> List[Dict[str, int]]:
    """Get label ranges for the root timeline or a nested symbol."""
    if symbol_name is None:
        layers = animation_json.get("AN", {}).get("TL", {}).get("L", [])
    else:
        for symbol in animation_json.get("SD", {}).get("S", []):
            if symbol.get("SN") == symbol_name:
                layers = symbol.get("TL", {}).get("L", [])
                break
        else:
            layers = []
    return _extract_label_ranges_from_layers(layers)


def extract_label_ranges_from_layers(layers: Optional[List[dict]]) -> List[Dict[str, int]]:
    """Public helper mirroring the internal implementation."""
    return _extract_label_ranges_from_layers(layers)
