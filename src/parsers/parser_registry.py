#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Parser registry for automatic format detection and unified parsing.

This module provides:
    - ParserRegistry: Central registry of all available parsers.
    - Auto-detection of file formats based on extension and content.
    - Unified parse_file() entry point for the extraction pipeline.
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Type

from parsers.base_parser import BaseParser
from parsers.parser_types import (
    FileError,
    FormatError,
    ParseResult,
    ParserErrorCode,
)


class ParserRegistry:
    """Central registry for all available parsers.

    Provides format auto-detection and a unified entry point for parsing
    any supported spritesheet/atlas format.

    Usage:
        result = ParserRegistry.parse_file("/path/to/atlas.json")
        if result.is_valid:
            for sprite in result.sprites:
                process_sprite(sprite)
        else:
            handle_errors(result.errors)
    """

    # Registered parsers by extension
    _parsers_by_ext: Dict[str, List[Type[BaseParser]]] = {}

    # All registered parser classes
    _all_parsers: List[Type[BaseParser]] = []

    @classmethod
    def register(cls, parser_cls: Type[BaseParser]) -> Type[BaseParser]:
        """Register a parser class.

        Can be used as a decorator:
            @ParserRegistry.register
            class MyParser(BaseParser):
                FILE_EXTENSIONS = (".myext",)
                ...

        Args:
            parser_cls: Parser class to register.

        Returns:
            The parser class (for decorator usage).
        """
        if parser_cls not in cls._all_parsers:
            cls._all_parsers.append(parser_cls)

        for ext in getattr(parser_cls, "FILE_EXTENSIONS", ()):
            ext_lower = ext.lower()
            if ext_lower not in cls._parsers_by_ext:
                cls._parsers_by_ext[ext_lower] = []
            if parser_cls not in cls._parsers_by_ext[ext_lower]:
                cls._parsers_by_ext[ext_lower].append(parser_cls)

        return parser_cls

    @classmethod
    def get_parsers_for_extension(cls, ext: str) -> List[Type[BaseParser]]:
        """Get all parsers that support a given file extension.

        Args:
            ext: File extension including dot (e.g., ".json").

        Returns:
            List of parser classes that handle this extension.
        """
        return cls._parsers_by_ext.get(ext.lower(), [])

    @classmethod
    def detect_parser(cls, file_path: str) -> Optional[Type[BaseParser]]:
        """Detect the best parser for a given file.

        First checks extension, then attempts content-based detection
        for ambiguous formats like .json.

        Args:
            file_path: Path to the file to parse.

        Returns:
            The most appropriate parser class, or None if unsupported.
        """
        ext = os.path.splitext(file_path)[1].lower()
        candidates = cls.get_parsers_for_extension(ext)

        if not candidates:
            return None

        if len(candidates) == 1:
            return candidates[0]

        # Multiple candidates - try content-based detection
        if ext == ".json":
            return cls._detect_json_parser(file_path, candidates)
        elif ext == ".xml":
            return cls._detect_xml_parser(file_path, candidates)
        elif ext == ".plist":
            return cls._detect_plist_parser(file_path, candidates)

        # Default to first candidate
        return candidates[0]

    @classmethod
    def _detect_json_parser(
        cls,
        file_path: str,
        candidates: List[Type[BaseParser]],
    ) -> Optional[Type[BaseParser]]:
        """Detect the correct JSON parser based on content structure.

        Args:
            file_path: Path to the JSON file.
            candidates: List of parser classes to check.

        Returns:
            The matching parser class or the first candidate as fallback.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Check for specific JSON structures
            if "textures" in data:
                # Could be Godot Atlas or Phaser3
                textures = data.get("textures", [])
                if textures and "sprites" in textures[0]:
                    # Godot Atlas format
                    for parser in candidates:
                        if parser.__name__ == "GodotAtlasParser":
                            return parser
                elif textures and "frames" in textures[0]:
                    # Phaser3 format
                    for parser in candidates:
                        if parser.__name__ == "Phaser3Parser":
                            return parser

            if "frames" in data:
                frames = data["frames"]
                if isinstance(frames, list):
                    # JSON Array format
                    for parser in candidates:
                        if parser.__name__ == "JsonArrayAtlasParser":
                            return parser
                elif isinstance(frames, dict):
                    # Check for Egret2D (simple x/y/w/h) vs Hash format
                    if frames:
                        first_frame = next(iter(frames.values()))
                        if "frame" in first_frame:
                            # Hash format with nested frame object
                            for parser in candidates:
                                if parser.__name__ == "JsonHashAtlasParser":
                                    return parser
                        else:
                            # Egret2D format with direct x/y/w/h
                            for parser in candidates:
                                if parser.__name__ == "Egret2DParser":
                                    return parser

            # Check for spritemap format (Adobe Animate)
            if "SD" in data or "ATLAS" in data:
                for parser in candidates:
                    if "Spritemap" in parser.__name__:
                        return parser

        except (json.JSONDecodeError, IOError):
            pass

        return candidates[0] if candidates else None

    @classmethod
    def _detect_xml_parser(
        cls,
        file_path: str,
        candidates: List[Type[BaseParser]],
    ) -> Optional[Type[BaseParser]]:
        """Detect the correct XML parser based on content structure.

        Args:
            file_path: Path to the XML file.
            candidates: List of parser classes to check.

        Returns:
            The matching parser class or the first candidate as fallback.
        """
        try:
            import xml.etree.ElementTree as ET

            tree = ET.parse(file_path)
            root = tree.getroot()

            # Check for matches_root method on candidates
            for parser in candidates:
                matcher = getattr(parser, "matches_root", None)
                if matcher and matcher(root):
                    return parser

        except Exception:
            pass

        return candidates[0] if candidates else None

    @classmethod
    def _detect_plist_parser(
        cls,
        file_path: str,
        candidates: List[Type[BaseParser]],
    ) -> Optional[Type[BaseParser]]:
        """Detect the correct plist parser based on content structure.

        Args:
            file_path: Path to the plist file.
            candidates: List of parser classes to check.

        Returns:
            The matching parser class or the first candidate as fallback.
        """
        try:
            import plistlib

            with open(file_path, "rb") as f:
                data = plistlib.load(f)

            frames = data.get("frames", {})
            if frames:
                first_frame = next(iter(frames.values()))
                # UIKit format uses scalar x/y/w/h keys
                if "x" in first_frame and "y" in first_frame:
                    for parser in candidates:
                        if parser.__name__ == "UIKitPlistParser":
                            return parser
                # TexturePacker format uses nested frame/sourceSize
                elif "frame" in first_frame or "textureRect" in first_frame:
                    for parser in candidates:
                        if parser.__name__ == "PlistAtlasParser":
                            return parser

        except Exception:
            pass

        return candidates[0] if candidates else None

    @classmethod
    def parse_file(cls, file_path: str) -> ParseResult:
        """Parse a file using the appropriate parser.

        This is the main entry point for the unified parsing pipeline.

        Args:
            file_path: Path to the file to parse.

        Returns:
            ParseResult with sprites, warnings, and errors.

        Raises:
            FileError: If the file cannot be found or read.
            FormatError: If no parser supports the file format.
        """
        if not os.path.exists(file_path):
            raise FileError(
                ParserErrorCode.FILE_NOT_FOUND,
                f"File not found: {file_path}",
                file_path=file_path,
            )

        parser_cls = cls.detect_parser(file_path)
        if not parser_cls:
            ext = os.path.splitext(file_path)[1]
            raise FormatError(
                ParserErrorCode.UNSUPPORTED_FORMAT,
                f"No parser available for extension: {ext}",
                file_path=file_path,
            )

        return parser_cls.parse_file(file_path)

    @classmethod
    def get_supported_extensions(cls) -> List[str]:
        """Get list of all supported file extensions.

        Returns:
            List of extensions including dots (e.g., [".json", ".xml"]).
        """
        return sorted(cls._parsers_by_ext.keys())

    @classmethod
    def initialize(cls) -> None:
        """Initialize the registry with all available parsers.

        This should be called once at application startup.
        """
        # Import all parser modules to trigger registration
        from parsers import (
            css_legacy_parser,
            css_spritesheet_parser,
            egret2d_parser,
            godot_atlas_parser,
            json_array_parser,
            json_hash_parser,
            paper2d_parser,
            phaser3_parser,
            plist_xml_parser,
            spine_parser,
            starling_xml_parser,
            texture_packer_unity_parser,
            texture_packer_xml_parser,
            txt_parser,
            uikit_plist_parser,
        )

        # Register all parsers
        parsers_to_register = [
            css_legacy_parser.CssLegacyParser,
            css_spritesheet_parser.CssSpriteSheetParser,
            egret2d_parser.Egret2DParser,
            godot_atlas_parser.GodotAtlasParser,
            json_array_parser.JsonArrayAtlasParser,
            json_hash_parser.JsonHashAtlasParser,
            paper2d_parser.Paper2DParser,
            phaser3_parser.Phaser3Parser,
            plist_xml_parser.PlistAtlasParser,
            spine_parser.SpineAtlasParser,
            starling_xml_parser.StarlingXmlParser,
            texture_packer_unity_parser.TexturePackerUnityParser,
            texture_packer_xml_parser.TexturePackerXmlParser,
            txt_parser.TxtParser,
            uikit_plist_parser.UIKitPlistParser,
        ]

        for parser in parsers_to_register:
            cls.register(parser)


# Convenience function for direct use
def parse_file(file_path: str) -> ParseResult:
    """Parse a spritesheet metadata file.

    Convenience wrapper around ParserRegistry.parse_file().

    Args:
        file_path: Path to the file to parse.

    Returns:
        ParseResult with sprites, warnings, and errors.
    """
    return ParserRegistry.parse_file(file_path)


__all__ = ["ParserRegistry", "parse_file"]
