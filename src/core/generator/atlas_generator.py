#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Atlas generator that combines packing and exporting.

This module provides the main generation pipeline:
    1. Load input images
    2. Pack them using the selected algorithm
    3. Composite the atlas image
    4. Export metadata in the selected format

Usage:
    from core.generator.atlas_generator import AtlasGenerator, GeneratorOptions

    generator = AtlasGenerator()
    result = generator.generate(
        frames={"anim1": ["frame1.png", "frame2.png"]},
        output_path="/path/to/atlas",
        options=GeneratorOptions(algorithm="maxrects"),
    )
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from PIL import Image

from packers import (
    ExpandStrategy,
    FrameInput,
    PackedFrame,
    PackerOptions,
    PackerResult,
    get_packer,
    list_algorithms,
)
from exporters.exporter_registry import ExporterRegistry
from exporters.exporter_types import GeneratorMetadata
from version import APP_VERSION


@dataclass
class GeneratorOptions:
    """Options for atlas generation.

    Attributes:
        algorithm: Packing algorithm name (e.g., 'maxrects', 'guillotine').
        heuristic: Algorithm-specific heuristic key.
        max_width: Maximum atlas width.
        max_height: Maximum atlas height.
        padding: Pixels between sprites.
        border_padding: Pixels around atlas edge.
        power_of_two: Force power-of-two dimensions.
        force_square: Force square atlas.
        allow_rotation: Allow 90° rotation for tighter packing.
        allow_flip: Allow sprite flipping (limited format support).
        expand_strategy: How to grow atlas when sprites don't fit.
        image_format: Output image format (png, webp, etc.).
        export_format: Metadata format key (e.g., 'starling-xml', 'json-hash').
        compression_settings: Format-specific compression options dict.
    """

    algorithm: str = "maxrects"
    heuristic: Optional[str] = None
    max_width: int = 4096
    max_height: int = 4096
    padding: int = 2
    border_padding: int = 0
    power_of_two: bool = False
    force_square: bool = False
    allow_rotation: bool = False
    allow_flip: bool = False
    expand_strategy: str = "short_side"
    image_format: str = "png"
    export_format: str = "starling-xml"
    compression_settings: Optional[Dict[str, Any]] = None

    def to_packer_options(self) -> PackerOptions:
        """Convert to PackerOptions for the packer system."""
        strategy_map = {
            "disabled": ExpandStrategy.DISABLED,
            "width_first": ExpandStrategy.WIDTH_FIRST,
            "height_first": ExpandStrategy.HEIGHT_FIRST,
            "short_side": ExpandStrategy.SHORT_SIDE,
            "long_side": ExpandStrategy.LONG_SIDE,
            "both": ExpandStrategy.BOTH,
        }
        expand = strategy_map.get(self.expand_strategy, ExpandStrategy.SHORT_SIDE)

        return PackerOptions(
            max_width=self.max_width,
            max_height=self.max_height,
            padding=self.padding,
            border_padding=self.border_padding,
            power_of_two=self.power_of_two,
            force_square=self.force_square,
            allow_rotation=self.allow_rotation,
            allow_flip=self.allow_flip,
            expand_strategy=expand,
            sort_by_max_side=True,
        )


