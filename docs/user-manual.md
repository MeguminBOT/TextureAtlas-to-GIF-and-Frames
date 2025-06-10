# User Manual
General help with the application.
**This doc file was partly written by AI, some parts may need to be rewritten which I will do whenever I have time**
**This doc is also very incomplete**

## 📋 Table of Contents


## 🚀 Getting Started

## 🖥️ Interface Overview

### Main Window Components

#### File Selection Area
- **Atlas Image**: Browse button to select your texture atlas image file
- **Metadata File**: Browse button to select XML or TXT metadata file
- **Output Directory**: Choose where exported files will be saved

#### Sprite Lists
- **Left Listbox**: Shows all available PNG files/spritesheets
- **Right Listbox**: Shows animations for the selected spritesheet
- **Multi-select**: Hold Ctrl/Cmd to select multiple items

#### Control Panel
- **Extract Selected**: Export chosen animations
- **Extract All**: Export all animations from all spritesheets
- **Preview GIF**: Preview animation before export (when available)

#### Settings Area
- **FPS**: Animation frames per second
- **Animation Format**: Choose between GIF, WebP, APNG
- **Scale**: Resize output (0.5 = 50%, 2.0 = 200%)
- **Additional Options**: Access advanced settings via buttons

### Menu Bar

#### File Menu

#### Settings Menu

#### Tools Menu

#### Help Menu

## 📁 Loading Texture Atlases

### Supported Input Formats

#### Image Files

#### Metadata Files
- **XML (Starling/Sparrow)**: Most common format used by texture packers
- **TXT (TextPacker)**: Simple text-based format

### Loading Process

### Metadata File Examples

#### XML Format (Starling/Sparrow)
```xml
<TextureAtlas imagePath="spritesheet.png">
    <SubTexture name="character_idle_0001" x="0" y="0" width="64" height="64"/>
    <SubTexture name="character_idle_0002" x="64" y="0" width="64" height="64"/>
    <SubTexture name="character_walk_0001" x="0" y="64" width="64" height="64"/>
</TextureAtlas>
```

#### TXT Format (TextPacker)
```
character_idle_0001.png
xy: 0, 0
size: 64, 64
orig: 64, 64
offset: 0, 0

character_idle_0002.png
xy: 64, 0
size: 64, 64
orig: 64, 64
offset: 0, 0
```

## 🎬 Basic Animation Export

### Simple Export


### Output Structure
```
output_directory/
├── spritesheet_name/
│   ├── animation_name.gif
│   ├── animation_name_frames/
│   │   ├── frame_001.png
│   │   ├── frame_002.png
│   │   └── ...
│   └── ...
```

## ⚙️ Advanced Settings

### Animation Controls

#### Frame Selection

### Image Processing

#### Cropping Options
- **No Crop**: Keep original frame dimensions
- **Crop Alpha**: Remove transparent borders
- **Smart Crop**: Intelligent cropping based on content

#### Scaling and Quality


### Output Customization


#### Find/Replace Rules
Create rules to transform filenames:
- **Find**: Text pattern to match (supports regex)
- **Replace**: Replacement text
- **Apply to**: Filenames, animation names, or both

## 📄 Output Formats

### GIF Format
- **Best for**: Web compatibility, small file sizes
- **Features**: Transparency, animation, wide support
- **Limitations**: 256 colors maximum
- **Optimization**: Automatic frame deduplication and palette optimization

### WebP Format  
- **Best for**: Modern web applications, superior compression
- **Features**: True transparency, better compression than GIF
- **Limitations**: Limited browser support (mainly Chrome/Firefox)
- **Quality**: Lossless or lossy compression options

### APNG Format
- **Best for**: High-quality animations with full transparency
- **Features**: 24-bit color, alpha transparency, better than GIF
- **Limitations**: Limited software support
- **Use case**: When quality is more important than compatibility

### PNG Frames
- **Best for**: Manual editing, compositing, maximum quality
- **Features**: Lossless compression, full transparency
- **Use case**: When you need individual frames for remaking spritesheets or manual fixing without original source files

### Error Messages

#### "XML/TXT frame dimension data doesn't match"
- Atlas dimensions in metadata don't match actual image
- Try reducing alpha threshold
- Check for corrupted atlas file

## 💡 Tips and Best Practices

### Preparation
- **Organize your files**: Keep atlas and metadata in same directory
- **Name consistently**: Use clear, descriptive filenames

### Performance

---

*For additional help, see the [FAQ](faq.md) or [Friday Night Funkin' Guide](fnf-guide.md) for specialized workflows.*
