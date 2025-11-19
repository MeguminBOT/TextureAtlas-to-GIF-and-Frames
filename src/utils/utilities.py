import re
import os
import sys
from string import Template
from PySide6.QtCore import QCoreApplication


class Utilities:
    """
    A utility class providing static methods for common tasks.

    Methods:
        find_root(target_name):
            Walks up the directory tree from the current file location until it finds a directory containing the target_name (file or folder).
            Returns the path to the directory containing the target_name, or None if not found.
        is_compiled():
            Determine if the application is running as a Nuitka-compiled executable.
        count_spritesheets(spritesheet_list):
            Count the number of spritesheet data files in a list.
        replace_invalid_chars(name):
            Replace invalid filename characters (\\, /, :, *, ?, ", <, >, |) with an underscore and strip trailing whitespace.
        strip_trailing_digits(name):
            Remove trailing digits (1 to 4 digits) and optional ".png" extension, then strip any trailing whitespace.
        format_filename(prefix, sprite_name, animation_name, filename_format, replace_rules, suffix=None):
            Formats the filename based on the given parameters and applies find/replace rules, with optional suffix.
    """

    # Application constants
    APP_NAME = QCoreApplication.translate("Utilities", "TextureAtlas Toolbox")

    @staticmethod
    def find_root(target_name):
        if Utilities.is_compiled():
            root_path = os.path.dirname(sys.executable)
        else:
            root_path = os.path.abspath(os.path.dirname(__file__))

        target_path = os.path.join(root_path, target_name)
        if os.path.exists(target_path):
            print(f"[find_root] Found '{target_name}' at: {target_path}")
            return root_path

        while True:
            target_path = os.path.join(root_path, target_name)
            if os.path.exists(target_path):
                print(f"[find_root] Found '{target_name}' at: {target_path}")
                return root_path
            new_root = os.path.dirname(root_path)
            if new_root == root_path:
                break
            root_path = new_root

        print(f"[find_root] Could not find '{target_name}' in directory tree")
        return None

    @staticmethod
    def is_compiled():
        if "__compiled__" in globals():
            return True
        else:
            return False

    @staticmethod
    def count_spritesheets(spritesheet_list):
        return len(spritesheet_list)

    @staticmethod
    def replace_invalid_chars(name):
        return re.sub(r'[\\/:*?"<>|]', "_", name).rstrip()

    @staticmethod
    def strip_trailing_digits(name):
        # Strip trailing digits and optional .png extension, then strip any trailing underscores
        return re.sub(r"[_\s]*\d{1,4}(?:\.png)?$", "", name).rstrip("_").rstrip()

    @staticmethod
    def format_filename(
        prefix, sprite_name, animation_name, filename_format, replace_rules, suffix=None
    ):
        # Provide safe defaults for preview function or missing values
        if filename_format is None:
            filename_format = "Standardized"
        if not replace_rules:
            replace_rules = []

        sprite_name = os.path.splitext(sprite_name)[0]
        if filename_format in ("Standardized", "No spaces", "No special characters"):
            # Build base name with prefix and suffix embedded
            if prefix and suffix:
                base_name = f"{prefix} - {sprite_name} - {animation_name} - {suffix}"
            elif prefix:
                base_name = f"{prefix} - {sprite_name} - {animation_name}"
            elif suffix:
                base_name = f"{sprite_name} - {animation_name} - {suffix}"
            else:
                base_name = f"{sprite_name} - {animation_name}"

            if filename_format == "No spaces":
                base_name = base_name.replace(" ", "")
            elif filename_format == "No special characters":
                base_name = base_name.replace(" ", "").replace("-", "").replace("_", "")
        else:
            base_name = Template(filename_format).safe_substitute(
                sprite=sprite_name, anim=animation_name
            )
            # For template formats, add prefix and suffix separately since template doesn't include them
            if prefix:
                base_name = f"{prefix} - {base_name}"
            if suffix:
                base_name = f"{base_name} - {suffix}"

        for rule in replace_rules:
            if rule["regex"]:
                base_name = re.sub(rule["find"], rule["replace"], base_name)
            else:
                base_name = base_name.replace(rule["find"], rule["replace"])

        return Utilities.replace_invalid_chars(base_name)
