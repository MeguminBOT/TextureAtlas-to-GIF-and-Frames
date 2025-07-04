import json
import os
import tkinter as tk
from PIL import Image
import numpy as np
from functools import lru_cache

# Try to import Wand, but make it optional
try:
    from wand.image import Image as WandImage
    from wand.color import Color as WandColor
    WAND_AVAILABLE = True
except ImportError:
    WAND_AVAILABLE = False
    print("Warning: Wand (ImageMagick) not available. Advanced spritemap features may be limited.")


class TransformMatrix:
    """2D affine transformation matrix."""

    def __init__(self, m=None, a=1, b=0, c=0, d=0, e=1, f=0):
        if m is None:
            # Standard 2D affine transformation matrix:
            # [[a, b, c],
            #  [d, e, f],
            #  [0, 0, 1]]
            # where a,b,c,d,e,f correspond to the standard affine parameters
            self.m = np.array([[a, b, c], [d, e, f], [0, 0, 1]], dtype=np.float64)
        else:
            self.m = m

    @classmethod
    def parse(cls, m):
        """Parse transformation matrix from various formats."""
        if isinstance(m, dict):
            return cls(a=m["a"], b=m["b"], c=m["c"], d=m["d"], e=m["e"], f=m["f"])
        elif isinstance(m, list) and len(m) >= 6:
            # Handle list format: [a, b, c, d, e, f]
            return cls(a=m[0], b=m[1], c=m[2], d=m[3], e=m[4], f=m[5])
        else:
            # Return identity matrix if format is unknown
            return cls()

    def data(self):
        """Return a data tuple for Pillow's affine transformation."""
        # Pillow expects (a, b, c, d, e, f) where:
        # x' = a*x + b*y + c
        # y' = d*x + e*y + f
        # Our matrix is [[a, b, c], [d, e, f], [0, 0, 1]]
        # So we need to return (a, b, c, d, e, f)
        return (self.m[0, 0], self.m[0, 1], self.m[0, 2], 
                self.m[1, 0], self.m[1, 1], self.m[1, 2])

    def __eq__(self, other):
        return type(other) is TransformMatrix and self.m.tobytes() == other.m.tobytes()

    def __hash__(self):
        return hash(self.m.tobytes())

    def __matmul__(self, other):
        if type(other) is not TransformMatrix:
            return NotImplemented
        return TransformMatrix(self.m @ other.m)

    def __repr__(self):
        return f"TransformMatrix({self.m!r})"


class ColorEffect:
    """Color effects for RGBA images."""

    def __init__(self, effect=None):
        # None is a no-op effect
        self.effect = effect

    @classmethod
    def parse(cls, effect):
        """Create a ColorEffect from a `C` dictionary."""
        try:
            if not isinstance(effect, dict) or "M" not in effect:
                return cls()  # Return no-op effect for invalid data
                
            mode = effect["M"]
            if mode == "AD":  # Alpha and color transformation
                # Check if all required keys are present
                required_keys = ["AM", "RM", "GM", "BM", "AO", "RO", "GO", "BO"]
                if all(key in effect for key in required_keys):
                    return cls(("AD", effect["AM"], effect["RM"], effect["GM"], effect["BM"],
                               effect["AO"], effect["RO"], effect["GO"], effect["BO"]))
            return cls()  # Return no-op effect for unknown modes or missing data
        except Exception:
            return cls()  # Return no-op effect on any error

    def __call__(self, im):
        # An effect of None will return the input image.
        if self.effect is not None:
            mode, am, rm, gm, bm, ao, ro, go, bo = self.effect
            if mode == "AD":
                # Apply color transformation
                r, g, b, a = im.split()
                r = r.point(lambda x: min(255, max(0, int(x * rm + ro))))
                g = g.point(lambda x: min(255, max(0, int(x * gm + go))))
                b = b.point(lambda x: min(255, max(0, int(x * bm + bo))))
                a = a.point(lambda x: min(255, max(0, int(x * am + ao))))
                im = Image.merge("RGBA", (r, g, b, a))
        return im

    def __eq__(self, other):
        if type(other) is not ColorEffect:
            return False
        elif self.effect is None or other.effect is None:
            return self.effect == other.effect
        else:
            return self.effect == other.effect

    def __hash__(self):
        if self.effect is None:
            return hash(None)
        else:
            return hash(self.effect)

    def __matmul__(self, other):
        if type(other) is not ColorEffect:
            return NotImplemented
        
        # ColorEffects are immutable, so it's fine to not always return a new instance.
        if self.effect is None:
            return other
        elif other.effect is None:
            return self
        else:
            # For simplicity, just return the first effect
            return self

    def __repr__(self):
        return f"ColorEffect({self.effect!r})"


