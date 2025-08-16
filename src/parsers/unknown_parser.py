#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Qt-compatible unknown parser for sprite data.
Replaces the tkinter-dependent unknown_parser.py with a UI-agnostic implementation.
"""

import os
from typing import Set, Optional, Callable, List, Dict, Any, Tuple
from PIL import Image
import numpy as np

# Import our own modules
from parsers.base_parser import BaseParser, populate_qt_listbox

# Qt imports
from PySide6.QtWidgets import QMessageBox, QApplication


class UnknownParser(BaseParser):
    """
    A Qt-compatible class to parse unknown spritesheets without metadata files by detecting sprite boundaries.

    This parser analyzes an image to automatically detect individual sprites based on
    connected regions of pixels with opacity >= 1%. Each detected region is treated
    as a separate sprite and exported as individual frames.
    This is an experimental fallback feature and may not work for all spritesheets.

    This class is UI-agnostic and can work with both Qt and tkinter interfaces.
    """

    def __init__(
        self,
        directory: str,
        image_filename: str,
        listbox_data=None,
        name_callback: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize the unknown parser.

        Args:
            directory: The directory where the image file is located
            image_filename: The name of the image file to parse
            listbox_data: Optional listbox widget (Qt or tkinter) to populate with detected sprite names
            name_callback: Optional callback function to call for each extracted name
        """
        super().__init__(directory, image_filename, name_callback)
        self.listbox_data = listbox_data

    def extract_names(self) -> Set[str]:
        """Detect sprites in the image and return their names."""
        try:
            file_path = os.path.join(self.directory, self.filename)
            _, sprites = self.parse_unknown_image(file_path)

            names = set()
            for i, sprite in enumerate(sprites):
                # Generate names like "sprite_001", "sprite_002", etc.
                name = f"sprite_{i + 1:03d}"
                names.add(name)

            return names
        except Exception as e:
            print(f"Error extracting names from image {self.filename}: {e}")
            return set()

    def populate_listbox(self, names: Set[str]):
        """Populate the Qt listbox with names."""
        if self.listbox_data is None:
            return

        populate_qt_listbox(self.listbox_data, names)

    @staticmethod
    def parse_unknown_image(
        file_path: str, parent_window=None
    ) -> Tuple[Image.Image, List[Dict[str, Any]]]:
        """
        Static method to analyze an image and return both processed image and sprite information.

        Args:
            file_path: Path to the image file
            parent_window: Optional parent window for dialogs (Qt or tkinter)

        Returns:
            Tuple of (processed_image, list_of_sprite_data)
        """
        try:
            from PIL import Image

            # Ignore any decompression bomb warnings/errors and always allow large images
            Image.MAX_IMAGE_PIXELS = None
            image = Image.open(file_path)

            # Ensure the image has an alpha channel
            if image.mode != "RGBA":
                image = image.convert("RGBA")

            # Detect background color if needed
            background_color = UnknownParser._detect_background_color(image)

            # Apply color keying if background was detected
            if background_color and UnknownParser._should_apply_color_keying(
                background_color, parent_window
            ):
                processed_image = UnknownParser._apply_color_keying(image, background_color)
            else:
                processed_image = image

            # Find sprites using connected regions
            sprites = UnknownParser._find_sprites_in_image(processed_image)

            return processed_image, sprites

        except Exception as e:
            print(f"Error parsing unknown image {file_path}: {e}")
            from PIL import Image

            return Image.new("RGBA", (1, 1), (0, 0, 0, 0)), []

    @staticmethod
    def _detect_background_color(image: Image.Image) -> Optional[Tuple[int, int, int]]:
        """Detect the most common background color."""
        try:
            # Convert to RGB for color detection (ignore alpha)
            rgb_image = image.convert("RGB")

            # Get the most common color from the edges
            width, height = image.size
            edge_pixels = []

            # Sample from edges
            for x in range(width):
                edge_pixels.append(rgb_image.getpixel((x, 0)))  # Top edge
                edge_pixels.append(rgb_image.getpixel((x, height - 1)))  # Bottom edge

            for y in range(height):
                edge_pixels.append(rgb_image.getpixel((0, y)))  # Left edge
                edge_pixels.append(rgb_image.getpixel((width - 1, y)))  # Right edge

            # Find most common color
            from collections import Counter

            color_counts = Counter(edge_pixels)
            most_common = color_counts.most_common(1)

            if (
                most_common and most_common[0][1] > len(edge_pixels) * 0.1
            ):  # At least 10% of edge pixels
                return most_common[0][0]

            return None
        except Exception:
            return None

    @staticmethod
    def _should_apply_color_keying(
        background_color: Tuple[int, int, int], parent_window=None
    ) -> bool:
        """Ask user if they want to apply color keying to remove background."""
        try:
            # Find the main window if parent is not provided
            if parent_window is None:
                app = QApplication.instance()
                if app:
                    for widget in app.topLevelWidgets():
                        if widget.isMainWindow():
                            parent_window = widget
                            break

            msg_box = QMessageBox(parent_window)
            msg_box.setIcon(QMessageBox.Icon.Question)
            msg_box.setWindowTitle("Background Color Detected")
            msg_box.setText(
                f"Detected background color: RGB{background_color}\n\n"
                "Would you like to remove this background color and make it transparent?"
            )
            msg_box.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            result = msg_box.exec()
            return result == QMessageBox.StandardButton.Yes
        except Exception:
            # Default to not applying color keying if dialog fails
            return False

    @staticmethod
    def _apply_color_keying(
        image: Image.Image, background_color: Tuple[int, int, int], tolerance: int = 10
    ) -> Image.Image:
        """Apply color keying to make background color transparent."""
        try:
            # Convert to numpy array for faster processing
            img_array = np.array(image)

            # Create mask for pixels that match background color (within tolerance)
            r, g, b = background_color
            mask = (
                (np.abs(img_array[:, :, 0] - r) <= tolerance)
                & (np.abs(img_array[:, :, 1] - g) <= tolerance)
                & (np.abs(img_array[:, :, 2] - b) <= tolerance)
            )

            # Set alpha to 0 for background pixels
            img_array[mask, 3] = 0

            # Convert back to PIL Image
            return Image.fromarray(img_array, "RGBA")
        except Exception as e:
            print(f"Error applying color keying: {e}")
            return image

    @staticmethod
    def _find_sprites_in_image(image: Image.Image) -> List[Dict[str, Any]]:
        """Find individual sprites in the image using connected component analysis."""
        try:
            # Convert to numpy array
            img_array = np.array(image)

            # Create binary mask from alpha channel (pixels with alpha > 0)
            alpha_mask = img_array[:, :, 3] > 0

            # Find connected regions
            regions = UnknownParser._find_connected_regions(alpha_mask)

            sprites = []
            for i, region in enumerate(regions):
                if len(region) > 10:  # Filter out very small regions (noise)
                    bbox = UnknownParser._get_bounding_box(region)
                    sprite_data = {
                        "name": f"sprite_{i + 1:03d}",
                        "x": bbox[0],
                        "y": bbox[1],
                        "width": bbox[2] - bbox[0],
                        "height": bbox[3] - bbox[1],
                    }
                    sprites.append(sprite_data)

            return sprites
        except Exception as e:
            print(f"Error finding sprites in image: {e}")
            return []

    @staticmethod
    def _find_connected_regions(alpha_mask: np.ndarray) -> List[List[Tuple[int, int]]]:
        """Find connected regions in an alpha mask using flood fill."""
        try:
            height, width = alpha_mask.shape
            visited = np.zeros_like(alpha_mask, dtype=bool)
            regions = []

            def flood_fill(start_x, start_y):
                stack = [(start_x, start_y)]
                region = []

                while stack:
                    x, y = stack.pop()
                    if (
                        x < 0
                        or x >= width
                        or y < 0
                        or y >= height
                        or visited[y, x]
                        or not alpha_mask[y, x]
                    ):
                        continue

                    visited[y, x] = True
                    region.append((x, y))

                    # Add 8-connected neighbors
                    for dx in [-1, 0, 1]:
                        for dy in [-1, 0, 1]:
                            if dx != 0 or dy != 0:
                                stack.append((x + dx, y + dy))

                return region

            # Find all connected regions
            for y in range(height):
                for x in range(width):
                    if alpha_mask[y, x] and not visited[y, x]:
                        region = flood_fill(x, y)
                        if region:
                            regions.append(region)

            return regions
        except Exception as e:
            print(f"Error finding connected regions: {e}")
            return []

    @staticmethod
    def _get_bounding_box(region_coords: List[Tuple[int, int]]) -> Tuple[int, int, int, int]:
        """Calculate the bounding box of a region."""
        if not region_coords:
            return (0, 0, 0, 0)

        x_coords = [coord[0] for coord in region_coords]
        y_coords = [coord[1] for coord in region_coords]

        return (min(x_coords), min(y_coords), max(x_coords) + 1, max(y_coords) + 1)

    @staticmethod
    def _has_transparency(image: Image.Image) -> bool:
        """Check if the image has transparent pixels."""
        try:
            if image.mode != "RGBA":
                return False

            # Convert to numpy array for faster processing
            img_array = np.array(image)

            # Check if any pixel has alpha < 255 (transparent)
            return np.any(img_array[:, :, 3] < 255)
        except Exception as e:
            print(f"Error checking transparency: {e}")
            return False

    @staticmethod
    def _detect_background_colors(
        image: Image.Image, max_colors: int = 3
    ) -> List[Tuple[int, int, int]]:
        """Detect multiple background colors from image edges."""
        try:
            # Convert to RGB for color detection (ignore alpha)
            rgb_image = image.convert("RGB")

            width, height = image.size
            edge_pixels = []

            # Sample from edges more comprehensively
            # Top and bottom edges
            for x in range(0, width, max(1, width // 50)):  # Sample every ~2% of width
                edge_pixels.append(rgb_image.getpixel((x, 0)))  # Top edge
                if height > 1:
                    edge_pixels.append(rgb_image.getpixel((x, height - 1)))  # Bottom edge

            # Left and right edges
            for y in range(0, height, max(1, height // 50)):  # Sample every ~2% of height
                edge_pixels.append(rgb_image.getpixel((0, y)))  # Left edge
                if width > 1:
                    edge_pixels.append(rgb_image.getpixel((width - 1, y)))  # Right edge

            # Sample corners more heavily
            corners = [(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)]
            for corner in corners:
                for _ in range(5):  # Weight corners more heavily
                    edge_pixels.append(rgb_image.getpixel(corner))

            # Find most common colors
            from collections import Counter

            color_counts = Counter(edge_pixels)

            # Filter colors that appear frequently enough to be considered background
            min_occurrences = max(1, len(edge_pixels) * 0.05)  # At least 5% of edge pixels
            background_colors = []

            for color, count in color_counts.most_common(max_colors * 2):  # Get more candidates
                if count >= min_occurrences and len(background_colors) < max_colors:
                    background_colors.append(color)

            return background_colors

        except Exception as e:
            print(f"Error detecting background colors: {e}")
            return []
