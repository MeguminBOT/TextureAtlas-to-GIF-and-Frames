import os
import sys
import platform
import shutil

def check_imagemagick_in_path():
    return shutil.which("magick") is not None

def configure_bundled_imagemagick():
    dll_path = os.path.join(os.path.dirname(sys.argv[0]), 'ImageMagick')
    os.environ['PATH'] = dll_path + os.pathsep + os.environ.get('PATH', '')
    os.environ['MAGICK_CODER_MODULE_PATH'] = dll_path
    print("Using bundled ImageMagick.")

if check_imagemagick_in_path():
    print("Using the user's existing ImageMagick.")
else:
    if platform.system() == "Windows":
        print("System ImageMagick not found. Attempting to configure bundled version.")
        configure_bundled_imagemagick()
    else:
        print("No ImageMagick install detected on the system.")

import concurrent.futures
import json
import re
import shutil
import tempfile
import time
import tkinter as tk
import webbrowser
import numpy
import requests
import xml.etree.ElementTree as ET

from tkinter import filedialog, ttk, messagebox
from PIL import Image
from wand.color import Color
from wand.image import Image as WandImg

## Update Checking
def check_for_updates(current_version):
    try:
        response = requests.get('https://raw.githubusercontent.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/main/latestVersion.txt')
        latest_version = response.text.strip()

        if latest_version > current_version:
            root = tk.Tk()
            root.withdraw()
            result = messagebox.askyesno("Update available", "An update is available. Do you want to download it now?")
            if result:
                print("User chose to download the update.")
                webbrowser.open('https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/releases/latest')
                sys.exit()
            else:
                print("User chose not to download the update.")
            root.destroy()
        else:
            print("You are using the latest version of the application.")
    except requests.exceptions.RequestException as err:
        print("No internet connection or something went wrong, could not check for updates.")
        print("Error details:", err)

current_version = '1.9.0'
check_for_updates(current_version)

## File processing
user_settings = {}
spritesheet_settings = {}
xml_dict = {}
temp_dir = tempfile.mkdtemp()
fnf_char_json_directory = ""

def count_spritesheets(directory):
    return sum(1 for filename in os.listdir(directory) if filename.endswith('.xml') or filename.endswith('.txt'))

def sanitize_filename(name):
    return re.sub(r'[\\/:*?"<>|]', '_', name).rstrip()

def clear_filelist():
    listbox_png.delete(0, tk.END)
    listbox_xml.delete(0, tk.END)
    user_settings.clear()

def select_directory(variable, label):
    directory = filedialog.askdirectory()
    if directory:
        variable.set(directory)
        label.config(text=directory)
        
        if variable == input_dir:
            clear_filelist()

            for filename in os.listdir(directory):
                if filename.endswith('.xml') or filename.endswith('.txt'):
                    listbox_png.insert(tk.END, os.path.splitext(filename)[0] + '.png')

            def on_select_png(evt):
                listbox_xml.delete(0, tk.END)

                png_filename = listbox_png.get(listbox_png.curselection())
                base_filename = os.path.splitext(png_filename)[0]
                xml_filename = base_filename + '.xml'
                txt_filename = base_filename + '.txt'

                if os.path.isfile(os.path.join(directory, xml_filename)):
                    parse_xml(directory, xml_filename)
                elif os.path.isfile(os.path.join(directory, txt_filename)):
                    parse_txt(directory, txt_filename)

            listbox_png.bind('<<ListboxSelect>>', on_select_png)
            listbox_png.bind('<Double-1>', on_double_click_png)
            listbox_xml.bind('<Double-1>', on_double_click_xml)
    return directory

def select_files_manually(variable, label):
    global temp_dir
    temp_dir = tempfile.mkdtemp()  # Create a temporary directory
    xml_files = filedialog.askopenfilenames(filetypes=[("XML and TXT files", "*.xml *.txt")])
    png_files = filedialog.askopenfilenames(filetypes=[("PNG files", "*.png")])
    
    variable.set(temp_dir)
    label.config(text=temp_dir)
    
    if xml_files and png_files:
        for file in xml_files:
            shutil.copy(file, temp_dir)
            png_filename = os.path.splitext(os.path.basename(file))[0] + '.png'
            if any(png_filename == os.path.basename(png) for png in png_files):
                if png_filename not in [listbox_png.get(idx) for idx in range(listbox_png.size())]:
                    listbox_png.insert(tk.END, png_filename)
                    xml_dict[png_filename] = os.path.join(temp_dir, os.path.basename(file))
        
        for file in png_files:
            shutil.copy(file, temp_dir)

        listbox_png.unbind('<<ListboxSelect>>')
        listbox_xml.unbind('<Double-1>')

        def on_select_png(evt):
            listbox_xml.delete(0, tk.END)

            selected_png = listbox_png.get(listbox_png.curselection())
            xml_path = xml_dict[selected_png]
            
            if os.path.exists(xml_path):
                tree = ET.parse(xml_path)
                root = tree.getroot()
                names = set()
                for subtexture in root.findall(".//SubTexture"):
                    name = subtexture.get('name')
                    name = re.sub(r'\d{1,4}(?:\.png)?$', '', name).rstrip()
                    names.add(name)
                
                for name in names:
                    listbox_xml.insert(tk.END, name)
        
        listbox_png.bind('<<ListboxSelect>>', on_select_png)
        listbox_xml.bind('<Double-1>', on_double_click_xml)
    return temp_dir

