# Installation Guide

This guide will walk you through manually installing and setting up TextureAtlas-to-GIF-and-Frames on your system from source code.
**This doc file was partly written by AI, some parts may need to be rewritten which I will do whenever I have time**

## 📋 System Requirements

- **Operating System**: Windows 7/8/10/11, macOS 10.12+, or Linux
- **Python**: Version 3.10 or higher
- **RAM**: 2GB minimum (4GB+ recommended for large atlases)
- **Storage**: 100MB for application + space for output files

## 🐍 Python Installation

### Windows
1. Download Python from [python.org](https://www.python.org/downloads/)
2. **Important**: Check "Add Python to PATH" during installation
3. Verify installation by opening Command Prompt and typing:
   ```cmd
   python --version
   ```

### macOS
```bash
# Using Homebrew (recommended)
brew install python

# Or download from python.org
```

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install python3 python3-pip
```

## 📦 Installing Python Dependencies

The application requires several Python packages. Install them using pip:

```bash
pip install pillow wand numpy tkinter requests
```

### Package Details
- **Pillow (PIL)**: Image processing and manipulation
- **Wand**: Python binding for ImageMagick
- **NumPy**: Numerical operations for image arrays
- **Tkinter**: GUI framework (usually included with Python)
- **Requests**: HTTP library for update checking

## 🎨 ImageMagick Setup

ImageMagick is required for advanced image processing and GIF optimization.

### Windows

#### Option 1: Automatic Setup (Recommended)
The application includes automatic ImageMagick detection and will prompt you to download it if not found.

#### Option 2: Manual Installation
1. Download ImageMagick from [imagemagick.org](https://imagemagick.org/script/download.php#windows)
2. Choose the version matching your system (32-bit or 64-bit)
3. Run the installer and follow the setup wizard
4. **Important**: Ensure "Install development headers and libraries for C and C++" is checked

### macOS
```bash
# Using Homebrew
brew install imagemagick

# Using MacPorts
sudo port install ImageMagick
```

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install imagemagick libmagickwand-dev
```

### Linux (CentOS/RHEL/Fedora)
```bash
# CentOS/RHEL
sudo yum install ImageMagick ImageMagick-devel

# Fedora
sudo dnf install ImageMagick ImageMagick-devel
```

## 📥 Downloading the Application

### Option 1: Download Release (Recommended for Users)
1. Visit the [GitHub Releases page](https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/releases)
2. Download the latest release ZIP file
3. Extract to your desired location

### Option 2: Clone Repository (For Developers)
```bash
git clone https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames.git
cd TextureAtlas-to-GIF-and-Frames
```

## 🚀 Running the Application

1. Navigate to the application directory
2. Open a terminal/command prompt in the `src` folder
3. Run the application:
   ```bash
   python Main.py
   ```

### Alternative Methods

#### Windows
- Double-click `Main.py` if Python is properly associated
- Create a batch file with: `python Main.py`

#### macOS/Linux
- Make the file executable: `chmod +x Main.py`
- Run directly: `./Main.py` (if shebang is added)

## 🔧 Troubleshooting Installation

### Common Issues

#### "Python is not recognized"
- **Solution**: Add Python to your system PATH
- **Windows**: Reinstall Python with "Add to PATH" checked
- **macOS/Linux**: Add Python directory to your `.bashrc` or `.zshrc`

#### "No module named 'PIL'"
```bash
pip install Pillow
# If that fails, try:
pip install --upgrade Pillow
```

#### "ImportError: MagickWand shared library not found"
- **Windows**: Reinstall ImageMagick or use bundled version
- **macOS**: `brew reinstall imagemagick`
- **Linux**: `sudo apt install libmagickwand-dev`

#### "tkinter not found" (Linux)
```bash
# Ubuntu/Debian
sudo apt install python3-tk

# CentOS/RHEL
sudo yum install tk-devel

# Fedora
sudo dnf install tkinter
```

### Performance Issues

#### Large Memory Usage
- Close other applications when processing large atlases
- Consider processing animations one at a time
- Use lower scale settings for very large sprites

#### Slow Processing
- Ensure ImageMagick is properly installed
- Consider using SSD storage for temporary files
- Check that antivirus isn't interfering with file operations

## ✅ Verifying Installation

To verify everything is working correctly:

1. **Start the application**:
   ```bash
   cd src
   python Main.py
   ```

2. **Check for error messages** in the console

3. **Test basic functionality**:
   - The GUI should open without errors
   - Help menu should be accessible
   - Settings windows should open properly

4. **Test ImageMagick integration**:
   - Try loading a sample texture atlas
   - Attempt to export a simple animation
   - Check that GIF optimization works

## 🔄 Updating the Application

The application includes an automatic update checker that runs on startup. When updates are available:

1. You'll see a notification dialog
2. Click "Yes" to open the releases page
3. Download and extract the new version
4. Your settings and configurations are preserved

### Manual Updates
1. Download the latest release
2. Replace the old files with new ones
3. Keep your `app_config.cfg` file to preserve settings

## 🎯 Next Steps

Once installation is complete:
1. Read the [User Manual](user-manual.md) for detailed usage instructions
2. Check out the [Friday Night Funkin' Guide](fnf-guide.md) if working with FNF sprites
3. Explore the advanced settings and customization options

---

*Need help? Check the [FAQ](faq.md) or visit our [GitHub Issues](https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/issues) page.*
