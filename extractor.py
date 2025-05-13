import os
import sys
import concurrent.futures
import time
import tkinter as tk
import xml.etree.ElementTree as ET
from tkinter import messagebox
import io
from PIL import Image
import tempfile

## Import our own modules
from atlas_processor import AtlasProcessor
from sprite_processor import SpriteProcessor
from animation_processor import AnimationProcessor
from exception_handler import ExceptionHandler
from utilities import Utilities

class Extractor:
    """
    A class to extract sprites from a directory of spritesheets and their corresponding metadata files.

    Attributes:
        progress_bar (tkinter.Progressbar): The progress bar to update during processing.
        current_version (str): The current version of the extractor.
        settings_manager (SettingsManager): Manages global, animation-specific, and spritesheet-specific settings.
        use_all_threads (tk.BooleanVar): A flag to determine if all CPU threads should be used.
        fnf_idle_loop (tk.BooleanVar): A flag to determine if idle animations should have a loop delay of 0.

    Methods:
        process_directory(input_dir, output_dir, progress_var, tk_root):
            Processes the given directory of spritesheets and metadata files, extracting sprites and generating animations.
        extract_sprites(atlas_path, metadata_path, output_dir, settings):
            Extracts sprites from a given atlas and metadata file, and processes the animations.
        extract_preview_gif_frames(atlas_path, metadata_path, settings, animation_name=None):
            Extracts frames for a single animation for preview purposes.
        generate_temp_gif_for_preview(atlas_path, metadata_path, settings, animation_name=None, temp_dir=None):
            Generates a temporary GIF file using the actual AnimationProcessor.save_gif logic.
    """

    def __init__(self, progress_bar, current_version, settings_manager):
        self.settings_manager = settings_manager
        self.use_all_threads = tk.BooleanVar()
        self.fnf_idle_loop = tk.BooleanVar()
        self.progress_bar = progress_bar
        self.current_version = current_version

    def process_directory(self, input_dir, output_dir, progress_var, tk_root):
        total_frames_generated = 0
        total_anims_generated = 0
        total_sprites_failed = 0

        progress_var.set(0)
        total_files = Utilities.count_spritesheets(input_dir)
        self.progress_bar["maximum"] = total_files

        cpu_threads = os.cpu_count() if self.use_all_threads.get() else os.cpu_count() // 2
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=cpu_threads) as executor:
            futures = []

            for filename in os.listdir(input_dir):
                if filename.endswith('.png'):
                    base_filename = filename.rsplit('.', 1)[0]
                    xml_path = os.path.join(input_dir, base_filename + '.xml')
                    txt_path = os.path.join(input_dir, base_filename + '.txt')

                    if os.path.isfile(xml_path) or os.path.isfile(txt_path):
                        sprite_output_dir = os.path.join(output_dir, base_filename)
                        os.makedirs(sprite_output_dir, exist_ok=True)

                        settings = self.settings_manager.get_settings(filename)

                        future = executor.submit(
                            self.extract_sprites,
                            os.path.join(input_dir, filename),
                            xml_path if os.path.isfile(xml_path) else txt_path,
                            sprite_output_dir,
                            settings,
                        )
                        futures.append(future)

            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    total_frames_generated += result['frames_generated']
                    total_anims_generated += result['anims_generated']
                    total_sprites_failed += result['sprites_failed']

                except Exception as e:
                    total_sprites_failed += 1
                    messagebox.showerror("Error", f"Something went wrong!!\n{str(e)}")
                    if not messagebox.askyesno("Continue?", "Do you want to try continue processing?"):
                        sys.exit()
                        
                tk_root.after(0, progress_var.set, progress_var.get() + 1)
                tk_root.after(0, tk_root.update_idletasks)

        end_time = time.time()
        duration = end_time - start_time
        minutes, seconds = divmod(duration, 60)

        tk_root.after(0, messagebox.showinfo,
            "Information",
            f"Finished processing all files.\n\n"
            f"Frames Generated: {total_frames_generated}\n"
            f"Animations Generated: {total_anims_generated}\n"
            f"Sprites Failed: {total_sprites_failed}\n\n"
            f"Processing Duration: {int(minutes)} minutes and {int(seconds)} seconds",
        )

    def extract_sprites(self, atlas_path, metadata_path, output_dir, settings):
        frames_generated = 0
        anims_generated = 0
        sprites_failed = 0

        try:
            atlas_processor = AtlasProcessor(atlas_path, metadata_path)
            sprite_processor = SpriteProcessor(atlas_processor.atlas, atlas_processor.sprites)
            animations = sprite_processor.process_sprites()
            animation_processor = AnimationProcessor(animations, atlas_path, output_dir, self.settings_manager, self.current_version)

            frames_generated, anims_generated = animation_processor.process_animations()
            return {
                'frames_generated': frames_generated,
                'anims_generated': anims_generated,
                'sprites_failed': sprites_failed
            }

        except ET.ParseError:
            sprites_failed += 1
            raise ET.ParseError(f"Badly formatted XML file:\n\n{metadata_path}")

        except Exception as e:
            ExceptionHandler.handle_exception(e, metadata_path, sprites_failed)

    def generate_temp_gif_for_preview(self, atlas_path, metadata_path, settings, animation_name=None, temp_dir=None):
        try:
            atlas_processor = AtlasProcessor(atlas_path, metadata_path)
            sprite_processor = SpriteProcessor(atlas_processor.atlas, atlas_processor.sprites)
            animations = sprite_processor.process_sprites()
            if animation_name:
                animations = {animation_name: animations.get(animation_name, [])}
            else:
                if animations:
                    first_anim = next(iter(animations))
                    animations = {first_anim: animations[first_anim]}
                else:
                    return None

            if temp_dir is None:
                temp_dir = tempfile.mkdtemp()

            animation_processor = AnimationProcessor(
                animations, atlas_path, temp_dir, self.settings_manager, self.current_version
            )
            for anim_name, image_tuples in animations.items():
                images = [img_tuple[1] for img_tuple in image_tuples]
                if images:
                    sizes = [frame.size for frame in images]
                    max_size = tuple(map(max, zip(*sizes)))
                else:
                    max_size = (1, 1)
                animation_processor.save_gif(
                    images,
                    os.path.basename(atlas_path),
                    anim_name,
                    settings.get('fps', 24),
                    settings.get('delay', 250),
                    settings.get('period', 0),
                    settings.get('scale', 1),
                    settings.get('threshold', 0.5),
                    max_size,  # Pass the computed max_size
                    image_tuples,
                    settings
                )
    
                for file in os.listdir(temp_dir):
                    if file.endswith('.gif'):
                        return os.path.join(temp_dir, file)
            return None
        except Exception as e:
            print(f"Preview GIF generation error: {e}")
            return None