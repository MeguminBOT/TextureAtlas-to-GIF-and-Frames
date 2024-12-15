import os
import json
import tkinter as tk
from tkinter import filedialog

class FnfUtilities:
    """
    A utility class for importing Friday Night Funkin' (FNF) character JSON data.
    Attributes:
        fnf_char_json_directory (str): Directory path where FNF character JSON files are stored.
    Methods:
        fnf_load_char_json_settings(user_settings, data_dict, listbox_png, listbox_data): Loads character JSON from the specified directory and updates user settings with the correct fps for every animation.
        fnf_select_char_json_directory(user_settings, data_dict, listbox_png, listbox_data): Prompts the user to select a directory containing FNF character JSON files, and loads the data from the selected directory.
    """

    def __init__(self):
        self.fnf_char_json_directory = ""

    def fnf_load_char_json_settings(self, user_settings, data_dict, listbox_png, listbox_data):
        for filename in os.listdir(self.fnf_char_json_directory):
            if filename.endswith('.json'):
                with open(os.path.join(self.fnf_char_json_directory, filename), 'r') as file:
                    data = json.load(file)
                    image_base = os.path.splitext(os.path.basename(data.get("image", "")))[0]
                    png_filename = image_base + '.png'
                    
                    if png_filename not in [listbox_png.get(idx) for idx in range(listbox_png.size())]:
                        listbox_png.insert(tk.END, png_filename)
                        data_dict[png_filename] = os.path.join(self.fnf_char_json_directory, image_base + '.xml')
                    
                    for anim in data.get("animations", []):
                        anim_name = anim.get("name", "")
                        fps = anim.get("fps", 0)
                        user_settings[png_filename + '/' + anim_name] = {'fps': fps}

    def fnf_select_char_json_directory(self, user_settings, data_dict, listbox_png, listbox_data):
        self.fnf_char_json_directory = filedialog.askdirectory(title="Select FNF Character JSON Directory")
        if self.fnf_char_json_directory:
            self.fnf_load_char_json_settings(user_settings, data_dict, listbox_png, listbox_data)
            print("User settings populated:", user_settings)