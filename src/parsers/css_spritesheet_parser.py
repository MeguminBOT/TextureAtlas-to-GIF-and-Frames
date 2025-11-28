#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Parser for CSS-based spritesheet definitions."""

from __future__ import annotations

import os
import re
from typing import Any, Callable, Dict, List, Optional, Set

from parsers.base_parser import BaseParser
from utils.utilities import Utilities


_CLASS_BLOCK_RE = re.compile(r"\.([A-Za-z0-9_\-]+)\s*\{([^}]*)\}", re.DOTALL)
_BACKGROUND_RE = re.compile(
    r"background\s*:[^;]*?(-?\d+(?:\.\d+)?)px\s+(-?\d+(?:\.\d+)?)px",
    re.IGNORECASE,
)
_WIDTH_RE = re.compile(r"width\s*:\s*(-?\d+(?:\.\d+)?)px", re.IGNORECASE)
_HEIGHT_RE = re.compile(r"height\s*:\s*(-?\d+(?:\.\d+)?)px", re.IGNORECASE)
_MARGIN_LEFT_RE = re.compile(r"margin-left\s*:\s*(-?\d+(?:\.\d+)?)px", re.IGNORECASE)
_MARGIN_TOP_RE = re.compile(r"margin-top\s*:\s*(-?\d+(?:\.\d+)?)px", re.IGNORECASE)
_ROTATE_RE = re.compile(
    r"transform\s*:\s*[^;]*rotate\s*\(\s*-?90deg\s*\)", re.IGNORECASE
)


class CssSpriteSheetParser(BaseParser):
    """Parse CSS files emitted by spritesheet generators."""

    FILE_EXTENSIONS = (".css",)

    def __init__(
        self,
        directory: str,
        css_filename: str,
        name_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Initialize the CSS spritesheet parser.

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

    def _parse_css(self) -> List[Dict[str, Any]]:
        """Parse the CSS file and return sprite metadata.

        Returns:
            List of sprite dicts with position, dimension, and rotation data.
        """
        file_path = os.path.join(self.directory, self.filename)
        return self.parse_css_data(file_path)

    @staticmethod
    def parse_css_data(file_path: str) -> List[Dict[str, Any]]:
        """Parse a CSS file and extract sprite definitions.

        Supports rotation via ``transform: rotate(-90deg)`` and trim offsets
        via ``margin-left`` / ``margin-top`` properties.

        Args:
            file_path: Path to the CSS file.

        Returns:
            List of sprite dicts with keys: name, x, y, width, height,
            frameX, frameY, frameWidth, frameHeight, rotated.
        """
        with open(file_path, "r", encoding="utf-8") as css_file:
            content = css_file.read()

        sprites: List[Dict[str, Any]] = []
        for match in _CLASS_BLOCK_RE.finditer(content):
            name = match.group(1)
            body = match.group(2)

            bg_match = _BACKGROUND_RE.search(body)
            width_match = _WIDTH_RE.search(body)
            height_match = _HEIGHT_RE.search(body)

            if not (bg_match and width_match and height_match):
                continue

            x_offset = CssSpriteSheetParser._parse_float(bg_match.group(1))
            y_offset = CssSpriteSheetParser._parse_float(bg_match.group(2))
            width_px = CssSpriteSheetParser._parse_float(width_match.group(1))
            height_px = CssSpriteSheetParser._parse_float(height_match.group(1))

            rotated = bool(_ROTATE_RE.search(body))
            margin_left = CssSpriteSheetParser._parse_float(
                CssSpriteSheetParser._extract_value(_MARGIN_LEFT_RE, body)
            )
            margin_top = CssSpriteSheetParser._parse_float(
                CssSpriteSheetParser._extract_value(_MARGIN_TOP_RE, body)
            )

            if rotated:
                sprite_width = height_px
                sprite_height = width_px
            else:
                sprite_width = width_px
                sprite_height = height_px

            sprite_data = {
                "name": name,
                "x": int(round(-x_offset)),
                "y": int(round(-y_offset)),
                "width": int(round(sprite_width)),
                "height": int(round(sprite_height)),
                "frameX": -int(round(margin_left)),
                "frameY": -int(round(margin_top)),
                "frameWidth": int(round(sprite_width)),
                "frameHeight": int(round(sprite_height)),
                "rotated": rotated,
            }
            sprites.append(sprite_data)
        return sprites

    @staticmethod
    def _extract_value(pattern: re.Pattern[str], body: str) -> Optional[str]:
        """Extract the first capture group from a regex match.

        Args:
            pattern: Compiled regex pattern with at least one group.
            body: String to search.

        Returns:
            First captured group or None if no match.
        """
        match = pattern.search(body)
        return match.group(1) if match else None

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


__all__ = ["CssSpriteSheetParser"]
