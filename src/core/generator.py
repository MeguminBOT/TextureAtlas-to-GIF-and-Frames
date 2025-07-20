#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image
import numpy as np
import re
from typing import List, Dict, Tuple, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import time

# Import our own modules
from packers import GrowingPacker, OrderedPacker


class PackingAlgorithm(Enum):
    """Available packing algorithms."""

    NONE = 0  # No optimization - simple grid
    GROWING_PACKER = 1  # Growing packer (dynamically expands)
    ORDERED_PACKER = 2  # Ordered packer (preserves order)


@dataclass
class Frame:
    """Represents a single frame in the atlas."""

    name: str
    image_path: str
    width: int
    height: int
    x: int = 0
    y: int = 0
    rotated: bool = False
    # Original frame dimensions before trimming
    original_width: int = 0
    original_height: int = 0
    # Offset from original frame origin
    frame_x: int = 0
    frame_y: int = 0
    # Trimmed dimensions (actual sprite content)
    trimmed_width: int = 0
    trimmed_height: int = 0

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def perimeter(self) -> int:
        return 2 * (self.width + self.height)


@dataclass
class AtlasSettings:
    """Configuration for atlas generation."""

    max_size: int = 2048
    min_size: int = 128
    padding: int = 2
    power_of_2: bool = True
    optimization_level: int = 5
    allow_rotation: bool = True

    @property
    def algorithm(self) -> PackingAlgorithm:
        """Get packing algorithm based on optimization level."""
        if self.optimization_level == 0:
            return PackingAlgorithm.NONE
        elif self.optimization_level <= 5:
            return PackingAlgorithm.GROWING_PACKER
        else:  # Level 6-10 - Use ordered packer for preserving frame order when needed
            return PackingAlgorithm.ORDERED_PACKER


class Rectangle:
    """Simple rectangle class for packing."""

    def __init__(self, x: int, y: int, width: int, height: int):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    @property
    def area(self) -> int:
        return self.width * self.height

    def intersects(self, other: "Rectangle") -> bool:
        return not (
            self.right <= other.x
            or other.right <= self.x
            or self.bottom <= other.y
            or other.bottom <= self.y
        )


