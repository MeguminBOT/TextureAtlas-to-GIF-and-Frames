import json
import os
import tkinter as tk

# Import our own modules
from utils.utilities import Utilities


class AnimateParser:
    """
    A class to parse Adobe Animate atlas JSON files and extract sprite data.
    Supports Adobe Animate CC 2021+ texture atlas format with both spritemap and animation data.

    The parser handles two types of JSON files:
    1. Spritemap JSON: Contains sprite atlas data (ATLAS.SPRITES)
    2. Animation JSON: Contains animation timeline data (SD, AN)

    Attributes:
        directory (str): The directory where the JSON file is located.
        json_filename (str): The name of the JSON file to parse.
        listbox_data (tk.Listbox): The Tkinter listbox to populate with extracted names.

    Methods:
        __init__(directory, json_filename, listbox_data): Initializes the parser with directory, filename, and listbox.
        get_data(): Parses the JSON file and populates the listbox with names.
        extract_names(json_data): Extracts names from the JSON data.
        get_names(names): Populates the listbox with the given names.
        parse_animate_data(file_path): Static method to parse JSON data from a file and return sprite information.
        parse_spritemap_data(json_data): Static method to parse spritemap data and return sprite information.
        parse_animation_data(json_data): Static method to parse animation data and return sprite information.
    """

    def __init__(self, directory, json_filename, listbox_data):
        self.directory = directory
        self.json_filename = json_filename
        self.listbox_data = listbox_data

    def get_data(self):
        with open(os.path.join(self.directory, self.json_filename), "r", encoding='utf-8-sig') as file:
            json_data = json.load(file)
        names = self.extract_names(json_data)
        self.get_names(names)

    def extract_names(self, json_data):
        names = set()
        
        # Check if this is a spritemap JSON
        if "ATLAS" in json_data:
            sprites = json_data["ATLAS"]
            if "SPRITES" in sprites:
                sprites = sprites["SPRITES"]
            
            for sprite_data in sprites:
                sprite = sprite_data.get("SPRITE", sprite_data)
                name = sprite.get("name", "")
                if name:
                    # For Adobe Animate, sprites are often just numbered (0000, 0001, etc.)
                    # In this case, we want to keep the full name or create a base name
                    stripped_name = Utilities.strip_trailing_digits(name)
                    if stripped_name:  # If there's still a name after stripping digits
                        names.add(stripped_name)
                    else:  # If the name was just digits, use a generic base name
                        names.add("sprite")  # This will group all numbered sprites under "sprite"
        
        # Check if this is an animation JSON with symbol dictionary
        elif "SD" in json_data:
            symbols_data = json_data["SD"]
            if "S" in symbols_data:
                symbols_data = symbols_data["S"]
            
            for symbol in symbols_data:
                name = symbol.get("SN", "")
                if name:
                    names.add(name)
        
        # Check for timeline animations
        if "AN" in json_data and "TL" in json_data["AN"]:
            timeline = json_data["AN"]["TL"]
            if "L" in timeline:
                timeline = timeline["L"]
            
            for layer in timeline:
                if "FR" in layer:
                    for frame in layer["FR"]:
                        if "N" in frame:  # Frame has a name (animation name)
                            names.add(frame["N"])
        
        return names

    def get_names(self, names):
        for name in sorted(names):
            self.listbox_data.insert(tk.END, name)

    @staticmethod
    def parse_animate_data(file_path):
        """
        Parse Adobe Animate JSON file and return sprite information.
        
        Args:
            file_path (str): Path to the JSON file
            
        Returns:
            list: List of sprite dictionaries with keys: name, x, y, width, height, frameX, frameY, frameWidth, frameHeight, rotated
        """
        with open(file_path, "r", encoding='utf-8-sig') as file:
            json_data = json.load(file)
        
        # Check if this is a spritemap JSON (contains sprite atlas data)
        if "ATLAS" in json_data:
            return AnimateParser.parse_spritemap_data(json_data)
        
        # Check if this is an animation JSON (contains symbol dictionary)
        elif "SD" in json_data:
            return AnimateParser.parse_animation_data(json_data)
        
        else:
            raise ValueError("Invalid Adobe Animate JSON format: missing ATLAS or SD sections")

    @staticmethod
    def parse_spritemap_data(json_data):
        """
        Parse spritemap data from Adobe Animate JSON.
        
        Args:
            json_data (dict): Parsed JSON data
            
        Returns:
            list: List of sprite dictionaries
        """
        sprites = []
        atlas_data = json_data["ATLAS"]
        
        # Handle nested SPRITES structure
        sprites_data = atlas_data
        if "SPRITES" in atlas_data:
            sprites_data = atlas_data["SPRITES"]
        
        for sprite_entry in sprites_data:
            # Handle nested SPRITE structure
            sprite = sprite_entry
            if "SPRITE" in sprite_entry:
                sprite = sprite_entry["SPRITE"]
            
            # Extract sprite data
            name = sprite.get("name", "")
            x = sprite.get("x", 0)
            y = sprite.get("y", 0)
            w = sprite.get("w", 0)
            h = sprite.get("h", 0)
            rotated = sprite.get("rotated", False)
            
            # Adobe Animate doesn't typically include frame offset data in spritemap
            # These would be handled in the animation data
            sprites.append({
                "name": name,
                "x": int(x),
                "y": int(y),
                "width": int(w),
                "height": int(h),
                "frameX": 0,
                "frameY": 0,
                "frameWidth": int(w),
                "frameHeight": int(h),
                "rotated": rotated
            })
        
        return sprites

    @staticmethod
    def parse_animation_data(json_data):
        """
        Parse animation data from Adobe Animate JSON.
        This is more complex as it involves parsing the symbol dictionary and timeline.
        For now, this creates placeholder sprites based on symbol names.
        
        Args:
            json_data (dict): Parsed JSON data
            
        Returns:
            list: List of sprite dictionaries (placeholders for symbols)
        """
        sprites = []
        
        # Parse Symbol Dictionary (SD)
        symbols_data = json_data["SD"]
        if "S" in symbols_data:
            symbols_data = symbols_data["S"]
        
        for symbol in symbols_data:
            name = symbol.get("SN", "")
            if name:
                # Create a placeholder sprite for each symbol
                # In a real implementation, you'd need to render the symbol
                # or extract sprite data from the associated spritemap
                sprites.append({
                    "name": name,
                    "x": 0,
                    "y": 0,
                    "width": 100,  # Placeholder dimensions
                    "height": 100,
                    "frameX": 0,
                    "frameY": 0,
                    "frameWidth": 100,
                    "frameHeight": 100,
                    "rotated": False
                })
        
        return sprites

    @staticmethod
    def is_animate_json(file_path):
        """
        Check if a JSON file is an Adobe Animate atlas file.
        
        Args:
            file_path (str): Path to the JSON file
            
        Returns:
            bool: True if the file is an Adobe Animate JSON
        """
        try:
            with open(file_path, "r", encoding='utf-8-sig') as file:
                json_data = json.load(file)
            
            # Check for Adobe Animate specific structure
            return "ATLAS" in json_data or ("SD" in json_data and "AN" in json_data)
        
        except (json.JSONDecodeError, FileNotFoundError, KeyError):
            return False
