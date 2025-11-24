#!/usr/bin/env python3
"""Helpers for detecting the engine used by a Friday Night Funkin' character file."""
from __future__ import annotations

import json
from typing import Any, Mapping, Tuple
import xml.etree.ElementTree as ET

EngineDetectionResult = Tuple[str, Any]


def detect_engine(file_path: str) -> EngineDetectionResult:
    """Return the engine type and parsed payload for the provided file."""
    if file_path.endswith(".json"):
        return _detect_from_json(file_path)
    if file_path.endswith(".xml"):
        return _detect_from_xml(file_path)
    return "Unknown", None


def _detect_from_json(file_path: str) -> EngineDetectionResult:
    try:
        with open(file_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return "Unknown", None

    if _is_psych_engine(data):
        return "Psych Engine", data
    if _is_kade_engine(data):
        return "Kade Engine", data
    return "Unknown", None


def _detect_from_xml(file_path: str) -> EngineDetectionResult:
    try:
        tree = ET.parse(file_path)
    except (OSError, ET.ParseError):
        return "Unknown", None

    root = tree.getroot()
    if _is_codename_engine(root):
        return "Codename Engine", root
    return "Unknown", None


def _is_psych_engine(data: Any) -> bool:
    animations = data.get("animations") if isinstance(data, Mapping) else None
    if not isinstance(animations, list):
        return False

    required_keys = {"name", "fps", "anim", "loop", "indices"}
    for anim in animations:
        if not isinstance(anim, Mapping):
            return False
        if not required_keys.issubset(anim.keys()):
            return False
        if not isinstance(anim.get("indices"), list):
            return False

    required_top_level = {"image", "scale", "flip_x", "no_antialiasing"}
    return required_top_level.issubset(data.keys())


def _is_kade_engine(data: Any) -> bool:
    if not isinstance(data, Mapping):
        return False
    required_keys = {"name", "asset", "startingAnim", "animations"}
    if not required_keys.issubset(data.keys()):
        return False

    animations = data["animations"]
    if not isinstance(animations, list):
        return False

    for anim in animations:
        if not isinstance(anim, Mapping):
            return False
        if not {"name", "prefix", "offsets"}.issubset(anim.keys()):
            return False
        offsets = anim.get("offsets")
        if not isinstance(offsets, list) or len(offsets) != 2:
            return False
        frame_indices = anim.get("frameIndices")
        if frame_indices is not None and not isinstance(frame_indices, list):
            return False
        looped = anim.get("looped")
        if looped is not None and not isinstance(looped, bool):
            return False
    return True


def _is_codename_engine(root: ET.Element) -> bool:
    if root.tag != "character":
        return False

    for anim in root.findall("anim"):
        attrib = anim.attrib
        if not {"name", "anim", "fps", "loop"}.issubset(attrib):
            return False
        indices = attrib.get("indices")
        if indices is not None and ".." not in indices:
            return False
    return True
