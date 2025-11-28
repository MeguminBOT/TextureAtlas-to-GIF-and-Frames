#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Parser for hash-style JSON atlas metadata."""

from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, List, Optional, Set

from parsers.base_parser import BaseParser
from utils.utilities import Utilities


class JsonHashAtlasParser(BaseParser):
    """Parse atlas JSON where ``frames`` is a mapping from name to metadata."""

    FILE_EXTENSIONS = (".json",)

    def __init__(
        self,
        directory: str,
        json_filename: str,
        name_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Initialize the JSON hash parser.

        Args:
            directory: Directory containing the JSON file.
            json_filename: Name of the JSON file.
            name_callback: Optional callback invoked for each extracted name.
        """
        super().__init__(directory, json_filename, name_callback)

    def extract_names(self) -> Set[str]:
        """Extract unique animation/sprite base names from the JSON file.

        Returns:
            Set of sprite names with trailing digits stripped.
        """
        data = self._load_json()
        frames: Dict[str, Dict[str, Any]] = data.get("frames", {})
        return {Utilities.strip_trailing_digits(name) for name in frames.keys()}

    def _load_json(self) -> Dict[str, Any]:
        """Load and parse the JSON file.

        Returns:
            Parsed JSON data as a dictionary.
        """
        file_path = os.path.join(self.directory, self.filename)
        with open(file_path, "r", encoding="utf-8") as json_file:
            return json.load(json_file)

    @classmethod
    def parse_from_frames(
        cls, frames: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Convert a frames hash to normalized sprite list.

        Args:
            frames: Dictionary mapping sprite names to frame metadata.

        Returns:
            List of normalized sprite dicts with pivot information.
        """
        sprites: List[Dict[str, Any]] = []
        for filename, entry in frames.items():
            frame = entry.get("frame", {})
            frame_x = int(frame.get("x", 0))
            frame_y = int(frame.get("y", 0))
            frame_w = int(frame.get("w", 0))
            frame_h = int(frame.get("h", 0))

            sprite_source = entry.get("spriteSourceSize", {})
            source_size = entry.get("sourceSize", {})
            rotated = bool(entry.get("rotated", False))

            sprite_data = {
                "name": filename,
                "x": frame_x,
                "y": frame_y,
                "width": frame_w,
                "height": frame_h,
                "frameX": -int(sprite_source.get("x", 0)),
                "frameY": -int(sprite_source.get("y", 0)),
                "frameWidth": int(source_size.get("w", frame_w)),
                "frameHeight": int(source_size.get("h", frame_h)),
                "rotated": rotated,
                "pivotX": float(entry.get("pivot", {}).get("x", 0.5)),
                "pivotY": float(entry.get("pivot", {}).get("y", 0.5)),
            }
            sprites.append(sprite_data)
        return sprites

    @staticmethod
    def parse_json_data(file_path: str) -> List[Dict[str, Any]]:
        """Parse a JSON hash atlas file and return sprite metadata.

        Args:
            file_path: Path to the JSON file.

        Returns:
            List of sprite dicts with position, dimension, and pivot data.
        """
        with open(file_path, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)
        frames = data.get("frames", {})
        return JsonHashAtlasParser.parse_from_frames(frames)


__all__ = ["JsonHashAtlasParser"]
