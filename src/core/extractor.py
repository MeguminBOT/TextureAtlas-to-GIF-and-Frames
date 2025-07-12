import os
import time
import gc
import xml.etree.ElementTree as ET
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
        progress_callback (callable): Callback function to update progress during processing.
        current_version (str): The current version of the extractor.
        settings_manager (SettingsManager): Manages global, animation-specific, and spritesheet-specific settings.
        app_config (AppConfig): Configuration for resource limits (CPU/memory).
        fnf_idle_loop (bool): A flag to determine if idle animations should have a loop delay of 0.

    Methods:
        process_directory(input_dir, output_dir, progress_callback, parent_window=None, spritesheet_list=None):
            Processes the given directory of spritesheets and metadata files, extracting sprites and generating animations.
            Returns early without processing if the user cancels background color detection dialogs.
        extract_sprites(atlas_path, metadata_path, output_dir, settings):
            Extracts sprites from a given atlas and metadata file, and processes the animations.
        generate_temp_animation_for_preview(atlas_path, metadata_path, settings, animation_name=None, temp_dir=None):
            Generates a temporary animated image file for preview purposes.
    """

    def __init__(self, progress_callback, current_version, settings_manager, app_config=None, statistics_callback=None):
        self.settings_manager = settings_manager
        self.progress_callback = progress_callback
        self.statistics_callback = statistics_callback
        self.current_version = current_version
        self.app_config = app_config
        self.fnf_idle_loop = False  # Changed from tk.BooleanVar to simple boolean

    def process_directory(self, input_dir, output_dir, progress_callback=None, parent_window=None, spritesheet_list=None):
        """
        Process a directory of spritesheets and metadata files.
        
        Args:
            input_dir: Input directory path
            output_dir: Output directory path 
            progress_callback: Callback function for progress updates (optional)
            parent_window: Parent window for dialogs (optional)
            spritesheet_list: List of specific files to process (optional)
        """
        total_frames_generated = 0
        total_anims_generated = 0
        total_sprites_failed = 0

        total_files = Utilities.count_spritesheets(spritesheet_list)
        
        # Use the instance progress callback, fallback to parameter if provided
        callback_to_use = self.progress_callback if self.progress_callback else progress_callback
        
        # Call progress callback if available
        if callback_to_use:
            callback_to_use(0, total_files, "Initializing...")

        cpu_threads = os.cpu_count() // 4
        if self.app_config:
            resource_limits = self.app_config.get("resource_limits", {})
            cpu_cores_val = resource_limits.get("cpu_cores", "auto")
            print(f"[Extractor] CPU cores setting from config: {cpu_cores_val}")
            try:
                if cpu_cores_val != "auto":
                    cpu_threads = max(1, min(int(cpu_cores_val), os.cpu_count()))
                    print(f"[Extractor] Using {cpu_threads} CPU threads (from config)")
                else:
                    print(f"[Extractor] Using {cpu_threads} CPU threads (auto: {os.cpu_count()} / 4)")
            except Exception:
                cpu_threads = os.cpu_count() // 4
                print(f"[Extractor] Error reading CPU config, defaulting to {cpu_threads} threads")
        else:
            print(f"[Extractor] No app config found, using default {cpu_threads} CPU threads")

        start_time = time.time()

        # Handle background color detection for unknown spritesheets before processing
        if self._handle_unknown_spritesheets_background_detection(input_dir, spritesheet_list, parent_window):
            print("[Extractor] Background detection was cancelled - stopping processing")
            return

        current_file = 0
        # Process files sequentially to avoid Qt threading issues
        filenames = spritesheet_list
        
        for filename in filenames:
            base_filename = filename.rsplit(".", 1)[0]
            xml_path = os.path.join(input_dir, base_filename + ".xml")
            txt_path = os.path.join(input_dir, base_filename + ".txt")
            image_path = os.path.join(input_dir, filename)

            sprite_output_dir = os.path.join(output_dir, base_filename)
            os.makedirs(sprite_output_dir, exist_ok=True)

            settings = self.settings_manager.get_settings(filename)

            try:
                if os.path.isfile(xml_path) or os.path.isfile(txt_path):
                    result = self.extract_sprites(
                        os.path.join(input_dir, filename),
                        xml_path if os.path.isfile(xml_path) else txt_path,
                        sprite_output_dir,
                        settings,
                        parent_window,
                    )
                    total_frames_generated += result["frames_generated"]
                    total_anims_generated += result["anims_generated"]
                    total_sprites_failed += result["sprites_failed"]

                # Fallback if no metadata file is found or if the spritesheet is not officially supported.
                elif (os.path.isfile(image_path) and filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp'))):
                    result = self.extract_sprites(
                        image_path,
                        None,
                        sprite_output_dir,
                        settings,
                        parent_window,
                    )
                    total_frames_generated += result["frames_generated"]
                    total_anims_generated += result["anims_generated"]
                    total_sprites_failed += result["sprites_failed"]

            except Exception as e:
                total_sprites_failed += 1
                print(f"Error processing {filename}: {str(e)}")
                
                # Update statistics even when there's an error
                if self.statistics_callback:
                    self.statistics_callback(total_frames_generated, total_anims_generated, total_sprites_failed)

            current_file += 1
            if callback_to_use:
                callback_to_use(current_file, total_files, filename)
            
            # Update statistics in real-time
            if self.statistics_callback:
                self.statistics_callback(total_frames_generated, total_anims_generated, total_sprites_failed)
                
            gc.collect()

        end_time = time.time()
        duration = end_time - start_time
        minutes, seconds = divmod(duration, 60)

        print("Finished processing all files.")
        print(f"Frames Generated: {total_frames_generated}")
        print(f"Animations Generated: {total_anims_generated}")
        print(f"Sprites Failed: {total_sprites_failed}")
        print(f"Processing Duration: {int(minutes)} minutes and {int(seconds)} seconds")
        
        # Final statistics update
        if self.statistics_callback:
            self.statistics_callback(total_frames_generated, total_anims_generated, total_sprites_failed)

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

            animation_exporter = AnimationExporter(
                temp_dir,
                self.current_version,
                lambda img, size: img.resize(
                    (round(img.width * abs(size)), round(img.height * abs(size))), Image.NEAREST
                ),
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

    def _handle_unknown_spritesheets_background_detection(self, input_dir, spritesheet_list, parent_window):
        """
        Handle background color detection for unknown spritesheets.

        Args:
            input_dir (str): The input directory containing spritesheets
            spritesheet_list (list): List of spritesheet filenames
            parent_window: The Qt parent window

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
                return False

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
                    parent_window, detection_results
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
