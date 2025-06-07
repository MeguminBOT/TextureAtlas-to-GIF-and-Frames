# Frequently Asked Questions (FAQ)

Common questions and solutions for TextureAtlas to GIF and Frames users.
**This doc file was partly written by AI, some parts may need to be rewritten which I will do whenever I have time**

## 📋 Table of Contents

- [Installation Issues](#installation-issues)
- [File Format Questions](#file-format-questions)
- [Export Problems](#export-problems)
- [Performance Issues](#performance-issues)
- [Friday Night Funkin' Questions](#friday-night-funkin-questions)
- [Advanced Usage](#advanced-usage)
- [Troubleshooting](#troubleshooting)

## 🔧 Installation Issues (Not applicable for .exe file)

### Q: "Python is not recognized as an internal or external command"
**A:** Python is not added to your system PATH.
- **Windows**: Reinstall Python and check "Add Python to PATH" during installation
- **Alternative**: Add Python manually to your system environment variables
- **Test**: Open Command Prompt and type `python --version`

### Q: "No module named 'PIL'" or similar import errors
**A:** Required Python packages are not installed.
```bash
pip install pillow wand numpy requests

# If pip is not found:
python -m pip install pillow wand numpy requests
```

### Q: "ImportError: MagickWand shared library not found"
**A:** ImageMagick is not properly installed or configured.
- **Windows**: Verify the ImageMagick folder exists in your downloaded source otherwise manually download and install from [imagemagick.org](https://imagemagick.org/script/download.php#windows)
- **macOS**: `brew install imagemagick`
- **Linux**: `sudo apt install imagemagick libmagickwand-dev`

### Q: Application won't start or crashes immediately
**A:** Check these common issues:
1. **Python version**: Ensure you have Python 3.10 or higher
2. **Dependencies**: Install all required packages
3. **File permissions**: Ensure you can read/write in the application directory
4. **Antivirus**: Check if antivirus is blocking the application

## 📄 File Format Questions

### Q: What texture atlas formats are supported?
**A:** Input formats:
- **Images**: PNG
- **Metadata**: XML (Starling/Sparrow), TXT (TextPacker)
- **FNF Data**: JSON or XML files from Kade Engine, Psych Engine, Codename Engine

### Q: My Sparrow/Starling XML file isn't loading properly 
**A:** Check these requirements:
- XML must be properly formatted.
- Root element should be `<TextureAtlas>`
- SubTexture elements need `name`, `x`, `y`, `width`, `height` attributes

### Q: What about TexturePacker files?
**A:** Supported formats from TexturePacker:
- **XML**: Starling/Sparrow format (recommended)
- **TXT**: Generic text format

## 📤 Export Problems

### Q: Exported GIFs are too large
**A:** Try these optimization strategies if they're not important for your end result:
- **Reduce scale**: Use 0.5 or 0.75 instead of 1.0
- **Lower FPS**

### Q: Some frames are missing from my animation
**A:** Check these settings:
- **Alpha threshold**: Lower value to include transparent frames
- **Atlas data file**: Verify all frames are properly defined

### Q: Exported frames have wrong dimensions
**A:** Review cropping settings:
- **No crop**: Maintains original atlas dimensions
- **Frame-based**: Crops each frame individually (Only applied to PNGs).
- **Animation-based**: Consistent crop across all frames

### Q: Output files are not where I expected
**A:** Check output directory settings:
- Files are organized by animation name in subfolders
- Frames go in `animation_name_frames/` subdirectory
- Animations save as `animation_name.gif/webp/png`

## ⚡ Performance Issues

### Q: Application is very slow with large atlases
**A:** Optimization strategies:
- **Process fewer animations**: Don't batch process everything at once
- **Close other applications**: Free up system memory
- **Use SSD storage**: Faster disk access for temporary files

### Q: Running out of memory during processing
**A:** Memory management tips:
- **Reduce amount of CPU Threads**: More CPU threads results more images being processed which in return results in more memory usage.
- **Reduce image scale**: Lower memory usage per frame
- **Close preview windows**: They consume memory

### Q: Export is taking forever
**A:** Speed improvements:
- **Disable antivirus scanning**: Temporarily for the output directory
- **Use local storage**: Network drives are slower
- **Reduce amount of CPU Threads**: Directly impact how much RAM is being used. More doesn't necessarily mean faster if you run out of memory.

## 🎵 Friday Night Funkin' Questions
### Q: FNF character data isn't loading
**A:** Verify these requirements:
- Character data file is valid and properly formatted
- Image path in JSON/XML matches your atlas file
- JSON/XML follows engine-specific format (Kade/Psych/Codename)

### Q: Animation speeds don't match the game (Primarily GIFs)
**A:** Reason:
- GIFs don't support decimal numbers in their frame delays, so they're getting rounded to the closest whole number. 
This tool uses a generic FPS value which then is converted to the duration it would be in MS, let's say you set your export to "24 FPS", this results in a frame delay value "41.66666" this get's rounded up to "42".


## 🔧 Advanced Usage

### Q: How do I create custom filename patterns?
**A:** Use template variables:
- `{sprite_name}`: Original sprite name
- `{animation_name}`: Animation identifier
- `{frame_number}`: Frame index
- `{prefix}`: Custom prefix text
- Example: `{prefix}_{animation_name}_frame_{frame_number:03d}.png`

### Q: Can I automate batch processing?
**A:** Current automation options:
- **Select multiple**: Use Ctrl+click to select multiple animations
- **Process all**: Extract all animations from loaded atlas
- **Settings persistence**: Configure once, apply to all
- **Future**: Command-line interface planned for full automation

### Q: How do I handle very large sprite collections?
**A:** Large collection strategies:
- **Process in batches**: Don't load everything at once
- **Use consistent settings**: Set up defaults for efficiency
- **Organize output**: Plan directory structure in advance
- **Monitor resources**: Watch memory and disk usage

### Q: Can I extend the tool with new formats?
**A:** Yes, the tool is designed for extensibility:
- See [Developer Documentation](developer-docs.md) for API details
- Add new parsers for custom metadata formats
- Implement new export formats
- Contribute back to the project

## 🐛 Troubleshooting

### Q: Application freezes during export
**A:** Potential causes and solutions:
- **Large atlas**: Try smaller test files first
- **Memory shortage**: Close other applications
- **Corrupted data**: Verify atlas and metadata files

### Q: Error: "XML frame dimension data doesn't match"
**A:** Common solutions:
- **Alpha threshold**: Lower the transparency threshold
- **Atlas size**: Verify atlas dimensions match metadata
- **Coordinate system**: Check if coordinates are within image bounds
- **File corruption**: Try re-exporting the atlas

### Q: Preview window shows black/empty frames
**A:** Preview troubleshooting:
- **Alpha channel**: Frames may be fully transparent
- **Scale setting**: Try different scale values
- **Cropping**: Disable cropping to see full frames
- **Metadata**: Verify frame coordinates are correct

### Q: Find/Replace rules not working
**A:** Rule configuration:
- **Regex enabled**: Check if regex checkbox is properly set
- **Pattern syntax**: Verify regex patterns are valid
- **Case sensitivity**: Rules are case-sensitive by default
- **Order matters**: Rules are applied in sequence

### Q: Settings aren't saving
**A:** Settings persistence:
- **File permissions**: Ensure write access to config directory
- **Path issues**: Check that config file path is valid
- **Manual save**: Try closing and reopening application
- **Reset config**: Delete `app_config.cfg` to reset

### Q: Updates not working
**A:** Update process:
- **Internet connection**: Required for update checking
- **Manual download**: Get latest version from GitHub releases
- **File replacement**: Replace all files except config
- **Settings preservation**: `app_config.cfg` preserves your settings

## 📞 Getting More Help

### Still having issues?

1. **Check logs**: Look for error messages in the console window if you're running the tool directly as a python script.
2. **Try minimal example**: Test with a simple, small atlas
3. **Update software**: Ensure you have the latest version
4. **System check**: Verify all dependencies are properly installed

### Reporting bugs:

1. **GitHub Issues**: [Report bugs here](https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/issues)
2. **Include details**: Error messages, file examples, system info
3. **Steps to reproduce**: Detailed instructions to recreate the issue
4. **Screenshots**: Visual problems benefit from screenshots

### Community support:

- **Documentation**: Check [User Manual](user-manual.md) for detailed instructions
- **FNF specific**: See [Friday Night Funkin' Guide](fnf-guide.md)
- **Development**: Review [Developer Documentation](developer-docs.md)

---

*Can't find your answer? Open an issue on [GitHub](https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/issues) with your question.*
