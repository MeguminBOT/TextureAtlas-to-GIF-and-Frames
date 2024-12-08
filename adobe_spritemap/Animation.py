""" 
Code taken from PluieElectrique's Texture Atlas Renderer. 
Repository: https://github.com/PluieElectrique/texture-atlas-renderer

Will be edited to fit TextureAtlas to GIF and Frames functionality.
"""

import json
import os

from PIL import Image

# Import our local modules
from SpriteAtlas import SpriteAtlas
from Symbols import Symbols

try:
    from tqdm import trange
except ImportError:
    trange = range


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
        
    def render_to_png_sequence(self, output_dir):
        os.makedirs(output_dir, exist_ok=True)

        for symbol_name in self.symbols.timelines.keys():
            symbol_output_dir = os.path.join(output_dir, symbol_name)
            os.makedirs(symbol_output_dir, exist_ok=True)
            symbol_length = self.symbols.length(symbol_name)
            for frame_idx in trange(symbol_length, unit="fr", desc=f"Rendering PNG frames for {symbol_name}"):
                try:
                    frame = self.symbols.render_symbol(symbol_name, frame_idx)

                    if frame is None:
                        print(f"Frame {frame_idx} is empty!")
                        continue

                    # Save the frame
                    frame_file = os.path.join(symbol_output_dir, f"frame_{frame_idx:04d}.png")
                    frame.save(frame_file, format="PNG")
                    print(f"Saved frame {frame_idx} to {frame_file}")
                except Exception as e:
                    print(f"Error rendering frame {frame_idx} for symbol {symbol_name}: {e}")