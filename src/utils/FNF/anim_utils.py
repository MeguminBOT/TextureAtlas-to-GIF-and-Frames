#!/usr/bin/env python3
"""Utilities for parsing animation metadata from FNF character files."""
from __future__ import annotations

from typing import List, Optional
from xml.etree.ElementTree import Element


def parse_indices_attribute(raw_indices: Optional[str]) -> Optional[List[int]]:
    """Parse an indices attribute into a list of integers.

    Handles comma-separated values ("0,1,2") and range notation ("0..3").

    Args:
        raw_indices: String containing frame indices.

    Returns:
        List of parsed integers, or None if the input is empty or invalid.
    """
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
    """Extract offset values from a Codename Engine <anim> element.

    Args:
        anim_element: XML element with an 'offset' or 'offsets' attribute.

    Returns:
        Two-element list of [x, y] offsets, or None if not present or invalid.
    """
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
