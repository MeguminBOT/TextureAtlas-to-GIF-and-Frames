#!/bin/bash

# Check for Homebrew, install if we don't have it
if test ! $(which brew); then
    echo "Homebrew not found. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Ensure Homebrew is up to date
brew update

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python not found. Installing Python..."
    brew install python
else
    echo "Python is already installed."
fi

# Ensure pip is up to date
echo "Updating pip..."
pip3 install --upgrade pip

# Check and install Python dependencies
declare -a packages=("pillow" "requests" "tk")

for package in "${packages[@]}"; do
    if python3 -c "import $package" &> /dev/null; then
        echo "$package is already installed."
    else
        echo "$package not found. Installing $package..."
        pip3 install $package
    fi
done

# Run the Python script
SCRIPT_NAME="TextureAtlas to GIF and Frames.py"
if [ -f "$SCRIPT_NAME" ]; then
    echo "Running $SCRIPT_NAME..."
    python3 "$SCRIPT_NAME"
else
    echo "Error: $SCRIPT_NAME not found in the current directory."
fi
