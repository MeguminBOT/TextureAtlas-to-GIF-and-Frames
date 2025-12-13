#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Test script to export a spritesheet with all combinations of formats, packers, and heuristics.

This script:
    1. Loads a Sparrow/Starling XML spritesheet
    2. Extracts all animations (just like the UI's "Load Atlas" button)
    3. Exports with every combination of:
       - Atlas format (starling-xml, json-hash, json-array, etc.)
       - Packer algorithm (maxrects, guillotine, skyline, shelf)
       - Heuristic (all available for each packer)

Output filenames follow the pattern:
    "{spritesheet_name}_{atlas_type}_{packer_type}_{heuristic_type}"

Usage:
    python test_all_combinations.py <path_to_xml> <path_to_png> [output_dir]

Example:
    python test_all_combinations.py GF_assets.xml GF_assets.png ./test_output
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from PIL import Image

from core.extractor.atlas_processor import AtlasProcessor
from core.generator.atlas_generator import AtlasGenerator, GeneratorOptions
from exporters.exporter_registry import ExporterRegistry
from packers import list_algorithms, get_heuristics_for_algorithm


def get_all_export_formats() -> List[Dict[str, str]]:
    """Get all available export formats.

    Returns:
        List of dicts with 'name' and 'extension' keys.
    """
    ExporterRegistry.initialize()
    formats = []
    for exporter_cls in ExporterRegistry._all_exporters:
        formats.append(
            {
                "name": getattr(exporter_cls, "FORMAT_NAME", "unknown"),
                "extension": getattr(exporter_cls, "FILE_EXTENSION", ".txt"),
                "display_name": getattr(
                    exporter_cls, "DISPLAY_NAME", exporter_cls.__name__
                ),
            }
        )
    return formats


def get_all_packers_and_heuristics() -> List[Dict[str, Any]]:
    """Get all available packers with their heuristics.

    Returns:
        List of dicts with 'name', 'display_name', and 'heuristics' keys.
    """
    algorithms = list_algorithms()
    result = []

    for algo in algorithms:
        algo_name = algo.get("name", "")
        if not algo_name or algo_name == "auto":
            continue

        heuristics = get_heuristics_for_algorithm(algo_name)
        result.append(
            {
                "name": algo_name,
                "display_name": algo.get("display_name", algo_name),
                "heuristics": heuristics if heuristics else [("default", "Default")],
            }
        )

    return result


def load_spritesheet(
    metadata_path: str,
    image_path: str,
) -> Tuple[Optional[Image.Image], List[Dict[str, Any]], Dict[str, List[str]]]:
    """Load a spritesheet and extract animation groups.

    Args:
        metadata_path: Path to the XML/JSON metadata file.
        image_path: Path to the atlas image.

    Returns:
        Tuple of (atlas_image, sprites_list, animation_groups).
        animation_groups maps animation names to lists of temp frame paths.
    """
    print(f"Loading spritesheet: {metadata_path}")

    # Use AtlasProcessor to parse the metadata
    processor = AtlasProcessor(
        atlas_path=image_path,
        metadata_path=metadata_path,
        parent_window=None,
    )

    if processor.atlas is None:
        print("ERROR: Failed to load atlas image")
        return None, [], {}

    if not processor.sprites:
        print("ERROR: No sprites found in metadata")
        return None, [], {}

    print(f"  Loaded {len(processor.sprites)} sprites")

    # Group sprites by animation name (strip trailing digits)
    from utils.utilities import Utilities

    animation_groups: Dict[str, List[Dict[str, Any]]] = {}

    for sprite in processor.sprites:
        name = sprite.get("name", "")
        # Strip trailing digits to get animation name
        anim_name = Utilities.strip_trailing_digits(name)
        if anim_name not in animation_groups:
            animation_groups[anim_name] = []
        animation_groups[anim_name].append(sprite)

    print(f"  Found {len(animation_groups)} animations")

    # Sort frames within each animation by their original name
    for anim_name in animation_groups:
        animation_groups[anim_name].sort(key=lambda s: s.get("name", ""))

    return processor.atlas, processor.sprites, animation_groups


def extract_frames_to_temp(
    atlas: Image.Image,
    animation_groups: Dict[str, List[Dict[str, Any]]],
    temp_dir: Path,
) -> Dict[str, List[str]]:
    """Extract individual frames from atlas to temporary directory.

    Args:
        atlas: The atlas image.
        animation_groups: Dict mapping animation names to sprite dicts.
        temp_dir: Directory to save extracted frames.

    Returns:
        Dict mapping animation names to lists of frame file paths.
    """
    temp_dir.mkdir(parents=True, exist_ok=True)
    frame_paths: Dict[str, List[str]] = {}

    for anim_name, sprites in animation_groups.items():
        frame_paths[anim_name] = []

        for sprite in sprites:
            x = sprite.get("x", 0)
            y = sprite.get("y", 0)
            width = sprite.get("width", 0)
            height = sprite.get("height", 0)
            name = sprite.get("name", f"{anim_name}_frame")

            # Crop the sprite from the atlas
            frame = atlas.crop((x, y, x + width, y + height))

            # Save to temp file
            frame_path = temp_dir / f"{name}.png"
            frame.save(str(frame_path), "PNG")
            frame_paths[anim_name].append(str(frame_path))

    return frame_paths


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use in filenames.

    Args:
        name: The string to sanitize.

    Returns:
        Sanitized string safe for filenames.
    """
    # Replace problematic characters
    for char in ["/", "\\", ":", "*", "?", '"', "<", ">", "|", " "]:
        name = name.replace(char, "_")
    return name


def run_all_combinations(
    metadata_path: str,
    image_path: str,
    output_dir: str,
) -> Dict[str, Any]:
    """Run all export combinations.

    Args:
        metadata_path: Path to the XML/JSON metadata file.
        image_path: Path to the atlas image.
        output_dir: Directory to save all outputs.

    Returns:
        Summary dict with results.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Create temp directory for extracted frames
    temp_dir = output_path / "_temp_frames"

    # Get base name from input file
    base_name = Path(metadata_path).stem

    # Load the spritesheet
    atlas, sprites, animation_groups = load_spritesheet(metadata_path, image_path)
    if atlas is None:
        return {"success": False, "error": "Failed to load spritesheet"}

    # Extract frames to temp directory
    print("\nExtracting frames to temporary directory...")
    frame_paths = extract_frames_to_temp(atlas, animation_groups, temp_dir)
    total_frames = sum(len(paths) for paths in frame_paths.values())
    print(f"  Extracted {total_frames} frames")

    # Get all formats, packers, and heuristics
    formats = get_all_export_formats()
    packers = get_all_packers_and_heuristics()

    print(f"\nAvailable export formats: {len(formats)}")
    for fmt in formats:
        print(f"  - {fmt['name']} ({fmt['extension']})")

    print(f"\nAvailable packers:")
    for packer in packers:
        heuristic_names = [h[0] for h in packer["heuristics"]]
        print(f"  - {packer['name']}: {len(packer['heuristics'])} heuristics")
        print(f"      {heuristic_names}")

    # Calculate total combinations
    total_heuristics = sum(len(p["heuristics"]) for p in packers)
    total_combinations = len(formats) * total_heuristics
    print(f"\nTotal combinations to generate: {total_combinations}")

    # Generate all combinations
    generator = AtlasGenerator()
    results = {
        "success": True,
        "total": total_combinations,
        "completed": 0,
        "failed": 0,
        "outputs": [],
    }

    start_time = time.time()
    combination_num = 0

    for fmt in formats:
        fmt_name = fmt["name"]

        for packer in packers:
            packer_name = packer["name"]

            for heuristic_key, heuristic_display in packer["heuristics"]:
                combination_num += 1

                # Build output filename
                safe_fmt = sanitize_filename(fmt_name)
                safe_packer = sanitize_filename(packer_name)
                safe_heuristic = sanitize_filename(heuristic_key)
                output_name = f"{base_name}_{safe_fmt}_{safe_packer}_{safe_heuristic}"
                output_file = output_path / output_name

                print(
                    f"\n[{combination_num}/{total_combinations}] "
                    f"Format: {fmt_name}, Packer: {packer_name}, Heuristic: {heuristic_key}"
                )

                # Create generator options
                options = GeneratorOptions(
                    algorithm=packer_name,
                    heuristic=heuristic_key,
                    export_format=fmt_name,
                    max_width=8192,
                    max_height=8192,
                    padding=2,
                    power_of_two=False,
                    force_square=False,
                    allow_rotation=False,
                )

                # Generate the atlas
                try:
                    result = generator.generate(
                        animation_groups=frame_paths,
                        output_path=str(output_file),
                        options=options,
                    )

                    if result.success:
                        results["completed"] += 1
                        results["outputs"].append(
                            {
                                "format": fmt_name,
                                "packer": packer_name,
                                "heuristic": heuristic_key,
                                "atlas_path": result.atlas_path,
                                "metadata_path": result.metadata_path,
                                "efficiency": result.efficiency,
                                "size": f"{result.atlas_width}x{result.atlas_height}",
                            }
                        )
                        print(
                            f"  ✓ Success: {result.atlas_width}x{result.atlas_height}, "
                            f"efficiency: {result.efficiency:.1%}"
                        )
                    else:
                        results["failed"] += 1
                        print(f"  ✗ Failed: {result.errors}")

                except Exception as e:
                    results["failed"] += 1
                    print(f"  ✗ Exception: {e}")

    elapsed = time.time() - start_time

    # Cleanup temp directory
    print("\nCleaning up temporary files...")
    import shutil

    if temp_dir.exists():
        shutil.rmtree(temp_dir)

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total combinations: {results['total']}")
    print(f"Completed: {results['completed']}")
    print(f"Failed: {results['failed']}")
    print(f"Time elapsed: {elapsed:.1f}s")
    print(f"Output directory: {output_path}")

    # Print efficiency comparison
    if results["outputs"]:
        print("\nTop 10 by efficiency:")
        sorted_outputs = sorted(
            results["outputs"],
            key=lambda x: x["efficiency"],
            reverse=True,
        )
        for i, out in enumerate(sorted_outputs[:10], 1):
            print(
                f"  {i}. {out['packer']}/{out['heuristic']}: "
                f"{out['efficiency']:.2%} ({out['size']})"
            )

    return results


def main():
    """Main entry point."""
    # Hardcoded test paths - modify these for quick testing
    DEFAULT_XML = r"R:/Coding/GitHub/TextureAtlas-TestSuite/BOYFRIEND.xml"
    DEFAULT_PNG = r"R:/Coding/GitHub/TextureAtlas-TestSuite/BOYFRIEND.png"
    DEFAULT_OUTPUT = r"R:/Coding/GitHub/TextureAtlas-TestSuite/BOYFRIEND_TEST_"

    if len(sys.argv) >= 3:
        metadata_path = sys.argv[1]
        image_path = sys.argv[2]
        output_dir = sys.argv[3] if len(sys.argv) > 3 else "./test_output"
    elif os.path.exists(DEFAULT_XML) and os.path.exists(DEFAULT_PNG):
        # Use hardcoded defaults if they exist
        print("Using hardcoded test paths:")
        print(f"  XML: {DEFAULT_XML}")
        print(f"  PNG: {DEFAULT_PNG}")
        print(f"  Output: {DEFAULT_OUTPUT}")
        print()
        metadata_path = DEFAULT_XML
        image_path = DEFAULT_PNG
        output_dir = DEFAULT_OUTPUT
    else:
        print(
            "Usage: python test_all_combinations.py <xml_path> <png_path> [output_dir]"
        )
        print()
        print("Example:")
        print(
            "  python test_all_combinations.py BOYFRIEND.xml BOYFRIEND.png ./test_output"
        )
        sys.exit(1)

    # Validate inputs
    if not os.path.exists(metadata_path):
        print(f"ERROR: Metadata file not found: {metadata_path}")
        sys.exit(1)

    if not os.path.exists(image_path):
        print(f"ERROR: Image file not found: {image_path}")
        sys.exit(1)

    # Run all combinations
    results = run_all_combinations(metadata_path, image_path, output_dir)

    if not results["success"]:
        print(f"ERROR: {results.get('error', 'Unknown error')}")
        sys.exit(1)

    sys.exit(0 if results["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
