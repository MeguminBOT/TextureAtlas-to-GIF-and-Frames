import shutil
import os
import sys
import platform

class DependenciesChecker:
    """
    A class to check and configure dependencies.
    Methods:
        check_imagemagick():
            Checks if ImageMagick is installed on the system.
        configure_imagemagick():
            Configures the environment to use a bundled version of ImageMagick.
        check_and_configure_imagemagick():
            Checks if ImageMagick is installed and configures it if not found.
    """

    @staticmethod
    def check_imagemagick():
        return shutil.which("magick") is not None

    @staticmethod
    def configure_imagemagick():
        dll_path = os.path.join(os.path.dirname(sys.argv[0]), 'ImageMagick')
        os.environ['PATH'] = dll_path + os.pathsep + os.environ.get('PATH', '')
        os.environ['MAGICK_CODER_MODULE_PATH'] = dll_path
        print("Using bundled ImageMagick.")

    @staticmethod
    def check_and_configure_imagemagick():
        if DependenciesChecker.check_imagemagick():
            print("Using the user's existing ImageMagick.")
        else:
            if platform.system() == "Windows":
                print("System ImageMagick not found. Attempting to configure bundled version.")
                DependenciesChecker.configure_imagemagick()
            else:
                print("No ImageMagick install detected on the system.")