class SparrowAtlasGenerator:
    """
    Fast and efficient texture atlas generator specifically for Sparrow format.
    Optimized for speed and tight packing with configurable optimization levels.
    """

    def __init__(self, progress_callback: Optional[Callable] = None):
        self.progress_callback = progress_callback
        self.frames: List[Frame] = []

    def generate_atlas(
        self,
        animation_groups: Dict[str, List[str]],
        output_path: str,
        settings: AtlasSettings,
        current_version: str,
    ) -> Dict:
        """
        Generate a Sparrow format texture atlas.

        Args:
            animation_groups: Dictionary mapping animation names to frame file paths
            output_path: Path for output files (without extension)
            settings: Atlas generation settings
            current_version: Application version for XML comments

        Returns:
            Dictionary containing generation results
        """
        start_time = time.time()

        try:
            # Step 1: Load and prepare frames
            self._update_progress(0, 5, "Loading frames...")
            self._load_frames(animation_groups)

            if not self.frames:
                return {"success": False, "error": "No frames to pack"}

            # Step 2: Sort frames for optimal packing
            self._update_progress(1, 5, "Sorting frames...")
            self._sort_frames(settings)

            # Step 3: Calculate optimal atlas size
            self._update_progress(2, 5, "Calculating atlas size...")
            atlas_width, atlas_height = self._calculate_atlas_size(settings)

            # Step 4: Pack frames into atlas
            self._update_progress(3, 5, "Packing frames...")
            if not self._pack_frames(atlas_width, atlas_height, settings):
                return {"success": False, "error": "Could not fit all frames in atlas"}

            # Step 5: Generate output files
            self._update_progress(4, 5, "Generating output...")
            atlas_image = self._create_atlas_image(atlas_width, atlas_height)
            xml_content = self._generate_sparrow_xml(
                output_path, atlas_width, atlas_height, current_version, settings
            )

            # Save files
            image_path = f"{output_path}.png"
            xml_path = f"{output_path}.xml"

            atlas_image.save(image_path, "PNG")
            with open(xml_path, "w", encoding="utf-8") as f:
                f.write(xml_content)

            self._update_progress(5, 5, "Complete!")

            generation_time = time.time() - start_time

            return {
                "success": True,
                "atlas_path": image_path,
                "xml_path": xml_path,
                "atlas_size": (atlas_width, atlas_height),
                "frame_count": len(self.frames),
                "frames_count": len(self.frames),  # Alternative key for compatibility
                "generation_time": generation_time,
                "efficiency": self._calculate_efficiency(atlas_width, atlas_height),
                "metadata_files": [xml_path],  # For compatibility with UI
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _load_frames(self, animation_groups: Dict[str, List[str]]):
        """Load frame images and extract metadata with whitespace trimming."""
        self.frames = []

        for animation_name, frame_paths in animation_groups.items():
            for i, frame_path in enumerate(frame_paths):
                try:
                    with Image.open(frame_path) as img:
                        # Store original dimensions
                        original_width, original_height = img.width, img.height

                        # Trim whitespace to get actual content bounds
                        trimmed_bounds = self._get_trim_bounds(img)
                        if trimmed_bounds:
                            left, top, right, bottom = trimmed_bounds
                            trimmed_width = right - left
                            trimmed_height = bottom - top
                            frame_x = left
                            frame_y = top
                        else:
                            # No trimming needed - image is fully opaque
                            trimmed_width = original_width
                            trimmed_height = original_height
                            frame_x = 0
                            frame_y = 0
                            left, top = 0, 0

                        frame_name = f"{animation_name}_{i:04d}"
                        frame = Frame(
                            name=frame_name,
                            image_path=frame_path,
                            width=trimmed_width,  # Use trimmed dimensions for packing
                            height=trimmed_height,
                            original_width=original_width,
                            original_height=original_height,
                            frame_x=frame_x,
                            frame_y=frame_y,
                            trimmed_width=trimmed_width,
                            trimmed_height=trimmed_height,
                        )
                        # Store trim bounds for later use in atlas creation
                        frame._trim_bounds = (left, top, left + trimmed_width, top + trimmed_height)
                        self.frames.append(frame)
                except Exception as e:
                    print(f"Error loading frame {frame_path}: {e}")
                    continue

    def _sort_frames(self, settings: AtlasSettings):
        """Sort frames for optimal packing based on optimization level."""
        if settings.optimization_level == 0:
            # No sorting - keep original order
            return
        elif settings.optimization_level <= 3:
            # Simple area-based sorting
            self.frames.sort(key=lambda f: f.area, reverse=True)
        elif settings.optimization_level <= 6:
            # Height-based sorting for better packing
            self.frames.sort(key=lambda f: f.height, reverse=True)
        elif settings.optimization_level <= 9:
            # Advanced sorting: area, then height, then width
            self.frames.sort(key=lambda f: (f.area, f.height, f.width), reverse=True)
        else:
            # Level 10: Best multi-criteria sorting for optimal packing
            # Sort by area first, then by the longer dimension, then by shorter dimension
            # This generally produces better results than simple area sorting
            self.frames.sort(
                key=lambda f: (f.area, max(f.width, f.height), min(f.width, f.height)), reverse=True
            )

    def _calculate_atlas_size(self, settings: AtlasSettings) -> Tuple[int, int]:
        """Calculate optimal atlas dimensions."""
        if settings.algorithm == PackingAlgorithm.NONE:
            # Grid packing needs pre-calculated dimensions
            return self._calculate_grid_size(settings)
        elif settings.algorithm == PackingAlgorithm.GROWING_PACKER:
            # Growing packer determines its own optimal size
            return self._get_growing_packer_size(settings)
        elif settings.algorithm == PackingAlgorithm.ORDERED_PACKER:
            # Ordered packer determines its own optimal size
            return self._get_ordered_packer_size(settings)
        else:
            # Default to growing packer
            return self._get_growing_packer_size(settings)

    def _calculate_grid_size(self, settings: AtlasSettings) -> Tuple[int, int]:
        """Calculate size for simple grid packing (level 0) - allows rectangular grids."""
        if not self.frames:
            return settings.min_size, settings.min_size

        # Calculate frame dimensions
        max_width = max(f.width for f in self.frames)
        max_height = max(f.height for f in self.frames)
        frame_count = len(self.frames)

        # Calculate cell dimensions with padding
        cell_width = max_width + settings.padding * 2
        cell_height = max_height + settings.padding * 2

        # Try different grid arrangements to find the most compact
        best_area = float("inf")
        best_width, best_height = 0, 0

        # Try various grid configurations
        for cols in range(1, min(frame_count + 1, 20)):  # Limit to reasonable number of columns
            rows = int(np.ceil(frame_count / cols))

            grid_width = cols * cell_width
            grid_height = rows * cell_height

            # Apply power of 2 constraint if needed
            if settings.power_of_2:
                grid_width = self._next_power_of_2(grid_width)
                grid_height = self._next_power_of_2(grid_height)

            # Clamp to size limits
            grid_width = min(max(grid_width, settings.min_size), settings.max_size)
            grid_height = min(max(grid_height, settings.min_size), settings.max_size)

            # Check if this arrangement is better (smaller total area)
            total_area = grid_width * grid_height
            if total_area < best_area:
                best_area = total_area
                best_width, best_height = grid_width, grid_height

        return best_width, best_height

    def _get_growing_packer_size(self, settings: AtlasSettings) -> Tuple[int, int]:
        """Get size from growing packer by doing a test pack."""
        if not self.frames:
            return settings.min_size, settings.min_size

        # Convert frames to blocks format
        blocks = []
        for frame in self.frames:
            blocks.append(
                {
                    "w": frame.width + settings.padding * 2,
                    "h": frame.height + settings.padding * 2,
                }
            )

        # Sort blocks by height (largest first) for better packing
        blocks.sort(key=lambda b: b["h"], reverse=True)

        # Use growing packer to determine optimal size
        packer = GrowingPacker()
        packer.fit(blocks)

        # Get the final dimensions from the packer
        width = packer.root["w"] if packer.root else settings.min_size
        height = packer.root["h"] if packer.root else settings.min_size

        # Apply power of 2 constraint if needed
        if settings.power_of_2:
            width = self._next_power_of_2(width)
            height = self._next_power_of_2(height)

        # Clamp to size limits
        width = min(max(width, settings.min_size), settings.max_size)
        height = min(max(height, settings.min_size), settings.max_size)

        return width, height

    def _get_ordered_packer_size(self, settings: AtlasSettings) -> Tuple[int, int]:
        """Get size from ordered packer by doing a test pack."""
        if not self.frames:
            return settings.min_size, settings.min_size

        # Convert frames to blocks format
        blocks = []
        for frame in self.frames:
            blocks.append(
                {
                    "w": frame.width + settings.padding * 2,
                    "h": frame.height + settings.padding * 2,
                }
            )

        # Use ordered packer to determine optimal size
        packer = OrderedPacker()
        packer.fit(blocks)

        # Get the final dimensions from the packer
        width = packer.root["w"] if packer.root else settings.min_size
        height = packer.root["h"] if packer.root else settings.min_size

        # Apply power of 2 constraint if needed
        if settings.power_of_2:
            width = self._next_power_of_2(width)
            height = self._next_power_of_2(height)

        # Clamp to size limits
        width = min(max(width, settings.min_size), settings.max_size)
        height = min(max(height, settings.min_size), settings.max_size)

        return width, height

    def _pack_growing(self, atlas_width: int, atlas_height: int, settings: AtlasSettings) -> bool:
        """Pack frames using the growing packer algorithm."""
        if not self.frames:
            return True

        # Convert frames to blocks format expected by GrowingPacker
        blocks = []
        for frame in self.frames:
            blocks.append(
                {
                    "w": frame.width + settings.padding * 2,
                    "h": frame.height + settings.padding * 2,
                    "frame": frame,
                }
            )

        # Sort blocks by height (largest first) for better packing
        blocks.sort(key=lambda b: b["h"], reverse=True)

        # Use growing packer
        packer = GrowingPacker()
        packer.fit(blocks)

        # Set frame positions (accounting for padding)
        for block in blocks:
            fit = block.get("fit")
            if not fit:
                return False

            frame = block["frame"]
            frame.x = fit["x"] + settings.padding
            frame.y = fit["y"] + settings.padding

        return True

    def _pack_ordered(self, atlas_width: int, atlas_height: int, settings: AtlasSettings) -> bool:
        """Pack frames using the ordered packer algorithm."""
        if not self.frames:
            return True

        # Convert frames to blocks format expected by OrderedPacker
        blocks = []
        for frame in self.frames:
            blocks.append(
                {
                    "w": frame.width + settings.padding * 2,
                    "h": frame.height + settings.padding * 2,
                    "frame": frame,
                }
            )

        # Use ordered packer
        packer = OrderedPacker()
        packer.fit(blocks)

        # Set frame positions (accounting for padding)
        for block in blocks:
            fit = block.get("fit")
            if not fit:
                return False

            frame = block["frame"]
            frame.x = fit["x"] + settings.padding
            frame.y = fit["y"] + settings.padding

        return True

        return True

    def _pack_frames(self, atlas_width: int, atlas_height: int, settings: AtlasSettings) -> bool:
        """Pack frames into the atlas using the selected algorithm."""
        if settings.algorithm == PackingAlgorithm.NONE:
            return self._pack_grid(atlas_width, atlas_height, settings)
        elif settings.algorithm == PackingAlgorithm.GROWING_PACKER:
            return self._pack_growing(atlas_width, atlas_height, settings)
        elif settings.algorithm == PackingAlgorithm.ORDERED_PACKER:
            return self._pack_ordered(atlas_width, atlas_height, settings)
        else:
            # Default to growing packer for other algorithms
            return self._pack_growing(atlas_width, atlas_height, settings)

    def _pack_grid(self, atlas_width: int, atlas_height: int, settings: AtlasSettings) -> bool:
        """Simple grid packing - uses calculated rectangular dimensions."""
        if not self.frames:
            return True

        max_width = max(f.width for f in self.frames) if self.frames else 0
        max_height = max(f.height for f in self.frames) if self.frames else 0

        cell_width = max_width + settings.padding * 2
        cell_height = max_height + settings.padding * 2

        # Calculate how many columns and rows we can fit
        cols = max(1, atlas_width // cell_width)
        rows = max(1, atlas_height // cell_height)

        # Check if we can fit all frames
        if cols * rows < len(self.frames):
            return False

        # Position frames in the grid
        for i, frame in enumerate(self.frames):
            col = i % cols
            row = i // cols

            x = col * cell_width + settings.padding
            y = row * cell_height + settings.padding

            # Double-check bounds
            if x + frame.width > atlas_width or y + frame.height > atlas_height:
                return False

            frame.x = x
            frame.y = y

        return True

    def _create_atlas_image(self, atlas_width: int, atlas_height: int) -> Image.Image:
        """Create the final atlas image using trimmed sprites."""
        atlas = Image.new("RGBA", (atlas_width, atlas_height), (0, 0, 0, 0))

        for frame in self.frames:
            try:
                with Image.open(frame.image_path) as img:
                    # Extract the trimmed portion of the image
                    if hasattr(frame, "_trim_bounds"):
                        left, top, right, bottom = frame._trim_bounds
                        trimmed_img = img.crop((left, top, right, bottom))
                    else:
                        trimmed_img = img

                    if frame.rotated:
                        trimmed_img = trimmed_img.rotate(90, expand=True)

                    atlas.paste(trimmed_img, (frame.x, frame.y))
            except Exception as e:
                print(f"Error pasting frame {frame.name}: {e}")
                continue

        return atlas

    def _generate_sparrow_xml(
        self,
        output_path: str,
        atlas_width: int,
        atlas_height: int,
        current_version: str,
        settings: AtlasSettings = None,
    ) -> str:
        """Generate Sparrow XML format metadata."""
        root = ET.Element("TextureAtlas")
        root.set("imagePath", f"{Path(output_path).name}.png")

        # Sort frames alphabetically and numerically by name
        sorted_frames = sorted(self.frames, key=lambda f: self._natural_sort_key(f.name))

        for frame in sorted_frames:
            subtexture = ET.SubElement(root, "SubTexture")
            subtexture.set("name", frame.name)
            subtexture.set("x", str(frame.x))
            subtexture.set("y", str(frame.y))
            subtexture.set("width", str(frame.width))
            subtexture.set("height", str(frame.height))
            # Use proper frame offset and original dimensions for Sparrow format
            subtexture.set(
                "frameX", str(-frame.frame_x)
            )  # Negative because it's offset from origin
            subtexture.set("frameY", str(-frame.frame_y))
            subtexture.set("frameWidth", str(frame.original_width))
            subtexture.set("frameHeight", str(frame.original_height))
            subtexture.set("flipX", "false")
            subtexture.set("flipY", "false")
            subtexture.set("rotated", str(frame.rotated).lower())

        # Create XML string with proper header and comments
        xml_declaration = '<?xml version="1.0" encoding="utf-8"?>\n'

        # Pretty print XML
        from xml.dom import minidom

        rough_string = ET.tostring(root, encoding="unicode")
        parsed = minidom.parseString(rough_string)
        pretty_xml = parsed.toprettyxml(indent="  ")

        # Remove the default XML declaration from minidom output
        lines = pretty_xml.split("\n")
        if lines[0].startswith("<?xml"):
            lines = lines[1:]

        # Add our custom header and comments
        result_lines = [xml_declaration.rstrip()]
        result_lines.append(f'<TextureAtlas imagePath="{Path(output_path).name}.png">')
        result_lines.append(f"    <!-- Generated by TextureAtlas Toolbox v{current_version} -->")

        # Add optimization level info if available
        if settings:
            result_lines.append(f"    <!-- Optimization Level: {settings.optimization_level} -->")

        result_lines.append("    <!-- https://textureatlastoolbox.com/ -->")
        result_lines.append(
            "    <!-- https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/ -->"
        )

        # Add all SubTexture elements
        for frame in sorted_frames:
            result_lines.append(
                f'    <SubTexture name="{frame.name}" x="{frame.x}" y="{frame.y}" '
                + f'width="{frame.width}" height="{frame.height}" frameX="{-frame.frame_x}" frameY="{-frame.frame_y}" '
                + f'frameWidth="{frame.original_width}" frameHeight="{frame.original_height}" '
                + f'flipX="false" flipY="false" rotated="{str(frame.rotated).lower()}"/>'
            )

        result_lines.append("</TextureAtlas>")

        return "\n".join(result_lines)

    def _natural_sort_key(self, text: str):
        """Generate a key for natural sorting (handles numbers properly)."""
        # Split text into parts: letters and numbers
        parts = re.split(r"(\d+)", text)
        # Convert numeric parts to integers for proper sorting
        result = []
        for part in parts:
            if part.isdigit():
                result.append(int(part))
            else:
                result.append(part)
        return result

    def _calculate_efficiency(self, atlas_width: int, atlas_height: int) -> float:
        """Calculate packing efficiency."""
        if not self.frames:
            return 0.0

        used_area = sum(f.area for f in self.frames)
        total_area = atlas_width * atlas_height
        return (used_area / total_area) * 100 if total_area > 0 else 0.0

    def _next_power_of_2(self, value: int) -> int:
        """Find the next power of 2 greater than or equal to value."""
        return 2 ** int(np.ceil(np.log2(value)))

    def _update_progress(self, current: int, total: int, message: str = ""):
        """Update progress callback."""
        if self.progress_callback:
            self.progress_callback(current, total, message)

    def _get_trim_bounds(self, img: Image.Image) -> Optional[Tuple[int, int, int, int]]:
        """
        Get the bounding box of non-transparent pixels in an image.
        Returns (left, top, right, bottom) or None if image is fully transparent.
        """

        if img.mode != "RGBA":
            img = img.convert("RGBA")

        alpha = img.split()[-1]

        bbox = alpha.getbbox()
        if bbox is None:
            return None

        return bbox

    @staticmethod
    def fast_image_cmp(img1: Image.Image, img2: Image.Image) -> bool:
        """
        Fast image comparison - check if two images are identical.
        Returns True if images are the same, False otherwise.
        """
        if img1.size != img2.size:
            return False
        if img1.tobytes() != img2.tobytes():
            return False

        # Additional check using PIL's built-in difference
        from PIL import ImageChops

        return ImageChops.difference(img1, img2).getbbox() is None
