# API Reference

Technical reference for developers integrating TextureAtlas Toolbox extraction capabilities into
other applications or extending its functionality.

This document focuses on the public interfaces of the extraction pipeline. For implementation
details and contribution guidelines, see [developer-docs.md](developer-docs.md).

---

# Table of Contents

- Extractor Tool
  - [Extraction Pipeline](#extraction-pipeline)
    - [Extractor](#extractor)
    - [AtlasProcessor](#atlasprocessor)
    - [SpriteProcessor](#spriteprocessor)
    - [AnimationProcessor](#animationprocessor)
    - [FramePipeline](#framepipeline)
    - [FrameSelector](#frameselector)
    - [FrameExporter](#frameexporter)
    - [AnimationExporter](#animationexporter)
  - [Parsers](#parsers)
    - [ParserRegistry](#parserregistry)
    - [BaseParser](#baseparser)
    - [Parser Types](#parser-types)
    - [Supported Formats](#supported-formats)
  - [Spritemap Module](#spritemap-module)
    - [AdobeSpritemapRenderer](#adobespritemaprenderer)
    - [SpriteAtlas](#spriteatlas)
  - [Unknown Spritesheet Handling](#unknown-spritesheet-handling)
    - [UnknownParser](#unknownparser)
    - [UnknownSpritesheetHandler](#unknownspritesheethandler)
  - [Extraction Utilities](#extraction-utilities)
    - [SettingsManager](#settingsmanager)
    - [Image Utilities](#image-utilities)
    - [Frame Duration Utilities](#frame-duration-utilities)
  - [UI Bindings](#ui-bindings)
    - [Signal-Based Progress Reporting](#signal-based-progress-reporting)
    - [Integrating with Custom UI Frameworks](#integrating-with-custom-ui-frameworks)
- Generator Tool
  - [Generation Pipeline](#generation-pipeline)
    - [AtlasGenerator](#atlasgenerator)
    - [GeneratorOptions](#generatoroptions)
    - [GeneratorResult](#generatorresult)
  - [Packers](#packers)
    - [PackerRegistry](#packerregistry)
    - [BasePacker](#basepacker)
    - [Packer Types](#packer-types)
    - [Available Algorithms](#available-algorithms)
  - [Exporters](#exporters)
    - [ExporterRegistry](#exporterregistry)
    - [BaseExporter](#baseexporter)
    - [Exporter Types](#exporter-types)
    - [Supported Export Formats](#supported-export-formats)
- Editor Tool
  - [Editor Composite](#editor-composite)
    - [build_editor_composite_frames](#build_editor_composite_frames)
    - [clone_animation_map](#clone_animation_map)
    - [Type Aliases](#type-aliases)
- General
  - [Utility Classes](#utility-classes)
  - [Configuration](#configuration)
  - [Error Handling](#error-handling)

---

# Extraction Pipeline

The extraction pipeline converts texture atlases into individual frames and animations. The main
entry point is `Extractor`, which coordinates multiple worker threads to process batches of
spritesheets in parallel.

## Extractor

Orchestrates parallel spritesheet parsing and animation export. Manages worker threads, dispatches
files from a queue, aggregates statistics, and supports pause/cancel semantics.

```python
from core.extractor.extractor import Extractor

extractor = Extractor(
    progress_callback,      # Callable[[int, int, str], None]
    current_version,        # str - version string for metadata
    settings_manager,       # SettingsManager instance
    app_config=None,        # Optional AppConfig for resource limits
    statistics_callback=None,
    cancel_event=None,
    error_prompt_callback=None,
)
```

### Key Methods

| Method | Description |
|--------|-------------|
| `process_directory(input_dir, output_dir, ...)` | Process a batch of spritesheets using a worker pool. |
| `cancel()` | Signal cancellation to all workers. |
| `pause()` / `resume()` | Pause or resume processing. |

#### Callbacks

- **progress_callback**: Receives `(current_file_index, total_files, status_message)`.
- **statistics_callback**: Receives `(frames_generated, anims_generated, sprites_failed)`.
- **error_prompt_callback**: Receives `(error_message, exception)`, returns `True` to continue.

---
<br>

## AtlasProcessor

Loads a texture atlas image and parses its metadata. Uses the unified `ParserRegistry` for format
detection, falling back to `UnknownParser` for images without metadata.

```python
from core.extractor.atlas_processor import AtlasProcessor

processor = AtlasProcessor(
    atlas_path,             # str - path to atlas image
    metadata_path,          # Optional[str] - path to metadata file
    parent_window=None,     # Optional widget for dialogs
)
atlas_image = processor.atlas       # PIL.Image or None
sprites = processor.sprites         # List[dict] - sprite metadata
```

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `atlas` | `PIL.Image` | Loaded atlas image, or `None` on error. |
| `sprites` | `List[dict]` | Parsed sprite metadata dicts. |
| `parse_result` | `ParseResult` | Full parse result with warnings/errors. |

### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `open_atlas_and_parse_metadata()` | `(Image, List[dict])` | Load atlas and parse metadata. |
| `has_parse_errors()` | `bool` | Check if parsing produced errors. |

---
<br>

## SpriteProcessor

Extracts individual sprites from an atlas image and groups them into animation sequences.

```python
from core.extractor.sprite_processor import SpriteProcessor

processor = SpriteProcessor(atlas_image, sprites_list)
animations = processor.process_sprites()
# animations: Dict[str, List[Tuple[str, np.ndarray, dict]]]
```

### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `process_sprites()` | `Dict[str, List[FrameTuple]]` | Group all sprites into animations. |
| `process_specific_animation(name)` | `Dict[str, List[FrameTuple]]` | Extract a single animation by name. |

**FrameTuple**: `Tuple[name: str, image: np.ndarray, metadata: dict]`

---
<br>

## AnimationProcessor

Coordinates frame and animation export. Applies alignment overrides, injects editor-defined
composite animations, and delegates to `FrameExporter` and `AnimationExporter`.

```python
from core.extractor.animation_processor import AnimationProcessor

processor = AnimationProcessor(
    animations,             # Dict[str, List[FrameTuple]]
    atlas_path,             # str
    output_dir,             # str
    settings_manager,       # SettingsManager
    current_version,        # str
    spritesheet_label=None, # Optional display name
)
frames, anims = processor.process_animations()
```

### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `process_animations(is_unknown=False)` | `(int, int)` | Export all animations; returns counts. |
| `scale_image(image, factor)` | `PIL.Image` | Scale image (negative flips horizontally). |

---
<br>

## FramePipeline

Normalizes input frames (sorting, RGBA conversion) and builds export-ready context objects.

```python
from core.extractor.frame_pipeline import FramePipeline, AnimationContext

pipeline = FramePipeline()
context = pipeline.build_context(
    spritesheet_name,
    animation_name,
    image_tuples,
    settings,
)
```

### AnimationContext (dataclass)

Immutable container describing a prepared set of frames for export.

| Attribute | Type | Description |
|-----------|------|-------------|
| `spritesheet_name` | `str` | Source spritesheet identifier. |
| `animation_name` | `str` | Animation sequence name. |
| `settings` | `dict` | Export settings. |
| `frames` | `List[FrameTuple]` | Normalized frame tuples. |
| `kept_indices` | `List[int]` | Indices of frames to export. |
| `single_frame` | `bool` | `True` if all frames are identical. |

| Method | Description |
|--------|-------------|
| `with_frames(frames)` | Return copy with replaced frame list. |
| `iter_selected_frames()` | Yield frames at `kept_indices`. |
| `selected_frames` | Property returning list of selected frames. |

---
<br>

## FrameSelector

Static utilities for selecting which frames to export based on selection strategies.

```python
from core.extractor.frame_selector import FrameSelector

is_single = FrameSelector.is_single_frame(image_tuples)
kept = FrameSelector.get_kept_frames(settings, is_single, image_tuples)
indices = FrameSelector.get_kept_frame_indices(kept, image_tuples)
```

### Selection Strategies

| Value | Behavior |
|-------|----------|
| `"all"` | Keep every frame. |
| `"first"` | Keep only the first frame. |
| `"last"` | Keep only the last frame. |
| `"first_last"` | Keep first and last frames. |
| `"no_duplicates"` | Remove visually identical consecutive frames. |
| `"0,2,4"` / `"0-5"` | Explicit indices or ranges. |

---
<br>

## FrameExporter

Exports individual animation frames as image files (PNG, WebP, AVIF, etc.).

```python
from core.extractor.frame_exporter import FrameExporter

exporter = FrameExporter(output_dir, current_version, scale_image_func)
count = exporter.save_frames(
    image_tuples,
    kept_frame_indices,
    spritesheet_name,
    animation_name,
    scale,
    settings,
)
```

### Supported Frame Formats

`PNG`, `WebP`, `AVIF`, `BMP`, `DDS`, `TGA`, `TIFF`

---
<br>

## AnimationExporter

Exports frame sequences to animated image formats (GIF, WebP, APNG).

```python
from core.extractor.animation_exporter import AnimationExporter

exporter = AnimationExporter(output_dir, current_version, scale_image_func)
count = exporter.save_animations(image_tuples, spritesheet_name, animation_name, settings)
```

### Key Methods

| Method | Description |
|--------|-------------|
| `save_animations(...)` | Dispatch to format-specific exporter. |
| `save_gif(images, filename, fps, ...)` | Export optimized GIF. |
| `save_webp(images, filename, fps, ...)` | Export lossless animated WebP. |
| `save_apng(images, filename, fps, ...)` | Export animated PNG. |
| `remove_dups(animation)` | Merge duplicate frames in a Wand animation. |

---
<br>
<br>


# Parsers

The parser system provides unified metadata parsing across multiple spritesheet formats.

## ParserRegistry

Central registry for all available parsers. Provides format auto-detection and a single entry
point for parsing any supported format.

```python
from parsers.parser_registry import ParserRegistry

# Initialize (called automatically on first use)
ParserRegistry.initialize()

# Parse a file with auto-detection
result = ParserRegistry.parse_file("/path/to/atlas.json")
if result.is_valid:
    for sprite in result.sprites:
        process(sprite)
```

### Class Methods

| Method | Description |
|--------|-------------|
| `register(parser_cls)` | Register a parser class (can be used as decorator). |
| `get_parsers_for_extension(ext)` | Get parsers supporting an extension. |
| `detect_parser(file_path)` | Auto-detect best parser for a file. |
| `parse_file(file_path)` | Parse a file and return `ParseResult`. |

---
<br>

## BaseParser

Abstract base class all parsers must inherit from.

```python
from parsers.base_parser import BaseParser

class MyParser(BaseParser):
    FILE_EXTENSIONS = (".myext",)

    def extract_names(self) -> Set[str]:
        # Return animation/sprite names for UI
        ...

    @classmethod
    def parse_file(cls, file_path: str) -> ParseResult:
        # Parse and return structured result
        ...
```

---
<br>

## Parser Types

Core types defined in `parsers.parser_types`:

| Type | Description |
|------|-------------|
| `SpriteData` | TypedDict with canonical sprite structure. |
| `ParseResult` | Dataclass holding sprites, warnings, errors. |
| `ParserError` | Base exception for parser failures. |
| `ParserErrorCode` | Enum of error categories. |

#### SpriteData Keys

| Key | Required | Description |
|-----|----------|-------------|
| `name` | ✓ | Sprite identifier. |
| `x`, `y` | ✓ | Position in atlas (pixels). |
| `width`, `height` | ✓ | Sprite dimensions (pixels). |
| `frameX`, `frameY` | | Offset for trimmed sprites. |
| `frameWidth`, `frameHeight` | | Original dimensions before trim. |
| `rotated` | | `True` if rotated 90° in atlas. |

---
<br>

## Supported Formats

| Format | Parser | Extension(s) |
|--------|--------|--------------|
| Starling/Sparrow XML | `StarlingXmlParser` | `.xml` |
| TexturePacker JSON (Hash) | `JsonHashParser` | `.json` |
| TexturePacker JSON (Array) | `JsonArrayParser` | `.json` |
| Aseprite | `AsepriteParser` | `.json` |
| Spine | `SpineParser` | `.atlas` |
| Phaser 3 | `Phaser3Parser` | `.json` |
| Godot | `GodotAtlasParser` | `.tpsheet` |
| Unity | `TexturePackerUnityParser` | `.tpsheet` |
| CSS Spritesheet | `CssSpritesheetParser` | `.css` |
| Plist (Cocos2d) | `PlistXmlParser` | `.plist` |
| Adobe Animate Spritemap | `SpritemapParser` | `.json` |
| Plain text | `TxtParser` | `.txt` |
---
<br>
<br>

# Spritemap Module

Handles Adobe Animate spritemap exports (`Animation.json` + atlas image).

## AdobeSpritemapRenderer

High-level renderer for extracting symbol animations from Adobe Animate exports.

```python
from core.extractor.spritemap import AdobeSpritemapRenderer

renderer = AdobeSpritemapRenderer(
    animation_path,         # Path to Animation.json
    spritemap_json_path,    # Path to spritemap JSON
    atlas_image_path,       # Path to atlas PNG
)
symbols = renderer.list_symbol_names()
frames = renderer.render_symbol(symbol_name)  # List of PIL Images
```

### Key Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `list_symbol_names()` | `List[str]` | All symbols in the document. |
| `render_symbol(name)` | `List[Image]` | Render all frames of a symbol. |
| `get_symbol_frame_count(name)` | `int` | Number of frames in a symbol. |

---
<br>

## SpriteAtlas

Low-level sprite slicing and transformation for spritemap JSON.

```python
from core.extractor.spritemap.sprite_atlas import SpriteAtlas

atlas = SpriteAtlas(spritemap_json, atlas_image, canvas_size, resample)
image, offset = atlas.get_sprite(name, transform_matrix, color_effect)
```

<br>
<br>

---

# Unknown Spritesheet Handling

For images without metadata, the toolbox uses computer vision to detect sprite regions.

## UnknownParser

Fallback parser using flood-fill algorithms to detect sprite boundaries.

```python
from parsers.unknown_parser import UnknownParser

image, sprites = UnknownParser.parse_unknown_image(file_path, parent_window)
# sprites: List[dict] with detected regions
```

---
<br>

## UnknownSpritesheetHandler

Orchestrates background color detection and user prompts for unknown spritesheets.

```python
from core.extractor.unknown_spritesheet_handler import UnknownSpritesheetHandler

handler = UnknownSpritesheetHandler(logger=print)
cancelled = handler.handle_background_detection(input_dir, spritesheet_list, parent)
```

<br>
<br>

---

# Extraction Utilities

## SettingsManager

Manages layered settings with a three-tier hierarchy: global defaults → spritesheet overrides →
animation overrides. When retrieving settings, values merge with later tiers taking precedence.

```python
from utils.settings_manager import SettingsManager

manager = SettingsManager()

# Set global defaults
manager.set_global_settings(fps=24, scale=1.0, animation_format="GIF")

# Override for a specific spritesheet
manager.set_spritesheet_settings("player.png", fps=30, scale=2.0)

# Override for a specific animation
manager.set_animation_settings("player.png/idle", fps=12)

# Retrieve merged settings (global + spritesheet + animation)
settings = manager.get_settings("player.png", "player.png/idle")
# settings["fps"] == 12, settings["scale"] == 2.0, settings["animation_format"] == "GIF"
```

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `global_settings` | `dict` | Default settings applied to all exports. |
| `spritesheet_settings` | `dict` | Per-spritesheet overrides keyed by filename. |
| `animation_settings` | `dict` | Per-animation overrides keyed by animation name. |

### Methods

| Method | Description |
|--------|-------------|
| `set_global_settings(**kwargs)` | Update global defaults with key-value pairs. |
| `set_spritesheet_settings(name, **kwargs)` | Set overrides for a specific spritesheet. |
| `set_animation_settings(name, **kwargs)` | Set overrides for a specific animation. |
| `delete_spritesheet_settings(name)` | Remove stored settings for a spritesheet. |
| `delete_animation_settings(name)` | Remove stored settings for an animation. |
| `get_settings(filename, animation_name=None)` | Retrieve merged settings with all overrides applied. |

---
<br>

## Image Utilities

Helper functions in `core.extractor.image_utils`:

| Function | Description |
|----------|-------------|
| `scale_image(image, size, method)` | Scale with configurable resampling. |
| `pad_frames_to_canvas(images)` | Pad frames to common canvas size. |
| `ensure_rgba_array(source)` | Convert PIL Image or array to RGBA array. |
| `array_to_rgba_image(array)` | Convert RGBA array to PIL Image. |
| `frame_bbox(source)` | Get non-transparent bounding box. |
| `crop_to_bbox(array, bbox)` | Crop array to bounding box. |

---
<br>

## Frame Duration Utilities

Functions in `core.extractor.frame_pipeline`:

| Function | Description |
|----------|-------------|
| `build_frame_durations(count, fps, delay, period, var_delay)` | Compute per-frame durations in ms. |
| `compute_shared_bbox(images)` | Union bounding box across all frames. |
| `prepare_scaled_sequence(images, scale_func, scale, crop)` | Crop and scale a frame sequence. |

<br>
<br>

---

# UI Bindings

The extraction pipeline is designed for easy integration with any UI framework.

## Signal-Based Progress Reporting

The `Extractor` class accepts callbacks rather than binding directly to Qt signals, allowing
integration with any framework.

```python
def my_progress_handler(current: int, total: int, status: str):
    # Update your progress bar or status label
    ...

extractor = Extractor(
    progress_callback=my_progress_handler,
    ...
)
```

## Integrating with Custom UI Frameworks

1. **Create callback functions** matching the expected signatures.
2. **Pass callbacks** to `Extractor` on construction.
3. **Call `process_directory()`** from a background thread if needed.
4. **Use the cancel_event** (`threading.Event`) to signal abort.

```python
import threading

cancel_event = threading.Event()
extractor = Extractor(
    progress_callback=lambda c, t, s: update_ui(c, t, s),
    cancel_event=cancel_event,
    ...
)

# Run extraction in background
thread = threading.Thread(target=extractor.process_directory, args=(in_dir, out_dir))
thread.start()

# Cancel from UI
cancel_event.set()
```

<br>
<br>

---

# Generation Pipeline

The generation pipeline packs individual sprite images into optimized texture atlases. The main
entry point is `AtlasGenerator`, which orchestrates image loading, packing, compositing, and
metadata export.

## AtlasGenerator

Orchestrates the complete atlas generation workflow: loads images, detects duplicates, packs frames
using configurable algorithms, composites the final atlas, and exports metadata in various formats.

```python
from core.generator.atlas_generator import AtlasGenerator, GeneratorOptions

generator = AtlasGenerator()
generator.set_progress_callback(my_progress_handler)

result = generator.generate(
    animation_groups={"walk": ["walk_0.png", "walk_1.png", "walk_2.png"]},
    output_path="/path/to/atlas",
    options=GeneratorOptions(algorithm="maxrects", export_format="json-hash"),
)
```

### Key Methods

| Method | Description |
|--------|-------------|
| `generate(animation_groups, output_path, options)` | Generate an atlas from animation groups. |
| `set_progress_callback(callback)` | Set callback for progress updates. |

#### Progress Callback

The progress callback receives `(current: int, total: int, message: str)` during generation.

---
<br>

## GeneratorOptions

Configuration dataclass controlling atlas generation behavior.

```python
from core.generator.atlas_generator import GeneratorOptions

options = GeneratorOptions(
    algorithm="maxrects",       # Packing algorithm name
    heuristic="bssf",           # Algorithm-specific heuristic
    max_width=4096,             # Maximum atlas width
    max_height=4096,            # Maximum atlas height
    padding=2,                  # Pixels between sprites
    border_padding=0,           # Pixels around atlas edge
    power_of_two=False,         # Force power-of-two dimensions
    force_square=False,         # Force square atlas
    allow_rotation=False,       # Allow 90° rotation for tighter packing
    allow_flip=False,           # Allow sprite flipping
    trim_sprites=False,         # Trim transparent edges from sprites
    expand_strategy="short_side",  # How to grow atlas when needed
    image_format="png",         # Output image format
    export_format="starling-xml",  # Metadata format key
    compression_settings=None,  # Format-specific compression options
)
```

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `algorithm` | `str` | `"maxrects"` | Packing algorithm (`maxrects`, `guillotine`, `skyline`, `shelf`, `auto`). |
| `heuristic` | `str` | `None` | Algorithm-specific heuristic key. |
| `max_width` | `int` | `4096` | Maximum atlas width in pixels. |
| `max_height` | `int` | `4096` | Maximum atlas height in pixels. |
| `padding` | `int` | `2` | Pixels of padding between sprites. |
| `border_padding` | `int` | `0` | Pixels of padding around atlas edges. |
| `power_of_two` | `bool` | `False` | Force atlas dimensions to power of 2. |
| `force_square` | `bool` | `False` | Force atlas to be square. |
| `allow_rotation` | `bool` | `False` | Allow 90° rotation for tighter packing. |
| `allow_flip` | `bool` | `False` | Allow sprite flipping (limited format support). |
| `trim_sprites` | `bool` | `False` | Trim transparent edges from sprites. |
| `expand_strategy` | `str` | `"short_side"` | How to grow atlas (`disabled`, `width_first`, `height_first`, `short_side`, `long_side`, `both`). |
| `image_format` | `str` | `"png"` | Output image format (`png`, `webp`, `jpg`, etc.). |
| `export_format` | `str` | `"starling-xml"` | Metadata format key. |

---
<br>

## GeneratorResult

Dataclass containing the outcome of atlas generation.

```python
result = generator.generate(animation_groups, output_path, options)

if result.success:
    print(f"Atlas: {result.atlas_path}")
    print(f"Metadata: {result.metadata_path}")
    print(f"Size: {result.atlas_width}x{result.atlas_height}")
    print(f"Frames: {result.frame_count}")
    print(f"Efficiency: {result.efficiency * 100:.1f}%")
else:
    for error in result.errors:
        print(f"Error: {error}")
```

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `success` | `bool` | Whether generation succeeded. |
| `atlas_path` | `str` | Path to the generated atlas image. |
| `metadata_path` | `str` | Path to the generated metadata file. |
| `atlas_width` | `int` | Final atlas width in pixels. |
| `atlas_height` | `int` | Final atlas height in pixels. |
| `frame_count` | `int` | Number of packed frames. |
| `efficiency` | `float` | Packing efficiency (0.0–1.0). |
| `errors` | `List[str]` | List of error messages. |
| `warnings` | `List[str]` | List of warning messages. |

<br>
<br>

---

# Packers

The packer system provides bin packing algorithms for positioning sprites within an atlas. All
packers share a common interface defined by `BasePacker`.

## PackerRegistry

Central registry for all available packing algorithms with convenience functions for discovery
and instantiation.

```python
from packers import get_packer, pack, list_algorithms, get_heuristics_for_algorithm

# List available algorithms
for algo in list_algorithms():
    print(f"{algo['display_name']}: {algo['name']}")

# Get packer instance
packer = get_packer("maxrects")
result = packer.pack(frames)

# One-liner convenience function
result = pack("guillotine", frames, options)

# Get heuristics for an algorithm
heuristics = get_heuristics_for_algorithm("maxrects")
# [("bssf", "Best Short Side Fit"), ("blsf", "Best Long Side Fit"), ...]
```

### Functions

| Function | Description |
|----------|-------------|
| `get_packer(name, options)` | Get a packer instance by algorithm name. |
| `pack(algorithm, frames, options)` | Pack frames using the specified algorithm. |
| `list_algorithms()` | Get list of all registered algorithms. |
| `get_heuristics_for_algorithm(name)` | Get available heuristics for an algorithm. |
| `register_packer(cls)` | Decorator to register a custom packer class. |

---
<br>

## BasePacker

Abstract base class all packing algorithms must inherit from.

```python
from packers.base_packer import BasePacker
from packers.packer_types import FrameInput, PackerOptions, PackerResult

class MyPacker(BasePacker):
    ALGORITHM_NAME = "my-packer"
    DISPLAY_NAME = "My Custom Packer"
    SUPPORTED_HEURISTICS = [("fast", "Fast"), ("quality", "Quality")]

    def _pack_internal(
        self,
        frames: List[FrameInput],
        width: int,
        height: int,
    ) -> List[PackedFrame]:
        # Implement packing logic
        ...
```

### Abstract Methods

| Method | Description |
|--------|-------------|
| `_pack_internal(frames, width, height)` | Core packing algorithm implementation. |

### Provided Methods

| Method | Description |
|--------|-------------|
| `pack(frames)` | Main entry point with preprocessing and postprocessing. |
| `set_heuristic(key)` | Set the heuristic to use for packing. |

---
<br>

## Packer Types

Core types defined in `packers.packer_types`:

| Type | Description |
|------|-------------|
| `FrameInput` | Input frame data with id, width, height, and user_data. |
| `PackedFrame` | Result with frame position, rotation, and flip state. |
| `PackerOptions` | Configuration for sizing, padding, and expansion. |
| `PackerResult` | Container for packed frames with dimensions and efficiency. |
| `Rect` | NumPy-backed rectangle with position and size. |

#### FrameInput Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | `str` | Unique identifier for the frame. |
| `width` | `int` | Frame width in pixels. |
| `height` | `int` | Frame height in pixels. |
| `user_data` | `dict` | Optional arbitrary data passed through to output. |

#### PackedFrame Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | `str` | Frame identifier. |
| `x` | `int` | X position in atlas. |
| `y` | `int` | Y position in atlas. |
| `rotated` | `bool` | Whether the frame was rotated 90°. |
| `flipped_x` | `bool` | Whether the frame was flipped horizontally. |
| `flipped_y` | `bool` | Whether the frame was flipped vertically. |

#### Heuristic Enums

| Enum | Description |
|------|-------------|
| `MaxRectsHeuristic` | BSSF, BLSF, BAF, BL, CP heuristics for MaxRects. |
| `GuillotinePlacement` | BSSF, BLSF, BAF, WAF heuristics for Guillotine. |
| `GuillotineSplit` | SHORTER_LEFTOVER_AXIS, LONGER_LEFTOVER_AXIS, etc. |
| `SkylineHeuristic` | BOTTOM_LEFT, MIN_WASTE, BEST_FIT for Skyline. |
| `ShelfHeuristic` | NEXT_FIT, FIRST_FIT, BEST_WIDTH_FIT, etc. |
| `ExpandStrategy` | DISABLED, WIDTH_FIRST, HEIGHT_FIRST, SHORT_SIDE, LONG_SIDE, BOTH. |

---
<br>

## Available Algorithms

| Algorithm | Class | Description |
|-----------|-------|-------------|
| `maxrects` | `MaxRectsPacker` | Best overall quality, supports 5 heuristics. |
| `guillotine` | `GuillotinePacker` | Good balance of speed and quality. |
| `skyline` | `SkylinePacker` | Fast algorithm tracking top edge of placed rectangles. |
| `shelf` | `ShelfPacker` | Simple row-based packing, fastest. |
| `shelf-ffdh` | `ShelfPackerDecreasingHeight` | Shelf with height pre-sorting. |

<br>
<br>

---

# Exporters

The exporter system generates metadata files in various formats from packed sprite data. All
exporters share a common interface defined by `BaseExporter`.

## ExporterRegistry

Central registry for all available exporters with format lookup and unified export entry point.

```python
from exporters.exporter_registry import ExporterRegistry

# Initialize (called automatically on first use)
ExporterRegistry.initialize()

# Get all available formats
formats = ExporterRegistry.get_all_formats()
# ["aseprite", "css", "egret2d", "godot", "json-array", "json-hash", ...]

# Export using a specific format
result = ExporterRegistry.export_file(
    sprites=sprite_list,
    sprite_images=image_dict,
    output_path="/path/to/atlas",
    format_name="json-hash",
)
```

### Class Methods

| Method | Description |
|--------|-------------|
| `register(exporter_cls)` | Register an exporter class (can be used as decorator). |
| `get_exporter(format_name)` | Get exporter class by format name or extension. |
| `get_all_formats()` | Get list of all registered format names. |
| `get_supported_extensions()` | Get list of all supported output extensions. |
| `export_file(sprites, images, path, format)` | Export sprites using the specified format. |

---
<br>

## BaseExporter

Abstract base class all exporters must inherit from.

```python
from exporters.base_exporter import BaseExporter
from exporters.exporter_types import ExportOptions, PackedSprite

class MyExporter(BaseExporter):
    FILE_EXTENSION = ".myext"
    FORMAT_NAME = "my-format"

    def build_metadata(
        self,
        packed_sprites: List[PackedSprite],
        atlas_width: int,
        atlas_height: int,
        image_name: str,
        generator_metadata: Optional[GeneratorMetadata] = None,
    ) -> str:
        # Build and return metadata string
        ...
```

### Abstract Methods

| Method | Description |
|--------|-------------|
| `build_metadata(packed_sprites, width, height, image_name, generator_metadata)` | Generate format-specific metadata. |

### Provided Methods

| Method | Description |
|--------|-------------|
| `export_file(sprites, sprite_images, output_path)` | Main entry point for export. |
| `pack_sprites(sprites, sprite_images)` | Pack sprites into atlas layout. |
| `composite_atlas(packed_sprites, images, width, height)` | Render sprites onto atlas image. |

---
<br>

## Exporter Types

Core types defined in `exporters.exporter_types`:

| Type | Description |
|------|-------------|
| `ExportOptions` | Configuration for packing and output. |
| `ExportResult` | Container for export outcomes and diagnostics. |
| `PackedSprite` | Sprite with atlas position assigned. |
| `SpriteData` | TypedDict with canonical sprite structure (same as parser). |
| `GeneratorMetadata` | Metadata about the generation process for watermarking. |
| `ExporterError` | Base exception for exporter failures. |
| `ExporterErrorCode` | Enum of error categories. |

#### ExportOptions Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `image_format` | `str` | `"PNG"` | Output image format. |
| `padding` | `int` | `2` | Pixels between sprites. |
| `power_of_two` | `bool` | `False` | Force power-of-two dimensions. |
| `max_width` | `int` | `4096` | Maximum atlas width. |
| `max_height` | `int` | `4096` | Maximum atlas height. |
| `allow_rotation` | `bool` | `False` | Allow 90° rotation. |
| `trim_sprites` | `bool` | `False` | Trim transparent edges. |
| `pretty_print` | `bool` | `True` | Format metadata with indentation. |

---
<br>

## Supported Export Formats

| Format | Exporter | Extension |
|--------|----------|-----------|
| Starling/Sparrow XML | `StarlingXmlExporter` | `.xml` |
| TexturePacker JSON (Hash) | `JsonHashExporter` | `.json` |
| TexturePacker JSON (Array) | `JsonArrayExporter` | `.json` |
| Spine | `SpineExporter` | `.atlas` |
| TexturePacker XML | `TexturePackerXmlExporter` | `.xml` |
| Phaser 3 | `Phaser3Exporter` | `.json` |
| CSS Spritesheet | `CssExporter` | `.css` |
| Plain Text | `TxtExporter` | `.txt` |
| Plist (Cocos2d) | `PlistExporter` | `.plist` |
| UIKit Plist | `UIKitPlistExporter` | `.plist` |
| Godot | `GodotExporter` | `.tpsheet` |
| Egret 2D | `Egret2dExporter` | `.json` |
| Unreal Paper2D | `Paper2dExporter` | `.paper2dsprites` |
| Unity | `UnityExporter` | `.tpsheet` |
| Aseprite | `AsepriteExporter` | `.json` |

<br>
<br>

---

# Editor Composite

The editor composite module enables building new animations from existing frame sequences. It
provides utilities for assembling frames from multiple source animations with optional metadata
overrides.

## build_editor_composite_frames

Assembles frames for an editor-defined composite animation by referencing frames from source
animations and optionally overriding per-frame metadata.

```python
from core.editor.editor_composite import build_editor_composite_frames

definition = {
    "name": "custom_animation",
    "sequence": [
        {"source_animation": "walk", "source_frame_index": 0},
        {"source_animation": "walk", "source_frame_index": 1, "duration_ms": 100},
        {"source_animation": "idle", "source_frame_index": 0},
    ],
}

frames = build_editor_composite_frames(
    definition=definition,
    source_frames=animation_map,  # Dict[str, List[FrameTuple]]
    log_warning=print,            # Optional warning callback
)
# frames: List[Tuple[name, image, metadata]]
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `definition` | `dict` | Dict with `"sequence"` list defining frame references. |
| `source_frames` | `AnimationMap` | Available animations keyed by name. |
| `log_warning` | `Callable[[str], None]` | Optional callback for warning messages. |

### Sequence Entry Keys

| Key | Required | Description |
|-----|----------|-------------|
| `source_animation` | ✓ | Name of the source animation. |
| `source_frame_index` | ✓ | Index of the frame in the source animation. |
| `duration_ms` | | Override duration in milliseconds. |
| `name` | | Override frame name. |
| `original_key` | | Original frame key for lookup. |

---
<br>

## clone_animation_map

Creates a shallow copy of an animation map, duplicating lists but sharing image object references.

```python
from core.editor.editor_composite import clone_animation_map

cloned = clone_animation_map(original_animations)
# Modify cloned without affecting original
```

---
<br>

## Type Aliases

| Type | Definition | Description |
|------|------------|-------------|
| `FrameTuple` | `Tuple[str, Any, dict]` | A single frame: (name, image object, metadata dict). |
| `AnimationMap` | `Dict[str, List[FrameTuple]]` | Mapping from animation name to its ordered list of frames. |

<br>
<br>

---

# Utility Classes

## AppConfig

Manages persistent application configuration.

```python
class AppConfig:
    def __init__(self, config_path=None)
```

### Class Attributes
- `DEFAULTS` (dict): Default configuration values
- `TYPE_MAP` (dict): Type validation mapping

### Methods

**`load()`**
- Loads configuration from file

**`save()`**
- Saves current configuration to file

**`get(key, default=None)`**
- Retrieves configuration value
- **Parameters:**
  - `key` (str): Configuration key
  - `default` (any, optional): Default value if key not found
- **Returns:** Configuration value

**`set(key, value)`**
- Sets configuration value and saves immediately
- **Parameters:**
  - `key` (str): Configuration key
  - `value` (any): Value to set

**`get_extraction_defaults()`**
- Gets copy of extraction default settings
- **Returns:** Dictionary of extraction defaults

**`set_extraction_defaults(**kwargs)`**
- Updates extraction defaults
- **Parameters:** Keyword arguments for settings

## Utilities

Static utility functions for common operations.

```python
class Utilities:
```

### Static Methods

**`find_root(target_name)`**
- Finds directory containing target file/folder
- **Parameters:** `target_name` (str): Name to search for
- **Returns:** Path to containing directory or None

**`count_spritesheets(spritesheet_list)`**
- Counts number of spritesheets in list
- **Parameters:** `spritesheet_list` (list): List of spritesheets
- **Returns:** Integer count

**`replace_invalid_chars(name)`**
- Replaces invalid filename characters with underscores
- **Parameters:** `name` (str): Input filename
- **Returns:** Sanitized filename string

**`strip_trailing_digits(name)`**
- Removes trailing digits and .png extension
- **Parameters:** `name` (str): Input name
- **Returns:** Cleaned name string

**`format_filename(prefix, sprite_name, animation_name, filename_format, replace_rules)`**
- Formats filename using template and rules
- **Parameters:**
  - `prefix` (str): Custom prefix
  - `sprite_name` (str): Sprite name
  - `animation_name` (str): Animation name
  - `filename_format` (str): Format template
  - `replace_rules` (list): Find/replace rules
- **Returns:** Formatted filename string

<br>
<br>

---

# Configuration

## Settings Dictionary Structure

```python
settings = {
    "animation_format": str,      # "GIF", "WebP", "APNG", "None"
    "fps": int,                   # 1-120
    "delay": int,                 # milliseconds
    "period": int,                # total animation period
    "scale": float,               # scale factor
    "threshold": float,           # alpha threshold 0.0-1.0
    "keep_frames": str,           # "All", "First", "Last", etc.
    "crop_option": str,           # "Animation based", "Frame based", "No crop"
    "filename_format": str,       # filename template
    "variable_delay": bool,       # enable variable delays
    "fnf_idle_loop": bool,        # FNF idle loop optimization
}
```

## Configuration File Format

```json
{
    "resource_limits": {
        "cpu_cores": "auto",
        "memory_limit_mb": 0
    },
    "extraction_defaults": {
        "animation_format": "None",
        "fps": 24,
        "delay": 250,
        "period": 0,
        "scale": 1.0,
        "threshold": 0.5,
        "keep_frames": "All",
        "crop_option": "Animation based",
        "filename_format": "Standardized",
        "variable_delay": false,
        "fnf_idle_loop": false
    }
}
```

<br>
<br>

# Error Handling

## ExceptionHandler

Centralized error handling and user feedback.

```python
class ExceptionHandler:
```

### Static Methods

**`handle_exception(e, metadata_path, sprites_failed)`**
- Handles and translates exceptions for user display
- **Parameters:**
  - `e` (Exception): Caught exception
  - `metadata_path` (str): Path to metadata file
  - `sprites_failed` (int): Count of failed sprites
- **Raises:** Formatted exception with user-friendly message

**`handle_validation_error(key, expected_type)`**
- Formats validation error messages
- **Parameters:**
  - `key` (str): Setting key that failed validation
  - `expected_type` (type): Expected data type
- **Returns:** Formatted error message string

## Common Exception Types

- **File I/O Errors**: Missing files, permission issues
- **Format Errors**: Invalid XML/TXT/JSON format
- **Validation Errors**: Invalid setting values
- **Memory Errors**: Insufficient memory for large atlases
- **ImageMagick Errors**: Missing or misconfigured ImageMagick

---