# TextureAtlas to GIF and Frames

This tool simplifies the process of extracting frames from sprite sheets, organizing them into individual folders, and optionally creating GIFs/WebPs. It's designed to streamline your workflow by automating tedious tasks.

## Current Spritesheet types supported
* Sparrow
* Starling

## Functionality
* Extracts and organizes frames from sprite sheets into folders named after respective sprites and animations.
* Provides an option to generate GIF or WebP for each animation. GIFs and WEBPs are prefixed with the spritesheet name for easy identification.
* Automatically crops GIFs as much as possible.
* Customization of animation frame rate.
* Customization of animation loop delay.
* Customization of alpha transparency threshold for GIFs.
* Override settings above and indices for individual sprites and animations.
* Option to delete frames after GIF/WebP generation.

## Not yet implemented
Feel free to help me implement anything on this list.
* Transition to the new QT UI inside the "new_ui_project" folder. (I'm malding over python classes, and I'm bit more busy irl lately)
* Implement the icon splitter tool into a sub menu when the new QT UI is fully implemented https://github.com/MeguminBOT/FNF-Icon-Splitter
* Selection of specific sprites for extraction (Currently processes entire folders).
* Automatically crop frames using the xml file data.

## How to Install
### Windows
**Download**: [Get the executable here](https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/releases/)

### Mac OSX
1. Download and Install Python 3.10+. You can download Python here: [https://www.python.org/downloads/](https://www.python.org/downloads/macos/)
2. Go to Applications > Utilities and open Terminal.
3. Type `python --version` to ensure that Python gets recognized by your system. If it returns the python version properly, proceed to step 4.
4. Type `python -m ensurepip`. After it's installed, make sure pip gets recognized by your system by typing: `pip --version` befoe proceeding to step 5.
5. Type `pip install pillow` to install PIL.
6. Type `pip install requests` to install Requests.
7. Type `pip install tk` to install Tkinter.

You should now be able to run the "TextureAtlas to GIF and Frames.py" file by double clicking it. 
If not, then open a terminal window in the same folder as the script and type `python TextureAtlas to GIF and Frames.py`, or drag and drop the file on the python application. 

### Linux (Ubuntu / Debian based)
1. Open the terminal.
2. Type `sudo apt install python3.10` and install (if it's not already installed).
3. Type `sudo apt install python3-pip` and install (if it's not already installed)
4. Type `sudo pip3 install pillow` to install PIL.
5. Type `sudo pip3 install requests` to install Requests.
6. Type `sudo pip3 install tk` to install Tkinter.

You should now be able to run the "TextureAtlas to GIF and Frames.py" file by double clicking it. 
If not, then open a terminal window in the same folder as the script and type `python3 TextureAtlas to GIF and Frames.py`.