def parse_xml(directory, xml_filename):
    tree = ET.parse(os.path.join(directory, xml_filename))
    root = tree.getroot()
    names = set()
    for subtexture in root.findall(".//SubTexture"):
        name = subtexture.get('name')
        name = re.sub(r'\d{1,4}(?:\.png)?$', '', name).rstrip()
        names.add(name)

    for name in names:
        listbox_xml.insert(tk.END, name)

def parse_txt(directory, txt_filename):
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

def create_settings_window():
    global settings_window
    settings_window = tk.Toplevel()
    settings_window.geometry("400x300")

    settings_canvas = tk.Canvas(settings_window)
    settings_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    settings_scrollbar = tk.Scrollbar(settings_window, orient=tk.VERTICAL, command=settings_canvas.yview)
    settings_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    settings_canvas.config(yscrollcommand=settings_scrollbar.set)
    
    settings_frame = tk.Frame(settings_canvas)
    settings_canvas.create_window((0, 0), window=settings_frame, anchor=tk.NW)
    update_settings_window(settings_frame, settings_canvas)
    settings_frame.update_idletasks()
    settings_canvas.config(scrollregion=settings_canvas.bbox("all"))

def update_settings_window(settings_frame, settings_canvas):
    for widget in settings_frame.winfo_children():
        widget.destroy()

    tk.Label(settings_frame, text="Animation Settings").pack(pady=10)
    for key, value in user_settings.items():
        tk.Label(settings_frame, text=f"{key}: {value}").pack(anchor=tk.W, padx=20)

    tk.Label(settings_frame, text="Spritesheet Settings").pack(pady=10)
    for key, value in spritesheet_settings.items():
        tk.Label(settings_frame, text=f"{key}: {value}").pack(anchor=tk.W, padx=20)

    settings_frame.update_idletasks()
    settings_canvas.config(scrollregion=settings_canvas.bbox("all"))

indices_trans = str.maketrans('','','[] ')
            
