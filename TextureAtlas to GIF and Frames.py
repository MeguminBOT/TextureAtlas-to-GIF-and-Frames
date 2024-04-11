import os
import re
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageSequence
import xml.etree.ElementTree as ET

def select_directory(variable):
    directory = filedialog.askdirectory()
    if directory:
        variable.set(directory)

def count_png_files(directory):
    return sum(1 for filename in os.listdir(directory) if filename.endswith('.png'))

def extract_sprites(atlas_path, xml_path, output_dir, create_gif, create_webp):
    atlas = Image.open(atlas_path)
    tree = ET.parse(xml_path)
    root = tree.getroot()
    animations = {}

    for sprite in root.findall('SubTexture'):
        name = sprite.get('name')
        x, y, width, height = map(int, (sprite.get(attr) for attr in ('x', 'y', 'width', 'height')))
        frameX = int(sprite.get('frameX', 0))
        frameY = int(sprite.get('frameY', 0))
        frameWidth = int(sprite.get('frameWidth', width))
        frameHeight = int(sprite.get('frameHeight', height))
        rotated = sprite.get('rotated', 'false') == 'true'

        sprite_image = atlas.crop((x, y, x + width, y + height))
        if rotated: 
            sprite_image = sprite_image.rotate(90, expand=True)

        frame_image = Image.new('RGBA', (frameWidth, frameHeight))
        frame_image.paste(sprite_image, (-frameX, -frameY))

        if frame_image.mode != 'RGBA':
            frame_image = frame_image.convert('RGBA')

        frame_image.save(os.path.join(output_dir, f"{name}.png"))

        if create_gif or create_webp:
            animation_name = re.sub(r'\d+$', '', name)
            animations.setdefault(animation_name, []).append(frame_image)

    if create_gif:
        for animation_name, images in animations.items():
            images[0].save(os.path.join(output_dir, f"_{animation_name}.gif"), save_all=True, append_images=images[1:], disposal=2, optimize=False, duration=1000/24, loop=0)

    if create_webp:
        for animation_name, images in animations.items():
            images[0].save(os.path.join(output_dir, f"_{animation_name}.webp"), save_all=True, append_images=images[1:], disposal=2, optimize=False, duration=1000/24, loop=0)

def process_directory(input_dir, output_dir, progress_var, tk_root, create_gif, create_webp):
    progress_var.set(0)
    total_files = count_png_files(input_dir)
    progress_bar["maximum"] = total_files

    for filename in os.listdir(input_dir):
        if filename.endswith('.png'):
            xml_filename = filename.rsplit('.', 1)[0] + '.xml'
            xml_path = os.path.join(input_dir, xml_filename)
            
            if os.path.isfile(xml_path):
                sprite_output_dir = os.path.join(output_dir, filename.rsplit('.', 1)[0])
                os.makedirs(sprite_output_dir, exist_ok=True)
                extract_sprites(os.path.join(input_dir, filename), xml_path, sprite_output_dir, create_gif, create_webp)
                progress_var.set(progress_var.get() + 1)
                tk_root.update_idletasks()
    
    messagebox.showinfo("Information","Finished processing all files.")

root = tk.Tk()
root.title("TextureAtlas to GIF and Frames")

input_dir = tk.StringVar()
output_dir = tk.StringVar()
progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(root, length=200, variable=progress_var)
progress_bar.pack()

input_button = tk.Button(root, text="Select directory with spritesheets", command=lambda: select_directory(input_dir))
input_button.pack()

output_button = tk.Button(root, text="Select save directory", command=lambda: select_directory(output_dir))
output_button.pack()

create_gif = tk.BooleanVar()
gif_checkbox = tk.Checkbutton(root, text="Create GIFs for each animation", variable=create_gif)
gif_checkbox.pack()

create_webp = tk.BooleanVar()
webp_checkbox = tk.Checkbutton(root, text="Create WebPs for each animation", variable=create_webp)
webp_checkbox.pack()

process_button = tk.Button(root, text="DO MAGIC!!", command=lambda: process_directory(input_dir.get(), output_dir.get(), progress_var, root, create_gif.get(), create_webp.get()))
process_button.pack()

author_label = tk.Label(root, text="Tool written by AutisticLulu")
author_label.pack(side='bottom')

root.mainloop()
