import os
import re
from string import Template

class Utilities:
    """
    A utility class providing static methods for common tasks.

    Methods:
        count_spritesheets(directory): Count the number of spritesheet data files in a directory.
        clean_invalid_chars(name): Replace invalid filename characters (\\, /, :, *, ?, ", <, >, |) with an underscore and strip trailing whitespace.
        strip_trailing_digits(name): Remove trailing digits (1 to 4 digits) and optional ".png" extension, then strip any trailing whitespace.
        format_filename(prefix, sprite_name, animation_name, filename_format): Formats the filename based on the given parameters.
        find_and_replace(string, rules): #TODO
    """

    @staticmethod
    def count_spritesheets(directory):
        return sum(1 for filename in os.listdir(directory) if filename.endswith('.xml') or filename.endswith('.txt'))

    @staticmethod
    def replace_invalid_chars(name):
        return re.sub(r'[\\/:*?"<>|]', '_', name).rstrip()
    
    @staticmethod
    def strip_trailing_digits(name):
        return re.sub(r'\d{1,4}(?:\.png)?$', '', name).rstrip()
    
    @staticmethod
    def format_filename(prefix, sprite_name, animation_name, filename_format):
        sprite_name = os.path.splitext(sprite_name)[0]
        if filename_format == "Standardized" or filename_format == "No Spaces" or filename_format == "No Special Characters":
            base_name = f"{prefix} - {sprite_name} - {animation_name}" if prefix else f"{sprite_name} - {animation_name}"
            if filename_format == "No Spaces":
                return base_name.replace(" ", "")
            elif filename_format == "No Special Characters":
                return base_name.replace(" ", "").replace("-", "").replace("_", "")
        else:
            base_name = Template(filename_format).safe_substitute(sprite=sprite_name, anim=animation_name)
        return base_name
    
    @staticmethod
    def find_and_replace(string, rules):
        for rule in rules:
            if rule["regex"]:
                string = string.replace(rule["find"], rule["replace"])
            else:
                string = re.sub(rule["find"], rule["replace"], string)
        return string
