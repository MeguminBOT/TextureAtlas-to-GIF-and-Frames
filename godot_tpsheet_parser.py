import os
import json
import tkinter as tk
import re

# Import our own modules
from utilities import Utilities

class GodotTpsheetParser:
    """
    >>>> UNFINISHED CODE, JUST MADE AS A STARTING POINT FOR GODOT TPSHEETS <<<<

    A class to parse Godot .tpsheet files and extract sprite data.

    Attributes:
        directory: The directory where the .tpsheet file is located.
        tpsheet_filename: The name of the .tpsheet file to parse.
        listbox_data: The Tkinter listbox to populate with extracted names.

    Methods:
        get_data(): Parses the .tpsheet file and populates the listbox with names.
        extract_names(data): Extracts names from the parsed .tpsheet data.
        get_names(names): Populates the listbox with the given names.
        parse_tpsheet_data(file_path): Static method to parse .tpsheet data from a file and return sprite information.
        group_animation_frames(sprites): #Todo
    """

    def __init__(self, directory, tpsheet_filename, listbox_data):
        self.directory = directory
        self.tpsheet_filename = tpsheet_filename
        self.listbox_data = listbox_data

    def get_data(self):
        file_path = os.path.join(self.directory, self.tpsheet_filename)
        sprites = self.parse_tpsheet_data(file_path)
        animations = self.group_animation_frames(sprites)
        names = self.extract_names(animations)
        self.get_names(names)

    def extract_names(self, animations):
        return set(animations.keys())

    def get_names(self, names):
        for name in sorted(names):
            self.listbox_data.insert(tk.END, name)

    @staticmethod
    def parse_tpsheet_data(file_path):
        with open(file_path, 'r') as file:
            data = json.load(file)

        sprites = []
        for texture in data.get("textures", []):
            for sprite in texture.get("sprites", []):
                region = sprite["region"]
                margin = sprite.get("margin", {"x": 0, "y": 0, "w": region["w"], "h": region["h"]})

                sprites.append({
                    "name": sprite["filename"],
                    "x": region["x"],
                    "y": region["y"],
                    "width": region["w"],
                    "height": region["h"],
                    "frameX": -margin["x"],
                    "frameY": -margin["y"],
                    "frameWidth": region["w"] + margin["x"] + margin["w"],
                    "frameHeight": region["h"] + margin["y"] + margin["h"],
                    "rotated": False  # No rotation information in my .tpsheet format so idk if this is exist.
                })

        return sprites

    @staticmethod
    def group_animation_frames(sprites):
        animations = {}
        frame_pattern = re.compile(r"(.*?)(\d+)$")

        for sprite in sprites:
            match = frame_pattern.match(sprite["name"])
            if match:
                base_name, frame_number = match.groups()
                animations.setdefault(base_name, []).append(sprite)
            else:
                # No number, treat as a single texture.
                animations.setdefault(sprite["name"], []).append(sprite)

        # Sort frames
        for base_name, frames in animations.items():
            animations[base_name] = sorted(frames, key=lambda s: int(frame_pattern.match(s["name"]).group(2)))

        return animations