class SpritemapAtlas:
    """Extract and transform sprites from a spritemap."""

    def __init__(self, spritemap_json, img, canvas_size, resample=Image.NEAREST):
        if img.mode == "P":
            img = img.convert("RGBA")
        # Keep as RGBA instead of RGBa to avoid PNG save issues
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        self.img = img
        self.canvas_width, self.canvas_height = canvas_size
        self.resample = resample
        self.sprite_info = {}
        self.sprites = {}

        for sprite in spritemap_json["ATLAS"]["SPRITES"]:
            sprite = sprite["SPRITE"]
            x = sprite["x"]
            y = sprite["y"]
            w = sprite["w"]
            h = sprite["h"]
            self.sprite_info[sprite["name"]] = {
                "box": (x, y, x + w, y + h),
                "rotated": sprite["rotated"],
            }

    @lru_cache(maxsize=1024)
    def get_sprite(self, name, m, color_effect):
        """Get a transformed sprite."""
        if name not in self.sprite_info:
            return Image.new("RGBA", (self.canvas_width, self.canvas_height))
        
        info = self.sprite_info[name]
        sprite = self.img.crop(info["box"])
        
        if info["rotated"]:
            sprite = sprite.rotate(-90, expand=True)
        
        # Apply color effect
        sprite = color_effect(sprite)
        
        # Transform sprite
        if m:
            transform_data = m.data()
            sprite = sprite.transform(
                (self.canvas_width, self.canvas_height),
                Image.AFFINE,
                transform_data,
                resample=self.resample
            )
        
        return sprite


