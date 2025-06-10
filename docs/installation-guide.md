# Installation Guide

This guide will walk you through manually installing and setting up TextureAtlas-to-GIF-and-Frames on your system from source code.
**This doc file was partly written by AI, some parts may need to be rewritten which I will do whenever I have time**

## 📑 Table of Contents

- [System Requirements](#-system-requirements)
  - [Minimum Requirements](#minimum-requirements)
  - [Recommended Requirements](#recommended-requirements)
- [Python Installation](#-python-installation)
  - [Windows](#windows)
  - [macOS](#macos)
  - [Linux (Ubuntu/Debian)](#linux-ubuntudebian)
- [Installing Python Dependencies](#-installing-python-dependencies)
  - [Using requirements.txt (Recommended)](#using-requirementstxt-recommended)
    - [Windows](#windows-1)
    - [macOS](#macos-1)
    - [Linux](#linux)
  - [Full manual Installation](#full-manual-installation)
  - [Package Details](#package-details)
- [ImageMagick Setup](#-imagemagick-setup)
  - [Windows](#windows-2)
  - [macOS](#macos-2)
  - [Linux](#linux-1)
- [Downloading the Application](#-downloading-the-application)
  - [Option 1: Download Release (Recommended for Users)](#option-1-download-release-recommended-for-users)
  - [Option 2: Clone Repository (For Developers)](#option-2-clone-repository-for-developers)
- [Running the Application](#-running-the-application)
- [Troubleshooting Installation & Common Errors](#-troubleshooting-installation--common-errors)
  - [Python Not Recognized](#python-not-recognized)
  - [Missing Packages](#missing-packages)
  - [ImageMagick Errors](#imagemagick-errors)
  - ["No module named 'PIL'"](#no-module-named-pil)
  - ["tkinter not found" (Linux)](#tkinter-not-found-linux)
- [Verifying Installation](#-verifying-installation)
- [Updating the Application](#-updating-the-application)
- [Next Steps](#-next-steps)

## 📋 System Requirements

### Minimum Requirements
- **Operating System**: Windows 7/8/10/11, macOS 10.12+, or Linux (Ubuntu/Debian/CentOS/Fedora etc)
- **CPU**: At least 2 cores (dual-core or better required)
- **Python**: Version 3.10 or higher
- **RAM**: At least 4GB
- **Storage**: 1GB for application + output of single spritesheet processing (5GB+ recommended for batch processing)
- **Internet Access**: Required for downloading dependencies and updates

> **Important Notices:**
> - 32-bit operating systems are **not officially supported** and will **not receive troubleshooting help**.
> - Operating systems below macOS 11, Windows 10, and older Linux distributions are **not officially supported** and will **not receive troubleshooting help**.
> - Python versions below 3.10 are **not officially supported** and will **not receive troubleshooting help**.

### Recommended Requirements
- **Operating System**: Windows 10/11 (64-bit), macOS 11+ (Big Sur or later), or recent Linux (Ubuntu 20.04+/Fedora 36+)
- **CPU**: Quad-core or better
- **Python**: Version 3.11 or higher (64-bit)
- **RAM**: 8GB or more (16GB+ recommended for for batch processing large atlases)
- **Storage**: SSD with 10GB+ free space for faster processing speeds but a regular hard drive will suffice.
- **Internet Access**: Required for downloading dependencies and updates


## 🐍 Python Installation

### Windows

1. Download Python from [python.org](https://www.python.org/downloads/).
2. **Important**: During installation, check the box for **"Add Python to PATH"**.
3. Complete the installation.
4. Open Command Prompt and verify installation:
   ```cmd
   python --version
   ```
   If you see a version number (e.g., `Python 3.12.3`), Python is installed correctly.

### macOS

1. **Recommended**: Install Homebrew if you haven't already:
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
2. Install Python:
   ```bash
   brew install python
   ```
3. Verify installation:
   ```bash
   python3 --version
   ```

### Linux (Ubuntu/Debian)

1. Update package lists:
   ```bash
   sudo apt update
   ```
2. Install Python and pip:
   ```bash
   sudo apt install python3 python3-pip
   ```
3. Verify installation:
   ```bash
   python3 --version
   ```


## 📦 Installing Python Dependencies

### Using requirements.txt (Recommended)

#### Windows
1. Double-click or run `setup/setup_windows.bat` from the project folder. This will attempt to install all required dependencies automatically.
2. If you prefer manual steps, open a terminal or command prompt, navigate to the project root directory, and run:
   ```powershell
   pip install -r setup/requirements.txt
   ```
   If you encounter permission errors, try:
   ```powershell
   python -m pip install --user -r setup/requirements.txt
   ```

#### macOS
1. Open Terminal and run the setup script:
   ```bash
   bash setup/setup_macOSX.sh
   ```
   This will attempt to install all required dependencies automatically, please note that the .sh script for OSX is experimental and not tested by me.
2. If you prefer manual steps, navigate to the project root directory and run:
   ```bash
   pip install -r setup/requirements.txt
   ```
   If you encounter permission errors, try:
   ```bash
   python3 -m pip install --user -r setup/requirements.txt
   ```

#### Linux
1. Open a terminal, navigate to the project root directory, and run:
   ```bash
   pip install -r setup/requirements.txt
   ```
   If you encounter permission errors, try:
   ```bash
   python3 -m pip install --user -r setup/requirements.txt
   ```

### Full manual Installation

If you prefer, you can install packages individually:
```bash
pip install certifi charset-normalizer colorama idna numpy pillow psutil requests tqdm urllib3 Wand tkinter
```
- **Note:** On some Linux systems, you may need to install `tkinter` separately (see Troubleshooting).

### Package Details
- **Pillow (PIL)**: Image processing and manipulation
- **Wand**: Python binding for ImageMagick
- **NumPy**: Numerical operations for image arrays
- **Tkinter**: GUI framework (usually included with Python)
- **Requests**: HTTP library for update checking
- **certifi**: Root certificates for validating the trustworthiness of SSL certificates
- **charset-normalizer**: Encoding detection for text files and web content
- **colorama**: Cross-platform colored terminal text
- **idna**: Internationalized Domain Names in Applications (IDNA) support
- **psutil**: System and process utilities (used for resource monitoring)
- **tqdm**: Progress bar for loops and CLI operations
- **urllib3**: HTTP client for Python (dependency of requests)

## 🎨 ImageMagick Setup

ImageMagick is required for GIF processing and optimization.

### Windows

1. Download ImageMagick from [imagemagick.org](https://imagemagick.org/script/download.php#windows).
2. Choose the version matching your system (64-bit recommended).
3. Run the installer.
4. **Important**: During installation, check:
   - "Install development headers and libraries for C and C++"
   - "Add application directory to your system PATH"
5. After installation, open a new Command Prompt and verify:
   ```cmd
   magick --version
   ```
   If you see version info, ImageMagick is installed.

### macOS

1. Install via Homebrew:
   ```bash
   brew install imagemagick
   ```
2. Verify:
   ```bash
   magick --version
   ```

### Linux

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install imagemagick libmagickwand-dev
```
#### Fedora
```bash
sudo dnf install ImageMagick ImageMagick-devel
```
#### CentOS/RHEL
```bash
sudo yum install ImageMagick ImageMagick-devel
```
#### Verify Installation
```bash
magick --version
```


## 📥 Downloading the Application

### Option 1: Download Release (Recommended for Users)

1. Go to the [GitHub Releases page](https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/releases).
2. Download the latest release ZIP file.
3. Extract all files to a folder of your choice (e.g., `C:\TextureAtlas-to-GIF-and-Frames`).

### Option 2: Clone Repository (For Developers)

1. Open a terminal or command prompt.
2. Run:
   ```bash
   git clone https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames.git
   cd TextureAtlas-to-GIF-and-Frames
   ```


## 🚀 Running the Application

1. Open a terminal or command prompt.
2. Navigate to the `src` directory:
   ```bash
   cd src
   ```
3. Start the application:
   ```bash
   python Main.py
   ```
   - On Windows, you may also double-click `Main.py` if Python is associated with `.py` files.
   - On macOS/Linux, you can make the script executable:
     ```bash
     chmod +x Main.py
     ./Main.py
     ```

## 🔧 Troubleshooting Installation & Common Errors

If you run into installation or startup problems, use this section to diagnose and fix the most common issues. These solutions apply to both source and (where relevant) .exe versions.

### Python Not Recognized

- **Windows**: Run `setup/setup_windows.bat` or reinstall Python and ensure "Add Python to PATH" is checked.
- **macOS**: Run `setup/setup_macOSX.sh` or install Python via Homebrew. (The setup script for OSX is experimental and not tested by me)
- **Linux**: Install Python using your package manager.

### Missing Packages

- Install all dependencies:
  ```bash
  pip install -r setup/requirements.txt
  ```

### ImageMagick Errors

- Ensure ImageMagick is installed and added to your PATH.
- On Windows, verify the `ImageMagick` folder exists or reinstall manually.

### "No module named 'PIL'"

- Install Pillow:
  ```bash
  pip install Pillow
  ```

### "tkinter not found" (Linux)

- **Ubuntu/Debian**:
  ```bash
  sudo apt install python3-tk
  ```
- **Fedora**:
  ```bash
  sudo dnf install python3-tkinter
  ```
- **CentOS/RHEL**:
  ```bash
  sudo yum install tk-devel
  ```


## ✅ Verifying Installation

1. Start the application:
   ```bash
   cd src
   python Main.py
   ```
2. Ensure the GUI opens without errors.
3. Test loading a sample texture atlas and exporting a GIF.


## 🔄 Updating the Application

- The app checks for updates on startup.
- If notified, download the latest release and replace your files.


## 🎯 Next Steps

- Read the [User Manual](user-manual.md) for usage instructions.
- See the [FAQ](faq.md) for troubleshooting.
- For FNF sprites, check the [FNF Guide](fnf-guide.md).

---

**Tip:** If you encounter issues not covered here, please open an issue on [GitHub](https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/issues).
