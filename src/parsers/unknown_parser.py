import os
import tkinter as tk
from PIL import Image
import numpy as np

GUI_AVAILABLE = True  # We'll check for specific dialog availability in the code


class UnknownParser:
    """
    A class to parse unknown spritesheets without metadata files by detecting sprite boundaries.

    This parser analyzes an image to automatically detect individual sprites based on
    connected regions of pixels with opacity >= 1%. Each detected region is treated
    as a separate sprite and exported as individual frames.
    This is an experimental fallback feature and may not work for all spritesheets.

    Attributes:
        directory (str): The directory where the image file is located.
        image_filename (str): The name of the image file to parse.
        listbox_data (tk.Listbox): The Tkinter listbox to populate with detected sprite names.    Methods:
        get_data(): Analyzes the image and populates the listbox with detected sprite names.
        extract_names(): Detects sprites in the image and returns their names.
        get_names(names): Populates the listbox with the given names.
        parse_unknown_image(file_path, parent_window=None): Static method to analyze an image and return sprite information.
        _find_connected_regions(alpha_mask): Static method to find connected regions in an alpha mask.
        _get_bounding_box(region_coords): Static method to calculate the bounding box of a region.
        _detect_background_color(image): Static method to detect the most common background color.
        _apply_color_keying(image, background_color, tolerance): Static method to make background color transparent.
        _parse_excluding_background(image, file_path, background_color): Static method to parse sprites while excluding background color pixels.
    """

    def __init__(self, directory, image_filename, listbox_data):
        self.directory = directory
        self.image_filename = image_filename
        self.listbox_data = listbox_data

    def get_data(self):
        names = self.extract_names()
        self.get_names(names)

    def extract_names(self):
        names = {f"unsupported spritesheet - {os.path.splitext(self.image_filename)[0]}"}
        return names

    def get_names(self, names):
        for name in names:
            self.listbox_data.insert(tk.END, name)

    @staticmethod
    def parse_unknown_image(file_path, parent_window=None):
        """
        Analyzes an image file to automatically detect sprite boundaries.

        Args:
            file_path (str): Path to the image file to analyze
            parent_window (tk.Tk, optional): Parent window for displaying dialogs

        Returns:
            list: List of sprite dictionaries with keys: name, x, y, width, height
        """
        try:
            image = Image.open(file_path)

            if image.mode != "RGBA":
                image = image.convert("RGBA")            # Detect and apply background color keying if the image doesn't have full transparency
            if not UnknownParser._has_transparency(image):
                background_colors = UnknownParser._detect_background_colors(image, max_colors=3)
                if background_colors:
                    # Check if user choice has been pre-determined (from the batch detection dialog)
                    keying_action = "key_background"  # Default action

                    # Import the dialog class to check for stored user choice
                    try:
                        from gui.background_keying_dialog import BackgroundKeyingDialog
                        if hasattr(BackgroundKeyingDialog, '_user_choice') and BackgroundKeyingDialog._user_choice:
                            keying_action = BackgroundKeyingDialog._user_choice
                            print(f"Using pre-determined user choice: {keying_action}")
                        else:
                            # Fallback to individual dialog if no batch choice was made
                            # For display purposes, show the primary background color in the dialog
                            primary_bg_color = background_colors[0]
                            bg_color_display = f"{primary_bg_color}"
                            if len(background_colors) > 1:
                                bg_color_display += f" (+ {len(background_colors) - 1} additional colors)"

                            if GUI_AVAILABLE and parent_window:
                                try:
                                    keying_action = BackgroundKeyingDialog.show_dialog(
                                        parent_window, os.path.basename(file_path), bg_color_display
                                    )
                                except Exception as e:
                                    print(f"Error showing background keying dialog: {e}")
                                    print("Defaulting to automatic multi-color keying")
                            else:
                                print(
                                    f"Detected {len(background_colors)} background color(s) in {file_path}: {background_colors}"
                                )
                                print(
                                    "GUI not available or no parent window - defaulting to automatic multi-color keying"
                                )
                    except ImportError:
                        print("Background keying dialog not available - defaulting to automatic multi-color keying")

                    if keying_action == "cancel":
                        print("User cancelled processing of unknown atlas")
                        return []
                    elif keying_action == "key_background":
                        print(
                            f"Applying multi-color keying to remove {len(background_colors)} background color(s)..."
                        )
                        image = UnknownParser._apply_multi_color_keying(image, background_colors)
                    elif keying_action == "exclude_background":
                        print(
                            f"Processing sprites while excluding {len(background_colors)} background color(s)..."
                        )
                        return UnknownParser._parse_excluding_multiple_backgrounds(
                            image, file_path, background_colors
                        )

            img_array = np.array(image)

            # Create alpha mask - pixels with >= 1% opacity (alpha >= 2.55)
            alpha_channel = img_array[:, :, 3]
            alpha_mask = alpha_channel >= int(255 * 0.01)

            regions = UnknownParser._find_connected_regions(alpha_mask)

            sprites = []
            base_name = os.path.splitext(os.path.basename(file_path))[0]

            for i, region in enumerate(regions):
                if len(region) == 0:
                    continue

                bbox = UnknownParser._get_bounding_box(region)
                x, y, width, height = bbox

                # Skip very small regions (likely noise)
                if width < 2 or height < 2:
                    continue

                # Apply precise cropping to remove remaining background/transparent areas
                cropped_x, cropped_y, cropped_width, cropped_height = UnknownParser._crop_sprite_precisely(
                    image, x, y, width, height
                )

                sprite_name = f"unsupported spritesheet - {base_name} - {i + 1:04d}"
                sprites.append(
                    {"name": sprite_name, "x": cropped_x, "y": cropped_y, "width": cropped_width, "height": cropped_height}
                )

            print(f"Detected {len(sprites)} sprites in unknown spritesheet: {file_path}")
            return sprites

        except Exception as e:
            print(f"Error parsing unknown image {file_path}: {str(e)}")
            return []

    @staticmethod
    def _find_connected_regions(alpha_mask):
        """
        Find connected regions of pixels in a binary mask using flood fill.

        Args:
            alpha_mask (numpy.ndarray): Binary mask of pixels with sufficient opacity

        Returns:
            list: List of regions, where each region is a list of (y, x) coordinates
        """
        height, width = alpha_mask.shape
        visited = np.zeros_like(alpha_mask, dtype=bool)
        regions = []

        def flood_fill(start_y, start_x):
            """Flood fill to find all connected pixels in a region."""
            stack = [(start_y, start_x)]
            region = []

            while stack:
                y, x = stack.pop()

                if (
                    y < 0
                    or y >= height
                    or x < 0
                    or x >= width
                    or visited[y, x]
                    or not alpha_mask[y, x]
                ):
                    continue

                visited[y, x] = True
                region.append((y, x))

                # Add adjacent pixels (4-connectivity)
                stack.extend([(y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)])

            return region

        # Find all connected regions
        for y in range(height):
            for x in range(width):
                if alpha_mask[y, x] and not visited[y, x]:
                    region = flood_fill(y, x)
                    if region:
                        regions.append(region)

        return regions

    @staticmethod
    def _get_bounding_box(region_coords):
        """
        Calculate the bounding box of a region.

        Args:
            region_coords (list): List of (y, x) coordinates

        Returns:
            tuple: (x, y, width, height) of the bounding box
        """
        if not region_coords:
            return (0, 0, 0, 0)

        y_coords = [coord[0] for coord in region_coords]
        x_coords = [coord[1] for coord in region_coords]

        min_x = min(x_coords)
        max_x = max(x_coords)
        min_y = min(y_coords)
        max_y = max(y_coords)

        width = max_x - min_x + 1
        height = max_y - min_y + 1

        return (min_x, min_y, width, height)

    @staticmethod
    def _has_transparency(image):
        """
        Check if the image already has meaningful transparency.

        Args:
            image (PIL.Image): The image to check

        Returns:
            bool: True if the image has pixels with alpha < 255, False otherwise
        """
        if image.mode != "RGBA":
            return False

        img_array = np.array(image)
        alpha_channel = img_array[:, :, 3]
        return np.any(alpha_channel < 255)

    @staticmethod
    def _detect_background_colors(image, max_colors=3):
        """
        Detect multiple background colors by sampling edges and analyzing the entire image.
        Enhanced to better detect grid lines and bounding box colors typical in Sega Genesis-style sprites.

        Args:
            image (PIL.Image): The image to analyze
            max_colors (int): Maximum number of background colors to detect

        Returns:
            list: List of RGB tuples of detected background colors, ordered by dominance
        """
        try:
            rgb_image = image.convert("RGB")
            img_array = np.array(rgb_image)
            height, width = img_array.shape[:2]

            edge_pixels = []

            # 1. Sample all border pixels (most reliable for background detection)
            # Top and bottom edges - these are most likely to be background
            edge_pixels.extend(img_array[0, :].reshape(-1, 3))  # Top row
            edge_pixels.extend(img_array[-1, :].reshape(-1, 3))  # Bottom row

            # Left and right edges (excluding corners to avoid double counting)
            if height > 2:
                edge_pixels.extend(img_array[1:-1, 0].reshape(-1, 3))  # Left column
                edge_pixels.extend(img_array[1:-1, -1].reshape(-1, 3))  # Right column

            # 2. Sample corners (very likely to be background)
            corner_samples = [
                img_array[0, 0],
                img_array[0, -1],
                img_array[-1, 0],
                img_array[-1, -1],  # Corners
            ]
            edge_pixels.extend(corner_samples)

            # 3. Sample from a coarse grid pattern to catch grid lines/bounding boxes
            # Use larger steps to avoid over-sampling sprite content
            grid_step = max(8, min(width, height) // 15)
            for y in range(0, height, grid_step):
                for x in range(0, width, grid_step):
                    # Only sample if we're near edges or corners
                    edge_distance = min(x, y, width - 1 - x, height - 1 - y)
                    if edge_distance <= max(5, min(width, height) // 20):
                        edge_pixels.append(img_array[y, x])

            # 4. Sample from regular grid lines that might represent sprite boundaries
            # but only near the edges
            # Vertical lines near edges
            if width > 20:
                line_step = width // 8  # Check fewer vertical lines
                for x in range(line_step, width, line_step):
                    # Sample points along this vertical line, but prefer edge areas
                    for y in [0, height // 4, height // 2, 3 * height // 4, height - 1]:
                        if 0 <= y < height:
                            edge_pixels.append(img_array[y, x])

            # Horizontal lines near edges
            if height > 20:
                line_step = height // 8  # Check fewer horizontal lines
                for y in range(line_step, height, line_step):
                    # Sample points along this horizontal line, but prefer edge areas
                    for x in [0, width // 4, width // 2, 3 * width // 4, width - 1]:
                        if 0 <= x < width:
                            edge_pixels.append(img_array[y, x])

            edge_colors = [tuple(int(val) for val in pixel) for pixel in edge_pixels]

            color_counts = {}
            for color in edge_colors:
                color_counts[color] = color_counts.get(color, 0) + 1

            if not color_counts:
                return []

            # Sort colors by frequency
            sorted_colors = sorted(color_counts.items(), key=lambda x: x[1], reverse=True)

            background_colors = []
            total_edge_pixels = len(edge_colors)

            for i, (color, count) in enumerate(sorted_colors[: max_colors * 2]):
                dominance = count / total_edge_pixels

                # More strict thresholds for detecting background vs sprite colors
                if i == 0 and dominance > 0.25:
                    background_colors.append(color)
                    print(
                        f"Primary background color detected: {color} (dominance: {dominance:.2%})"
                    )
                elif i > 0 and dominance > 0.08:
                    # Check if this color is different enough from already detected colors
                    is_different = True
                    for existing_color in background_colors:
                        color_distance = np.sqrt(
                            sum((a - b) ** 2 for a, b in zip(color, existing_color))
                        )
                        if color_distance < 25:
                            is_different = False
                            break

                    if is_different and len(background_colors) < max_colors:
                        background_colors.append(color)
                        print(
                            f"Secondary background color detected: {color} (dominance: {dominance:.2%})"
                        )
                else:
                    if dominance <= 0.08:
                        break

            # Additional validation: check if detected colors actually appear in large connected regions
            # This helps distinguish background colors from sprite details
            validated_colors = []
            for color in background_colors:
                # Count how many times this color appears in the entire image
                color_mask = np.all(img_array == color, axis=2)
                total_occurrences = np.sum(color_mask)
                total_pixels = width * height
                overall_dominance = total_occurrences / total_pixels

                # Also check if this color forms large connected regions (typical of backgrounds)
                regions = UnknownParser._find_connected_regions(color_mask)
                if regions:
                    largest_region_size = max(len(region) for region in regions)
                    largest_region_ratio = (
                        largest_region_size / total_occurrences if total_occurrences > 0 else 0
                    )
                    total_large_regions = sum(
                        1 for region in regions if len(region) > min(100, total_occurrences * 0.1)
                    )
                else:
                    largest_region_ratio = 0
                    total_large_regions = 0

                # Determine if this color is likely a background color based on:
                # 1. Very dominant colors (>50% of image) are likely background even if fragmented
                # 2. Colors with large connected regions are likely background
                # 3. Colors with many medium-sized regions might be background too (e.g., fragmented by grid)
                is_background = False

                if overall_dominance > 0.5:  # Very dominant color is probably background
                    is_background = True
                    reason = "dominant color"
                elif (
                    overall_dominance > 0.02 and largest_region_ratio > 0.7
                ):  # Large connected region
                    is_background = True
                    reason = "large connected region"
                elif (
                    overall_dominance > 0.05 and total_large_regions >= 3
                ):  # Multiple substantial regions
                    is_background = True
                    reason = "multiple substantial regions"
                elif (
                    overall_dominance > 0.02 and len(regions) == 1
                ):  # Single region, even if not huge
                    is_background = True
                    reason = "single connected region"

                if is_background:
                    validated_colors.append(color)
                    print(
                        f"Validated background color {color}: {overall_dominance:.2%} of total image, largest region: {largest_region_ratio:.1%} ({reason})"
                    )
                else:
                    print(
                        f"Rejected background color {color}: {overall_dominance:.2%} of total image, largest region: {largest_region_ratio:.1%} (likely sprite color)"
                    )

            return validated_colors

        except Exception as e:
            print(f"Error detecting background colors: {str(e)}")
            return []

    @staticmethod
    def _detect_background_color(image):
        """
        Detect the most common background color (for backward compatibility).

        Args:
            image (PIL.Image): The image to analyze

        Returns:
            tuple: RGB tuple of the detected background color, or None if detection fails
        """
        colors = UnknownParser._detect_background_colors(image, max_colors=1)
        return colors[0] if colors else None

    @staticmethod
    def _apply_color_keying(image, background_color, tolerance=30):
        """
        Apply color keying to make the background color transparent.

        Args:
            image (PIL.Image): The image to process
            background_color (tuple): RGB tuple of the background color to key out
            tolerance (int): Color tolerance for matching (0-255)

        Returns:
            PIL.Image: The image with background color made transparent
        """
        try:
            if image.mode != "RGBA":
                image = image.convert("RGBA")

            img_array = np.array(image)
            height, width = img_array.shape[:2]

            r, g, b = img_array[:, :, 0], img_array[:, :, 1], img_array[:, :, 2]
            bg_r, bg_g, bg_b = background_color

            # Calculate color distance from background color
            color_distance = np.sqrt(
                (r.astype(int) - bg_r) ** 2
                + (g.astype(int) - bg_g) ** 2
                + (b.astype(int) - bg_b) ** 2
            )
            # Create mask for pixels that match the background color within tolerance
            background_mask = color_distance <= tolerance

            # Set alpha to 0 for background pixels
            img_array[background_mask, 3] = 0

            # Create new image from modified array
            keyed_image = Image.fromarray(img_array, "RGBA")

            transparent_count = np.sum(background_mask)
            total_pixels = width * height
            percentage = (transparent_count / total_pixels) * 100

            print(
                f"Color keying applied: {transparent_count}/{total_pixels} pixels ({percentage:.1f}%) made transparent"
            )

            return keyed_image

        except Exception as e:
            print(f"Error applying color keying: {str(e)}")
            return image

    @staticmethod
    def _apply_multi_color_keying(image, background_colors, tolerance=35):
        """
        Apply color keying to make multiple background colors transparent.
        Enhanced with improved tolerance handling for better background removal.

        Args:
            image (PIL.Image): The image to process
            background_colors (list): List of RGB tuples of background colors to key out
            tolerance (int): Color tolerance for matching (0-255)

        Returns:
            PIL.Image: The image with background colors made transparent
        """
        try:
            if not background_colors:
                return image

            if image.mode != "RGBA":
                image = image.convert("RGBA")

            img_array = np.array(image)
            height, width = img_array.shape[:2]

            r, g, b = img_array[:, :, 0], img_array[:, :, 1], img_array[:, :, 2]

            # Create combined mask for all background colors
            combined_mask = np.zeros((height, width), dtype=bool)

            total_keyed = 0
            for i, bg_color in enumerate(background_colors):
                bg_r, bg_g, bg_b = bg_color

                # Calculate color distance from background color
                color_distance = np.sqrt(
                    (r.astype(int) - bg_r) ** 2
                    + (g.astype(int) - bg_g) ** 2
                    + (b.astype(int) - bg_b) ** 2
                )

                # Use adaptive tolerance - higher tolerance for primary background color
                adaptive_tolerance = tolerance if i == 0 else max(25, tolerance - 10)

                # Create mask for pixels that match this background color within tolerance
                bg_mask = color_distance <= adaptive_tolerance
                combined_mask |= bg_mask

                keyed_count = np.sum(bg_mask)
                total_keyed += keyed_count
                print(
                    f"Color {i + 1} {bg_color}: {keyed_count} pixels keyed (tolerance: {adaptive_tolerance})"
                )

            # Additional pass: detect and key out pixels that are "close enough" to any background color
            # This helps with anti-aliasing and similar colors around sprite edges
            if len(background_colors) > 0:
                # Create a more aggressive mask for edge cleanup
                edge_cleanup_mask = np.zeros((height, width), dtype=bool)

                for bg_color in background_colors:
                    bg_r, bg_g, bg_b = bg_color
                    color_distance = np.sqrt(
                        (r.astype(int) - bg_r) ** 2
                        + (g.astype(int) - bg_g) ** 2
                        + (b.astype(int) - bg_b) ** 2
                    )

                    # More aggressive tolerance for edge cleanup
                    edge_cleanup_tolerance = tolerance + 15
                    edge_mask = color_distance <= edge_cleanup_tolerance
                    edge_cleanup_mask |= edge_mask
                # Only apply edge cleanup to pixels that are adjacent to already keyed pixels
                # This prevents removing sprite colors that happen to be similar to background
                # Using basic numpy operations instead of scipy for edge detection

                # Create a simple dilation by checking neighboring pixels
                dilated_mask = np.copy(combined_mask)
                h, w = combined_mask.shape

                # Check 4-connected neighbors (up, down, left, right)
                for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    # Shift the mask in each direction to find adjacent pixels
                    shifted_mask = np.zeros_like(combined_mask)

                    if dy == -1:  # Up
                        shifted_mask[1:, :] = combined_mask[:-1, :]
                    elif dy == 1:  # Down
                        shifted_mask[:-1, :] = combined_mask[1:, :]
                    elif dx == -1:  # Left
                        shifted_mask[:, 1:] = combined_mask[:, :-1]
                    elif dx == 1:  # Right
                        shifted_mask[:, :-1] = combined_mask[:, 1:]

                    dilated_mask |= shifted_mask

                # Apply edge cleanup only to adjacent pixels
                additional_cleanup = edge_cleanup_mask & dilated_mask & ~combined_mask
                combined_mask |= additional_cleanup

                cleanup_count = np.sum(additional_cleanup)
                if cleanup_count > 0:
                    print(f"Edge cleanup: {cleanup_count} additional pixels keyed")
                    total_keyed += cleanup_count

            # Set alpha to 0 for all background pixels
            img_array[combined_mask, 3] = 0

            # Create new image from modified array
            keyed_image = Image.fromarray(img_array, "RGBA")

            total_pixels = width * height
            percentage = (total_keyed / total_pixels) * 100

            print(
                f"Enhanced multi-color keying applied: {total_keyed}/{total_pixels} pixels ({percentage:.1f}%) made transparent"
            )

            return keyed_image

        except Exception as e:
            print(f"Error applying multi-color keying: {str(e)}")
            # Fall back to basic multi-color keying without edge cleanup
            try:
                return UnknownParser._apply_basic_multi_color_keying(
                    image, background_colors, tolerance
                )
            except Exception:
                return image

    @staticmethod
    def _apply_basic_multi_color_keying(image, background_colors, tolerance=30):
        """
        Basic multi-color keying without advanced edge cleanup (fallback method).

        Args:
            image (PIL.Image): The image to process
            background_colors (list): List of RGB tuples of background colors to key out
            tolerance (int): Color tolerance for matching (0-255)

        Returns:
            PIL.Image: The image with background colors made transparent
        """
        try:
            if not background_colors:
                return image

            if image.mode != "RGBA":
                image = image.convert("RGBA")

            img_array = np.array(image)
            height, width = img_array.shape[:2]

            r, g, b = img_array[:, :, 0], img_array[:, :, 1], img_array[:, :, 2]

            # Create combined mask for all background colors
            combined_mask = np.zeros((height, width), dtype=bool)

            total_keyed = 0
            for i, bg_color in enumerate(background_colors):
                bg_r, bg_g, bg_b = bg_color

                # Calculate color distance from background color
                color_distance = np.sqrt(
                    (r.astype(int) - bg_r) ** 2
                    + (g.astype(int) - bg_g) ** 2
                    + (b.astype(int) - bg_b) ** 2
                )

                # Create mask for pixels that match this background color within tolerance
                bg_mask = color_distance <= tolerance
                combined_mask |= bg_mask

                keyed_count = np.sum(bg_mask)
                total_keyed += keyed_count
                print(f"Basic keying - Color {i + 1} {bg_color}: {keyed_count} pixels keyed")

            # Set alpha to 0 for all background pixels
            img_array[combined_mask, 3] = 0

            # Create new image from modified array
            keyed_image = Image.fromarray(img_array, "RGBA")

            total_pixels = width * height
            percentage = (total_keyed / total_pixels) * 100

            print(
                f"Basic multi-color keying applied: {total_keyed}/{total_pixels} pixels ({percentage:.1f}%) made transparent"
            )

            return keyed_image

        except Exception as e:
            print(f"Error applying basic multi-color keying: {str(e)}")
            return image

    @staticmethod
    def _parse_excluding_background(image, file_path, background_color, tolerance=30):
        """
        Parse sprites while excluding background color pixels from sprite detection.

        Args:
            image (PIL.Image): The image to process
            file_path (str): Path to the image file (for naming)
            background_color (tuple): RGB tuple of the background color to exclude
            tolerance (int): Color tolerance for background matching (0-255)

        Returns:
            list: List of sprite dictionaries with keys: name, x, y, width, height
        """
        try:
            if image.mode != "RGBA":
                image = image.convert("RGBA")

            img_array = np.array(image)
            height, width = img_array.shape[:2]

            r, g, b = img_array[:, :, 0], img_array[:, :, 1], img_array[:, :, 2]
            bg_r, bg_g, bg_b = background_color

            # Calculate color distance from background color
            color_distance = np.sqrt(
                (r.astype(int) - bg_r) ** 2
                + (g.astype(int) - bg_g) ** 2
                + (b.astype(int) - bg_b) ** 2
            )

            # Create mask for non-background pixels
            # This includes pixels that don't match the background color AND have some opacity
            alpha_channel = img_array[:, :, 3]
            non_background_mask = (color_distance > tolerance) & (alpha_channel >= int(255 * 0.01))

            # Find connected regions in the non-background mask
            regions = UnknownParser._find_connected_regions(non_background_mask)

            sprites = []
            base_name = os.path.splitext(os.path.basename(file_path))[0]

            for i, region in enumerate(regions):
                if len(region) == 0:
                    continue

                # Calculate bounding box
                bbox = UnknownParser._get_bounding_box(region)
                x, y, width, height = bbox

                # Skip very small regions (likely noise)
                if width < 2 or height < 2:
                    continue

                # Apply precise cropping to remove remaining background/transparent areas
                cropped_x, cropped_y, cropped_width, cropped_height = UnknownParser._crop_sprite_precisely(
                    image, x, y, width, height
                )

                sprite_name = f"unsupported spritesheet - {base_name} - {i + 1:04d}"
                sprites.append(
                    {"name": sprite_name, "x": cropped_x, "y": cropped_y, "width": cropped_width, "height": cropped_height}
                )

            background_count = np.sum(color_distance <= tolerance)
            total_pixels = width * height
            percentage = (background_count / total_pixels) * 100

            print(
                f"Background exclusion applied: {background_count}/{total_pixels} pixels ({percentage:.1f}%) excluded as background"
            )
            print(
                f"Detected {len(sprites)} sprites in unknown spritesheet (excluding background): {file_path}"
            )
            return sprites

        except Exception as e:
            print(f"Error parsing with background exclusion: {str(e)}")
            return UnknownParser.parse_unknown_image(file_path)

    @staticmethod
    def _parse_excluding_multiple_backgrounds(image, file_path, background_colors, tolerance=30):
        """
        Parse sprites while excluding multiple background color pixels from sprite detection.

        Args:
            image (PIL.Image): The image to process
            file_path (str): Path to the image file (for naming)
            background_colors (list): List of RGB tuples of background colors to exclude
            tolerance (int): Color tolerance for background matching (0-255)

        Returns:
            list: List of sprite dictionaries with keys: name, x, y, width, height
        """
        try:
            if not background_colors:
                return UnknownParser.parse_unknown_image(file_path)

            if image.mode != "RGBA":
                image = image.convert("RGBA")

            img_array = np.array(image)
            height, width = img_array.shape[:2]

            r, g, b = img_array[:, :, 0], img_array[:, :, 1], img_array[:, :, 2]

            # Create combined mask for all background colors
            combined_background_mask = np.zeros((height, width), dtype=bool)

            total_excluded = 0
            for i, bg_color in enumerate(background_colors):
                bg_r, bg_g, bg_b = bg_color

                # Calculate color distance from background color
                color_distance = np.sqrt(
                    (r.astype(int) - bg_r) ** 2
                    + (g.astype(int) - bg_g) ** 2
                    + (b.astype(int) - bg_b) ** 2
                )

                # Create mask for pixels that match this background color within tolerance
                bg_mask = color_distance <= tolerance
                combined_background_mask |= bg_mask

                excluded_count = np.sum(bg_mask)
                total_excluded += excluded_count
                print(f"Background color {i + 1} {bg_color}: {excluded_count} pixels excluded")

            # Create mask for non-background pixels
            # This includes pixels that don't match any background color AND have some opacity
            alpha_channel = img_array[:, :, 3]
            non_background_mask = (~combined_background_mask) & (alpha_channel >= int(255 * 0.01))

            # Find connected regions in the non-background mask
            regions = UnknownParser._find_connected_regions(non_background_mask)

            sprites = []
            base_name = os.path.splitext(os.path.basename(file_path))[0]

            for i, region in enumerate(regions):
                if len(region) == 0:
                    continue

                # Calculate bounding box
                bbox = UnknownParser._get_bounding_box(region)
                x, y, width, height = bbox

                # Skip very small regions (likely noise)
                if width < 2 or height < 2:
                    continue

                # Apply precise cropping to remove remaining background/transparent areas
                cropped_x, cropped_y, cropped_width, cropped_height = UnknownParser._crop_sprite_precisely(
                    image, x, y, width, height
                )

                sprite_name = f"unsupported spritesheet - {base_name} - {i + 1:04d}"
                sprites.append(
                    {"name": sprite_name, "x": cropped_x, "y": cropped_y, "width": cropped_width, "height": cropped_height}
                )

            # Count how many pixels were excluded
            total_pixels = width * height
            percentage = (total_excluded / total_pixels) * 100

            print(
                f"Multi-background exclusion applied: {total_excluded}/{total_pixels} pixels ({percentage:.1f}%) excluded as background"
            )
            print(
                f"Detected {len(sprites)} sprites in unknown spritesheet (excluding multiple backgrounds): {file_path}"
            )

            return sprites

        except Exception as e:
            print(f"Error parsing with multi-background exclusion: {str(e)}")
            return UnknownParser.parse_unknown_image(file_path)

    @staticmethod
    def _crop_sprite_precisely(image, x, y, width, height, padding=1):
        """
        Crop a sprite more precisely by finding the actual content boundaries.
        
        Args:
            image (PIL.Image): The source image (should have transparent background)
            x, y, width, height (int): Initial bounding box
            padding (int): Extra pixels to add around the content
            
        Returns:
            tuple: (new_x, new_y, new_width, new_height) - optimized bounding box
        """
        try:
            # Extract the region of interest with some padding
            padded_x = max(0, x - padding)
            padded_y = max(0, y - padding) 
            padded_width = min(image.width - padded_x, width + 2 * padding)
            padded_height = min(image.height - padded_y, height + 2 * padding)
            
            # Crop the region from the image
            region = image.crop((padded_x, padded_y, padded_x + padded_width, padded_y + padded_height))
            
            # Convert to numpy array and find actual content bounds
            region_array = np.array(region)
            
            if region_array.shape[2] >= 4:  # Has alpha channel
                # Find pixels with significant alpha (not transparent)
                alpha_channel = region_array[:, :, 3]
                content_mask = alpha_channel > 10  # More than just barely visible
            else:
                # If no alpha channel, look for non-background colors
                # Assume white/near-white is background
                rgb_sum = np.sum(region_array[:, :, :3], axis=2)
                content_mask = rgb_sum < (255 * 3 * 0.95)  # Not near-white
            
            # Find the actual content boundaries
            content_rows = np.any(content_mask, axis=1)
            content_cols = np.any(content_mask, axis=0)
            
            if not np.any(content_rows) or not np.any(content_cols):
                # No content found, return original bounds
                return x, y, width, height
            
            # Find the tight bounding box around content
            content_y_indices = np.where(content_rows)[0]
            content_x_indices = np.where(content_cols)[0]
            
            content_top = content_y_indices[0]
            content_bottom = content_y_indices[-1]
            content_left = content_x_indices[0]
            content_right = content_x_indices[-1]
            
            # Calculate new bounds (relative to original image coordinates)
            new_x = padded_x + content_left
            new_y = padded_y + content_top
            new_width = content_right - content_left + 1
            new_height = content_bottom - content_top + 1
            
            # Add minimal padding back
            final_x = max(0, new_x - padding//2)
            final_y = max(0, new_y - padding//2)
            final_width = min(image.width - final_x, new_width + padding)
            final_height = min(image.height - final_y, new_height + padding)
            
            # Only use the new bounds if they're significantly smaller
            original_area = width * height
            new_area = final_width * final_height
            area_reduction = (original_area - new_area) / original_area
            
            if area_reduction > 0.1:  # At least 10% reduction to make it worthwhile
                print(f"  Cropped sprite: {width}x{height} -> {final_width}x{final_height} ({area_reduction:.1%} reduction)")
                return final_x, final_y, final_width, final_height
            else:
                return x, y, width, height
                
        except Exception as e:
            print(f"Error cropping sprite: {str(e)}")
            return x, y, width, height
