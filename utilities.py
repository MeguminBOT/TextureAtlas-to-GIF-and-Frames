import re
import os

class Utilities:
    """
    A utility class providing static methods for common tasks.

    Methods:
    - count_spritesheets(directory): Count the number of spritesheet data files in a directory.
    - clean_invalid_chars(name): Replace invalid filename characters (\\, /, :, *, ?, ", <, >, |) with an underscore and strip trailing whitespace.
    - strip_trailing_digits(name): Remove trailing digits (1 to 4 digits) and optional ".png" extension, then strip any trailing whitespace.
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