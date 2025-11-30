#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Parser for Apple/TexturePacker ``.plist`` atlas metadata files."""

from __future__ import annotations

import os
import plistlib
import re
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from parsers.base_parser import BaseParser
from utils.utilities import Utilities


_RECT_RE = re.compile(
    r"\{\{\s*(-?\d+)\s*,\s*(-?\d+)\s*\},\s*\{\s*(-?\d+)\s*,\s*(-?\d+)\s*\}\}"
)
_SIZE_RE = re.compile(r"\{\s*(-?\d+)\s*,\s*(-?\d+)\s*\}")


class PlistAtlasParser(BaseParser):
    """Parse ``.plist`` metadata exported by Apple/TexturePacker tools."""

    FILE_EXTENSIONS = (".plist",)

    def __init__(
        self,
        directory: str,
        plist_filename: str,
        name_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Initialize the plist parser.

        Args:
            directory: Directory containing the plist file.
            plist_filename: Name of the plist file.
            name_callback: Optional callback invoked for each extracted name.
        """
        super().__init__(directory, plist_filename, name_callback)

    def extract_names(self) -> Set[str]:
        """Extract unique animation/sprite base names from the plist file.

        Returns:
            Set of sprite names with trailing digits stripped.
        """
        plist_data = self._load_plist()
        frames = plist_data.get("frames", {})
        names: Set[str] = set()
        for sprite_name in frames.keys():
            names.add(Utilities.strip_trailing_digits(sprite_name))
        return names

    def _load_plist(self) -> Dict[str, Any]:
        """Load and parse the plist file.

        Returns:
            Parsed plist data as a dictionary.
        """
        file_path = os.path.join(self.directory, self.filename)
        with open(file_path, "rb") as plist_file:
            return plistlib.load(plist_file)

    @classmethod
    def parse_from_frames(
        cls, frames: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Convert a plist frames dict to normalized sprite list.

        Args:
            frames: Dictionary mapping sprite names to frame metadata.

        Returns:
            List of normalized sprite dicts with position and trim data.
        """
        sprites: List[Dict[str, Any]] = []
        for sprite_name, sprite_info in frames.items():
            frame_rect = cls._parse_rect(sprite_info.get("frame"))
            color_rect = cls._parse_rect(sprite_info.get("sourceColorRect"))
            source_size = cls._parse_size(sprite_info.get("sourceSize"))

            sprite_data = {
                "name": sprite_name,
                "x": frame_rect[0],
                "y": frame_rect[1],
                "width": frame_rect[2],
                "height": frame_rect[3],
                "frameX": -color_rect[0],
                "frameY": -color_rect[1],
                "frameWidth": source_size[0] or frame_rect[2],
                "frameHeight": source_size[1] or frame_rect[3],
                "rotated": cls._parse_bool(sprite_info.get("rotated")),
            }
            sprites.append(sprite_data)
        return sprites

    @staticmethod
    def parse_plist_data(file_path: str) -> List[Dict[str, Any]]:
        """Parse a plist atlas file and return sprite metadata.

        Args:
            file_path: Path to the plist file.

        Returns:
            List of sprite dicts with position, dimension, and rotation data.
        """
        with open(file_path, "rb") as plist_file:
            plist_data = plistlib.load(plist_file)
        frames = plist_data.get("frames", {})
        return PlistAtlasParser.parse_from_frames(frames)

    @staticmethod
    def _parse_rect(rect_value: Any) -> Tuple[int, int, int, int]:
        """Parse a rectangle from plist format.

        Args:
            rect_value: Either a nested list/tuple or a string like
                ``{{x,y},{w,h}}``.

        Returns:
            A tuple (x, y, width, height), or (0, 0, 0, 0) on failure.
        """
        if isinstance(rect_value, (list, tuple)) and len(rect_value) == 2:
            (x, y), (w, h) = rect_value
            return int(x), int(y), int(w), int(h)
        if isinstance(rect_value, str):
            match = _RECT_RE.match(rect_value)
            if match:
                return tuple(int(match.group(i)) for i in range(1, 5))  # type: ignore
        return 0, 0, 0, 0

    @staticmethod
    def _parse_size(size_value: Any) -> Tuple[int, int]:
        """Parse a size from plist format.

        Args:
            size_value: Either a list/tuple or a string like ``{w,h}``.

        Returns:
            A tuple (width, height), or (0, 0) on failure.
        """
        if isinstance(size_value, (list, tuple)) and len(size_value) == 2:
            return int(size_value[0]), int(size_value[1])
        if isinstance(size_value, str):
            match = _SIZE_RE.match(size_value)
            if match:
                return int(match.group(1)), int(match.group(2))
        return 0, 0

    @staticmethod
    def _parse_bool(value: Any) -> bool:
        """Parse a boolean from plist format.

        Args:
            value: A bool, or a string like ``'true'`` / ``'yes'`` / ``'1'``.

        Returns:
            The parsed boolean value.
        """
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"true", "yes", "1"}
        return False


__all__ = ["PlistAtlasParser"]
