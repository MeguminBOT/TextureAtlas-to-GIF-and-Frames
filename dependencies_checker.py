import shutil
import os
import sys
import platform

def check_imagemagick():
    return shutil.which("magick") is not None

def configure_imagemagick():
    dll_path = os.path.join(os.path.dirname(sys.argv[0]), 'ImageMagick')
    os.environ['PATH'] = dll_path + os.pathsep + os.environ.get('PATH', '')
    os.environ['MAGICK_CODER_MODULE_PATH'] = dll_path
    print("Using bundled ImageMagick.")

if check_imagemagick():
    print("Using the user's existing ImageMagick.")
else:
    if platform.system() == "Windows":
        print("System ImageMagick not found. Attempting to configure bundled version.")
        configure_imagemagick()
    else:
        print("No ImageMagick install detected on the system.")