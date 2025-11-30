#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Spritesheet/atlas exporters for generating texture atlases.

This package provides exporters that create atlas images and metadata files
from collections of sprite images. It mirrors the parser architecture:

    Parsers:   metadata file → List[SpriteData]
    Exporters: List[SpriteData] + images → atlas image + metadata file

Quick Start:
    from exporters import ExporterRegistry, ExportOptions, SpriteData
    from PIL import Image

    # Prepare sprite data and images
    sprites = [
        {"name": "frame_01", "x": 0, "y": 0, "width": 64, "height": 64, ...},
        {"name": "frame_02", "x": 0, "y": 0, "width": 64, "height": 64, ...},
    ]
    images = {
        "frame_01": Image.open("frame_01.png"),
        "frame_02": Image.open("frame_02.png"),
    }

    # Export to JSON Hash format
    result = ExporterRegistry.export_file(
        sprites=sprites,
        sprite_images=images,
        output_path="/path/to/atlas",
        format_name="json-hash",
    )

    if result.success:
        print(f"Created {result.atlas_path} and {result.metadata_path}")

Supported Formats:
    - json-hash: TexturePacker JSON Hash format
    - json-array: TexturePacker JSON Array format
    - starling-xml: Starling/Sparrow XML format
    - texture-packer-xml: TexturePacker generic XML
    - spine: Spine .atlas text format
    - plist: Apple property list format
    - uikit-plist: UIKit-style plist with scalar keys
    - css: CSS sprite definitions
    - txt: Simple text format
    - phaser3: Phaser 3 JSON format
    - godot: Godot atlas format
    - egret2d: Egret 2D JSON format
    - paper2d: Unreal Paper2D JSON format
    - unity: TexturePacker Unity text format

Classes:
    BaseExporter: Abstract base class for all exporters.
    ExporterRegistry: Central registry and format detection.
    ExportOptions: Configuration for export behavior.
    ExportResult: Container for export outcomes.

Type Aliases:
    SpriteData: Canonical sprite structure (re-exported from parsers).
    PackedSprite: Sprite with assigned atlas position.
"""

from exporters.exporter_types import (
    ExporterError,
    ExporterErrorCode,
    ExporterWarning,
    ExportOptions,
    ExportResult,
    FileWriteError,
    FormatError,
    ImageError,
    PackedSprite,
    PackingError,
    SpriteData,
)

from exporters.base_exporter import BaseExporter

from exporters.exporter_registry import (
    ExporterRegistry,
    export_file,
)

# Import format-specific exporters to trigger registration
from exporters.starling_xml_exporter import (
    StarlingXmlExporter,
    StarlingExportOptions,
)
from exporters.json_hash_exporter import (
    JsonHashExporter,
    JsonHashExportOptions,
)
from exporters.json_array_exporter import (
    JsonArrayExporter,
    JsonArrayExportOptions,
)
from exporters.spine_exporter import (
    SpineExporter,
    SpineExportOptions,
)
from exporters.texture_packer_xml_exporter import (
    TexturePackerXmlExporter,
    TexturePackerXmlExportOptions,
)
from exporters.phaser3_exporter import (
    Phaser3Exporter,
    Phaser3ExportOptions,
)
from exporters.css_exporter import (
    CssExporter,
    CssExportOptions,
)
from exporters.txt_exporter import (
    TxtExporter,
    TxtExportOptions,
)
from exporters.plist_exporter import (
    PlistExporter,
    PlistExportOptions,
)
from exporters.uikit_plist_exporter import (
    UIKitPlistExporter,
    UIKitPlistExportOptions,
)
from exporters.godot_exporter import (
    GodotExporter,
    GodotExportOptions,
)
from exporters.egret2d_exporter import (
    Egret2DExporter,
    Egret2DExportOptions,
)
from exporters.paper2d_exporter import (
    Paper2DExporter,
    Paper2DExportOptions,
)
from exporters.unity_exporter import (
    UnityExporter,
    UnityExportOptions,
)

__all__ = [
    # Base class
    "BaseExporter",
    # Registry
    "ExporterRegistry",
    "export_file",
    # Types and options
    "ExportOptions",
    "ExportResult",
    "PackedSprite",
    "SpriteData",
    # Errors and warnings
    "ExporterError",
    "ExporterErrorCode",
    "ExporterWarning",
    "FileWriteError",
    "FormatError",
    "ImageError",
    "PackingError",
    # Format-specific exporters and options
    "StarlingXmlExporter",
    "StarlingExportOptions",
    "JsonHashExporter",
    "JsonHashExportOptions",
    "JsonArrayExporter",
    "JsonArrayExportOptions",
    "SpineExporter",
    "SpineExportOptions",
    "TexturePackerXmlExporter",
    "TexturePackerXmlExportOptions",
    "Phaser3Exporter",
    "Phaser3ExportOptions",
    "CssExporter",
    "CssExportOptions",
    "TxtExporter",
    "TxtExportOptions",
    "PlistExporter",
    "PlistExportOptions",
    "UIKitPlistExporter",
    "UIKitPlistExportOptions",
    "GodotExporter",
    "GodotExportOptions",
    "Egret2DExporter",
    "Egret2DExportOptions",
    "Paper2DExporter",
    "Paper2DExportOptions",
    "UnityExporter",
    "UnityExportOptions",
]
