import tkinter as tk
from tkinter import filedialog
from PIL import Image
from Animation import Animation
import json
import os

def browse_directory(entry):
    directory = filedialog.askdirectory()
    entry.delete(0, tk.END)
    entry.insert(0, directory)

def extract_sprites():
    animation_dir = animation_dir_entry.get().replace("\\", "/")
    output_dir = output_dir_entry.get().replace("\\", "/")
    canvas_size = (int(canvas_width_entry.get()), int(canvas_height_entry.get()))
    resample = RESAMPLE_FILTERS[resample_var.get()]
    export_all = export_all_var.get()
    
    anim = Animation(animation_dir, canvas_size, resample)
    anim.render_to_png_sequence(output_dir=output_dir, export_all=export_all)

def load_animation_data():
    animation_dir = animation_dir_entry.get().replace("\\", "/")
    animation_json_path = os.path.join(animation_dir, "Animation.json")
    
    if not os.path.exists(animation_json_path):
        print("Animation.json not found in the specified directory.")
        return
    
    with open(animation_json_path) as f:
        animation_json = json.load(f)
    
    global symbol_names
    symbol_names = [(symbol["SN"], max(frame["I"] + frame["DU"] for layer in symbol["TL"]["L"] for frame in layer["FR"])) for symbol in animation_json["SD"]["S"]]
    timeline_names = [timeline["LN"] for timeline in animation_json["AN"]["TL"]["L"]]
    
    update_symbol_listbox()
    
    timeline_listbox.delete(0, tk.END)
    for name in timeline_names:
        timeline_listbox.insert(tk.END, name)

def update_symbol_listbox():
    symbol_listbox.delete(0, tk.END)
    for name, frames in symbol_names:
        symbol_listbox.insert(tk.END, f"{name} ({frames} frames)")

def sort_by_name():
    global symbol_names, sort_name_ascending
    symbol_names = sorted(symbol_names, key=lambda x: x[0], reverse=not sort_name_ascending)
    sort_name_ascending = not sort_name_ascending
    update_symbol_listbox()

def sort_by_frames():
    global symbol_names, sort_frames_ascending
    symbol_names = sorted(symbol_names, key=lambda x: x[1], reverse=not sort_frames_ascending)
    sort_frames_ascending = not sort_frames_ascending
    update_symbol_listbox()

if __name__ == "__main__":
    RESAMPLE_FILTERS = {
        "nearest": Image.NEAREST,
        "bilinear": Image.BILINEAR,
        "bicubic": Image.BICUBIC,
    }

    root = tk.Tk()
    root.title("Adobe Spritemap to PNG (BETA)")

    tk.Label(root, text="Spritemap Directory:").grid(row=0, column=0, padx=10, pady=5)
    animation_dir_entry = tk.Entry(root, width=50)
    animation_dir_entry.grid(row=0, column=1, padx=10, pady=5)
    tk.Button(root, text="Browse", command=lambda: browse_directory(animation_dir_entry)).grid(row=0, column=2, padx=10, pady=5)

    tk.Label(root, text="Output Directory:").grid(row=1, column=0, padx=10, pady=5)
    output_dir_entry = tk.Entry(root, width=50)
    output_dir_entry.grid(row=1, column=1, padx=10, pady=5)
    tk.Button(root, text="Browse", command=lambda: browse_directory(output_dir_entry)).grid(row=1, column=2, padx=10, pady=5)

    tk.Label(root, text="Canvas Width:").grid(row=2, column=0, padx=10, pady=5)
    canvas_width_entry = tk.Entry(root, width=10)
    canvas_width_entry.insert(0, "4096")
    canvas_width_entry.grid(row=2, column=1, padx=10, pady=5, sticky='w')

    tk.Label(root, text="Canvas Height:").grid(row=3, column=0, padx=10, pady=5)
    canvas_height_entry = tk.Entry(root, width=10)
    canvas_height_entry.insert(0, "4096")
    canvas_height_entry.grid(row=3, column=1, padx=10, pady=5, sticky='w')

    tk.Label(root, text="Resample Filter:").grid(row=4, column=0, padx=10, pady=5)
    resample_var = tk.StringVar(value="bicubic")
    resample_menu = tk.OptionMenu(root, resample_var, *RESAMPLE_FILTERS.keys())
    resample_menu.grid(row=4, column=1, padx=10, pady=5, sticky='w')

    export_all_var = tk.BooleanVar(value=False)
    export_all_checkbox = tk.Checkbutton(root, text="Include single frame symbols", variable=export_all_var)
    export_all_checkbox.grid(row=5, column=0, columnspan=3, pady=5)

    tk.Button(root, text="Extract Spritemap", command=extract_sprites).grid(row=6, column=0, columnspan=3, pady=20)

    tk.Button(root, text="Load Animation Data", command=load_animation_data).grid(row=7, column=0, columnspan=3, pady=20)

    tk.Label(root, text="Symbols:").grid(row=8, column=0, padx=10, pady=5)
    symbol_listbox = tk.Listbox(root, width=50, height=10)
    symbol_listbox.grid(row=8, column=1, padx=10, pady=5)

    tk.Button(root, text="Sort by Name", command=sort_by_name).grid(row=9, column=0, padx=10, pady=5)
    tk.Button(root, text="Sort by Frames", command=sort_by_frames).grid(row=9, column=1, padx=10, pady=5)

    tk.Label(root, text="Timelines:").grid(row=10, column=0, padx=10, pady=5)
    timeline_listbox = tk.Listbox(root, width=50, height=10)
    timeline_listbox.grid(row=10, column=1, padx=10, pady=5)

    sort_name_ascending = True
    sort_frames_ascending = True

    root.mainloop()