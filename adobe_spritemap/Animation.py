""" 
Code taken from PluieElectrique's Texture Atlas Renderer. 
Repository: https://github.com/PluieElectrique/texture-atlas-renderer

Will be edited to fit TextureAtlas to GIF and Frames functionality.
"""

import json
import os
import re
import psutil

from PIL import Image

# Import our local modules
from SpriteAtlas import SpriteAtlas
from Symbols import Symbols

try:
    from tqdm import trange
except ImportError:
    trange = range


# Temporary function to sanitize filenames, will be replaced with the one in the utilities.py later on
def sanitize_filename(name):
    """Sanitize the symbol name to be a valid filename."""
    return re.sub(r'[\\/*?:"<>|]', "_", name)

class Animation:
    """Render a texture atlas animation (or one particular symbol)."""

    def __init__(self, animation_dir, canvas_size, resample):
        """Create an Animation from a texture atlas export directory."""
        with open(os.path.join(animation_dir, "Animation.json")) as f:
            animation_json = json.load(f)

        with open(os.path.join(animation_dir, "spritemap1.json"), "rb") as f:
            # json can't handle BOM
            spritemap_json = json.loads(f.read().decode("utf-8-sig"))

        spritemap_img = Image.open(os.path.join(animation_dir, "spritemap1.png"))

        self.frame_rate = animation_json["MD"]["FRT"]
        self.sprite_atlas = SpriteAtlas(
            spritemap_json, spritemap_img, canvas_size, resample
        )
        self.symbols = Symbols(
            animation_json, self.sprite_atlas, canvas_size
        )


    def render_to_png_sequence(self, output_dir, export_all, initial_batch_size=24, memory_threshold=0.5):
        os.makedirs(output_dir, exist_ok=True)

        for symbol_name in self.symbols.timelines.keys():
            if symbol_name is None:
                continue

            sanitized_symbol_name = sanitize_filename(symbol_name)
            symbol_length = self.symbols.length(symbol_name)
            batch_size = initial_batch_size

            for batch_start in range(0, symbol_length, batch_size):
                images = []
                batch_end = min(batch_start + batch_size, symbol_length)

                for frame_idx in trange(batch_start, batch_end, unit="fr", desc=f"Rendering PNG frames for {symbol_name}"):
                    try:
                        frame = self.symbols.render_symbol(symbol_name, frame_idx)

                        if frame is None:
                            print(f"Frame {frame_idx} is empty!")
                            continue

                        images.append((frame_idx, frame))
                    except Exception as e:
                        print(f"Error rendering frame {frame_idx} for symbol {symbol_name}: {e}")

                if images:
                    if not export_all and len(images) == 1:
                        print(f"Skipping symbol {symbol_name} with only one frame.")
                        continue

                    symbol_output_dir = os.path.join(output_dir, sanitized_symbol_name)
                    os.makedirs(symbol_output_dir, exist_ok=True)

                    sizes = [frame.size for _, frame in images]
                    max_size = tuple(map(max, zip(*sizes)))
                    min_size = tuple(map(min, zip(*sizes)))
                    if max_size != min_size:
                        for index, (frame_idx, frame) in enumerate(images):
                            new_frame = Image.new('RGBA', max_size)
                            offset = ((max_size[0] - frame.size[0]) // 2, (max_size[1] - frame.size[1]) // 2)
                            new_frame.paste(frame, offset)
                            images[index] = (frame_idx, new_frame)

                    min_x, min_y, max_x, max_y = float('inf'), float('inf'), 0, 0
                    for _, frame in images:
                        bbox = frame.getbbox()
                        if bbox:
                            min_x = min(min_x, bbox[0])
                            min_y = min(min_y, bbox[1])
                            max_x = max(max_x, bbox[2])
                            max_y = max(max_y, bbox[3])

                    if min_x > max_x:
                        continue

                    cropped_images = []
                    for frame_idx, frame in images:
                        cropped_frame = frame.crop((min_x, min_y, max_x, max_y))
                        cropped_images.append((frame_idx, cropped_frame))

                    for frame_idx, frame in cropped_images:
                        frame_file = os.path.join(symbol_output_dir, f"{sanitized_symbol_name}_{frame_idx:04d}.png")
                        frame.save(frame_file, format="PNG")
                        print(f"Saved frame {frame_idx} to {frame_file}")

                # Adjust batch size based on memory usage
                memory_usage = psutil.virtual_memory().percent / 100
                if memory_usage > memory_threshold:
                    batch_size = max(1, batch_size // 2)
                else:
                    batch_size = min(initial_batch_size, batch_size * 2)