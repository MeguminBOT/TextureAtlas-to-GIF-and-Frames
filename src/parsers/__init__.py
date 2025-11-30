#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Parsers package for spritesheet/atlas metadata formats.

This package provides unified parsing for various spritesheet and texture atlas
formats including JSON, XML, plist, CSS, and text-based definitions.

Main entry points:
    - ParserRegistry: Auto-detects format and provides unified parsing.
    - parse_file(): Convenience function for parsing any supported format.

Error handling:
    - ParserError: Base exception for all parsing errors.
    - ParseResult: Structured result with sprites, warnings, and errors.

Sprite data:
    - SpriteData: TypedDict defining the canonical sprite structure.
    - normalize_sprite(): Ensures sprites have consistent fields and types.
"""

# Core types - no dependencies on other parser modules
from parsers.parser_types import (
    ContentError,
    FileError,
    FormatError,
    ParseResult,
    ParserError,
    ParserErrorCode,
    ParserWarning,
    SpriteData,
    SpriteError,
    normalize_sprite,
    validate_sprites,
)

from parsers.base_parser import BaseParser


# Lazy import for registry to avoid circular imports
def get_registry():
    """Get the parser registry, initializing if needed."""
    from parsers.parser_registry import ParserRegistry

    if not ParserRegistry._all_parsers:
        ParserRegistry.initialize()
    return ParserRegistry


def parse_file(file_path: str) -> ParseResult:
    """Parse a spritesheet metadata file.

    Convenience wrapper that auto-detects format and uses the appropriate parser.

    Args:
        file_path: Path to the file to parse.

    Returns:
        ParseResult with sprites, warnings, and errors.
    """
    registry = get_registry()
    return registry.parse_file(file_path)


__all__ = [
    # Types and errors
    "ParserErrorCode",
    "SpriteData",
    "ParserError",
    "FileError",
    "FormatError",
    "ContentError",
    "SpriteError",
    "ParserWarning",
    "ParseResult",
    "normalize_sprite",
    "validate_sprites",
    # Base class
    "BaseParser",
    # Functions
    "get_registry",
    "parse_file",
]
