#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Parser for simple text-based spritesheet metadata (name = x y w h)."""

from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Optional, Set

from parsers.base_parser import BaseParser
from parsers.parser_types import (
    ContentError,
    FormatError,
    ParseResult,
    ParserErrorCode,
)
from utils.utilities import Utilities


class TxtParser(BaseParser):
    """Parse text files with 'name = x y w h' sprite definitions."""

    FILE_EXTENSIONS = (".txt",)

    def __init__(
        self,
        directory: str,
        txt_filename: str,
        name_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Initialize the TXT parser.

        Args:
            directory: Directory containing the text file.
            txt_filename: Name of the text file.
            name_callback: Optional callback invoked for each extracted name.
        """
        super().__init__(directory, txt_filename, name_callback)

    def extract_names(self) -> Set[str]:
        """Extract unique animation/sprite base names from the text file.

        Returns:
            Set of sprite names with trailing digits stripped.
        """
        names: Set[str] = set()
        txt_path = os.path.join(self.directory, self.filename)
        with open(txt_path, "r", encoding="utf-8") as txt_file:
            for raw_line in txt_file:
                line = raw_line.strip()
                if " = " not in line:
                    continue
                name = line.split(" = ", 1)[0].strip()
                sanitized_name = Utilities.strip_trailing_digits(name) or name
                names.add(sanitized_name)
        return names

    @classmethod
    def parse_file(cls, file_path: str) -> ParseResult:
        """Parse a TXT spritesheet file with full error handling.

        Args:
            file_path: Path to the TXT file.

        Returns:
            ParseResult with parsed sprites and any errors.
        """
        result = ParseResult(file_path=file_path, parser_name=cls.__name__)

        try:
            raw_sprites = cls.parse_txt_packer(file_path)
            validated = cls.validate_sprites(raw_sprites, file_path)
            result.sprites = validated.sprites
            result.warnings = validated.warnings
            result.errors = validated.errors
        except ContentError as e:
            result.add_error(e.code, e.message, details=e.details)
        except FormatError as e:
            result.add_error(e.code, e.message, details=e.details)
        except FileNotFoundError:
            result.add_error(
                ParserErrorCode.FILE_NOT_FOUND,
                f"File not found: {file_path}",
            )
        except UnicodeDecodeError as e:
            result.add_error(
                ParserErrorCode.FILE_ENCODING_ERROR,
                f"Encoding error: {e}",
            )
        except Exception as e:
            result.add_error(
                ParserErrorCode.UNKNOWN_ERROR,
                f"Unexpected error: {e}",
                details={"exception_type": type(e).__name__},
            )

        return result

    @staticmethod
    def parse_txt_packer(file_path: str) -> List[Dict[str, Any]]:
        """Parse a TXT file and return raw sprite dicts.

        Args:
            file_path: Path to the TXT file.

        Returns:
            List of sprite dicts with name, x, y, width, height, etc.

        Raises:
            FormatError: If the file has no valid sprite definitions.
        """
        sprites: List[Dict[str, Any]] = []

        with open(file_path, "r", encoding="utf-8") as file:
            for line_num, raw_line in enumerate(file, start=1):
                line = raw_line.strip()
                if not line or " = " not in line:
                    continue

                parts = line.split(" = ")
                if len(parts) != 2:
                    continue

                name = parts[0].strip()
                coords = parts[1].strip().split()

                if len(coords) < 4:
                    continue

                try:
                    x, y, width, height = map(int, coords[:4])
                except ValueError:
                    continue

                sprite_data: Dict[str, Any] = {
                    "name": name,
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height,
                    "frameX": 0,
                    "frameY": 0,
                    "frameWidth": width,
                    "frameHeight": height,
                    "rotated": False,
                }
                sprites.append(sprite_data)

        if not sprites:
            raise FormatError(
                ParserErrorCode.EMPTY_SPRITE_LIST,
                "No valid sprite definitions found in TXT file",
                file_path=file_path,
            )

        return sprites


__all__ = ["TxtParser"]