class SpritemapSymbols:
    """Render symbols and timelines from spritemap animations."""

    def __init__(self, animation_json, sprite_atlas, canvas_size):
        self.background_color = (0, 0, 0, 0)
        self.canvas_size = canvas_size
        self.sprite_atlas = sprite_atlas
        self.timelines = {}
        self.main_timeline = None
        
        # Store animation timelines (AN) - these are the actual animations to extract
        if "AN" in animation_json:
            animations = animation_json["AN"]
            
            if isinstance(animations, dict):
                # Single animation
                if "TL" in animations and "L" in animations["TL"]:
                    anim_name = animations.get("name", "MainTimeline")
                    self.timelines[anim_name] = animations["TL"]["L"]
                    self.main_timeline = animations["TL"]["L"]
                    print(f"[SpritemapSymbols] Stored animation timeline: {anim_name}")
            
            elif isinstance(animations, list):
                # Multiple animations
                for i, animation in enumerate(animations):
                    if "TL" in animation and "L" in animation["TL"]:
                        anim_name = animation.get("name", f"Animation_{i}")
                        self.timelines[anim_name] = animation["TL"]["L"]
                        if i == 0:  # First animation as main
                            self.main_timeline = animation["TL"]["L"]
                        print(f"[SpritemapSymbols] Stored animation timeline: {anim_name}")

        # Store symbol timelines as fallback (for compatibility with symbols that represent animations)
        if "SD" in animation_json and "S" in animation_json["SD"]:
            for symbol in animation_json["SD"]["S"]:
                if "SN" in symbol and "TL" in symbol:
                    symbol_name = symbol["SN"]
                    timeline = symbol["TL"]
                    if "L" in timeline:
                        # Only store symbol timelines if no animation timelines were found
                        # or if this symbol has meaningful content (multi-frame animation)
                        if not self.timelines:
                            total_frames = 0
                            for layer in timeline["L"]:
                                if "FR" in layer:
                                    for frame in layer["FR"]:
                                        total_frames += frame.get("DU", 1)
                            
                            if total_frames > 1:  # Only meaningful animations
                                self.timelines[symbol_name] = timeline["L"]
                                print(f"[SpritemapSymbols] Stored symbol timeline: {symbol_name}")

        # Store main timeline as fallback if nothing else was found
        if not self.timelines and "AN" in animation_json and "TL" in animation_json["AN"]:
            main_tl = animation_json["AN"]["TL"]
            if "L" in main_tl:
                self.main_timeline = main_tl["L"]
                self.timelines["MainTimeline"] = self.main_timeline
                print("[SpritemapSymbols] Stored fallback main timeline")

        # Don't apply centering transformation by default - let sprites render at their specified positions
        self.center_in_canvas = TransformMatrix()  # Identity matrix

    def length(self, timeline_name):
        """The length of a timeline is the index of its final frame."""
        timeline = self.get_timeline(timeline_name)
        if not timeline:
            return 0
            
        length = 0
        for layer in timeline:
            if "FR" in layer:
                for frame in layer["FR"]:
                    length = max(length, frame["I"] + frame["DU"])
        return length

    def get_timeline(self, timeline_name):
        """Get the timeline data for a given timeline name."""
        if timeline_name == "MainTimeline" and self.main_timeline:
            print(f"[SpritemapSymbols] Using main timeline for: {timeline_name}")
            return self.main_timeline
        elif timeline_name in self.timelines:
            print(f"[SpritemapSymbols] Found timeline for: {timeline_name}")
            return self.timelines[timeline_name]
        else:
            print(f"[SpritemapSymbols] No timeline found for: {timeline_name}, available: {list(self.timelines.keys())}")
            return None

    def render_timeline(self, timeline_name, frame_idx):
        """Render a timeline (or symbol) at a specific frame."""
        timeline = self.get_timeline(timeline_name)
        if not timeline:
            return Image.new("RGBA", self.canvas_size, self.background_color)
            
        canvas = Image.new("RGBA", self.canvas_size, self.background_color)
        self._render_timeline_frame(canvas, timeline, frame_idx, self.center_in_canvas, ColorEffect())
        return canvas

    def render_symbol(self, name, frame_idx):
        """Render a symbol (on a certain frame) to an image. Kept for compatibility."""
        return self.render_timeline(name, frame_idx)

    def _render_timeline_frame(self, canvas, timeline, frame_idx, m, color):
        """Render a specific frame of a timeline."""
        print(f"[SpritlemapSymbols] Rendering timeline frame {frame_idx}")
        for i, layer in enumerate(timeline):
            print(f"[SpritlemapSymbols] Processing layer {i}")
            if "FR" not in layer:
                print(f"[SpritlemapSymbols] Layer {i} has no frames (FR)")
                continue
                
            for j, frame in enumerate(layer["FR"]):
                frame_start = frame["I"]
                frame_duration = frame["DU"] 
                frame_end = frame_start + frame_duration
                print(f"[SpritlemapSymbols] Frame {j}: start={frame_start}, duration={frame_duration}, end={frame_end}, checking frame_idx={frame_idx}")
                
                if frame_start <= frame_idx < frame_end:
                    print(f"[SpritlemapSymbols] Frame {j} is active for frame_idx {frame_idx}")
                    if "E" in frame:
                        elements = frame["E"]
                        print(f"[SpritlemapSymbols] Frame {j} has {len(elements)} elements")
                        for k, element in enumerate(elements):
                            print(f"[SpritlemapSymbols] Processing element {k}: {list(element.keys())}")
                            self._render_element(canvas, element, frame_idx - frame_start, m, color)
                    else:
                        print(f"[SpritlemapSymbols] Frame {j} has no elements (E)")
                else:
                    print(f"[SpritlemapSymbols] Frame {j} is not active for frame_idx {frame_idx}")

    def _render_symbol(self, canvas, name, frame_idx, m, color):
        """Recursively render a symbol and its children. Kept for compatibility."""
        timeline = self.get_timeline(name)
        if timeline:
            self._render_timeline_frame(canvas, timeline, frame_idx, m, color)

    def _render_element(self, canvas, element, relative_frame_idx, m, color):
        """Render a timeline element (sprite instance or animated symbol instance)."""
        print(f"[SpritlemapSymbols] _render_element called with element keys: {list(element.keys())}")
        
        if "SI" in element:  # Sprite Instance
            si = element["SI"]
            print(f"[SpritlemapSymbols] Processing Sprite Instance: {list(si.keys())}")
            
            if "SN" not in si:
                print(f"[SpritlemapSymbols] No sprite name (SN) in SI, skipping")
                return  # Skip if no sprite name
                
            sprite_name = si["SN"]
            print(f"[SpritlemapSymbols] Sprite name: '{sprite_name}'")
            
            # Get transformation matrix
            element_m = m
            if "M3D" in si:
                print(f"[SpritlemapSymbols] Found M3D transformation: {si['M3D']}")
                element_m = element_m @ TransformMatrix.parse(si["M3D"])
            else:
                print(f"[SpritlemapSymbols] No M3D transformation found")
            
            # Get color effect
            element_color = color
            if "C" in si:
                print(f"[SpritlemapSymbols] Found color effect")
                element_color = element_color @ ColorEffect.parse(si["C"])
            else:
                print(f"[SpritlemapSymbols] No color effect")
            
            print(f"[SpritlemapSymbols] Getting sprite '{sprite_name}' from atlas...")
            # Render sprite
            sprite = self.sprite_atlas.get_sprite(sprite_name, element_m, element_color)
            print(f"[SpritlemapSymbols] Got sprite, checking content...")
            
            if sprite:
                # Check if sprite has content
                bbox = sprite.getbbox()
                print(f"[SpritlemapSymbols] Sprite bbox: {bbox}")
                if bbox:
                    print(f"[SpritlemapSymbols] Pasting sprite to canvas...")
                    canvas.paste(sprite, (0, 0), sprite)
                    print(f"[SpritlemapSymbols] Successfully rendered sprite '{sprite_name}' with bbox: {bbox}")
                else:
                    print(f"[SpritlemapSymbols] Sprite '{sprite_name}' has empty bbox")
            else:
                print(f"[SpritlemapSymbols] Could not get sprite '{sprite_name}' - sprite is None")
        
        elif "ASI" in element:  # Animated Symbol Instance
            print(f"[SpritlemapSymbols] Processing Animated Symbol Instance")
            asi = element["ASI"]
            if "SN" not in asi:
                return  # Skip if no symbol name
            symbol_name = asi["SN"]
            
            # Calculate frame for nested symbol
            nested_frame = relative_frame_idx
            if "FF" in asi:  # First Frame
                nested_frame += asi["FF"]
            
            # Get transformation matrix
            element_m = m
            if "M3D" in asi:
                element_m = element_m @ TransformMatrix.parse(asi["M3D"])
            
            # Get color effect
            element_color = color
            if "C" in asi:
                element_color = element_color @ ColorEffect.parse(asi["C"])
            
            # Recursively render nested symbol
            print(f"[SpritlemapSymbols] Rendering nested symbol '{symbol_name}' at frame {nested_frame}")
            self._render_symbol(canvas, symbol_name, nested_frame, element_m, element_color)
        else:
            print(f"[SpritlemapSymbols] Unknown element type: {list(element.keys())}")


