import os
import re
import tkinter as tk

def parse_txt(directory, txt_filename, listbox_xml):
    names = set()
    with open(os.path.join(directory, txt_filename), 'r') as file:
        for line in file:
            parts = line.split(' = ')[0]
            name = re.sub(r'\d{1,4}(?:\.png)?$', '', parts).rstrip()
            names.add(name)

    for name in names:
        listbox_xml.insert(tk.END, name)
        
def parse_plain_text_atlas(file_path):
    sprites = []
    with open(file_path, 'r') as file:
        for line in file:
            parts = line.split(' = ')
            name = parts[0].strip()
            x, y, width, height = map(int, parts[1].split())
            sprites.append({'name': name, 'x': x, 'y': y, 'width': width, 'height': height})
    return sprites