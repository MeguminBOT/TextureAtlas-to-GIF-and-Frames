import json
from PIL import Image
import os
import re
import xml.etree.ElementTree as ET

import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import chardet

def parse_spritemap(spritemap_file):

    print("Parsing spritemap file...")

    try:

        with open(spritemap_file, 'r') as f:

            data = json.load(f)
        atlas = data['ATLAS']
        sprites = atlas['SPRITES']
        sprite_dict = {}
        for sprite in sprites:
            sprite_data = sprite['SPRITE']
            sprite_dict[sprite_data['name']] = {
                'x': sprite_data['x'],
                'y': sprite_data['y'],
                'w': sprite_data['w'],
                'h': sprite_data['h'],
                'rotated': sprite_data['rotated']
            }
        return sprite_dict
    except json.JSONDecodeError as e:
        with open('error.txt', 'w') as f:
            f.write(f"ErroADr parsing JSON file: {str(e)}\n")
    except Exception as e:
        with open('error.txt', 'w') as f:
            f.write(f"ErrASDSAor: {str(e)}\n")
            f.write(f"Spritemap file: {spritemap_file}\n")

def parse_animation(animation_file):
    try:
        with open(animation_file, 'r') as f:
            data = json.load(f)
        
        if 'ANIMATION' in data:
            animation = data['ANIMATION']
            timeline = animation['TIMELINE']
            layers = timeline['LAYERS']
            layer = layers[0]
            frames = layer['Frames']
            frame_dict = {}
            
            for frame in frames:
                frame_dict[frame['index']] = {
                    'name': frame['name'],
                    'duration': frame['duration'],
                    'elements': []
                }
                
                for element in frame['elements']:
                    symbol_instance = element['SYMBOL_Instance']
                    decomposed_matrix = symbol_instance.get('DecomposedMatrix', {})
                    position = decomposed_matrix.get('Position', {})
                    rotation = decomposed_matrix.get('Rotation', {})
                    scaling = decomposed_matrix.get('Scaling', {})
                    
                    frame_dict[frame['index']]['elements'].append({
                        'symbol_name': symbol_instance['SYMBOL_name'],
                        'instance_name': symbol_instance['Instance_Name'],
                        'symbol_type': symbol_instance['symbolType'],
                        'first_frame': symbol_instance['firstFrame'],
                        'loop': symbol_instance['loop'],
                        'transformation_point': symbol_instance['transformationPoint'],
                        'matrix3d': symbol_instance['Matrix3D'],
                        'decomposed_matrix': {
                            'position': position,
                            'rotation': rotation,
                            'caling': scaling
                        }
                    })
        else:
            animation = data['AN']
            timeline = animation['TL']
            layers = timeline['L']
            layer = layers[0]
            frames = layer['FR']
            frame_dict = {}
            
            for frame in frames:
                frame_dict[frame['I']] = {
                    'name': '',
                    'duration': frame['DU'],
                    'elements': []
                }
                
                for element in frame['E']:
                    symbol_instance = element['SI']
                    transformation = {
                        'x': symbol_instance['TRP']['x'],
                        'y': symbol_instance['TRP']['y'],
                        'scaleX': 1,
                        'scaleY': 1,
                        'skewX': 0,
                        'skewY': 0,
                        'rotationX': 0,
                        'rotationY': 0,
                        'rotationZ': 0
                    }
                    
                    frame_dict[frame['I']]['elements'].append({
                        'symbol_name': symbol_instance['SN'],
                        'instance_name': symbol_instance['IN'],
                        'symbol_type': symbol_instance['ST'],
                        'first_frame': symbol_instance['FF'],
                        'loop': symbol_instance['LP'],
                        'transformation_point': transformation
                    })
        
        return frame_dict
    except json.JSONDecodeError as e:
        with open('errorAnim.txt', 'w') as f:
            f.write(f"ErroADr parsing JSON file: {str(e)}\n")
    except Exception as e:
        with open('errorAnim.txt', 'w') as f:
            f.write(f"ErrASDSAor: {str(e)}\n")
            f.write(f"Anim file: {animation_file}\n")

def extract_sprites(atlas_path, spritemap_file, animation_file, output_dir, create_gif, create_webp):
    try:
        atlas = Image.open(atlas_path)
        frame_dict = parse_animation(animation_file)
        sprite_dict = parse_spritemap(spritemap_file)

        print("Sprite dict:", sprite_dict)
        print("fRAME dict:", frame_dict)
        
        for frame_index, frame_data in frame_dict.items():
            frame_name = frame_data['name']
            elements = frame_data['elements']
            
            frame_images = []
            for element in elements:
                symbol_name = element['symbol_name']
                sprite_data = sprite_dict.get(symbol_name)
                if sprite_data:
                    x, y, w, h = sprite_data['x'], sprite_data['y'], sprite_data['w'], sprite_data['h']
                    rotated = sprite_data['rotated']
                    
                    sprite_image = atlas.crop((x, y, x + w, y + h))
                    if rotated:
                        sprite_image = sprite_image.rotate(90, expand=True)
                    
                    frame_images.append(sprite_image)
            
            if frame_images:
                folder_name = re.sub(r'\d{1,4}(?:\.png)?$', '', frame_name).rstrip()
                sprite_folder = os.path.join(output_dir, folder_name)
                os.makedirs(sprite_folder, exist_ok=True)
                
                for i, frame_image in enumerate(frame_images):
                    frame_image.save(os.path.join(sprite_folder, f"{frame_name}_{i}.png"))
                
                if create_gif or create_webp:
                    durations = [frame_data['duration']] * len(frame_images)
                    if create_gif:
                        frame_images[0].save(os.path.join(output_dir, f"{frame_name}.gif"), save_all=True, append_images=frame_images[1:], duration=durations, loop=0)
                    if create_webp:
                        frame_images[0].save(os.path.join(output_dir, f"{frame_name}.webp"), save_all=True, append_images=frame_images[1:], duration=durations, loop=0, lossless=True)
    except Exception as e:
        with open('error.txt', 'w') as f:
            f.write(str(e))

if __name__ == "__main__":

    try:

        atlas_path = "spritemap1.png"

        spritemap_file = "spritemap1.json"

        animation_file = "spritemap1anim.json"

        output_dir = "spritemap1"

        create_gif = True

        create_webp = True

        

        extract_sprites(atlas_path, spritemap_file, animation_file, output_dir, create_gif, create_webp)

    except Exception as e:

        print("Error:", str(e))

    input("Press Enter to close...")