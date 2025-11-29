#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Parser for legacy CSS spritesheet format without rotation/trim metadata."""

from __future__ import annotations

import os
import re
from typing import Callable, Dict, List, Optional, Set

from parsers.base_parser import BaseParser
from utils.utilities import Utilities


_CLASS_BLOCK_RE = re.compile(
    r"\.([A-Za-z0-9_\-]+)\s*\{([^}]*)\}", re.DOTALL | re.IGNORECASE
)
_BACKGROUND_RE = re.compile(
    r"background\s*:[^;]*?(-?\d+(?:\.\d+)?)px\s+(-?\d+(?:\.\d+)?)px",
    re.IGNORECASE,
)
_WIDTH_RE = re.compile(r"width\s*:\s*(-?\d+(?:\.\d+)?)px", re.IGNORECASE)
_HEIGHT_RE = re.compile(r"height\s*:\s*(-?\d+(?:\.\d+)?)px", re.IGNORECASE)


class CssLegacyParser(BaseParser):
    """Parse the simple CSS export variant (no rotation or trimming)."""

    FILE_EXTENSIONS = (".css",)

    def __init__(
        self,
        directory: str,
        css_filename: str,
        name_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Initialize the legacy CSS parser.

        Args:
            directory: Directory containing the CSS file.
            css_filename: Name of the CSS file.
            name_callback: Optional callback invoked for each extracted name.
        """
        super().__init__(directory, css_filename, name_callback)

    def extract_names(self) -> Set[str]:
        """Extract unique animation/sprite base names from the CSS file.

        Returns:
            Set of sprite names with trailing digits stripped.
        """
        sprites = self._parse_css()
        return {Utilities.strip_trailing_digits(entry["name"]) for entry in sprites}

    def _parse_css(self) -> List[Dict[str, int]]:
        """Parse the CSS file and return sprite metadata.

        Returns:
            List of sprite dicts with position and dimension data.
        """
        file_path = os.path.join(self.directory, self.filename)
        return self.parse_css_data(file_path)

    @staticmethod
    def parse_css_data(file_path: str) -> List[Dict[str, int]]:
        """Parse a CSS file and extract sprite definitions.

        Extracts class blocks matching ``.classname { ... }`` and reads
        background position, width, and height properties.

        Args:
            file_path: Path to the CSS file.

        Returns:
            List of sprite dicts with keys: name, x, y, width, height,
            frameX, frameY, frameWidth, frameHeight, rotated.
        """
        with open(file_path, "r", encoding="utf-8") as css_file:
            content = css_file.read()

        sprites: List[Dict[str, int]] = []
        for match in _CLASS_BLOCK_RE.finditer(content):
            name = match.group(1)
            body = match.group(2)

            bg_match = _BACKGROUND_RE.search(body)
            width_match = _WIDTH_RE.search(body)
            height_match = _HEIGHT_RE.search(body)

            if not (bg_match and width_match and height_match):
                continue

            x_offset = CssLegacyParser._parse_float(bg_match.group(1))
            y_offset = CssLegacyParser._parse_float(bg_match.group(2))
            width_px = CssLegacyParser._parse_float(width_match.group(1))
            height_px = CssLegacyParser._parse_float(height_match.group(1))

            sprite_data = {
                "name": name,
                "x": int(round(-x_offset)),
                "y": int(round(-y_offset)),
                "width": int(round(width_px)),
                "height": int(round(height_px)),
                "frameX": 0,
                "frameY": 0,
                "frameWidth": int(round(width_px)),
                "frameHeight": int(round(height_px)),
                "rotated": False,
            }
            sprites.append(sprite_data)
        return sprites

    @staticmethod
    def _parse_float(value: Optional[str]) -> float:
        """Safely parse a string to float, defaulting to 0.0 on failure.

        Args:
            value: String value to parse.

        Returns:
            Parsed float or 0.0 if parsing fails.
        """
        if value is None:
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0


__all__ = ["CssLegacyParser"]
