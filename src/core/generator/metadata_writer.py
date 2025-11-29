#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Metadata writer for generating alternative atlas format outputs.

This module bridges the generator's packed frames to the exporter system,
allowing generation of multiple metadata formats from a single atlas.

Usage:
    from core.generator.metadata_writer import MetadataWriter

    # After generator has packed frames
    writer = MetadataWriter(generator.frames, atlas_width, atlas_height)
    writer.write_metadata(output_path, "json-hash", image_name="atlas.png")
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, TYPE_CHECKING
from xml.dom import minidom

if TYPE_CHECKING:
    from core.generator.generator import Frame


class MetadataWriter:
    """Write atlas metadata in various formats from packed frame data.

    This class provides format-specific metadata generation without
    depending on the full exporter infrastructure, keeping the generator
    lean while supporting multiple output formats.

    Attributes:
        frames: List of packed Frame objects from the generator.
        atlas_width: Width of the generated atlas image.
        atlas_height: Height of the generated atlas image.
    """

    # Format key to file extension mapping
    FORMAT_EXTENSIONS = {
        "starling-xml": ".xml",
        "json-hash": ".json",
        "json-array": ".json",
        "texture-packer-xml": ".xml",
        "spine": ".atlas",
        "phaser3": ".json",
        "css": ".css",
        "txt": ".txt",
        "plist": ".plist",
        "uikit-plist": ".plist",
        "godot": ".tpsheet",
        "egret2d": ".json",
        "paper2d": ".paper2dsprites",
        "unity": ".tpsheet",
    }

    # Formats that support sprite rotation metadata.
    # Rotation is always 90° clockwise (standard TexturePacker convention).
    # Formats NOT in this set cannot represent rotated sprites,
    # so the packer should avoid rotating sprites for these formats.
    FORMATS_SUPPORTING_ROTATION = frozenset(
        {
            "starling-xml",  # Has rotated attribute
            "json-hash",  # Has "rotated" field
            "json-array",  # Has "rotated" field
            "texture-packer-xml",  # Has r="y" attribute
            "spine",  # Has rotate: true/false
            "phaser3",  # Has "rotated" field
            "plist",  # Has "rotated" field
            "paper2d",  # Has "rotated" field
        }
    )

    # Formats that support vertical flip metadata.
    # Note: Only starling-xml has flipX/flipY attributes, and even then
    # only specific engines like HaxeFlixel actually support reading them.
    # Most Starling/Sparrow implementations ignore flip attributes.
    FORMATS_SUPPORTING_FLIP = frozenset(
        {
            "starling-xml",  # Has flipX/flipY attributes (HaxeFlixel only)
        }
    )

    @classmethod
    def supports_rotation(cls, format_key: str) -> bool:
        """Check if a format supports sprite rotation metadata.

        Args:
            format_key: The format identifier (e.g., "json-hash", "css").

        Returns:
            True if the format can represent rotated sprites, False otherwise.
        """
        return format_key in cls.FORMATS_SUPPORTING_ROTATION

    @classmethod
    def supports_flip(cls, format_key: str) -> bool:
        """Check if a format supports vertical flip metadata.

        Args:
            format_key: The format identifier (e.g., "starling-xml", "json-hash").

        Returns:
            True if the format can represent flipped sprites, False otherwise.
        """
        return format_key in cls.FORMATS_SUPPORTING_FLIP

    def __init__(
        self,
        frames: List["Frame"],
        atlas_width: int,
        atlas_height: int,
    ) -> None:
        """Initialize the metadata writer.

        Args:
            frames: List of packed Frame objects.
            atlas_width: Atlas image width in pixels.
            atlas_height: Atlas image height in pixels.
        """
        self.frames = frames
        self.atlas_width = atlas_width
        self.atlas_height = atlas_height

    def get_extension(self, format_key: str) -> str:
        """Get the file extension for a format.

        Args:
            format_key: Format identifier (e.g., "json-hash").

        Returns:
            File extension including dot (e.g., ".json").
        """
        return self.FORMAT_EXTENSIONS.get(format_key, ".txt")

    def write_metadata(
        self,
        output_path: str,
        format_key: str,
        image_name: Optional[str] = None,
        version: str = "2.0.0",
        pretty_print: bool = True,
    ) -> str:
        """Write metadata file in the specified format.

        Args:
            output_path: Base output path (without extension).
            format_key: Target format identifier.
            image_name: Atlas image filename. Defaults to basename + .png.
            version: Application version for comments.
            pretty_print: Whether to format output for readability.

        Returns:
            Path to the written metadata file.
        """
        if image_name is None:
            image_name = Path(output_path).name + ".png"

        extension = self.get_extension(format_key)
        metadata_path = f"{output_path}{extension}"

        # Get the appropriate generator method
        generator_map = {
            "starling-xml": self._generate_starling_xml,
            "json-hash": self._generate_json_hash,
            "json-array": self._generate_json_array,
            "texture-packer-xml": self._generate_texture_packer_xml,
            "spine": self._generate_spine_atlas,
            "phaser3": self._generate_phaser3_json,
            "css": self._generate_css,
            "txt": self._generate_txt,
            "plist": self._generate_plist,
            "uikit-plist": self._generate_uikit_plist,
            "godot": self._generate_godot,
            "egret2d": self._generate_egret2d,
            "paper2d": self._generate_paper2d,
            "unity": self._generate_unity,
        }

        generator_func = generator_map.get(format_key, self._generate_starling_xml)
        content = generator_func(image_name, version, pretty_print)

        # Write the file
        if isinstance(content, bytes):
            with open(metadata_path, "wb") as f:
                f.write(content)
        else:
            with open(metadata_path, "w", encoding="utf-8") as f:
                f.write(content)

        return metadata_path

    def _sorted_frames(self) -> List["Frame"]:
        """Return frames sorted by natural alphanumeric order.

        Returns:
            List of frames sorted so that "frame2" comes before "frame10".
        """
        import re

        def natural_key(frame):
            return [
                int(c) if c.isdigit() else c.lower()
                for c in re.split(r"(\d+)", frame.name)
            ]

        return sorted(self.frames, key=natural_key)

    def _generate_starling_xml(
        self, image_name: str, version: str, pretty_print: bool
    ) -> str:
        """Generate Starling/Sparrow XML format content.

        Args:
            image_name: Atlas image filename for the imagePath attribute.
            version: App version string (unused in output but kept for parity).
            pretty_print: Indent XML for readability when True.

        Returns:
            XML string with TextureAtlas root and SubTexture children.
        """
        root = ET.Element("TextureAtlas")
        root.set("imagePath", image_name)

        for frame in self._sorted_frames():
            sub = ET.SubElement(root, "SubTexture")
            sub.set("name", frame.name)
            sub.set("x", str(frame.x))
            sub.set("y", str(frame.y))
            sub.set("width", str(frame.width))
            sub.set("height", str(frame.height))
            sub.set("frameX", str(-frame.frame_x))
            sub.set("frameY", str(-frame.frame_y))
            sub.set("frameWidth", str(frame.original_width))
            sub.set("frameHeight", str(frame.original_height))
            sub.set("flipX", "false")
            sub.set("flipY", str(frame.flip_y).lower())
            sub.set("rotated", str(frame.rotated).lower())

        if pretty_print:
            rough = ET.tostring(root, encoding="unicode")
            parsed = minidom.parseString(rough)
            lines = parsed.toprettyxml(indent="  ").split("\n")[1:]
            return '<?xml version="1.0" encoding="utf-8"?>\n' + "\n".join(lines)
        else:
            return ET.tostring(root, encoding="unicode")

    def _generate_json_hash(
        self, image_name: str, version: str, pretty_print: bool
    ) -> str:
        """Generate TexturePacker JSON Hash format content.

        Args:
            image_name: Atlas image filename for metadata.
            version: App version recorded in meta.app.
            pretty_print: Indent JSON for readability when True.

        Returns:
            JSON string with frames keyed by sprite name.
        """
        frames_dict = {}
        for frame in self._sorted_frames():
            frames_dict[frame.name] = {
                "frame": {
                    "x": frame.x,
                    "y": frame.y,
                    "w": frame.width,
                    "h": frame.height,
                },
                "rotated": frame.rotated,
                "trimmed": frame.frame_x != 0 or frame.frame_y != 0,
                "spriteSourceSize": {
                    "x": frame.frame_x,
                    "y": frame.frame_y,
                    "w": frame.width,
                    "h": frame.height,
                },
                "sourceSize": {
                    "w": frame.original_width,
                    "h": frame.original_height,
                },
            }

        output = {
            "frames": frames_dict,
            "meta": {
                "app": f"TextureAtlas Toolbox v{version}",
                "image": image_name,
                "format": "RGBA8888",
                "size": {"w": self.atlas_width, "h": self.atlas_height},
                "scale": "1",
            },
        }

        indent = 4 if pretty_print else None
        return json.dumps(output, indent=indent, ensure_ascii=False)

    def _generate_json_array(
        self, image_name: str, version: str, pretty_print: bool
    ) -> str:
        """Generate TexturePacker JSON Array format content.

        Args:
            image_name: Atlas image filename for metadata.
            version: App version recorded in meta.app.
            pretty_print: Indent JSON for readability when True.

        Returns:
            JSON string with frames as an ordered array.
        """
        frames_list = []
        for frame in self._sorted_frames():
            frames_list.append(
                {
                    "filename": frame.name,
                    "frame": {
                        "x": frame.x,
                        "y": frame.y,
                        "w": frame.width,
                        "h": frame.height,
                    },
                    "rotated": frame.rotated,
                    "trimmed": frame.frame_x != 0 or frame.frame_y != 0,
                    "spriteSourceSize": {
                        "x": frame.frame_x,
                        "y": frame.frame_y,
                        "w": frame.width,
                        "h": frame.height,
                    },
                    "sourceSize": {
                        "w": frame.original_width,
                        "h": frame.original_height,
                    },
                }
            )

        output = {
            "frames": frames_list,
            "meta": {
                "app": f"TextureAtlas Toolbox v{version}",
                "image": image_name,
                "format": "RGBA8888",
                "size": {"w": self.atlas_width, "h": self.atlas_height},
                "scale": "1",
            },
        }

        indent = 4 if pretty_print else None
        return json.dumps(output, indent=indent, ensure_ascii=False)

    def _generate_texture_packer_xml(
        self, image_name: str, version: str, pretty_print: bool
    ) -> str:
        """Generate TexturePacker generic XML format content.

        Args:
            image_name: Atlas image filename for the imagePath attribute.
            version: App version string (unused in output).
            pretty_print: Indent XML for readability when True.

        Returns:
            XML string using sprite elements with abbreviated attributes.
        """
        root = ET.Element("TextureAtlas")
        root.set("imagePath", image_name)
        root.set("width", str(self.atlas_width))
        root.set("height", str(self.atlas_height))

        for frame in self._sorted_frames():
            sprite = ET.SubElement(root, "sprite")
            sprite.set("n", frame.name)
            sprite.set("x", str(frame.x))
            sprite.set("y", str(frame.y))
            sprite.set("w", str(frame.width))
            sprite.set("h", str(frame.height))
            if frame.frame_x != 0:
                sprite.set("oX", str(frame.frame_x))
            if frame.frame_y != 0:
                sprite.set("oY", str(frame.frame_y))
            if frame.original_width != frame.width:
                sprite.set("oW", str(frame.original_width))
            if frame.original_height != frame.height:
                sprite.set("oH", str(frame.original_height))
            if frame.rotated:
                sprite.set("r", "y")

        if pretty_print:
            rough = ET.tostring(root, encoding="unicode")
            parsed = minidom.parseString(rough)
            return parsed.toprettyxml(indent="  ")
        else:
            return ET.tostring(root, encoding="unicode")

    def _generate_spine_atlas(
        self, image_name: str, version: str, pretty_print: bool
    ) -> str:
        """Generate Spine/libGDX .atlas format content.

        Args:
            image_name: Atlas image filename as the first line.
            version: App version string (unused in output).
            pretty_print: Ignored; Spine format uses fixed indentation.

        Returns:
            Text content with header and per-sprite property blocks.
        """
        lines = [
            image_name,
            f"size: {self.atlas_width},{self.atlas_height}",
            "format: RGBA8888",
            "filter: Linear,Linear",
            "repeat: none",
        ]

        for frame in self._sorted_frames():
            lines.append(frame.name)
            lines.append("  rotate: " + ("true" if frame.rotated else "false"))
            lines.append(f"  xy: {frame.x}, {frame.y}")
            lines.append(f"  size: {frame.width}, {frame.height}")
            lines.append(f"  orig: {frame.original_width}, {frame.original_height}")
            lines.append(f"  offset: {frame.frame_x}, {frame.frame_y}")
            lines.append("  index: -1")

        return "\n".join(lines) + "\n"

    def _generate_phaser3_json(
        self, image_name: str, version: str, pretty_print: bool
    ) -> str:
        """Generate Phaser 3 JSON multi-atlas format content.

        Args:
            image_name: Atlas image filename in texture entry.
            version: App version recorded in meta.app.
            pretty_print: Indent JSON for readability when True.

        Returns:
            JSON string with textures array containing frames.
        """
        frames_list = []
        for frame in self._sorted_frames():
            frames_list.append(
                {
                    "filename": frame.name,
                    "frame": {
                        "x": frame.x,
                        "y": frame.y,
                        "w": frame.width,
                        "h": frame.height,
                    },
                    "rotated": frame.rotated,
                    "trimmed": frame.frame_x != 0 or frame.frame_y != 0,
                    "spriteSourceSize": {
                        "x": frame.frame_x,
                        "y": frame.frame_y,
                        "w": frame.width,
                        "h": frame.height,
                    },
                    "sourceSize": {
                        "w": frame.original_width,
                        "h": frame.original_height,
                    },
                }
            )

        output = {
            "textures": [
                {
                    "image": image_name,
                    "format": "RGBA8888",
                    "size": {"w": self.atlas_width, "h": self.atlas_height},
                    "scale": 1,
                    "frames": frames_list,
                }
            ],
            "meta": {
                "app": f"TextureAtlas Toolbox v{version}",
                "version": "1.0",
            },
        }

        indent = 4 if pretty_print else None
        return json.dumps(output, indent=indent, ensure_ascii=False)

    def _generate_css(self, image_name: str, version: str, pretty_print: bool) -> str:
        """Generate CSS spritesheet format content.

        Args:
            image_name: Atlas image filename for background-image URL.
            version: App version recorded in header comment.
            pretty_print: Add blank lines between rules when True.

        Returns:
            CSS with a base .sprite class and per-sprite selectors.
        """
        lines = [
            f"/* Generated by TextureAtlas Toolbox v{version} */",
            f"/* Atlas: {image_name} ({self.atlas_width}x{self.atlas_height}) */",
            "",
        ]

        # Common sprite class
        lines.append(".sprite {")
        lines.append(f"    background-image: url('{image_name}');")
        lines.append("    background-repeat: no-repeat;")
        lines.append("    display: inline-block;")
        lines.append("}")
        lines.append("")

        # Individual sprite classes
        for frame in self._sorted_frames():
            # Sanitize name for CSS class
            css_name = frame.name.replace(" ", "-").replace("_", "-")
            lines.append(f".sprite-{css_name} {{")
            lines.append(f"    width: {frame.width}px;")
            lines.append(f"    height: {frame.height}px;")
            lines.append(f"    background-position: -{frame.x}px -{frame.y}px;")
            lines.append("}")
            if pretty_print:
                lines.append("")

        return "\n".join(lines)

    def _generate_txt(self, image_name: str, version: str, pretty_print: bool) -> str:
        """Generate plain text format content.

        Args:
            image_name: Atlas image filename in header comment.
            version: App version string (unused in output).
            pretty_print: Ignored; format is always single-line per sprite.

        Returns:
            Text with one "name = x y width height" line per sprite.
        """
        lines = [f"# Atlas: {image_name}", "# name = x y width height", ""]

        for frame in self._sorted_frames():
            lines.append(
                f"{frame.name} = {frame.x} {frame.y} {frame.width} {frame.height}"
            )

        return "\n".join(lines) + "\n"

    def _generate_plist(
        self, image_name: str, version: str, pretty_print: bool
    ) -> bytes:
        """Generate Apple plist format content.

        Args:
            image_name: Atlas image filename in metadata.
            version: App version string (unused in output).
            pretty_print: Ignored; always outputs binary plist.

        Returns:
            Binary plist bytes using Cocos2d-style string rects.
        """
        import plistlib

        frames_dict = {}
        for frame in self._sorted_frames():
            frames_dict[frame.name] = {
                "frame": f"{{{{{frame.x},{frame.y}}},{{{frame.width},{frame.height}}}}}",
                "offset": f"{{{frame.frame_x},{frame.frame_y}}}",
                "rotated": frame.rotated,
                "sourceColorRect": (
                    f"{{{{{-frame.frame_x},{-frame.frame_y}}},"
                    f"{{{frame.width},{frame.height}}}}}"
                ),
                "sourceSize": f"{{{frame.original_width},{frame.original_height}}}",
            }

        plist_data = {
            "frames": frames_dict,
            "metadata": {
                "format": 2,
                "realTextureFileName": image_name,
                "size": f"{{{self.atlas_width},{self.atlas_height}}}",
                "textureFileName": image_name,
            },
        }

        return plistlib.dumps(plist_data, fmt=plistlib.FMT_BINARY)

    def _generate_uikit_plist(
        self, image_name: str, version: str, pretty_print: bool
    ) -> bytes:
        """Generate UIKit plist format content.

        Args:
            image_name: Atlas image filename in metadata.
            version: App version string (unused in output).
            pretty_print: Ignored; always outputs binary plist.

        Returns:
            Binary plist bytes using scalar integer keys.
        """
        import plistlib

        frames_dict = {}
        for frame in self._sorted_frames():
            frames_dict[frame.name] = {
                "x": frame.x,
                "y": frame.y,
                "w": frame.width,
                "h": frame.height,
                "oX": frame.frame_x,
                "oY": frame.frame_y,
                "oW": frame.original_width,
                "oH": frame.original_height,
            }

        plist_data = {
            "frames": frames_dict,
            "meta": {
                "image": image_name,
                "size": {"w": self.atlas_width, "h": self.atlas_height},
            },
        }

        return plistlib.dumps(plist_data, fmt=plistlib.FMT_BINARY)

    def _generate_godot(self, image_name: str, version: str, pretty_print: bool) -> str:
        """Generate Godot atlas JSON format content.

        Args:
            image_name: Atlas image filename in texture entry.
            version: App version string (unused in output).
            pretty_print: Indent JSON for readability when True.

        Returns:
            JSON string with textures array and sprite regions.
        """
        sprites = []
        for frame in self._sorted_frames():
            sprites.append(
                {
                    "filename": frame.name,
                    "region": {
                        "x": frame.x,
                        "y": frame.y,
                        "w": frame.width,
                        "h": frame.height,
                    },
                }
            )

        output = {
            "textures": [
                {
                    "image": image_name,
                    "size": {"w": self.atlas_width, "h": self.atlas_height},
                    "sprites": sprites,
                }
            ]
        }

        indent = 4 if pretty_print else None
        return json.dumps(output, indent=indent, ensure_ascii=False)

    def _generate_egret2d(
        self, image_name: str, version: str, pretty_print: bool
    ) -> str:
        """Generate Egret2D JSON format content.

        Args:
            image_name: Atlas image filename in file key.
            version: App version string (unused in output).
            pretty_print: Indent JSON for readability when True.

        Returns:
            JSON string with frames keyed by sprite name.
        """
        frames_dict = {}
        for frame in self._sorted_frames():
            entry: Dict[str, int] = {
                "x": frame.x,
                "y": frame.y,
                "w": frame.width,
                "h": frame.height,
            }
            if frame.frame_x != 0:
                entry["offX"] = -frame.frame_x
            if frame.frame_y != 0:
                entry["offY"] = -frame.frame_y
            if frame.original_width != frame.width:
                entry["sourceW"] = frame.original_width
            if frame.original_height != frame.height:
                entry["sourceH"] = frame.original_height
            frames_dict[frame.name] = entry

        output = {
            "file": image_name,
            "frames": frames_dict,
        }

        indent = 4 if pretty_print else None
        return json.dumps(output, indent=indent, ensure_ascii=False)

    def _generate_paper2d(
        self, image_name: str, version: str, pretty_print: bool
    ) -> str:
        """Generate Unreal Engine Paper2D format content.

        Args:
            image_name: Atlas image filename in meta.
            version: App version string (unused in output).
            pretty_print: Indent JSON for readability when True.

        Returns:
            JSON string compatible with Paper2D sprite import.
        """
        frames_dict = {}
        for frame in self._sorted_frames():
            trimmed = frame.frame_x != 0 or frame.frame_y != 0
            frames_dict[frame.name] = {
                "frame": {
                    "x": frame.x,
                    "y": frame.y,
                    "w": frame.width,
                    "h": frame.height,
                },
                "rotated": frame.rotated,
                "trimmed": trimmed,
                "spriteSourceSize": {
                    "x": -frame.frame_x,
                    "y": -frame.frame_y,
                    "w": frame.width,
                    "h": frame.height,
                },
                "sourceSize": {
                    "w": frame.original_width,
                    "h": frame.original_height,
                },
                "pivot": {"x": 0.5, "y": 0.5},
            }

        output = {
            "frames": frames_dict,
            "meta": {
                "image": image_name,
                "format": "RGBA8888",
                "size": {"w": self.atlas_width, "h": self.atlas_height},
                "scale": "1",
            },
        }

        indent = 4 if pretty_print else None
        return json.dumps(output, indent=indent, ensure_ascii=False)

    def _generate_unity(self, image_name: str, version: str, pretty_print: bool) -> str:
        """Generate TexturePacker Unity format content.

        Args:
            image_name: Atlas image filename in :texture header.
            version: App version string (unused in output).
            pretty_print: Ignored; format uses fixed semicolon delimiters.

        Returns:
            Text with header lines and semicolon-delimited sprite rows.
        """
        lines = [
            ":format=40300",
            f":texture={image_name}",
            f":size={self.atlas_width}x{self.atlas_height}",
        ]

        for frame in self._sorted_frames():
            parts = [
                frame.name,
                str(frame.x),
                str(frame.y),
                str(frame.width),
                str(frame.height),
                "0.5",  # pivot X
                "0.5",  # pivot Y
            ]
            lines.append(";".join(parts))

        return "\n".join(lines) + "\n"


__all__ = ["MetadataWriter"]
