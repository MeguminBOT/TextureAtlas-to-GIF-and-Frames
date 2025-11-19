# Developer Documentation

Technical documentation for developers working with the TextureAtlas to GIF and Frames codebase.

**This doc file was partly written by AI**

## 📋 Table of Contents

- [Architecture Overview](#️-architecture-overview)
- [Code Structure](#-code-structure)
- [Core Classes](#-core-classes)
- [API Reference](#-api-reference)
- [Development Setup](#️-development-setup)
- [Contributing Guidelines](#-contributing-guidelines)
- [Extension Points](#-extension-points)
- [Development Notes](#-development-notes)

## 🏗️ Architecture Overview

We're attempting to keep the code structure as modular as possible with clear separation of concerns:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GUI Layer     │    │  Utils Layer    │    │ Parsers Layer   │
│                 │    │                 │    │                 │
│ • Windows       │    │ • Configuration │    │ • XML Parser    │
│ • Dialogs       │    │ • Utilities     │    │ • TXT Parser    │
│ • User Input    │    │ • Dependencies  │    │ • FNF Support   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Core Layer                               │
│                                                                 │
│ • Extractor       • Animation Processor    • Frame Selector    │
│ • Atlas Processor • Animation Exporter     • Sprite Processor  │
│ • Frame Exporter  • Exception Handler                          │
└─────────────────────────────────────────────────────────────────┘
```

### Key Design Principles

- **Separation of Concerns**: Each module has a specific responsibility
- **Modular Design**: Components can be modified independently
- **Error Handling**: Centralized exception handling and user feedback
- **Configuration Management**: Persistent settings with validation
- **Extensibility**: Support for new formats and engines


## 📁 Code Structure

### Directory Organization

```
src/
├── Main.py                 # Application entry point
├── core/                   # Core processing logic
│   ├── extractor.py        # Main extraction coordinator
│   ├── atlas_processor.py  # Texture atlas handling
│   ├── sprite_processor.py # Individual sprite processing
│   ├── animation_*.py      # Animation-related processing
│   ├── frame_*.py          # Frame handling utilities
│   └── exception_handler.py # Error handling
├── gui/                    # User interface components
│   ├── *_window.py         # Individual window classes
│   └── __init__.py
├── parsers/                # Metadata file parsers
│   ├── xml_parser.py       # XML/Starling format support
│   ├── txt_parser.py       # TextPacker format support
│   └── __init__.py
└── utils/                  # Utility functions and helpers
    ├── app_config.py       # Application configuration
    ├── settings_manager.py # Animation settings management
    ├── utilities.py        # General utilities
    ├── fnf_utilities.py    # FNF-specific functions
    ├── dependencies_checker.py # System dependency validation
    ├── update_checker.py   # Version checking
    └── __init__.py
```


### Import Structure
Imports should be organized like the example below:
```python
# Python packages, preferably built-in packages being listed first.
import os
import platform
import shutil
import tempfile

# Our classes
from utils.dependencies_checker import DependenciesChecker
from utils.app_config import AppConfig
from core.extractor import Extractor
from core.atlas_processor import AtlasProcessor
from core.sprite_processor import SpriteProcessor
from parsers.xml_parser import XmlParser
from parsers.txt_parser import TxtParser
from gui.* import *
```


## 🔧 Core Classes

### Main Application (`Main.py`)

```python
class TextureAtlasExtractorApp:
    """Main application class managing the GUI and orchestrating all operations."""
    
    def __init__(self):
        # Initialize GUI, configuration, and managers
        self.current_version = '1.9.4'
        self.app_config = AppConfig()
        self.settings_manager = SettingsManager()
        
    def setup_gui(self):
        # Create and configure main window and widgets
        
    def load_atlas_data(self, atlas_path, metadata_path):
        # Load and parse texture atlas and metadata
        
    def extract_animations(self):
        # Coordinate the extraction process
```

### Extractor (`core/extractor.py`)

```python
class Extractor:
    """Coordinates the sprite extraction and animation generation process."""
    
    def process_directory(self, input_dir, output_dir, progress_var, tk_root, spritesheet_list=None):
        # Process multiple atlas files with progress tracking
        
    def extract_sprites(self, atlas_path, metadata_path, output_dir, settings):
        # Extract sprites from a single atlas file
        
    def generate_temp_gif_for_preview(self, atlas_path, metadata_path, settings, animation_name=None, temp_dir=None):
        # Generate temporary GIF for preview functionality
```

### Settings Management (`utils/settings_manager.py`)

```python
class SettingsManager:
    """Manages global, spritesheet-specific, and animation-specific settings."""
    
    def __init__(self):
        self.global_settings = {}
        self.spritesheet_settings = {}
        self.animation_settings = {}
    
    def get_settings(self, filename, animation_name=None):
        # Retrieve merged settings with proper inheritance
        
    def set_animation_settings(self, animation_name, **kwargs):
        # Set animation-specific overrides
```

### Animation Processing (`core/animation_processor.py`)

```python
class AnimationProcessor:
    """Processes animations from texture atlas data."""
    
    def __init__(self, animations, atlas_path, output_dir, settings_manager, current_version):
        self.animations = animations
        self.frame_exporter = FrameExporter(...)
        self.animation_exporter = AnimationExporter(...)
    
    def process_animations(self):
        # Process all animations and return statistics
```


## 📚 API Reference

### Core Processing Pipeline

#### 1. Atlas Loading
```python
# Load texture atlas and metadata
atlas_processor = AtlasProcessor(atlas_path, metadata_path)
atlas, sprites = atlas_processor.atlas, atlas_processor.sprites
```

#### 2. Sprite Processing
```python
# Process sprites into animations
sprite_processor = SpriteProcessor(atlas, sprites)
animations = sprite_processor.process_sprites()
```

#### 3. Animation Export
```python
# Export animations with settings
animation_processor = AnimationProcessor(animations, atlas_path, output_dir, settings_manager, version)
frames_generated, anims_generated = animation_processor.process_animations()
```


### Configuration API

#### Application Configuration
```python
# Persistent app settings
app_config = AppConfig()
app_config.set("extraction_defaults", {"fps": 24, "format": "GIF"})
defaults = app_config.get_extraction_defaults()
```

#### Settings Management
```python
# Runtime settings management
settings_manager = SettingsManager()
settings_manager.set_global_settings(fps=24, scale=1.0)
settings_manager.set_animation_settings("character_idle", fps=12)
final_settings = settings_manager.get_settings("spritesheet.png", "character_idle")
```

### Parser Extensions

#### Adding New Format Support
```python
class CustomParser:
    """Template for adding new metadata format support."""
    
    @staticmethod
    def parse_custom_data(file_path):
        """Parse custom format and return sprite list."""
        sprites = []
        # Parse file and populate sprites list
        # Each sprite dict must contain: name, x, y, width, height
        # Optional: frameX, frameY, frameWidth, frameHeight, rotated
        return sprites
        
    def extract_names(self, data):
        """Extract animation names for UI display."""
        names = set()
        # Process data and extract unique animation names
        return names
```

### GUI Extension Points

#### Custom Windows
```python
class CustomWindow:
    """Template for adding new GUI windows."""
    
    def __init__(self, parent, *args, **kwargs):
        self.window = tk.Toplevel(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """Create and arrange UI elements."""
        pass
        
    def on_confirm(self):
        """Handle user confirmation."""
        pass
```
*For full API overview, see the [API Reference](api-reference.md).* al


## 🛠️ Development Setup

### Prerequisites
- Python 3.10+
- Git for version control
- Text editor/IDE (VS Code recommended)

### Environment Setup
```bash
# Clone repository
git clone https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames.git
cd TextureAtlas-to-GIF-and-Frames

# Create virtual environment (if desired)
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies (stable set)
pip install -r setup/requirements.txt

# Optional: install the experimental/latest stack
# pip install -r setup/requirements-experimental.txt

# Install development dependencies (Optional)
pip install pytest black flake8 mypy
```

### Project Structure Setup
```bash
# Create development branches
git checkout -b feature/new-feature
git checkout -b bugfix/issue-description

# Set up pre-commit hooks (optional)
pip install pre-commit
pre-commit install
```

### Running Tests
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_extractor.py

# Run with coverage
pytest --cov=src tests/
```

### Code Quality
```bash
# Format code
black src/

# Check style
flake8 src/

# Type checking
mypy src/
```


## 🤝 Contributing Guidelines

### Code Style
- Follow PEP 8 style guidelines as much as you can.
- Use meaningful variable and function names, they should be as directly on the nose as possible
- Add docstrings to all classes and public methods
- Keep functions focused and under 50 lines when possible
- Avoid repetitive code, if it can be used for something else it's more likely to fit as a Utility class.
- Back-end and front-end code should be as separated as possible, this makes updates to the graphical user interface easier.
- Pass as little variables as possible to functions.

### Documentation
- Update relevant documentation for new features
- Include inline comments for complex logic
- Add examples for new API methods
- Update version numbers in relevant files, excluding "latestVersion.txt" as this will cause pre-mature update notifications for users

### Testing
- Test edge cases and error conditions
- Ensure all tests pass before submitting
- Maintain test coverage above 80%

**OR**
- Test app functionality thoroughly with a large number of spritesheets

### Git Workflow
```bash
# Create feature branch
git checkout -b feature/feature-name

# Make commits with descriptive messages
git commit -m "Add support for new animation format"

# Push branch and create pull request
git push origin feature/feature-name
```


### Pull Request Guidelines
- Provide clear description of changes
- Include screenshots for UI changes
- Link related issues
- Ensure you've tested with at least 25 spritesheets if your changes impact the extraction process.


## 🔌 Extension Points

### Adding New Export Formats

1. **Create Exporter Class**:
```python
class NewFormatExporter:
    def save_animation(self, images, filename, settings):
        # Implement format-specific export logic
        pass
```

2. **Register in AnimationExporter**:
```python
# In save_animations method
elif animation_format == 'NewFormat':
    self.save_new_format(images, filename, fps, delay, period, scale, settings)
```

3. **Add UI Support**:
```python
# Add to format dropdown in main GUI
format_options = ['None', 'GIF', 'WebP', 'APNG', 'NewFormat']
```

### Adding New FNF Engine Support

1. **Extend FnfUtilities**:
```python
def detect_new_engine(self, file_path):
    # Add detection logic for new engine format
    if self.is_new_engine_format(data):
        return "New Engine", parsed_data
    return "Unknown", None
```

2. **Add Parser Logic**:
```python
elif engine_type == "New Engine" and parsed_data:
    # Handle new engine specific data structure
    self.process_new_engine_data(parsed_data)
```

### Custom Settings Validation

```python
# In AppConfig class
TYPE_MAP = {
    "custom_setting": lambda x: custom_validator(x),
    # Add custom validation functions
}

def custom_validator(value):
    # Implement custom validation logic
    if not is_valid(value):
        raise ValueError("Invalid custom setting")
    return processed_value
```

### Adding New Utilities

```python
# In utils/utilities.py
class Utilities:
    @staticmethod
    def new_utility_function(input_data):
        """Add new utility functions here."""
        # Implement utility logic
        return processed_data
```

## 📝 Development Notes

### Performance Considerations
- Implement progress callbacks for long operations
- Consider memory usage increases.
- Use appropriate image formats for intermediate processing

### Error Handling
- Use centralized exception handling through ExceptionHandler
- Provide meaningful error messages to users
- Log errors for debugging purposes
- Gracefully handle missing dependencies

### Threading Considerations
- GUI operations must run on main thread
- Use ThreadPoolExecutor for parallel processing
- Implement proper progress reporting from worker threads
- Handle thread cleanup and cancellation

### Memory Management
- Dispose of large Image objects when no longer needed
- Use appropriate image modes (RGBA vs RGB)
- Monitor memory usage during batch processing

---

*For usage instructions, see the [User Manual](user-manual.md). For installation help, see the [Installation Guide](installation-guide.md).*

*You can also see a fully AI generated documentation on DeepWiki as an alternative*
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames)