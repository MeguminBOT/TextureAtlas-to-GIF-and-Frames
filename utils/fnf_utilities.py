import os
import json
import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import filedialog

class FnfUtilities:
    """
    A utility class for importing Friday Night Funkin' (FNF) character data.

    Supports characters from: 
        Kade Engine, Psych Engine, Codename Engine

    Attributes:
        fnf_char_json_directory (str): Directory path where FNF character data files are stored.

    Methods:
        detect_engine(file_path):
            Attempt to detect the engine character file is from and return the parsed data.
        fnf_load_char_data_settings(settings_manager, data_dict, tree):
            Loads character JSON from the specified directory and updates the settings manager with the correct fps for every animation.
        fnf_select_char_data_directory(settings_manager, data_dict, tree, app=None):
            Prompts the user to select a directory containing FNF character JSON files, and loads the data from the selected directory.
    """

    def __init__(self):
        self.fnf_char_json_directory = ""
     
    def detect_engine(self, file_path):
        if file_path.endswith('.json'):
            with open(file_path, 'r') as file:
                try:
                    data = json.load(file)
                    # Check Psych Engine
                    if (
                        "animations" in data and
                        isinstance(data["animations"], list) and
                        all(
                            isinstance(anim, dict) and
                            "name" in anim and
                            "fps" in anim and
                            "anim" in anim and
                            "loop" in anim and
                            "indices" in anim and
                            isinstance(anim["indices"], list)
                            for anim in data["animations"]
                        ) and
                        "image" in data and
                        "scale" in data and
                        "flip_x" in data and
                        "no_antialiasing" in data
                    ):
                        return "Psych Engine", data

                    # Check Kade Engine
                    elif (
                        "name" in data and
                        "asset" in data and
                        "startingAnim" in data and
                        "animations" in data and
                        isinstance(data["animations"], list) and
                        all(
                            isinstance(anim, dict) and
                            "name" in anim and
                            "prefix" in anim and
                            "offsets" in anim and
                            isinstance(anim["offsets"], list) and
                            len(anim["offsets"]) == 2 and
                            (
                                "frameIndices" not in anim or isinstance(anim["frameIndices"], list)
                            ) and
                            (
                                "looped" not in anim or isinstance(anim["looped"], bool)
                            )
                            for anim in data["animations"]
                        )
                    ):
                        return "Kade Engine", data
                except json.JSONDecodeError:
                    pass

        elif file_path.endswith('.xml'):
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()
                # Check Codename Engine
                if (
                    root.tag == "character" and
                    all(
                        anim.tag == "anim" and
                        "name" in anim.attrib and
                        "anim" in anim.attrib and
                        "fps" in anim.attrib and
                        "loop" in anim.attrib and
                        (
                            "indices" not in anim.attrib or
                            ".." in anim.attrib["indices"]
                        )
                        for anim in root.findall("anim")
                    )
                ):
                    scale = root.attrib.get("scale")
                    antialiasing = root.attrib.get("antialiasing")
                    if scale is not None:
                        root.attrib["scale"] = scale
                    if antialiasing is not None:
                        root.attrib["antialiasing"] = antialiasing
                    return "Codename Engine", root
            except ET.ParseError:
                pass
        return "Unknown", None

    def fnf_load_char_data_settings(self, settings_manager, data_dict, tree):
        for filename in os.listdir(self.fnf_char_json_directory):
            file_path = os.path.join(self.fnf_char_json_directory, filename)

            # Detect which engine character data is from.
            engine_type, parsed_data = self.detect_engine(file_path)
            print(f"Found {engine_type} data for {filename}.")

            if engine_type == "Psych Engine" and parsed_data:
                image_base = os.path.splitext(os.path.basename(parsed_data.get("image", "")))[0]
                png_filename = image_base + '.png'

                existing_items = [tree.item(item)['text'] for item in tree.get_children()]
                if png_filename not in existing_items:
                    parent_id = tree.insert('', 'end', text=png_filename, values=("Spritesheet",))
                    data_dict[png_filename] = file_path
                else:
                    parent_id = next((item for item in tree.get_children() if tree.item(item)['text'] == png_filename), None)

                scale = parsed_data.get("scale")
                for anim in parsed_data.get("animations", []):
                    anim_name = anim.get("name", "")
                    fps = anim.get("fps", 0)
                    indices = anim.get("indices", None)
                    loop = anim.get("loop", False)

                    full_anim_name = f"{png_filename}/{anim_name}"
                    settings = {"fps": fps}

                    if scale != 1: 
                        settings["scale"] = scale
                    if indices:
                        settings["indices"] = indices
                    if loop:
                        settings["delay"] = 0  # Set delay to 0 for looping animations

                    settings_manager.set_animation_settings(full_anim_name, **settings)

                    # Insert animation as child if not already present
                    anim_exists = any(tree.item(child)['text'] == anim_name for child in tree.get_children(parent_id))
                    if not anim_exists:
                        tree.insert(parent_id, 'end', text=anim_name, values=("Animation",))

            elif engine_type == "Codename Engine" and parsed_data:
                image_base = os.path.splitext(filename)[0]
                png_filename = image_base + '.png'

                existing_items = [tree.item(item)['text'] for item in tree.get_children()]
                if png_filename not in existing_items:
                    parent_id = tree.insert('', 'end', text=png_filename, values=("Spritesheet",))
                    data_dict[png_filename] = file_path
                else:
                    parent_id = next((item for item in tree.get_children() if tree.item(item)['text'] == png_filename), None)

                scale = float(parsed_data.attrib.get("scale", 1))
                for anim in parsed_data.findall("anim"):
                    anim_name = anim.get("name", "")
                    fps = int(anim.get("fps", 0))
                    indices = anim.get("indices", None)
                    loop = anim.get("loop", "false").lower() == "true"

                    full_anim_name = f"{png_filename}/{anim_name}"
                    settings = {"fps": fps}

                    if scale != 1: 
                        settings["scale"] = scale
                    if indices:
                        settings["indices"] = [int(i) for i in indices.split("..") if i] if ".." in indices else [int(i) for i in indices.split(",") if i]
                    if loop:
                        settings["delay"] = 0  # Set delay to 0 for looping animations

                    settings_manager.set_animation_settings(full_anim_name, **settings)

                    anim_exists = any(tree.item(child)['text'] == anim_name for child in tree.get_children(parent_id))
                    if not anim_exists:
                        tree.insert(parent_id, 'end', text=anim_name, values=("Animation",))

            elif engine_type == "Kade Engine" and parsed_data:
                image_base = os.path.splitext(filename)[0]
                png_filename = image_base + '.png'

                existing_items = [tree.item(item)['text'] for item in tree.get_children()]
                if png_filename not in existing_items:
                    parent_id = tree.insert('', 'end', text=png_filename, values=("Spritesheet",))
                    data_dict[png_filename] = file_path
                else:
                    parent_id = next((item for item in tree.get_children() if tree.item(item)['text'] == png_filename), None)

                for anim in parsed_data.get("animations", []):
                    anim_name = anim.get("name", "")
                    fps = parsed_data.get("frameRate", 0)
                    indices = anim.get("frameIndices", None)
                    loop = anim.get("looped", False)

                    full_anim_name = f"{png_filename}/{anim_name}"
                    settings = {"fps": fps}

                    if indices:
                        settings["indices"] = indices
                    if loop:
                        settings["delay"] = 0  # Set delay to 0 for looping animations

                    settings_manager.set_animation_settings(full_anim_name, **settings)

                    anim_exists = any(tree.item(child)['text'] == anim_name for child in tree.get_children(parent_id))
                    if not anim_exists:
                        tree.insert(parent_id, 'end', text=anim_name, values=("Animation",))

            else:
                print(f"Skipping {filename}: Not a FNF character data file or unsupported engine type.")

    def fnf_select_char_data_directory(self, settings_manager, data_dict, tree, app=None):
        """
        Opens a directory dialog and loads FNF character data settings, updating the provided single Treeview widget.
        """
        self.fnf_char_json_directory = filedialog.askdirectory(title="Select FNF Character Data Directory")
        if self.fnf_char_json_directory:
            self.fnf_load_char_data_settings(settings_manager, data_dict, tree)
            print("Animation settings updated in SettingsManager.")
            # If app is provided, update the tree settings nodes
            if app is not None and hasattr(app, 'add_settings_to_tree'):
                app.add_settings_to_tree()