# TextureAtlas Toolbox

**A powerful, free and open-source tool for extracting, generating, and converting Texture Atlases**

[TextureAtlas Toolbox](https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames) is an all-in-one solution for working with texture atlases and spritesheets. Extract sprites into organized frame collections and GIF/WebP/APNG animations, generate optimized atlases from individual frames, or convert between 15+ atlas formats. Perfect for game developers, modders, and anyone creating showcases of game sprites.

*Formerly known as TextureAtlas to GIFs and Frames*

📄 **Licensed under [AGPL-3.0](https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/blob/main/LICENSE)**  
📜 **Third-party licenses:** See [`docs/licenses.md`](docs/licenses.md)

## Quick Navigation

-   [Quick Start](#quick-start)
-   [Features](#features)
    -   [Extractor](#extractor)
    -   [Generator](#generator)
    -   [Editor (Beta)](#beta-editor-works-with-extractor-only-for-now)
    -   [General](#general)
-   [Supported Formats](#supported-formats)
    -   [Extraction](#extraction)
    -   [Generation](#generation)
-   [Current Limitations](#current-limitations)
-   [Planned Features](#planned-features)
-   [Installation and Usage](#installation-and-usage)
-   [Community Translations](#community-translations)
-   [Official Download Sites](#official-download-sites)
-   [Technical Information](#technical-information)
-   [Support & Contributing](#support--contributing)
-   [Special Thanks](#special-thanks)
-   [Documentation](docs/README.md)

## Quick Start

### Get the app:

1. **Download** from [official sources](#official-download-sites)
2. **Install** following the [Installation Guide](https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/wiki/Installation)

### Extracting Sprites

1. **Load** a folder with texture atlases
2. **Configure** settings (frame rate, scale, cropping)
3. **Select** your desired output formats
4. **Press** Start process and enjoy the results.

### Creating Texture Atlases

1. **Load** individual frame images or existing spritesheets
2. **Configure** packing options (algorithm, padding, dimensions)
3. **Select** your desired output format
4. **Press** Generate Atlas and enjoy the results.

## Features

### Extractor

Extract TextureAtlas for showcases/galleries of game sprites.

-   ✅ **Wide format support**: Parses 15+ texture atlas formats — see [Supported Formats](#supported-formats)
-   ✅ **Batch processing**: Extract multiple animations and spritesheets simultaneously
-   ✅ **Organized output**: Sort frames from spritesheets into individual folders
-   ✅ **Advanced controls**: Customizable frame rate, loop delay, scale, frame selection, and alpha transparency threshold
-   ✅ **Smart cropping**: Animation-based and frame-based cropping options
-   ✅ **Find/Replace rules**: Customize output filenames with pattern matching
-   ✅ **Multiple animation formats**: Export to GIF, WebP, and APNG
-   ✅ **Multiple frame formats**: Export individual frames as PNG, WebP, AVIF, BMP, DDS, TGA, or TIFF
-   ✅ **Compression control**: Lossless and lossy compression methods
-   ✅ **Preview system**: Real-time GIF preview with playback controls
-   ✅ (\*) **Friday Night Funkin' support**: Import character data files from various FNF engines
-   ✅ (\*) **Automatic sprite detection**: Process image files without metadata using intelligent boundary detection

### Generator

Create TextureAtlases for usage in games or applications.

-   ✅ **Wide format support**: Exports to 15+ different texture atlas formats — see [Supported Formats](#supported-formats)
-   ✅ **Create TextureAtlases from Frames**: Combine individual frames into optimized spritesheets
-   ✅ **Convert/Repack TextureAtlases**: Quickly convert between different formats or repack with higher efficiency
-   ✅ **Multiple packing algorithms**: MaxRects, Guillotine, Skyline, and Shelf packers with various heuristics
-   ✅ **Auto-optimization**: Automatically selects the best algorithm and heuristic for your current export to ensure highest packing efficiency
-   ✅ **Duplicate detection**: Identifies identical frames and deduplicates them in the atlas
-   ✅ **Configurable atlas options**: Padding, border, power-of-two, square, and max dimensions
-   ✅ **Sprite rotation**: Optional 90° rotation for tighter packing (format-dependent)
-   ✅ **Multiple image formats**: Save atlases as PNG, WebP, JPEG, TIFF, AVIF, BMP, TGA, or DDS
-   ✅ **Compression settings**: Fine-grained control over output quality and file size

### (Beta) Editor (Works with Extractor only for now)

Edit and combine animations prior to extraction. 

Currently only works with Extraction tool and is in very early beta, feedback on GUI and workflow is appreciated. Will support Generator tool in the future.

-   🟨 **Interactive alignment canvas**: Drag-and-drop sprite positioning with real-time preview
-   🟨 **Ghost overlay**: Semi-transparent reference frame for precise alignment comparisons
-   🟨 **Zoom and pan controls**: Mouse wheel zoom, viewport panning, and preset zoom levels
-   🟨 **Grid snapping**: Configurable snap-to-grid for consistent positioning
-   🟨 **Origin modes**: Choose between centered or top-left (FlxSprite) coordinate systems
-   🟨 **Keyboard fine-tuning**: Arrow keys for pixel-perfect adjustments (Shift for 5px steps)
-   🟨 **Multi-animation support**: Load and edit multiple animations simultaneously
-   🟨 **Combine animations**: Merge selected animations into composite entries for group alignment
-   🟨 **Detachable canvas**: Pop out the editor canvas into a separate window
-   🟨 **FNF offset import**: Import Friday Night Funkin' character offset data
-   🟨 **Save alignment overrides**: Apply alignment changes back to the extractor

### General

-   ✅ **Auto-update system**: Automatic checking and installation of updates
-   ✅ **Persistent settings**: Configuration saved between sessions

(*) = *Feature may have inconsistent results or is not fully stable yet\*

## Supported Formats

### Extraction

| Format                  | Extension            | Status    | Notes                                 |
| ----------------------- | -------------------- | --------- | ------------------------------------- |
| **Starling/Sparrow**    | `.xml`               | ✅ Stable | Standard XML atlas format             |
| **TexturePacker XML**   | `.xml`               | ✅ Stable | Generic `<sprite>` element format     |
| **TexturePacker Unity** | `.tpsheet`           | ✅ Stable | Semicolon-delimited Unity export      |
| **JSON Hash**           | `.json`              | ✅ Stable | Frames as key-value mapping           |
| **JSON Array**          | `.json`              | ✅ Stable | Frames as array with filenames        |
| **Aseprite**            | `.json`              | ✅ Stable | Full frame tag and duration support   |
| **Phaser 3**            | `.json`              | ✅ Stable | `textures[].frames[]` schema          |
| **Egret2D**             | `.json`              | ✅ Stable | Simple x/y/w/h schema                 |
| **Plist (Cocos2d)**     | `.plist`             | ✅ Stable | Apple/TexturePacker plist format      |
| **UIKit Plist**         | `.plist`             | ✅ Stable | Scalar frame keys format              |
| **Spine Atlas**         | `.atlas`             | ✅ Stable | Spine runtime text format             |
| **Godot Atlas**         | `.tpsheet`, `.tpset` | ✅ Stable | Godot texture atlas JSON              |
| **Paper2D (Unreal)**    | `.paper2dsprites`    | ✅ Stable | Unreal Engine sprite format           |
| **CSS Spritesheet**     | `.css`               | ✅ Stable | CSS sprite definitions                |
| **Packer TXT**          | `.txt`               | ✅ Stable | `name = x y w h` format               |
| **Adobe Spritemap**     | `.json`              | 🟨 Beta   | Adobe Animate/Adobe Flash Pro formats |
| **Unknown/Fallback**    | _any image_          | 🟨 Beta   | Computer vision sprite detection      |

### Generation

| Format                | Extension         | Description                 |
| --------------------- | ----------------- | --------------------------- |
| **Starling XML**      | `.xml`            | Sparrow/Starling compatible |
| **TexturePacker XML** | `.xml`            | Generic sprite XML          |
| **JSON Hash**         | `.json`           | Frames as key-value object  |
| **JSON Array**        | `.json`           | Frames as array             |
| **Aseprite JSON**     | `.json`           | Aseprite-compatible export  |
| **Phaser 3**          | `.json`           | Phaser game framework       |
| **Egret2D**           | `.json`           | Egret game engine           |
| **Plist**             | `.plist`          | Cocos2d/TexturePacker       |
| **UIKit Plist**       | `.plist`          | iOS UIKit format            |
| **Spine Atlas**       | `.atlas`          | Spine runtime               |
| **Godot**             | `.tpsheet`        | Godot Engine                |
| **Paper2D**           | `.paper2dsprites` | Unreal Engine               |
| **Unity**             | `.tpsheet`        | Unity TexturePacker         |
| **CSS**               | `.css`            | CSS sprite classes          |
| **TXT**               | `.txt`            | Simple text format          |

## Current Limitations

-   ⚠️ **False positive virus (Windows only)**: Some anti-virus software flags compiled Python code as malware. Read [this](https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/issues/20) for more info

## Planned Features

**Contributors are welcome to help implement the following features:**

-   Anything that improves the application.

-   🔄 **Command-line interface**: Full CLI support for automation and scripting
-   🖱️ **Drag & drop support**: Easier file loading interface
    _Note: Features mentioned above are planned for future versions and are not currently implemented._

## Installation and Usage

**Need help getting started?** Check out the documentation:

-   [📖 Installation Guide →](https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/wiki/Installation)
-   [📚 Full Documentation →](docs/README.md)

## Community Translations

Help localize the TextureAtlas Toolbox with our **Translation Editor** located in `tools/translator-app/`. The Qt-based helper offers placeholder-aware syntax highlighting, grouped context editing, validation, so you can translate `.ts` files quickly with near zero knowledge requirements!

Supports optional machine-translation providers from DeepL, Google Cloud Translate and LibreTranslate. (You need API keys or setup your own local LibreTranslate instance.)

-   Read the dedicated guide: [`tools/translator-app/README.md`](tools/translator-app/README.md)
-   Launch the packaged executable or run `python tools/translator-app/src/main.py` to start contributing translations.

## Official Download Sites

**_Note: Mac OSX and Linux users need to download source code from GitHub!_**

### SourceForge

[![Download TextureAtlas Extractor and GIF Generator](https://a.fsdn.com/con/app/sf-download-button)](https://sourceforge.net/projects/textureatlas-to-gif-and-frames/)

### Itch.io

[![Download TextureAtlas Extractor and GIF Generator Itchio](https://static.itch.io/images/badge-color.svg)](https://autisticlulu.itch.io/textureatlas-to-gif-and-frames)

### GameBanana

[![Download TextureAtlas Extractor and GIF Generator GB](https://gamebanana.com/tools/embeddables/16621?type=large)](https://gamebanana.com/tools/16621)

> ⚠️ **Security Notice**: Only download from official sources listed above. I'm are not responsible for any damage or issues caused by downloading from unofficial sites.

## Technical Information

This application uses [ImageMagick](https://imagemagick.org/) for advanced image processing capabilities. ImageMagick is a powerful, open-source software suite for image manipulation and conversion.

**Learn more about ImageMagick:**

-   [🌐 ImageMagick Website →](https://imagemagick.org/)
-   [📄 ImageMagick License →](https://imagemagick.org/script/license.php)

For Windows users, all necessary ImageMagick libraries are included with the release package.

## Support & Contributing

**Need help?**

-   [❓ FAQ →](docs/faq.md)
-   [📖 User Manual →](docs/user-manual.md)
-   [🐛 Report Issues →](https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/issues)

**Want to contribute?**

-   [👩‍💻 Developer Documentation →](docs/developer-docs.md)
-   [🔀 Submit Pull Requests →](https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/pulls)

---

## Special Thanks

-   Jsfasdf250
    -   For major contribution to the project.
-   Funkipedia Mods Wiki
    -   Members of their Discord server for supporting and using this tool. They are the biggest motivation force that makes me want to continue refining this tool.
-   PluieElectrique's [TextureAtlas Renderer](https://github.com/PluieElectrique/texture-atlas-renderer).
    -   Their code was referenced to bring Adobe TextureAtlas (Spritemap) support.
-   Wo1fseas's [PyTexturePacker](https://github.com/wo1fsea/PyTexturePacker)
    -   Their code was referenced to bring packing algorithms.

_Last updated: December 5, 2025 - Visit the [📚 Documentation →](docs/README.md) for more details_
