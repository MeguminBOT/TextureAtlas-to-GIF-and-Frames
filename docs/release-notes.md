# Release Notes

Version history and changelog for TextureAtlas to GIF and Frames.
**This doc file was partly written by AI, some parts may need to be rewritten which I will do whenever I have time**

## 📋 Current Version

### Version 1.9.4 (Current)
*Release Date: Latest*

#### 🚀 Features
- **Multi-engine FNF support**: Kade Engine, Psych Engine, and Codename Engine
- **Advanced animation controls**: FPS, delay, period, scaling, and frame selection
- **Multiple output formats**: GIF, WebP, APNG, and PNG frames
- **Intelligent cropping**: Animation-based, frame-based, and alpha-based options
- **Batch processing**: Process multiple animations and atlases simultaneously
- **Customizable filename patterns**: Template system with find/replace rules
- **Preview functionality**: Real-time GIF preview with playback controls
- **Persistent configuration**: Application settings saved between sessions

#### 🔧 Technical Details
- **Python 3.10+ support**: Compatible with modern Python versions
- **ImageMagick integration**: Advanced image processing and optimization
- **Automatic dependency checking**: Built-in installation guidance
- **Memory optimization**: Efficient handling of large texture atlases
- **Multi-threading**: Parallel processing for improved performance

---

## 📚 Version History

### Version 1.9.x Series - Advanced Features

#### Version 1.9.3
- **Enhanced FNF support**: Improved character data loading
- **Performance optimizations**: Better memory management for large atlases
- **Bug fixes**: Resolved issues with specific XML formats
- **UI improvements**: Better progress reporting and error messages

#### Version 1.9.2  
- **WebP export support**: Modern web-compatible animation format
- **Advanced cropping options**: Multiple cropping strategies
- **Settings management**: Per-animation and per-spritesheet overrides
- **Preview window**: Interactive animation preview with frame scrubbing

#### Version 1.9.1
- **Batch processing**: Process multiple animations simultaneously
- **Find/replace rules**: Filename transformation system
- **Configuration persistence**: Settings saved between sessions
- **Error handling improvements**: Better user feedback and recovery

#### Version 1.9.0
- **Major architecture rewrite**: Modular codebase for better maintainability
- **FNF engine detection**: Automatic detection of Kade/Psych/Codename formats
- **Advanced animation controls**: Period, variable delay, frame selection
- **GUI overhaul**: Modern interface with improved usability

### Version 1.8.x Series - Stability and Polish

#### Version 1.8.5
- **Stability improvements**: Fixed crashes with large atlases
- **Memory optimization**: Reduced RAM usage during processing
- **Export quality**: Better GIF optimization and color handling
- **Documentation**: Comprehensive user manual and help system

#### Version 1.8.4
- **Friday Night Funkin' support**: Initial FNF character integration
- **Animation looping**: Configurable loop settings and delays
- **Scale options**: Resize output with quality interpolation
- **Progress tracking**: Real-time progress bars and status updates

#### Version 1.8.3
- **Alpha threshold**: Transparency-based cropping control
- **Frame selection**: Custom frame ranges and duplicate removal
- **Performance**: Faster processing with optimized algorithms
- **Bug fixes**: Resolved XML parsing edge cases

#### Version 1.8.2
- **APNG support**: High-quality animation export format
- **Cropping system**: Automatic transparent border removal
- **Settings persistence**: Remember user preferences
- **UI polish**: Improved layout and visual feedback

#### Version 1.8.1
- **Multi-format support**: XML (Starling) and TXT (TextPacker)
- **Batch operations**: Process multiple spritesheets
- **Quality improvements**: Better GIF optimization
- **Error handling**: Graceful failure and user guidance

#### Version 1.8.0
- **Complete rewrite**: Modern Python architecture
- **GUI interface**: User-friendly Tkinter application
- **Animation export**: GIF generation with timing controls
- **Extensible design**: Support for future format additions

### Version 1.7.x Series - Foundation

#### Version 1.7.x
- **Initial release**: Basic sprite extraction functionality
- **XML parsing**: Starling format support
- **PNG export**: Individual frame extraction
- **Command-line interface**: Script-based operation

---

## 🔮 Planned Features

### Version 2.0.0 (Future Major Release)
- **Command-line interface**: Full CLI for automation and scripting
- **Plugin system**: Third-party extension support
- **Additional formats**: More texture atlas and export formats
- **Cloud integration**: Direct export to cloud storage services
- **Performance improvements**: Multi-core optimization and GPU acceleration

### Near-term Improvements
- **Drag & drop support**: Easier file loading
- **Undo/redo system**: Reversible operations
- **Preset management**: Save and load configuration presets
- **Advanced filtering**: Search and filter animations
- **Sprite sheet creation**: Reverse operation - create atlases from frames

---

## 🐛 Known Issues

### Current Limitations
- **Large file handling**: Very large atlases (>4GB) may cause memory issues
- **Complex XML**: Some non-standard XML variants not fully supported
- **Platform differences**: Minor UI differences between operating systems
- **Preview performance**: Large animations may preview slowly

### Workarounds
- **Memory issues**: Process animations individually for large atlases
- **XML compatibility**: Convert to standard Starling format if needed
- **Performance**: Use lower scale for previews, full scale for final export

---

## 🔄 Update Process

### Automatic Updates
1. **Update checker**: Runs automatically on application startup
2. **Notification**: Dialog appears when new version is available
3. **Download**: Click "Yes" to open GitHub releases page
4. **Manual installation**: Download and extract new version

### Manual Updates
1. **Download**: Get latest release from GitHub
2. **Backup settings**: Keep your `app_config.cfg` file
3. **Replace files**: Extract new version over old installation
4. **Verify**: Run application to confirm successful update

### Settings Migration
- **Preserved**: User settings and configurations
- **Reset if needed**: Delete `app_config.cfg` to reset to defaults
- **Compatibility**: Settings format maintained across versions

---

## 📝 Development Notes

### Version Numbering
- **Major.Minor.Patch**: Semantic versioning system
- **Major**: Breaking changes or significant rewrites
- **Minor**: New features and enhancements
- **Patch**: Bug fixes and small improvements

### Release Cycle
- **Regular updates**: Monthly minor releases when possible
- **Patch releases**: As needed for critical bug fixes
- **Major releases**: Annual or bi-annual for significant changes

### Testing Process
- **Automated testing**: Unit tests for core functionality
- **Manual testing**: GUI and integration testing
- **Community feedback**: Beta testing with active users
- **Compatibility testing**: Multiple Python versions and operating systems

---

## 🤝 Contributing

### How to Contribute
- **Bug reports**: Submit issues on GitHub with detailed information
- **Feature requests**: Suggest improvements through GitHub issues
- **Code contributions**: Fork, develop, and submit pull requests
- **Documentation**: Help improve guides and documentation

### Development Setup
See [Developer Documentation](developer-docs.md) for detailed setup instructions.

---

*For installation instructions, see the [Installation Guide](installation-guide.md). For usage help, check the [User Manual](user-manual.md).*
