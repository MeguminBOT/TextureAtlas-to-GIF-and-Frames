# 🎨 TextureAtlas to GIF and Frames

**A powerful, free and open-source tool for extracting frames and animations from Texture Atlases**

[TextureAtlas to GIF and Frames](https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames) converts texture atlases into organized frame collections and GIF/WebP/APNG animations. 
Perfect for creating showcases and galleries of game sprites.

📄 **Licensed under [AGPL-3.0](https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/blob/main/LICENSE)**

## 📋 Quick Navigation

- [🚀 Quick Start](#-quick-start)
- [📦 Supported Formats](#-supported-spritesheet-types)
- [✨ Features](#-features)
- [⚠️ Current Limitations](#️-current-limitations)
- [🔮 Planned Features](#-planned-features)
- [💾 Downloads](#-official-download-sites)
- [📖 Documentation](docs/README.md)

## 🚀 Quick Start

1. **Download** from [official sources](#-official-download-sites)
2. **Install** following the [Installation Guide](https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/wiki/Installation)
3. **Load** your texture atlas and metadata file
4. **Configure** animation settings
5. **Extract** and enjoy your animations!

## 📦 Supported Spritesheet Types

- ✅ **Sparrow** (XML format)
- ✅ **Starling** (XML format)  
- ✅ **Packer TXT** (TXT format)
- 🟨 (/) **Adobe TextureAtlas/Spritemaps** (JSON format) *[NOTE: Only working on "Optimized" spritemap exports and needs more testing before being marked as stable]*
- 🟨 (/) **Unknown/Unsupported** (Attempts to extract sprites despite missing official support)

(/) = *Feature may have bad results or are not fully stable yet*

## ✨ Features

- ✅ **Multiple output formats**: GIF, WebP, APNG animations + individual frames (PNG, WebP, AVIF, BMP, DDS, TGA, TIFF)
- ✅ **Batch processing**: Extract multiple animations and spritesheets simultaneously
- ✅ **Automatic sprite detection**: Process image files without metadata using intelligent boundary detection
- ✅ **Organized** Sort frames from spritesheets into individual folders.
- ✅ **Advanced controls**: Customizable frame rate, loop delay, scale, frame selection, and alpha transparency threshold
- ✅ **Compression control**: Lossless and lossy compression methods.
- ✅ **Smart cropping**: Animation-based and frame-based cropping options
- ✅ **Find/Replace rules**: Customize output filenames with pattern matching
- ✅ **Auto-update system**: Automatic checking and installation of updates
- ✅ **Persistent settings**: Configuration saved between sessions
- ✅ (*) **Preview system**: Real-time GIF preview with playback controls
- ✅ (*) **Friday Night Funkin' character data**: Import character data files from various FNF engines to set correct animation settings

(*) = *Feature may have bad results or are not fully stable yet*

## ⚠️ Current Limitations

- ⚠️ **Input image format**: Currently supports PNG texture atlases only
- ⚠️ **Static thread and memory usage**: Currently uses the resources you tell it to without any dynamic managing of system resources.
- ⚠️ **False positive virus (Windows only)**: Some anti-virus software flags compiled Python code as malware. Read [this](https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/issues/20) for more info

## 🔮 Planned Features

**Contributors are welcome to help implement the following features:**
- 📚 **QT graphical interface**: Swapping to QT based UI. (Repo maintainer will do the initial work in a branch named "QT", afterwards any help is welcome) 
- 🔄 **Command-line interface**: Full CLI support for automation and scripting
- 🖼️ **Additional input formats**: Support for more image formats beyond PNG
- 🖱️ **Drag & drop support**: Easier file loading interface
- 🔌 **Custom FFMPEG output**: Custom output formats through FFMPEG
- ⚡ **Enhanced memory management**: Dynamic memory limits and optimization

*Note: Features mentioned above are planned for future versions and are not currently implemented.*

## 📚 Installation and Usage

**Need help getting started?** Check out the documentation:
- [📖 Installation Guide →](https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/wiki/Installation)
- [📚 Full Documentation →](docs/README.md)

## 💾 Official Download Sites
***Note: Mac OSX and Linux users need to download source code from GitHub!***
### 🔗 SourceForge
[![Download TextureAtlas Extractor and GIF Generator](https://a.fsdn.com/con/app/sf-download-button)](https://sourceforge.net/projects/textureatlas-to-gif-and-frames/)

### Itch.io
[![Download TextureAtlas Extractor and GIF Generator Itchio](https://static.itch.io/images/badge-color.svg)](https://autisticlulu.itch.io/textureatlas-to-gif-and-frames)

### 🎮 GameBanana
[![Download TextureAtlas Extractor and GIF Generator GB](https://gamebanana.com/tools/embeddables/16621?type=large)](https://gamebanana.com/tools/16621)

> ⚠️ **Security Notice**: Only download from official sources listed above. I'm are not responsible for any damage or issues caused by downloading from unofficial sites.

## 🔧 Technical Information

This application uses [ImageMagick](https://imagemagick.org/) for advanced image processing capabilities. ImageMagick is a powerful, open-source software suite for image manipulation and conversion.

**Learn more about ImageMagick:**
- [🌐 ImageMagick Website →](https://imagemagick.org/)
- [📄 ImageMagick License →](https://imagemagick.org/script/license.php)

For Windows users, all necessary ImageMagick libraries are included with the release package.

## 📞 Support & Contributing

**Need help?**
- [❓ FAQ →](docs/faq.md)
- [📖 User Manual →](docs/user-manual.md)
- [🐛 Report Issues →](https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/issues)

**Want to contribute?**
- [👩‍💻 Developer Documentation →](docs/developer-docs.md)
- [🔀 Submit Pull Requests →](https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/pulls)

---
## Special Thanks
- Jsfasdf250
    - For major contribution to the project.
- PluieElectrique's [TextureAtlas Renderer](https://github.com/PluieElectrique/texture-atlas-renderer). 
    - Parts of their code was used to bring Adobe TextureAtlas (Spritemap) support.
- Funkipedia Mods Wiki
    - Members of their Discord server for supporting and using this tool. They are the biggest motivation force that makes me want to continue refining this tool.



*Last updated: June 23, 2025 - Visit the [📚 Documentation →](docs/README.md) for more details*
