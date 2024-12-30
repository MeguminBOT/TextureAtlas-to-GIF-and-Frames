import os
import json
import tkinter as tk
from tkinter import filedialog

from tkinter import filedialog
import os
import json

class FnfUtilities:
    """
    A utility class for importing Friday Night Funkin' (FNF) character JSON data.
    Attributes:
        fnf_char_json_directory (str): Directory path where FNF character JSON files are stored.
    Methods:
        fnf_load_char_json_settings(extraction_config, data_dict, listbox_png, listbox_data): Loads character JSON from the specified directory and updates extraction config with the correct fps for every animation.
        fnf_select_char_json_directory(extraction_config, data_dict, listbox_png, listbox_data): Prompts the user to select a directory containing FNF character JSON files, and loads the data from the selected directory.
    """

    def __init__(self, extraction_config):
        self.fnf_char_json_directory = ""
        self.extraction_config = extraction_config

    def fnf_load_char_json_settings(self, extraction_config, data_dict, listbox_png, listbox_data):
        for filename in os.listdir(self.fnf_char_json_directory):
            if filename.endswith('.json'):
                with open(os.path.join(self.fnf_char_json_directory, filename), 'r') as file:
                    char_data = json.load(file)
                    animations = char_data.get('animations', [])
                    if isinstance(animations, list):
                        for anim in animations:
                            anim_name = anim.get('name')
                            fps = anim.get('fps', 24)
                            png_filename = os.path.splitext(filename)[0] + '.png'
                            extraction_config.set_animation_setting(png_filename, anim_name, 'fps', fps)

    def fnf_select_char_json_directory(self, extraction_config, data_dict, listbox_png, listbox_data):
        self.fnf_char_json_directory = filedialog.askdirectory(title="Select FNF Character JSON Directory")
        if self.fnf_char_json_directory:
            self.fnf_load_char_json_settings(extraction_config, data_dict, listbox_png, listbox_data)