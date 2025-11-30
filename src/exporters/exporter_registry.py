#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Exporter registry for format selection and unified export entry point.

This module provides:
    - ExporterRegistry: Central registry of all available exporters.
    - Format selection based on extension or format name.
    - Unified export_file() entry point for the generation pipeline.

Usage:
    from exporters import ExporterRegistry, ExportOptions

    # Export with auto-detected format
    result = ExporterRegistry.export_file(
        sprites=sprite_list,
        sprite_images=image_dict,
        output_path="/path/to/output",
        format_name="json-hash",
    )

    # Or use a specific exporter
    exporter_cls = ExporterRegistry.get_exporter("starling-xml")
    exporter = exporter_cls(options=ExportOptions(padding=4))
    result = exporter.export_file(sprites, images, "/path/to/output")
"""

from __future__ import annotations

from typing import Dict, List, Optional, Type

from PIL import Image

from exporters.base_exporter import BaseExporter
from exporters.exporter_types import (
    ExporterErrorCode,
    ExportOptions,
    ExportResult,
    SpriteData,
)


class ExporterRegistry:
    """Central registry for all available exporters.

    Provides format lookup and a unified entry point for exporting
    to any supported spritesheet/atlas format.

    Class Attributes:
        _exporters_by_name: Mapping of format names to exporter classes.
        _exporters_by_ext: Mapping of extensions to exporter classes.
        _all_exporters: List of all registered exporter classes.
    """

    _exporters_by_name: Dict[str, Type[BaseExporter]] = {}
    _exporters_by_ext: Dict[str, Type[BaseExporter]] = {}
    _all_exporters: List[Type[BaseExporter]] = []

    @classmethod
    def register(cls, exporter_cls: Type[BaseExporter]) -> Type[BaseExporter]:
        """Register an exporter class.

        Can be used as a decorator:
            @ExporterRegistry.register
            class MyExporter(BaseExporter):
                FILE_EXTENSION = ".myext"
                FORMAT_NAME = "my-format"
                ...

        Args:
            exporter_cls: Exporter class to register.

        Returns:
            The exporter class (for decorator usage).
        """
        if exporter_cls not in cls._all_exporters:
            cls._all_exporters.append(exporter_cls)

        # Register by format name
        format_name = getattr(exporter_cls, "FORMAT_NAME", "").lower()
        if format_name:
            cls._exporters_by_name[format_name] = exporter_cls

        # Register by extension
        ext = getattr(exporter_cls, "FILE_EXTENSION", "").lower()
        if ext:
            cls._exporters_by_ext[ext] = exporter_cls

        return exporter_cls

    @classmethod
    def get_exporter(cls, format_name: str) -> Optional[Type[BaseExporter]]:
        """Get an exporter class by format name or extension.

        Args:
            format_name: Format name (e.g., "json-hash") or extension (".json").

        Returns:
            The matching exporter class, or None if not found.
        """
        format_lower = format_name.lower().lstrip(".")

        # Try by format name first
        if format_lower in cls._exporters_by_name:
            return cls._exporters_by_name[format_lower]

        # Try by extension
        ext_key = (
            f".{format_lower}" if not format_lower.startswith(".") else format_lower
        )
        if ext_key in cls._exporters_by_ext:
            return cls._exporters_by_ext[ext_key]

        # Try partial match on format name
        for name, exporter in cls._exporters_by_name.items():
            if format_lower in name or name in format_lower:
                return exporter

        return None

    @classmethod
    def get_all_formats(cls) -> List[str]:
        """Get list of all registered format names.

        Returns:
            Sorted list of format names.
        """
        return sorted(cls._exporters_by_name.keys())

    @classmethod
    def get_supported_extensions(cls) -> List[str]:
        """Get list of all supported output extensions.

        Returns:
            Sorted list of extensions including dots.
        """
        return sorted(cls._exporters_by_ext.keys())

    @classmethod
    def export_file(
        cls,
        sprites: List[SpriteData],
        sprite_images: Dict[str, Image.Image],
        output_path: str,
        format_name: str,
        options: Optional[ExportOptions] = None,
    ) -> ExportResult:
        """Export sprites using the specified format.

        This is the main entry point for the unified export pipeline.

        Args:
            sprites: List of sprite definitions to export.
            sprite_images: Mapping of sprite names to PIL Images.
            output_path: Base path for output files (without extension).
            format_name: Target format name or extension.
            options: Optional export configuration.

        Returns:
            ExportResult with paths, dimensions, and any errors.
        """
        exporter_cls = cls.get_exporter(format_name)

        if not exporter_cls:
            result = ExportResult()
            result.add_error(
                ExporterErrorCode.UNSUPPORTED_FORMAT,
                f"No exporter available for format: {format_name}",
                details={"available_formats": cls.get_all_formats()[:10]},
            )
            return result

        exporter = exporter_cls(options)
        return exporter.export_file(sprites, sprite_images, output_path)

    @classmethod
    def initialize(cls) -> None:
        """Initialize the registry with all available exporters.

        This should be called once at application startup.
        Imports all exporter modules to trigger registration.
        """
        # Import exporters here to trigger registration
        # Each import decorates the exporter with @ExporterRegistry.register
        # fmt: off
        from exporters import starling_xml_exporter  # noqa: F401
        from exporters import json_hash_exporter  # noqa: F401
        from exporters import json_array_exporter  # noqa: F401
        from exporters import spine_exporter  # noqa: F401
        from exporters import texture_packer_xml_exporter  # noqa: F401
        from exporters import phaser3_exporter  # noqa: F401
        from exporters import css_exporter  # noqa: F401
        from exporters import txt_exporter  # noqa: F401
        from exporters import plist_exporter  # noqa: F401
        from exporters import uikit_plist_exporter  # noqa: F401
        from exporters import godot_exporter  # noqa: F401
        from exporters import egret2d_exporter  # noqa: F401
        from exporters import paper2d_exporter  # noqa: F401
        from exporters import unity_exporter  # noqa: F401
        # fmt: on


# Convenience function for direct use
def export_file(
    sprites: List[SpriteData],
    sprite_images: Dict[str, Image.Image],
    output_path: str,
    format_name: str,
    options: Optional[ExportOptions] = None,
) -> ExportResult:
    """Export sprites to an atlas and metadata file.

    Convenience wrapper around ExporterRegistry.export_file().

    Args:
        sprites: List of sprite definitions.
        sprite_images: Mapping of sprite names to PIL Images.
        output_path: Base output path (without extension).
        format_name: Target format name or extension.
        options: Optional export configuration.

    Returns:
        ExportResult with export outcomes.
    """
    return ExporterRegistry.export_file(
        sprites, sprite_images, output_path, format_name, options
    )


__all__ = ["ExporterRegistry", "export_file"]
