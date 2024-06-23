import concurrent.futures
import os
import re
import requests
import sys
import webbrowser
import xml.etree.ElementTree as ET

from PIL import Image
import tkinter as tk
from tkinter import filedialog, ttk, messagebox

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

current_version = '1.6.0'
check_for_updates(current_version)

## File processing
def count_xml_files(directory):
    return sum(1 for filename in os.listdir(directory) if filename.endswith('.xml'))

def sanitize_filename(name):
    return re.sub(r'[\\/:*?"<>|]', '_', name).rstrip()

def select_directory(variable, label):
    directory = filedialog.askdirectory()
    if directory:
        variable.set(directory)
        label.config(text=directory)
        
        if variable == input_dir:
            listbox_png.delete(0, tk.END)
            listbox_xml.delete(0, tk.END)

            for filename in os.listdir(directory):
                if filename.endswith('.xml'):
                    listbox_png.insert(tk.END, os.path.splitext(filename)[0] + '.png')

            def on_select_png(evt):
                listbox_xml.delete(0, tk.END)

                png_filename = listbox_png.get(listbox_png.curselection())
                xml_filename = os.path.splitext(png_filename)[0] + '.xml'

                tree = ET.parse(os.path.join(directory, xml_filename))
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
    return directory
            
def on_double_click_xml(evt):
    spritesheet_name = listbox_png.get(listbox_png.curselection())
    animation_name = listbox_xml.get(listbox_xml.curselection())
    new_window = tk.Toplevel()
    new_window.geometry("360x240")

    tk.Label(new_window, text="FPS for " + animation_name).pack()
    fps_entry = tk.Entry(new_window)
    fps_entry.pack()

    tk.Label(new_window, text="Delay for " + animation_name).pack()
    delay_entry = tk.Entry(new_window)
    delay_entry.pack()

    tk.Label(new_window, text="Threshold for " + animation_name).pack()
    threshold_entry = tk.Entry(new_window)
    threshold_entry.pack()

    tk.Label(new_window, text="Indices for " + animation_name).pack()
    indices_entry = tk.Entry(new_window)
    indices_entry.pack()

    def store_input():
        anim_settings = {}

        try:
            if fps_entry.get() != '':
                anim_settings['fps'] = float(fps_entry.get())
            if delay_entry.get() != '':
                anim_settings['delay'] = int(delay_entry.get())
            if threshold_entry.get() != '':
                anim_settings['threshold'] = float(threshold_entry.get())
            if indices_entry.get() != '':
                indices = [int(ele) for ele in indices_entry.get().split(',')]
                anim_settings['indices'] = indices
            if len(anim_settings) > 0:
                user_settings[spritesheet_name + '/' + animation_name] = anim_settings
            elif user_settings.get(spritesheet_name + '/' + animation_name):
                user_settings.pop(spritesheet_name + '/' + animation_name)
            new_window.destroy()
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a valid integer for FPS and delay.")
            new_window.lift()

    tk.Button(new_window, text="OK", command=store_input).pack()
user_settings = {}

def process_directory(input_dir, output_dir, progress_var, tk_root, create_gif, create_webp, keep_frames, set_framerate, set_loopdelay, set_threshold):
    if not (create_gif or create_webp or keep_frames):
        return
    progress_var.set(0)
    total_files = count_xml_files(input_dir)
    progress_bar["maximum"] = total_files

    max_workers = os.cpu_count() // 2
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []

        for filename in os.listdir(input_dir):
            if filename.endswith('.png'):
                xml_filename = filename.rsplit('.', 1)[0] + '.xml'
                xml_path = os.path.join(input_dir, xml_filename)

                if os.path.isfile(xml_path):
                    sprite_output_dir = os.path.join(output_dir, filename.rsplit('.', 1)[0])
                    os.makedirs(sprite_output_dir, exist_ok=True)
                    future = executor.submit(extract_sprites, os.path.join(input_dir, filename), xml_path, sprite_output_dir, create_gif, create_webp, keep_frames, set_framerate, set_loopdelay, set_threshold)
                    futures.append(future)

        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except ET.ParseError as e:
                messagebox.showerror("Error", f"Something went wrong!!\n{e}")
                if not messagebox.askyesno("Continue?", "Do you want to try continue processing?"):
                    sys.exit()
            except Exception as e:
                messagebox.showerror("Error", f"Something went wrong!!\n{str(e)}")
                if not messagebox.askyesno("Continue?", "Do you want to try continue processing?"):
                    sys.exit()

            progress_var.set(progress_var.get() + 1)
            tk_root.update_idletasks()

    messagebox.showinfo("Information","Finished processing all files.")

