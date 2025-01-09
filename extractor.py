import os
import sys
import concurrent.futures
import time
import tkinter as tk
import xml.etree.ElementTree as ET
from tkinter import messagebox

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
        spritesheet_settings (dict): A dictionary to store settings for each spritesheet.
        user_settings (dict): A dictionary to store user settings.
        use_all_threads (tk.BooleanVar): A boolean variable to determine if all CPU threads should be used.
    Methods:
        process_directory(input_dir, output_dir, progress_var, tk_root, create_gif, create_webp, set_framerate, set_loopdelay, set_minperiod, set_scale, set_threshold, keep_frames, crop_option, var_delay):
            Processes the given directory of spritesheets and metadata files, extracting sprites and generating animations.
        extract_sprites(atlas_path, metadata_path, output_dir, create_gif, create_webp, set_framerate, set_loopdelay, set_minperiod, set_scale, set_threshold, set_indices, keep_frames, crop_option, var_delay, user_settings, quant_frames, current_version):
            Extracts sprites from a given atlas and metadata file, and processes the animations.
    """

    def __init__(self, progress_bar, current_version, spritesheet_settings, user_settings):
        self.spritesheet_settings = spritesheet_settings
        self.user_settings = user_settings
        self.use_all_threads = tk.BooleanVar()
        self.progress_bar = progress_bar
        self.current_version = current_version

    def process_directory(self, input_dir, output_dir, progress_var, tk_root, create_gif, create_webp, set_framerate, set_loopdelay, set_minperiod, set_scale, set_threshold, keep_frames, crop_option, var_delay):
        total_frames_generated = 0
        total_anims_generated = 0
        total_sprites_failed = 0

        progress_var.set(0)
        total_files = Utilities.count_spritesheets(input_dir)
        self.progress_bar["maximum"] = total_files

        if self.use_all_threads.get():
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
                        settings = self.spritesheet_settings.get(filename, {})
                        print(filename)
                        print(self.spritesheet_settings)
                        print('test')
                        print(self.user_settings)
                        print(settings)
                        fps = settings.get('fps', set_framerate)
                        delay = settings.get('delay', set_loopdelay)
                        period = settings.get('period', set_minperiod)
                        frames = settings.get('frames', keep_frames)
                        threshold = settings.get('threshold', set_threshold)
                        scale = settings.get('scale', set_scale)
                        indices = settings.get('indices')
                        future = executor.submit(self.extract_sprites, os.path.join(input_dir, filename), xml_path if os.path.isfile(xml_path) else txt_path, sprite_output_dir, create_gif, create_webp, fps, delay, period, scale, threshold, indices, frames, crop_option, var_delay, self.user_settings, self.current_version)
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

    def extract_sprites(self, atlas_path, metadata_path, output_dir, create_gif, create_webp, set_framerate, set_loopdelay, set_minperiod, set_scale, set_threshold, set_indices, keep_frames, crop_option, var_delay, user_settings, current_version):
        frames_generated = 0
        anims_generated = 0
        sprites_failed = 0
        try:
            atlas_processor = AtlasProcessor(atlas_path, metadata_path)
            sprite_processor = SpriteProcessor(atlas_processor.atlas, atlas_processor.sprites)
            animations = sprite_processor.process_sprites()
            animation_processor = AnimationProcessor(animations, atlas_path, output_dir, create_gif, create_webp, set_framerate, set_loopdelay, set_minperiod, set_scale, set_threshold, set_indices, keep_frames, crop_option, var_delay, user_settings, current_version)
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