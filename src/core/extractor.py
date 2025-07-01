import os
import sys
import concurrent.futures
import time
import gc
import tkinter as tk
import xml.etree.ElementTree as ET
from tkinter import messagebox
from PIL import Image
import tempfile

# Import our own modules
from core.atlas_processor import AtlasProcessor
from core.sprite_processor import SpriteProcessor
from core.frame_selector import FrameSelector
from core.animation_processor import AnimationProcessor
from core.animation_exporter import AnimationExporter
from core.exception_handler import ExceptionHandler
from utils.utilities import Utilities


class Extractor:
    """
    A class to extract sprites from a directory of spritesheets and their corresponding metadata files.

    Attributes:
        progress_bar (tkinter.Progressbar): The progress bar to update during processing.
        current_version (str): The current version of the extractor.
        settings_manager (SettingsManager): Manages global, animation-specific, and spritesheet-specific settings.
        app_config (AppConfig): Configuration for resource limits (CPU/memory).
        fnf_idle_loop (tk.BooleanVar): A flag to determine if idle animations should have a loop delay of 0.

    Methods:
        process_directory(input_dir, output_dir, progress_var, tk_root, spritesheet_list=None):
            Processes the given directory of spritesheets and metadata files, extracting sprites and generating animations.
            Returns early without processing if the user cancels background color detection dialogs.
        extract_sprites(atlas_path, metadata_path, output_dir, settings):
            Extracts sprites from a given atlas and metadata file, and processes the animations.
        generate_temp_animation_for_preview(atlas_path, metadata_path, settings, animation_name=None, temp_dir=None):
            Generates a temporary animated image file for preview purposes.
    """

    def __init__(self, progress_bar, current_version, settings_manager, app_config=None):
        self.settings_manager = settings_manager
        self.progress_bar = progress_bar
        self.current_version = current_version
        self.app_config = app_config
        self.fnf_idle_loop = tk.BooleanVar()

    def process_directory(self, input_dir, output_dir, progress_var, tk_root, spritesheet_list=None):
        total_frames_generated = 0
        total_anims_generated = 0
        total_sprites_failed = 0

        progress_var.set(0)
        total_files = Utilities.count_spritesheets(spritesheet_list)
        self.progress_bar["maximum"] = total_files

        cpu_count = os.cpu_count()
        if cpu_count is None:
            cpu_count = 1
        cpu_threads = cpu_count // 4 if cpu_count > 1 else 1
        if self.app_config:
            resource_limits = self.app_config.get("resource_limits", {})
            cpu_cores_val = resource_limits.get("cpu_cores", "auto")
            print(f"[Extractor] CPU cores setting from config: {cpu_cores_val}")
            try:
                if cpu_cores_val != "auto":
                    cpu_threads = max(1, min(int(cpu_cores_val), cpu_count))
                    print(f"[Extractor] Using {cpu_threads} CPU threads (from config)")
                else:
                    print(f"[Extractor] Using {cpu_threads} CPU threads (auto: {cpu_count} / 4)")
            except Exception:
                cpu_threads = cpu_count // 4 if cpu_count > 1 else 1
                print(f"[Extractor] Error reading CPU config, defaulting to {cpu_threads} threads")
        else:
            print(f"[Extractor] No app config found, using default {cpu_threads} CPU threads")

        start_time = time.time()

        # Handle background color detection for unknown spritesheets before processing
        if self._handle_unknown_spritesheets_background_detection(input_dir, spritesheet_list, tk_root):
            print("[Extractor] Background detection was cancelled - stopping processing")
            return

        with concurrent.futures.ThreadPoolExecutor(max_workers=cpu_threads) as executor:
            futures = []

            filenames = spritesheet_list if spritesheet_list is not None else []
            for filename in filenames:
                base_filename = filename.rsplit(".", 1)[0]
                xml_path = os.path.join(input_dir, base_filename + ".xml")
                txt_path = os.path.join(input_dir, base_filename + ".txt")
                image_path = os.path.join(input_dir, filename)

                sprite_output_dir = os.path.join(output_dir, base_filename)
                os.makedirs(sprite_output_dir, exist_ok=True)

                settings = self.settings_manager.get_settings(filename)

                if os.path.isfile(xml_path) or os.path.isfile(txt_path):
                    future = executor.submit(
                        self.extract_sprites,
                        os.path.join(input_dir, filename),
                        xml_path if os.path.isfile(xml_path) else txt_path,
                        sprite_output_dir,
                        settings,
                        tk_root,
                    )
                    futures.append(future)

                # Fallback if no metadata file is found or if the spritesheet is not officially supported.
                elif (os.path.isfile(image_path) and filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp'))):
                    future = executor.submit(
                        self.extract_sprites,
                        image_path,
                        None,
                        sprite_output_dir,
                        settings,
                        tk_root,
                    )
                    futures.append(future)

            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    total_frames_generated += result["frames_generated"]
                    total_anims_generated += result["anims_generated"]
                    total_sprites_failed += result["sprites_failed"]

                except Exception as e:
                    total_sprites_failed += 1
                    messagebox.showerror("Error", f"Something went wrong!!\n{str(e)}")
                    if not messagebox.askyesno("Continue?", "Do you want to try continue processing?"):
                        sys.exit()

                tk_root.after(0, progress_var.set, progress_var.get() + 1)
                tk_root.after(0, tk_root.update_idletasks)
                gc.collect()

        end_time = time.time()
        duration = end_time - start_time
        minutes, seconds = divmod(duration, 60)

        tk_root.after(
            0,
            messagebox.showinfo,
            "Information",
            f"Finished processing all files.\n\n"
            f"Frames Generated: {total_frames_generated}\n"
            f"Animations Generated: {total_anims_generated}\n"
            f"Sprites Failed: {total_sprites_failed}\n\n"
            f"Processing Duration: {int(minutes)} minutes and {int(seconds)} seconds",
        )

    def extract_sprites(self, atlas_path, metadata_path, output_dir, settings, parent_window=None):
        frames_generated = 0
        anims_generated = 0
        sprites_failed = 0

        try:
            is_unknown_spritesheet = metadata_path is None
            
            atlas_processor = AtlasProcessor(atlas_path, metadata_path, parent_window)
            sprite_processor = SpriteProcessor(atlas_processor.atlas, atlas_processor.sprites)
            animations = sprite_processor.process_sprites()
            animation_processor = AnimationProcessor(
                animations, atlas_path, output_dir, self.settings_manager, self.current_version
            )

            frames_generated, anims_generated = animation_processor.process_animations(is_unknown_spritesheet)
            return {
                "frames_generated": frames_generated,
                "anims_generated": anims_generated,
                "sprites_failed": sprites_failed,
            }

        except ET.ParseError:
            sprites_failed += 1
            raise ET.ParseError(f"Badly formatted XML file:\n\n{metadata_path}")

        except Exception as e:
            ExceptionHandler.handle_exception(e, metadata_path if metadata_path else atlas_path, sprites_failed)

    def generate_temp_animation_for_preview(self, atlas_path, metadata_path, settings, animation_name=None, temp_dir=None):
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

            quant_frames = {}
            animation_exporter = AnimationExporter(
                temp_dir,
                self.current_version,
                lambda img, size: img.resize(
                    (round(img.width * abs(size)), round(img.height * abs(size))), Image.Resampling.NEAREST
                ),
                quant_frames,
            )

            for anim_name, image_tuples in animations.items():
                spritesheet_name = os.path.basename(atlas_path)
                preview_settings = self.settings_manager.get_settings(
                    spritesheet_name, f"{spritesheet_name}/{anim_name}"
                )
                merged_settings = {**preview_settings, **settings}

                animation_format = merged_settings.get("animation_format", "GIF")
                if animation_format == "None":
                    animation_format = "GIF"
                merged_settings["animation_format"] = animation_format

                indices = merged_settings.get("indices")
                if indices:
                    indices = list(filter(lambda i: ((i < len(image_tuples)) & (i >= 0)), indices))
                    image_tuples = [image_tuples[i] for i in indices]

                single_frame = FrameSelector.is_single_frame(image_tuples)
                kept_frames = FrameSelector.get_kept_frames(
                    merged_settings, single_frame, image_tuples
                )

                kept_frame_indices = FrameSelector.get_kept_frame_indices(kept_frames, image_tuples)
                image_tuples = [
                    img for idx, img in enumerate(image_tuples) if idx in kept_frame_indices
                ]

                animation_exporter.save_animations(
                    image_tuples, spritesheet_name, anim_name, merged_settings
                )

                file_extensions = {
                    "GIF": ".gif",
                    "WebP": ".webp", 
                    "APNG": ".png"
                }
                target_extension = file_extensions.get(animation_format, ".gif")

                for file in os.listdir(temp_dir):
                    if file.endswith(target_extension):
                        return os.path.join(temp_dir, file)
            return None

        except Exception as e:
            print(f"Preview animation generation error: {e}")
            return None

    def _handle_unknown_spritesheets_background_detection(self, input_dir, spritesheet_list, tk_root):
        """
        Handle background color detection for unknown spritesheets.

        Args:
            input_dir (str): The input directory containing spritesheets
            spritesheet_list (list): List of spritesheet filenames
            tk_root: The tkinter root window

        Returns:
            bool: True if the user cancelled the dialog, False otherwise
        """
        try:
            unknown_spritesheets = []
            print(
                f"[Extractor] Checking {len(spritesheet_list)} spritesheets for unknown files..."
            )

            for filename in spritesheet_list:
                base_filename = filename.rsplit(".", 1)[0]
                xml_path = os.path.join(input_dir, base_filename + ".xml")
                txt_path = os.path.join(input_dir, base_filename + ".txt")
                image_path = os.path.join(input_dir, filename)

                if (
                    not os.path.isfile(xml_path)
                    and not os.path.isfile(txt_path)
                    and os.path.isfile(image_path)
                    and filename.lower().endswith(
                        (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp")
                    )
                ):
                    unknown_spritesheets.append(filename)
                    print(f"[Extractor] Found unknown spritesheet: {filename}")

            if not unknown_spritesheets:
                print("[Extractor] No unknown spritesheets found")
                return

            print(
                f"[Extractor] Found {len(unknown_spritesheets)} unknown spritesheet(s), checking for background colors..."
            )

            from parsers.unknown_parser import UnknownParser
            from gui.background_handler_window import BackgroundHandlerWindow
            from PIL import Image

            BackgroundHandlerWindow.reset_batch_state()

            detection_results = []

            for filename in unknown_spritesheets:
                image_path = os.path.join(input_dir, filename)
                try:
                    image = Image.open(image_path)
                    if image.mode != "RGBA":
                        image = image.convert("RGBA")

                    has_transparency = UnknownParser._has_transparency(image)
                    detected_colors = []

                    if not has_transparency:
                        detected_colors = UnknownParser._detect_background_colors(
                            image, max_colors=3
                        )

                    # Always add unknown spritesheets to detection results
                    detection_results.append(
                        {
                            "filename": filename,
                            "colors": detected_colors,
                            "has_transparency": has_transparency,
                        }
                    )

                except Exception as e:
                    print(f"Error detecting background colors for {filename}: {e}")
                    detection_results.append(
                        {"filename": filename, "colors": [], "has_transparency": False}
                    )

            print(f"[Extractor] Detection results: {len(detection_results)} entries")
            for result in detection_results:
                print(
                    f"  - {result['filename']}: {len(result['colors'])} colors, transparency: {result['has_transparency']}"
                )

            if detection_results:
                print("[Extractor] Showing background handler window...")
                background_choices = BackgroundHandlerWindow.show_background_options(
                    tk_root, detection_results
                )
                print(f"[Extractor] User choices: {background_choices}")

                # Check if user cancelled the background handler dialog
                if background_choices.get("_cancelled", False):
                    print(
                        "[Extractor] Background handler was cancelled by user - stopping extraction"
                    )
                    return True

                if background_choices:
                    # Store the individual choices for each file
                    if not hasattr(BackgroundHandlerWindow, "_file_choices"):
                        BackgroundHandlerWindow._file_choices = {}
                    BackgroundHandlerWindow._file_choices.update(background_choices)
                    print(
                        f"Background handling preferences set for {len(background_choices)} files"
                    )
            else:
                print("[Extractor] No detection results to show")

        except Exception as e:
            print(f"Error in background color detection: {e}")

        return False