## Extraction logic
def extract_sprites(atlas_path, xml_path, output_dir, create_gif, create_webp, keep_frames, set_framerate, set_loopdelay, set_threshold):
    try:
        atlas = Image.open(atlas_path)
        tree = ET.parse(xml_path)
        root = tree.getroot()
        animations = {}
        spritesheet_name = os.path.split(atlas_path)[1]

        for sprite in root.findall('SubTexture'):
            name = sprite.get('name')
            x, y, width, height = map(int, (sprite.get(attr) for attr in ('x', 'y', 'width', 'height')))
            frameX = int(sprite.get('frameX', 0))
            frameY = int(sprite.get('frameY', 0))
            frameWidth = max(int(sprite.get('frameWidth', width)), 1)
            frameHeight = max(int(sprite.get('frameHeight', height)), 1)
            rotated = sprite.get('rotated', 'false') == 'true'

            sprite_image = atlas.crop((x, y, x + width, y + height))
            if rotated: 
                sprite_image = sprite_image.rotate(90, expand=True)

            frame_image = Image.new('RGBA', (frameWidth, frameHeight))
            frame_image.paste(sprite_image, (-frameX, -frameY))

            if frame_image.mode != 'RGBA':
                frame_image = frame_image.convert('RGBA')
            folder_name = re.sub(r'\d{1,4}(?:\.png)?$', '', name).rstrip()
            sprite_folder = os.path.join(output_dir, folder_name)
            os.makedirs(sprite_folder, exist_ok=True)

            frame_image.save(os.path.join(sprite_folder, f"{name}.png"))

            if create_gif or create_webp:
                animations.setdefault(folder_name, []).append(frame_image)

        for animation_name, images in animations.items():
            settings = user_settings.get(spritesheet_name + '/' + animation_name, {})
            fps = settings.get('fps', set_framerate)
            delay = settings.get('delay', set_loopdelay)
            threshold = settings.get('threshold', set_threshold)
            indices = settings.get('indices')
            if indices:
                indices = list(filter(lambda i: ((i < len(images)) & (i >= 0)), indices))
                images = [images[i] for i in indices]
            sizes = [frame.size for frame in images]
            max_size = tuple(map(max, zip(*sizes)))
            min_size = tuple(map(min, zip(*sizes)))
            if max_size != min_size:
                for index, frame in enumerate(images):
                    images[index] = Image.new('RGBA', max_size)
                    images[index].paste(frame)

            if create_webp:
                durations = [round(1000/fps)] * len(images)
                durations[-1] += delay
                images[0].save(os.path.join(output_dir, os.path.splitext(spritesheet_name)[0] + f" {animation_name}.webp"), save_all=True, append_images=images[1:], disposal=2, duration=durations, loop=0, lossless=True)

            if create_gif:
                for frame in images:
                    alpha = frame.getchannel('A')
                    alpha = alpha.point(lambda i: i > 255*threshold and 255)
                    frame.putalpha(alpha)
                durations = [round(1000/fps)] * len(images)
                durations[-1] += delay
                images[0].save(os.path.join(output_dir, os.path.splitext(spritesheet_name)[0] + f" {animation_name}.gif"), save_all=True, append_images=images[1:], disposal=2, optimize=False, duration=durations, loop=0)
            
            if not keep_frames:
                frames_folder = os.path.join(output_dir, animation_name)
                for i in os.listdir(frames_folder):
                    os.remove(os.path.join(frames_folder, i))
                os.rmdir(frames_folder)

    except ET.ParseError:
        raise ET.ParseError(f"Badly formatted XML file:\n{xml_path}")
    except Exception as e:
        raise Exception(f"An error occurred: {str(e)}")

## Graphical User Interface setup
root = tk.Tk()
root.title("TextureAtlas to GIF and Frames")
root.geometry("900x480")
root.resizable(False, False)

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

keep_frames = tk.BooleanVar()
frame_checkbox = tk.Checkbutton(root, text="Keep individual frames", variable=keep_frames)
frame_checkbox.pack()

set_framerate = tk.DoubleVar(value=24)
frame_rate_label = tk.Label(root, text="Frame Rate (fps):")
frame_rate_label.pack()
frame_rate_entry = tk.Entry(root, textvariable=set_framerate)
frame_rate_entry.pack()

set_loopdelay = tk.DoubleVar(value=0)
loopdelay_label = tk.Label(root, text="Loop Delay (ms):")
loopdelay_label.pack()
loopdelay_entry = tk.Entry(root, textvariable=set_loopdelay)
loopdelay_entry.pack()

set_threshold = tk.DoubleVar(value=0.5)
threshold_label = tk.Label(root, text="Alpha Threshold:")
threshold_label.pack()
threshold_entry = tk.Entry(root, textvariable=set_threshold)
threshold_entry.pack()

process_button = tk.Button(root, text="Start process", cursor="hand2", command=lambda: process_directory(input_dir.get(), output_dir.get(), progress_var, root, create_gif.get(), create_webp.get(), keep_frames.get(), set_framerate.get(), set_loopdelay.get(), set_threshold.get()))
process_button.pack(pady=8)

author_label = tk.Label(root, text="Tool written by AutisticLulu")
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
