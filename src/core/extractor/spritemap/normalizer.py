#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Normalize Adobe Animate spritemap JSON into a consistent abbreviated format.

Adobe Animate exports spritemap data in two forms:
  - **Optimized**: Compact keys (``AN``, ``SD``, ``TL``, ``FR``, etc.)
  - **Verbose**: Descriptive keys (``ANIMATION``, ``TIMELINE``, ``LAYERS``, etc.)

This module ensures all Animation.json documents use the optimized schema
regardless of export settings. The :func:`normalize_animation_document`
function detects verbose structures and transforms them into the abbreviated
layout, allowing the rest of the extraction pipeline to work with a single
predictable format.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

IDENTITY_M3D: List[float] = [
    1.0,
    0.0,
    0.0,
    0.0,
    0.0,
    1.0,
    0.0,
    0.0,
    0.0,
    0.0,
    1.0,
    0.0,
    0.0,
    0.0,
    0.0,
    1.0,
]

LOOP_MAP = {
    "loop": "LP",
    "play once": "PO",
    "single frame": "SF",
    "singleframe": "SF",
}

SYMBOL_TYPE_MAP = {
    "graphic": "G",
    "graphics": "G",
    "movie clip": "MC",
    "movieclip": "MC",
    "button": "BTN",
}


def normalize_animation_document(data: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of *data* with optimized spritemap keys.

    Args:
        data: Parsed Animation.json payload.

    Returns:
        Dict guaranteed to expose the abbreviated ``AN`` / ``SD`` layout.
    """

    if not isinstance(data, dict):
        return data

    if "AN" in data and "SD" in data:
        return data

    verbose_key_candidates = {
        key.lower(): key for key in data.keys() if isinstance(key, str)
    }
    has_verbose_keys = (
        "animation" in verbose_key_candidates
        or "symbol_dictionary" in verbose_key_candidates
    )
    if not has_verbose_keys:
        return data

    normalized = dict(data)

    animation_section = _normalize_animation_section(
        _get_first(data, "ANIMATION", "animation")
    )
    if animation_section:
        normalized["AN"] = animation_section

    symbol_dictionary = _normalize_symbol_dictionary(
        _get_first(data, "SYMBOL_DICTIONARY", "symbolDictionary")
    )
    if symbol_dictionary:
        normalized["SD"] = symbol_dictionary

    metadata_section = _normalize_metadata(_get_first(data, "metadata", "MD"))
    if metadata_section:
        merged = dict(normalized.get("MD", {}))
        merged.update(metadata_section)
        normalized["MD"] = merged

    return normalized


def _normalize_animation_section(section: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize the root ``ANIMATION`` section into the abbreviated shape."""
    if not isinstance(section, dict):
        return {}

    timeline = _normalize_timeline(_get_first(section, "TIMELINE", "timeline"))
    normalized: Dict[str, Any] = {}
    name = _get_first(section, "name", "NAME")
    if name:
        normalized["N"] = name
    symbol_name = _get_first(
        section,
        "SYMBOL_name",
        "symbol_name",
        "SYMBOLName",
        "symbolName",
    )
    if symbol_name:
        normalized["SN"] = symbol_name
    if timeline:
        normalized["TL"] = timeline
    return normalized


def _normalize_symbol_dictionary(section: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Convert ``symbolDictionary`` entries into the compact ``SD`` layout."""
    if not isinstance(section, dict):
        return {}

    symbols: List[Dict[str, Any]] = []
    symbols_source = _get_first(section, "Symbols", "symbols") or []
    for symbol in symbols_source:
        if not isinstance(symbol, dict):
            continue
        normalized_symbol: Dict[str, Any] = {}
        symbol_name = _get_first(
            symbol,
            "SYMBOL_name",
            "symbol_name",
            "SYMBOLName",
            "symbolName",
        )
        if symbol_name:
            normalized_symbol["SN"] = symbol_name
        timeline = _normalize_timeline(_get_first(symbol, "TIMELINE", "timeline"))
        if timeline:
            normalized_symbol["TL"] = timeline
        if normalized_symbol:
            symbols.append(normalized_symbol)
    if symbols:
        return {"S": symbols}
    return {}


def _normalize_timeline(section: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize timeline layers from verbose ``LAYERS`` definitions."""
    if not isinstance(section, dict):
        return {}

    layers_source = _get_first(section, "LAYERS", "layers") or []
    layers = [
        layer for layer in (_normalize_layer(entry) for entry in layers_source) if layer
    ]
    if layers:
        return {"L": layers}
    return {}


def _normalize_layer(layer: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Convert a single layer definition and its frames into ``FR`` blocks."""
    if not isinstance(layer, dict):
        return {}

    frames_source = _get_first(layer, "Frames", "frames", "FRAMES") or []
    frames = [
        frame for frame in (_normalize_frame(entry) for entry in frames_source) if frame
    ]
    normalized: Dict[str, Any] = {}
    name = _get_first(layer, "Layer_name", "layerName", "name")
    if name:
        normalized["LN"] = name
    if frames:
        normalized["FR"] = frames
    layer_type = (_get_first(layer, "layerType", "Layer_type") or "").lower()
    if _truthy(layer.get("isClippingLayer")) or layer_type == "clipping":
        normalized["LT"] = "Clp"
    if _truthy(layer.get("hasClippingMask")):
        normalized["Clpb"] = True
    return normalized


def _normalize_frame(frame: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Translate a frame record plus its elements into the shorthand form."""
    if not isinstance(frame, dict):
        return {}

    elements_source = _get_first(frame, "E", "elements", "Elements") or []
    elements = [
        element
        for element in (_normalize_element(entry) for entry in elements_source)
        if element
    ]
    normalized: Dict[str, Any] = {
        "I": _safe_int(_get_first(frame, "I", "index"), default=0),
        "DU": max(1, _safe_int(_get_first(frame, "DU", "duration"), default=1)),
        "E": elements,
    }
    label = _get_first(frame, "N", "name", "label")
    if label:
        normalized["N"] = label
    return normalized


def _normalize_element(element: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize symbol or atlas instances embedded inside a frame."""
    if not isinstance(element, dict):
        return {}

    if "ASI" in element:
        return element
    if "SI" in element:
        bitmap_instance = _normalize_symbol_bitmap(element.get("SI"))
        if bitmap_instance:
            return {"ASI": bitmap_instance}
        return element

    symbol_instance = _get_first(
        element,
        "SI",
        "SYMBOL_Instance",
        "symbol_instance",
        "symbolInstance",
    )
    if symbol_instance is not None:
        bitmap_instance = _normalize_symbol_bitmap(symbol_instance)
        if bitmap_instance:
            return {"ASI": bitmap_instance}
        symbol = _normalize_symbol_instance(symbol_instance)
        if symbol:
            return {"SI": symbol}
    atlas_instance = _get_first(
        element,
        "ASI",
        "ATLAS_SPRITE_instance",
        "atlas_sprite_instance",
        "atlasSpriteInstance",
    )
    if atlas_instance is not None:
        atlas = _normalize_atlas_instance(atlas_instance)
        if atlas:
            return {"ASI": atlas}
    return {}


def _normalize_symbol_instance(instance: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Convert verbose symbol instance dictionaries into ``SI`` payloads."""
    if not isinstance(instance, dict):
        return {}

    normalized: Dict[str, Any] = {}
    symbol_name = _get_first(
        instance,
        "SN",
        "SYMBOL_name",
        "symbol_name",
        "SYMBOLName",
        "symbolName",
    )
    if symbol_name:
        normalized["SN"] = symbol_name
    instance_name = _get_first(instance, "IN", "Instance_Name", "instanceName")
    if instance_name is not None:
        normalized["IN"] = instance_name
    symbol_type = (
        _get_first(instance, "ST", "symbolType", "symbol_type") or ""
    ).lower()
    normalized["ST"] = SYMBOL_TYPE_MAP.get(symbol_type, symbol_type.upper() or "G")
    normalized["FF"] = _safe_int(_get_first(instance, "FF", "firstFrame"), default=0)
    loop_mode = _get_first(instance, "LP", "loop", "Loop")
    if isinstance(loop_mode, str):
        normalized["LP"] = LOOP_MAP.get(loop_mode.lower(), loop_mode)
    elif loop_mode is not None:
        normalized["LP"] = loop_mode
    transform_point = _get_first(
        instance,
        "TRP",
        "transformationPoint",
        "transformPoint",
    )
    if isinstance(transform_point, dict):
        normalized["TRP"] = {
            "x": float(transform_point.get("x", 0.0)),
            "y": float(transform_point.get("y", 0.0)),
        }
    normalized["M3D"] = _normalize_matrix(_get_first(instance, "M3D", "Matrix3D"))
    color_effect = _get_first(instance, "C", "colorEffect", "colourEffect")
    if color_effect is not None:
        normalized["C"] = color_effect
    return normalized


def _normalize_symbol_bitmap(instance: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Convert a symbol instance that only references a bitmap into ``ASI``."""
    if not isinstance(instance, dict):
        return {}
    bitmap = instance.get("bitmap")
    if not isinstance(bitmap, dict):
        return {}
    name = bitmap.get("name")
    if not name:
        return {}
    normalized: Dict[str, Any] = {"N": name}
    normalized["M3D"] = _normalize_matrix(_get_first(instance, "M3D", "Matrix3D"))
    return normalized


def _normalize_atlas_instance(instance: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize atlas sprite instances into ``ASI`` structures."""
    if not isinstance(instance, dict):
        return {}

    normalized: Dict[str, Any] = {}
    name = _get_first(instance, "N", "name", "Name")
    if name:
        normalized["N"] = name
    normalized["M3D"] = _normalize_matrix(
        _get_first(instance, "M3D", "Matrix3D", "matrix3D")
    )
    return normalized


def _normalize_matrix(matrix: Optional[Any]) -> List[float]:
    """Return a 16-value matrix list no matter the incoming representation."""
    if isinstance(matrix, list) and len(matrix) == 16:
        return matrix
    if isinstance(matrix, dict):
        return [
            _get_first(matrix, "m00", "M00") or 1.0,
            _get_first(matrix, "m01", "M01") or 0.0,
            _get_first(matrix, "m02", "M02") or 0.0,
            _get_first(matrix, "m03", "M03") or 0.0,
            _get_first(matrix, "m10", "M10") or 0.0,
            _get_first(matrix, "m11", "M11") or 1.0,
            _get_first(matrix, "m12", "M12") or 0.0,
            _get_first(matrix, "m13", "M13") or 0.0,
            _get_first(matrix, "m20", "M20") or 0.0,
            _get_first(matrix, "m21", "M21") or 0.0,
            _get_first(matrix, "m22", "M22") or 1.0,
            _get_first(matrix, "m23", "M23") or 0.0,
            _get_first(matrix, "m30", "M30") or 0.0,
            _get_first(matrix, "m31", "M31") or 0.0,
            _get_first(matrix, "m32", "M32") or 0.0,
            _get_first(matrix, "m33", "M33") or 1.0,
        ]
    return list(IDENTITY_M3D)


def _normalize_metadata(section: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract frame-rate metadata from verbose ``metadata`` blocks."""
    if not isinstance(section, dict):
        return {}
    framerate = section.get("framerate") or section.get("frameRate")
    if framerate is None:
        return {}
    try:
        framerate_value = float(framerate)
    except (TypeError, ValueError):
        return {}
    return {"FRT": framerate_value}


def _safe_int(value: Optional[Any], default: int = 0) -> int:
    """Return ``value`` coerced to ``int`` or the provided default."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _get_first(container: Optional[Dict[str, Any]], *keys: str) -> Any:
    """Fetch the first key present in ``container`` (case insensitive)."""
    if not isinstance(container, dict):
        return None
    for key in keys:
        if key in container:
            return container[key]
    lowercase_map = None
    for key in keys:
        if not isinstance(key, str):
            continue
        if lowercase_map is None:
            lowercase_map = {
                existing_key.lower(): existing_key
                for existing_key in container.keys()
                if isinstance(existing_key, str)
            }
        match = lowercase_map.get(key.lower())
        if match is not None:
            return container[match]
    return None


def _truthy(value: Any) -> bool:
    """Return ``True`` if the provided value is truthy or affirmative text."""
    if isinstance(value, str):
        return value.lower() in {"true", "1", "yes"}
    return bool(value)


__all__ = ["normalize_animation_document"]
