import os
import re
import xml.etree.ElementTree as ET
import tkinter as tk

def parse_xml(directory, xml_filename, listbox_xml):
    tree = ET.parse(os.path.join(directory, xml_filename))
    root = tree.getroot()
    names = set()
    for subtexture in root.findall(".//SubTexture"):
        name = subtexture.get('name')
        name = re.sub(r'\d{1,4}(?:\.png)?$', '', name).rstrip()
        names.add(name)

    for name in names:
        listbox_xml.insert(tk.END, name)
