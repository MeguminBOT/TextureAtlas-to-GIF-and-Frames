import os
import json
import tkinter as tk
from tkinter import filedialog

## FNF specific stuff
def fnf_load_char_json_settings(fnf_char_json_directory, user_settings, xml_dict, listbox_png, listbox_xml):

    for filename in os.listdir(fnf_char_json_directory):
        if filename.endswith('.json'):
            with open(os.path.join(fnf_char_json_directory, filename), 'r') as file:
                data = json.load(file)
                image_base = os.path.splitext(os.path.basename(data.get("image", "")))[0]
                png_filename = image_base + '.png'
                
                if png_filename not in [listbox_png.get(idx) for idx in range(listbox_png.size())]:
                    listbox_png.insert(tk.END, png_filename)
                    xml_dict[png_filename] = os.path.join(fnf_char_json_directory, image_base + '.xml')
                
                for anim in data.get("animations", []):
                    anim_name = anim.get("name", "")
                    fps = anim.get("fps", 0)
                    user_settings[png_filename + '/' + anim_name] = {'fps': fps}

def fnf_select_char_json_directory(user_settings, xml_dict, listbox_png, listbox_xml):
    fnf_char_json_directory = filedialog.askdirectory(title="Select FNF Character JSON Directory")
    if fnf_char_json_directory:
        fnf_load_char_json_settings(fnf_char_json_directory, user_settings, xml_dict, listbox_png, listbox_xml)
        print("User settings populated:", user_settings)