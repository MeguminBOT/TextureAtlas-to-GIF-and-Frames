#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Exporter for Godot atlas JSON format.

Generates JSON metadata compatible with Godot's TexturePacker importer,
using the textures/sprites structure.

Output Format:
    ```json
    {
        "textures": [
            {
                "image": "atlas.png",
                "size": {"w": 512, "h": 512},
                "sprites": [
                    {
                        "filename": "sprite_01",
                        "region": {"x": 0, "y": 0, "w": 64, "h": 64}
                    }
                ]
            }
        ]
    }
    ```
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from exporters.base_exporter import BaseExporter
from exporters.exporter_registry import ExporterRegistry
from exporters.exporter_types import (
    ExportOptions,
    PackedSprite,
)


@dataclass
class GodotExportOptions:
    """Godot atlas-specific export options.

    Attributes:
        include_size: Include size in texture entry.
    """

    include_size: bool = True


@ExporterRegistry.register
class GodotExporter(BaseExporter):
    """Export sprites to Godot atlas JSON format.

    Creates JSON files compatible with Godot's TexturePacker import
    plugin using the textures[].sprites[] structure.

    Usage:
        from exporters import GodotExporter, ExportOptions

        exporter = GodotExporter()
        result = exporter.export_file(sprites, images, "/path/to/atlas")
    """

    FILE_EXTENSION = ".tpsheet"
    FORMAT_NAME = "godot"

    def __init__(self, options: Optional[ExportOptions] = None) -> None:
        """Initialize the Godot exporter.

        Args:
            options: Export options. Format-specific options should be
                     provided in options.custom_properties["godot"].
        """
        super().__init__(options)
        self._format_options = self._get_format_options()

    def _get_format_options(self) -> GodotExportOptions:
        """Extract format-specific options from custom_properties.

        Returns:
            GodotExportOptions instance.
        """
        custom = self.options.custom_properties
        opts = custom.get("godot")

        if isinstance(opts, GodotExportOptions):
            return opts
        elif isinstance(opts, dict):
            return GodotExportOptions(**opts)
        else:
            return GodotExportOptions()

    def build_metadata(
        self,
        packed_sprites: List[PackedSprite],
        atlas_width: int,
        atlas_height: int,
        image_name: str,
    ) -> str:
        """Generate Godot atlas JSON metadata.

        Args:
            packed_sprites: Sprites with their atlas positions assigned.
            atlas_width: Final atlas width in pixels.
            atlas_height: Final atlas height in pixels.
            image_name: Filename of the atlas image.

        Returns:
            JSON string with textures array containing sprites.
        """
        opts = self._format_options

        # Build sprites list
        sprites: List[Dict[str, Any]] = []
        for packed in packed_sprites:
            sprites.append(self._build_sprite_entry(packed))

        # Build texture entry
        texture: Dict[str, Any] = {
            "image": image_name,
            "sprites": sprites,
        }

        if opts.include_size:
            texture["size"] = {"w": atlas_width, "h": atlas_height}

        # Build output
        output = {"textures": [texture]}

        # Serialize
        indent = 4 if self.options.pretty_print else None
        return json.dumps(output, indent=indent, ensure_ascii=False)

    def _build_sprite_entry(self, packed: PackedSprite) -> Dict[str, Any]:
        """Build a sprite entry for the sprites array.

        Args:
            packed: Packed sprite with atlas position.

        Returns:
            Sprite data dict with filename and region.
        """
        sprite = packed.sprite
        return {
            "filename": packed.name,
            "region": {
                "x": packed.atlas_x,
                "y": packed.atlas_y,
                "w": sprite["width"],
                "h": sprite["height"],
            },
        }


__all__ = ["GodotExporter", "GodotExportOptions"]