@dataclass
class GeneratorResult:
    """Result of atlas generation.

    Attributes:
        success: Whether generation succeeded.
        atlas_path: Path to the generated atlas image.
        metadata_path: Path to the generated metadata file.
        atlas_width: Final atlas width.
        atlas_height: Final atlas height.
        frame_count: Number of packed frames.
        efficiency: Packing efficiency (0.0-1.0).
        errors: List of error messages.
        warnings: List of warning messages.
    """

    success: bool = False
    atlas_path: str = ""
    metadata_path: str = ""
    atlas_width: int = 0
    atlas_height: int = 0
    frame_count: int = 0
    efficiency: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for compatibility with existing UI."""
        return {
            "success": self.success,
            "atlas_path": self.atlas_path,
            "metadata_files": [self.metadata_path] if self.metadata_path else [],
            "atlas_size": (self.atlas_width, self.atlas_height),
            "frames_count": self.frame_count,
            "efficiency": self.efficiency * 100,  # Convert to percentage
            "errors": self.errors,
            "warnings": self.warnings,
        }


class AtlasGenerator:
    """Main atlas generation pipeline.

    Orchestrates loading images, packing, compositing, and exporting.
    """

    def __init__(self) -> None:
        self._progress_callback: Optional[Callable[[int, int, str], None]] = None

    def set_progress_callback(self, callback: Callable[[int, int, str], None]) -> None:
        """Set callback for progress updates.

        Args:
            callback: Function(current, total, message) called during generation.
        """
        self._progress_callback = callback

    def _emit_progress(self, current: int, total: int, message: str) -> None:
        """Emit progress update if callback is set."""
        if self._progress_callback:
            self._progress_callback(current, total, message)

    @staticmethod
    def _compute_image_hash(img: Image.Image) -> str:
        """Compute a hash for image content comparison.

        Uses a fast hash of raw pixel data. Images that are 100% identical
        (same dimensions, mode, and pixels) will produce the same hash.

        Args:
            img: PIL Image to hash.

        Returns:
            Hex digest string uniquely identifying the image content.
        """
        # Ensure consistent mode for comparison
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        # Get raw pixel data as bytes
        pixel_bytes = img.tobytes()

        # Include dimensions in hash to avoid collisions from resized images
        header = f"{img.width}x{img.height}:{img.mode}:".encode("utf-8")

        # Use SHA-256 for a good balance of speed and collision resistance
        hasher = hashlib.sha256()
        hasher.update(header)
        hasher.update(pixel_bytes)

        return hasher.hexdigest()

    def generate(
        self,
        animation_groups: Dict[str, List[str]],
        output_path: str,
        options: Optional[GeneratorOptions] = None,
    ) -> GeneratorResult:
        """Generate an atlas from animation groups.

        Args:
            animation_groups: Dict mapping animation names to lists of frame paths.
            output_path: Base output path (without extension).
            options: Generation options.

        Returns:
            GeneratorResult with paths, dimensions, and status.
        """
        options = options or GeneratorOptions()
        result = GeneratorResult()

        try:
            # Step 1: Load all images and detect duplicates
            self._emit_progress(0, 4, "Loading images...")
            load_result = self._load_images_with_dedup(animation_groups)
            unique_frames = load_result["unique_frames"]
            images = load_result["images"]
            duplicate_map = load_result["duplicate_map"]
            all_frame_data = load_result["all_frame_data"]

            if not unique_frames:
                result.errors.append("No valid images found to pack")
                return result

            # Report duplicate detection stats
            duplicate_count = len(all_frame_data) - len(unique_frames)
            if duplicate_count > 0:
                result.warnings.append(
                    f"Detected {duplicate_count} duplicate frame(s), "
                    f"packing {len(unique_frames)} unique frames"
                )

            # Step 2: Pack only unique frames
            self._emit_progress(1, 4, f"Packing with {options.algorithm}...")
            pack_result = self._pack_frames(unique_frames, options)

            if not pack_result.success:
                for err in pack_result.errors:
                    result.errors.append(err.message)
                return result

            # Step 3: Composite atlas image (only unique frames)
            self._emit_progress(2, 4, "Compositing atlas...")
            atlas_image = self._composite_atlas(
                pack_result.packed_frames,
                images,
                pack_result.atlas_width,
                pack_result.atlas_height,
                options.padding,
            )

            # Step 4: Save atlas and metadata
            # Expand packed_frames to include duplicates pointing to same position
            expanded_packed_frames = self._expand_packed_frames_with_duplicates(
                pack_result.packed_frames,
                duplicate_map,
                all_frame_data,
            )

            self._emit_progress(3, 4, "Saving files...")
            atlas_path, metadata_path = self._save_output(
                atlas_image,
                pack_result,
                output_path,
                options,
                expanded_packed_frames,
            )

            # Build result
            result.success = True
            result.atlas_path = atlas_path
            result.metadata_path = metadata_path
            result.atlas_width = pack_result.atlas_width
            result.atlas_height = pack_result.atlas_height
            result.frame_count = len(
                all_frame_data
            )  # Total frames including duplicates
            result.efficiency = pack_result.efficiency

            self._emit_progress(4, 4, "Complete!")

        except Exception as e:
            result.errors.append(f"Generation failed: {e}")

        return result

    def _load_images_with_dedup(
        self,
        animation_groups: Dict[str, List[str]],
    ) -> Dict[str, Any]:
        """Load images from animation groups with duplicate detection.

        Detects images that are 100% identical and deduplicates them so
        only unique images are packed. Duplicates are mapped to their
        canonical (first-seen) version.

        Returns:
            Dict with:
                - unique_frames: List[FrameInput] for unique images only
                - images: Dict[str, Image] mapping unique IDs to images
                - duplicate_map: Dict[str, str] mapping duplicate IDs to canonical IDs
                - all_frame_data: List[FrameInput] for all frames (for metadata)
        """
        all_frame_data: List[FrameInput] = []
        unique_frames: List[FrameInput] = []
        images: Dict[str, Image.Image] = {}

        # hash -> first frame ID that had this hash (the canonical version)
        hash_to_canonical: Dict[str, str] = {}
        # duplicate frame ID -> canonical frame ID
        duplicate_map: Dict[str, str] = {}

        for anim_name, frame_paths in animation_groups.items():
            for idx, path in enumerate(frame_paths):
                try:
                    img = Image.open(path)
                    if img.mode != "RGBA":
                        img = img.convert("RGBA")

                    # Generate unique ID for this frame
                    frame_id = f"{anim_name}_{idx:04d}"
                    path_obj = Path(path)

                    # Create frame input with metadata
                    frame_input = FrameInput(
                        id=frame_id,
                        width=img.width,
                        height=img.height,
                        user_data={
                            "path": path,
                            "name": path_obj.stem,
                            "animation": anim_name,
                            "index": idx,
                        },
                    )
                    all_frame_data.append(frame_input)

                    # Compute hash and check for duplicates
                    img_hash = self._compute_image_hash(img)

                    if img_hash in hash_to_canonical:
                        # This is a duplicate - map to canonical
                        canonical_id = hash_to_canonical[img_hash]
                        duplicate_map[frame_id] = canonical_id
                        # Don't store the duplicate image
                    else:
                        # First occurrence - this is the canonical version
                        hash_to_canonical[img_hash] = frame_id
                        unique_frames.append(frame_input)
                        images[frame_id] = img

                except Exception as e:
                    print(f"Warning: Failed to load {path}: {e}")

        return {
            "unique_frames": unique_frames,
            "images": images,
            "duplicate_map": duplicate_map,
            "all_frame_data": all_frame_data,
        }

    def _expand_packed_frames_with_duplicates(
        self,
        packed_frames: List[PackedFrame],
        duplicate_map: Dict[str, str],
        all_frame_data: List[FrameInput],
    ) -> List[PackedFrame]:
        """Expand packed frames list to include duplicates.

        Creates PackedFrame entries for duplicate frames that point to
        the same atlas position as their canonical version.

        Args:
            packed_frames: Packed frames for unique images only.
            duplicate_map: Maps duplicate frame IDs to canonical frame IDs.
            all_frame_data: All frame inputs including duplicates.

        Returns:
            List of PackedFrame for all frames (unique + duplicates).
        """
        if not duplicate_map:
            return packed_frames  # No duplicates, return as-is

        # Build lookup from canonical ID to its packed frame
        packed_lookup: Dict[str, PackedFrame] = {pf.id: pf for pf in packed_frames}

        expanded: List[PackedFrame] = []

        for frame in all_frame_data:
            if frame.id in duplicate_map:
                # This is a duplicate - use the canonical's position
                canonical_id = duplicate_map[frame.id]
                canonical_packed = packed_lookup.get(canonical_id)
                if canonical_packed:
                    # Create a new PackedFrame for the duplicate
                    # pointing to the same atlas position
                    duplicate_packed = PackedFrame(
                        frame=frame,
                        x=canonical_packed.x,
                        y=canonical_packed.y,
                        rotated=canonical_packed.rotated,
                        flipped_x=canonical_packed.flipped_x,
                        flipped_y=canonical_packed.flipped_y,
                    )
                    expanded.append(duplicate_packed)
            else:
                # This is a unique frame - use its own packed position
                packed = packed_lookup.get(frame.id)
                if packed:
                    expanded.append(packed)

        return expanded

    def _load_images(
        self,
        animation_groups: Dict[str, List[str]],
    ) -> Tuple[List[FrameInput], Dict[str, Image.Image]]:
        """Load images from animation groups.

        Returns:
            Tuple of (list of FrameInput, dict of id->Image).
        """
        frame_data: List[FrameInput] = []
        images: Dict[str, Image.Image] = {}

        for anim_name, frame_paths in animation_groups.items():
            for idx, path in enumerate(frame_paths):
                try:
                    img = Image.open(path)
                    if img.mode != "RGBA":
                        img = img.convert("RGBA")

                    # Generate unique ID for this frame
                    frame_id = f"{anim_name}_{idx:04d}"
                    path_obj = Path(path)

                    # Store with original filename as user_data for metadata
                    frame_input = FrameInput(
                        id=frame_id,
                        width=img.width,
                        height=img.height,
                        user_data={
                            "path": path,
                            "name": path_obj.stem,
                            "animation": anim_name,
                            "index": idx,
                        },
                    )
                    frame_data.append(frame_input)
                    images[frame_id] = img

                except Exception as e:
                    print(f"Warning: Failed to load {path}: {e}")

        return frame_data, images

    def _pack_frames(
        self,
        frames: List[FrameInput],
        options: GeneratorOptions,
    ) -> PackerResult:
        """Pack frames using the selected algorithm.

        If algorithm is "auto", tries all available algorithms with their
        best heuristics and returns the result with the best packing efficiency.

        If heuristic is "auto" or None, tries all available heuristics
        and returns the result with the best packing efficiency.
        """
        packer_options = options.to_packer_options()

        # Get packer instance
        algorithm = options.algorithm

        # True auto mode: try all algorithms and pick the best
        if algorithm == "auto":
            return self._pack_with_best_algorithm(
                frames, packer_options, options.heuristic
            )

        # Check if we should auto-select the best heuristic
        if options.heuristic == "auto" or options.heuristic is None:
            return self._pack_with_best_heuristic(frames, algorithm, packer_options)

        # Use specified heuristic
        packer = get_packer(algorithm, packer_options)
        packer.set_heuristic(options.heuristic)
        return packer.pack(frames)

    def _pack_with_best_algorithm(
        self,
        frames: List[FrameInput],
        options: PackerOptions,
        heuristic_hint: Optional[str] = None,
    ) -> PackerResult:
        """Try all algorithms and return the best result.

        For each algorithm, if heuristic_hint is "auto" or None, tries all
        heuristics. Otherwise uses the specified heuristic if supported.

        "Best" is determined by:
        1. Successful packing (all frames fit)
        2. Smallest atlas area
        3. Highest packing efficiency

        Args:
            frames: Frames to pack.
            options: Packer options.
            heuristic_hint: Optional heuristic to prefer, or "auto"/None for best.

        Returns:
            The PackerResult with the best efficiency across all algorithms.
        """
        algorithms = list_algorithms()

        best_result: Optional[PackerResult] = None
        best_score: float = float("inf")  # Lower is better (area)

        auto_heuristic = heuristic_hint == "auto" or heuristic_hint is None

        for algo_info in algorithms:
            algo_name = algo_info.get("name", "")
            if not algo_name or algo_name == "auto":
                continue  # Skip meta-algorithm placeholder

            try:
                if auto_heuristic:
                    # Try all heuristics for this algorithm
                    result = self._pack_with_best_heuristic(frames, algo_name, options)
                else:
                    # Use specified heuristic
                    packer = get_packer(algo_name, options)
                    packer.set_heuristic(heuristic_hint)
                    result = packer.pack(frames)

                if not result.success:
                    continue

                # Score by area (smaller is better), tie-break by efficiency
                score = result.atlas_width * result.atlas_height
                # Subtract efficiency to prefer higher efficiency at same area
                score -= result.efficiency * 0.01

                if best_result is None or score < best_score:
                    best_result = result
                    best_score = score

            except Exception as e:
                print(f"Warning: Algorithm '{algo_name}' failed: {e}")
                continue

        if best_result is None:
            # All algorithms failed, fall back to maxrects default
            packer = get_packer("maxrects", options)
            return packer.pack(frames)

        return best_result

    def _pack_with_best_heuristic(
        self,
        frames: List[FrameInput],
        algorithm: str,
        options: PackerOptions,
    ) -> PackerResult:
        """Try all heuristics for an algorithm and return the best result.

        "Best" is determined by:
        1. Successful packing (all frames fit)
        2. Smallest atlas area
        3. Highest packing efficiency

        Args:
            frames: Frames to pack.
            algorithm: Algorithm name.
            options: Packer options.

        Returns:
            The PackerResult with the best efficiency.
        """
        from packers import get_heuristics_for_algorithm

        heuristics = get_heuristics_for_algorithm(algorithm)

        if not heuristics:
            # No heuristics available (e.g., SimplePacker), just pack directly
            packer = get_packer(algorithm, options)
            return packer.pack(frames)

        best_result: Optional[PackerResult] = None
        best_score: float = float("inf")  # Lower is better (area)

        for heuristic_key, _ in heuristics:
            try:
                # Create fresh packer for each attempt
                packer = get_packer(algorithm, options)
                packer.set_heuristic(heuristic_key)
                result = packer.pack(frames)

                if not result.success:
                    continue

                # Score by area (smaller is better), tie-break by efficiency
                score = result.atlas_width * result.atlas_height
                # Subtract efficiency to prefer higher efficiency at same area
                score -= result.efficiency * 0.01

                if best_result is None or score < best_score:
                    best_result = result
                    best_score = score

            except Exception as e:
                print(f"Warning: Heuristic '{heuristic_key}' failed: {e}")
                continue

        if best_result is None:
            # All heuristics failed, try with default
            packer = get_packer(algorithm, options)
            return packer.pack(frames)

        return best_result

    def _composite_atlas(
        self,
        packed_frames: List[PackedFrame],
        images: Dict[str, Image.Image],
        width: int,
        height: int,
        padding: int,
    ) -> Image.Image:
        """Composite packed frames onto atlas image."""
        atlas = Image.new("RGBA", (width, height), (0, 0, 0, 0))

        for packed in packed_frames:
            img = images.get(packed.id)
            if img is None:
                continue

            # Handle rotation if needed
            if packed.rotated:
                img = img.transpose(Image.Transpose.ROTATE_270)

            # Paste onto atlas
            atlas.paste(img, (packed.x, packed.y), img)

        return atlas

    def _build_save_kwargs(self, options: GeneratorOptions) -> Dict[str, Any]:
        """Build PIL save kwargs from compression settings.

        Uses compression_settings from options if provided, otherwise
        falls back to sensible defaults for each format.

        Args:
            options: Generator options containing format and compression settings.

        Returns:
            Dict of kwargs to pass to PIL's Image.save().
        """
        fmt = options.image_format.lower()
        user_settings = options.compression_settings or {}
        save_kwargs: Dict[str, Any] = {}

        if fmt == "png":
            # PNG compression settings
            save_kwargs["compress_level"] = user_settings.get("compress_level", 9)
            save_kwargs["optimize"] = user_settings.get("optimize", True)

        elif fmt == "webp":
            # WebP compression settings
            lossless = user_settings.get("lossless", True)
            save_kwargs["lossless"] = lossless
            if lossless:
                # For lossless, quality affects compression effort (0-100)
                save_kwargs["quality"] = user_settings.get("quality", 90)
            else:
                # For lossy, quality is the actual quality setting
                save_kwargs["quality"] = user_settings.get("quality", 85)
            if "method" in user_settings:
                save_kwargs["method"] = user_settings["method"]

        elif fmt in ("jpg", "jpeg"):
            # JPEG compression settings
            save_kwargs["quality"] = user_settings.get("quality", 95)
            save_kwargs["optimize"] = user_settings.get("optimize", True)
            if "progressive" in user_settings:
                save_kwargs["progressive"] = user_settings["progressive"]
            if "subsampling" in user_settings:
                save_kwargs["subsampling"] = user_settings["subsampling"]

        elif fmt == "tiff":
            # TIFF compression settings
            compression = user_settings.get("compression", "tiff_lzw")
            save_kwargs["compression"] = compression

        elif fmt == "avif":
            # AVIF compression settings (requires pillow-avif-plugin)
            save_kwargs["quality"] = user_settings.get("quality", 80)
            if "speed" in user_settings:
                save_kwargs["speed"] = user_settings["speed"]

        elif fmt == "bmp":
            # BMP has no compression options
            pass

        elif fmt == "tga":
            # TGA compression
            if user_settings.get("rle", False):
                save_kwargs["rle"] = True

        elif fmt == "dds":
            # DDS format (if supported)
            pass

        return save_kwargs

    def _save_output(
        self,
        atlas_image: Image.Image,
        pack_result: PackerResult,
        output_path: str,
        options: GeneratorOptions,
        expanded_packed_frames: Optional[List[PackedFrame]] = None,
    ) -> Tuple[str, str]:
        """Save atlas image and metadata.

        Args:
            atlas_image: Composited atlas image.
            pack_result: Result from packer.
            output_path: Base output path without extension.
            options: Generator options.
            expanded_packed_frames: Optional list of all frames including duplicates.
                                    If None, uses pack_result.packed_frames.

        Returns:
            Tuple of (atlas_path, metadata_path).
        """
        output_base = Path(output_path)
        output_base.parent.mkdir(parents=True, exist_ok=True)

        # Save atlas image
        image_ext = f".{options.image_format.lower()}"
        atlas_path = output_base.with_suffix(image_ext)

        # Build save kwargs from compression settings or use defaults
        save_kwargs = self._build_save_kwargs(options)

        atlas_image.save(str(atlas_path), **save_kwargs)

        # Generate metadata using expanded frames if provided
        frames_for_metadata = expanded_packed_frames or pack_result.packed_frames

        # Create generator metadata for watermarking
        # Use pack_result values which contain actual algorithm/heuristic used
        # (important when "auto" was selected - these show what was actually chosen)
        algorithm_name = pack_result.algorithm_name or options.algorithm or "Unknown"
        heuristic_name = pack_result.heuristic_name or options.heuristic or "Unknown"

        # Format names nicely (e.g., "best_short_side_fit" -> "Best Short Side Fit")
        algorithm_name = algorithm_name.replace("_", " ").title()
        heuristic_name = heuristic_name.replace("_", " ").title()

        generator_metadata = GeneratorMetadata(
            app_version=APP_VERSION,
            packer=algorithm_name,
            heuristic=heuristic_name,
            efficiency=pack_result.efficiency * 100,  # Convert to percentage
        )

        metadata_path = self._save_metadata(
            frames_for_metadata,
            pack_result.atlas_width,
            pack_result.atlas_height,
            output_base,
            atlas_path.name,
            options.export_format,
            generator_metadata,
        )

        return str(atlas_path), metadata_path

    def _save_metadata(
        self,
        packed_frames: List[PackedFrame],
        atlas_width: int,
        atlas_height: int,
        output_base: Path,
        image_name: str,
        export_format: str,
        generator_metadata: Optional[GeneratorMetadata] = None,
    ) -> str:
        """Generate and save metadata file.

        Args:
            packed_frames: List of packed frames (including duplicates).
            atlas_width: Width of the atlas image.
            atlas_height: Height of the atlas image.
            output_base: Base path for output files.
            image_name: Name of the atlas image file.
            export_format: Format key for the exporter.
            generator_metadata: Optional metadata for watermarking comments.

        Returns:
            Path to the metadata file.
        """
        # Convert PackedFrame to the format expected by exporters
        sprites_data = []
        for packed in packed_frames:
            user_data = packed.frame.user_data or {}
            sprite = {
                "name": user_data.get("name", packed.id),
                "x": packed.x,
                "y": packed.y,
                "width": packed.width,
                "height": packed.height,
                "source_width": packed.source_width,
                "source_height": packed.source_height,
                "rotated": packed.rotated,
                "animation": user_data.get("animation", ""),
                "index": user_data.get("index", 0),
            }
            sprites_data.append(sprite)

        # Get exporter and generate metadata
        try:
            # Initialize the registry if needed
            ExporterRegistry.initialize()

            exporter_cls = ExporterRegistry.get_exporter(export_format)
            if not exporter_cls:
                print(f"Warning: No exporter found for format: {export_format}")
                return ""

            exporter = exporter_cls()
            metadata_ext = exporter.FILE_EXTENSION
            metadata_path = output_base.with_suffix(metadata_ext)

            # Build metadata content
            # Convert to PackedSprite format expected by exporters
            from exporters.exporter_types import PackedSprite

            packed_sprites = []
            for sprite in sprites_data:
                # Create SpriteData-like dict
                sprite_data = {
                    "name": sprite["name"],
                    "x": sprite["x"],
                    "y": sprite["y"],
                    "width": sprite["source_width"],
                    "height": sprite["source_height"],
                }
                packed_sprite = PackedSprite(
                    sprite=sprite_data,
                    atlas_x=sprite["x"],
                    atlas_y=sprite["y"],
                    rotated=sprite["rotated"],
                )
                packed_sprites.append(packed_sprite)

            metadata = exporter.build_metadata(
                packed_sprites,
                atlas_width,
                atlas_height,
                image_name,
                generator_metadata,
            )

            # Save metadata
            if isinstance(metadata, bytes):
                with open(metadata_path, "wb") as f:
                    f.write(metadata)
            else:
                with open(metadata_path, "w", encoding="utf-8") as f:
                    f.write(metadata)

            return str(metadata_path)

        except Exception as e:
            print(f"Warning: Failed to save metadata: {e}")
            return ""


def get_available_algorithms() -> List[Dict[str, Any]]:
    """Get list of available packing algorithms for UI.

    Returns:
        List of dicts with 'name', 'display_name', 'heuristics' keys.
    """
    return list_algorithms()


__all__ = [
    "AtlasGenerator",
    "GeneratorOptions",
    "GeneratorResult",
    "get_available_algorithms",
]
