""" 
Code taken from PluieElectrique's Texture Atlas Renderer. 
Repository: https://github.com/PluieElectrique/texture-atlas-renderer

Will be edited to fit TextureAtlas to GIF and Frames functionality.
"""

import json
import os

from PIL import Image

# Import our local modules
import SpriteAtlas
import Symbols

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
        
    def render_to_png_sequence(self, output_dir, symbol_name=None):
        os.makedirs(output_dir, exist_ok=True)

        symbol_length = self.symbols.length(symbol_name)
        for frame_idx in trange(symbol_length, unit="fr", desc="Rendering PNG frames"):
            try:
                frame = self.symbols.render_symbol(symbol_name, frame_idx)

                if frame is None:
                    print(f"Frame {frame_idx} is empty!")
                    continue

                # Save the frame
                frame_file = os.path.join(output_dir, f"frame_{frame_idx:04d}.png")
                frame.save(frame_file, format="PNG")
                print(f"Saved frame {frame_idx} to {frame_file}")
            except Exception as e:
                print(f"Error rendering frame {frame_idx}: {e}")

    def render_to_gif(self, output_file, symbol_name=None):
        symbol_length = self.symbols.length(symbol_name)
        frames = []
        frame_duration=41

        for frame_idx in trange(symbol_length, unit="fr", desc="Rendering GIF frames"):
            try:
                frame = self.symbols.render_symbol(symbol_name, frame_idx)

                if frame is None:
                    print(f"Frame {frame_idx} is empty!")
                    continue

                # Ensure frame is in RGBA mode
                if frame.mode != "RGBA":
                    frame = frame.convert("RGBA")

                # Set transparent background
                transparent_frame = Image.new("RGBA", frame.size)
                transparent_frame.paste(frame, mask=frame)
                frames.append(transparent_frame)
            except Exception as e:
                print(f"Error rendering frame {frame_idx}: {e}")

        if frames:
            # Save the frames as an animated GIF
            frames[0].save(
                output_file,
                save_all=True,
                append_images=frames[1:],  # Subsequent frames
                duration=frame_duration,  # Frame duration in milliseconds
                loop=0,  # Loop infinitely
                transparency=0,  # Set the first palette index as transparent
                disposal=2,  # Clear frame to transparent before drawing the next
            )
            print(f"GIF saved to {output_file}")
        else:
            print("No frames were rendered. GIF was not created.")