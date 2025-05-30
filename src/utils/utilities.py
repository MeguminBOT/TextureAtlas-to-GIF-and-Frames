import re
import os
from string import Template

class Utilities:
    """
    A utility class providing static methods for common tasks.

    Methods:
        find_root(target_name):
            Walks up the directory tree from the current file location until it finds a directory containing the target_name (file or folder).
            Returns the path to the directory containing the target_name, or None if not found.
        count_spritesheets(spritesheet_list):
            Count the number of spritesheet data files in a list.
        replace_invalid_chars(name):
            Replace invalid filename characters (\\, /, :, *, ?, ", <, >, |) with an underscore and strip trailing whitespace.
        strip_trailing_digits(name):
            Remove trailing digits (1 to 4 digits) and optional ".png" extension, then strip any trailing whitespace.
        format_filename(prefix, sprite_name, animation_name, filename_format, replace_rules):
            Formats the filename based on the given parameters and applies find/replace rules.
    """
    
    @staticmethod
    def find_root(target_name):
        root_path = os.path.abspath(os.path.dirname(__file__))
        while True:
            target_path = os.path.join(root_path, target_name)
            if os.path.exists(target_path):
                print(f"[find_root] Found '{target_name}' at: {target_path}")
                return root_path
            new_root = os.path.dirname(root_path)
            if new_root == root_path:
                break
            root_path = new_root
        return None

    @staticmethod
    def count_spritesheets(spritesheet_list):
        return len(spritesheet_list)

    @staticmethod
    def replace_invalid_chars(name):
        return re.sub(r'[\\/:*?"<>|]', '_', name).rstrip()
    
    @staticmethod
    def strip_trailing_digits(name):
        return re.sub(r'\d{1,4}(?:\.png)?$', '', name).rstrip()
    
    @staticmethod
    def format_filename(prefix, sprite_name, animation_name, filename_format, replace_rules):
        # Provide safe defaults for preview function or missing values
        if filename_format is None:
            filename_format = "Standardized"
        if not replace_rules:
            replace_rules = []

        sprite_name = os.path.splitext(sprite_name)[0]
        if filename_format in ("Standardized", "No spaces", "No special characters"):
            base_name = f"{prefix} - {sprite_name} - {animation_name}" if prefix else f"{sprite_name} - {animation_name}"
            if filename_format == "No spaces":
                base_name = base_name.replace(" ", "")
            elif filename_format == "No special characters":
                base_name = base_name.replace(" ", "").replace("-", "").replace("_", "")
        else:
            base_name = Template(filename_format).safe_substitute(sprite=sprite_name, anim=animation_name)
            
        for rule in replace_rules:
            if rule["regex"]:
                base_name = re.sub(rule["find"], rule["replace"], base_name)
            else:
                base_name = base_name.replace(rule["find"], rule["replace"])
        return base_name