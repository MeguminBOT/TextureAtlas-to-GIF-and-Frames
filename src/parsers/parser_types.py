#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Unified types and error handling for all spritesheet/atlas parsers.

This module defines:
    - SpriteData: TypedDict describing the canonical sprite structure.
    - ParserError hierarchy: Typed exceptions for parsing failures.
    - ParseResult: Dataclass holding parsed sprites, warnings, and errors.
    - ParserErrorCode: Enum of error categories for programmatic handling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, TypedDict


class ParserErrorCode(Enum):
    """Categorized error codes for parser failures."""

    # File-level errors
    FILE_NOT_FOUND = auto()
    FILE_READ_ERROR = auto()
    FILE_ENCODING_ERROR = auto()

    # Format-level errors
    INVALID_FORMAT = auto()
    UNSUPPORTED_FORMAT = auto()
    MALFORMED_STRUCTURE = auto()

    # Content-level errors
    MISSING_REQUIRED_KEY = auto()
    INVALID_VALUE_TYPE = auto()
    INVALID_COORDINATE = auto()
    NEGATIVE_DIMENSION = auto()
    ZERO_DIMENSION = auto()

    # Sprite-level errors
    SPRITE_PARSE_FAILED = auto()
    SPRITE_OUT_OF_BOUNDS = auto()
    DUPLICATE_SPRITE_NAME = auto()

    # Metadata errors
    MISSING_FRAMES_KEY = auto()
    MISSING_TEXTURES_KEY = auto()
    EMPTY_SPRITE_LIST = auto()

    # Unknown/fallback
    UNKNOWN_ERROR = auto()


class SpriteData(TypedDict, total=False):
    """Canonical sprite dictionary structure.

    All parsers must normalize their output to this format.

    Required keys:
        name: Sprite identifier (filename or frame name).
        x: X position in atlas texture (pixels).
        y: Y position in atlas texture (pixels).
        width: Cropped sprite width (pixels).
        height: Cropped sprite height (pixels).

    Optional keys:
        frameX: Horizontal offset for trimmed sprites (default: 0).
        frameY: Vertical offset for trimmed sprites (default: 0).
        frameWidth: Original frame width before trimming (default: width).
        frameHeight: Original frame height before trimming (default: height).
        rotated: True if sprite is rotated 90 degrees in atlas (default: False).
        pivotX: Horizontal pivot point 0.0-1.0 (optional).
        pivotY: Vertical pivot point 0.0-1.0 (optional).
    """

    # Required keys
    name: str
    x: int
    y: int
    width: int
    height: int

    # Optional keys with defaults
    frameX: int
    frameY: int
    frameWidth: int
    frameHeight: int
    rotated: bool
    pivotX: float
    pivotY: float


