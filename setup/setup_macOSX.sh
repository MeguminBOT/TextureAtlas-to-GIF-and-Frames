### THIS SCRIPT IS EXPERIMENTAL AND UNTESTED ON macOS/OSX, AS I DO NOT HAVE ACCESS TO A MACOS/OSX SYSTEM. 
### Potential issues include compatibility with Homebrew installation, Python version detection, and library installation.

#!/bin/bash
if ! command -v brew &> /dev/null; then
    if ! command -v curl &> /dev/null; then
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    SHELL_NAME=$(basename "$SHELL")
    if [ "$SHELL_NAME" = "zsh" ]; then
        echo 'eval "$($(brew --prefix)/bin/brew shellenv)"' >> ~/.zprofile
    elif [ "$SHELL_NAME" = "bash" ]; then
        echo 'eval "$($(brew --prefix)/bin/brew shellenv)"' >> ~/.bash_profile
    elif [ "$SHELL_NAME" = "fish" ]; then
        echo 'eval "$($(brew --prefix)/bin/brew shellenv)"' >> ~/.config/fish/config.fish
    else
        echo "Unsupported shell: $SHELL_NAME. Please manually configure Homebrew shell environment."
    fi
    eval "$($(brew --prefix)/bin/brew shellenv)"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    echo 'eval "$($(brew --prefix)/bin/brew shellenv)"' >> ~/.zprofile
    eval "$($(brew --prefix)/bin/brew shellenv)"
else
    echo "Homebrew is already installed."
fi

if ! command -v magick &> /dev/null; then
    echo "ImageMagick not found. Installing ImageMagick..."
    brew install imagemagick
else
    echo "ImageMagick is already installed."
fi

if ! command -v gs &> /dev/null; then
    echo "Ghostscript not found. Installing Ghostscript..."
    PY_VER=$($PY_CMD --version 2>&1 | awk '{print $2}' | grep -oE '^[0-9]+\.[0-9]+(\.[0-9]+)?')
else
    echo "Ghostscript is already installed."
fi

PY_CMD=""
PY_VER=""
if command -v python3 &> /dev/null; then
    PY_CMD="python3"
    PY_VER=$($PY_CMD --version 2>&1 | awk '{print $2}')
elif command -v python &> /dev/null; then
    PY_CMD="python"
    PY_VER=$($PY_CMD --version 2>&1 | awk '{print $2}')
fi

if [ -z "$PY_VER" ]; then
    echo "Python 3.10 or later not found."
    read -p "Do you want to download and install the latest Python version? (Y/N): " INSTALL_PY
    if [[ "$INSTALL_PY" =~ ^[Yy]$ ]]; then
        echo "Downloading and installing Python using Homebrew..."
        brew install python
        PY_CMD="python3"
        PY_VER=$($PY_CMD --version 2>&1 | awk '{print $2}')
        if [ -z "$PY_VER" ]; then
            echo "Python installation failed. Please install Python manually and re-run this script."
            read -p "Press Enter to exit..."
            exit 1
        fi
    else
        echo "Python is required. Exiting."
MAJOR=$(echo $PY_VER | awk -F. '{print $1}')
MINOR=$(echo $PY_VER | awk -F. '{print $2}')
    fi
fi

MAJOR=$(echo $PY_VER | cut -d. -f1)
MINOR=$(echo $PY_VER | cut -d. -f2)
VER_OK=0
if [ "$MAJOR" -gt 3 ]; then
    VER_OK=1
elif [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 10 ]; then
    VER_OK=1
fi

    if ! $PY_CMD -m pip --version &> /dev/null; then
        echo "pip not found. Installing pip..."
        $PY_CMD -m ensurepip --upgrade
    fi
    $PY_CMD -m pip install --upgrade pip
    $PY_CMD -m pip install -r "$(dirname "$0")/requirements.txt"
    read -p "Do you want to download and install the latest Python version? (Y/N): " INSTALL_PY
    if [[ "$INSTALL_PY" =~ ^[Yy]$ ]]; then
        open "https://www.python.org/downloads/macos/"
        echo "Please install Python, then re-run this script."
        read -p "Press Enter to exit..."
        exit 1
    else
        echo "Python 3.10 or later is required. Exiting."
        read -p "Press Enter to exit..."
        exit 1
    fi
read -p "Do you want to install the required python libraries for TextureAtlas to GIF and Frames? (Y/N): " INSTALL_REQ
if [[ "$INSTALL_REQ" =~ ^[Yy]$ ]]; then
    REQUIREMENTS_FILE="$(dirname "$0")/requirements.txt"
    if [ -f "$REQUIREMENTS_FILE" ]; then
        $PY_CMD -m pip install --upgrade pip
        $PY_CMD -m pip install -r "$REQUIREMENTS_FILE"
        read -p "Press Enter to continue..."
    else
        echo "Error: requirements.txt file not found at $REQUIREMENTS_FILE."
        echo "Please ensure the file exists and re-run the script."
        read -p "Press Enter to exit..."
        exit 1
    fi
else
    echo "Skipping requirements installation. Note: Without installing the required Python libraries, the TextureAtlas-to-GIF-and-Frames functionality may not work as expected."
    read -p "Press Enter to continue..."
fi
else
    echo "Skipping requirements installation."
    read -p "Press Enter to continue..."
fi