class SpritlemapParser:
    """
    A class to parse Adobe Animate spritemap directories and extract animation data.
    
    Handles the full spritemap format with Animation.json and spritemap1.json files,
    rendering the symbols into individual frames for use with the TextureAtlas workflow.
    """

    def __init__(self, directory, listbox_data):
        self.directory = directory
        self.listbox_data = listbox_data

    def get_data(self):
        """Extract animation names from the spritemap directory."""
        animation_json_path = os.path.join(self.directory, "Animation.json")
        
        if not os.path.exists(animation_json_path):
            return
        
        with open(animation_json_path, "r", encoding='utf-8-sig') as f:
            animation_json = json.load(f)
        
        names = self.extract_names(animation_json)
        self.get_names(names)

    def extract_names(self, animation_json):
        """Extract animation names from the animation JSON."""
        names = set()
        
        # Primary method: Look for animations (AN) which contain the actual timelines
        if "AN" in animation_json:
            animations = animation_json["AN"]
            
            # Check if this is a single animation or multiple animations
            if isinstance(animations, dict):
                # Single animation - check if it has a timeline
                if "TL" in animations and "L" in animations["TL"]:
                    timeline_data = animations["TL"]["L"]
                    if timeline_data:
                        # Check if timeline has content
                        has_content = False
                        for layer in timeline_data:
                            if "FR" in layer and layer["FR"]:
                                has_content = True
                                break
                        
                        if has_content:
                            # Use animation name if available, otherwise use default
                            anim_name = animations.get("name", "MainTimeline")
                            names.add(anim_name)
                            print(f"[SpritlemapParser] Found animation: {anim_name}")
            
            elif isinstance(animations, list):
                # Multiple animations
                for i, animation in enumerate(animations):
                    if "TL" in animation and "L" in animation["TL"]:
                        timeline_data = animation["TL"]["L"]
                        if timeline_data:
                            # Check if timeline has content
                            has_content = False
                            for layer in timeline_data:
                                if "FR" in layer and layer["FR"]:
                                    has_content = True
                                    break
                            
                            if has_content:
                                # Use animation name if available, otherwise use index
                                anim_name = animation.get("name", f"Animation_{i}")
                                names.add(anim_name)
                                print(f"[SpritlemapParser] Found animation: {anim_name}")
        
        # Fallback: If no animations found, check if there are symbols with meaningful timelines
        # (This handles cases where symbols themselves represent different animations)
        if not names and "SD" in animation_json and "S" in animation_json["SD"]:
            symbols = animation_json["SD"]["S"]
            for symbol in symbols:
                if "SN" in symbol and "TL" in symbol:
                    symbol_name = symbol["SN"]
                    timeline = symbol["TL"]
                    if "L" in timeline and timeline["L"]:
                        # Check if this symbol has a meaningful timeline (more than just a static pose)
                        total_frames = 0
                        for layer in timeline["L"]:
                            if "FR" in layer:
                                for frame in layer["FR"]:
                                    total_frames += frame.get("DU", 1)
                        
                        # Only consider it an animation if it has multiple frames or duration > 1
                        if total_frames > 1:
                            names.add(symbol_name)
                            print(f"[SpritlemapParser] Found symbol animation: {symbol_name}")
        
        # Final fallback: If still no names found, add a default main timeline
        if not names:
            names.add("MainTimeline")
            print("[SpritlemapParser] No specific animations found, using default MainTimeline")
        
        print(f"[SpritlemapParser] Total animations extracted: {len(names)}")
        return names

    def get_names(self, names):
        """Populate the listbox with the given names."""
        for name in sorted(names):
            self.listbox_data.insert(tk.END, name)

    @staticmethod
    def is_spritemap_directory(directory):
        """Check if a directory contains spritemap files."""
        animation_json = os.path.join(directory, "Animation.json")
        spritemap_json = os.path.join(directory, "spritemap1.json")
        spritemap_png = os.path.join(directory, "spritemap1.png")
        
        return (os.path.exists(animation_json) and 
                os.path.exists(spritemap_json) and 
                os.path.exists(spritemap_png))

    @staticmethod
    def parse_spritemap_data(directory, animation_name):
        """
        Parse spritemap data and return rendered frames for a specific animation.
        
        Args:
            directory (str): Path to the spritemap directory
            animation_name (str): Name of the animation/symbol to render
            
        Returns:
            list: List of sprite dictionaries compatible with TextureAtlas workflow
        """
        animation_json_path = os.path.join(directory, "Animation.json")
        spritemap_json_path = os.path.join(directory, "spritemap1.json")
        spritemap_png_path = os.path.join(directory, "spritemap1.png")
        
        # Load animation data
        with open(animation_json_path, "r", encoding='utf-8-sig') as f:
            animation_json = json.load(f)
        
        # Load spritemap data
        with open(spritemap_json_path, "rb") as f:
            spritemap_json = json.loads(f.read().decode("utf-8-sig"))
        
        # Load spritemap image
        spritemap_img = Image.open(spritemap_png_path)
        
        # Set up rendering components
        canvas_size = (1920, 1080)  # Default canvas size, can be made configurable
        sprite_atlas = SpritemapAtlas(spritemap_json, spritemap_img, canvas_size)
        symbols = SpritemapSymbols(animation_json, sprite_atlas, canvas_size)
        
        # Render all frames for the specified timeline/animation
        sprites = []
        timeline_length = symbols.length(animation_name)
        
        if timeline_length > 0:
            for frame_idx in range(timeline_length):
                frame = symbols.render_timeline(animation_name, frame_idx)
                
                if frame:
                    # Crop the frame to remove excess transparency
                    bbox = frame.getbbox()
                    if bbox:
                        cropped_frame = frame.crop(bbox)
                        
                        # Create sprite data compatible with the TextureAtlas workflow
                        sprite_data = {
                            "name": f"{animation_name}_{frame_idx:04d}",
                            "x": 0,  # Will be set when creating temporary atlas
                            "y": 0,  # Will be set when creating temporary atlas
                            "width": cropped_frame.width,
                            "height": cropped_frame.height,
                            "frameX": 0,
                            "frameY": 0,
                            "frameWidth": cropped_frame.width,
                            "frameHeight": cropped_frame.height,
                            "rotated": False,
                            "image": cropped_frame  # Store the actual image data
                        }
                        sprites.append(sprite_data)
        
        return sprites

    @staticmethod
    def create_temporary_atlas(sprites, output_dir):
        """
        Create a temporary atlas image and metadata from rendered spritemap frames.
        
        Args:
            sprites (list): List of sprite data with images
            output_dir (str): Directory to save the temporary atlas
            
        Returns:
            tuple: (atlas_path, metadata_path) paths to the created temporary files
        """
        if not sprites:
            return None, None
        
        # Calculate atlas dimensions (simple grid layout)
        sprites_per_row = int(len(sprites) ** 0.5) + 1
        max_width = max(sprite["width"] for sprite in sprites)
        max_height = max(sprite["height"] for sprite in sprites)
        
        atlas_width = sprites_per_row * max_width
        atlas_height = ((len(sprites) - 1) // sprites_per_row + 1) * max_height
        
        # Create atlas image
        atlas = Image.new("RGBA", (atlas_width, atlas_height), (0, 0, 0, 0))
        
        # Place sprites in atlas and update coordinates
        for i, sprite in enumerate(sprites):
            row = i // sprites_per_row
            col = i % sprites_per_row
            
            x = col * max_width
            y = row * max_height
            
            sprite["x"] = x
            sprite["y"] = y
            
            # Paste sprite image into atlas
            atlas.paste(sprite["image"], (x, y))
        
        # Save atlas image
        atlas_filename = "temp_spritemap_atlas.png"
        atlas_path = os.path.join(output_dir, atlas_filename)
        atlas.save(atlas_path)
        
        # Create metadata file (XML format for compatibility)
        metadata_filename = "temp_spritemap_atlas.xml"
        metadata_path = os.path.join(output_dir, metadata_filename)
        
        with open(metadata_path, 'w') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<TextureAtlas imagePath="temp_spritemap_atlas.png">\n')
            
            for sprite in sprites:
                f.write(f'    <SubTexture name="{sprite["name"]}" '
                       f'x="{sprite["x"]}" y="{sprite["y"]}" '
                       f'width="{sprite["width"]}" height="{sprite["height"]}" '
                       f'frameX="{sprite["frameX"]}" frameY="{sprite["frameY"]}" '
                       f'frameWidth="{sprite["frameWidth"]}" frameHeight="{sprite["frameHeight"]}" '
                       f'rotated="{str(sprite["rotated"]).lower()}"/>\n')
            
            f.write('</TextureAtlas>\n')
        
        return atlas_path, metadata_path