class ParserError(Exception):
    """Base exception for all parser errors.

    Attributes:
        code: Categorized error code for programmatic handling.
        message: Human-readable error description.
        file_path: Path to the file that caused the error.
        details: Optional dict with additional context (line number, key, etc.).
    """

    def __init__(
        self,
        code: ParserErrorCode,
        message: str,
        file_path: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.code = code
        self.message = message
        self.file_path = file_path
        self.details = details or {}
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        parts = [self.message]
        if self.file_path:
            parts.append(f"File: {self.file_path}")
        if self.details:
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            parts.append(f"Details: {detail_str}")
        return " | ".join(parts)


class FileError(ParserError):
    """Error reading or accessing a file."""

    pass


class FormatError(ParserError):
    """Error in file structure or format."""

    pass


class ContentError(ParserError):
    """Error in file content (missing keys, invalid values)."""

    pass


class SpriteError(ParserError):
    """Error parsing a specific sprite entry."""

    def __init__(
        self,
        code: ParserErrorCode,
        message: str,
        sprite_name: Optional[str] = None,
        file_path: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        details = details or {}
        if sprite_name:
            details["sprite_name"] = sprite_name
        super().__init__(code, message, file_path, details)
        self.sprite_name = sprite_name


@dataclass
class ParserWarning:
    """Non-fatal issue detected during parsing.

    Attributes:
        code: Categorized warning code.
        message: Human-readable description.
        sprite_name: Name of affected sprite, if applicable.
        details: Additional context.
    """

    code: ParserErrorCode
    message: str
    sprite_name: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class ParseResult:
    """Container for parser output with full diagnostics.

    Attributes:
        sprites: List of successfully parsed sprite dicts.
        warnings: Non-fatal issues encountered during parsing.
        errors: Fatal errors for specific sprites (partial failures).
        file_path: Path to the parsed file.
        parser_name: Name of the parser class used.
        is_valid: True if parsing produced usable sprites.
    """

    sprites: List[SpriteData] = field(default_factory=list)
    warnings: List[ParserWarning] = field(default_factory=list)
    errors: List[SpriteError] = field(default_factory=list)
    file_path: Optional[str] = None
    parser_name: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        """Return True if at least one sprite was successfully parsed."""
        return len(self.sprites) > 0

    @property
    def sprite_count(self) -> int:
        """Return count of successfully parsed sprites."""
        return len(self.sprites)

    @property
    def warning_count(self) -> int:
        """Return count of warnings."""
        return len(self.warnings)

    @property
    def error_count(self) -> int:
        """Return count of sprite-level errors."""
        return len(self.errors)

    def add_warning(
        self,
        code: ParserErrorCode,
        message: str,
        sprite_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a warning to the result."""
        self.warnings.append(ParserWarning(code, message, sprite_name, details))

    def add_error(
        self,
        code: ParserErrorCode,
        message: str,
        sprite_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a sprite-level error to the result."""
        self.errors.append(
            SpriteError(code, message, sprite_name, self.file_path, details)
        )

    def get_summary(self) -> str:
        """Return a human-readable summary of the parse result."""
        status = "success" if self.is_valid else "failed"
        parts = [
            f"Parse {status}: {self.sprite_count} sprites",
            f"{self.warning_count} warnings",
            f"{self.error_count} errors",
        ]
        if self.file_path:
            parts.insert(0, f"File: {self.file_path}")
        return " | ".join(parts)


def normalize_sprite(sprite: Dict[str, Any]) -> SpriteData:
    """Normalize a raw sprite dict to the canonical SpriteData format.

    Ensures all required fields are present and have correct types.
    Optional fields get sensible defaults.

    Args:
        sprite: Raw sprite dict from a parser.

    Returns:
        Normalized SpriteData with guaranteed fields and types.

    Raises:
        ContentError: If required fields are missing or have invalid values.
    """
    # Extract required fields with validation
    name = sprite.get("name")
    if not name:
        raise ContentError(
            ParserErrorCode.MISSING_REQUIRED_KEY,
            "Sprite missing required 'name' field",
            details={"sprite": str(sprite)[:100]},
        )

    try:
        x = int(sprite.get("x", 0))
        y = int(sprite.get("y", 0))
        width = int(sprite.get("width", 0))
        height = int(sprite.get("height", 0))
    except (TypeError, ValueError) as e:
        raise ContentError(
            ParserErrorCode.INVALID_VALUE_TYPE,
            f"Invalid coordinate value for sprite '{name}': {e}",
            details={"sprite_name": name},
        )

    # Validate dimensions
    if width <= 0 or height <= 0:
        raise ContentError(
            ParserErrorCode.ZERO_DIMENSION,
            f"Sprite '{name}' has zero or negative dimensions: {width}x{height}",
            details={"sprite_name": name, "width": width, "height": height},
        )

    # Extract optional fields with defaults
    frame_x = int(sprite.get("frameX", 0))
    frame_y = int(sprite.get("frameY", 0))
    frame_width = int(sprite.get("frameWidth", 0)) or width
    frame_height = int(sprite.get("frameHeight", 0)) or height
    rotated = bool(sprite.get("rotated", False))

    result: SpriteData = {
        "name": str(name),
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "frameX": frame_x,
        "frameY": frame_y,
        "frameWidth": frame_width,
        "frameHeight": frame_height,
        "rotated": rotated,
    }

    # Include optional pivot if present
    if "pivotX" in sprite:
        result["pivotX"] = float(sprite["pivotX"])
    if "pivotY" in sprite:
        result["pivotY"] = float(sprite["pivotY"])

    return result


def validate_sprites(
    sprites: List[Dict[str, Any]],
    file_path: Optional[str] = None,
) -> ParseResult:
    """Validate and normalize a list of raw sprite dicts.

    Attempts to normalize each sprite, collecting successes and failures.
    Returns a ParseResult that can be used even if some sprites failed.

    Args:
        sprites: List of raw sprite dicts from a parser.
        file_path: Path to the source file for error context.

    Returns:
        ParseResult with normalized sprites, warnings, and errors.
    """
    result = ParseResult(file_path=file_path)

    for i, raw_sprite in enumerate(sprites):
        sprite_name = raw_sprite.get("name", f"sprite_{i}")
        try:
            normalized = normalize_sprite(raw_sprite)
            result.sprites.append(normalized)
        except ContentError as e:
            result.add_error(
                e.code,
                e.message,
                sprite_name=sprite_name,
                details=e.details,
            )
        except Exception as e:
            result.add_error(
                ParserErrorCode.SPRITE_PARSE_FAILED,
                f"Unexpected error normalizing sprite: {e}",
                sprite_name=sprite_name,
            )

    # Add warning if no sprites were parsed
    if not result.sprites and sprites:
        result.add_warning(
            ParserErrorCode.EMPTY_SPRITE_LIST,
            f"All {len(sprites)} sprites failed validation",
        )

    return result


__all__ = [
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
]
