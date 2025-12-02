#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Parser for Aseprite JSON texture atlas metadata.

Aseprite exports sprite sheets with accompanying JSON metadata that includes:
    - Frame data with position, size, trimming, and duration.
    - Frame tags for grouping frames into named animations.
    - Layer and slice metadata.
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, List, Optional, Set

from parsers.base_parser import BaseParser
from parsers.parser_types import (
    FileError,
    FormatError,
    ParseResult,
    ParserErrorCode,
)
from utils.utilities import Utilities


class AsepriteParser(BaseParser):
    """Parse Aseprite JSON atlas files with frame tag support.

    Aseprite's JSON export format uses a hash-style frames dictionary
    with additional metadata including:
        - Per-frame duration for variable-speed animations.
        - Frame tags for grouping frames into named animations.
        - Layer and slice information.

    The parser can extract either:
        - Animation names from frame tags (for UI population).
        - Individual sprite names with trailing digits stripped.
        - Full sprite data with duration for extraction.

    Attributes:
        FILE_EXTENSIONS: Supported file extensions (.json).
    """

    FILE_EXTENSIONS = (".json",)

    # Marker to identify Aseprite JSON files
    ASEPRITE_APP_MARKER = "aseprite.org"

    def __init__(
        self,
        directory: str,
        json_filename: str,
        name_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Initialize the Aseprite parser.

        Args:
            directory: Directory containing the JSON file.
            json_filename: Name of the JSON file.
            name_callback: Optional callback invoked for each extracted name.
        """
        super().__init__(directory, json_filename, name_callback)

    def extract_names(self) -> Set[str]:
        """Extract unique animation/sprite base names from the JSON file.

        If frame tags are present, returns tag names (animation names).
        Otherwise, returns sprite names with trailing digits stripped.

        Returns:
            Set of animation or sprite base names.
        """
        data = self._load_json()

        # Try to get names from frame tags first (preferred for animations)
        meta = data.get("meta", {})
        frame_tags = meta.get("frameTags", [])
        if frame_tags:
            return {tag.get("name", "") for tag in frame_tags if tag.get("name")}

        # Fall back to frame names with digits stripped
        frames: Dict[str, Dict[str, Any]] = data.get("frames", {})
        return {Utilities.strip_trailing_digits(name) for name in frames.keys()}

    def _load_json(self) -> Dict[str, Any]:
        """Load and parse the JSON file.

        Returns:
            Parsed JSON data as a dictionary.

        Raises:
            FileError: If the file cannot be read.
            FormatError: If the JSON is malformed.
        """
        file_path = os.path.join(self.directory, self.filename)
        try:
            with open(file_path, "r", encoding="utf-8") as json_file:
                return json.load(json_file)
        except FileNotFoundError:
            raise FileError(
                ParserErrorCode.FILE_NOT_FOUND,
                f"File not found: {file_path}",
                file_path=file_path,
            )
        except json.JSONDecodeError as e:
            raise FormatError(
                ParserErrorCode.MALFORMED_STRUCTURE,
                f"Invalid JSON: {e}",
                file_path=file_path,
            )

    @classmethod
    def is_aseprite_json(cls, data: Dict[str, Any]) -> bool:
        """Check if JSON data is from Aseprite export.

        Args:
            data: Parsed JSON dictionary.

        Returns:
            True if the data appears to be Aseprite format.
        """
        meta = data.get("meta", {})
        app = meta.get("app", "")

        # Check for Aseprite app marker
        if cls.ASEPRITE_APP_MARKER in app.lower():
            return True

        # Check for Aseprite-specific metadata patterns
        # Aseprite always includes frameTags (even if empty) and layers
        if "frameTags" in meta and "layers" in meta:
            return True

        # Check if frames have duration (Aseprite-specific)
        frames = data.get("frames", {})
        if isinstance(frames, dict) and frames:
            first_frame = next(iter(frames.values()))
            if "duration" in first_frame:
                return True

        return False

    @classmethod
    def parse_from_frames(
        cls,
        frames: Dict[str, Dict[str, Any]],
        meta: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Convert Aseprite frames hash to normalized sprite list.

        Args:
            frames: Dictionary mapping sprite names to frame metadata.
            meta: Optional metadata dict with frameTags for animation info.

        Returns:
            List of normalized sprite dicts with Aseprite-specific fields.
        """
        sprites: List[Dict[str, Any]] = []

        # Build frame tag lookup if available
        frame_tags: List[Dict[str, Any]] = []
        if meta:
            frame_tags = meta.get("frameTags", [])

        # Get ordered list of frame names (Aseprite exports in order)
        for idx, (filename, entry) in enumerate(frames.items()):
            frame = entry.get("frame", {})
            frame_x = int(frame.get("x", 0))
            frame_y = int(frame.get("y", 0))
            frame_w = int(frame.get("w", 0))
            frame_h = int(frame.get("h", 0))

            sprite_source = entry.get("spriteSourceSize", {})
            source_size = entry.get("sourceSize", {})
            rotated = bool(entry.get("rotated", False))
            trimmed = bool(entry.get("trimmed", False))
            duration = int(entry.get("duration", 100))

            sprite_data: Dict[str, Any] = {
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
                "trimmed": trimmed,
                "duration": duration,
            }

            # Find which animation tag this frame belongs to
            for tag in frame_tags:
                tag_from = tag.get("from", 0)
                tag_to = tag.get("to", 0)
                if tag_from <= idx <= tag_to:
                    sprite_data["animation_tag"] = tag.get("name", "")
                    sprite_data["animation_direction"] = tag.get("direction", "forward")
                    break

            sprites.append(sprite_data)

        return sprites

    @classmethod
    def parse_file(cls, file_path: str) -> ParseResult:
        """Parse an Aseprite JSON atlas file.

        Args:
            file_path: Path to the JSON file.

        Returns:
            ParseResult with sprites, warnings, and errors.

        Raises:
            FileError: If the file cannot be read.
            FormatError: If the JSON structure is invalid.
        """
        result = ParseResult(file_path=file_path, parser_name=cls.__name__)

        if not os.path.exists(file_path):
            raise FileError(
                ParserErrorCode.FILE_NOT_FOUND,
                f"File not found: {file_path}",
                file_path=file_path,
            )

        try:
            with open(file_path, "r", encoding="utf-8") as json_file:
                data = json.load(json_file)
        except json.JSONDecodeError as e:
            raise FormatError(
                ParserErrorCode.MALFORMED_STRUCTURE,
                f"Invalid JSON: {e}",
                file_path=file_path,
            )

        # Validate structure
        frames = data.get("frames")
        if frames is None:
            raise FormatError(
                ParserErrorCode.MISSING_FRAMES_KEY,
                "Missing 'frames' key in JSON",
                file_path=file_path,
            )

        if not isinstance(frames, dict):
            raise FormatError(
                ParserErrorCode.INVALID_FORMAT,
                "Expected 'frames' to be a dictionary (hash format)",
                file_path=file_path,
            )

        meta = data.get("meta", {})

        # Parse frames
        raw_sprites = cls.parse_from_frames(frames, meta)

        # Validate and normalize sprites
        for raw_sprite in raw_sprites:
            try:
                normalized = cls.normalize_sprite(raw_sprite)
                # Preserve Aseprite-specific fields
                if "duration" in raw_sprite:
                    normalized["duration"] = raw_sprite["duration"]
                if "animation_tag" in raw_sprite:
                    normalized["animation_tag"] = raw_sprite["animation_tag"]
                if "animation_direction" in raw_sprite:
                    normalized["animation_direction"] = raw_sprite[
                        "animation_direction"
                    ]
                if "trimmed" in raw_sprite:
                    normalized["trimmed"] = raw_sprite["trimmed"]
                result.sprites.append(normalized)
            except Exception as e:
                result.add_error(
                    ParserErrorCode.SPRITE_PARSE_FAILED,
                    f"Failed to parse sprite: {e}",
                    sprite_name=raw_sprite.get("name", "unknown"),
                )

        # Add metadata as warnings for informational purposes
        if "frameTags" in meta and meta["frameTags"]:
            tag_names = [t.get("name", "") for t in meta["frameTags"]]
            result.add_warning(
                ParserErrorCode.UNKNOWN_ERROR,  # Using as info marker
                f"Found {len(tag_names)} animation tags: {', '.join(tag_names)}",
            )

        return result

    @staticmethod
    def parse_json_data(file_path: str) -> List[Dict[str, Any]]:
        """Parse an Aseprite JSON file and return sprite metadata.

        Legacy method for compatibility with base parser interface.

        Args:
            file_path: Path to the JSON file.

        Returns:
            List of sprite dicts with position, dimension, and duration data.
        """
        with open(file_path, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)
        frames = data.get("frames", {})
        meta = data.get("meta", {})
        return AsepriteParser.parse_from_frames(frames, meta)

    @classmethod
    def get_frame_tags(cls, file_path: str) -> List[Dict[str, Any]]:
        """Extract frame tags (animation definitions) from an Aseprite JSON.

        Args:
            file_path: Path to the JSON file.

        Returns:
            List of frame tag dicts with name, from, to, direction, color.
        """
        with open(file_path, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)
        meta = data.get("meta", {})
        return meta.get("frameTags", [])

    @classmethod
    def get_animation_frames(
        cls,
        file_path: str,
        animation_name: str,
    ) -> List[Dict[str, Any]]:
        """Get frames belonging to a specific animation tag.

        Args:
            file_path: Path to the JSON file.
            animation_name: Name of the animation tag.

        Returns:
            List of sprite dicts for frames in the specified animation.
        """
        with open(file_path, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)

        meta = data.get("meta", {})
        frames = data.get("frames", {})
        frame_tags = meta.get("frameTags", [])

        # Find the matching tag
        target_tag = None
        for tag in frame_tags:
            if tag.get("name") == animation_name:
                target_tag = tag
                break

        if not target_tag:
            return []

        # Get frame indices
        from_idx = target_tag.get("from", 0)
        to_idx = target_tag.get("to", 0)

        # Get ordered frame list
        frame_list = list(frames.items())
        animation_frames = []

        for idx in range(from_idx, to_idx + 1):
            if idx < len(frame_list):
                filename, entry = frame_list[idx]
                frame = entry.get("frame", {})
                sprite_source = entry.get("spriteSourceSize", {})
                source_size = entry.get("sourceSize", {})

                sprite_data = {
                    "name": filename,
                    "x": int(frame.get("x", 0)),
                    "y": int(frame.get("y", 0)),
                    "width": int(frame.get("w", 0)),
                    "height": int(frame.get("h", 0)),
                    "frameX": -int(sprite_source.get("x", 0)),
                    "frameY": -int(sprite_source.get("y", 0)),
                    "frameWidth": int(source_size.get("w", frame.get("w", 0))),
                    "frameHeight": int(source_size.get("h", frame.get("h", 0))),
                    "rotated": bool(entry.get("rotated", False)),
                    "duration": int(entry.get("duration", 100)),
                    "animation_tag": animation_name,
                    "animation_direction": target_tag.get("direction", "forward"),
                }
                animation_frames.append(sprite_data)

        return animation_frames


__all__ = ["AsepriteParser"]
