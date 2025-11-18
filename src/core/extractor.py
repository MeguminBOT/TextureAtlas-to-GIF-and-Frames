import os
import time
import xml.etree.ElementTree as ET
from PIL import Image
import tempfile
from threading import Lock
from pathlib import Path

from PySide6.QtCore import QThread, Signal, QCoreApplication

# Import our own modules
from core.atlas_processor import AtlasProcessor
from core.sprite_processor import SpriteProcessor
from core.frame_selector import FrameSelector
from core.animation_processor import AnimationProcessor
from core.animation_exporter import AnimationExporter
from core.spritemap import AdobeSpritemapRenderer
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
        generate_temp_animation_for_preview(atlas_path, metadata_path, settings, animation_name, temp_dir=None):
            Generates a temporary animated image file for preview purposes using optimized processing 
            that only loads sprites belonging to the specific animation.
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
        Process a directory of spritesheets and metadata files using multiple threads.
        
        Args:
            input_dir: Input directory path
            output_dir: Output directory path 
            progress_callback: Callback function for progress updates (optional)
            parent_window: Parent window for dialogs (optional)
            spritesheet_list: List of specific files to process (optional)
        """
        
        # Initialize threading attributes
        self.stats_lock = Lock()
        self.total_frames_generated = 0
        self.total_anims_generated = 0
        self.total_sprites_failed = 0
        self.processed_count = 0
        self.active_workers = []
        self.completed_files = []

        total_files = Utilities.count_spritesheets(spritesheet_list)
        
        # Use the instance progress callback, fallback to parameter if provided
        callback_to_use = self.progress_callback if self.progress_callback else progress_callback
        
        # Call progress callback if available
        if callback_to_use:
            callback_to_use(0, total_files, "Initializing...")

        # Get CPU thread setting from app config
        cpu_threads = max(1, os.cpu_count() // 2)  # Default fallback, minimum 1 thread
        
        if self.app_config:
            try:
                # Access the settings properly
                resource_limits = self.app_config.settings.get("resource_limits", {})
                cpu_cores_val = resource_limits.get("cpu_cores", "auto")
                print(f"[Extractor] CPU cores setting from config: {cpu_cores_val}")
                
                if cpu_cores_val != "auto":
                    # Use the configured value, but ensure it's within reasonable bounds
                    configured_threads = int(cpu_cores_val)
                    cpu_threads = max(1, min(configured_threads, os.cpu_count()))
                    print(f"[Extractor] Using {cpu_threads} CPU threads (from config: {cpu_cores_val})")
                else:
                    # Auto mode: use half of available cores, minimum 1
                    cpu_threads = max(1, os.cpu_count() // 2)
                    print(f"[Extractor] Using {cpu_threads} CPU threads (auto mode: {os.cpu_count()} cores / 2)")
                    
            except (ValueError, TypeError, KeyError) as e:
                # Fallback if config is invalid
                cpu_threads = max(1, os.cpu_count() // 2)
                print(f"[Extractor] Error reading CPU config ({e}), using fallback: {cpu_threads} threads")
        else:
            print(f"[Extractor] No app config available, using default {cpu_threads} CPU threads")

        start_time = time.time()

        # Use multi-threading with QThread
        filenames = spritesheet_list
        self.remaining_files = filenames.copy()
        
        # Determine optimal number of threads (limited by config and available files)
        max_threads = min(cpu_threads, len(filenames))
        
        print("[Extractor] Processing configuration:")
        print(f"  - CPU threads configured: {cpu_threads}")
        print(f"  - Files to process: {len(filenames)}")
        print(f"  - Workers to start: {max_threads}")
        
        # Store start time for duration calculation
        self.start_time = start_time
        
        # Start initial batch of workers
        for i in range(min(max_threads, len(filenames))):
            print(f"[process_directory] Starting initial worker {i+1}/{max_threads}")
            self._start_next_worker(input_dir, output_dir, parent_window, callback_to_use, total_files)
            
        print(f"[process_directory] Started {len(self.active_workers)} initial workers")
        print(f"[process_directory] Remaining files after initial start: {len(self.remaining_files)}")
        
        # Wait for all workers to complete using Qt's event system
        while self.active_workers or self.remaining_files:
            QCoreApplication.processEvents()
            time.sleep(0.01)  # Small delay to prevent busy waiting
            
            # Clean up finished workers
            for worker in self.active_workers[:]:  # Copy list to avoid modification during iteration
                if worker.isFinished():
                    worker.wait()
                    worker.deleteLater()
                    self.active_workers.remove(worker)
            time.sleep(0.01)
            
        # Process any remaining Qt events after all workers finish
        QCoreApplication.processEvents()
        
        # Give a small additional delay to ensure all signals are processed
        time.sleep(0.1)
        QCoreApplication.processEvents()
        
        print(f"[process_directory] All workers finished. Final totals before completion: F:{self.total_frames_generated}, A:{self.total_anims_generated}, S:{self.total_sprites_failed}")

        end_time = time.time()
        duration = end_time - self.start_time
        minutes, seconds = divmod(duration, 60)

        print("Finished processing all files.")
        print(f"Frames Generated: {self.total_frames_generated}")
        print(f"Animations Generated: {self.total_anims_generated}")
        print(f"Sprites Failed: {self.total_sprites_failed}")
        print(f"Processing Duration: {int(minutes)} minutes and {int(seconds)} seconds")
        
        # Final statistics update
        if self.statistics_callback:
            print(f"[process_directory] Final statistics callback: F:{self.total_frames_generated}, A:{self.total_anims_generated}, S:{self.total_sprites_failed}")
            self.statistics_callback(self.total_frames_generated, self.total_anims_generated, self.total_sprites_failed)
    
    def _start_next_worker(self, input_dir, output_dir, parent_window, callback_to_use, total_files):
        """Start the next worker thread if files remain."""
        if not self.remaining_files:
            print("[_start_next_worker] No remaining files")
            return
            
        filename = self.remaining_files.pop(0)
        print(f"[_start_next_worker] Starting worker for {filename}, {len(self.remaining_files)} files left")
        worker = FileProcessorWorker(filename, input_dir, output_dir, parent_window, self)
        
        # Connect signals
        worker.file_completed.connect(self._on_file_completed)
        worker.file_failed.connect(self._on_file_failed)
        worker.finished.connect(lambda: self._worker_finished(worker, input_dir, output_dir, parent_window, callback_to_use, total_files))
        
        print(f"[_start_next_worker] Started worker for {filename}, connected signals, {len(self.active_workers)} workers active before adding")
        
        self.active_workers.append(worker)
        worker.start()
        
        print(f"[_start_next_worker] Now have {len(self.active_workers)} active workers")
        
        # Update progress with list of currently processing files
        if callback_to_use:
            processing_files = [w.filename for w in self.active_workers if hasattr(w, 'filename')]
            current_files_text = ", ".join(processing_files) if processing_files else "Starting..."
            callback_to_use(len(self.completed_files), total_files, current_files_text)
    
    def _on_file_completed(self, filename, result):
        """Handle successful file completion."""
        print(f"[_on_file_completed] {filename} completed with result: {result}")
        with self.stats_lock:
            if result:
                frames_added = result.get('frames_generated', 0)
                anims_added = result.get('anims_generated', 0)
                failed_added = result.get('sprites_failed', 0)
                
                print(f"[_on_file_completed] Adding to totals: {frames_added} frames, {anims_added} anims, {failed_added} failed")
                
                self.total_frames_generated += frames_added
                self.total_anims_generated += anims_added
                self.total_sprites_failed += failed_added
                
                print(f"[_on_file_completed] New totals: {self.total_frames_generated} frames, {self.total_anims_generated} anims, {self.total_sprites_failed} failed")
                
                # Emit debug info to processing log if callback supports it
                if hasattr(self, 'debug_callback') and self.debug_callback:
                    self.debug_callback(f"✓ {filename}: {frames_added} frames, {anims_added} animations generated")
            else:
                self.total_sprites_failed += 1
                print(f"[_on_file_completed] {filename} failed - no result returned")
                
                if hasattr(self, 'debug_callback') and self.debug_callback:
                    self.debug_callback(f"✗ {filename}: Processing failed - no result returned")
            
            self.processed_count += 1
            self.completed_files.append(filename)
            
            print(f"[_on_file_completed] Calling statistics_callback with: {self.total_frames_generated}, {self.total_anims_generated}, {self.total_sprites_failed}")
            
            # Update statistics in real-time
            if self.statistics_callback:
                self.statistics_callback(self.total_frames_generated, self.total_anims_generated, self.total_sprites_failed)
            else:
                print("[_on_file_completed] No statistics_callback available")
    
    def _on_file_failed(self, filename, error):
        """Handle file processing failure."""
        with self.stats_lock:
            self.total_sprites_failed += 1
            self.processed_count += 1
            self.completed_files.append(filename)
            print(f"Error processing {filename}: {error}")
            
            # Emit debug info to processing log
            if hasattr(self, 'debug_callback') and self.debug_callback:
                self.debug_callback(f"✗ {filename}: Error - {error}")
            
            # Update statistics even when there's an error
            if self.statistics_callback:
                self.statistics_callback(self.total_frames_generated, self.total_anims_generated, self.total_sprites_failed)
    
    def _worker_finished(self, worker, input_dir, output_dir, parent_window, callback_to_use, total_files):
        """Handle worker thread completion and start next worker if needed."""
        print(f"[_worker_finished] Worker for {getattr(worker, 'filename', 'unknown')} finished")
        
        # Start next worker if files remain and we're not at max capacity
        if self.remaining_files:
            print(f"[_worker_finished] Starting next worker, {len(self.remaining_files)} files remaining")
            self._start_next_worker(input_dir, output_dir, parent_window, callback_to_use, total_files)
        else:
            print("[_worker_finished] No more files to process")
        
        # Update progress with current processing files
        if callback_to_use:
            processing_files = [w.filename for w in self.active_workers if hasattr(w, 'filename')]
            if processing_files:
                current_files_text = ", ".join(processing_files)
                callback_to_use(len(self.completed_files), total_files, current_files_text)
            else:
                # No more workers active
                callback_to_use(len(self.completed_files), total_files, "Completing...")

    def extract_sprites(self, atlas_path, metadata_path, output_dir, settings, parent_window=None, spritesheet_label=None):
        frames_generated = 0
        anims_generated = 0
        sprites_failed = 0

        try:
            is_unknown_spritesheet = metadata_path is None
            
            atlas_processor = AtlasProcessor(atlas_path, metadata_path, parent_window)
            sprite_processor = SpriteProcessor(atlas_processor.atlas, atlas_processor.sprites)
            animations = sprite_processor.process_sprites()
            animation_processor = AnimationProcessor(
                animations,
                atlas_path,
                output_dir,
                self.settings_manager,
                self.current_version,
                spritesheet_label=spritesheet_label,
            )

            frames_generated, anims_generated = animation_processor.process_animations(is_unknown_spritesheet)
            result = {
                "frames_generated": frames_generated,
                "anims_generated": anims_generated,
                "sprites_failed": sprites_failed,
            }
            print(f"[extract_sprites] Returning result for {atlas_path}: {result}")
            return result

        except ET.ParseError:
            sprites_failed += 1
            print(f"[extract_sprites] ParseError for {atlas_path}: sprites_failed = {sprites_failed}")
            raise ET.ParseError(f"Badly formatted XML file:\n\n{metadata_path}")

        except Exception as e:
            sprites_failed += 1
            print(f"[extract_sprites] Exception for {atlas_path}: {str(e)}, sprites_failed = {sprites_failed}")
            print(f"[extract_sprites] Returning error result: frames_generated=0, anims_generated=0, sprites_failed={sprites_failed}")
            # Return a result even on failure so statistics can be updated
            return {
                "frames_generated": 0,
                "anims_generated": 0,
                "sprites_failed": sprites_failed,
            }

    def extract_spritemap_project(
        self,
        atlas_path,
        animation_json_path,
        spritemap_json_path,
        output_dir,
        settings,
        spritesheet_label=None,
    ):
        frames_generated = 0
        anims_generated = 0
        sprites_failed = 0

        try:
            spritesheet_name = spritesheet_label or os.path.basename(atlas_path)
            renderer = AdobeSpritemapRenderer(
                animation_json_path,
                spritemap_json_path,
                atlas_path,
                filter_single_frame=settings.get("filter_single_frame_spritemaps", True),
            )
            renderer.ensure_animation_defaults(self.settings_manager, spritesheet_name)
            animations = renderer.build_animation_frames()

            if not animations:
                return {
                    "frames_generated": 0,
                    "anims_generated": 0,
                    "sprites_failed": 0,
                }

            animation_processor = AnimationProcessor(
                animations,
                atlas_path,
                output_dir,
                self.settings_manager,
                self.current_version,
                spritesheet_label=spritesheet_name,
            )
            frames_generated, anims_generated = animation_processor.process_animations()
            return {
                "frames_generated": frames_generated,
                "anims_generated": anims_generated,
                "sprites_failed": 0,
            }
        except Exception as exc:
            sprites_failed += 1
            print(f"[extract_spritemap_project] Error processing {atlas_path}: {exc}")
            return {
                "frames_generated": 0,
                "anims_generated": 0,
                "sprites_failed": sprites_failed,
            }

    def generate_temp_animation_for_preview(
        self,
        atlas_path,
        metadata_path,
        settings,
        animation_name,
        temp_dir=None,
        spritemap_info=None,
        spritesheet_label=None,
    ):
        """
        Optimized version that only processes the specific animation frames for regeneration.
        This reduces performance overhead by not processing the entire atlas.
        """
        try:
            import tempfile

            animations = {}

            label = spritesheet_label or os.path.basename(atlas_path)

            if spritemap_info:
                animation_json_path = spritemap_info.get("animation_json")
                spritemap_json_path = spritemap_info.get("spritemap_json")
                if not animation_json_path or not spritemap_json_path:
                    return None

                renderer = AdobeSpritemapRenderer(
                    animation_json_path,
                    spritemap_json_path,
                    atlas_path,
                    filter_single_frame=settings.get("filter_single_frame_spritemaps", True),
                )
                renderer.ensure_animation_defaults(self.settings_manager, label)
                symbol_entry = spritemap_info.get("symbol_map", {}).get(animation_name, animation_name)
                frames = renderer.render_animation(symbol_entry)
                if not frames:
                    print(f"No frames rendered for spritemap animation: {animation_name}")
                    return None
                animations[animation_name] = frames
            else:
                atlas_processor = AtlasProcessor(atlas_path, metadata_path)

                if metadata_path and metadata_path.endswith(".xml"):
                    animation_sprites = atlas_processor.parse_xml_for_preview(animation_name)
                elif metadata_path and metadata_path.endswith(".txt"):
                    animation_sprites = atlas_processor.parse_txt_for_preview(animation_name)
                else:
                    return self.generate_temp_animation_for_preview(
                        atlas_path,
                        metadata_path,
                        settings,
                        animation_name,
                        temp_dir,
                        spritemap_info,
                        spritesheet_label=label,
                    )

                if not animation_sprites:
                    print(f"No sprites found for animation: {animation_name}")
                    return None

                sprite_processor = SpriteProcessor(atlas_processor.atlas, animation_sprites)
                processed = sprite_processor.process_specific_animation(animation_name)

                if animation_name not in processed:
                    print(f"Animation {animation_name} not found in processed sprites")
                    return None

                animations = {animation_name: processed[animation_name]}

            if temp_dir is None:
                temp_dir = tempfile.mkdtemp()

            from core.animation_exporter import AnimationExporter

            animation_exporter = AnimationExporter(
                temp_dir,
                self.current_version,
                lambda img, size: img.resize(
                    (round(img.width * abs(size)), round(img.height * abs(size))), Image.NEAREST
                ),
            )

            for anim_name, image_tuples in animations.items():
                spritesheet_name = label
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

                from core.frame_selector import FrameSelector

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

                file_extensions = {"GIF": ".gif", "WebP": ".webp", "APNG": ".png"}
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

            base_directory = Path(input_dir)

            for filename in spritesheet_list:
                relative_path = Path(filename)
                atlas_path = base_directory / relative_path
                base_filename = relative_path.stem
                atlas_dir = atlas_path.parent

                xml_path = atlas_dir / f"{base_filename}.xml"
                txt_path = atlas_dir / f"{base_filename}.txt"

                spritemap_json_path = atlas_dir / f"{base_filename}.json"
                animation_json_path = atlas_dir / "Animation.json"
                has_spritemap_metadata = animation_json_path.is_file() and spritemap_json_path.is_file()

                if (
                    not xml_path.is_file()
                    and not txt_path.is_file()
                    and not has_spritemap_metadata
                    and atlas_path.is_file()
                    and atlas_path.suffix.lower()
                    in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp")
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
                image_path = str(base_directory / Path(filename))
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

            # Check if any images actually need background handling
            needs_background_handling = False
            for result in detection_results:
                # An image needs background handling if it has no transparency AND has detected background colors
                if not result['has_transparency'] and len(result['colors']) > 0:
                    needs_background_handling = True
                    break
            
            if detection_results and needs_background_handling:
                print("[Extractor] Some images have backgrounds that need handling - showing background handler window...")
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
            elif detection_results:
                print("[Extractor] All images either have transparency or no detectable backgrounds - skipping background handler window")
            else:
                print("[Extractor] No detection results to show")

        except Exception as e:
            print(f"Error in background color detection: {e}")

        return False


class FileProcessorWorker(QThread):
    """Worker thread for processing individual files."""
    
    file_completed = Signal(str, dict)  # filename, result
    file_failed = Signal(str, str)      # filename, error
    
    def __init__(self, filename, input_dir, output_dir, parent_window, extractor_instance):
        super().__init__()
        self.filename = filename
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.parent_window = parent_window
        self.extractor = extractor_instance

    def tr(self, text):
        """Translation helper method."""
        from PySide6.QtCore import QCoreApplication
        return QCoreApplication.translate(self.__class__.__name__, text)

        
    def run(self):
        """Process a single file in this thread."""
        try:
            import threading
            thread_id = threading.get_ident()
            print(f"[FileProcessorWorker] Starting processing of {self.filename} on thread {thread_id} at {time.time():.3f}")
            
            relative_path = Path(self.filename)
            atlas_path = Path(self.input_dir) / relative_path
            atlas_dir = atlas_path.parent
            base_filename = relative_path.stem
            xml_path = atlas_dir / f"{base_filename}.xml"
            txt_path = atlas_dir / f"{base_filename}.txt"
            image_path = str(atlas_path)
            sprite_output_dir = Path(self.output_dir) / relative_path.with_suffix("")
            animation_json_path = atlas_dir / "Animation.json"
            spritemap_json_path = atlas_dir / f"{base_filename}.json"
            
            os.makedirs(sprite_output_dir, exist_ok=True)
            sprite_output_dir = str(sprite_output_dir)
            
            # Get settings for this file
            settings = self.extractor.settings_manager.get_settings(self.filename)
            
            print(f"[FileProcessorWorker] {self.filename} about to start extract_sprites on thread {thread_id}")

            # Process Adobe spritemap exports first
            if animation_json_path.is_file() and spritemap_json_path.is_file():
                print(f"[FileProcessorWorker] Processing {self.filename} as Adobe spritemap")
                result = self.extractor.extract_spritemap_project(
                    image_path,
                    str(animation_json_path),
                    str(spritemap_json_path),
                    sprite_output_dir,
                    settings,
                    spritesheet_label=self.filename,
                )
                print(f"[FileProcessorWorker] {self.filename} completed with result: {result} on thread {thread_id} at {time.time():.3f}")
                self.file_completed.emit(self.filename, result)

            # Process the file with XML/TXT metadata
            elif xml_path.is_file() or txt_path.is_file():
                print(f"[FileProcessorWorker] Processing {self.filename} with metadata")
                result = self.extractor.extract_sprites(
                    image_path,
                    str(xml_path) if xml_path.is_file() else str(txt_path),
                    sprite_output_dir,
                    settings,
                    None,  # No parent window for worker threads to avoid Qt threading issues
                    spritesheet_label=self.filename,
                )
                print(f"[FileProcessorWorker] {self.filename} completed with result: {result} on thread {thread_id} at {time.time():.3f}")
                self.file_completed.emit(self.filename, result)
                
            elif (os.path.isfile(image_path) and 
                self.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp'))):
                print(f"[FileProcessorWorker] Processing {self.filename} as unknown spritesheet")
                result = self.extractor.extract_sprites(
                    image_path,
                    None,
                    sprite_output_dir,
                    settings,
                    None,  # No parent window for worker threads to avoid Qt threading issues
                    spritesheet_label=self.filename,
                )
                print(f"[FileProcessorWorker] {self.filename} completed with result: {result} on thread {thread_id} at {time.time():.3f}")
                self.file_completed.emit(self.filename, result)
            else:
                print(f"[FileProcessorWorker] No valid processing path found for {self.filename}")
                self.file_failed.emit(self.filename, "No valid processing path found")
            
        except Exception as e:
            print(f"[FileProcessorWorker] Error processing {self.filename}: {str(e)}")
            import traceback
            traceback.print_exc()
            self.file_failed.emit(self.filename, str(e))