def on_double_click_png(evt):
    spritesheet_name = listbox_png.get(listbox_png.curselection())
    new_window = tk.Toplevel()
    new_window.geometry("360x360")

    tk.Label(new_window, text="FPS for " + spritesheet_name).pack()
    fps_entry = tk.Entry(new_window)
    if spritesheet_name in spritesheet_settings:
        fps_entry.insert(0, str(spritesheet_settings[spritesheet_name].get('fps', '')))
    fps_entry.pack()

    tk.Label(new_window, text="Delay for " + spritesheet_name).pack()
    delay_entry = tk.Entry(new_window)
    if spritesheet_name in spritesheet_settings:
        delay_entry.insert(0, str(spritesheet_settings[spritesheet_name].get('delay', '')))
    delay_entry.pack()

    tk.Label(new_window, text="Min period for " + spritesheet_name).pack()
    period_entry = tk.Entry(new_window)
    if spritesheet_name in spritesheet_settings:
        period_entry.insert(0, str(spritesheet_settings[spritesheet_name].get('period', '')))
    period_entry.pack()

    tk.Label(new_window, text="Scale for " + spritesheet_name).pack()
    scale_entry = tk.Entry(new_window)
    if spritesheet_name in spritesheet_settings:
        scale_entry.insert(0, str(spritesheet_settings[spritesheet_name].get('scale', '')))
    scale_entry.pack()

    tk.Label(new_window, text="Threshold for " + spritesheet_name).pack()
    threshold_entry = tk.Entry(new_window)
    if spritesheet_name in spritesheet_settings:
        threshold_entry.insert(0, str(spritesheet_settings[spritesheet_name].get('threshold', '')))
    threshold_entry.pack()

    tk.Label(new_window, text="Indices for " + spritesheet_name).pack()
    indices_entry = tk.Entry(new_window)
    if spritesheet_name in spritesheet_settings:
        indices_entry.insert(0, str(spritesheet_settings[spritesheet_name].get('indices', '')).translate(indices_trans))
    indices_entry.pack()

    tk.Label(new_window, text="Keep frames for " + spritesheet_name).pack()
    frames_entry = tk.Entry(new_window)
    if spritesheet_name in spritesheet_settings:
        frames_entry.insert(0, str(spritesheet_settings[spritesheet_name].get('frames', '')))
    frames_entry.pack()

    def store_input():
        anim_settings = {}
        try:
            if fps_entry.get() != '':
                anim_settings['fps'] = float(fps_entry.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a valid float for FPS.")
            new_window.lift()
            return
        try:
            if delay_entry.get() != '':
                anim_settings['delay'] = int(delay_entry.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a valid integer for delay.")
            new_window.lift()
            return
        try:
            if period_entry.get() != '':
                anim_settings['period'] = int(period_entry.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a valid integer for period.")
            new_window.lift()
            return
        try:
            if scale_entry.get() != '':
                if float(scale_entry.get()) == 0:
                    raise ValueError
                scale = float(scale_entry.get())
                anim_settings['scale'] = scale
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a valid float for scale.")
            new_window.lift()
            return
        try:
            if threshold_entry.get() != '':
                anim_settings['threshold'] = min(max(float(threshold_entry.get()),0),1)
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a valid float between 0 and 1 inclusive for threshold.")
            new_window.lift()
            return
        try:
            if indices_entry.get() != '':
                indices = [int(ele) for ele in indices_entry.get().split(',')]
                anim_settings['indices'] = indices
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a comma-separated list of integers for indices.")
            new_window.lift()
            return
        try:
            if frames_entry.get() != '':
                if not re.fullmatch(r',|all|first|last|first, ?last|none', frames_entry.get().lower()):
                    keep_frames = [ele for ele in frames_entry.get().split(',')]
                    for entry in keep_frames:
                        if not re.fullmatch(r'-?\d+(--?\d+)?', entry):
                            raise ValueError
                anim_settings['frames'] = frames_entry.get().lower()
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a keyword or a comma-separated list of integers or integer ranges for keep frames.")
            new_window.lift()
            return
        if len(anim_settings) > 0:
            spritesheet_settings[spritesheet_name] = anim_settings
        elif spritesheet_settings.get(spritesheet_name):
            spritesheet_settings.pop(spritesheet_name)
        new_window.destroy()

    tk.Button(new_window, text="OK", command=store_input).pack()

            
def on_double_click_xml(evt):
    spritesheet_name = listbox_png.get(listbox_png.curselection())
    animation_name = listbox_xml.get(listbox_xml.curselection())
    full_anim_name = spritesheet_name + '/' + animation_name
    new_window = tk.Toplevel()
    new_window.geometry("360x360")

    tk.Label(new_window, text="FPS for " + animation_name).pack()
    fps_entry = tk.Entry(new_window)
    if full_anim_name in user_settings:
        fps_entry.insert(0, str(user_settings[full_anim_name].get('fps', '')))
    fps_entry.pack()

    tk.Label(new_window, text="Delay for " + animation_name).pack()
    delay_entry = tk.Entry(new_window)
    if full_anim_name in user_settings:
        delay_entry.insert(0, str(user_settings[full_anim_name].get('delay', '')))
    delay_entry.pack()

    tk.Label(new_window, text="Min period for " + animation_name).pack()
    period_entry = tk.Entry(new_window)
    if full_anim_name in user_settings:
        period_entry.insert(0, str(user_settings[full_anim_name].get('period', '')))
    period_entry.pack()

    tk.Label(new_window, text="Scale for " + animation_name).pack()
    scale_entry = tk.Entry(new_window)
    if full_anim_name in user_settings:
        scale_entry.insert(0, str(user_settings[full_anim_name].get('scale', '')))
    scale_entry.pack()

    tk.Label(new_window, text="Threshold for " + animation_name).pack()
    threshold_entry = tk.Entry(new_window)
    if full_anim_name in user_settings:
        threshold_entry.insert(0, str(user_settings[full_anim_name].get('threshold', '')))
    threshold_entry.pack()

    tk.Label(new_window, text="Indices for " + animation_name).pack()
    indices_entry = tk.Entry(new_window)
    if full_anim_name in user_settings:
        indices_entry.insert(0, str(user_settings[full_anim_name].get('indices', '')).translate(indices_trans))
    indices_entry.pack()

    tk.Label(new_window, text="Keep frames for " + animation_name).pack()
    frames_entry = tk.Entry(new_window)
    if full_anim_name in user_settings:
        frames_entry.insert(0, str(user_settings[full_anim_name].get('frames', '')))
    frames_entry.pack()

    def store_input():
        anim_settings = {}
        try:
            if fps_entry.get() != '':
                anim_settings['fps'] = float(fps_entry.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a valid float for FPS.")
            new_window.lift()
            return
        try:
            if delay_entry.get() != '':
                anim_settings['delay'] = int(delay_entry.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a valid integer for delay.")
            new_window.lift()
            return
        try:
            if period_entry.get() != '':
                anim_settings['period'] = int(period_entry.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a valid integer for period.")
            new_window.lift()
            return
        try:
            if scale_entry.get() != '':
                if float(scale_entry.get()) == 0:
                    raise ValueError
                scale = float(scale_entry.get())
                anim_settings['scale'] = scale
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a valid float for scale.")
            new_window.lift()
            return
        try:
            if threshold_entry.get() != '':
                anim_settings['threshold'] = min(max(float(threshold_entry.get()),0),1)
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a valid float between 0 and 1 inclusive for threshold.")
            new_window.lift()
            return
        try:
            if indices_entry.get() != '':
                indices = [int(ele) for ele in indices_entry.get().split(',')]
                anim_settings['indices'] = indices
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a comma-separated list of integers for indices.")
            new_window.lift()
            return
        try:
            if frames_entry.get() != '':
                if not re.fullmatch(r',|all|first|last|first, ?last|none', frames_entry.get().lower()):
                    keep_frames = [ele for ele in frames_entry.get().split(',')]
                    for entry in keep_frames:
                        if not re.fullmatch(r'-?\d+(--?\d+)?', entry):
                            raise ValueError
                anim_settings['frames'] = frames_entry.get().lower()
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a keyword or a comma-separated list of integers or integer ranges for keep frames.")
            new_window.lift()
            return
        if len(anim_settings) > 0:
            user_settings[full_anim_name] = anim_settings
        elif user_settings.get(full_anim_name):
            user_settings.pop(full_anim_name)
        new_window.destroy()

    tk.Button(new_window, text="OK", command=store_input).pack()

def process_directory(input_dir, output_dir, progress_var, tk_root, create_gif, create_webp, set_framerate, set_loopdelay, set_minperiod, set_scale, set_threshold, keep_frames, crop_pngs, var_delay, hq_colors):
    
    total_frames_generated = 0
    total_anims_generated = 0
    total_sprites_failed = 0

    progress_var.set(0)
    total_files = count_spritesheets(input_dir)
    progress_bar["maximum"] = total_files

    if use_all_threads.get():
        cpuThreads = os.cpu_count()
    else:
        cpuThreads = os.cpu_count() // 2

    start_time = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=cpuThreads) as executor:
        futures = []

        for filename in os.listdir(input_dir):
            if filename.endswith('.png'):
                base_filename = filename.rsplit('.', 1)[0]
                xml_path = os.path.join(input_dir, base_filename + '.xml')
                txt_path = os.path.join(input_dir, base_filename + '.txt')

                if os.path.isfile(xml_path) or os.path.isfile(txt_path):
                    sprite_output_dir = os.path.join(output_dir, base_filename)
                    os.makedirs(sprite_output_dir, exist_ok=True)
                    settings = spritesheet_settings.get(filename, {})
                    fps = settings.get('fps', set_framerate)
                    delay = settings.get('delay', set_loopdelay)
                    period = settings.get('period', set_minperiod)
                    frames = settings.get('frames', keep_frames)
                    threshold = settings.get('threshold', set_threshold)
                    scale = settings.get('scale', set_scale)
                    indices = settings.get('indices')
                    future = executor.submit(extract_sprites, os.path.join(input_dir, filename), xml_path if os.path.isfile(xml_path) else txt_path, sprite_output_dir, create_gif, create_webp, fps, delay, period, scale, threshold, indices, frames, crop_pngs, var_delay, hq_colors)
                    futures.append(future)

        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                total_frames_generated += result['frames_generated']
                total_anims_generated += result['anims_generated']
                total_sprites_failed += result['sprites_failed']
            except ET.ParseError as e:
                total_sprites_failed += 1
                messagebox.showerror("Error", f"Something went wrong!!\n{e}")
                if not messagebox.askyesno("Continue?", "Do you want to try continue processing?"):
                    sys.exit()
            except Exception as e:
                total_sprites_failed += 1
                messagebox.showerror("Error", f"Something went wrong!!\n{str(e)}")
                if not messagebox.askyesno("Continue?", "Do you want to try continue processing?"):
                    sys.exit()

            progress_var.set(progress_var.get() + 1)
            tk_root.update_idletasks()

    end_time = time.time()
    duration = end_time - start_time
    minutes, seconds = divmod(duration, 60)

    messagebox.showinfo(
        "Information",
        f"Finished processing all files.\n\n"
        f"Frames Generated: {total_frames_generated}\n"
        f"Animations Generated: {total_anims_generated}\n"
        f"Sprites Failed: {total_sprites_failed}\n\n"
        f"Processing Duration: {int(minutes)} minutes and {int(seconds)} seconds",
    )

## Extraction logic
def extract_sprites(atlas_path, metadata_path, output_dir, create_gif, create_webp, set_framerate, set_loopdelay, set_minperiod, set_scale, set_threshold, set_indices, keep_frames, crop_pngs, var_delay, hq_colors):
    frames_generated = 0
    anims_generated = 0
    sprites_failed = 0
    try:
        atlas = Image.open(atlas_path)

        if metadata_path.endswith('.xml'):
            tree = ET.parse(metadata_path)
            root = tree.getroot()
            sprites = [
                {
                    'name': sprite.get('name'),
                    'x': int(sprite.get('x')),
                    'y': int(sprite.get('y')),
                    'width': int(sprite.get('width')),
                    'height': int(sprite.get('height')),
                    'frameX': int(sprite.get('frameX', 0)),
                    'frameY': int(sprite.get('frameY', 0)),
                    'frameWidth': int(sprite.get('frameWidth', sprite.get('width'))),
                    'frameHeight': int(sprite.get('frameHeight', sprite.get('height'))),
                    'rotated': sprite.get('rotated', 'false') == 'true'
                } for sprite in root.findall('SubTexture')
            ]
        else:
            sprites = parse_plain_text_atlas(metadata_path)

        animations = {}
        quant_frames = {}
        spritesheet_name = os.path.split(atlas_path)[1]

        for sprite in sprites:
            name = sprite['name']
            x, y, width, height = sprite['x'], sprite['y'], sprite['width'], sprite['height']
            frameX = sprite.get('frameX', 0)
            frameY = sprite.get('frameY', 0)
            frameWidth = sprite.get('frameWidth', width)
            frameHeight = sprite.get('frameHeight', height)
            rotated = sprite.get('rotated', False)

            sprite_image = atlas.crop((x, y, x + width, y + height))

            if rotated:
                sprite_image = sprite_image.rotate(90, expand=True)
                frameWidth = max(height-frameX, frameWidth, 1)
                frameHeight = max(width-frameY, frameHeight, 1)
            else:
                frameWidth = max(width-frameX, frameWidth, 1)
                frameHeight = max(height-frameY, frameHeight, 1)

            frame_image = Image.new('RGBA', (frameWidth, frameHeight))
            frame_image.paste(sprite_image, (-frameX, -frameY))

            if frame_image.mode != 'RGBA':
                frame_image = frame_image.convert('RGBA')
            folder_name = re.sub(r'\d{1,4}(?:\.png)?$', '', name).rstrip()

            animations.setdefault(folder_name, []).append((name, frame_image, (x, y, width, height, frameX, frameY)))

        for animation_name, image_tuples in animations.items():
            settings = user_settings.get(spritesheet_name + '/' + animation_name, {})
            scale = settings.get('scale', set_scale)
            image_tuples.sort(key=lambda x: x[0])

            indices = settings.get('indices', set_indices)

            if indices:
                indices = list(filter(lambda i: ((i < len(image_tuples)) & (i >= 0)), indices))
                image_tuples = [image_tuples[i] for i in indices]

            single_frame = True
            for i in image_tuples:
                if i[2] != image_tuples[0][2]:
                    single_frame = False
                    break

            if single_frame:
                kept_frames = '0'
            else:
                kept_frames = settings.get('frames', keep_frames)
                if kept_frames == 'all':
                    kept_frames = '0--1'
                elif kept_frames == 'first':
                    kept_frames = '0'
                elif kept_frames == 'last':
                    kept_frames = '-1'
                elif re.fullmatch(r'first, ?last', kept_frames):
                    kept_frames = '0,-1'
                elif kept_frames == 'none':
                    kept_frames = ''
                kept_frames = [ele for ele in kept_frames.split(',')]

            kept_frame_indices = set()
            for entry in kept_frames:
                try:
                    frame_index = int(entry)
                    if frame_index < 0:
                       frame_index += len(image_tuples)
                    if frame_index >= 0 and frame_index < len(image_tuples):
                       kept_frame_indices.add(frame_index)
                except ValueError:
                    if entry != '':
                        start_frame = int(re.match(r'-?\d+', entry).group())
                        if start_frame < 0:
                           start_frame += len(image_tuples)
                        end_frame = int(re.search(r'(?<=-)-?\d+$', entry).group())
                        if end_frame < 0:
                           end_frame += len(image_tuples)
                        if (start_frame < 0 and end_frame < 0) or (start_frame >= len(image_tuples) and end_frame >= len(image_tuples)):
                            continue
                        frame_range = range(max(start_frame,0),min(end_frame+1,len(image_tuples)))
                        for i in frame_range:
                            kept_frame_indices.add(i)

            if single_frame:
                frame_filename = os.path.join(output_dir, os.path.splitext(spritesheet_name)[0] + f" {animation_name}.png")
                if len(image_tuples) == 0:
                    continue
                frame_image = image_tuples[0][1]
                bbox = frame_image.getbbox()
                if bbox is None:
                    continue
                if bbox:
                    final_frame_image = scale_image(frame_image.crop(bbox), scale)
                final_frame_image.save(frame_filename)
                frames_generated += 1
                continue
            else:
                frames_folder = os.path.join(output_dir, animation_name)
                for index, frame in enumerate(image_tuples):
                    frame_filename = os.path.join(frames_folder, image_tuples[index][0] + '.png')
                    if index in kept_frame_indices:
                        frame_image = image_tuples[index][1]
                        bbox = frame_image.getbbox()
                        if bbox is None:
                            continue
                        if crop_pngs and bbox:
                            final_frame_image = scale_image(frame_image.crop(bbox), scale)
                        else:
                            final_frame_image = scale_image(frame_image, scale)
                        os.makedirs(frames_folder, exist_ok=True)
                        final_frame_image.save(frame_filename)
                        frames_generated += 1
                    
            if create_gif or create_webp:
                fps = settings.get('fps', set_framerate)
                delay = settings.get('delay', set_loopdelay)
                period = settings.get('period', set_minperiod)
                threshold = settings.get('threshold', min(max(set_threshold,0),1))
                images = [img[1] for img in image_tuples]
                sizes = [frame.size for frame in images]
                max_size = tuple(map(max, zip(*sizes)))
                min_size = tuple(map(min, zip(*sizes)))
                if max_size != min_size:
                    for index, frame in enumerate(images):
                        new_frame = Image.new('RGBA', max_size)
                        new_frame.paste(frame)
                        images[index] = new_frame

                if create_webp:
                    durations = []
                    if var_delay:
                        for index in range(len(images)):
                            durations.append(round((index+1)*1000/fps) - round(index*1000/fps))
                    else:
                        durations = [round(1000/fps)] * len(images)
                    durations[-1] += delay
                    durations[-1] += max(period - sum(durations), 0)
                    scaled_images = list(map(lambda x: scale_image(x, scale), images))

                    scaled_images[0].save(os.path.join(output_dir, os.path.splitext(spritesheet_name)[0] + f" {animation_name}.webp"), save_all=True, append_images=images[1:], disposal=2, duration=durations, loop=0, lossless=True)

                if create_gif:
                    for frame in images:
                        alpha = frame.getchannel('A')
                        if (threshold == 1):
                            alpha = alpha.point(lambda i: i >= 255 and 255)
                        else:
                            alpha = alpha.point(lambda i: i > 255*threshold and 255)
                        frame.putalpha(alpha)
                    min_x, min_y, max_x, max_y = float('inf'), float('inf'), 0, 0

                    for index, frame in enumerate(images):
                        bbox = frame.getbbox()
                        if bbox is None:
                            continue
                        min_x = min(min_x, bbox[0])
                        min_y = min(min_y, bbox[1])
                        max_x = max(max_x, bbox[2])
                        max_y = max(max_y, bbox[3])
    
                        if not hq_colors:
                            continue

                        if image_tuples[index][2] + (threshold,) in quant_frames:
                            images[index] = quant_frames[image_tuples[index][2] + (threshold,)]
                            if images[index].size != max_size:
                                new_frame = Image.new('RGBA', max_size)
                                new_frame.paste(frame)
                                images[index] = new_frame
                        else:
                            with WandImg.from_array(numpy.array(frame)) as wand_frame:
                                wand_frame.background_color = Color('None')
                                wand_frame.alpha_channel = 'background'
                                wand_frame.trim(background_color='None')
                                if wand_frame.colors > 256:
                                    wand_frame.quantize(number_colors=256, dither=False)
                                wand_frame.coalesce()
                                fd, temp_filename = tempfile.mkstemp(suffix='.gif')
                                wand_frame.save(filename=temp_filename)
                                with Image.open(temp_filename) as quant_frame:
                                    images[index] = quant_frame
                                    quant_frame.load()
                                    quant_frames[image_tuples[index][2] + (threshold,)] = quant_frame
                                os.close(fd)
                                os.remove(temp_filename)
                        
                    width, height = max_x - min_x, max_y - min_y
                    cropped_images = []
                    for frame in images:
                        cropped_frame = frame.crop((min_x, min_y, max_x, max_y))
                        cropped_images.append(scale_image(cropped_frame, scale))
                    durations = []
                    if var_delay:
                        for index in range(len(images)):
                            durations.append(round((index+1)*1000/fps, -1) - round(index*1000/fps, -1))
                    else:
                        durations = [round(1000/fps, -1)] * len(cropped_images)
                    durations[-1] += delay
                    durations[-1] += max(round(period, -1) - sum(durations), 0)
                    cropped_images[0].save(os.path.join(output_dir, os.path.splitext(spritesheet_name)[0] + f" {animation_name}.gif"), save_all=True, append_images=cropped_images[1:], disposal=2, optimize=False, duration=durations, loop=0, comment=f'GIF generated by: TextureAtlas to GIF and Frames v{current_version}')

                anims_generated += 1

        return {
            'frames_generated': frames_generated,
            'anims_generated': anims_generated,
            'sprites_failed': sprites_failed
        }

    except ET.ParseError:
        sprites_failed += 1
        raise ET.ParseError(f"Badly formatted XML file:\n\n{metadata_path}")
    except Exception as e:
        if "Coordinate '" in str(e) and "' is less than '" in str(e):
            sprites_failed += 1
            raise Exception(f"XML or TXT frame dimension data doesn't match the spritesheet dimensions.\n\nError: {str(e)}\n\nFile: {metadata_path}\n\nThis error can also occur from Alpha Threshold being set too high.")
        elif "'NoneType' object is not subscriptable" in str(e):
            sprites_failed += 1
            raise Exception(f"XML or TXT frame dimension data doesn't match the spritesheet dimensions.\n\nError: {str(e)}\n\nFile: {metadata_path}")
        else:
            sprites_failed += 1
            raise Exception(f"An error occurred: {str(e)}.\n\nFile:{metadata_path}")

def scale_image(img, size):
    if size < 0:
        img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if abs(size) == 1:
        return img
    else:
        new_width_float = img.width * abs(size)
        new_height_float = img.height * abs(size)

        new_width = round(new_width_float)
        new_height = round(new_height_float)
        return img.resize((new_width, new_height), Image.NEAREST)

## FNF specific stuff
def fnf_load_char_json_settings(fnf_char_json_directory):
    global user_settings
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

def fnf_select_char_json_directory():
    fnf_char_json_directory = filedialog.askdirectory(title="Select FNF Character JSON Directory")
    if fnf_char_json_directory:
        fnf_load_char_json_settings(fnf_char_json_directory)
        # print("User settings populated:", user_settings)

## Help Menu
def create_scrollable_help_window():
    help_text = (
        "_________________________________________ Main Window _________________________________________\n\n"
        "Double clicking a spritesheet entry will open up a window where you can override the global fps/loop/alpha settings and customize indices used for all the animations in that spritesheet.\n\n"
        "Double clicking an animation entry will open up a window where you can override the global and spritesheets' fps/loop/alpha settings and customize indices used for that animation.\n\n"
        "Select Directory with Spritesheets:\nOpens a file dialog for you to choose a folder containing the spritesheets you want to process.\n\n"
        "Select Save Directory:\nOpens a file dialog for you to specify where the application should save the exported frames or GIF/WebP files.\n\n"
        "Create GIFs for Each Animation:\nWhen enabled, generates animated .GIF files for each animation found in the spritesheet data.\n\n"
        "Create WebPs for Each Animation:\nWhen enabled, generates animated .WebP files for each animation found in the spritesheet data.\n\n"
        "Frame Rate (fps):\nDefines the playback speed of the animated image in frames per second.\n\n"
        "Loop Delay (ms):\nSets the minimum delay time, in milliseconds, before the animation loops again.\n\n"
        "Minimum Period (ms):\nSets the minimum duration, in milliseconds, before the animation loops again.\n\n"
        "Scale:\nResizes frames and animations using nearest-neighbor interpolation to preserve pixels. Negative numbers flip the sprites horizontally.\n\n"
        "Alpha Threshold (GIFs only):\nThis setting adjusts the level of transparency applied to pixels in GIF images.\nThe threshold value determines the cutoff point for transparency.\nPixels with an alpha value below this threshold become fully transparent, while those above the threshold become fully opaque.\n\n"
        "Indices (not available in global settings):\nSelect the frame indices to use in the animation by typing a comma-separated list of non-negative integers.\n\n"
        "Keep Individual Frames:\nSelect the frames of the animation to save by typing 'all', 'first', 'last', 'none', or a comma-separated list of integers or integer ranges. Negative numbers count from the final frame.\n\n"
        "Crop Individual Frames:\nCrops every extracted png frame. (This doesn't affect GIFs,  WebP's or single frame animations)\n\n"
        "Show User Settings:\nOpens a window displaying a list of animations and spritesheets with settings that override the global configuration.\n\n"
        "Start Process:\nBegins the tasks you have selected for processing.\n\n"
        "_________________________________________ Menubar: File _________________________________________\n\n"
        "Select Directory:\nOpens a file dialog for you to choose a folder containing the spritesheets you want to process.\n\n"
        "Select Files:\nOpens a file dialog for you to manually choose spritesheet .XML/TXT and .PNG files.\n\n"
        "Clear Filelist and User settings:\nRemoves all entries from the list and clears the settings.\n\n"
        "Exit:\nExits the application\n\n"
        "_________________________________________ Menubar: Import _________________________________________\n\n"
        "(FNF) Import FPS from character json:\nOpens a file dialog for you to choose the folder containing the json files of your characters to automatically set the correct fps values of each animation.\nFPS values are added to the User Settings.\n\n"
        "*NOT YET IMPLEMENTED* (FNF) Set idle loop delay to 0:\nSets all animations containing the phrase 'idle' to have no delay before looping. Usually recommended.\n\n"
        "_________________________________________ Menubar: Advanced _________________________________________\n\n"
        "Higher Color Quality (GIFs only):\nWhen enabled, use Wand to achieve better colors. May increase processing time.\n\n"
        "Variable Delay:\nWhen enabled, vary the delays of each frame slightly to more accurately reach the desired fps.\n\n"
        "Use All CPU Threads:\nWhen checked, the application utilizes all available CPU threads. When unchecked, it uses only half of the available CPU threads.\n\n"
    )

    help_window = tk.Toplevel()
    help_window.geometry("800x600")
    help_window.title("Help")

    main_frame = ttk.Frame(help_window)
    main_frame.pack(fill=tk.BOTH, expand=1)

    canvas = tk.Canvas(main_frame)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

    scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    scrollable_frame = ttk.Frame(canvas)
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

    help_label = tk.Label(scrollable_frame, text=help_text, justify="left", padx=10, pady=10, wraplength=780)
    help_label.pack()
    
def create_scrollable_fnf_help_window():
    fnf_help_text = (
        "Use the import fps button to get the correct framerate from the character json files. (Make sure you select spritesheet directory first)\n\n"
        "Loop delay:\n"
        "For anything that doesn't need to smoothly loop like sing poses for characters, 250 ms is recommended (100 ms minimum)\n"
        "Idle animations usually looks best with 0"
        "Idle animations usually looks best with 0, some do look better with 150-250ms."
        "If unsure about the loop delay, start by leaving it at default, start processing, then inspect the generated gifs.\n"
        "Doesn't look good? Just double click the animation name in the application and change the delay and start processing again."
    )

    fnf_help_window = tk.Toplevel()
    fnf_help_window.geometry("800x600")
    fnf_help_window.title("Help (FNF Sprites)")

    fnf_main_frame = ttk.Frame(fnf_help_window)
    fnf_main_frame.pack(fill=tk.BOTH, expand=1)

    fnf_canvas = tk.Canvas(fnf_main_frame)
    fnf_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

    fnf_scrollbar = ttk.Scrollbar(fnf_main_frame, orient=tk.VERTICAL, command=fnf_canvas.yview)
    fnf_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    fnf_canvas.configure(yscrollcommand=fnf_scrollbar.set)
    fnf_canvas.bind('<Configure>', lambda e: fnf_canvas.configure(scrollregion=fnf_canvas.bbox("all")))

    fnf_scrollable_frame = ttk.Frame(fnf_canvas)
    fnf_canvas.create_window((0, 0), window=fnf_scrollable_frame, anchor="nw")

    fnf_help_label = tk.Label(fnf_scrollable_frame, text=fnf_help_text, justify="left", padx=10, pady=10, wraplength=780)
    fnf_help_label.pack()

## Remove temp dir on exit
def on_closing():
    if temp_dir and os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    root.destroy()

## Graphical User Interface setup
root = tk.Tk()

script_dir = os.path.dirname(__file__)
icon_path = os.path.join(script_dir, 'assets', 'icon.png')
icon = tk.PhotoImage(file=icon_path)
root.iconphoto(True, icon)

menubar = tk.Menu(root)
root.title("TextureAtlas to GIF and Frames")
root.geometry("900x560")
root.resizable(False, False)
root.protocol("WM_DELETE_WINDOW", on_closing)
root.config(menu=menubar)

file_menu = tk.Menu(menubar, tearoff=0)
file_menu.add_command(label="Select directory", command=lambda: select_directory(input_dir, input_dir_label) and user_settings.clear())
file_menu.add_command(label="Select files", command=lambda: select_files_manually(input_dir, input_dir_label))
file_menu.add_command(label="Clear filelist and user settings", command=lambda: clear_filelist())
file_menu.add_separator()
file_menu.add_command(label="Exit", command=on_closing)
menubar.add_cascade(label="File", menu=file_menu)

import_menu = tk.Menu(menubar, tearoff=0)
import_menu.add_command(label="FNF: Import FPS from character json", command=lambda: fnf_select_char_json_directory())
menubar.add_cascade(label="Import", menu=import_menu)

help_menu = tk.Menu(menubar, tearoff=0)
help_menu.add_command(label="Manual", command=lambda: create_scrollable_help_window())
help_menu.add_separator()
help_menu.add_command(label="FNF: GIF/WebP settings advice", command=lambda: create_scrollable_fnf_help_window())
menubar.add_cascade(label="Help", menu=help_menu)

better_colors = tk.BooleanVar()
variable_delay = tk.BooleanVar()
use_all_threads = tk.BooleanVar()

advanced_menu = tk.Menu(menubar, tearoff=0)
advanced_menu.add_checkbutton(label="Higher color quality", variable=better_colors)
advanced_menu.add_checkbutton(label="Variable delay", variable=variable_delay)
advanced_menu.add_checkbutton(label="Use all CPU threads", variable=use_all_threads)
menubar.add_cascade(label="Advanced", menu=advanced_menu)

progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(root, length=865, variable=progress_var)
progress_bar.pack(pady=8)

scrollbar_png = tk.Scrollbar(root)
scrollbar_png.pack(side=tk.LEFT, fill=tk.Y)

listbox_png = tk.Listbox(root, width=30, exportselection=0, yscrollcommand=scrollbar_png.set)
listbox_png.pack(side=tk.LEFT, fill=tk.Y)

scrollbar_xml = tk.Scrollbar(root)
scrollbar_xml.pack(side=tk.LEFT, fill=tk.Y)

listbox_xml = tk.Listbox(root, width=30, yscrollcommand=scrollbar_xml.set)
listbox_xml.pack(side=tk.LEFT, fill=tk.Y)

scrollbar_png.config(command=listbox_png.yview)
scrollbar_xml.config(command=listbox_xml.yview)

input_dir = tk.StringVar()
input_button = tk.Button(root, text="Select directory with spritesheets", cursor="hand2", command=lambda: select_directory(input_dir, input_dir_label) and user_settings.clear())
input_button.pack(pady=2)

input_dir_label = tk.Label(root, text="No input directory selected")
input_dir_label.pack(pady=4)

output_dir = tk.StringVar()
output_button = tk.Button(root, text="Select save directory", cursor="hand2", command=lambda: select_directory(output_dir, output_dir_label))
output_button.pack(pady=2)

output_dir_label = tk.Label(root, text="No output directory selected")
output_dir_label.pack(pady=4)

create_gif = tk.BooleanVar()
gif_checkbox = tk.Checkbutton(root, text="Create GIFs for each animation", variable=create_gif)
gif_checkbox.pack()

create_webp = tk.BooleanVar()
webp_checkbox = tk.Checkbutton(root, text="Create WebPs for each animation", variable=create_webp)
webp_checkbox.pack()

set_framerate = tk.DoubleVar(value=24)
frame_rate_label = tk.Label(root, text="Frame Rate (fps):")
frame_rate_label.pack()
frame_rate_entry = tk.Entry(root, textvariable=set_framerate)
frame_rate_entry.pack()

set_loopdelay = tk.DoubleVar(value=250)
loopdelay_label = tk.Label(root, text="Loop Delay (ms):")
loopdelay_label.pack()
loopdelay_entry = tk.Entry(root, textvariable=set_loopdelay)
loopdelay_entry.pack()

set_minperiod = tk.DoubleVar(value=0)
minperiod_label = tk.Label(root, text="Minimum Period (ms):")
minperiod_label.pack()
minperiod_entry = tk.Entry(root, textvariable=set_minperiod)
minperiod_entry.pack()

set_scale = tk.DoubleVar(value=1)
scale_label = tk.Label(root, text="Scale:")
scale_label.pack()
scale_entry = tk.Entry(root, textvariable=set_scale)
scale_entry.pack()

set_threshold = tk.DoubleVar(value=0.5)
threshold_label = tk.Label(root, text="Alpha Threshold:")
threshold_label.pack()
threshold_entry = tk.Entry(root, textvariable=set_threshold)
threshold_entry.pack()

keep_frames = tk.StringVar(value='all')
keepframes_label = tk.Label(root, text="Keep individual frames:")
keepframes_label.pack()
keepframes_entry = tk.Entry(root, textvariable=keep_frames)
keepframes_entry.pack(pady=2)

crop_pngs = tk.BooleanVar()
crop_pngs_checkbox = tk.Checkbutton(root, text="Crop individual frames", variable=crop_pngs)
crop_pngs_checkbox.pack(pady=1)

button_frame = tk.Frame(root)
button_frame.pack(pady=8)

show_user_settings = tk.Button(button_frame, text="Show User Settings", command=create_settings_window)
show_user_settings.pack(side=tk.LEFT, padx=4)

process_button = tk.Button(button_frame, text="Start process", cursor="hand2", command=lambda: process_directory(input_dir.get(), output_dir.get(), progress_var, root, create_gif.get(), create_webp.get(), set_framerate.get(), set_loopdelay.get(), set_minperiod.get(), set_scale.get(), set_threshold.get(), keep_frames.get(), crop_pngs.get(), variable_delay.get(), better_colors.get()))
process_button.pack(side=tk.LEFT, padx=2)

author_label = tk.Label(root, text="Project started by AutisticLulu")
author_label.pack(side='bottom')

## Source Code
def contributeLink(url):
    webbrowser.open_new(url)

linkSourceCode = "https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames"
link1 = tk.Label(root, text="If you wish to contribute to the project, click here!", fg="blue", cursor="hand2")
link1.pack(side='bottom')
link1.bind("<Button-1>", lambda e: contributeLink(linkSourceCode))

## Main loop
root.mainloop()
