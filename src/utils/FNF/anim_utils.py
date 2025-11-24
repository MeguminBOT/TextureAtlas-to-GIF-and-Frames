#!/usr/bin/env python3
"""Helpers for parsing animation metadata from FNF character files."""
from __future__ import annotations

from typing import List, Optional
from xml.etree.ElementTree import Element


def parse_indices_attribute(raw_indices: Optional[str]) -> Optional[List[int]]:
    """Convert an indices attribute ("0,1" or "0..3") into explicit integers."""
    if not raw_indices:
        return None

    if ".." in raw_indices:
        try:
            return [int(i) for i in raw_indices.split("..")]
        except (TypeError, ValueError):
            return None

    indices: List[int] = []
    for chunk in raw_indices.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            indices.append(int(chunk))
        except (TypeError, ValueError):
            return None
    return indices or None


def parse_xml_offsets(anim_element: Element) -> Optional[List[int]]:
    """Extract offsets from a Codename Engine <anim> element."""
    raw_value = anim_element.attrib.get("offset") or anim_element.attrib.get("offsets")
    if not raw_value:
        return None

    cleaned = [
        part.strip() for part in raw_value.replace(" ", "").split(",") if part.strip()
    ]
    if len(cleaned) != 2:
        return None

    try:
        return [int(cleaned[0]), int(cleaned[1])]
    except (TypeError, ValueError):
        return None
