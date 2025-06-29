# Release Notes

## 🗂️ Table of Contents (Major Versions)

- [Version 1.9.x](#version-19x)
- [Version 1.8.x](#version-18x)
- [Version 1.7.x](#version-17x)
- [Version 1.6.x](#version-16x)
- [Version 1.5.x](#version-15x)
- [Version 1.4.x](#version-14x)
- [Version 1.3.x](#version-13x)
- [Version 1.2.x](#version-12x)
- [Version 1.1.x](#version-11x)
- [Version 1.0.x](#version-10x)
- [Planned Features (2.0.0)](#future-development)

---

Version history and changelog for TextureAtlas to GIF and Frames.


## 📋 Current Version

### Version 1.9.5 (Current)
Release date: **Not released yet**

---

## 📚 Version History

### Version 1.9.x

#### Version 1.9.5
- Bugfix: **Start process button can no longer be pressed if there's an extraction already started**
- Bugfix: **CPU Thread amount is now properly using the value from AppConfig**
- Enhancement: **Debug console can now be shown for .exe releases if started through Command Prompt / PowerShell**
- Enhancement: **Added support for AVIF, BMP, DDS, TGA and TIFF for frame exporting**
- Enhancement: **Extraction settings are now greyed out if it's unneeded or a format not supporting that specific setting**
- Feature: **Added compression settings for frame exporting.**
- Feature: **Attempt to extract unsupported spritesheets**
    - *App can now in **theory** extract any spritesheet type despite not officially supporting them*
    - *Background keying for non transparent images*
    - *Warns if unsupported spritesheet is detected*
    - *Warns if non transparent background is detected*
    - *NOTE: This feature only supports exporting as frames and not animations due to limitations*
- Feature: **Added support for tooltips**
    - *Currently only implemented on compression settings*
- Feature/Tweak: **Update system overhaul**
    - *Show changelog on update notifications*
    - *App can now download updates and replace itself*
    - *Check for updates button in Menubar > Options*
    - *Log update process to a logs folder*
- Feature: **App configuration menu**: 
    - *Modify default extraction settings*
    - *Modify processing threads*
    - *Toggle Automatic update checks*
    - *Toggle Automatically install new updates*
    - *Automatic config file migration between versions*
- Tweak: **Updated in-app help menu**
    - *Added missing option descriptions and the new ones**
    - *FNF Settings advice updated*
- Misc: **Contributors Menu**
- Misc: **New app icon by [Julnz](https://www.julnz.com/)**
  

#### Version 1.9.4
- Bugfix: **Fixed "Invalid Palette Size" error for good by swapping GIF generation to Wand**
- Enhancement: **Improve single frame handling, clear spritesheet settings along with user settings**
- Feature: **Deleting spritesheets from the list by right clicking is now possible**.
- Feature: **Custom filename formats**
- Feature: **Make animation cropping optional, add find and replace feature**
- Feature: **Preview GIFs from Override settings window.**
- Feature: **Filename formatting presets.**

#### Version 1.9.3
- Feature: **Different crop methods for png frames depending on your needs. Defaults to cropping based on animation bounding box.**
- Bugfix: **Fix bug causing user_settings not being applied correctly.**
- Bugfix: **Fix bug involving animations with transparency, all shades of gray and no other colors. (Should solve most gray/black/white spritesheets having problems) Still minor issues on some sprites.**

#### Version 1.9.2  
- Enhancement: **User settings list is now scrollable**
- Enhancement: **User settings no longer show "NONE" values.**
- Bugfix: **Setting scale to 0 actually raises an error** 
- Bugfix: **Blank animations no longer prevents remaining animations from being processed.**
- Bugfix: **Fix GIFs being blank when using HQ color mode on grayscale spritesheets and spritesheets with low color data.**

#### Version 1.9.1
- Tweak: **Crop individual frames is no longer automatic, added a checkbox to let users decide**
- Tweak: **Default Minimum Duration changed from 500 to 0**
- Bugfix: **Fix spritesheet_settings not being cleared for a specific sheet**
- Bugfix: **Windows users with ImageMagick already installed had an issue where the paths clashed, now we're checking if it's already in path**

#### Version 1.9.0
- Enhancement: **Crop individual frames**
- Enhancement: **Frames are only saved when necessary**
- Enhancement: **User settings are only accessed when necessary**
- Enhancement: **Single-frame animations are saved as PNG, no matter what**
- Enhancement: **Instead of being all-or-nothing, specific frames can be chosen to be saved**
- Enhancement: **Use Wand/ImageMagick to achieve better color quality for GIFs, can be turned on under the 'Advanced' tab in the app.**
- Feature: **Advanced delay option: vary some frame delays slightly for more accurate fps, can be turned on under the 'Advanced' tab in the app**
- Feature: **Resize frames and animations, with an option to flip by using negative numbers**
- Experimental Feature: **Set total animation duration to be at least a certain value*- (Not sure if this will be necessary to use at all but w/e)


### Version 1.8.x

#### Version 1.8.1
- Enhancement: **Shows time processed, gif and frames generated**
- Bugfix: **Fixed GIF/WebPs not using correct frame order if the spritesheets xml is unsorted (Like when using Free Packer Tool)**

#### Version 1.8.0
- Feature: **(FNF Specific): Import character animation fps from character json files. Located within the "import" menu**
- Feature: **Support for spritesheets using txt packer (Like Spirit in FNF)**
- Feature: **You can now select individual spritesheets instead of directories. Located within the "file" menu**
- Feature: **Help and advice on the application. Located within the "help" menu**
- Bugfix: **Force all cpu threads now work as intended**
- Bugfix: **Fix cropping for sprites that end up having an empty frame after threshold is applied*- _(does not work for all sprites)_


### Version 1.7.x

#### Version 1.7.1
- Improvement: **If Alpha threshold is set to 1, keep all fully-opaque pixels**
- Improvement: **Alpha threshold is set between 0 and 1 inclusive**
- Bugfix/Improvement: **Frame dimensions are enlarged to hold the entire sprite when necessary, like rotated sprites.**
- Improvement: **Apply Alpha threshold before cropping on GIFs**
- Improvement: **Throw an error when sprite dimensions don't match xml data**
- Bugfix: **Windows .exe having errors**

#### Version 1.7.0
- Feature: **GIFs now automatically gets trimmed/cropped.**
- Feature: **Force max CPU threads**

### Version 1.6.x

#### Version 1.6.0
- Feature: **Indices option (individual animations only) formatted as CSV**
- Feature: **Option to remove png frames**
- Feature: **Show User Settings button.**
- Enhancement: **Allow local settings to be reset to global settings by entering blank values in the popup dialog**
- Enhancement: **Fps now accepts non-integer values**
- Adjustment: **Delay option adds to the final frame duration**
- Adjustment: **Animation names are now in the form of [spritesheet name] [animation name]**
- Bugfix: **Progress bar considers xml files instead of png files**
- Bugfix: **Non-positive width/height no longer trigger errors**
- Bugfix: **Changing the input directory now resets the user settings**
- Bugfix: **Png files without corresponding xml files no longer cause a crash**


### Version 1.5.x

#### Version 1.5.0
- Bugfix: Fix crash when an animation has different size frames
- Bugfix: Fix animations of the same name from different spritesheets not having their settings set independently
- Add threshold option for handling semi-transparent pixels
- Improve handling of some XMLs with unusual SubTexture names, such as those with ".png" suffix or more than 4 digits at the end


### Version 1.4.x

#### Version 1.4.1
- Bugfix: Now properly rounds the loop delay value. GIFs and WebPs should now always have the same loop delay (if not override is used of course)

#### Version 1.4.0
- Enhancement: Now processes multiple files at once (based on your CPU threads divided by two)
- Feature: Setting FPS and delay for individual animations is now possible through a scrollable filelist

```
Performance increase benchmark: 
Processing 106 spritesheets and generating GIFs on an AMD Ryzen 9 3900X and exporting to a regular hard drive.

v1.3.1: 377.82 seconds
v1.4.0: 52.55 seconds
```


### Version 1.3.x

#### Version 1.3.1
- Bugfix: Some spritesheets ended up making a "space" after the file name, this caused an error causing the script to not find the file and directory.
- Enhancement: Show error message when xml files are badly formatted and other errors.
- Enhancement: WebPs are now lossless.

#### Version 1.3.0
- Feature: Added support for framerate.
- Feature: Added support for loop delay.


### Version 1.2.x

#### Version 1.2.0
- Feature: Added support for exporting animated WebPs.
- Feature: Added Update notifications system added
- Enhancement: Frames of animations are now sorted into folders. GIFs/WebPs are now in the main folder of the extracted sprite.
- Enhancement: Now properly supports 'rotated' variable of some spritesheets.


### Version 1.1.x

#### Version 1.1.0
- Bugfix: Frame extraction now properly uses `frameX` / `frameY` / `frameWidth` / `frameHeight` if present in the XML files.
- Bugfix: No longer adds black background to transparent sprites
- Bugfix: GIFs are now properly aligned.


### Version 1.0.x

#### Version 1.0.0
- Initial Release
- Currently only takes folders as input and not individually selected sprites.

---

## 🔮 Planned Features

### Future Development
*Note: The following features are planned for future versions but are not currently implemented*

#### Version 2.0.0 (Future Major Release)
- **Command-line interface**: Full CLI for automation and scripting
- **Plugin system**: Third-party extension support
- **Additional input formats**: More texture atlas formats beyond PNG/XML/TXT
- **Enhanced memory management**: Dynamic memory limit controls
- **Performance improvements**: GPU acceleration and advanced optimization

#### Near-term Improvements
- **Drag & drop support**: Easier file loading through drag and drop
- **Undo/redo system**: Reversible operations for settings changes
- **Preset management**: Save and load configuration presets
- **Advanced filtering**: Search and filter animations
- **Extended image format support**: Support for additional input image formats

---

## 🐛 Known Issues

### Current Limitations
- **Large file handling**: Very large atlases (>4GB) may cause memory issues on systems with limited RAM
- **Complex XML variants**: Some non-standard XML formats may not be fully supported
- **Platform differences**: Minor UI differences between operating systems
- **Preview performance**: Large animations may preview slowly on older hardware
- **Memory limit controls**: Memory limit settings in preferences are not yet active (UI placeholder for future implementation)

### Workarounds
- **Memory issues**: Process animations individually for very large atlases
- **XML compatibility**: Convert to standard Starling/Sparrow format if needed
- **Performance**: Use lower scale settings for previews, full scale for final export
- **Complex animations**: Break down large animation sets into smaller batches

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


*Last updated: June 23, 2025 - Version 1.9.5 - Visit the [📚 Documentation →](docs/README.md) for more details*