# API Reference

Technical reference for developers wanting to contribute to TextureAtlas to GIF and Frames.
**This doc file was partly written by AI, some parts may need to be rewritten which I will do whenever I have time**

## 📋 Table of Contents

- [Core Classes](#-core-classes)
- [Utility Classes](#-utility-classes)
- [Parser Classes](#-parser-classes)
- [GUI Classes](#-gui-classes)
- [Configuration](#️-configuration)
- [Error Handling](#-error-handling)

## 🔧 Core Classes

### Extractor

Main coordinator class for sprite extraction and animation generation.

```python
class Extractor:
    def __init__(self, progress_bar, current_version, settings_manager, app_config=None)
```

#### Methods

**`process_directory(input_dir, output_dir, progress_var, tk_root, spritesheet_list=None)`**
- Processes multiple texture atlases in a directory
- **Parameters:**
  - `input_dir` (str): Input directory path
  - `output_dir` (str): Output directory path  
  - `progress_var` (tk.DoubleVar): Progress tracking variable
  - `tk_root` (tk.Tk): Main application window
  - `spritesheet_list` (list, optional): List of specific files to process
- **Returns:** Tuple of (frames_generated, anims_generated, sprites_failed)

**`extract_sprites(atlas_path, metadata_path, output_dir, settings)`**
- Extracts sprites from a single atlas file
- **Parameters:**
  - `atlas_path` (str): Path to texture atlas image
  - `metadata_path` (str): Path to metadata file (XML/TXT)
  - `output_dir` (str): Output directory
  - `settings` (dict): Export settings
- **Returns:** Tuple of (frames_generated, anims_generated)

**`generate_temp_gif_for_preview(atlas_path, metadata_path, settings, animation_name=None, temp_dir=None)`**
- Creates temporary GIF for preview functionality
- **Parameters:**
  - `atlas_path` (str): Path to texture atlas
  - `metadata_path` (str): Path to metadata file
  - `settings` (dict): Export settings
  - `animation_name` (str, optional): Specific animation to preview
  - `temp_dir` (str, optional): Temporary directory path
- **Returns:** Path to generated temporary GIF

### AtlasProcessor

Handles loading and processing of texture atlas files.

```python
class AtlasProcessor:
    def __init__(self, atlas_path, metadata_path)
```

#### Attributes
- `atlas_path` (str): Path to the texture atlas image
- `metadata_path` (str): Path to the metadata file
- `atlas` (PIL.Image): Loaded atlas image
- `sprites` (list): Parsed sprite data

#### Methods

**`open_atlas_and_parse_metadata()`**
- Opens atlas image and parses metadata file
- **Returns:** Tuple of (atlas_image, sprites_list)

### SpriteProcessor

Processes individual sprites from atlas data.

```python
class SpriteProcessor:
    def __init__(self, atlas, sprites)
```

#### Methods

**`process_sprites()`**
- Processes sprites into grouped animations
- **Returns:** Dictionary mapping animation names to sprite lists

### AnimationProcessor

Handles animation generation and export coordination.

```python
class AnimationProcessor:
    def __init__(self, animations, atlas_path, output_dir, settings_manager, current_version)
```

#### Methods

**`process_animations()`**
- Processes all animations and exports them
- **Returns:** Tuple of (frames_generated, anims_generated)

**`scale_image(img, size)`**
- Scales an image by the given factor
- **Parameters:**
  - `img` (PIL.Image): Source image
  - `size` (float): Scale factor (negative values flip horizontally)
- **Returns:** Scaled PIL.Image

### AnimationExporter

Exports animations in various formats (GIF, WebP, APNG).

```python
class AnimationExporter:
    def __init__(self, output_dir, current_version, scale_image_func, quant_frames)
```

#### Methods

**`save_animations(image_tuples, spritesheet_name, animation_name, settings)`**
- Saves animation in specified format
- **Parameters:**
  - `image_tuples` (list): List of (name, image, metadata) tuples
  - `spritesheet_name` (str): Name of source spritesheet
  - `animation_name` (str): Name of animation
  - `settings` (dict): Export settings
- **Returns:** Number of animations generated

**`save_gif(images, filename, fps, delay, period, scale, threshold, settings)`**
- Exports GIF animation with optimization
- **Parameters:**
  - `images` (list): List of PIL.Image objects
  - `filename` (str): Output filename
  - `fps` (int): Frames per second
  - `delay` (int): Frame delay in milliseconds
  - `period` (int): Total animation period
  - `scale` (float): Scale factor
  - `threshold` (float): Alpha threshold for optimization
  - `settings` (dict): Additional settings

### FrameExporter

Exports individual frames as PNG files.

```python
class FrameExporter:
    def __init__(self, output_dir, current_version, scale_image_func)
```

#### Methods

**`save_frames(image_tuples, kept_frame_indices, spritesheet_name, animation_name, scale, settings)`**
- Saves selected frames as PNG files
- **Parameters:**
  - `image_tuples` (list): Frame data
  - `kept_frame_indices` (list): Indices of frames to save
  - `spritesheet_name` (str): Source spritesheet name
  - `animation_name` (str): Animation name
  - `scale` (float): Scale factor
  - `settings` (dict): Export settings
- **Returns:** Number of frames generated

### FrameSelector

Utility class for frame selection logic.

```python
class FrameSelector:
```

#### Static Methods

**`is_single_frame(image_tuples)`**
- Determines if animation consists of a single frame
- **Parameters:** `image_tuples` (list): Frame data
- **Returns:** Boolean indicating single frame status

**`get_kept_frames(settings, single_frame, image_tuples)`**
- Gets list of frame identifiers to keep based on settings
- **Parameters:**
  - `settings` (dict): Export settings
  - `single_frame` (bool): Whether animation is single frame
  - `image_tuples` (list): Frame data
- **Returns:** List of frame identifiers

**`get_kept_frame_indices(kept_frames, image_tuples)`**
- Converts frame identifiers to integer indices
- **Parameters:**
  - `kept_frames` (list): Frame identifiers
  - `image_tuples` (list): Frame data
- **Returns:** Sorted list of integer indices

## 🔧 Utility Classes

### SettingsManager

Manages global, spritesheet-specific, and animation-specific settings.

```python
class SettingsManager:
    def __init__(self)
```

#### Attributes
- `global_settings` (dict): Default settings for all animations
- `spritesheet_settings` (dict): Per-spritesheet setting overrides
- `animation_settings` (dict): Per-animation setting overrides

#### Methods

**`set_global_settings(**kwargs)`**
- Updates global default settings
- **Parameters:** Keyword arguments for settings

**`set_spritesheet_settings(spritesheet_name, **kwargs)`**
- Sets settings for a specific spritesheet
- **Parameters:**
  - `spritesheet_name` (str): Name of spritesheet
  - `**kwargs`: Setting key-value pairs

**`set_animation_settings(animation_name, **kwargs)`**
- Sets settings for a specific animation
- **Parameters:**
  - `animation_name` (str): Name of animation
  - `**kwargs`: Setting key-value pairs

**`get_settings(filename, animation_name=None)`**
- Retrieves merged settings with proper inheritance
- **Parameters:**
  - `filename` (str): Spritesheet filename
  - `animation_name` (str, optional): Animation name
- **Returns:** Dictionary of merged settings

### AppConfig

Manages persistent application configuration.

```python
class AppConfig:
    def __init__(self, config_path=None)
```

#### Class Attributes
- `DEFAULTS` (dict): Default configuration values
- `TYPE_MAP` (dict): Type validation mapping

#### Methods

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

### Utilities

Static utility functions for common operations.

```python
class Utilities:
```

#### Static Methods

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

## 📄 Parser Classes

### XmlParser

Parses XML metadata files in Starling/Sparrow format.

```python
class XmlParser:
    def __init__(self, directory, xml_filename, listbox_data)
```

#### Methods

**`get_data()`**
- Parses XML and populates listbox with animation names

**`extract_names(xml_root)`**
- Extracts unique animation names from XML
- **Parameters:** `xml_root` (xml.etree.ElementTree.Element): XML root
- **Returns:** Set of animation names

#### Static Methods

**`parse_xml_data(file_path)`**
- Parses XML file and returns sprite data
- **Parameters:** `file_path` (str): Path to XML file
- **Returns:** List of sprite dictionaries

### TxtParser

Parses TXT metadata files in TextPacker format.

```python
class TxtParser:
    def __init__(self, directory, txt_filename, listbox_data)
```

#### Methods

**`get_data()`**
- Parses TXT and populates listbox with animation names

**`extract_names()`**
- Extracts unique animation names from TXT
- **Returns:** Set of animation names

#### Static Methods

**`parse_txt_packer(file_path)`**
- Parses TXT file and returns sprite data
- **Parameters:** `file_path` (str): Path to TXT file
- **Returns:** List of sprite dictionaries

### FnfUtilities

Handles Friday Night Funkin' character data import.

```python
class FnfUtilities:
    def __init__(self)
```

#### Methods

**`detect_engine(file_path)`**
- Detects FNF engine type from file
- **Parameters:** `file_path` (str): Path to character file
- **Returns:** Tuple of (engine_type, parsed_data)

**`fnf_load_char_data_settings(settings_manager, data_dict, listbox_png, listbox_data)`**
- Loads FNF character settings into settings manager
- **Parameters:**
  - `settings_manager` (SettingsManager): Settings manager instance
  - `data_dict` (dict): Data dictionary
  - `listbox_png` (tk.Listbox): PNG listbox widget
  - `listbox_data` (tk.Listbox): Data listbox widget

## 🎨 GUI Classes

### TextureAtlasExtractorApp

Main application class managing the GUI interface.

```python
class TextureAtlasExtractorApp:
    def __init__(self)
```

#### Attributes
- `current_version` (str): Application version
- `app_config` (AppConfig): Configuration manager
- `settings_manager` (SettingsManager): Settings manager
- `root` (tk.Tk): Main window

### Window Classes

Each GUI window class follows a similar pattern:

```python
class WindowClass:
    def __init__(self, parent, *args, **kwargs)
```

Common window classes:
- `AppConfigWindow`: Application configuration
- `HelpWindow`: Help and documentation
- `FindReplaceWindow`: Filename find/replace rules
- `OverrideSettingsWindow`: Animation-specific settings
- `GifPreviewWindow`: Animation preview
- `SettingsWindow`: Settings display

## ⚙️ Configuration

### Settings Dictionary Structure

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

### Configuration File Format

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

## 🐛 Error Handling

### ExceptionHandler

Centralized error handling and user feedback.

```python
class ExceptionHandler:
```

#### Static Methods

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

### Common Exception Types

- **File I/O Errors**: Missing files, permission issues
- **Format Errors**: Invalid XML/TXT/JSON format
- **Validation Errors**: Invalid setting values
- **Memory Errors**: Insufficient memory for large atlases
- **ImageMagick Errors**: Missing or misconfigured ImageMagick

---